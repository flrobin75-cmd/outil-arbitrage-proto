"""
test_pdf_audit_render_comparateur_regimes.py — PDF audit-ready, comparateur multi-régimes.

SP8 — extension du périmètre v1.0.0 au comparateur multi-régimes
(`strategy/comparateur_regimes.py::calcul_comparateur_regimes`).

Ce test est le **test final de robustesse architecturelle** du renderer :

- **Profondeur effective 5** dans le graphe d'audit (la plus profonde
  du dépôt MODE_AUDIT v1.6).
- **~412 étapes tracées** sur l'ensemble du graphe (vs 156 pour TNS
  isolé, 70 pour Assimilé, 136 pour Libéral SELARL).
- **30 sous-traces totales**, 4 lignes_régimes en parallèle
  (`ligne_assimile`, `ligne_tns`, `ligne_liberal`, `ligne_salarie`),
  chacune avec son propre sous-arbre.
- **Code le plus long du dépôt** : `COMP_REG_LIB_CODE_STRATEGIE_PLUS_EFFICACE`
  (41 chars) — teste les limites du calibrage dynamique SP7.

Si le renderer tient ici, il tient pour toute trace future construite
sur la même grammaire `core/audit.py` spec 1.1.0.

Ce test fait deux choses (pattern Q4-(a) SP7 reconduit) :

1. **Helper commun** — 10 sections d'assertions transverses
   (`test_pdf_audit_render_common.py`).

2. **Spécifique comparateur** — propriétés attendues :
   - 4 lignes_régime au niveau N1
   - Récursion à profondeur 5 absorbée
   - Code 41 chars rendu intact (calibrage SP7)
   - Codes namespace `COMP_REG_*` rendus
   - Codes des sous-régimes (`STRAT_TNS_*`, `STRAT_LIB_*`, `STRAT_ASSIM_*`,
     `SAL_*`) tous rendus identiquement à leurs tests isolés
     (preuve forte de neutralité — le contexte d'appel ne change rien)
   - Sommaire tient sur 1 page (correction SP8 du défaut D8.1)

Le pilote TNS de référence reste figé dans `test_pdf_audit_render_tns.py`.
Ce test ne remet pas en cause cette baseline ; il finalise la couverture
PDF audit-ready v1.0.0 sur l'ensemble du périmètre stratégies du dépôt.

Usage : python3 test_pdf_audit_render_comparateur_regimes.py
Exit code 0 si tous les contrôles passent.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import pdfplumber

from core.audit import TraceAudit
from core.profil import Profil
from strategy.comparateur_regimes import calcul_comparateur_regimes

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


def construire_trace_comparateur() -> TraceAudit:
    """Construit la trace comparateur_regimes de référence pour SP8.

    Profil par défaut = SAS, IS 200k, marié 2p. Cf.
    test_mode_audit_strategy_comparateur_regimes.py pour la même
    convention.
    """
    profil = Profil()
    trace = TraceAudit(
        regime="Comparateur Régimes",
        profil_resume="Profil par défaut (SAS, marié 2p, IS 200k)",
    )
    calcul_comparateur_regimes(profil, audit=trace)
    return trace


def _profondeur_max(trace: TraceAudit, niveau: int = 0) -> int:
    """Profondeur effective du graphe (récursif sans présomption)."""
    noms = list(trace.noms_sous_traces())
    if not noms:
        return niveau
    return max(
        _profondeur_max(trace.get_sous_trace(n), niveau + 1)
        for n in noms
    )


def main() -> int:
    print()
    print("=" * 95)
    print("  TEST PDF audit-ready — Comparateur Régimes (SP8)")
    print("=" * 95)

    # Construction trace + PDF
    trace = construire_trace_comparateur()
    pdf_bytes = generer_pdf_audit(
        trace,
        cabinet_nom="Cabinet TestCo",
        client_nom="M. Dupont",
        expert_comptable="Mme Martin",
    )

    # Sauvegarde
    chemin = PDF_OUT_DIR / "sp8_audit_comparateur_regimes.pdf"
    chemin.write_bytes(pdf_bytes)

    # Inventaire structure
    profondeur = _profondeur_max(trace)
    print()
    print(f"  Trace pilote          : {trace.regime}")
    print(f"  Étapes racine         : {len(trace.racines())}")
    print(f"  Sous-traces N1        : {list(trace.noms_sous_traces())}")
    print(f"  Profondeur effective  : {profondeur} niveaux")
    print(f"  PDF sauvegardé        : {chemin}")
    print(f"  Taille PDF            : {len(pdf_bytes)} bytes")

    # Construction CasTest commun
    cas = faire_cas_test(trace, pdf_bytes,
                         regime_attendu="Comparateur Régimes")
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

    # === SECTIONS SPÉCIFIQUES COMPARATEUR ===
    runner.section("Spécifique Comparateur : structure 4 régimes en parallèle")

    noms_n1 = list(trace.noms_sous_traces())
    for ligne in ("ligne_assimile", "ligne_tns",
                  "ligne_liberal", "ligne_salarie"):
        runner.check(
            f"Ligne régime '{ligne}' présente dans la trace",
            ligne in noms_n1,
            detail=f"observé: {noms_n1}" if ligne not in noms_n1 else "",
        )

    # 4 lignes_régimes à profondeur 1 (en plus de la racine)
    runner.check(
        "Exactement 4 sous-traces N1 (une par régime)",
        len(noms_n1) == 4,
        detail=f"observé: {len(noms_n1)}",
    )

    runner.section("Spécifique Comparateur : profondeur du graphe")

    runner.check(
        "Profondeur effective ≥ 4 (graphe le plus profond du dépôt)",
        profondeur >= 4,
        detail=f"profondeur observée: {profondeur}",
    )
    # ligne_tns contient arbitrage_tns qui contient les strategies_T*
    # qui contiennent module_tns → profondeur 5 attendue
    runner.check(
        "Profondeur effective ≥ 5 (chaîne ligne_tns → arbitrage_tns → strategie_T → module_tns)",
        profondeur >= 5,
        detail=f"profondeur observée: {profondeur}",
    )

    runner.section("Spécifique Comparateur : volumétrie")

    # Cf. KNOWN_LIMITATIONS : « 412 étapes structurées, profondeur 6 max »
    # On valide au moins l'ordre de grandeur (≥ 300 étapes, ≥ 25 sous-traces).
    runner.check(
        f"Volumétrie : {cas.kpis['etapes_total']} étapes (≥ 300 attendues)",
        cas.kpis["etapes_total"] >= 300,
        detail=f"observé: {cas.kpis['etapes_total']}",
    )
    runner.check(
        f"Volumétrie : {cas.kpis['sous_traces_total']} sous-traces (≥ 25 attendues)",
        cas.kpis["sous_traces_total"] >= 25,
        detail=f"observé: {cas.kpis['sous_traces_total']}",
    )

    runner.section("Spécifique Comparateur : codes namespace tous régimes")

    # Codes namespace COMP_REG_* du comparateur lui-même
    runner.check(
        "Codes namespace 'COMP_REG_*' rendus",
        "COMP_REG_" in cas.texte,
    )
    # Codes des sous-régimes appelés depuis le comparateur — preuve forte
    # de neutralité : le même renderer doit produire les mêmes codes
    # qu'en mode isolé.
    for prefix, regime in (
        ("STRAT_TNS_", "TNS appelé depuis comparateur"),
        ("STRAT_LIB_", "Libéral appelé depuis comparateur"),
        ("STRAT_ASSIM_", "Assimilé appelé depuis comparateur"),
        ("SAL_", "Salarié appelé depuis comparateur"),
        ("TNS_", "module_tns en N5 sous ligne_tns/strategie_TX"),
        ("LIB_BNC_", "module_bnc en N4 sous ligne_liberal/L1-L2"),
    ):
        runner.check(
            f"Codes '{prefix}*' rendus ({regime})",
            prefix in cas.texte,
            detail=f"prefix '{prefix}' non trouvé" if prefix not in cas.texte else "",
        )

    runner.section("Spécifique Comparateur : code 41 chars (calibrage SP7)")

    code_le_plus_long = "COMP_REG_LIB_CODE_STRATEGIE_PLUS_EFFICACE"
    runner.check(
        f"Code 41 chars '{code_le_plus_long}' rendu intact (calibrage SP7)",
        code_le_plus_long in cas.texte,
        detail="code non trouvé — possible wrap"
        if code_le_plus_long not in cas.texte else "",
    )

    runner.section("Spécifique Comparateur : pagination sommaire (correction SP8)")

    # Le sommaire doit tenir sur **une seule page** après la correction
    # SP8 (spaceBefore N0 4 → 2). Avant SP8, il débordait sur une 2e
    # page quasi vide avec une seule ligne orpheline.
    with pdfplumber.open(chemin) as pdf_doc:
        pages_avec_toc = []
        for i, p in enumerate(pdf_doc.pages, 1):
            txt = p.extract_text() or ""
            # Une page est « TOC » si elle contient le motif de lignes pointillées
            if re.search(r"(?:\.\s+){3,}\d{1,3}", txt):
                pages_avec_toc.append(i)
    runner.check(
        f"Sommaire tient sur 1 seule page (correction SP8 D8.1)",
        len(pages_avec_toc) == 1,
        detail=f"TOC trouvé sur pages: {pages_avec_toc}",
    )

    runner.section("Spécifique Comparateur : volume de hypothèses longues")

    # ~21 hypothèses longues attendues (issues des alertes BNC/SEL,
    # mentions retention v2, alertes structuration v2, etc.)
    nb_hyp_longues = sum(
        1 for nom in cas.trace.noms_sous_traces()
        for e in _all_etapes(cas.trace.get_sous_trace(nom))
        for k, v in e.hypotheses.items()
        if len(f"{k}={v}") >= 80
    )
    # On vérifie aussi sur la trace racine + autre niveau pour totaliser
    nb_hyp_longues_total = sum(
        1 for e in _all_etapes(cas.trace)
        for k, v in e.hypotheses.items()
        if len(f"{k}={v}") >= 80
    )
    runner.check(
        f"≥ 5 hypothèses longues dans la trace ({nb_hyp_longues_total} observées)",
        nb_hyp_longues_total >= 5,
        detail=f"observé: {nb_hyp_longues_total}",
    )
    # En-tête « Hypothèses longues développées » présent au moins une fois
    runner.check(
        "En-tête 'Hypothèses longues développées' présent",
        "Hypothèses longues développées" in cas.texte_norm,
    )

    # Synthèse
    return runner.synthese("SP8 Comparateur Régimes")


def _all_etapes(trace: TraceAudit):
    """Générateur récursif sur toutes les étapes du graphe."""
    for e in trace.etapes:
        yield e
    for _, sub in trace.sous_traces.items():
        yield from _all_etapes(sub)


if __name__ == "__main__":
    sys.exit(main())
