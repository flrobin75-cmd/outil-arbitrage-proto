"""
test_strategy_receptacles_goldens.py — Mini-goldens métier des modules réceptacles.

SP15 — Mécanisme de protection anti-régression économique (Q6=c).

Contexte
────────
Les goldens PDF SP11 (`test_pdf_audit_render_goldens.py`) protègent
contre les régressions de **rendu** (signets, codes étapes, KPIs,
texte normalisé). Ils ne détectent pas les régressions de **calcul**
(une formule fiscale qui dérive d'un cent, un plafond mal appliqué).

Les mini-goldens métier comblent ce vide : ils snapshot le **résultat
économique** sérialisé en JSON, indépendamment du rendu PDF. Une
régression de calcul (par exemple un bug introduit en SP16 qui
casserait PERIN par effet de bord) sera détectée immédiatement.

Discipline (validée par utilisateur G-3 / Q6=c)
──────────────────────────────────────────────
- Goldens **très ciblés** : 1-2 cas par enveloppe, pas de snapshots
  gigantesques
- Démarrage SP15 (PERIN seul), enrichissement progressif SP16-SP17
  (PEE, PERECO) puis consolidation SP18+
- Pattern verify/update similaire à SP11 (deux modes, var env
  `GOLDEN_METIER_UPDATE_FORCE=1` pour CI)

Cas couverts en SP15-SP16
──────────────────────────
- **Cas A — PERIN borné par plafond** (SP15) : profil par défaut, flux
  10 000 € → plafond 4 806 € (10 % PASS) borne le versement. Démontre
  le mécanisme de bornage.
- **Cas B — PERIN sous plafond** (SP15) : profil par défaut, flux
  2 000 € → versement intégral (sous plafond). Démontre la dépendance
  directe flux → valeur nette.
- **Cas C — PEE avec abondement plafonné** (SP16) : profil par défaut,
  flux salarié 5 000 €, abondement 100 % plafonné à 8 % PASS, frottement
  CSG-CRDS 9,7 %. Démontre la dualité flux salarié / abondement et
  l'écart entre effort réel et capital crédité.

Usage : python3 test_strategy_receptacles_goldens.py
        python3 test_strategy_receptacles_goldens.py --update

Exit code 0 si tous les goldens conformes, 1 si divergence,
2 si fichier golden absent.
"""

import json
import os
import sys
from dataclasses import asdict

sys.path.insert(0, os.path.dirname(__file__))

from core.profil import Profil
from strategy.receptacles_perin import allocation_perin
from strategy.receptacles_pee import allocation_pee
from strategy.receptacles_pereco import allocation_pereco
from strategy.receptacles_pero import allocation_pero


# ============================================================
# CONFIGURATION
# ============================================================
GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden_metiers")
GOLDEN_PRECISION = 0.01  # tolérance € pour comparaison


# ============================================================
# CAS DE TEST FIGÉS (cf. doctrine ci-dessus)
# ============================================================
CAS_GOLDENS_METIER = [
    {
        "nom": "borne_par_plafond",
        "enveloppe": "PERIN",
        "description": (
            "PERIN : profil par défaut (sans remuneration_brute), "
            "flux 10 000 €. Le plafond annuel se rabat à 10 % PASS "
            "= 4 806 €, qui borne le versement. Démontre le mécanisme "
            "de bornage et la fiscalité de sortie capital."
        ),
        "flux_disponible": 10000.0,
        "horizons": (5, 10, 20),
    },
    {
        "nom": "sous_plafond",
        "enveloppe": "PERIN",
        "description": (
            "PERIN : profil par défaut, flux 2 000 €. Reste sous le "
            "plafond (4 806 €). Démontre la dépendance directe entre "
            "flux d'entrée et trajectoires économiques (effort réel, "
            "capital projeté, valeur nette)."
        ),
        "flux_disponible": 2000.0,
        "horizons": (5, 10, 20),
    },
    {
        "nom": "abondement_plafonne",
        "enveloppe": "PEE",
        "description": (
            "PEE : profil par défaut, flux salarié 5 000 €. Abondement "
            "100 % du versement (fallback doctrinal Q8=a), plafonné à "
            "8 % PASS = 3 844,80 €, frottement CSG-CRDS 9,7 %. Démontre "
            "le mécanisme d'abondement et l'écart entre effort salarié "
            "(flux_entrant_brut) et capital crédité (incluant l'abondement net)."
        ),
        "flux_disponible": 5000.0,
        "horizons": (5, 10, 20),
    },
    {
        "nom": "hybride_perin_pee",
        "enveloppe": "PERECO",
        "description": (
            "PERECO : profil par défaut, flux salarié 5 000 €. Hybride "
            "PERIN+PEE — déductibilité IR à l'entrée (TMI 30 % fallback) "
            "comme PERIN, ET abondement employeur 100 % plafonné à 8 % "
            "PASS avec CSG-CRDS comme PEE. Démontre la combinaison "
            "doctrinale Q2=γ : éco_fiscale > 0 ET coût_entreprise > 0, "
            "fiscalité sortie distinguant versement salarié (IR TMI) et "
            "abondement (exonéré IR)."
        ),
        "flux_disponible": 5000.0,
        "horizons": (5, 10, 20),
    },
    {
        "nom": "composition_5000",
        "enveloppe": "ORCHESTRATEUR",
        "description": (
            "Orchestrateur : profil par défaut, flux 5 000 €. Snapshot "
            "de composition cross-enveloppes (SP18, Q3=b). Capture "
            "l'agrégation des 3 résultats enveloppe et les 9 étapes "
            "récapitulatives RECAP avec ordre stable PERIN → PEE → "
            "PERECO. Protège contre les régressions d'orchestration : "
            "mauvaise association horizon, oubli d'enveloppe, "
            "désynchronisation trace/dataclass, ordre non stable."
        ),
        "flux_disponible": 5000.0,
        "horizons": (5, 10, 20),
    },
    {
        "nom": "standard_80k_3pct",
        "enveloppe": "PERO",
        "description": (
            "PERO (SP24) : profil par défaut, TMI 30 %, salaire brut "
            "80 000 €, taux cotisation employeur 3 %, horizons 5/10/20. "
            "Cotisation 2 400 €/an, entièrement exonérée (sous plafond "
            "6 400 € = 8 % rém). Sémantique A-Q1=β : flux_entrant_brut "
            "= CSG/CRDS 232,80 €, économie fiscale 720 €, effort_reel "
            "négatif −487,20 € (TMI > CSG/CRDS), coût entreprise "
            "2 784 € (cotisation × 1,16). Sortie capital simplifiée "
            "(B-Q1=β, wording WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL)."
        ),
        "salaire_brut_annuel": 80_000.0,
        "taux_cotisation_pero": 0.03,
        "tmi": 0.30,
        "horizons": (5, 10, 20),
    },
    {
        "nom": "composition_pero_actif",
        "enveloppe": "ORCHESTRATEUR",
        "description": (
            "Orchestrateur SP25 : profil avec PERO actif "
            "(taux_cotisation_pero=3 %), flux 5 000 €. Démontre la "
            "composition à 4 enveloppes en configuration cabinet-ready : "
            "PERIN/PEE/PERECO calculés sur flux disponible 5 000 €, "
            "PERO calculé sur salaire brut assimilé 80 000 € × 3 %. "
            "Snapshot capture l'ordre stable PERIN → PEE → PERECO → "
            "PERO (4 sous-traces ligne_*, RECAP à 4 enveloppes avec "
            "valeurs PERO non nulles). Distinct du golden de baseline "
            "`composition_5000` qui capture PERO à zéro (taux par "
            "défaut). Protège contre les régressions d'intégration "
            "PERO côté orchestration."
        ),
        "flux_disponible": 5000.0,
        "taux_cotisation_pero_profil": 0.03,
        "horizons": (5, 10, 20),
    },
]


# ============================================================
# CALCUL DES INVARIANTS MÉTIER POUR UN CAS
# ============================================================
def _extraire_invariants_metier(cas: dict) -> dict:
    """Calcule le résultat d'allocation pour le cas donné et sérialise les
    invariants économiques en dict JSON-serializable.

    Route selon `cas['enveloppe']` :
      - PERIN/PEE/PERECO : snapshot enveloppe individuelle
      - ORCHESTRATEUR : snapshot de composition cross-enveloppes (SP18)

    On extrait les champs scalaires en arrondissant à 2 décimales pour :
      - une comparaison exacte (== sur dicts/listes)
      - une lisibilité humaine du fichier golden
      - une stabilité face aux flottants
    """
    profil = Profil()
    enveloppe = cas["enveloppe"]

    # ====== Cas SP18 : snapshot orchestrateur ======
    if enveloppe == "ORCHESTRATEUR":
        return _extraire_invariants_orchestrateur(cas, profil)

    # ====== Cas enveloppes individuelles SP15/SP16/SP17 ======
    if enveloppe == "PERIN":
        result = allocation_perin(
            profil,
            flux_disponible=cas["flux_disponible"],
            horizons=cas["horizons"],
        )
    elif enveloppe == "PEE":
        result = allocation_pee(
            profil,
            flux_disponible=cas["flux_disponible"],
            horizons=cas["horizons"],
        )
    elif enveloppe == "PERECO":
        result = allocation_pereco(
            profil,
            flux_disponible=cas["flux_disponible"],
            horizons=cas["horizons"],
        )
    elif enveloppe == "PERO":
        # SP24 : signature spécifique (salaire brut + taux cotisation),
        # TMI passée via attribut profil dynamique (pattern PERIN/PERECO).
        profil.tmi = float(cas["tmi"])
        result = allocation_pero(
            profil,
            salaire_brut_annuel=cas["salaire_brut_annuel"],
            taux_cotisation_pero=cas["taux_cotisation_pero"],
            horizons=cas["horizons"],
        )
    else:
        raise NotImplementedError(
            f"Enveloppe '{enveloppe}' non supportée en mini-golden."
        )

    # Sérialisation des lignes par horizon (uniforme grâce à
    # LigneHorizonReceptacle commun à toutes enveloppes)
    lignes_serializees = []
    for ligne in result.lignes_par_horizon:
        lignes_serializees.append({
            "horizon_annees": ligne.horizon_annees,
            "flux_entrant_brut": round(ligne.flux_entrant_brut, 2),
            "economie_fiscale_immediate": round(
                ligne.economie_fiscale_immediate, 2),
            "effort_reel": round(ligne.effort_reel, 2),
            "capital_projete": round(ligne.capital_projete, 2),
            "fiscalite_sortie": round(ligne.fiscalite_sortie, 2),
            "valeur_nette": round(ligne.valeur_nette, 2),
            "cout_entreprise": round(ligne.cout_entreprise, 2),
            "disponibilite": ligne.disponibilite,
        })

    # Inputs : PERO a une signature distincte (salaire/taux/TMI)
    # vs PERIN/PEE/PERECO (flux_disponible). On adapte le snapshot.
    if enveloppe == "PERO":
        snapshot = {
            "cas_nom": cas["nom"],
            "input_salaire_brut_annuel": cas["salaire_brut_annuel"],
            "input_taux_cotisation_pero": cas["taux_cotisation_pero"],
            "input_tmi": cas["tmi"],
            "input_horizons": list(cas["horizons"]),
            "enveloppe": result.enveloppe,
            "accessible": result.accessible,
            "lignes_par_horizon": lignes_serializees,
        }
        # Ajouter motif si applicable (pour cohérence avec PERIN/PEE/PERECO)
        if result.motif_inaccessibilite:
            snapshot["motif_inaccessibilite"] = result.motif_inaccessibilite
        return snapshot

    return {
        "cas_nom": cas["nom"],
        "input_flux_disponible": cas["flux_disponible"],
        "input_horizons": list(cas["horizons"]),
        "enveloppe": result.enveloppe,
        "accessible": result.accessible,
        "motif_inaccessibilite": result.motif_inaccessibilite,
        "lignes_par_horizon": lignes_serializees,
    }


def _extraire_invariants_orchestrateur(cas: dict, profil: Profil) -> dict:
    """Snapshot de composition orchestrateur (SP18, Q3=b).

    Capture l'agrégation des 3 résultats enveloppe ET les 9 étapes
    récapitulatives RECAP avec ordre stable PERIN → PEE → PERECO.

    Le format snapshot retient :
      - Concision : pour chaque horizon, on capture les 3 valeurs nettes
        + 3 efforts réels + 3 coûts entreprise (= 9 valeurs par horizon).
        Pas tous les champs des LigneHorizonReceptacle (déjà couverts
        par les goldens enveloppes individuels).
      - **Ordre stable explicite** : les hypothèses RECAP sont sérialisées
        comme **listes ordonnées de tuples** `[["PERIN", val], ["PEE", val],
        ["PERECO", val]]` plutôt que dicts. Cela rend l'ordre visible et
        détectable par diff JSON.
      - Couverture des bugs orchestrateur : association horizon
        incorrecte, oubli d'enveloppe, désynchronisation trace/dataclass.

    Args:
        cas: Définition du cas de test.
        profil: Profil instancié.

    Returns:
        Dict JSON-serializable décrivant la composition.
    """
    from core.audit import TraceAudit
    from strategy.receptacles_orchestrateur import allocation_receptacles

    # SP25 : si le cas spécifie un taux_cotisation_pero_profil,
    # on l'applique au profil pour activer PERO dans le snapshot.
    # Par défaut (cas baseline 'composition_5000'), PERO reste à
    # zéro (taux 0 % par défaut Profil).
    if "taux_cotisation_pero_profil" in cas:
        profil.taux_cotisation_pero = float(cas["taux_cotisation_pero_profil"])

    trace = TraceAudit(regime="Mini-golden orchestrateur", profil_resume="")
    result = allocation_receptacles(
        profil,
        flux_disponible=cas["flux_disponible"],
        horizons=cas["horizons"],
        audit=trace,
    )

    # 1. Composition dataclass : pour chaque enveloppe, valeurs nettes
    # par horizon (résumé compact)
    composition_dataclass = {
        "PERIN": {
            "enveloppe": result.perin.enveloppe,
            "accessible": result.perin.accessible,
            "valeurs_nettes_par_horizon": [
                {"horizon": l.horizon_annees,
                 "valeur_nette": round(l.valeur_nette, 2),
                 "effort_reel": round(l.effort_reel, 2),
                 "cout_entreprise": round(l.cout_entreprise, 2)}
                for l in result.perin.lignes_par_horizon
            ],
        },
        "PEE": {
            "enveloppe": result.pee.enveloppe,
            "accessible": result.pee.accessible,
            "valeurs_nettes_par_horizon": [
                {"horizon": l.horizon_annees,
                 "valeur_nette": round(l.valeur_nette, 2),
                 "effort_reel": round(l.effort_reel, 2),
                 "cout_entreprise": round(l.cout_entreprise, 2)}
                for l in result.pee.lignes_par_horizon
            ],
        },
        "PERECO": {
            "enveloppe": result.pereco.enveloppe,
            "accessible": result.pereco.accessible,
            "valeurs_nettes_par_horizon": [
                {"horizon": l.horizon_annees,
                 "valeur_nette": round(l.valeur_nette, 2),
                 "effort_reel": round(l.effort_reel, 2),
                 "cout_entreprise": round(l.cout_entreprise, 2)}
                for l in result.pereco.lignes_par_horizon
            ],
        },
        "PERO": {
            "enveloppe": result.pero.enveloppe,
            "accessible": result.pero.accessible,
            "valeurs_nettes_par_horizon": [
                {"horizon": l.horizon_annees,
                 "valeur_nette": round(l.valeur_nette, 2),
                 "effort_reel": round(l.effort_reel, 2),
                 "cout_entreprise": round(l.cout_entreprise, 2)}
                for l in result.pero.lignes_par_horizon
            ],
        },
    }

    # 2. Snapshot des étapes RECAP : on capture l'ordre dans une **liste**
    # plutôt qu'un dict pour rester insensible au sort_keys du dump JSON.
    etapes_recap_snapshot = []
    for etape in trace.etapes:
        if not etape.code.startswith("REC_RECAP_"):
            continue
        # Liste ordonnée des hypothèses enveloppes (ordre d'insertion
        # préservé par dict Python 3.7+)
        hypotheses_envs_ordonnees = []
        for cle, val in etape.hypotheses.items():
            if any(env in cle for env in ["PERIN", "PEE", "PERECO"]):
                # Garder l'ordre d'insertion via liste de tuples
                hypotheses_envs_ordonnees.append(
                    [cle, round(val, 2) if isinstance(val, (int, float))
                     else val]
                )
        etapes_recap_snapshot.append({
            "code": etape.code,
            "valeur_scalaire": etape.valeur,
            "hypotheses_enveloppes_ordonnees": hypotheses_envs_ordonnees,
            "ordre_stable_mention": etape.hypotheses.get("ordre_stable", ""),
        })

    # 3. Nombre de sous-traces enveloppes attachées (preuve de
    # composition complète : doit être exactement 3 : ligne_perin,
    # ligne_pee, ligne_pereco)
    sous_traces_attachees = list(trace.noms_sous_traces())

    return {
        "cas_nom": cas["nom"],
        "input_flux_disponible": cas["flux_disponible"],
        "input_horizons": list(cas["horizons"]),
        "enveloppe": "ORCHESTRATEUR",
        "composition_dataclass": composition_dataclass,
        "etapes_recap_snapshot": etapes_recap_snapshot,
        "sous_traces_attachees_ordonnees": sous_traces_attachees,
        "nb_etapes_racine_total": len(trace.etapes),
    }


# ============================================================
# COMPARAISON DEEP
# ============================================================
def _comparer_invariants(actuel: dict, attendu: dict,
                          chemin: str = "") -> list:
    """Compare récursivement deux dicts d'invariants.

    Retourne une liste de divergences (vide si conforme). Format :
    `[(chemin, actuel, attendu), ...]`.

    Tolérance numérique : 0,01 € sur les valeurs scalaires float
    (gestion des arrondis flottants).
    """
    divergences: list = []

    if isinstance(actuel, dict) and isinstance(attendu, dict):
        cles_communes = set(actuel.keys()) | set(attendu.keys())
        for cle in sorted(cles_communes):
            if cle not in actuel:
                divergences.append((f"{chemin}.{cle}", "<absent>",
                                    attendu[cle]))
            elif cle not in attendu:
                divergences.append((f"{chemin}.{cle}", actuel[cle],
                                    "<absent>"))
            else:
                divergences.extend(_comparer_invariants(
                    actuel[cle], attendu[cle], f"{chemin}.{cle}"))
        return divergences

    if isinstance(actuel, list) and isinstance(attendu, list):
        if len(actuel) != len(attendu):
            divergences.append((f"{chemin}[len]", len(actuel),
                                len(attendu)))
            return divergences
        for i, (a, b) in enumerate(zip(actuel, attendu)):
            divergences.extend(_comparer_invariants(
                a, b, f"{chemin}[{i}]"))
        return divergences

    # Comparaison scalaire
    if isinstance(actuel, float) and isinstance(attendu, (int, float)):
        if abs(actuel - attendu) > GOLDEN_PRECISION:
            divergences.append((chemin, actuel, attendu))
    elif actuel != attendu:
        divergences.append((chemin, actuel, attendu))
    return divergences


# ============================================================
# VERIFY / UPDATE
# ============================================================
def verifier_goldens() -> int:
    """Mode verify : compare l'état actuel aux fichiers golden figés."""
    print()
    print("=" * 90)
    print("  Mini-goldens métier — vérification")
    print("=" * 90)
    print()

    nb_conformes = 0
    nb_divergents = 0
    nb_absents = 0
    rapports: list = []

    for cas in CAS_GOLDENS_METIER:
        nom = cas["nom"]
        enveloppe = cas["enveloppe"]
        prefix = enveloppe.lower()
        chemin_golden = os.path.join(GOLDEN_DIR, f"{prefix}_{nom}.json")
        actuel = _extraire_invariants_metier(cas)

        if not os.path.exists(chemin_golden):
            print(f"  ⚠ {enveloppe}/{nom} : golden ABSENT ({chemin_golden})")
            nb_absents += 1
            rapports.append((nom, "absent", None))
            continue

        with open(chemin_golden, encoding="utf-8") as f:
            attendu = json.load(f)

        divergences = _comparer_invariants(actuel, attendu)

        if divergences:
            print(f"  ✗ {enveloppe}/{nom} : DIVERGENT ({len(divergences)} écart(s))")
            for chemin, val_actuel, val_attendu in divergences[:5]:
                print(f"      {chemin}: actuel={val_actuel!r} "
                      f"attendu={val_attendu!r}")
            if len(divergences) > 5:
                print(f"      ... ({len(divergences) - 5} autres)")
            nb_divergents += 1
            rapports.append((f"{enveloppe}/{nom}", "divergent", divergences))
        else:
            print(f"  ✓ {enveloppe}/{nom} : conforme")
            nb_conformes += 1
            rapports.append((f"{enveloppe}/{nom}", "conforme", None))

    print()
    print("=" * 90)
    print("  SYNTHÈSE")
    print("=" * 90)
    print(f"  Conformes  : {nb_conformes}/{len(CAS_GOLDENS_METIER)}")
    print(f"  Divergents : {nb_divergents}")
    print(f"  Absents    : {nb_absents}")
    print()

    if nb_absents > 0:
        print("  ⚠ Goldens absents — lancer `--update` pour les initialiser.")
        return 2
    if nb_divergents > 0:
        print("  ✗ Divergences détectées. Si volontaire, lancer `--update`.")
        return 1

    print(f"  ✓ Mini-goldens métier PASS — "
          f"{nb_conformes} cas conformes (anti-régression économique)")
    return 0


def update_goldens(force: bool = False) -> int:
    """Mode update : recalcule et écrase les goldens figés."""
    print()
    print("=" * 90)
    print("  Mini-goldens métier — mise à jour")
    print("=" * 90)
    print()

    if not force:
        print("  ⚠ Cette opération va écraser les fichiers golden figés.")
        print("  ⚠ Les régressions de calcul antérieures seront perdues.")
        print("  ⚠ Conserver les anciens fichiers en sauvegarde si besoin.")
        print()
        reponse = input("  Confirmer la mise à jour ? (oui/non) : ").strip().lower()
        if reponse not in ("oui", "o", "yes", "y"):
            print("  Mise à jour annulée.")
            return 1

    os.makedirs(GOLDEN_DIR, exist_ok=True)
    for cas in CAS_GOLDENS_METIER:
        nom = cas["nom"]
        enveloppe = cas["enveloppe"]
        prefix = enveloppe.lower()
        chemin_golden = os.path.join(GOLDEN_DIR, f"{prefix}_{nom}.json")
        invariants = _extraire_invariants_metier(cas)
        with open(chemin_golden, "w", encoding="utf-8") as f:
            json.dump(invariants, f, indent=2, ensure_ascii=False,
                      sort_keys=True)
        print(f"  ✓ {enveloppe}/{nom} → {chemin_golden}")

    print()
    print(f"  ✓ {len(CAS_GOLDENS_METIER)} goldens métier mis à jour.")
    return 0


def main(argv: list) -> int:
    if len(argv) > 1 and argv[1] == "--update":
        force = os.environ.get("GOLDEN_METIER_UPDATE_FORCE") == "1"
        return update_goldens(force=force)
    return verifier_goldens()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
