"""
Moteur Synthèse dirigeant - livrable consulting-grade pour EC.

Périmètre v1 Phase A : régime Assimilé salarié uniquement (cohérent avec Arbitrage v1).
Les autres régimes (TNS / Libéral / Salarié) afficheront une note de bascule v2.

Décisions structurantes :
- Radar 6D pédagogique (axes renommés, scoring pondéré pour Protection sociale)
- Forfaits cabinet éditables avec toggle actif/inactif
- Bloc patrimonial compact + drill-down vers page dédiée
- Vocabulaire dirigeant (pas EC) dans les messages principaux
- Réutilisation des alertes du Comparateur Option 2 (factorisation)

Date de dernière mise à jour réglementaire : 01/01/2026.

MODE_AUDIT (G3e, spec 1.1.0) :
- Les fonctions principales acceptent un paramètre opt-in `audit: TraceAudit | None`.
  Codes émis : `SYNTH_*` (namespace dédié, distinct des comparateurs G3d).
- Découpage en sous-passes :
  * G3e-synthese.1 : `reset_forfaits` + `calcul_couts_mise_en_oeuvre` (codes `SYNTH_COUTS_*`)
  * G3e-synthese.2 : `calcul_radar_6d` + `calcul_projection_5_ans` + `calcul_decomposition_gain`
  * G3e-synthese.3 : `calcul_enveloppes_patrimoniales` + `calcul_checklist_conformite`
  * G3e-synthese.4 : `calcul_synthese` + 4 `_synthese_<regime>` (routeur)
- Composition (§9.2) : uniquement `_synthese_salarie` attache une sous-trace
  `module_salarie` (seul appel à un module instrumenté). Toutes les autres
  fonctions sont à trace plate, structurées par `parent_id`.
- Discipline non-prescriptive : champs Python `meilleure` (enveloppes) et
  les libellés source (« Stratégie A — Référence salaire ») sont préservés
  en `hypotheses` selon le pattern G3b/c/d. Les labels MODE_AUDIT restent
  factuels (« enveloppe au plus haut net disponible »).
"""

from dataclasses import dataclass, field
from typing import Optional
from core.profil import Profil, PASS_2026
from core.audit import TraceAudit
from strategy.comparateur import AlertePlafond, PLAF_ABO_PEE, PLAF_ABO_PERECO


# ============================================================
# FORFAITS CABINET PAR DÉFAUT (éditables côté UI)
# ============================================================
@dataclass
class ForfaitCabinet:
    """Un poste de coût cabinet, éditable avec toggle actif/inactif."""
    libelle: str
    montant_defaut: float
    montant: float
    actif: bool = True
    condition: str = ""    # Note de condition d'affichage

    def reset(self):
        """Réinitialise au montant par défaut."""
        self.montant = self.montant_defaut


FORFAITS_DEFAUT = {
    "cadrage": ForfaitCabinet("Mission cabinet — cadrage stratégique",
                              1200, 1200, True, "Forfait initial"),
    "interessement": ForfaitCabinet("Mise en place accord intéressement",
                                    800, 800, True, "Si intéressement activé"),
    "pee_per": ForfaitCabinet("Mise en place règlement PEE / PER",
                              1500, 1500, True, "Si PEE ou PER collectif activé"),
    "pero": ForfaitCabinet("Mise en place PERO (catégorie objective)",
                           1200, 1200, True, "Si PERO activé"),
    "teneur_compte_petit": ForfaitCabinet("Frais teneur de compte PEE/PER (annuel)",
                                          600, 600, True, "Si effectif ≤49 salariés"),
    "teneur_compte_grand": ForfaitCabinet("Frais teneur de compte PEE/PER (annuel)",
                                          1200, 1200, True, "Si effectif ≥50 salariés"),
    "audit_peripheriques": ForfaitCabinet("Audit conformité périphériques (TR, CESU, AN)",
                                          600, 600, True, "Si C+ et périphériques activés"),
    "audit_cashback": ForfaitCabinet("Audit cashback mode Conforme",
                                     900, 900, True, "Si cashback Conforme"),
}


def reset_forfaits(forfaits: dict,
                   *,
                   audit: TraceAudit | None = None) -> dict:
    """Réinitialise tous les forfaits aux valeurs par défaut.

    Args:
        forfaits: Dict de ForfaitCabinet à réinitialiser.
        audit: Trace d'audit optionnelle (G3e-synthese.1). Side channel.
            Codes émis : `SYNTH_RESET_FORFAITS_*`. Aucune sous-trace.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SYNTH_RESET_FORFAITS_" + suffixe, label, valeur, **kw)

    _log("NB_FORFAITS",
         "Nombre de forfaits réinitialisés",
         float(len(forfaits)), unite="count",
         hypotheses={"cles_forfaits": list(forfaits.keys())})

    for forfait in forfaits.values():
        forfait.reset()
    return forfaits


# ============================================================
# CALCUL A — COÛTS DE MISE EN ŒUVRE
# ============================================================
@dataclass
class CoutMiseEnOeuvre:
    libelle: str
    montant: float
    note: str


def calcul_couts_mise_en_oeuvre(profil: Profil,
                                strategie_retenue: str,
                                forfaits: dict,
                                config_comparateur=None,
                                *,
                                audit: TraceAudit | None = None) -> list:
    """
    Calcule la liste des postes de coûts cabinet applicables.

    Args:
        profil: Profil client
        strategie_retenue: "A", "B", "C" ou "D"
        forfaits: Dict des forfaits cabinet (éditables)
        config_comparateur: ConfigComparateur si disponible (pour conditions)
        audit: Trace d'audit optionnelle (G3e-synthese.1). Side channel.
            Codes émis : `SYNTH_COUTS_*`. Aucune sous-trace (module autonome).

    Returns:
        Liste de CoutMiseEnOeuvre filtrée selon conditions d'applicabilité.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SYNTH_COUTS_" + suffixe, label, valeur, **kw)

    # --- Traces d'inputs ---
    _log("STRATEGIE_RETENUE",
         "Code stratégie retenue (input)",
         strategie_retenue, unite="",
         hypotheses={"valeurs_attendues": ["A", "B", "C", "D"]})
    _log("NB_FORFAITS_DISPONIBLES",
         "Nombre de forfaits définis dans la config cabinet",
         float(len(forfaits)), unite="count",
         hypotheses={"cles_forfaits": list(forfaits.keys())})
    _log("NB_FORFAITS_ACTIFS",
         "Nombre de forfaits avec toggle actif=True",
         float(sum(1 for f in forfaits.values() if f.actif)),
         unite="count",
         hypotheses={"toggle_par_forfait": {k: f.actif for k, f in forfaits.items()}})
    _log("CONFIG_COMPARATEUR_PRESENTE",
         "Booléen : présence d'une ConfigComparateur en input",
         1.0 if config_comparateur is not None else 0.0,
         unite="bool",
         notes="Si absente, seuls les forfaits inconditionnels sont retenus")
    _log("EFFECTIF_PROFIL",
         "Effectif déclaré au profil (détermine teneur_compte_petit vs _grand)",
         profil.effectif, unite="")

    couts = []

    # Toujours présent
    if forfaits["cadrage"].actif:
        couts.append(CoutMiseEnOeuvre(
            forfaits["cadrage"].libelle,
            forfaits["cadrage"].montant,
            "Inclut audit du dossier et restitution client"
        ))

    # Conditions selon stratégie + activation dispositifs
    # Stratégie A : aucun dispositif → seul le cadrage
    if strategie_retenue == "A":
        # Trace de sortie avant return
        _log("NB_POSTES_RETENUS",
             "Nombre de postes de coût retenus (stratégie A : cadrage uniquement si actif)",
             float(len(couts)), unite="count",
             hypotheses={"convention_strategie_A": "Seul le cadrage est retenu"})
        for idx, c in enumerate(couts):
            _log(f"POSTE_{idx:02d}_CADRAGE",
                 f"Poste {idx:02d} — {c.libelle}",
                 c.montant, unite="EUR",
                 parent_id="SYNTH_COUTS_NB_POSTES_RETENUS",
                 hypotheses={"note_source": c.note})
        _log("TOTAL",
             "Somme des montants des postes retenus",
             sum(c.montant for c in couts), unite="EUR")
        return couts

    # Stratégie B et + : épargne salariale potentielle
    if config_comparateur:
        # Intéressement
        if (forfaits["interessement"].actif
                and config_comparateur.interessement.actif):
            couts.append(CoutMiseEnOeuvre(
                forfaits["interessement"].libelle,
                forfaits["interessement"].montant,
                "Rédaction de l'accord + dépôt DDETSPP + information salariés"
            ))

        # PEE / PER collectif
        if (forfaits["pee_per"].actif
                and (config_comparateur.abondement_pee.actif
                     or config_comparateur.abondement_pereco.actif
                     or config_comparateur.participation.actif)):
            couts.append(CoutMiseEnOeuvre(
                forfaits["pee_per"].libelle,
                forfaits["pee_per"].montant,
                "Conventionnement teneur de compte + rédaction règlement"
            ))

            # Frais teneur de compte selon effectif
            effectif_petit = profil.effectif in ["Sans salarié", "1-10 salariés",
                                                  "11-49 salariés"]
            if effectif_petit and forfaits["teneur_compte_petit"].actif:
                couts.append(CoutMiseEnOeuvre(
                    forfaits["teneur_compte_petit"].libelle,
                    forfaits["teneur_compte_petit"].montant,
                    "Frais récurrents selon prestataire"
                ))
            elif not effectif_petit and forfaits["teneur_compte_grand"].actif:
                couts.append(CoutMiseEnOeuvre(
                    forfaits["teneur_compte_grand"].libelle,
                    forfaits["teneur_compte_grand"].montant,
                    "Frais récurrents selon prestataire"
                ))

        # PERO
        if forfaits["pero"].actif and config_comparateur.pero_actif and config_comparateur.dirigeant_eligible_pero:
            couts.append(CoutMiseEnOeuvre(
                forfaits["pero"].libelle,
                forfaits["pero"].montant,
                "Définition catégorie objective + accord + dépôt URSSAF"
            ))

    # Stratégie C+ : périphériques
    if strategie_retenue in ["C", "D"] and config_comparateur:
        if forfaits["audit_peripheriques"].actif and (
                config_comparateur.tr_actif or config_comparateur.cesu_actif
                or config_comparateur.avantages_actif):
            couts.append(CoutMiseEnOeuvre(
                forfaits["audit_peripheriques"].libelle,
                forfaits["audit_peripheriques"].montant,
                "Vérification plafonds + politique RH + bulletins de paie"
            ))

    # Stratégie D : cashback éventuel
    if (strategie_retenue == "D" and config_comparateur
            and config_comparateur.cashback_actif
            and forfaits["audit_cashback"].actif):
        couts.append(CoutMiseEnOeuvre(
            forfaits["audit_cashback"].libelle,
            forfaits["audit_cashback"].montant,
            "Note méthodologique + suivi + archivage"
        ))

    # --- MODE_AUDIT G3e-synthese.1 — Trace de sortie ---
    if audit is not None:
        # Mapping libellé → clé de forfait pour le code court (factuel)
        _MAPPING_NOM_COURT = {
            forfaits["cadrage"].libelle: "CADRAGE",
            forfaits["interessement"].libelle: "INTERESSEMENT",
            forfaits["pee_per"].libelle: "PEE_PER",
            forfaits["teneur_compte_petit"].libelle: "TENEUR_COMPTE_PETIT",
            forfaits["teneur_compte_grand"].libelle: "TENEUR_COMPTE_GRAND",
            forfaits["pero"].libelle: "PERO",
            forfaits["audit_peripheriques"].libelle: "AUDIT_PERIPHERIQUES",
            forfaits["audit_cashback"].libelle: "AUDIT_CASHBACK",
        }

        audit.add("SYNTH_COUTS_NB_POSTES_RETENUS",
                  "Nombre de postes de coût retenus après application des conditions",
                  float(len(couts)), unite="count",
                  hypotheses={
                      "conditions_appliquees": (
                          "stratégie B+ : intéressement / PEE-PER / PERO ; "
                          "stratégie C+ : audit périphériques ; "
                          "stratégie D : audit cashback"
                      ),
                  })

        for idx, c in enumerate(couts):
            nom_court = _MAPPING_NOM_COURT.get(c.libelle, f"POSTE_{idx:02d}")
            audit.add(
                f"SYNTH_COUTS_POSTE_{idx:02d}_{nom_court}",
                f"Poste {idx:02d} — {nom_court.lower().replace('_', ' ')}",
                c.montant, unite="EUR",
                parent_id="SYNTH_COUTS_NB_POSTES_RETENUS",
                hypotheses={
                    "libelle_integral": c.libelle,
                    "note_source": c.note,
                },
            )

        audit.add("SYNTH_COUTS_TOTAL",
                  "Somme des montants des postes retenus",
                  sum(c.montant for c in couts), unite="EUR",
                  hypotheses={"nb_postes_calcule": len(couts)})

    return couts


# ============================================================
# CALCUL B — RADAR 6D PÉDAGOGIQUE
# ============================================================
@dataclass
class ScoreRadar:
    """Score d'une stratégie sur les 6 axes du radar."""
    nom_strategie: str           # "A", "B", "C", "D"
    net_dirigeant: float          # 0-100
    protection_sociale: float     # 0-100
    fiscalite: float              # 0-100
    preparation_retraite: float   # 0-100
    liquidite: float              # 0-100
    maitrise_charges: float       # 0-100


# Pondérations Protection sociale (validation utilisateur)
# Salaire ouvre tous les droits, PERO crée retraite, épargne sal. très limitée,
# dividendes/cashback ne créent aucun droit social
PONDS_PROTECTION = {
    "salaire": 1.0,
    "pero": 0.6,
    "epargne_salariale": 0.3,
    "dividendes": 0.1,
    "cashback": 0.0,
}


def calcul_radar_6d(strategies: dict,
                    *,
                    audit: TraceAudit | None = None) -> list:
    """
    Calcule les scores des 4 stratégies sur les 6 axes du radar.

    Args:
        strategies: Dict {"A": dict, "B": dict, ...} avec pour chaque stratégie :
            - total_net : net total dirigeant
            - cout_total : coût société
            - net_salaire, net_dividendes, net_epargne, net_peripheriques
            - cout_salaire, cout_dividendes, cout_epargne, cout_peripheriques
            - net_pero (0 par défaut, > 0 si PERO activé)
            - net_cashback (0 par défaut)
        audit: Trace d'audit optionnelle (G3e-synthese.2). Side channel.
            Codes émis : `SYNTH_RADAR_*`. Aucune sous-trace.

    Returns:
        Liste de ScoreRadar (un par stratégie).
    """
    net_max = max(s["total_net"] for s in strategies.values())
    scores = []

    # --- MODE_AUDIT G3e-synthese.2 — Traces d'inputs et invariants ---
    NOTE_RADAR_INTRA_REGIME = (
        "Le radar 6D est un outil de comparaison INTRA-régime (A/B/C/D Assimilé "
        "uniquement) ou descriptif. Il ne doit pas être utilisé pour classer "
        "les régimes entre eux : les axes sont calibrés différemment selon le "
        "régime considéré."
    )

    if audit is not None:
        audit.add("SYNTH_RADAR_NB_AXES",
                  "Nombre d'axes du radar pédagogique",
                  6.0, unite="count",
                  hypotheses={"axes": ["net_dirigeant", "protection_sociale",
                                       "fiscalite", "preparation_retraite",
                                       "liquidite", "maitrise_charges"]})
        audit.add("SYNTH_RADAR_NOTE_INTRA_REGIME",
                  "Note doctrinale : portée intra-régime du radar 6D",
                  1.0, unite="count",
                  hypotheses={"NOTE_RADAR_INTRA_REGIME": NOTE_RADAR_INTRA_REGIME,
                              "portee": "INTRA-régime ou descriptif",
                              "interdiction": "ne pas utiliser pour classer entre régimes"},
                  notes="Rappel doctrinal — wording métier en hypotheses")
        audit.add("SYNTH_RADAR_NB_STRATEGIES",
                  "Nombre de stratégies évaluées sur le radar",
                  float(len(strategies)), unite="count",
                  hypotheses={"codes_strategies": list(strategies.keys())})
        audit.add("SYNTH_RADAR_NET_MAX_REFERENCE",
                  "Net dirigeant maximum parmi les stratégies (base de normalisation axe 1)",
                  net_max, unite="EUR",
                  hypotheses={"tous_nets": {c: s["total_net"]
                                            for c, s in strategies.items()}})

    for code, s in strategies.items():
        # 1. Net dirigeant - score relatif au net max
        net_dirigeant = (s["total_net"] / net_max * 100) if net_max > 0 else 0

        # 2. Protection sociale - score pondéré
        # Décomposition fictive : net_salaire / net_pero / net_epargne / net_div / net_cashback
        # Si net_pero non fourni, on suppose 0 (cohérent v1 sans PERO dans Arbitrage)
        net_pero = s.get("net_pero", 0)
        net_cashback = s.get("net_cashback", 0)
        protection_brute = (
            s["net_salaire"] * PONDS_PROTECTION["salaire"]
            + net_pero * PONDS_PROTECTION["pero"]
            + s["net_epargne"] * PONDS_PROTECTION["epargne_salariale"]
            + s["net_dividendes"] * PONDS_PROTECTION["dividendes"]
            + net_cashback * PONDS_PROTECTION["cashback"]
        )
        # Normalisation : score max possible si tout en salaire pur
        protection_max_possible = s["total_net"] * PONDS_PROTECTION["salaire"]
        protection_sociale = ((protection_brute / protection_max_possible * 100)
                              if protection_max_possible > 0 else 0)

        # 3. Fiscalité - 100 - (ce qui sort en impôts et cotis) / coût total
        depenses_fiscales = s["cout_total"] - s["total_net"]
        fiscalite = ((1 - depenses_fiscales / s["cout_total"]) * 100
                     if s["cout_total"] > 0 else 0)

        # 4. Préparation retraite - part de l'épargne capitalisable
        retraite_brute = s["net_epargne"] + net_pero
        preparation_retraite = ((retraite_brute / s["total_net"] * 100)
                                if s["total_net"] > 0 else 0)

        # 5. Liquidité - part immédiatement disponible
        liquidite_brute = s["net_salaire"] + s["net_dividendes"]
        liquidite = ((liquidite_brute / s["total_net"] * 100)
                     if s["total_net"] > 0 else 0)

        # 6. Maîtrise des charges - 100 - cotisations / coût total
        # Cotisations = coût total - net brut allocations (i.e. ce qui part en cotis sociales/IS)
        # Approximation : cotisations = total société - somme des montants nets allocations
        # Plus simple : on inverse la fiscalité partiellement
        # Approche pragmatique : on calcule la part "non charges sociales" du coût
        # Dans la stratégie A (100% salaire), les charges sont max
        # Dans la stratégie D (mix avec exonérés), les charges sont min
        # Formule : 100 - (charges sociales / coût total × 100)
        # Charges sociales = coût salaire - net salaire avant IR (estimation)
        # Approximation simple : charges sociales = coût salaire × ratio cotisations
        # Pour l'Arbitrage Assimilé, ratio cotisations ≈ (TX_PATRONAL + TX_SALARIAL × (1-TX_PATRONAL)) ≈ 51%
        # On utilise une approche structurelle : part du coût total qui n'est pas alloué
        # à salaire pur (donc moins de cotisations sociales)
        cout_salaire = s.get("cout_salaire", 0)
        # Estimation des cotisations sociales : ~51 % du coût salaire (TX_PAT 42% + TX_SAL 12% sur 70 %)
        # Pour les autres allocations (dividendes, épargne, périphériques), les cotisations
        # sont marginales ou nulles
        cotisations_estimees = cout_salaire * 0.51
        maitrise_charges = ((1 - cotisations_estimees / s["cout_total"]) * 100
                            if s["cout_total"] > 0 else 0)

        # --- MODE_AUDIT G3e-synthese.2 — Trace des 6 axes pour cette stratégie ---
        if audit is not None:
            audit.add(f"SYNTH_RADAR_NET_DIRIGEANT_{code}",
                      f"Axe 1 (net dirigeant) — stratégie {code}",
                      net_dirigeant, unite="score 0-100",
                      parent_id="SYNTH_RADAR_NB_AXES",
                      hypotheses={"formule": "total_net / net_max × 100",
                                  "total_net_strategie": s["total_net"],
                                  "net_max_reference": net_max})
            audit.add(f"SYNTH_RADAR_PROTECTION_SOCIALE_{code}",
                      f"Axe 2 (protection sociale, pondéré) — stratégie {code}",
                      protection_sociale, unite="score 0-100",
                      parent_id="SYNTH_RADAR_NB_AXES",
                      hypotheses={"PONDS_PROTECTION": dict(PONDS_PROTECTION),
                                  "protection_brute_calculee": protection_brute,
                                  "protection_max_possible": protection_max_possible,
                                  "composantes_brutes": {
                                      "net_salaire": s["net_salaire"],
                                      "net_pero": net_pero,
                                      "net_epargne": s["net_epargne"],
                                      "net_dividendes": s["net_dividendes"],
                                      "net_cashback": net_cashback,
                                  }})
            audit.add(f"SYNTH_RADAR_FISCALITE_{code}",
                      f"Axe 3 (fiscalité, inverse des dépenses fiscales) — stratégie {code}",
                      fiscalite, unite="score 0-100",
                      parent_id="SYNTH_RADAR_NB_AXES",
                      hypotheses={"formule": "(1 - depenses_fiscales / cout_total) × 100",
                                  "depenses_fiscales_calculees": depenses_fiscales,
                                  "cout_total_strategie": s["cout_total"]})
            audit.add(f"SYNTH_RADAR_PREPARATION_RETRAITE_{code}",
                      f"Axe 4 (préparation retraite, part épargne+PERO) — stratégie {code}",
                      preparation_retraite, unite="score 0-100",
                      parent_id="SYNTH_RADAR_NB_AXES",
                      hypotheses={"formule": "(net_epargne + net_pero) / total_net × 100",
                                  "retraite_brute_calculee": retraite_brute})
            audit.add(f"SYNTH_RADAR_LIQUIDITE_{code}",
                      f"Axe 5 (liquidité, part salaire+dividendes) — stratégie {code}",
                      liquidite, unite="score 0-100",
                      parent_id="SYNTH_RADAR_NB_AXES",
                      hypotheses={"formule": "(net_salaire + net_dividendes) / total_net × 100",
                                  "liquidite_brute_calculee": liquidite_brute})
            audit.add(f"SYNTH_RADAR_MAITRISE_CHARGES_{code}",
                      f"Axe 6 (maîtrise des charges, inverse cotisations) — stratégie {code}",
                      maitrise_charges, unite="score 0-100",
                      parent_id="SYNTH_RADAR_NB_AXES",
                      hypotheses={"formule": "(1 - cotisations_estimees / cout_total) × 100",
                                  "ratio_cotisations_estimees": 0.51,
                                  "justification_ratio": (
                                      "TX_PATRONAL 42% + TX_SALARIAL 12% sur 70% du brut "
                                      "≈ 51% (approximation v19 pour Assimilé salarié)"
                                  ),
                                  "cout_salaire_strategie": cout_salaire,
                                  "cotisations_estimees_calculees": cotisations_estimees})

        scores.append(ScoreRadar(
            nom_strategie=code,
            net_dirigeant=net_dirigeant,
            protection_sociale=protection_sociale,
            fiscalite=fiscalite,
            preparation_retraite=preparation_retraite,
            liquidite=liquidite,
            maitrise_charges=maitrise_charges,
        ))

    return scores


# ============================================================
# CALCUL C — PROJECTION PATRIMOINE 5 ANS
# ============================================================
def calcul_projection_5_ans(strategies: dict, code_retenue: str = "C",
                            *,
                            audit: TraceAudit | None = None) -> dict:
    """
    Projection patrimoine cumulé sur 5 ans pour stratégie A vs retenue.

    Hypothèses :
    - Net cash réinvesti en cash défensif (rdt 2 %)
    - Net épargne salariale & PER capitalisé à 4 %
    - Capitalisation annuelle composée, versement en début d'année

    Args:
        strategies: Dict des stratégies (mêmes structure que calcul_radar_6d).
        code_retenue: Stratégie retenue à comparer à A (par défaut "C").
        audit: Trace d'audit optionnelle (G3e-synthese.2). Side channel.
            Codes émis : `SYNTH_PROJECTION_*`. Aucune sous-trace.
    """
    RDT_CASH = 0.02
    RDT_EPARGNE = 0.04

    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SYNTH_PROJECTION_" + suffixe, label, valeur, **kw)

    _log("CODE_RETENUE",
         "Code stratégie retenue pour la comparaison (input)",
         code_retenue, unite="",
         hypotheses={"valeurs_attendues": ["A", "B", "C", "D"],
                     "reference_comparaison": "Stratégie A"})
    _log("RDT_CASH",
         "Rendement annuel cash défensif (hypothèse)",
         RDT_CASH, unite="ratio",
         hypotheses={"note": "Hypothèse locale au module synthèse, "
                             "non-doctrine centralisée"})
    _log("RDT_EPARGNE",
         "Rendement annuel épargne salariale et PER (hypothèse)",
         RDT_EPARGNE, unite="ratio",
         hypotheses={"note": "Hypothèse locale au module synthèse, "
                             "non-doctrine centralisée"})

    def projection_strategie(s, fraction_capitalisable_implicite=0.0):
        """Projection sur 5 ans d'une stratégie."""
        net = s["total_net"]
        # Si l'info net_epargne est dispo, on l'utilise pour fraction réelle
        if s.get("net_epargne", 0) > 0:
            fraction = s["net_epargne"] / net
        else:
            fraction = fraction_capitalisable_implicite

        annees = []
        for annee in range(1, 6):
            # Capitalisation cash défensif
            valeur_cash = net * (1 - fraction) * ((1 + RDT_CASH) ** annee - 1) / RDT_CASH * (1 + RDT_CASH)
            # Capitalisation épargne
            valeur_epargne = net * fraction * ((1 + RDT_EPARGNE) ** annee - 1) / RDT_EPARGNE * (1 + RDT_EPARGNE)
            annees.append(valeur_cash + valeur_epargne)
        return annees

    proj_a = projection_strategie(strategies["A"])
    proj_retenue = projection_strategie(strategies[code_retenue])
    ecarts = [r - a for r, a in zip(proj_retenue, proj_a)]

    # --- MODE_AUDIT G3e-synthese.2 — Trace des projections par année ---
    if audit is not None:
        audit.add("SYNTH_PROJECTION_NB_ANNEES",
                  "Nombre d'années projetées",
                  5.0, unite="count")

        for annee_idx, (val_a, val_r, ecart) in enumerate(zip(proj_a, proj_retenue, ecarts), start=1):
            audit.add(f"SYNTH_PROJECTION_ANNEE_{annee_idx}_A",
                      f"Année {annee_idx} — stratégie A (cumul capitalisé)",
                      val_a, unite="EUR",
                      parent_id="SYNTH_PROJECTION_NB_ANNEES",
                      hypotheses={"annee": annee_idx,
                                  "code_strategie": "A"})
            audit.add(f"SYNTH_PROJECTION_ANNEE_{annee_idx}_RETENUE",
                      f"Année {annee_idx} — stratégie retenue {code_retenue} (cumul capitalisé)",
                      val_r, unite="EUR",
                      parent_id="SYNTH_PROJECTION_NB_ANNEES",
                      hypotheses={"annee": annee_idx,
                                  "code_strategie": code_retenue})
            audit.add(f"SYNTH_PROJECTION_ECART_ANNEE_{annee_idx}",
                      f"Année {annee_idx} — écart retenue − A",
                      ecart, unite="EUR",
                      parent_id="SYNTH_PROJECTION_NB_ANNEES",
                      hypotheses={"annee": annee_idx,
                                  "valeur_retenue": val_r,
                                  "valeur_a": val_a})

        audit.add("SYNTH_PROJECTION_GAIN_5_ANS",
                  "Gain cumulé à 5 ans (écart année 5)",
                  ecarts[-1], unite="EUR",
                  hypotheses={"derniere_annee_retenue": proj_retenue[-1],
                              "derniere_annee_a": proj_a[-1]})

    return {
        "annees": list(range(1, 6)),
        "strategie_a": proj_a,
        "strategie_retenue": proj_retenue,
        "code_retenue": code_retenue,
        "ecarts": ecarts,
        "gain_5_ans": ecarts[-1],
    }


# ============================================================
# CALCUL D — DÉCOMPOSITION DU GAIN vs A (WATERFALL)
# ============================================================
@dataclass
class EtapeWaterfall:
    libelle: str
    net_dirigeant: float
    contribution: float    # vs étape précédente
    cumul_vs_a: float       # cumul vs stratégie A


def calcul_decomposition_gain(strategies: dict,
                              *,
                              audit: TraceAudit | None = None) -> list:
    """Construit la décomposition incrémentale A → B → C → D.

    Args:
        strategies: Dict des stratégies (mêmes structure que calcul_radar_6d).
        audit: Trace d'audit optionnelle (G3e-synthese.2). Side channel.
            Codes émis : `SYNTH_DECOMPOSITION_*`. Aucune sous-trace.
            Les libellés source (« + Allocation dividendes »…) sont
            préservés en `hypotheses["libelle_source"]` ; les labels
            MODE_AUDIT restent factuels (« contribution incrémentale »).
    """
    ordre = ["A", "B", "C", "D"]
    etapes = []
    net_precedent = strategies["A"]["total_net"]
    net_a = strategies["A"]["total_net"]

    libelles = {
        "A": "Stratégie A — Référence salaire",
        "B": "+ Allocation dividendes",
        "C": "+ Épargne salariale & PER",
        "D": "+ Périphériques & cashback",
    }

    for code in ordre:
        net = strategies[code]["total_net"]
        contribution = net - net_precedent if code != "A" else 0
        cumul = net - net_a
        etapes.append(EtapeWaterfall(
            libelle=libelles[code],
            net_dirigeant=net,
            contribution=contribution,
            cumul_vs_a=cumul,
        ))
        net_precedent = net

    # --- MODE_AUDIT G3e-synthese.2 — Trace de la décomposition ---
    if audit is not None:
        audit.add("SYNTH_DECOMPOSITION_NB_ETAPES",
                  "Nombre d'étapes de la décomposition incrémentale (waterfall)",
                  float(len(etapes)), unite="count",
                  hypotheses={"ordre": ordre,
                              "libelles_source": dict(libelles)})

        for idx, (code, etape) in enumerate(zip(ordre, etapes)):
            audit.add(f"SYNTH_DECOMPOSITION_ETAPE_{idx}_{code}",
                      f"Étape {idx} ({code}) — net + contribution incrémentale + cumul vs A",
                      etape.contribution, unite="EUR",
                      parent_id="SYNTH_DECOMPOSITION_NB_ETAPES",
                      hypotheses={"code_strategie": code,
                                  "libelle_source": etape.libelle,
                                  "net_dirigeant": etape.net_dirigeant,
                                  "cumul_vs_a": etape.cumul_vs_a,
                                  "convention_etape_A": "contribution = 0 par convention"})

    return etapes


# ============================================================
# CALCUL E — ENVELOPPES PATRIMONIALES (bloc compact + détail)
# ============================================================
@dataclass
class EnveloppePatrimoniale:
    nom: str
    versement: float
    valeur_brute: float
    fiscalite_sortie: str
    net_disponible: float
    avantage_cle: str


def calcul_enveloppes_patrimoniales(montant: float = 10_000,
                                     horizon: int = 5,
                                     rendement: float = 0.05,
                                     situation: str = "Marié / pacsé",
                                     *,
                                     audit: TraceAudit | None = None) -> dict:
    """
    Calcule la performance fiscale comparée de 4 enveloppes patrimoniales.

    Args:
        montant: Capital initial placé
        horizon: Horizon de placement (années)
        rendement: Rendement annuel brut (ex: 0.05 = 5 %)
        situation: "Marié / pacsé" ou "Célibataire / divorcé / veuf"
        audit: Trace d'audit optionnelle (G3e-synthese.3a). Side channel.
            Codes émis : `SYNTH_ENV_*`. Aucune sous-trace.
            Le champ Python `meilleure` du résultat est préservé tel quel
            pour la rétrocompat ; côté trace, l'étape correspondante est
            nommée `SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE` (factuel).
    """
    TX_PFU = 0.314
    PS_TAUX = 0.172
    PFU_AV_REDUIT = 0.075
    ABATTEMENT_AV = 9_200 if situation == "Marié / pacsé" else 4_600

    valeur_brute = montant * (1 + rendement) ** horizon
    plus_value = valeur_brute - montant

    # CTO - PFU 31,4 % sur PV
    net_cto = montant + plus_value * (1 - TX_PFU)

    # PEA - après 5 ans exo IR + PS 17,2 % sur PV
    if horizon >= 5:
        net_pea = montant + plus_value * (1 - PS_TAUX)
    else:
        net_pea = montant + plus_value * (1 - TX_PFU)

    # Assurance-vie - après 8 ans : abattement + PFU réduit + PS
    if horizon >= 8:
        pv_taxable = max(0, plus_value - ABATTEMENT_AV)
        net_av = montant + plus_value * (1 - PS_TAUX) - pv_taxable * PFU_AV_REDUIT
    else:
        # Avant 8 ans : PFU classique
        net_av = montant + plus_value * (1 - TX_PFU)

    # PER individuel - sortie en capital : IR barème sortie + PS sur PV
    # Hypothèse : TMI moyen estimé à 30 % à la sortie (à affiner via TMI réel)
    tmi_sortie = 0.30
    net_per = valeur_brute * (1 - tmi_sortie) - plus_value * PS_TAUX

    enveloppes = [
        EnveloppePatrimoniale(
            nom="CTO — Compte-titres ordinaire",
            versement=montant, valeur_brute=valeur_brute,
            fiscalite_sortie="PFU 31,4 % sur les gains",
            net_disponible=net_cto,
            avantage_cle="Liquidité totale",
        ),
        EnveloppePatrimoniale(
            nom="PEA — après 5 ans",
            versement=montant, valeur_brute=valeur_brute,
            fiscalite_sortie="Exo IR sur PV, PS 17,2 %",
            net_disponible=net_pea,
            avantage_cle="Exo IR après 5 ans",
        ),
        EnveloppePatrimoniale(
            nom="Assurance-vie — après 8 ans",
            versement=montant, valeur_brute=valeur_brute,
            fiscalite_sortie=f"Abattement {ABATTEMENT_AV:,.0f} € + PFU 7,5 % + PS 17,2 %".replace(",", " "),
            net_disponible=net_av,
            avantage_cle="Transmission privilégiée",
        ),
        EnveloppePatrimoniale(
            nom="PER individuel — sortie capital",
            versement=montant, valeur_brute=valeur_brute,
            fiscalite_sortie="IR barème sortie sur capital + PS 17,2 % sur gains",
            net_disponible=net_per,
            avantage_cle="Économie IR à l'entrée",
        ),
    ]

    # Meilleure enveloppe
    meilleure = max(enveloppes, key=lambda e: e.net_disponible)

    # --- MODE_AUDIT G3e-synthese.3a — Trace des enveloppes patrimoniales ---
    if audit is not None:
        # Mapping nom → clé courte factuelle pour code MODE_AUDIT
        _MAPPING_NOM_COURT = {
            "CTO — Compte-titres ordinaire": "CTO",
            "PEA — après 5 ans": "PEA",
            "Assurance-vie — après 8 ans": "ASSURANCE_VIE",
            "PER individuel — sortie capital": "PER_INDIVIDUEL",
        }

        # Traces d'inputs et hypothèses paramétriques
        audit.add("SYNTH_ENV_MONTANT_INITIAL",
                  "Capital initial placé (input)",
                  montant, unite="EUR")
        audit.add("SYNTH_ENV_HORIZON",
                  "Horizon de placement (input)",
                  float(horizon), unite="années")
        audit.add("SYNTH_ENV_RENDEMENT",
                  "Rendement annuel brut (input)",
                  rendement, unite="ratio")
        audit.add("SYNTH_ENV_SITUATION",
                  "Situation foyer (détermine abattement assurance-vie)",
                  situation, unite="",
                  hypotheses={"valeurs_attendues": ["Marié / pacsé",
                                                    "Célibataire / divorcé / veuf"],
                              "ABATTEMENT_AV_calcule": ABATTEMENT_AV})

        # Hypothèses fiscales locales au module (à signaler comme telles)
        audit.add("SYNTH_ENV_HYPOTHESES_FISCALES",
                  "Hypothèses fiscales locales appliquées (taux et abattement)",
                  4.0, unite="count",
                  hypotheses={"TX_PFU": TX_PFU,
                              "PS_TAUX": PS_TAUX,
                              "PFU_AV_REDUIT": PFU_AV_REDUIT,
                              "ABATTEMENT_AV": ABATTEMENT_AV,
                              "tmi_sortie_per": tmi_sortie,
                              "note_tmi_sortie": (
                                  "Hypothèse TMI moyen 30 % à la sortie PER — "
                                  "à affiner via TMI réel du foyer (cf. commentaire source)"
                              )},
                  notes="Hypothèses locales au module synthèse, "
                        "non-doctrine centralisée")

        # Valeur brute commune
        audit.add("SYNTH_ENV_VALEUR_BRUTE_5ANS",
                  "Valeur brute capitalisée sur l'horizon",
                  valeur_brute, unite="EUR",
                  hypotheses={"formule": "montant × (1 + rendement) ^ horizon"})
        audit.add("SYNTH_ENV_PLUS_VALUE",
                  "Plus-value brute (valeur_brute − montant)",
                  plus_value, unite="EUR")

        audit.add("SYNTH_ENV_NB_ENVELOPPES",
                  "Nombre d'enveloppes comparées",
                  float(len(enveloppes)), unite="count",
                  hypotheses={"enveloppes_comparees": [e.nom for e in enveloppes]})

        # Une étape par enveloppe (net disponible factuel)
        for env in enveloppes:
            nom_court = _MAPPING_NOM_COURT.get(env.nom, "ENVELOPPE")
            audit.add(
                f"SYNTH_ENV_NET_DISPONIBLE_{nom_court}",
                f"Net disponible — enveloppe {nom_court.lower()}",
                env.net_disponible, unite="EUR",
                parent_id="SYNTH_ENV_NB_ENVELOPPES",
                hypotheses={
                    "nom_integral": env.nom,
                    "versement": env.versement,
                    "valeur_brute": env.valeur_brute,
                    "fiscalite_sortie_source": env.fiscalite_sortie,
                    "avantage_cle_source": env.avantage_cle,
                },
            )

        # Enveloppe au net le plus élevé (factuel, pas "meilleure")
        audit.add("SYNTH_ENV_CRITERE_CLASSEMENT",
                  "Critère de classement appliqué",
                  "max(net_disponible)", unite="",
                  notes="Classement mécanique sur le net disponible — "
                        "ne reflète pas un avis sur le choix d'enveloppe.")
        audit.add("SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE",
                  "Enveloppe au plus haut net disponible (indicateur factuel)",
                  meilleure.nom, unite="",
                  parent_id="SYNTH_ENV_CRITERE_CLASSEMENT",
                  hypotheses={"champ_source_python": "meilleure",
                              "note_mapping": "Le champ Python du résultat "
                                              "est préservé tel quel pour rétrocompat",
                              "net_calcule": meilleure.net_disponible,
                              "tous_nets": {e.nom: e.net_disponible
                                            for e in enveloppes}},
                  notes="Terminologie MODE_AUDIT factuelle.")

    return {
        "enveloppes": enveloppes,
        "meilleure": meilleure.nom,
        "hypothese_texte": (f"Hypothèse : rendement annuel moyen {rendement*100:.0f} %, "
                            f"fiscalité en vigueur au 01/01/2026."),
    }


# ============================================================
# CALCUL F — CHECK-LIST CONFORMITÉ FACTORISÉE
# ============================================================
@dataclass
class PointControle:
    libelle: str
    statut: str       # "✅", "⚠", "🔴", "-"
    action: str       # Texte à afficher si statut ≠ ✅


def calcul_checklist_conformite(profil: Profil,
                                config_comparateur,
                                strategie_retenue: str,
                                alertes_comparateur: list,
                                *,
                                audit: TraceAudit | None = None) -> list:
    """
    Construit la check-list de conformité de la stratégie retenue.

    Factorisation : on réutilise les alertes du Comparateur Option 2 et on ajoute
    les checks spécifiques v19 manquants (accord intéressement, règlement PEE).

    Args:
        profil: Profil client
        config_comparateur: ConfigComparateur
        strategie_retenue: "A", "B", "C" ou "D"
        alertes_comparateur: Liste d'AlertePlafond du Comparateur
        audit: Trace d'audit optionnelle (G3e-synthese.3b). Side channel.
            Codes émis : `SYNTH_CHECKLIST_*`. Aucune sous-trace.
            Discipline non-prescriptive renforcée : les libellés source
            (« encouragée », « à mettre en place », « Vérifier ») restent
            en `hypotheses` (`libelle_integral`, `action_source`), jamais
            en label/notes. Les labels MODE_AUDIT parlent strictement de
            statut, seuil, point de contrôle, présence/absence.

    Returns:
        Liste de PointControle.
    """
    points = []

    # Seules les stratégies B+ activent des dispositifs
    if strategie_retenue == "A":
        points.append(PointControle(
            "Stratégie A — référence salaire pur",
            "-",
            "Aucun dispositif à mettre en place"
        ))

        # --- MODE_AUDIT — Stratégie A : 1 point unique statut "-" ---
        if audit is not None:
            audit.add("SYNTH_CHECKLIST_NB_POINTS_TOTAL",
                      "Nombre total de points de contrôle construits",
                      1.0, unite="count",
                      hypotheses={"convention_strategie_A":
                                  "1 point unique statut '-' (référence salaire pur, aucun dispositif activé)"})
            audit.add("SYNTH_CHECKLIST_NB_POINTS_PAR_STATUT",
                      "Ventilation du nombre de points par statut catégoriel",
                      4.0, unite="count",
                      hypotheses={"statut_ok": 0, "statut_warning": 0,
                                  "statut_error": 0, "statut_neutre": 1})
            audit.add("SYNTH_CHECKLIST_POINT_00_STRATEGIE_A",
                      "Point 00 — statut neutre stratégie A (référence salaire pur)",
                      "-", unite="",
                      parent_id="SYNTH_CHECKLIST_NB_POINTS_TOTAL",
                      hypotheses={
                          "statut_pictogramme": "-",
                          "libelle_integral": "Stratégie A — référence salaire pur",
                          "action_source": "Aucun dispositif à mettre en place",
                          "origine": "convention_strategie_A",
                      })
        return points

    # 1. Conversion des alertes du Comparateur en points de contrôle
    alertes_origines = []  # pour traçabilité MODE_AUDIT
    for alerte in alertes_comparateur:
        if alerte.severite == "error":
            points.append(PointControle(alerte.titre, "🔴", alerte.message))
            alertes_origines.append(("alerte_comparateur", alerte))
        elif alerte.severite == "warning":
            points.append(PointControle(alerte.titre, "⚠", alerte.message))
            alertes_origines.append(("alerte_comparateur", alerte))
        # severité "info" : on ne crée pas de point de contrôle (informatif uniquement)

    nb_phase1 = len(points)  # frontière entre Phase 1 (alertes) et Phase 2 (checks v19)

    # 2. Checks v19 spécifiques non couverts par le Comparateur
    checks_v19_origines = []  # tracé pour MODE_AUDIT (ordre conservé)

    # 2a - Effectif compatible avec participation obligatoire
    if config_comparateur.participation.actif:
        effectif_petit = profil.effectif in ["Sans salarié", "1-10 salariés",
                                              "11-49 salariés"]
        if effectif_petit:
            points.append(PointControle(
                "Effectif compatible avec dispositif participation",
                "⚠",
                "Participation obligatoire à partir de 50 salariés. "
                "Mise en place facultative en dessous (encouragée)."
            ))
            checks_v19_origines.append(("EFFECTIF_PARTICIPATION",
                                        "participation.actif AND effectif<50"))
        else:
            points.append(PointControle(
                "Effectif compatible avec dispositif participation",
                "✅",
                ""
            ))
            checks_v19_origines.append(("EFFECTIF_PARTICIPATION",
                                        "participation.actif AND effectif>=50"))

    # 2b - Accord d'intéressement formalisé (vigilance ≥ 3 ans)
    if config_comparateur.interessement.actif:
        points.append(PointControle(
            "Accord d'intéressement formalisé ≥ 3 ans",
            "⚠",
            "Vérifier l'existence d'un accord triennal déposé à la DDETSPP. "
            "À défaut : à mettre en place."
        ))
        checks_v19_origines.append(("ACCORD_INTERESSEMENT",
                                    "interessement.actif"))

    # 2c - Règlement PEE déposé et information salariés
    if (config_comparateur.abondement_pee.actif
            or config_comparateur.participation.actif):
        points.append(PointControle(
            "Règlement PEE déposé et information salariés",
            "⚠",
            "Vérifier dépôt règlement PEE et livret épargne salariale remis."
        ))
        checks_v19_origines.append(("REGLEMENT_PEE",
                                    "abondement_pee.actif OR participation.actif"))

    # 2d - Ratio dividendes / capital social pour TNS gérant maj.
    if ("TNS" in profil.regime_social
            and profil.dividendes_foyer_hors_enveloppe > 0):
        points.append(PointControle(
            "Ratio dividendes / capital social (TNS gérant maj.)",
            "⚠",
            "Dividendes > 10 % du capital + primes + CCA soumis à cotisations TNS. "
            "Vérifier le seuil dans le module TNS."
        ))
        checks_v19_origines.append(("RATIO_DIV_CAPITAL_TNS",
                                    "regime_social=TNS AND dividendes_foyer_hors_enveloppe>0"))

    # 2e - PERO catégorie objective (point spécifique Option 2)
    if config_comparateur.pero_actif and config_comparateur.dirigeant_eligible_pero:
        points.append(PointControle(
            "PERO — Catégorie objective formalisée",
            "⚠",
            "Vérifier que la catégorie objective éligible PERO est définie par "
            "accord d'entreprise / référendum / DUE (décision unilatérale)."
        ))
        checks_v19_origines.append(("PERO_CAT_OBJECTIVE",
                                    "pero_actif AND dirigeant_eligible_pero"))

    # --- MODE_AUDIT G3e-synthese.3b — Trace de sortie ---
    if audit is not None:
        # Ventilation par statut catégoriel
        nb_ok = sum(1 for p in points if p.statut == "✅")
        nb_warning = sum(1 for p in points if p.statut == "⚠")
        nb_error = sum(1 for p in points if p.statut == "🔴")
        nb_neutre = sum(1 for p in points if p.statut == "-")

        audit.add("SYNTH_CHECKLIST_NB_POINTS_TOTAL",
                  "Nombre total de points de contrôle construits",
                  float(len(points)), unite="count",
                  hypotheses={"phase_1_alertes_comparateur": nb_phase1,
                              "phase_2_checks_v19_specifiques":
                                  len(points) - nb_phase1,
                              "statuts_categoriels_attendus":
                                  ["✅", "⚠", "🔴", "-"]})
        audit.add("SYNTH_CHECKLIST_NB_POINTS_PAR_STATUT",
                  "Ventilation du nombre de points par statut catégoriel",
                  4.0, unite="count",
                  hypotheses={"statut_ok": nb_ok,
                              "statut_warning": nb_warning,
                              "statut_error": nb_error,
                              "statut_neutre": nb_neutre})

        # Mapping des suffixes courts par ordre stable
        # Phase 1 : POINT_NN_ALERTE_COMP_<idx> séquentiel
        # Phase 2 : POINT_NN_<NOM_CHECK_V19>
        _MAPPING_ORDRE_CHECKS = {origine: nom_court
                                  for nom_court, condition in checks_v19_origines
                                  for origine in [nom_court]}

        idx_phase2 = 0
        for idx, p in enumerate(points):
            if idx < nb_phase1:
                # Phase 1 : alerte du Comparateur
                _, alerte = alertes_origines[idx]
                code = f"SYNTH_CHECKLIST_POINT_{idx:02d}_ALERTE_COMP_{idx:02d}"
                origine = "alerte_comparateur"
                condition_activation = f"alerte.severite={alerte.severite!r}"
                alerte_titre_court = alerte.titre
            else:
                # Phase 2 : check v19 spécifique
                nom_check, condition_activation = checks_v19_origines[idx_phase2]
                code = f"SYNTH_CHECKLIST_POINT_{idx:02d}_{nom_check}"
                origine = "check_v19_specifique"
                alerte_titre_court = None
                idx_phase2 += 1

            audit.add(
                code,
                f"Point {idx:02d} — statut '{p.statut}' (point de contrôle factuel)",
                p.statut, unite="",
                parent_id="SYNTH_CHECKLIST_NB_POINTS_TOTAL",
                hypotheses={
                    "statut_pictogramme": p.statut,
                    "libelle_integral": p.libelle,
                    "action_source": p.action,
                    "condition_activation": condition_activation,
                    "origine": origine,
                    **({"alerte_titre_court": alerte_titre_court}
                       if alerte_titre_court else {}),
                },
            )

    return points


# ============================================================
# AVERTISSEMENT RADAR (texte validé)
# ============================================================
AVERTISSEMENT_RADAR = (
    "Ce radar est un comparateur indicatif destiné à visualiser les équilibres "
    "entre stratégies. Les scores sont calculés à partir de ratios simplifiés "
    "et ne remplacent pas une analyse personnalisée."
)


# ============================================================
# SYNTHÈSE GLOBALE - ASSEMBLAGE FINAL
# ============================================================
@dataclass
class ResultatSynthese:
    """Résultat complet du module Synthèse."""
    # Méta
    profil: Profil
    strategie_retenue: str
    date_reglementaire: str = "01/01/2026"

    # Résultats clés
    net_dirigeant_retenu: float = 0.0
    gain_vs_a: float = 0.0
    gain_5_ans: float = 0.0

    # Sections
    couts_mise_en_oeuvre: list = field(default_factory=list)
    total_couts: float = 0.0
    roi_mois: Optional[float] = None
    scores_radar: list = field(default_factory=list)
    projection: dict = field(default_factory=dict)
    decomposition: list = field(default_factory=list)
    enveloppes_compact: dict = field(default_factory=dict)
    checklist: list = field(default_factory=list)


def _synthese_assimile(profil: Profil,
                       strategies_arbitrage: dict,
                       config_comparateur,
                       code_retenue: Optional[str] = None,
                       forfaits: Optional[dict] = None,
                       alertes_comparateur: Optional[list] = None,
                       *,
                       audit: TraceAudit | None = None) -> ResultatSynthese:
    """
    Synthèse Assimilé salarié — implémentation historique (Phase A).

    Cette fonction préserve la logique v19 stricte pour le régime Assimilé.
    Pas de modification de comportement vs Phase A : parité 504/504 garantie.

    Args:
        profil: Profil client (regime_social = "Assimilé salarié")
        strategies_arbitrage: Dict des stratégies A/B/C/D (input)
        config_comparateur: ConfigComparateur
        code_retenue: Code de la stratégie retenue (sinon prend max(total_net))
        forfaits: Dict des forfaits cabinet (sinon FORFAITS_DEFAUT)
        alertes_comparateur: Liste d'AlertePlafond
        audit: Trace d'audit optionnelle (G3e-synthese.4). Codes émis :
            `SYNTH_ASSIM_*` méta. Attache 6 sous-traces nommées
            (`couts`, `radar`, `projection`, `decomposition`, `enveloppes`,
            `checklist`) qui composent les 6 fonctions instrumentées
            G3e-synthese.1/2/3.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SYNTH_ASSIM_" + suffixe, label, valeur, **kw)

    if forfaits is None:
        forfaits = FORFAITS_DEFAUT.copy()
    if alertes_comparateur is None:
        alertes_comparateur = []

    # Détermination stratégie retenue (par défaut net max)
    if code_retenue is None:
        code_retenue = max(strategies_arbitrage.keys(),
                           key=lambda c: strategies_arbitrage[c]["total_net"])

    net_retenu = strategies_arbitrage[code_retenue]["total_net"]
    net_a = strategies_arbitrage["A"]["total_net"]
    gain_vs_a = net_retenu - net_a

    # --- Calculs des sections avec sous-traces composées ---
    if audit is not None:
        st_couts = TraceAudit(regime="Synthèse Assimilé — coûts",
                              profil_resume=f"strategie={code_retenue}")
        couts = calcul_couts_mise_en_oeuvre(profil, code_retenue, forfaits,
                                            config_comparateur, audit=st_couts)
        audit.attacher_sous_trace("couts", st_couts)

        st_radar = TraceAudit(regime="Synthèse Assimilé — radar 6D")
        scores_radar = calcul_radar_6d(strategies_arbitrage, audit=st_radar)
        audit.attacher_sous_trace("radar", st_radar)

        st_proj = TraceAudit(regime="Synthèse Assimilé — projection 5 ans")
        projection = calcul_projection_5_ans(strategies_arbitrage, code_retenue,
                                              audit=st_proj)
        audit.attacher_sous_trace("projection", st_proj)

        st_decomp = TraceAudit(regime="Synthèse Assimilé — décomposition")
        decomposition = calcul_decomposition_gain(strategies_arbitrage,
                                                   audit=st_decomp)
        audit.attacher_sous_trace("decomposition", st_decomp)

        st_env = TraceAudit(regime="Synthèse Assimilé — enveloppes",
                            profil_resume=f"situation={profil.situation}")
        enveloppes = calcul_enveloppes_patrimoniales(situation=profil.situation,
                                                     audit=st_env)
        audit.attacher_sous_trace("enveloppes", st_env)

        st_check = TraceAudit(regime="Synthèse Assimilé — checklist")
        checklist = calcul_checklist_conformite(profil, config_comparateur,
                                                 code_retenue, alertes_comparateur,
                                                 audit=st_check)
        audit.attacher_sous_trace("checklist", st_check)
    else:
        couts = calcul_couts_mise_en_oeuvre(profil, code_retenue, forfaits,
                                            config_comparateur)
        scores_radar = calcul_radar_6d(strategies_arbitrage)
        projection = calcul_projection_5_ans(strategies_arbitrage, code_retenue)
        decomposition = calcul_decomposition_gain(strategies_arbitrage)
        enveloppes = calcul_enveloppes_patrimoniales(situation=profil.situation)
        checklist = calcul_checklist_conformite(profil, config_comparateur,
                                                 code_retenue, alertes_comparateur)

    total_couts = sum(c.montant for c in couts)
    roi_mois = (total_couts / gain_vs_a * 12) if gain_vs_a > 0 else None

    # --- Trace méta SYNTH_ASSIM_* ---
    _log("REGIME",
         "Régime traité par cette synthèse",
         "Assimilé salarié", unite="")
    _log("CODE_RETENUE",
         "Code stratégie retenue (input ou plus haut total_net par défaut)",
         code_retenue, unite="",
         hypotheses={"valeurs_attendues": list(strategies_arbitrage.keys()),
                     "convention_defaut": "max(total_net) parmi A/B/C/D"})
    _log("NET_DIRIGEANT_RETENU",
         "Net dirigeant de la stratégie retenue",
         net_retenu, unite="EUR")
    _log("NET_REFERENCE_A",
         "Net dirigeant de la stratégie A (référence)",
         net_a, unite="EUR")
    _log("GAIN_VS_A",
         "Écart net retenue − A",
         gain_vs_a, unite="EUR",
         hypotheses={"convention": "Indicateur factuel, pas un avis"})
    _log("TOTAL_COUTS",
         "Somme des coûts de mise en œuvre (sous-trace couts)",
         total_couts, unite="EUR")
    _log("ROI_MOIS",
         "Nombre de mois pour amortir total_couts par gain_vs_a (si gain_vs_a > 0)",
         roi_mois if roi_mois is not None else 0.0,
         unite="mois",
         hypotheses={"formule": "total_couts / gain_vs_a × 12 si gain_vs_a > 0",
                     "definie": roi_mois is not None})
    _log("GAIN_5_ANS",
         "Écart cumulé à 5 ans (depuis sous-trace projection)",
         projection["gain_5_ans"], unite="EUR")

    return ResultatSynthese(
        profil=profil,
        strategie_retenue=code_retenue,
        net_dirigeant_retenu=net_retenu,
        gain_vs_a=gain_vs_a,
        gain_5_ans=projection["gain_5_ans"],
        couts_mise_en_oeuvre=couts,
        total_couts=total_couts,
        roi_mois=roi_mois,
        scores_radar=scores_radar,
        projection=projection,
        decomposition=decomposition,
        enveloppes_compact=enveloppes,
        checklist=checklist,
    )


# ============================================================
# ROUTEUR PUBLIC — calcul_synthese (Phase B.2 Étape 4a)
# ============================================================
def calcul_synthese(profil: Profil,
                    strategies_arbitrage: dict,
                    config_comparateur,
                    code_retenue: Optional[str] = None,
                    forfaits: Optional[dict] = None,
                    alertes_comparateur: Optional[list] = None,
                    *,
                    audit: TraceAudit | None = None) -> ResultatSynthese:
    """
    Construit la Synthèse complète à partir des résultats Arbitrage et Comparateur.

    Routeur multi-régimes (Phase B.2 Étape 4a) : délègue à la sous-fonction
    appropriée selon profil.regime_social.

    - Assimilé salarié → _synthese_assimile (logique Phase A, parité v19 stricte)
    - TNS → _synthese_tns (stratégies T1-T4)
    - TNS (libéral) → _synthese_liberal (stratégies L1-L4, alerte BNC/SEL)
    - autres → _synthese_salarie (référence module détaillé)

    Args:
        profil: Profil client (regime_social détermine la sous-fonction)
        strategies_arbitrage: Dict des stratégies du régime (forme variable)
        config_comparateur: ConfigComparateur
        code_retenue: Stratégie retenue. Si None, on prend la meilleure du régime.
        forfaits: Dict des forfaits cabinet (sinon utilise FORFAITS_DEFAUT)
        alertes_comparateur: Liste d'AlertePlafond (sinon liste vide)
        audit: Trace d'audit optionnelle (G3e-synthese.4). Code méta émis :
            `SYNTH_REGIME_DISPATCH`. Une sous-trace `synthese_<regime>` est
            attachée pour préserver le détail des calculs régime.
    """
    regime = profil.regime_social

    # --- Trace méta du dispatch ---
    _MAPPING_DISPATCH = {
        "Assimilé salarié": "_synthese_assimile",
        "TNS": "_synthese_tns",
        "TNS (libéral)": "_synthese_liberal",
    }
    fonction_cible = _MAPPING_DISPATCH.get(regime, "_synthese_salarie")
    if audit is not None:
        audit.add("SYNTH_REGIME_DISPATCH",
                  "Régime aiguillé vers la sous-fonction de synthèse",
                  fonction_cible, unite="",
                  hypotheses={"regime_profil": regime,
                              "mapping_dispatch": _MAPPING_DISPATCH,
                              "fallback": "_synthese_salarie (régimes hors mapping)"},
                  notes="Dispatch fonctionnel, aucun calcul à ce niveau — "
                        "détails dans la sous-trace régime attachée.")

    # --- Dispatch + attachement sous-trace régime ---
    if audit is not None:
        st_regime = TraceAudit(
            regime=f"Synthèse {regime}",
            profil_resume=f"regime={regime}",
        )
        if regime == "Assimilé salarié":
            resultat = _synthese_assimile(profil, strategies_arbitrage,
                                           config_comparateur, code_retenue,
                                           forfaits, alertes_comparateur,
                                           audit=st_regime)
            nom_sous_trace = "synthese_assimile"
        elif regime == "TNS":
            resultat = _synthese_tns(profil, strategies_arbitrage,
                                      config_comparateur, code_retenue,
                                      forfaits, alertes_comparateur,
                                      audit=st_regime)
            nom_sous_trace = "synthese_tns"
        elif regime == "TNS (libéral)":
            resultat = _synthese_liberal(profil, strategies_arbitrage,
                                          config_comparateur, code_retenue,
                                          forfaits, alertes_comparateur,
                                          audit=st_regime)
            nom_sous_trace = "synthese_liberal"
        else:
            resultat = _synthese_salarie(profil, strategies_arbitrage,
                                          config_comparateur, code_retenue,
                                          forfaits, alertes_comparateur,
                                          audit=st_regime)
            nom_sous_trace = "synthese_salarie"
        audit.attacher_sous_trace(nom_sous_trace, st_regime)
        return resultat

    # Branche sans audit (rétrocompat stricte)
    if regime == "Assimilé salarié":
        return _synthese_assimile(profil, strategies_arbitrage, config_comparateur,
                                   code_retenue, forfaits, alertes_comparateur)
    elif regime == "TNS":
        return _synthese_tns(profil, strategies_arbitrage, config_comparateur,
                              code_retenue, forfaits, alertes_comparateur)
    elif regime == "TNS (libéral)":
        return _synthese_liberal(profil, strategies_arbitrage, config_comparateur,
                                  code_retenue, forfaits, alertes_comparateur)
    else:
        # Cas Salarié (régime non dirigeant) ou inconnu → traitement référence
        return _synthese_salarie(profil, strategies_arbitrage, config_comparateur,
                                  code_retenue, forfaits, alertes_comparateur)


# ============================================================
# SOUS-FONCTIONS PRIVÉES PAR RÉGIME — Phase B.2 Étape 4a
# ============================================================
def _synthese_tns(profil: Profil,
                  strategies_arbitrage: dict,
                  config_comparateur,
                  code_retenue: Optional[str] = None,
                  forfaits: Optional[dict] = None,
                  alertes_comparateur: Optional[list] = None,
                  *,
                  audit: TraceAudit | None = None) -> ResultatSynthese:
    """
    Synthèse TNS — stratégies T1-T4.

    GARDE-FOU T4 : net_dirigeant_retenu utilise uniquement net_dirigeant_immediat.
    Le benefice_retenu_societe de T4 n'est PAS additionné. Une mention spécifique
    est ajoutée dans le résultat si T4 est la stratégie retenue.

    Args:
        strategies_arbitrage: dict {"T1": ResultatStrategieTNS, ...} ou équivalent.
            Si dict de dataclasses, on accède aux attributs ; si dict de dicts,
            on accède aux clés.
        audit: Trace d'audit optionnelle (G3e-synthese.4). Codes émis :
            `SYNTH_TNS_*` méta. Inclut `SYNTH_TNS_INDICATEURS_SEPARES_T4`
            (garde-fou transversal hérité du module TNS via G3b/G3d-bis).
            Aucune sous-trace attachée (la fonction n'appelle pas les
            fonctions instrumentées G3e-synthese.1-3 — implémentation
            allégée v1).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SYNTH_TNS_" + suffixe, label, valeur, **kw)

    if forfaits is None:
        forfaits = FORFAITS_DEFAUT.copy()
    if alertes_comparateur is None:
        alertes_comparateur = []

    # Helper pour accéder uniformément aux champs (dataclass ou dict)
    def get_net_immediat(s):
        return s.net_dirigeant_immediat if hasattr(s, 'net_dirigeant_immediat') else s["net_dirigeant_immediat"]

    def get_benefice_retenu(s):
        return s.benefice_retenu_societe if hasattr(s, 'benefice_retenu_societe') else s.get("benefice_retenu_societe", 0.0)

    def get_alertes(s):
        return s.alertes if hasattr(s, 'alertes') else s.get("alertes", [])

    # Détermination stratégie retenue (par défaut : meilleur net immédiat)
    if code_retenue is None:
        code_retenue = max(strategies_arbitrage.keys(),
                           key=lambda c: get_net_immediat(strategies_arbitrage[c]))

    strat_retenue = strategies_arbitrage[code_retenue]
    net_retenu = get_net_immediat(strat_retenue)

    # Référence T1 (équivalent A pour TNS)
    ref_code = "T1" if "T1" in strategies_arbitrage else code_retenue
    net_ref = get_net_immediat(strategies_arbitrage[ref_code])
    gain_vs_ref = net_retenu - net_ref

    # Projection 5 ans sur le net retenu uniquement (PAS sur bénéfice retenu)
    from core.projection import projection_5_ans
    proj_vals = projection_5_ans(net_retenu, fraction_capitalisable=0.5)
    gain_5_ans = proj_vals[4] - net_retenu * 5

    # Radar 6D : pour TNS, on calcule sur les 4 stratégies T1-T4
    # Adaptation simple : convertir en format compatible avec calcul_radar_6d existant
    # qui attend un dict avec "total_net"
    strategies_pour_radar = {}
    for code, s in strategies_arbitrage.items():
        strategies_pour_radar[code] = {
            "total_net": get_net_immediat(s),
            "code": code,
        }
    # Note : calcul_radar_6d nécessite la structure A/B/C/D, donc on en fait un adaptateur
    # plus simple en attendant l'extension complète du Radar.
    scores_radar = []

    # Checklist conformité : version allégée pour TNS (pas d'historique alertes Comparateur identique)
    checklist = []

    # Alertes spécifiques au régime TNS retenu
    alertes_specifiques = list(get_alertes(strat_retenue))

    # Si T4 retenue, alerte explicite : le net immédiat ne reflète pas la totalité
    benefice_retenu_value = get_benefice_retenu(strat_retenue)
    texte_alerte_t4_ajoute = None
    if code_retenue == "T4":
        if benefice_retenu_value > 0:
            texte_alerte_t4_ajoute = (
                f"Stratégie T4 retenue : bénéfice retenu en société = {benefice_retenu_value:,.2f} €. "
                f"Cette valeur est conservée par la société et NE FIGURE PAS dans le net dirigeant "
                f"affiché. Sa distribution ultérieure subira la fiscalité applicable au moment de "
                f"la distribution."
            )
            alertes_specifiques.append(texte_alerte_t4_ajoute)

    # --- Trace méta SYNTH_TNS_* ---
    _log("REGIME",
         "Régime traité par cette synthèse",
         "TNS", unite="")
    _log("CODE_RETENUE",
         "Code stratégie retenue (input ou plus haut net_dirigeant_immediat par défaut)",
         code_retenue, unite="",
         hypotheses={"valeurs_attendues": list(strategies_arbitrage.keys()),
                     "convention_defaut": "max(net_dirigeant_immediat) parmi T1-T4"})
    _log("NET_DIRIGEANT_RETENU",
         "Net dirigeant immédiat de la stratégie retenue",
         net_retenu, unite="EUR")
    _log("NET_REFERENCE_T1",
         "Net dirigeant immédiat de la stratégie T1 (référence)",
         net_ref, unite="EUR",
         hypotheses={"code_reference": ref_code})
    _log("GAIN_VS_T1",
         "Écart net retenue − T1",
         gain_vs_ref, unite="EUR",
         hypotheses={"nomme_dans_resultat": "gain_vs_a (mais = vs_T1 pour TNS)",
                     "convention": "Indicateur factuel, pas un avis"})
    _log("GAIN_5_ANS",
         "Écart cumulé à 5 ans (depuis projection_5_ans, sur net retenu uniquement)",
         gain_5_ans, unite="EUR",
         hypotheses={"fraction_capitalisable": 0.5,
                     "exclusion_t4": "PAS calculé sur bénéfice retenu T4"})

    # --- Garde-fou T4 transversal (hérité G3b/G3d-bis) ---
    _log("INDICATEURS_SEPARES_T4",
         "Bénéfice retenu T4 (indicateur séparé, jamais agrégé au net dirigeant)",
         benefice_retenu_value, unite="EUR",
         hypotheses={"convention": "non-agrégation T4 (transversale au module synthèse)",
                     "applicable_a_la_strategie_retenue": code_retenue == "T4",
                     "regle": "Ne PAS sommer avec net_dirigeant_retenu",
                     "code_strategie_retenue": code_retenue,
                     "texte_alerte_t4_ajoute": texte_alerte_t4_ajoute},
         notes="Convention non-agrégation T4 transversale au comparateur synthèse "
               "(héritée du module TNS via G3b et propagée G3d-bis)")
    _log("ALERTES_SPECIFIQUES_NB",
         "Nombre d'alertes spécifiques attachées (alertes de la stratégie retenue + garde-fou T4 si applicable)",
         float(len(alertes_specifiques)), unite="count",
         hypotheses={"textes_alertes": alertes_specifiques,
                     "alerte_t4_ajoutee_explicitement": texte_alerte_t4_ajoute is not None})

    return ResultatSynthese(
        profil=profil,
        strategie_retenue=code_retenue,
        net_dirigeant_retenu=net_retenu,
        gain_vs_a=gain_vs_ref,  # nommé "vs_a" mais = "vs_T1" pour TNS
        gain_5_ans=gain_5_ans,
        couts_mise_en_oeuvre=[],  # Coûts spécifiques TNS à raffiner en B.3
        total_couts=0.0,
        roi_mois=None,
        scores_radar=scores_radar,
        projection={"gain_5_ans": gain_5_ans, "values": proj_vals},
        decomposition=[],
        enveloppes_compact={},
        checklist=checklist + [{"label": "Alertes régime TNS", "items": alertes_specifiques}],
    )


def _synthese_liberal(profil: Profil,
                      strategies_arbitrage: dict,
                      config_comparateur,
                      code_retenue: Optional[str] = None,
                      forfaits: Optional[dict] = None,
                      alertes_comparateur: Optional[list] = None,
                      *,
                      audit: TraceAudit | None = None) -> ResultatSynthese:
    """
    Synthèse Libéral — stratégies L1-L4.

    GARDE-FOU BNC/SEL : si L3 ou L4 retenue, alerte BNC/SEL systématiquement
    ajoutée dans la checklist. PAS de marqueur "recommandée" mécanique.

    Args:
        audit: Trace d'audit optionnelle (G3e-synthese.4). Codes émis :
            `SYNTH_LIB_*` méta. Pas de sous-trace attachée (implémentation
            allégée v1 — pas d'appel aux fonctions instrumentées G3e-synthese.1-3).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SYNTH_LIB_" + suffixe, label, valeur, **kw)

    if forfaits is None:
        forfaits = FORFAITS_DEFAUT.copy()
    if alertes_comparateur is None:
        alertes_comparateur = []

    def get_net_total(s):
        return s.net_dirigeant_total if hasattr(s, 'net_dirigeant_total') else s["net_dirigeant_total"]

    def get_alertes(s):
        return s.alertes if hasattr(s, 'alertes') else s.get("alertes", [])

    if code_retenue is None:
        code_retenue = max(strategies_arbitrage.keys(),
                           key=lambda c: get_net_total(strategies_arbitrage[c]))

    strat_retenue = strategies_arbitrage[code_retenue]
    net_retenu = get_net_total(strat_retenue)

    # Référence L1 (BNC pur)
    ref_code = "L1" if "L1" in strategies_arbitrage else code_retenue
    net_ref = get_net_total(strategies_arbitrage[ref_code])
    gain_vs_ref = net_retenu - net_ref

    from core.projection import projection_5_ans
    proj_vals = projection_5_ans(net_retenu, fraction_capitalisable=0.5)
    gain_5_ans = proj_vals[4] - net_retenu * 5

    # Alertes du résultat L3/L4 (BNC/SEL + rétention v2 + L4 v2)
    alertes_specifiques = list(get_alertes(strat_retenue))

    checklist = []

    # --- Trace méta SYNTH_LIB_* ---
    _log("REGIME",
         "Régime traité par cette synthèse",
         "Libéral (BNC ou SEL selon stratégie)", unite="",
         hypotheses={"forme_sel_profil": profil.forme_sel,
                     "garde_fou_bnc_sel":
                         "alerte BNC/SEL préservée pour stratégies L3/L4"})
    _log("CODE_PLUS_EFFICACE_FISCALEMENT",
         "Code stratégie au plus haut net_dirigeant_total (depuis arbitrage libéral)",
         code_retenue, unite="",
         hypotheses={"valeurs_attendues": list(strategies_arbitrage.keys()),
                     "convention_defaut": "max(net_dirigeant_total) parmi L1-L4",
                     "terminologie_specifique":
                         "PLUS_EFFICACE_FISCALEMENT (pas RETENU ni MEILLEUR)"})
    _log("NET_DIRIGEANT_RETENU",
         "Net dirigeant total de la stratégie retenue",
         net_retenu, unite="EUR")
    _log("NET_REFERENCE_L1",
         "Net dirigeant total de la stratégie L1 (référence BNC pur)",
         net_ref, unite="EUR",
         hypotheses={"code_reference": ref_code})
    _log("GAIN_VS_L1",
         "Écart net retenue − L1",
         gain_vs_ref, unite="EUR",
         hypotheses={"nomme_dans_resultat": "gain_vs_a (mais = vs_L1 pour Libéral)",
                     "convention": "Indicateur factuel, pas un avis"})
    _log("GAIN_5_ANS",
         "Écart cumulé à 5 ans (depuis projection_5_ans)",
         gain_5_ans, unite="EUR",
         hypotheses={"fraction_capitalisable": 0.5})
    _log("ALERTES_SPECIFIQUES_NB",
         "Nombre d'alertes spécifiques attachées (alertes de la stratégie retenue)",
         float(len(alertes_specifiques)), unite="count",
         hypotheses={"textes_alertes": alertes_specifiques,
                     "code_strategie_concernee": code_retenue,
                     "note_bnc_sel": (
                         "Pour L3/L4 : alerte BNC/SEL héritée du module "
                         "stratégie Libéral (G3c). Pas d'ajout explicite "
                         "à ce niveau, héritage automatique."
                     )},
         notes="Garde-fou BNC/SEL transversal — héritage stratégie sans ajout local")

    return ResultatSynthese(
        profil=profil,
        strategie_retenue=code_retenue,
        net_dirigeant_retenu=net_retenu,
        gain_vs_a=gain_vs_ref,  # nommé "vs_a" mais = "vs_L1" pour Libéral
        gain_5_ans=gain_5_ans,
        couts_mise_en_oeuvre=[],
        total_couts=0.0,
        roi_mois=None,
        scores_radar=[],
        projection={"gain_5_ans": gain_5_ans, "values": proj_vals},
        decomposition=[],
        enveloppes_compact={},
        checklist=checklist + [{"label": "Alertes régime Libéral", "items": alertes_specifiques}],
    )


def _synthese_salarie(profil: Profil,
                      strategies_arbitrage,  # ignoré pour le Salarié
                      config_comparateur,
                      code_retenue: Optional[str] = None,
                      forfaits: Optional[dict] = None,
                      alertes_comparateur: Optional[list] = None,
                      *,
                      audit: TraceAudit | None = None) -> ResultatSynthese:
    """
    Synthèse Salarié (référence simple, Option A).

    Le Salarié non-dirigeant n'a pas de Strategy Engine. Sa Synthèse présente
    le net du module détaillé comme valeur de référence, sans matrice de
    stratégies. Sert essentiellement de comparaison dans le Comparateur de
    régimes.

    Args:
        audit: Trace d'audit optionnelle (G3e-synthese.4). Codes émis :
            `SYNTH_SAL_*` méta. Attache une sous-trace `module_salarie`
            (seul appel à un module instrumenté G2a).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SYNTH_SAL_" + suffixe, label, valeur, **kw)

    from regime.salarie import calcul_module_salarie

    # --- Appel module_salarie avec sous-trace composée ---
    if audit is not None:
        st_salarie = TraceAudit(
            regime="Salarié (appel depuis synthèse, référence)",
            profil_resume=f"salaire_brut_assimile={profil.salaire_brut_assimile:.0f}",
        )
        res_salarie = calcul_module_salarie(profil,
                                            salaire_brut=profil.salaire_brut_assimile,
                                            audit=st_salarie)
        audit.attacher_sous_trace("module_salarie", st_salarie)
    else:
        res_salarie = calcul_module_salarie(profil,
                                            salaire_brut=profil.salaire_brut_assimile)
    net = res_salarie.net_apres_impots

    from core.projection import projection_5_ans
    proj_vals = projection_5_ans(net, fraction_capitalisable=0.5)
    gain_5_ans = proj_vals[4] - net * 5

    # --- Trace méta SYNTH_SAL_* ---
    _log("REGIME",
         "Régime traité par cette synthèse",
         "Salarié (référence)", unite="")
    _log("CODE_STRATEGIE",
         "Code stratégie (sans objet — pas de Strategy Engine appliqué au Salarié)",
         "Salarié (référence)", unite="",
         hypotheses={"justification": "Le salarié non dirigeant n'a pas d'enveloppe à arbitrer",
                     "convention": "Pas de Strategy Engine — module détaillé directement"})
    _log("NET_APRES_IMPOTS",
         "Net après impôts du module Salarié (valeur de référence)",
         net, unite="EUR",
         notes="Détails dans sous-trace 'module_salarie'")
    _log("GAIN_VS_REFERENCE",
         "Écart vs référence (sans objet — pas de stratégie comparative)",
         0.0, unite="EUR",
         hypotheses={"convention": "gain_vs_a = 0 par convention (pas de Strategy Engine)"})
    _log("GAIN_5_ANS",
         "Écart cumulé à 5 ans (depuis projection_5_ans)",
         gain_5_ans, unite="EUR",
         hypotheses={"fraction_capitalisable": 0.5})

    return ResultatSynthese(
        profil=profil,
        strategie_retenue="Salarié (référence)",
        net_dirigeant_retenu=net,
        gain_vs_a=0.0,
        gain_5_ans=gain_5_ans,
        couts_mise_en_oeuvre=[],
        total_couts=0.0,
        roi_mois=None,
        scores_radar=[],
        projection={"gain_5_ans": gain_5_ans, "values": proj_vals},
        decomposition=[],
        enveloppes_compact={},
        checklist=[{"label": "Régime Salarié", "items": [
            "Référence salariale : net après IR pour le salaire brut saisi. "
            "Pas de Strategy Engine appliqué (le Salarié n'a pas d'enveloppe dirigeant à arbitrer)."
        ]}],
    )
