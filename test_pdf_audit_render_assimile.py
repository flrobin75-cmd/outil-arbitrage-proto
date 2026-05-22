"""
test_pdf_audit_render_assimile.py — Test PDF audit-ready, régime Assimilé.

SP7 — extension du périmètre v1.0.0 au régime Assimilé
(`strategy/assimile.py::arbitrage_complet`).

Ce test fait deux choses :

1. **Appelle les assertions communes** du helper `test_pdf_audit_render_common`,
   qui actent la neutralité structurelle du renderer (le même PDF doit
   honorer les mêmes contrats indépendamment du régime).

2. **Vérifie des propriétés spécifiques Assimilé** :
   - Présence d'une sous-trace `tx_ir_moy` (helper de calcul intercalé)
   - 4 sous-traces stratégies (`strategie_A` à `strategie_D`)
   - Graphe plat (profondeur 1, pas de sous-sous-traces)
   - Codes namespace `STRAT_ASSIM_*` rendus correctement
   - Profil : SAS / Assimilé par défaut

Le pilote TNS de référence reste figé dans `test_pdf_audit_render_tns.py`.
Ce test ne remet pas en cause cette baseline ; il complète la couverture.

Usage : python3 test_pdf_audit_render_assimile.py
Exit code 0 si tous les contrôles passent.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from core.audit import TraceAudit
from core.profil import Profil
from strategy.assimile import arbitrage_complet

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


def construire_trace_assimile() -> TraceAudit:
    """Construit la trace Assimilé de référence pour les tests SP7.

    Profil par défaut = SAS, IS 200k. Cf. test_mode_audit_assimile.py
    pour la même convention.
    """
    profil = Profil()  # SAS par défaut
    trace = TraceAudit(
        regime="Assimilé",
        profil_resume="Profil par défaut (SAS, marié 2p, IS 200k)",
    )
    arbitrage_complet(profil, audit=trace)
    return trace


def main() -> int:
    print()
    print("=" * 95)
    print("  TEST PDF audit-ready — Régime Assimilé (SP7)")
    print("=" * 95)

    # Construction trace + PDF
    trace = construire_trace_assimile()
    pdf_bytes = generer_pdf_audit(
        trace,
        cabinet_nom="Cabinet TestCo",
        client_nom="M. Dupont",
        expert_comptable="Mme Martin",
    )

    # Sauvegarde
    chemin = PDF_OUT_DIR / "sp7_audit_assimile.pdf"
    chemin.write_bytes(pdf_bytes)
    print()
    print(f"  Trace pilote          : {trace.regime}")
    print(f"  Étapes racine         : {len(trace.racines())}")
    print(f"  Sous-traces N1        : {list(trace.noms_sous_traces())}")
    print(f"  PDF sauvegardé        : {chemin}")
    print(f"  Taille PDF            : {len(pdf_bytes)} bytes")

    # Construction CasTest commun
    cas = faire_cas_test(trace, pdf_bytes, regime_attendu="Assimilé")
    runner = AssertionRunner()

    # === SECTIONS COMMUNES (helper, neutres) ===
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

    # === SECTIONS SPÉCIFIQUES ASSIMILÉ ===
    # Ces assertions sont régime-spécifiques. Elles ne vont PAS dans le
    # helper commun parce qu'elles présument du contenu de la trace
    # Assimilé (pas de la structure du renderer).
    runner.section("Spécifique Assimilé : structure de la trace")

    # Helper tx_ir_moy attendu (sous-trace utilitaire de calcul intercalé)
    noms_n1 = list(trace.noms_sous_traces())
    runner.check(
        "Sous-trace 'tx_ir_moy' présente (helper de calcul intercalé)",
        "tx_ir_moy" in noms_n1,
        detail=f"observé: {noms_n1}",
    )
    # 4 stratégies A/B/C/D
    for s in ("strategie_A", "strategie_B", "strategie_C", "strategie_D"):
        runner.check(
            f"Stratégie '{s}' présente dans la trace",
            s in noms_n1,
            detail=f"observé: {noms_n1}" if s not in noms_n1 else "",
        )

    # Profondeur 1 attendue (graphe plat — aucune sous-sous-trace)
    sous_traces_n2 = sum(
        len(trace.get_sous_trace(n).noms_sous_traces())
        for n in noms_n1
    )
    runner.check(
        "Graphe plat (profondeur 1, 0 sous-sous-traces)",
        sous_traces_n2 == 0,
        detail=f"observé: {sous_traces_n2} sous-sous-traces",
    )

    # Au moins 1 code STRAT_ASSIM_* présent dans le PDF
    runner.check(
        "Codes namespace 'STRAT_ASSIM_*' rendus dans le PDF",
        "STRAT_ASSIM_" in cas.texte,
    )

    # Synthèse
    return runner.synthese("SP7 Assimilé")


if __name__ == "__main__":
    sys.exit(main())
