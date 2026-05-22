"""
test_mode_audit_strategy_assimile.py — Tests dédiés à l'instrumentation
MODE_AUDIT du strategy/assimile (G3a, spec 1.1.0).

Spécificités G3a :
- Premier niveau « méta » du MODE_AUDIT : les stratégies arbitrent entre
  régimes, elles ne calculent pas.
- Premier usage des **sous-traces composables** (spec 1.1.0).
- Premier **test automatique de non-prescriptivité** : scan des labels et
  notes contre la liste des termes interdits.

Vérifie :
1. Rétrocompat parfaite calcul_strategie + arbitrage_complet
2. Structure attendue de la trace méta (codes STRAT_ASSIM_*)
3. Structure attendue de chaque trace stratégie (codes STRAT_ASSIM_<X>_*)
4. Sous-traces correctement attachées (graphe composé)
5. Aucune duplication d'étapes entre méta et sous-traces
6. Résolution doctrinale
7. Garde-fous d'attachement (refus doublons, réattachement, cycles)
8. Cohérence valeurs tracées vs dict retourné
9. **Test non-prescriptif** : aucun label/note ne contient de wording prescriptif
10. Rendu console complet (méta + sous-traces récursives)
11. Isolation des espaces de codes (STRAT_* ⊥ TNS_*/LIB_*/SAL_*/ASSIM_*)
12. Spec version 1.1.0

Usage : python3 test_mode_audit_strategy_assimile.py
Exit code 0 si tous les tests passent.
"""

import sys
import re

from core.profil import Profil
from core.audit import (
    TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref,
)
from strategy.assimile import calcul_strategie, arbitrage_complet, STRATEGIES
from ui.audit_render import rendre_trace_console


# ============================================================
# REGISTRES — Contrat G3a
# ============================================================
CODES_ATTENDUS_META = {
    "STRAT_ASSIM_TX_IR_MOY_RACINE",
    "STRAT_ASSIM_COMPARE_AB",
    "STRAT_ASSIM_DELTA_B_VS_A",
    "STRAT_ASSIM_DELTA_C_VS_A",
    "STRAT_ASSIM_DELTA_D_VS_A",
    "STRAT_ASSIM_CRITERE_RETENU",
    "STRAT_ASSIM_RETENU",
}

# Codes attendus dans une trace calcul_strategie (par stratégie)
def codes_attendus_strategie(code):
    p = f"STRAT_ASSIM_{code}_"
    return {
        p + "ENVELOPPE",
        p + "TX_IR_MOY_APPLIQUE",
        p + "ALLOCATION",
        p + "ALLOC_SALAIRE",
        p + "ALLOC_DIVIDENDES",
        p + "ALLOC_EPARGNE",
        p + "ALLOC_PERIPHERIQUES",
        p + "NET_SALAIRE",
        p + "NET_DIVIDENDES",
        p + "NET_EPARGNE",
        p + "NET_PERIPHERIQUES",
        p + "TOTAL_NET",
        p + "EFFICACITE",
    }


NOMS_SOUS_TRACES_ATTENDUS = {
    "tx_ir_moy", "strategie_A", "strategie_B", "strategie_C", "strategie_D"
}


# ============================================================
# VOCABULAIRE PRESCRIPTIF INTERDIT (test 9)
# ============================================================
# Termes interdits dans les labels et notes des étapes MODE_AUDIT.
# Le critère est plus strict que `semantic_guardrails.py` parce que la trace
# elle-même ne doit jamais véhiculer d'appréciation prescriptive.
TERMES_INTERDITS = [
    # Wording prescriptif explicite (élargi G3b à \boptim\w* pour capturer
    # optimum / optimisé / optime en plus de optimal / optimisation)
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
    r"\bsupérieur(?:e|s|es)?\b",  # « la stratégie X est supérieure à Y »
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

profil = Profil()

# calcul_strategie seul
r_sans_strat = calcul_strategie(profil, "C", 0.10)
trace_strat = TraceAudit(regime="Stratégie Assimilé/C")
r_avec_strat = calcul_strategie(profil, "C", 0.10, audit=trace_strat)
check("calcul_strategie(C): dict identique avec/sans audit",
      r_sans_strat == r_avec_strat)

# arbitrage_complet
r_sans_arb = arbitrage_complet(profil)
trace_arb = TraceAudit(regime="Strategy/Assimilé/arbitrage")
r_avec_arb = arbitrage_complet(profil, audit=trace_arb)
check("arbitrage_complet: dict identique avec/sans audit",
      r_sans_arb == r_avec_arb)
check("arbitrage_complet: même stratégie retenue",
      r_sans_arb["recommandee"] == r_avec_arb["recommandee"],
      f"sans={r_sans_arb['recommandee']}, avec={r_avec_arb['recommandee']}")


# ============================================================
# TEST 2 — STRUCTURE TRACE MÉTA
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure trace méta (codes STRAT_ASSIM_*)")
print("=" * 95)

codes_meta = set(trace_arb.codes())
check(f"Trace méta contient les {len(CODES_ATTENDUS_META)} codes attendus",
      codes_meta == CODES_ATTENDUS_META,
      f"manquants={CODES_ATTENDUS_META - codes_meta}, "
      f"extras={codes_meta - CODES_ATTENDUS_META}")

# Hiérarchie : DELTA_X_VS_A doivent avoir COMPARE_AB pour parent
for code_delta in ("STRAT_ASSIM_DELTA_B_VS_A",
                   "STRAT_ASSIM_DELTA_C_VS_A",
                   "STRAT_ASSIM_DELTA_D_VS_A"):
    e = trace_arb.get(code_delta)
    check(f"parent_id de {code_delta} = STRAT_ASSIM_COMPARE_AB",
          e.parent_id == "STRAT_ASSIM_COMPARE_AB")


# ============================================================
# TEST 3 — STRUCTURE TRACES STRATÉGIE (sous-traces)
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Structure de chaque sous-trace stratégie")
print("=" * 95)

for code_strat in ("A", "B", "C", "D"):
    sub = trace_arb.get_sous_trace(f"strategie_{code_strat}")
    check(f"Sous-trace 'strategie_{code_strat}' attachée",
          sub is not None)
    if sub is None:
        continue
    codes_obtenus = set(sub.codes())
    attendus = codes_attendus_strategie(code_strat)
    check(f"  → contient les {len(attendus)} codes attendus",
          codes_obtenus == attendus,
          f"manquants={attendus - codes_obtenus}")


# ============================================================
# TEST 4 — SOUS-TRACES ATTACHÉES
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Sous-traces correctement attachées (graphe composé)")
print("=" * 95)

noms = set(trace_arb.noms_sous_traces())
check(f"5 sous-traces attendues : {NOMS_SOUS_TRACES_ATTENDUS}",
      noms == NOMS_SOUS_TRACES_ATTENDUS,
      f"manquantes={NOMS_SOUS_TRACES_ATTENDUS - noms}, "
      f"extras={noms - NOMS_SOUS_TRACES_ATTENDUS}")

# tx_ir_moy doit pointer sur une vraie trace régime
sub_tx = trace_arb.get_sous_trace("tx_ir_moy")
check("Sous-trace 'tx_ir_moy' contient des codes ASSIM_TX_IR_MOY_*",
      sub_tx is not None and
      all(c.startswith("ASSIM_TX_IR_MOY_") for c in sub_tx.codes()))


# ============================================================
# TEST 5 — AUCUNE DUPLICATION DES ÉTAPES
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Aucune duplication d'étapes entre méta et sous-traces")
print("=" * 95)

# Les codes STRAT_ASSIM_<X>_* (spécifiques par stratégie) ne doivent JAMAIS
# apparaître dans la trace méta. Ils vivent uniquement dans leur sous-trace.
codes_strat_specifiques = set()
for code in ("A", "B", "C", "D"):
    codes_strat_specifiques |= codes_attendus_strategie(code)

collisions = codes_meta & codes_strat_specifiques
check("Aucun code spécifique par stratégie ne pollue la trace méta",
      not collisions,
      f"collisions={collisions}")

# Les codes ASSIM_TX_IR_MOY_* (sous-trace régime) ne doivent pas non plus
# apparaître dans la méta
codes_assim = {c for c in sub_tx.codes() if c.startswith("ASSIM_")}
collisions_assim = codes_meta & codes_assim
check("Codes ASSIM_TX_IR_MOY_* restent dans leur sous-trace",
      not collisions_assim)


# ============================================================
# TEST 6 — RÉSOLUTION DOCTRINALE
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Doctrine_refs (méta + sous-traces) se résolvent")
print("=" * 95)

# Collecter tous les doctrine_refs dans toute la trace (méta + sous-traces)
refs_uniques = set()
def collecter_refs(t):
    for e in t.etapes:
        refs_uniques.update(e.doctrine_refs)
    for n in t.noms_sous_traces():
        collecter_refs(t.get_sous_trace(n))
collecter_refs(trace_arb)

check(f"{len(refs_uniques)} doctrine_refs uniques dans le graphe",
      len(refs_uniques) >= 8,  # au moins celles de TX_IR_MOY + stratégies
      f"refs={sorted(refs_uniques)}")

for ref in sorted(refs_uniques):
    try:
        valeur = resoudre_doctrine_ref(ref)
        check(f"Résolution {ref} = {valeur}", True)
    except AttributeError as e:
        check(f"Résolution {ref}", False, str(e))


# ============================================================
# TEST 7 — GARDE-FOUS D'ATTACHEMENT (spec 1.1.0)
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Garde-fous attacher_sous_trace (spec 1.1.0)")
print("=" * 95)

# Refus doublon
t_test = TraceAudit(regime="Test")
sub1 = TraceAudit(regime="Sub1")
sub2 = TraceAudit(regime="Sub2")
t_test.attacher_sous_trace("nom_x", sub1)
try:
    t_test.attacher_sous_trace("nom_x", sub2)
    check("Refus doublon de nom", False, "doublon non détecté")
except ValueError:
    check("Refus doublon de nom : ValueError levée", True)

# Refus réattachement
try:
    t_test.attacher_sous_trace("autre_nom", sub1)
    check("Refus réattachement", False)
except ValueError:
    check("Refus réattachement : ValueError levée", True)

# Refus cycle direct
try:
    t_test.attacher_sous_trace("cycle", t_test)
    check("Refus cycle direct", False)
except ValueError:
    check("Refus cycle direct : ValueError levée", True)

# Refus type
try:
    t_test.attacher_sous_trace("bad", "pas une trace")
    check("Refus type incorrect", False)
except TypeError:
    check("Refus type incorrect : TypeError levée", True)


# ============================================================
# TEST 8 — COHÉRENCE VALEURS TRACÉES vs DICT RETOURNÉ
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Cohérence valeurs tracées vs dict retourné par calcul_strategie")
print("=" * 95)

for code_strat in ("A", "B", "C", "D"):
    sub = trace_arb.get_sous_trace(f"strategie_{code_strat}")
    res = r_avec_arb["strategies"][code_strat]
    mapping = {
        f"STRAT_ASSIM_{code_strat}_ENVELOPPE": "cout_total",  # env initiale
        f"STRAT_ASSIM_{code_strat}_ALLOC_SALAIRE": "cout_salaire",
        f"STRAT_ASSIM_{code_strat}_ALLOC_DIVIDENDES": "cout_dividendes",
        f"STRAT_ASSIM_{code_strat}_ALLOC_EPARGNE": "cout_epargne",
        f"STRAT_ASSIM_{code_strat}_ALLOC_PERIPHERIQUES": "cout_peripheriques",
        f"STRAT_ASSIM_{code_strat}_NET_SALAIRE": "net_salaire",
        f"STRAT_ASSIM_{code_strat}_NET_DIVIDENDES": "net_dividendes",
        f"STRAT_ASSIM_{code_strat}_NET_EPARGNE": "net_epargne",
        f"STRAT_ASSIM_{code_strat}_NET_PERIPHERIQUES": "net_peripheriques",
        f"STRAT_ASSIM_{code_strat}_TOTAL_NET": "total_net",
        f"STRAT_ASSIM_{code_strat}_EFFICACITE": "efficacite",
    }
    for code_trace, attr in mapping.items():
        v_trace = sub.get(code_trace).valeur
        v_res = res[attr]
        check(f"  {code_trace}",
              abs(v_trace - v_res) < TOL,
              f"trace={v_trace}, res={v_res}")


# ============================================================
# TEST 9 — NON-PRESCRIPTIF (scan automatique des labels et notes)
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Aucun wording prescriptif dans labels ou notes")
print("=" * 95)

def scanner_prescriptif(t, chemin=""):
    """Scan récursif trace + sous-traces. Retourne liste (chemin, code, terme, texte)."""
    violations = []
    for e in t.etapes:
        for champ, texte in (("label", e.label), ("notes", e.notes)):
            for pattern in TERMES_INTERDITS:
                if re.search(pattern, texte, re.IGNORECASE):
                    violations.append((chemin or t.regime, e.code, pattern, champ, texte))
    for nom in t.noms_sous_traces():
        sub = t.get_sous_trace(nom)
        violations.extend(scanner_prescriptif(sub, chemin=f"{chemin}/{nom}" if chemin else nom))
    return violations

violations = scanner_prescriptif(trace_arb)
if violations:
    check(f"Aucun wording prescriptif détecté", False,
          f"{len(violations)} violation(s)")
    for chemin, code, pattern, champ, texte in violations[:5]:
        print(f"       ⚠ {chemin} / {code} / {champ} : pattern={pattern} dans {texte!r}")
else:
    check("Aucun wording prescriptif détecté dans toute la trace", True,
          f"scanné {sum(len(trace_arb.get_sous_trace(n).etapes) for n in trace_arb.noms_sous_traces()) + len(trace_arb.etapes)} étapes")


# ============================================================
# TEST 10 — RENDU CONSOLE
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Rendu console (méta + sous-traces récursives)")
print("=" * 95)

rendu = rendre_trace_console(trace_arb)
check("Rendu non-vide", len(rendu) > 2000)
check("En-tête racine", "AUDIT — Régime Strategy" in rendu)
check("Contient STRAT_ASSIM_RETENU", "STRAT_ASSIM_RETENU" in rendu)
check("Contient toutes les sous-traces", "Sous-traces attachées (5)" in rendu)
check("Sous-trace tx_ir_moy rendue",
      "nom d'attachement : 'tx_ir_moy'" in rendu)
check("Sous-trace strategie_D rendue",
      "nom d'attachement : 'strategie_D'" in rendu)
check("Pas de référence introuvable", "référence introuvable" not in rendu)


# ============================================================
# TEST 11 — ISOLATION DES ESPACES DE CODES
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Isolation STRAT_* ⊥ {TNS_*, LIB_*, SAL_*, ASSIM_*}")
print("=" * 95)

prefixes_amont = ("TNS_", "LIB_BNC_", "LIB_SEL_", "SAL_", "ASSIM_")

# Méta : tous préfixés STRAT_ASSIM_
check("Méta : tous les codes préfixés STRAT_ASSIM_",
      all(c.startswith("STRAT_ASSIM_") for c in codes_meta))

# Stratégies : tous préfixés STRAT_ASSIM_<X>_
for code_strat in ("A", "B", "C", "D"):
    sub = trace_arb.get_sous_trace(f"strategie_{code_strat}")
    check(f"strategie_{code_strat}: tous préfixés STRAT_ASSIM_{code_strat}_",
          all(c.startswith(f"STRAT_ASSIM_{code_strat}_") for c in sub.codes()))


# ============================================================
# TEST 12 — SPEC VERSION
# ============================================================
print()
print("=" * 95)
print("  TEST 12 — Spec version 1.1.0")
print("=" * 95)

check(f"AUDIT_SPEC_VERSION = {AUDIT_SPEC_VERSION}", AUDIT_SPEC_VERSION == "1.1.0")
check("Trace méta porte la spec 1.1.0",
      trace_arb.spec_version == "1.1.0")
for nom in trace_arb.noms_sous_traces():
    sub = trace_arb.get_sous_trace(nom)
    check(f"Sous-trace {nom!r} porte la spec 1.1.0",
          sub.spec_version == "1.1.0")


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Strategy/Assimilé passent (G3a)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
