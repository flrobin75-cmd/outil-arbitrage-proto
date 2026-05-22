"""
test_pdf_audit_render_liberal.py — Test PDF audit-ready, régime Libéral.

SP7 — extension du périmètre v1.0.0 au régime Libéral
(`strategy/liberal.py::arbitrage_complet_liberal`).

Ce test couvre **les deux branches dynamiques** du Libéral :
- **SELARL** (gérant majoritaire TNS sur la SEL) → module_tns en N3
- **SELAS**  (président Assimilé sur la SEL)    → module_salarie en N3

Le Libéral est le plus complexe des 3 régimes du périmètre v1 :
- profondeur effective 3 (strategie_L4 → strategie_l3_deleguee → module_TX)
- code le plus long du dépôt (`STRAT_LIB_L4_ALERTE_STRUCTURATION_V2_NB`,
  39 chars) → test de robustesse du calibrage dynamique SP7
- 11 hypothèses longues (≥ 80 chars) issues des alertes BNC/SEL et v19
- branche dynamique L3/L4 selon forme_sel → 2 traces structurellement
  différentes à traiter par le même renderer

Comme pour Assimilé, le test fait deux choses :

1. **Helper commun** — assertions transverses (neutralité structurelle).
2. **Spécifique Libéral** — propriétés attendues du graphe Libéral.

Usage : python3 test_pdf_audit_render_liberal.py
Exit code 0 si tous les contrôles passent.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from core.audit import TraceAudit
from core.profil import Profil
from strategy.liberal import arbitrage_complet_liberal

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


def construire_trace_liberal(forme_sel: str) -> TraceAudit:
    """Construit une trace Libéral pour une forme SEL donnée.

    Args:
        forme_sel: "SELARL" (gérant majoritaire TNS sur SEL) ou
            "SELAS" (président Assimilé sur SEL).
    """
    profil = Profil(forme_sel=forme_sel)
    trace = TraceAudit(
        regime=f"Libéral {forme_sel}",
        profil_resume=f"Profil Libéral ({forme_sel})",
    )
    arbitrage_complet_liberal(profil, audit=trace)
    return trace


def tester_une_forme(forme_sel: str) -> tuple:
    """Lance toutes les assertions pour une forme SEL donnée.

    Returns:
        Tuple (nb_ok, nb_ko, failures) pour agrégation en sortie.
    """
    print()
    print("─" * 95)
    print(f"  BRANCHE : {forme_sel}")
    print("─" * 95)

    trace = construire_trace_liberal(forme_sel)
    pdf_bytes = generer_pdf_audit(
        trace,
        cabinet_nom="Cabinet TestCo",
        client_nom="M. Dupont",
        expert_comptable="Mme Martin",
    )

    chemin = PDF_OUT_DIR / f"sp7_audit_liberal_{forme_sel.lower()}.pdf"
    chemin.write_bytes(pdf_bytes)
    print()
    print(f"  Trace pilote          : {trace.regime}")
    print(f"  Étapes racine         : {len(trace.racines())}")
    print(f"  Sous-traces N1        : {list(trace.noms_sous_traces())}")
    print(f"  PDF sauvegardé        : {chemin}")
    print(f"  Taille PDF            : {len(pdf_bytes)} bytes")

    cas = faire_cas_test(trace, pdf_bytes,
                         regime_attendu=f"Libéral {forme_sel}")
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

    # === SECTIONS SPÉCIFIQUES LIBÉRAL ===
    runner.section(f"Spécifique Libéral {forme_sel} : structure de la trace")

    noms_n1 = list(trace.noms_sous_traces())
    for s in ("strategie_L1", "strategie_L2", "strategie_L3", "strategie_L4"):
        runner.check(
            f"Stratégie '{s}' présente dans la trace",
            s in noms_n1,
            detail=f"observé: {noms_n1}" if s not in noms_n1 else "",
        )

    # L1 et L2 contiennent module_bnc
    for nom_strat in ("strategie_L1", "strategie_L2"):
        sub = trace.get_sous_trace(nom_strat)
        runner.check(
            f"{nom_strat} contient sous-trace 'module_bnc'",
            "module_bnc" in sub.noms_sous_traces(),
            detail=f"observé: {sub.noms_sous_traces()}",
        )

    # L3 contient module_tns (SELARL) ou module_salarie (SELAS)
    sub_l3 = trace.get_sous_trace("strategie_L3")
    module_l3_attendu = "module_tns" if forme_sel == "SELARL" else "module_salarie"
    runner.check(
        f"strategie_L3 ({forme_sel}) contient sous-trace '{module_l3_attendu}'",
        module_l3_attendu in sub_l3.noms_sous_traces(),
        detail=f"observé: {sub_l3.noms_sous_traces()}",
    )

    # L4 contient strategie_l3_deleguee (profondeur 3 dans le graphe global)
    sub_l4 = trace.get_sous_trace("strategie_L4")
    runner.check(
        "strategie_L4 contient sous-trace 'strategie_l3_deleguee' (profondeur 3)",
        "strategie_l3_deleguee" in sub_l4.noms_sous_traces(),
        detail=f"observé: {sub_l4.noms_sous_traces()}",
    )

    # Profondeur effective : strategie_l3_deleguee a son propre module en N3
    sub_l3_deleguee = sub_l4.get_sous_trace("strategie_l3_deleguee")
    if sub_l3_deleguee is not None:
        runner.check(
            f"strategie_l3_deleguee contient le module '{module_l3_attendu}' (profondeur 3)",
            module_l3_attendu in sub_l3_deleguee.noms_sous_traces(),
            detail=f"observé: {sub_l3_deleguee.noms_sous_traces()}",
        )

    # Code spécifique Libéral L4 (le plus long, 39 chars) : rendu intact
    code_long = "STRAT_LIB_L4_ALERTE_STRUCTURATION_V2_NB"
    runner.check(
        f"Code Libéral 39 chars '{code_long}' rendu intact (calibrage SP7)",
        code_long in cas.texte,
        detail="code non trouvé — possible wrap" if code_long not in cas.texte else "",
    )

    # Au moins 1 hypothèse longue rendue en encadré
    runner.check(
        "En-tête 'Hypothèses longues développées' présent au moins une fois",
        "Hypothèses longues développées" in cas.texte_norm,
    )

    return (runner.nb_ok, runner.nb_ko, runner.failures)


def main() -> int:
    print()
    print("=" * 95)
    print("  TEST PDF audit-ready — Régime Libéral (SELARL + SELAS) — SP7")
    print("=" * 95)

    nb_ok_total = 0
    nb_ko_total = 0
    failures_total: list = []

    for forme in ("SELARL", "SELAS"):
        nb_ok, nb_ko, failures = tester_une_forme(forme)
        nb_ok_total += nb_ok
        nb_ko_total += nb_ko
        failures_total += [f"[{forme}] {f}" for f in failures]

    print()
    print("=" * 95)
    print("  SYNTHÈSE GLOBALE — Libéral (SELARL + SELAS)")
    print("=" * 95)
    print(f"  Contrôles OK     : {nb_ok_total}")
    print(f"  Contrôles KO     : {nb_ko_total}")
    print()

    if nb_ko_total == 0:
        print("  ✓ SP7 Libéral PASS — les 2 branches SELARL et SELAS conformes")
        return 0
    else:
        print("  ✗ SP7 Libéral FAIL :")
        for f in failures_total:
            print(f"    - {f}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
