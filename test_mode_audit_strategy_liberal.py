"""
test_mode_audit_strategy_liberal.py — Tests dédiés à l'instrumentation
MODE_AUDIT du strategy/liberal (G3c, spec 1.1.0).

Spécificités G3c :
- **Branches dynamiques L3/L4** : la sous-trace régime amont s'appelle
  `module_tns` ou `module_salarie` selon `profil.forme_sel`. Premier
  module strategy à intégrer plusieurs régimes amont distincts.
- **Délégation L4 → L3** : L4 est un wrapper minimal (3 étapes) avec une
  sous-trace `strategie_l3_deleguee` contenant le calcul L3 complet.
  Premier cas de **3 niveaux d'imbrication** :
    arbitrage → strategie_L4 → strategie_l3_deleguee → module_tns/salarie
- **3 alertes structurantes** (`ALERTE_BNC_VS_SEL`, `MENTION_RETENTION_V2`,
  `ALERTE_L4_V2`) préservées en `hypotheses` (wording métier intégral
  intact, non scanné par le test non-prescriptif).
- **Terminologie native non-prescriptive** : la méta utilise
  `STRAT_LIB_PLUS_EFFICACE_FISCALEMENT` au lieu de `STRAT_LIB_RETENU` —
  cohérent avec la doctrine du module (§36-38).

Vérifie :
1. Rétrocompat parfaite (4 stratégies + arbitrage_complet_liberal)
2. Structure trace méta (codes STRAT_LIB_*, terminologie PLUS_EFFICACE_FISCALEMENT)
3. Structure des 4 sous-traces stratégies (L1, L2, L3, L4)
4. Branches dynamiques L3 SELARL/SELAS : sous-trace régime correcte
5. Délégation L4 → L3 (sous-trace strategie_l3_deleguee)
6. 3 niveaux d'imbrication sur L4 (arbitrage → L4 → L3 délégué → régime)
7. Aucune duplication, isolation des espaces de codes
8. Résolution doctrinale sur tout le graphe
9. Alertes structurantes préservées en hypotheses (pas en label/notes)
10. **Test non-prescriptif** : 0 wording prescriptif sur tout le graphe
11. Rendu console complet 3 niveaux
12. Spec version 1.1.0

Usage : python3 test_mode_audit_strategy_liberal.py
Exit code 0 si tous les tests passent.
"""

import sys
import re
import dataclasses

from core.profil import Profil
from core.audit import (
    TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref,
)
from strategy.liberal import (
    _calcul_strategie_l1, _calcul_strategie_l2,
    _calcul_strategie_l3, _calcul_strategie_l4,
    arbitrage_complet_liberal,
)
from ui.audit_render import rendre_trace_console


# ============================================================
# REGISTRES — Contrat G3c
# ============================================================
CODES_ATTENDUS_META = {
    "STRAT_LIB_COMPARE_AB",
    "STRAT_LIB_DELTA_L2_VS_L1",
    "STRAT_LIB_DELTA_L3_VS_L1",
    "STRAT_LIB_DELTA_L4_VS_L1",
    "STRAT_LIB_AVERTISSEMENT_BNC_SEL",
    "STRAT_LIB_CRITERE_PLUS_EFFICACE",
    "STRAT_LIB_PLUS_EFFICACE_FISCALEMENT",  # PAS "RETENU" : terminologie spécifique Libéral
}

CODES_ATTENDUS_L1 = {
    f"STRAT_LIB_L1_{s}" for s in (
        "RECETTES_BNC", "FRAIS_PRO_BNC", "STRUCTURE",
        "BENEFICE_BRUT_BNC", "NET_BNC",
        "NET_DIRIGEANT_TOTAL", "EFFICACITE",
    )
}

CODES_ATTENDUS_L2 = {
    f"STRAT_LIB_L2_{s}" for s in (
        "RECETTES_BNC", "FRAIS_PRO_BNC", "STRUCTURE",
        "REVENU_PRO_BASE_PERIN", "VERSEMENT_PERIN",
        "IMPOTS_FOYER_SANS_PERIN", "IMPOTS_FOYER_AVEC_PERIN",
        "ECONOMIE_IR_PERIN",
        "NET_BNC", "NET_DIRIGEANT_TOTAL", "EFFICACITE",
    )
}

CODES_ATTENDUS_L3 = {
    f"STRAT_LIB_L3_{s}" for s in (
        "RECETTES_BNC", "FRAIS_PRO_SEL", "STRUCTURE",
        "REMUNERATION_BRUTE_SEL", "COTISATIONS_SEL",
        "COUT_REMUNERATION_SEL", "BENEFICE_AVANT_IS",
        "IS_SOCIETE", "DIVIDENDES_DISTRIBUES",
        "NET_REMUNERATION", "NET_DIVIDENDES",
        "NET_DIRIGEANT_TOTAL", "EFFICACITE", "ALERTES_NB",
    )
}

CODES_ATTENDUS_L4 = {
    f"STRAT_LIB_L4_{s}" for s in (
        "DELEGATION_L3", "ALERTE_STRUCTURATION_V2_NB", "NET_DIRIGEANT_TOTAL",
    )
}

NOMS_SOUS_TRACES_META = {"strategie_L1", "strategie_L2",
                          "strategie_L3", "strategie_L4"}


# ============================================================
# VOCABULAIRE PRESCRIPTIF INTERDIT (élargi G3b à \boptim\w*\b)
# ============================================================
TERMES_INTERDITS = [
    r"\boptim\w*\b",
    r"\bmeilleur(?:e|s|es)?\b",
    r"\bgagnant(?:e|s|es)?\b",
    r"\bperdant(?:e|s|es)?\b",
    r"\bavantageu(?:x|se|ses)\b",
    r"\brecommand(?:é|ée|és|ées|er|ation|ations)\b",
    r"\bpréconis(?:é|ée|er|ation)\b",
    r"\bconseill(?:é|ée|er)\b",
    r"\bidéal(?:e|s|es)?\b",
    r"\bparfait(?:e|s|es)?\b",
    r"\bsupérieur(?:e|s|es)?\b",
    r"\binférieur(?:e|s|es)?\b",
]


# ============================================================
# OUTIL DE TEST
# ============================================================
TOL = 0.001
echecs = []


def check(label, condition, detail=""):
    marker = "✓" if condition else "✗"
    suffix = f"  ({detail})" if detail else ""
    print(f"  {marker} {label}{suffix}")
    if not condition:
        echecs.append(label)


# ============================================================
# TEST 1 — RÉTROCOMPAT
# ============================================================
print("=" * 95)
print("  TEST 1 — Rétrocompat parfaite (audit=None ⇒ comportement historique)")
print("=" * 95)

profil = Profil()  # SELARL par défaut

# Chaque stratégie individuelle
for code_strat, fn in (("L1", _calcul_strategie_l1),
                       ("L2", _calcul_strategie_l2),
                       ("L3", _calcul_strategie_l3),
                       ("L4", _calcul_strategie_l4)):
    r_sans = fn(profil)
    t = TraceAudit(regime=f"Stratégie Libéral/{code_strat}")
    r_avec = fn(profil, audit=t)
    check(f"_calcul_strategie_{code_strat.lower()}: dataclass identique avec/sans audit",
          r_sans == r_avec)

# arbitrage_complet_liberal
r_sans_arb = arbitrage_complet_liberal(profil)
trace_arb = TraceAudit(regime="Strategy/Libéral/arbitrage_complet")
r_avec_arb = arbitrage_complet_liberal(profil, audit=trace_arb)
check("arbitrage_complet_liberal: même plus_efficace_fiscalement",
      r_sans_arb.plus_efficace_fiscalement == r_avec_arb.plus_efficace_fiscalement)
check("arbitrage_complet_liberal: 4 stratégies identiques avec/sans audit",
      all(r_sans_arb.strategies[c] == r_avec_arb.strategies[c]
          for c in ("L1", "L2", "L3", "L4")))


# ============================================================
# TEST 2 — STRUCTURE TRACE MÉTA
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure trace méta (terminologie PLUS_EFFICACE_FISCALEMENT)")
print("=" * 95)

codes_meta = set(trace_arb.codes())
check(f"Trace méta contient les {len(CODES_ATTENDUS_META)} codes attendus",
      codes_meta == CODES_ATTENDUS_META,
      f"manquants={CODES_ATTENDUS_META - codes_meta}, "
      f"extras={codes_meta - CODES_ATTENDUS_META}")

# Vérification critique : la trace méta utilise PLUS_EFFICACE_FISCALEMENT, pas RETENU
check("STRAT_LIB_PLUS_EFFICACE_FISCALEMENT présent (terminologie native Libéral)",
      "STRAT_LIB_PLUS_EFFICACE_FISCALEMENT" in codes_meta)
check("STRAT_LIB_RETENU ABSENT (terminologie réservée TNS/Assimilé)",
      "STRAT_LIB_RETENU" not in codes_meta)

# Hiérarchie : DELTA_L<X>_VS_L1 sous COMPARE_AB
for c in ("STRAT_LIB_DELTA_L2_VS_L1", "STRAT_LIB_DELTA_L3_VS_L1",
          "STRAT_LIB_DELTA_L4_VS_L1"):
    e = trace_arb.get(c)
    check(f"parent_id de {c} = STRAT_LIB_COMPARE_AB",
          e.parent_id == "STRAT_LIB_COMPARE_AB")


# ============================================================
# TEST 3 — STRUCTURE DES 4 SOUS-TRACES STRATÉGIES
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Structure des 4 sous-traces stratégies (L1/L2/L3/L4)")
print("=" * 95)

attendus_par_strat = {
    "L1": CODES_ATTENDUS_L1,
    "L2": CODES_ATTENDUS_L2,
    "L3": CODES_ATTENDUS_L3,
    "L4": CODES_ATTENDUS_L4,
}

for code_strat, attendus in attendus_par_strat.items():
    sub = trace_arb.get_sous_trace(f"strategie_{code_strat}")
    check(f"Sous-trace 'strategie_{code_strat}' attachée", sub is not None)
    if sub is None:
        continue
    codes_obtenus = set(sub.codes())
    check(f"  → {code_strat} contient les {len(attendus)} codes attendus",
          codes_obtenus == attendus,
          f"manquants={attendus - codes_obtenus}, "
          f"extras={codes_obtenus - attendus}")


# ============================================================
# TEST 4 — BRANCHES DYNAMIQUES L3 SELARL/SELAS
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Branches dynamiques L3 (sous-trace régime selon forme_sel)")
print("=" * 95)

# Branche SELARL : sous-trace 'module_tns'
profil_selarl = Profil(forme_sel="SELARL")
trace_selarl = TraceAudit(regime="Test SELARL")
arbitrage_complet_liberal(profil_selarl, audit=trace_selarl)
sub_l3_selarl = trace_selarl.get_sous_trace("strategie_L3")
noms_l3_selarl = set(sub_l3_selarl.noms_sous_traces())
check("SELARL : sous-trace L3 contient 'module_tns'",
      noms_l3_selarl == {"module_tns"},
      f"obtenu={noms_l3_selarl}")

sub_tns = sub_l3_selarl.get_sous_trace("module_tns")
check("  SELARL : module_tns contient des codes TNS_*",
      all(c.startswith("TNS_") for c in sub_tns.codes()))
check("  SELARL : module_tns contient 24 étapes (régime TNS complet)",
      len(sub_tns.etapes) == 24)

# Branche SELAS : sous-trace 'module_salarie'
profil_selas = dataclasses.replace(profil, forme_sel="SELAS")
trace_selas = TraceAudit(regime="Test SELAS")
arbitrage_complet_liberal(profil_selas, audit=trace_selas)
sub_l3_selas = trace_selas.get_sous_trace("strategie_L3")
noms_l3_selas = set(sub_l3_selas.noms_sous_traces())
check("SELAS : sous-trace L3 contient 'module_salarie'",
      noms_l3_selas == {"module_salarie"},
      f"obtenu={noms_l3_selas}")

sub_sal = sub_l3_selas.get_sous_trace("module_salarie")
check("  SELAS : module_salarie contient des codes SAL_*",
      all(c.startswith("SAL_") for c in sub_sal.codes()))
check("  SELAS : module_salarie contient 17 étapes (régime Salarié complet)",
      len(sub_sal.etapes) == 17)


# ============================================================
# TEST 5 — DÉLÉGATION L4 → L3 (option B validée)
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Délégation L4 → L3 (sous-trace 'strategie_l3_deleguee')")
print("=" * 95)

sub_l4 = trace_arb.get_sous_trace("strategie_L4")
check("L4 wrapper minimal : exactement 3 étapes",
      len(sub_l4.etapes) == 3,
      f"obtenu={len(sub_l4.etapes)}")

noms_l4 = set(sub_l4.noms_sous_traces())
check("L4 attache une sous-trace 'strategie_l3_deleguee'",
      noms_l4 == {"strategie_l3_deleguee"},
      f"obtenu={noms_l4}")

sub_l3_delegue = sub_l4.get_sous_trace("strategie_l3_deleguee")
check("  strategie_l3_deleguee contient un calcul L3 complet (14 étapes)",
      len(sub_l3_delegue.etapes) == 14)
check("  tous les codes sont STRAT_LIB_L3_*",
      all(c.startswith("STRAT_LIB_L3_") for c in sub_l3_delegue.codes()))

# Vérifier qu'aucun recalcul : net_dirigeant_total dans L3 délégué = celui dans L4
e_net_l4 = sub_l4.get("STRAT_LIB_L4_NET_DIRIGEANT_TOTAL")
e_net_l3_delegue = sub_l3_delegue.get("STRAT_LIB_L3_NET_DIRIGEANT_TOTAL")
check("  L4 net == L3 délégué net (pas de recalcul)",
      abs(e_net_l4.valeur - e_net_l3_delegue.valeur) < TOL)


# ============================================================
# TEST 6 — TROIS NIVEAUX D'IMBRICATION SUR L4
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — 3 niveaux d'imbrication sur L4 (premier cas G3c)")
print("=" * 95)

# Niveau 0 : arbitrage_complet_liberal (trace_arb)
# Niveau 1 : strategie_L4
# Niveau 2 : strategie_l3_deleguee
# Niveau 3 : module_tns ou module_salarie

# Profil par défaut = SELARL
sub_lvl1 = trace_arb.get_sous_trace("strategie_L4")
sub_lvl2 = sub_lvl1.get_sous_trace("strategie_l3_deleguee")
sub_lvl3_noms = set(sub_lvl2.noms_sous_traces())
check("Niveau 3 atteint : L4 → L3 délégué → module_tns (profil SELARL)",
      sub_lvl3_noms == {"module_tns"},
      f"obtenu={sub_lvl3_noms}")

sub_lvl3 = sub_lvl2.get_sous_trace("module_tns")
check("  Niveau 3 : module_tns contient 24 étapes TNS_*",
      len(sub_lvl3.etapes) == 24 and
      all(c.startswith("TNS_") for c in sub_lvl3.codes()))


# ============================================================
# TEST 7 — AUCUNE DUPLICATION / ISOLATION ESPACES DE CODES
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Isolation espaces de codes (STRAT_LIB_* ⊥ autres préfixes)")
print("=" * 95)

# Méta : tous codes préfixés STRAT_LIB_
check("Méta : tous codes préfixés STRAT_LIB_",
      all(c.startswith("STRAT_LIB_") for c in codes_meta))

# Aucune intrusion STRAT_TNS_* ou STRAT_ASSIM_* dans la méta
check("Méta : aucune intrusion STRAT_TNS_* ou STRAT_ASSIM_*",
      not any(c.startswith(("STRAT_TNS_", "STRAT_ASSIM_")) for c in codes_meta))

# Chaque stratégie : préfixée STRAT_LIB_L<X>_
for code_strat in ("L1", "L2", "L3", "L4"):
    sub = trace_arb.get_sous_trace(f"strategie_{code_strat}")
    check(f"strategie_{code_strat}: tous codes préfixés STRAT_LIB_{code_strat}_",
          all(c.startswith(f"STRAT_LIB_{code_strat}_") for c in sub.codes()))


# ============================================================
# TEST 8 — RÉSOLUTION DOCTRINALE
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Doctrine_refs se résolvent sur tout le graphe")
print("=" * 95)

refs_uniques = set()
def collecter_refs(t):
    for e in t.etapes:
        refs_uniques.update(e.doctrine_refs)
    for n in t.noms_sous_traces():
        collecter_refs(t.get_sous_trace(n))

# Combiner SELARL et SELAS pour couvrir les deux branches
collecter_refs(trace_selarl)
collecter_refs(trace_selas)

check(f"{len(refs_uniques)} doctrine_refs uniques dans les 2 branches",
      len(refs_uniques) >= 10)

attendues_minimales = {
    "TX_TNS", "TX_PATRONAL", "TX_LIB", "TX_PFU",
    "IS_PLAF_REDUIT", "TX_IS_REDUIT", "TX_IS_NORMAL",
}
check("Doctrine_refs minimales attendues présentes",
      attendues_minimales.issubset(refs_uniques),
      f"manquantes={attendues_minimales - refs_uniques}")

for ref in sorted(refs_uniques):
    try:
        valeur = resoudre_doctrine_ref(ref)
        check(f"  Résolution {ref} = {valeur}", True)
    except AttributeError as e:
        check(f"  Résolution {ref}", False, str(e))


# ============================================================
# TEST 9 — ALERTES STRUCTURANTES PRÉSERVÉES EN HYPOTHESES
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Alertes structurantes en hypotheses (pas en label/notes)")
print("=" * 95)

# L3 : ALERTE_BNC_VS_SEL + MENTION_RETENTION_V2
sub_l3 = trace_arb.get_sous_trace("strategie_L3")
e_alertes_l3 = sub_l3.get("STRAT_LIB_L3_ALERTES_NB")
check("L3 : STRAT_LIB_L3_ALERTES_NB présent", e_alertes_l3 is not None)
check("  L3 valeur = 2 alertes attachées",
      abs(e_alertes_l3.valeur - 2.0) < TOL)
check("  L3 ALERTE_BNC_VS_SEL dans hypotheses (intégral)",
      "ALERTE_BNC_VS_SEL" in e_alertes_l3.hypotheses)
check("  L3 MENTION_RETENTION_V2 dans hypotheses (intégral)",
      "MENTION_RETENTION_V2" in e_alertes_l3.hypotheses)
# Vérifier que le texte intégral est préservé (caractéristique d'origine)
texte_bnc_sel = e_alertes_l3.hypotheses.get("ALERTE_BNC_VS_SEL", "")
check("  L3 texte ALERTE_BNC_VS_SEL contient 'cadrage indicatif'",
      "cadrage indicatif" in texte_bnc_sel)

# L4 : ALERTE_L4_V2
sub_l4 = trace_arb.get_sous_trace("strategie_L4")
e_alertes_l4 = sub_l4.get("STRAT_LIB_L4_ALERTE_STRUCTURATION_V2_NB")
check("L4 : STRAT_LIB_L4_ALERTE_STRUCTURATION_V2_NB présent", e_alertes_l4 is not None)
check("  L4 ALERTE_L4_V2 dans hypotheses (intégral)",
      "ALERTE_L4_V2" in e_alertes_l4.hypotheses)

# Méta : avertissement BNC vs SEL au niveau méta
e_avert_meta = trace_arb.get("STRAT_LIB_AVERTISSEMENT_BNC_SEL")
check("Méta : STRAT_LIB_AVERTISSEMENT_BNC_SEL présent", e_avert_meta is not None)
check("  Méta : ALERTE_BNC_VS_SEL en hypotheses",
      "ALERTE_BNC_VS_SEL" in e_avert_meta.hypotheses)


# ============================================================
# TEST 10 — NON-PRESCRIPTIF (scan automatique de tout le graphe)
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Aucun wording prescriptif dans labels ou notes (récursif)")
print("=" * 95)

def scanner_prescriptif(t, chemin=""):
    violations = []
    for e in t.etapes:
        for champ, texte in (("label", e.label), ("notes", e.notes)):
            for pattern in TERMES_INTERDITS:
                if re.search(pattern, texte, re.IGNORECASE):
                    violations.append((chemin or t.regime, e.code, pattern, champ, texte))
    for nom in t.noms_sous_traces():
        sub = t.get_sous_trace(nom)
        violations.extend(scanner_prescriptif(
            sub, chemin=f"{chemin}/{nom}" if chemin else nom))
    return violations

def compter_etapes(t):
    n = len(t.etapes)
    for nom in t.noms_sous_traces():
        n += compter_etapes(t.get_sous_trace(nom))
    return n

# Scanner les deux branches (SELARL et SELAS)
violations = scanner_prescriptif(trace_arb)  # SELARL par défaut
violations.extend(scanner_prescriptif(trace_selas))
n_total = compter_etapes(trace_arb) + compter_etapes(trace_selas)

if violations:
    check(f"Aucun wording prescriptif détecté", False,
          f"{len(violations)} violation(s) sur {n_total} étapes scannées")
    for chemin, code, pattern, champ, texte in violations[:5]:
        print(f"       ⚠ {chemin} / {code} / {champ} : pattern={pattern} dans {texte!r}")
else:
    check(f"Aucun wording prescriptif dans tout le graphe", True,
          f"{n_total} étapes scannées sur 12 patterns (2 branches : SELARL + SELAS)")


# ============================================================
# TEST 11 — RENDU CONSOLE 3 NIVEAUX
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Rendu console (3 niveaux d'imbrication)")
print("=" * 95)

rendu = rendre_trace_console(trace_arb)
check("Rendu non-vide", len(rendu) > 5000)
check("En-tête racine Libéral", "Strategy/Libéral" in rendu)
check("Contient STRAT_LIB_PLUS_EFFICACE_FISCALEMENT",
      "STRAT_LIB_PLUS_EFFICACE_FISCALEMENT" in rendu)
check("Sous-traces niveau 1 (4 stratégies)",
      "Sous-traces attachées (4)" in rendu)
for c in ("strategie_L1", "strategie_L2", "strategie_L3", "strategie_L4"):
    check(f"  rendu sous-trace {c!r}",
          f"nom d'attachement : {c!r}" in rendu)
check("Sous-trace L4 → strategie_l3_deleguee (niveau 2)",
      "nom d'attachement : 'strategie_l3_deleguee'" in rendu)
check("Sous-trace L3/L4 → module_tns (niveau 2/3)",
      rendu.count("nom d'attachement : 'module_tns'") >= 2)
check("Pas de référence introuvable", "référence introuvable" not in rendu)


# ============================================================
# TEST 12 — SPEC VERSION
# ============================================================
print()
print("=" * 95)
print("  TEST 12 — Spec version 1.1.0")
print("=" * 95)

check(f"Spec version {AUDIT_SPEC_VERSION}",
      trace_arb.spec_version == AUDIT_SPEC_VERSION == "1.1.0")
for nom in trace_arb.noms_sous_traces():
    sub = trace_arb.get_sous_trace(nom)
    check(f"  sous-trace {nom!r} porte la spec 1.1.0",
          sub.spec_version == "1.1.0")


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Strategy/Libéral passent (G3c)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
