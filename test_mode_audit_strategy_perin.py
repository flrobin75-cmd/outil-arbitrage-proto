"""
test_mode_audit_strategy_perin.py — Tests dédiés à l'instrumentation
MODE_AUDIT du strategy/perin (G3f-perin, spec 1.1.0).

Spécificités G3f-perin :
- **Namespace dédié `PERIN_*`** distinct de tous les namespaces précédents
  (régimes, stratégies, comparateurs, post-arbitrage).
- **Module 100% autonome** : `calcul_plafond_perin` produit une trace plate
  (~7 étapes). `calcul_perin_mutualise` attache `plafond_dirigeant` toujours
  et `plafond_conjoint` uniquement si mutualisation effective.
- **Composition conditionnelle** validée : la sous-trace `plafond_conjoint`
  est attachée si et seulement si situation == "Marié / pacsé" AND
  conjoint_declare AND revenu_pro_conjoint > 0.
- **Conditions explicites** : `PERIN_MUTUALISATION_POSSIBLE.hypotheses["condition"]`
  trace la formule logique et les valeurs évaluées de chaque sous-condition.
- **Discipline non-prescriptive renforcée G3e (14 patterns)** : 0 occurrence.

Vérifie :
1. Rétrocompat parfaite — 2 fonctions × multiples scénarios
2. Structure `calcul_plafond_perin` (7 étapes plates)
3. Structure `calcul_perin_mutualise` sans mutualisation (12 étapes + 1 sous-trace)
4. Structure `calcul_perin_mutualise` avec mutualisation (12 étapes + 2 sous-traces)
5. Composition conditionnelle de `plafond_conjoint`
6. Cas plancher 10% PASS (revenu très bas)
7. Cas plafond 8 PASS (revenu très haut)
8. Cas excédent (versement > plafond)
9. Branche tracée dans hypotheses["branche"] (sans/avec mutualisation)
10. Cohérence valeurs trace vs ResultatPERINMutualise
11. **Test non-prescriptif renforcé** (14 patterns × tout le graphe)
12. Isolation `PERIN_*` ⊥ tous les autres namespaces
13. Doctrine_refs PASS_2026 résolu

Usage : python3 test_mode_audit_strategy_perin.py
Exit code 0 si tous les tests passent.
"""

import sys
import re

from core.audit import (
    TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref,
)
from strategy.perin import (
    calcul_plafond_perin, calcul_perin_mutualise,
    PlafondPERIN, ResultatPERINMutualise,
    PERIN_PLAFOND_MIN, PERIN_PLAFOND_MAX, PERIN_TAUX_REV_PRO,
)


# ============================================================
# PATTERNS NON-PRESCRIPTIFS RENFORCÉS G3e (14 patterns)
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
    r"\bprioritaire(?:s)?\b",
    r"\bprivilégi\w*\b",
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


def compter_etapes(t):
    n = len(t.etapes)
    for nom in t.noms_sous_traces():
        n += compter_etapes(t.get_sous_trace(nom))
    return n


def scanner_prescriptif(t, chemin=""):
    violations = []
    for e in t.etapes:
        for champ, texte in [("label", e.label), ("notes", e.notes)]:
            for pattern in TERMES_INTERDITS:
                if re.search(pattern, texte, re.IGNORECASE):
                    violations.append((chemin or t.regime, e.code,
                                       pattern, champ, texte))
    for nom in t.noms_sous_traces():
        sub = t.get_sous_trace(nom)
        violations.extend(scanner_prescriptif(
            sub, chemin=f"{chemin}/{nom}" if chemin else nom))
    return violations


def collecter_codes(t):
    codes = set(t.codes())
    for nom in t.noms_sous_traces():
        codes |= collecter_codes(t.get_sous_trace(nom))
    return codes


# ============================================================
# TEST 1 — RÉTROCOMPAT 2 FONCTIONS
# ============================================================
print("=" * 95)
print("  TEST 1 — Rétrocompat parfaite (2 fonctions × multiples scénarios)")
print("=" * 95)

# 1.a calcul_plafond_perin
for revenu in [1000, 50000, 80000, 5000000]:
    r_sans = calcul_plafond_perin("Dirigeant", revenu)
    t = TraceAudit(regime=f"Plafond rev={revenu}")
    r_avec = calcul_plafond_perin("Dirigeant", revenu, audit=t)
    check(f"calcul_plafond_perin rev={revenu}", r_sans == r_avec)

# 1.b calcul_perin_mutualise — 4 scénarios représentatifs
scenarios = [
    ("Célibataire", dict(versement_dirigeant=10000, revenu_pro_dirigeant=80000,
                          tmi_dirigeant=0.30,
                          situation="Célibataire / divorcé / veuf")),
    ("Marié non déclaré", dict(versement_dirigeant=10000, revenu_pro_dirigeant=80000,
                                tmi_dirigeant=0.30, situation="Marié / pacsé",
                                conjoint_declare=False, revenu_pro_conjoint=60000)),
    ("Marié déclaré", dict(versement_dirigeant=20000, revenu_pro_dirigeant=80000,
                            tmi_dirigeant=0.41, situation="Marié / pacsé",
                            conjoint_declare=True, revenu_pro_conjoint=60000,
                            versement_conjoint=3000)),
    ("Excédent", dict(versement_dirigeant=50000, revenu_pro_dirigeant=80000,
                       tmi_dirigeant=0.30,
                       situation="Célibataire / divorcé / veuf")),
]
for nom, kwargs in scenarios:
    r_sans = calcul_perin_mutualise(**kwargs)
    t = TraceAudit(regime=f"Mutualise {nom}")
    r_avec = calcul_perin_mutualise(audit=t, **kwargs)
    check(f"calcul_perin_mutualise {nom}", r_sans == r_avec)


# ============================================================
# TEST 2 — Structure calcul_plafond_perin (7 étapes plates)
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure calcul_plafond_perin (7 étapes plates)")
print("=" * 95)

t_pl = TraceAudit(regime="Plafond test")
calcul_plafond_perin("Dirigeant", 80000, audit=t_pl)
codes_pl = set(t_pl.codes())

attendus_pl = {
    "PERIN_TITULAIRE",
    "PERIN_REVENU_PRO_N_MOINS_1",
    "PERIN_PLAFOND_CALCULE",
    "PERIN_PLAFOND_PLANCHER",
    "PERIN_PLAFOND_PLAFOND",
    "PERIN_PLAFOND_INDIVIDUEL",
    "PERIN_SOLDE_DISPONIBLE_INITIAL",
}
check(f"7 codes attendus présents",
      attendus_pl.issubset(codes_pl),
      f"manquants={attendus_pl - codes_pl}")

# Pas de sous-trace
check("Aucune sous-trace (trace plate)",
      len(t_pl.noms_sous_traces()) == 0)

# Valeur PLAFOND_CALCULE = revenu × 10%
e_calc = t_pl.get("PERIN_PLAFOND_CALCULE")
check("PLAFOND_CALCULE = 8000 € (80000 × 10%)",
      abs(e_calc.valeur - 8000.0) < TOL)

# doctrine_refs présents
check("PERIN_PLAFOND_CALCULE.doctrine_refs contient PASS_2026",
      "PASS_2026" in e_calc.doctrine_refs)


# ============================================================
# TEST 3 — Structure calcul_perin_mutualise SANS mutualisation
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Structure SANS mutualisation (12 étapes + 1 sous-trace)")
print("=" * 95)

t_sm = TraceAudit(regime="Sans mutualisation")
calcul_perin_mutualise(
    versement_dirigeant=10000, revenu_pro_dirigeant=80000,
    tmi_dirigeant=0.30, situation="Célibataire / divorcé / veuf",
    audit=t_sm,
)
codes_sm = set(t_sm.codes())

attendus_sm = {
    "PERIN_VERSEMENT_DIRIGEANT", "PERIN_REVENU_PRO_DIRIGEANT",
    "PERIN_TMI_DIRIGEANT", "PERIN_SITUATION_FAMILIALE",
    "PERIN_CONJOINT_DECLARE", "PERIN_REVENU_PRO_CONJOINT",
    "PERIN_MUTUALISATION_POSSIBLE", "PERIN_PLAFOND_TOTAL_RETENU",
    "PERIN_VERSEMENT_DIRIGEANT_COUVERT", "PERIN_VERSEMENT_EXCEDENT",
    "PERIN_ECONOMIE_IR", "PERIN_MUTUALISATION_ACTIVE",
}
check(f"12 codes méta attendus",
      attendus_sm.issubset(codes_sm),
      f"manquants={attendus_sm - codes_sm}")

# Une seule sous-trace
check("1 sous-trace 'plafond_dirigeant'",
      t_sm.noms_sous_traces() == ["plafond_dirigeant"])

# Mutualisation NON active
e_mut = t_sm.get("PERIN_MUTUALISATION_ACTIVE")
check("MUTUALISATION_ACTIVE.valeur == 0.0",
      e_mut.valeur == 0.0)
check("MUTUALISATION_ACTIVE.hypotheses['branche'] == 'sans_mutualisation'",
      e_mut.hypotheses.get("branche") == "sans_mutualisation")


# ============================================================
# TEST 4 — Structure calcul_perin_mutualise AVEC mutualisation
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Structure AVEC mutualisation (12 étapes + 2 sous-traces)")
print("=" * 95)

t_am = TraceAudit(regime="Avec mutualisation")
calcul_perin_mutualise(
    versement_dirigeant=20000, revenu_pro_dirigeant=80000,
    tmi_dirigeant=0.41, situation="Marié / pacsé",
    conjoint_declare=True, revenu_pro_conjoint=60000,
    versement_conjoint=3000,
    audit=t_am,
)
codes_am = set(t_am.codes())
check(f"12 codes méta attendus",
      attendus_sm.issubset(codes_am))

# 2 sous-traces
check("2 sous-traces 'plafond_dirigeant' + 'plafond_conjoint'",
      set(t_am.noms_sous_traces()) == {"plafond_dirigeant", "plafond_conjoint"})

# Chaque sous-trace contient 7 codes PERIN_*
for nom in ("plafond_dirigeant", "plafond_conjoint"):
    sub = t_am.get_sous_trace(nom)
    check(f"  {nom}: 7 étapes plates",
          len(sub.etapes) == 7)
    check(f"  {nom}: tous codes préfixés PERIN_",
          all(c.startswith("PERIN_") for c in sub.codes()))

# Mutualisation active
e_mut = t_am.get("PERIN_MUTUALISATION_ACTIVE")
check("MUTUALISATION_ACTIVE.valeur == 1.0",
      e_mut.valeur == 1.0)
check("PLAFOND_TOTAL_RETENU.hypotheses['branche'] == 'avec_mutualisation'",
      t_am.get("PERIN_PLAFOND_TOTAL_RETENU").hypotheses.get("branche")
      == "avec_mutualisation")


# ============================================================
# TEST 5 — Composition conditionnelle de plafond_conjoint
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Composition conditionnelle plafond_conjoint")
print("=" * 95)

# Marié + conjoint déclaré + revenu_pro_conjoint > 0 → plafond_conjoint attaché
t_c1 = TraceAudit(regime="Marié déclaré rev>0")
calcul_perin_mutualise(
    versement_dirigeant=10000, revenu_pro_dirigeant=80000, tmi_dirigeant=0.30,
    situation="Marié / pacsé", conjoint_declare=True,
    revenu_pro_conjoint=50000, audit=t_c1,
)
check("Cas mutualisation effective : plafond_conjoint attaché",
      "plafond_conjoint" in t_c1.noms_sous_traces())

# Marié + conjoint NON déclaré → pas de plafond_conjoint
t_c2 = TraceAudit(regime="Marié non déclaré")
calcul_perin_mutualise(
    versement_dirigeant=10000, revenu_pro_dirigeant=80000, tmi_dirigeant=0.30,
    situation="Marié / pacsé", conjoint_declare=False,
    revenu_pro_conjoint=50000, audit=t_c2,
)
check("Marié + conjoint non déclaré : pas de plafond_conjoint",
      "plafond_conjoint" not in t_c2.noms_sous_traces())

# Marié + conjoint déclaré + revenu_pro_conjoint == 0 → pas de plafond_conjoint
t_c3 = TraceAudit(regime="Marié déclaré rev=0")
calcul_perin_mutualise(
    versement_dirigeant=10000, revenu_pro_dirigeant=80000, tmi_dirigeant=0.30,
    situation="Marié / pacsé", conjoint_declare=True,
    revenu_pro_conjoint=0, audit=t_c3,
)
check("Marié + conjoint déclaré + rev=0 : pas de plafond_conjoint",
      "plafond_conjoint" not in t_c3.noms_sous_traces())

# Célibataire → pas de plafond_conjoint quelle que soit la suite
t_c4 = TraceAudit(regime="Célibataire avec conjoint forcé")
calcul_perin_mutualise(
    versement_dirigeant=10000, revenu_pro_dirigeant=80000, tmi_dirigeant=0.30,
    situation="Célibataire / divorcé / veuf",
    conjoint_declare=True, revenu_pro_conjoint=50000, audit=t_c4,
)
check("Célibataire : pas de plafond_conjoint",
      "plafond_conjoint" not in t_c4.noms_sous_traces())

# Vérif MUTUALISATION_POSSIBLE.hypotheses['condition']
e_cond = t_c1.get("PERIN_MUTUALISATION_POSSIBLE")
hyp_cond = e_cond.hypotheses.get("condition", "")
check("MUTUALISATION_POSSIBLE.hypotheses['condition'] documente la formule",
      "situation" in hyp_cond and "conjoint_declare" in hyp_cond
      and "revenu_pro_conjoint" in hyp_cond)


# ============================================================
# TEST 6 — Cas plancher 10% PASS
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Cas plancher 10% PASS (revenu très bas)")
print("=" * 95)

t_pla = TraceAudit(regime="Plancher")
r_pla = calcul_plafond_perin("Dirigeant", 1000, audit=t_pla)
check(f"plafond_individuel == {PERIN_PLAFOND_MIN} (plancher 10% PASS)",
      abs(r_pla.plafond_individuel - PERIN_PLAFOND_MIN) < TOL)
check("plafond_calcule (1000 × 10%) < plancher",
      abs(t_pla.get("PERIN_PLAFOND_CALCULE").valeur - 100.0) < TOL)
check("plafond_individuel = plafond_plancher (clamp inférieur appliqué)",
      abs(t_pla.get("PERIN_PLAFOND_INDIVIDUEL").valeur - PERIN_PLAFOND_MIN) < TOL)


# ============================================================
# TEST 7 — Cas plafond 8 PASS
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Cas plafond 8 PASS (revenu très haut)")
print("=" * 95)

t_max = TraceAudit(regime="Plafond max")
r_max = calcul_plafond_perin("Dirigeant", 5000000, audit=t_max)
check(f"plafond_individuel == {PERIN_PLAFOND_MAX} (plafond 8 PASS)",
      abs(r_max.plafond_individuel - PERIN_PLAFOND_MAX) < TOL)
check("plafond_calcule (5M × 10%) > plafond",
      t_max.get("PERIN_PLAFOND_CALCULE").valeur > PERIN_PLAFOND_MAX)
check("plafond_individuel = plafond_plafond (clamp supérieur appliqué)",
      abs(t_max.get("PERIN_PLAFOND_INDIVIDUEL").valeur - PERIN_PLAFOND_MAX) < TOL)


# ============================================================
# TEST 8 — Cas excédent (versement > plafond)
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Cas excédent (versement > plafond)")
print("=" * 95)

t_ex = TraceAudit(regime="Excédent")
r_ex = calcul_perin_mutualise(
    versement_dirigeant=50000, revenu_pro_dirigeant=80000,
    tmi_dirigeant=0.30, situation="Célibataire / divorcé / veuf",
    audit=t_ex,
)
check("versement_excedent > 0",
      r_ex.versement_excedent > 0)
e_exc = t_ex.get("PERIN_VERSEMENT_EXCEDENT")
check("PERIN_VERSEMENT_EXCEDENT.hypotheses['depasse_plafond'] == True",
      e_exc.hypotheses.get("depasse_plafond") is True)
check("versement_couvert <= plafond_individuel",
      r_ex.versement_dirigeant_couvert <= r_ex.plafond_dirigeant.plafond_individuel)


# ============================================================
# TEST 9 — Branche tracée dans hypotheses["branche"]
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Branche (sans/avec mutualisation) en hypotheses")
print("=" * 95)

# Sans mutualisation
e_sm = t_sm.get("PERIN_PLAFOND_TOTAL_RETENU")
check("Sans mutualisation: branche='sans_mutualisation'",
      e_sm.hypotheses.get("branche") == "sans_mutualisation")

# Avec mutualisation
e_am = t_am.get("PERIN_PLAFOND_TOTAL_RETENU")
check("Avec mutualisation: branche='avec_mutualisation'",
      e_am.hypotheses.get("branche") == "avec_mutualisation")


# ============================================================
# TEST 10 — Cohérence valeurs trace vs ResultatPERINMutualise
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Cohérence valeurs trace vs résultat")
print("=" * 95)

# Recalcul avec audit
t_coh = TraceAudit(regime="Cohérence")
r_coh = calcul_perin_mutualise(
    versement_dirigeant=20000, revenu_pro_dirigeant=80000,
    tmi_dirigeant=0.41, situation="Marié / pacsé",
    conjoint_declare=True, revenu_pro_conjoint=60000,
    versement_conjoint=3000, audit=t_coh,
)

mapping = {
    "PERIN_VERSEMENT_DIRIGEANT": "versement_dirigeant",
    "PERIN_TMI_DIRIGEANT": "tmi_dirigeant",
    "PERIN_PLAFOND_TOTAL_RETENU": "plafond_mutualise_total",
    "PERIN_VERSEMENT_DIRIGEANT_COUVERT": "versement_dirigeant_couvert",
    "PERIN_VERSEMENT_EXCEDENT": "versement_excedent",
    "PERIN_ECONOMIE_IR": "economie_ir",
}
for code, attr in mapping.items():
    v_trace = t_coh.get(code).valeur
    v_res = getattr(r_coh, attr)
    check(f"{code} ↔ res.{attr}",
          abs(v_trace - v_res) < TOL,
          f"trace={v_trace} res={v_res}")


# ============================================================
# TEST 11 — Test non-prescriptif RENFORCÉ
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Non-prescriptif RENFORCÉ G3e (14 patterns × tout le graphe)")
print("=" * 95)

traces = [t_pl, t_sm, t_am, t_c1, t_c2, t_c3, t_c4, t_pla, t_max, t_ex, t_coh]
total_etapes = sum(compter_etapes(t) for t in traces)
total_violations = 0
for trace_obj in traces:
    violations = scanner_prescriptif(trace_obj)
    total_violations += len(violations)
    if violations:
        for v in violations[:3]:
            print(f"     ⚠ {v[0]} / {v[1]} / {v[3]}: pattern={v[2]} dans {v[4]!r}")
check(f"0 violation sur {total_etapes} étapes × 14 patterns",
      total_violations == 0,
      f"obtenu {total_violations}")


# ============================================================
# TEST 12 — Isolation PERIN_* ⊥ {autres namespaces}
# ============================================================
print()
print("=" * 95)
print("  TEST 12 — Isolation PERIN_* ⊥ {STRAT_*, COMP_*, SYNTH_*, SCEN_*, régimes}")
print("=" * 95)

tous_codes = set()
for t in traces:
    tous_codes |= collecter_codes(t)
check(f"Tous codes préfixés PERIN_ ({len(tous_codes)} codes scannés)",
      all(c.startswith("PERIN_") for c in tous_codes))

prefixes_etrangers = ("STRAT_", "COMP_", "SYNTH_", "SCEN_", "RECEPT_",
                       "TNS_", "LIB_BNC_", "LIB_SEL_", "SAL_", "ASSIM_")
intrus = [c for c in tous_codes
          if any(c.startswith(p) for p in prefixes_etrangers)]
check("Aucune intrusion de préfixe étranger",
      not intrus, f"intrus={intrus}")


# ============================================================
# TEST 13 — Doctrine_refs PASS_2026 résolu
# ============================================================
print()
print("=" * 95)
print("  TEST 13 — Doctrine_refs se résolvent (PASS_2026)")
print("=" * 95)

refs_uniques = set()
def collecter_refs(t):
    for e in t.etapes:
        refs_uniques.update(e.doctrine_refs)
    for n in t.noms_sous_traces():
        collecter_refs(t.get_sous_trace(n))
for t in traces:
    collecter_refs(t)

check("PASS_2026 cité (constante doctrinale unique de perin.py)",
      "PASS_2026" in refs_uniques)
check(f"Toutes les doctrine_refs ({len(refs_uniques)}) se résolvent",
      all(resoudre_doctrine_ref(ref) is not None for ref in refs_uniques))


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Strategy/PERIN passent (G3f-perin)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
