"""
test_pdf_audit_render_receptacles.py — Test PDF audit-ready, module Réceptacles.

SP19 (clôture v1.1.0) — extension du périmètre v1.0.1 au module
Réceptacles (`strategy/receptacles_orchestrateur.py::allocation_receptacles`).

Ce test fait deux choses :

1. **Appelle les assertions communes** du helper `test_pdf_audit_render_common`,
   qui actent la neutralité structurelle du renderer (le même PDF doit
   honorer les mêmes contrats indépendamment de la trace source).

2. **Vérifie des propriétés spécifiques Réceptacles** :
   - Présence des 3 sous-traces enveloppes au niveau N1 dans l'ordre
     stable PERIN → PEE → PERECO (`ligne_perin`, `ligne_pee`, `ligne_pereco`)
   - Présence des sous-traces N2 par horizon dans chaque enveloppe
     (`horizon_5ans`, `horizon_10ans`, `horizon_20ans`)
   - Présence des 9 codes RECAP au niveau racine
   - Codes namespace `REC_*` rendus correctement dans le PDF
   - Ordre stable PERIN → PEE → PERECO matérialisé dans le PDF
   - Aucun mot interdit (score, ranking, optimal, etc.) dans le PDF
     (garde-fou SP18)

Le pilote TNS de référence reste figé dans `test_pdf_audit_render_tns.py`.
Ce test ne remet pas en cause cette baseline ; il complète la couverture
v1.1.0 (modules métier Réceptacles SP15-SP18).

Cas de référence (Q1=a, 1 cas standard) :
  - Profil par défaut
  - Flux disponible 5 000 €
  - Horizons par défaut (5, 10, 20 ans)
  - 3 modules réels (PERIN/PEE/PERECO) + orchestrateur SP18

Usage : python3 test_pdf_audit_render_receptacles.py
Exit code 0 si tous les contrôles passent.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from core.audit import TraceAudit
from core.profil import Profil
from strategy.receptacles_orchestrateur import allocation_receptacles

from ui.pdf_audit_export import generer_pdf_audit
from test_pdf_audit_render_common import (
    AssertionRunner, faire_cas_test,
    section_pdf_valide, section_couverture,
    section_kpis_couverture, section_bandeau_intro_sommaire,
    section_sommaire_pagine, section_signets_hierarchises,
    section_no_declaratif, section_14_patterns_non_prescriptifs,
    section_neutralite_structurelle, section_calibrage_dynamique,
)

PDF_OUT_DIR = Path("/tmp/pdf_audit_test_outputs")
PDF_OUT_DIR.mkdir(parents=True, exist_ok=True)


def construire_trace_receptacles() -> TraceAudit:
    """Construit la trace orchestrateur Réceptacles de référence pour SP19.

    Cas standard cohérent avec le mini-golden orchestrateur SP18
    (`composition_5000`) :
      - Profil par défaut (SAS, marié 2p, IS 200k)
      - Flux disponible 5 000 €
      - Horizons par défaut (5, 10, 20 ans)
      - 3 modules réels PERIN/PEE/PERECO + étapes méta orchestrateur SP18

    Volumétrie attendue :
      - ~109 étapes au niveau racine (5 méta + 9 RECAP + lignes
        de chaque module via instrumentation interne)
      - 12 sous-traces (3 enveloppes N1 + 9 horizons N2)
      - ~168 hypothèses
    """
    profil = Profil()  # SAS par défaut
    trace = TraceAudit(
        regime="Réceptacles",
        profil_resume=(
            "Profil par défaut (SAS), flux 5 000 €, horizons (5, 10, 20)"
        ),
    )
    allocation_receptacles(
        profil,
        flux_disponible=5000.0,
        horizons=(5, 10, 20),
        audit=trace,
    )
    return trace


def main() -> int:
    print()
    print("=" * 95)
    print("  TEST PDF audit-ready — Module Réceptacles (SP19, clôture v1.1.0)")
    print("=" * 95)

    # Construction trace + PDF
    trace = construire_trace_receptacles()
    pdf_bytes = generer_pdf_audit(
        trace,
        cabinet_nom="Cabinet TestCo",
        client_nom="M. Dupont",
        expert_comptable="Mme Martin",
    )

    # Sauvegarde pour inspection
    pdf_path = PDF_OUT_DIR / "test_receptacles.pdf"
    pdf_path.write_bytes(pdf_bytes)
    print(f"  PDF généré : {pdf_path} ({len(pdf_bytes)} bytes)")

    # Cas de test commun
    cas = faire_cas_test(
        trace=trace,
        pdf_bytes=pdf_bytes,
        regime_attendu="Réceptacles",
    )

    runner = AssertionRunner()

    # === SECTIONS COMMUNES (helper SP7) ===
    section_pdf_valide(runner, cas)
    section_couverture(runner, cas)
    section_kpis_couverture(runner, cas)
    section_bandeau_intro_sommaire(runner, cas)
    section_sommaire_pagine(runner, cas)
    section_signets_hierarchises(runner, cas)
    section_no_declaratif(runner, cas)
    section_14_patterns_non_prescriptifs(runner, cas)
    section_neutralite_structurelle(runner, cas)
    section_calibrage_dynamique(runner, cas)

    # === SECTIONS SPÉCIFIQUES RÉCEPTACLES ===
    # Ces assertions sont module-spécifiques. Elles ne vont PAS dans le
    # helper commun (qui doit rester neutre vis-à-vis du module source).

    # ────────────────────────────────────────────────────────────
    # Section Récep-1 : Structure de la trace réceptacles
    # ────────────────────────────────────────────────────────────
    runner.section("Spécifique Réceptacles : structure de la trace")

    # Les 4 sous-traces enveloppes au niveau N1 dans l'ordre stable (SP25 : ajout PERO)
    noms_n1 = list(trace.noms_sous_traces())
    runner.check(
        "Récep-1.1 4 sous-traces enveloppes au niveau N1 (SP25 : PERO ajoutée)",
        len(noms_n1) == 4,
        detail=f"observé: {len(noms_n1)} — {noms_n1}",
    )
    ordre_attendu_n1 = ["ligne_perin", "ligne_pee", "ligne_pereco", "ligne_pero"]
    runner.check(
        "Récep-1.2 Ordre stable PERIN → PEE → PERECO → PERO dans les sous-traces N1 "
        "(contrainte SP18 étendue SP25)",
        noms_n1 == ordre_attendu_n1,
        detail=f"attendu: {ordre_attendu_n1}, observé: {noms_n1}",
    )

    # Chaque enveloppe a 3 sous-traces N2 (horizons)
    for nom_env in ordre_attendu_n1:
        sub = trace.get_sous_trace(nom_env)
        noms_n2 = list(sub.noms_sous_traces())
        runner.check(
            f"Récep-1.3 Enveloppe {nom_env} : 3 sous-traces horizons "
            f"(profondeur 2)",
            len(noms_n2) == 3,
            detail=f"observé: {noms_n2}",
        )
        ordre_attendu_n2 = ["horizon_5ans", "horizon_10ans", "horizon_20ans"]
        runner.check(
            f"Récep-1.4 {nom_env} : ordre horizons stable 5/10/20 ans",
            noms_n2 == ordre_attendu_n2,
            detail=f"attendu: {ordre_attendu_n2}, observé: {noms_n2}",
        )

    # 16 sous-traces totales (4 N1 + 4 × 3 N2) depuis SP25
    total_sous_traces = len(noms_n1) + sum(
        len(trace.get_sous_trace(n).noms_sous_traces())
        for n in noms_n1
    )
    runner.check(
        "Récep-1.5 16 sous-traces totales (4 N1 enveloppes + 12 N2 horizons, SP25)",
        total_sous_traces == 16,
        detail=f"observé: {total_sous_traces}",
    )

    # ────────────────────────────────────────────────────────────
    # Section Récep-2 : Étapes méta SP14 + RECAP SP18
    # ────────────────────────────────────────────────────────────
    runner.section("Spécifique Réceptacles : étapes méta racine "
                   "(scaffolding SP14 + RECAP SP18)")

    codes_racine = {e.code for e in trace.etapes}

    # 5 étapes méta SP14
    codes_meta_attendus = {
        "REC_NB_ENVELOPPES", "REC_FLUX_DISPONIBLE",
        "REC_HORIZONS_NB", "REC_RENDEMENT_HYPOTHESE",
        "REC_DISCLAIMERS_NB",
    }
    manquants_meta = codes_meta_attendus - codes_racine
    runner.check(
        "Récep-2.1 5 codes méta SP14 présents à la racine "
        "(REC_NB_ENVELOPPES, REC_FLUX_DISPONIBLE, REC_HORIZONS_NB, "
        "REC_RENDEMENT_HYPOTHESE, REC_DISCLAIMERS_NB)",
        not manquants_meta,
        detail=f"manquants: {manquants_meta}",
    )

    # 9 codes RECAP SP18 (3 dimensions × 3 horizons)
    codes_recap_attendus = {
        f"REC_RECAP_{dim}_{h}ANS"
        for dim in ["VALEUR_NETTE", "EFFORT_REEL", "COUT_ENTREPRISE"]
        for h in [5, 10, 20]
    }
    manquants_recap = codes_recap_attendus - codes_racine
    runner.check(
        "Récep-2.2 9 codes RECAP SP18 présents à la racine "
        "(3 dimensions × 3 horizons)",
        not manquants_recap,
        detail=f"manquants: {manquants_recap}",
    )

    # Tous les codes RECAP ont valeur scalaire = 3 (garde-fou SP18 :
    # valeur neutre, pas une métrique économique)
    etapes_recap = [e for e in trace.etapes if e.code.startswith("REC_RECAP_")]
    erreurs_valeur = [e.code for e in etapes_recap if e.valeur != 4]
    runner.check(
        "Récep-2.3 Toutes les étapes RECAP ont valeur scalaire = 4 "
        "(garde-fou SP18 étendu SP25 : valeur neutre, pas une métrique)",
        not erreurs_valeur,
        detail=f"étapes non conformes: {erreurs_valeur}",
    )

    # ────────────────────────────────────────────────────────────
    # Section Récep-3 : Codes namespace REC_<ENV>_* rendus dans le PDF
    # ────────────────────────────────────────────────────────────
    runner.section("Spécifique Réceptacles : codes namespace rendus dans le PDF")

    # PERIN
    runner.check(
        "Récep-3.1 Codes namespace 'REC_PERIN_*' rendus dans le PDF",
        "REC_PERIN_" in cas.texte,
    )
    # PEE
    runner.check(
        "Récep-3.2 Codes namespace 'REC_PEE_*' rendus dans le PDF",
        "REC_PEE_" in cas.texte,
    )
    # PERECO
    runner.check(
        "Récep-3.3 Codes namespace 'REC_PERECO_*' rendus dans le PDF",
        "REC_PERECO_" in cas.texte,
    )
    # Méta
    runner.check(
        "Récep-3.4 Codes méta 'REC_NB_ENVELOPPES' / 'REC_FLUX_DISPONIBLE' "
        "rendus dans le PDF",
        "REC_NB_ENVELOPPES" in cas.texte
        and "REC_FLUX_DISPONIBLE" in cas.texte,
    )
    # RECAP SP18
    runner.check(
        "Récep-3.5 Codes RECAP 'REC_RECAP_VALEUR_NETTE_5ANS' présents dans le PDF",
        "REC_RECAP_VALEUR_NETTE_5ANS" in cas.texte,
    )

    # ────────────────────────────────────────────────────────────
    # Section Récep-4 : Ordre stable PERIN → PEE → PERECO dans le PDF
    # ────────────────────────────────────────────────────────────
    runner.section("Spécifique Réceptacles : ordre stable PERIN → PEE → PERECO "
                   "dans le PDF rendu (contrainte SP18)")

    # Position de la 1ère occurrence de chaque enveloppe dans le texte PDF
    # (signets) : doit être PERIN < PEE < PERECO
    pos_perin = cas.texte.find("REC_PERIN_")
    pos_pee = cas.texte.find("REC_PEE_")
    pos_pereco = cas.texte.find("REC_PERECO_")
    runner.check(
        "Récep-4.1 Ordre PERIN < PEE < PERECO dans le PDF "
        "(1ère occurrence des namespaces)",
        pos_perin >= 0 and pos_pee >= 0 and pos_pereco >= 0
        and pos_perin < pos_pee < pos_pereco,
        detail=f"positions: PERIN={pos_perin}, PEE={pos_pee}, "
               f"PERECO={pos_pereco}",
    )

    # Dans les étapes RECAP, l'ordre des clés enveloppes dans les
    # hypothèses doit être PERIN → PEE → PERECO (lecture trace
    # directement, pas via texte PDF normalisé)
    erreurs_ordre_recap = []
    for etape in etapes_recap:
        cles_envs = [
            k for k in etape.hypotheses.keys()
            if any(env in k for env in ["PERIN", "PEE", "PERECO"])
        ]
        idx_perin = next(
            (i for i, k in enumerate(cles_envs) if "PERIN" in k), -1
        )
        idx_pee = next(
            (i for i, k in enumerate(cles_envs)
             if "_PEE" in k and "PERECO" not in k), -1
        )
        idx_pereco = next(
            (i for i, k in enumerate(cles_envs) if "PERECO" in k), -1
        )
        if not (idx_perin < idx_pee < idx_pereco):
            erreurs_ordre_recap.append((etape.code, cles_envs))
    runner.check(
        "Récep-4.2 Ordre PERIN → PEE → PERECO préservé dans toutes "
        "les hypothèses RECAP (trace directe, garde-fou SP18)",
        not erreurs_ordre_recap,
        detail=f"erreurs: {erreurs_ordre_recap[:2]}",
    )

    # ────────────────────────────────────────────────────────────
    # Section Récep-5 : Hypothèses doctrinales rendues (wordings)
    # ────────────────────────────────────────────────────────────
    runner.section("Spécifique Réceptacles : wordings doctrinaux rendus")

    # Disclaimer comparabilité (transverse v1.1) doit apparaître
    runner.check(
        "Récep-5.1 Disclaimer comparabilité présent (mention "
        "« 3 enveloppes comparées »)",
        "3 enveloppes comparées" in cas.texte
        or "3 enveloppes" in cas.texte,
    )

    # Convention rendement 2 % conventionnel mentionnée
    runner.check(
        "Récep-5.2 Convention de rendement mentionnée dans le PDF",
        "rendement" in cas.texte.lower()
        or "capitalisation" in cas.texte.lower(),
    )

    # Wording PERIN sur déductibilité IR rendu
    runner.check(
        "Récep-5.3 Wording PERIN sur déductibilité IR rendu",
        "déductible" in cas.texte.lower()
        and "PERIN" in cas.texte,
    )

    # Wording PEE sur abondement employeur rendu
    runner.check(
        "Récep-5.4 Wording PEE sur abondement employeur rendu",
        "abondement" in cas.texte.lower()
        and "PEE" in cas.texte,
    )

    # Wording PERECO sur disponibilité retraite rendu
    runner.check(
        "Récep-5.5 Wording PERECO sur disponibilité retraite rendu",
        "retraite" in cas.texte.lower()
        and "PERECO" in cas.texte,
    )

    # ────────────────────────────────────────────────────────────
    # Section Récep-6 : Garde-fous SP18 (aucun mot interdit en sortie)
    # ────────────────────────────────────────────────────────────
    runner.section("Spécifique Réceptacles : garde-fous SP18 "
                   "(aucun mot interdit dans le PDF)")

    # Le PDF complet ne doit contenir aucun mot interdit qui sortirait
    # de la trace orchestrateur. Note : on teste sur le texte PDF
    # normalisé (cas.texte), ce qui couvre labels + hypothèses rendus.
    mots_interdits_sp18 = [
        ("score", "score"),
        ("ranking", "ranking"),
        ("optimal", "optimal"),
        ("recommandation", "recommandation"),
        ("préconisation", "préconisation"),
        ("efficacité", "efficacité"),
        # « performance » est trop générique (peut apparaître dans
        # un wording légitime hors module réceptacles) ; on teste
        # spécifiquement les patterns enveloppe.
    ]
    erreurs_mots = []
    texte_lower = cas.texte.lower()
    for mot, label in mots_interdits_sp18:
        if mot in texte_lower:
            # Vérifier que le mot apparaît dans un contexte réceptacles
            # (codes REC_*) — sinon c'est un faux positif du framework
            # historique. On cherche une fenêtre de 200 caractères
            # autour de chaque occurrence.
            import re as _re
            for match in _re.finditer(_re.escape(mot), texte_lower):
                debut = max(0, match.start() - 200)
                fin = min(len(texte_lower), match.end() + 200)
                fenetre = texte_lower[debut:fin]
                if "rec_" in fenetre:  # contexte réceptacles
                    erreurs_mots.append((mot, fenetre[:80]))
                    break
    runner.check(
        "Récep-6.1 Aucun mot interdit (score/ranking/optimal/"
        "recommandation/préconisation/efficacité) dans le contexte "
        "réceptacles du PDF (garde-fou SP18)",
        not erreurs_mots,
        detail=f"erreurs: {erreurs_mots[:2]}",
    )

    # ────────────────────────────────────────────────────────────
    # Section Récep-7 : Profondeur graphe = 2 (spécifique Réceptacles)
    # ────────────────────────────────────────────────────────────
    runner.section("Spécifique Réceptacles : profondeur du graphe = 2")

    # Le pilote TNS a profondeur 2 (strategie_T* → module_tns).
    # L'Assimilé a profondeur 1 (graphe plat).
    # Le Comparateur a profondeur 2 (régime → stratégie).
    # Réceptacles a profondeur 2 (enveloppe → horizon).
    #
    # On vérifie qu'aucune sous-trace N2 n'a elle-même de sous-trace
    # (pas de profondeur 3).
    erreurs_profondeur = []
    for nom_env in noms_n1:
        sub_env = trace.get_sous_trace(nom_env)
        for nom_h in sub_env.noms_sous_traces():
            sub_h = sub_env.get_sous_trace(nom_h)
            if len(sub_h.noms_sous_traces()) > 0:
                erreurs_profondeur.append(
                    (nom_env, nom_h, list(sub_h.noms_sous_traces()))
                )
    runner.check(
        "Récep-7.1 Profondeur graphe = 2 (aucune sous-trace N2 n'a "
        "elle-même de sous-trace)",
        not erreurs_profondeur,
        detail=f"erreurs: {erreurs_profondeur[:2]}",
    )

    # Synthèse
    return runner.synthese("SP19 Réceptacles")


if __name__ == "__main__":
    sys.exit(main())
