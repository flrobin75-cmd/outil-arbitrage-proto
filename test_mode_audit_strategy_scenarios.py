"""
test_mode_audit_strategy_scenarios.py — Tests dédiés à l'instrumentation
MODE_AUDIT du strategy/scenarios (G3e-scenarios, spec 1.1.0).

Spécificités G3e-scenarios :
- **Namespace dédié `SCEN_*`** distinct de `SYNTH_*`, `COMP_*`, `COMP_REG_*`.
- **Module 100% autonome** : aucun import depuis un module instrumenté.
  Les sous-traces (`ir_barème`, `scenario_a`, `scenario_b`) sont des
  compositions internes au module.
- **Champ Python `gagnant`** ("A" / "B" / "égalité") préservé tel quel
  pour rétrocompat. Côté trace : `SCEN_SCENARIO_NET_LE_PLUS_ELEVE`
  factuel, avec `hypotheses["champ_source"] = "gagnant"`.
- **2 textes structurants** (`AVERTISSEMENT_SCENARIOS`, `MENTION_REGIMES`)
  préservés en hypotheses.
- **Discipline non-prescriptive renforcée** : 14 patterns scannés
  récursivement (12 base G3 + 2 renforcés G3e).

Vérifie :
1. Rétrocompat parfaite — 3 fonctions
2. Structure trace `_ir_barème_pur` (4 étapes plates)
3. Structure trace `_calcul_scenario` (méta + sous-trace ir_barème)
4. Structure trace `calcul_comparaison` (méta + 2 sous-traces scenario_a/b)
5. Composition correcte : `_calcul_scenario` attache `ir_barème`,
   `calcul_comparaison` attache `scenario_a` + `scenario_b`
6. Champ `gagnant` correctement préservé en `hypotheses["champ_source"]`
7. Textes structurants en `hypotheses` (jamais en label/notes)
8. Cas "égalité" tracé proprement
9. Cohérence valeurs trace vs ResultatComparaison
10. **Test non-prescriptif renforcé** (14 patterns × tout le graphe)
11. Isolation `SCEN_*` ⊥ {`SYNTH_*`, `COMP_*`, `STRAT_*`, régimes plats}
12. Résolution doctrinale (TX_TNS, TX_PFU, IR_PLAFOND_T1, etc.)

Usage : python3 test_mode_audit_strategy_scenarios.py
Exit code 0 si tous les tests passent.
"""

import sys
import re

from core.audit import (
    TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref,
)
from strategy.scenarios import (
    ScenarioInputs, _ir_barème_pur, _calcul_scenario, calcul_comparaison,
    AVERTISSEMENT_SCENARIOS, MENTION_REGIMES,
)


# ============================================================
# PATTERNS NON-PRESCRIPTIFS RENFORCÉS G3e
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
    # Renforcés G3e :
    r"\bprioritaire(?:s)?\b",
    r"\bprivilégi\w*\b",
]

CODES_META_ATTENDUS = {
    "SCEN_ECART_NET_TOTAL",
    "SCEN_ECART_POURCENT",
    "SCEN_CRITERE_CLASSEMENT",
    "SCEN_SCENARIO_NET_LE_PLUS_ELEVE",
    "SCEN_ECARTS_PROJECTION_NB",
    "SCEN_AVERTISSEMENT_SCENARIOS",
    "SCEN_MENTION_REGIMES",
}


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


# ============================================================
# TEST 1 — RÉTROCOMPAT 3 FONCTIONS
# ============================================================
print("=" * 95)
print("  TEST 1 — Rétrocompat parfaite (3 fonctions)")
print("=" * 95)

# 1.a _ir_barème_pur
ir_sans = _ir_barème_pur(50000, 2.0)
t = TraceAudit(regime="IR seul")
ir_avec = _ir_barème_pur(50000, 2.0, audit=t)
check("_ir_barème_pur : IR identique avec/sans audit",
      abs(ir_sans - ir_avec) < TOL)

# 1.b _calcul_scenario
s = ScenarioInputs(libelle="Test Assimilé", salaire_brut=100000,
                   dividendes_bruts=20000, epargne_salariale_per=5000,
                   peripheriques=2000)
r_sans = _calcul_scenario(s)
t = TraceAudit(regime="Scénario seul")
r_avec = _calcul_scenario(s, audit=t)
check("_calcul_scenario : ResultatScenario identique avec/sans audit",
      r_sans == r_avec)

# 1.c calcul_comparaison
s_a = ScenarioInputs(libelle="A salaire pur", salaire_brut=100000)
s_b = ScenarioInputs(libelle="B salaire+div", salaire_brut=80000,
                     dividendes_bruts=30000)
r_sans = calcul_comparaison(s_a, s_b)
trace = TraceAudit(regime="Comparaison A vs B")
r_avec = calcul_comparaison(s_a, s_b, audit=trace)
check("calcul_comparaison : ResultatComparaison identique avec/sans audit",
      r_sans == r_avec)


# ============================================================
# TEST 2 — Structure _ir_barème_pur
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure trace _ir_barème_pur")
print("=" * 95)

t_ir = TraceAudit(regime="IR test")
_ir_barème_pur(50000, 2.0, audit=t_ir)
codes_ir = set(t_ir.codes())

attendus_ir = {"SCEN_IR_REVENU_PAR_PART", "SCEN_IR_TRANCHE_ATTEINTE",
               "SCEN_IR_IR_PAR_PART", "SCEN_IR_IR_TOTAL"}
check("_ir_barème_pur : 4 codes attendus présents",
      attendus_ir.issubset(codes_ir),
      f"manquants={attendus_ir - codes_ir}")

# Valeur tranche atteinte
e_tranche = t_ir.get("SCEN_IR_TRANCHE_ATTEINTE")
check("SCEN_IR_TRANCHE_ATTEINTE : valeur est une string ('T1' à 'T5')",
      isinstance(e_tranche.valeur, str) and
      e_tranche.valeur in ["T1", "T2", "T3", "T4", "T5"])


# ============================================================
# TEST 3 — Structure _calcul_scenario
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Structure trace _calcul_scenario (méta + sous-trace ir_barème)")
print("=" * 95)

t_scen = TraceAudit(regime="Scénario test")
_calcul_scenario(s, audit=t_scen)
codes_scen = set(t_scen.codes())

attendus_scen = {
    "SCEN_LIBELLE",
    "SCEN_NET_SALAIRE_APRES_COTIS",
    "SCEN_REVENU_IMPOSABLE",
    "SCEN_IR_BAREME_RECUPERE",
    "SCEN_NET_SALAIRE_APRES_IR",
    "SCEN_NET_DIVIDENDES",
    "SCEN_NET_EPARGNE_SALARIALE",
    "SCEN_NET_PERIPHERIQUES",
    "SCEN_TOTAL_NET",
    "SCEN_RENDEMENT_COMPOSITE",
    "SCEN_PROJECTION_5_ANS_NB_VALEURS",
}
check(f"_calcul_scenario : {len(attendus_scen)} codes attendus présents",
      attendus_scen.issubset(codes_scen),
      f"manquants={attendus_scen - codes_scen}")

# Sous-trace ir_barème attachée
check("Sous-trace 'ir_barème' attachée",
      "ir_barème" in t_scen.noms_sous_traces())

# Préfixe de la sous-trace
sub_ir = t_scen.get_sous_trace("ir_barème")
if sub_ir:
    check("  Sous-trace ir_barème : codes préfixés SCEN_IR_",
          all(c.startswith("SCEN_IR_") for c in sub_ir.codes()))


# ============================================================
# TEST 4 — Structure calcul_comparaison
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Structure trace calcul_comparaison")
print("=" * 95)

codes_meta = set(trace.codes())
check(f"calcul_comparaison : {len(CODES_META_ATTENDUS)} codes méta attendus présents",
      codes_meta == CODES_META_ATTENDUS,
      f"manquants={CODES_META_ATTENDUS - codes_meta}, "
      f"extras={codes_meta - CODES_META_ATTENDUS}")

check("SCEN_SCENARIO_NET_LE_PLUS_ELEVE.parent_id = SCEN_CRITERE_CLASSEMENT",
      trace.get("SCEN_SCENARIO_NET_LE_PLUS_ELEVE").parent_id ==
      "SCEN_CRITERE_CLASSEMENT")


# ============================================================
# TEST 5 — Composition (scenario_a + scenario_b)
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Composition : 2 sous-traces scenario_a / scenario_b")
print("=" * 95)

noms_lvl1 = set(trace.noms_sous_traces())
check("Sous-traces 'scenario_a' et 'scenario_b' attachées",
      {"scenario_a", "scenario_b"}.issubset(noms_lvl1),
      f"obtenu {noms_lvl1}")

# Chaque sous-trace doit elle-même contenir une sous-sous-trace 'ir_barème'
for nom_scenario in ("scenario_a", "scenario_b"):
    sub = trace.get_sous_trace(nom_scenario)
    check(f"  {nom_scenario} : sous-trace 'ir_barème' attachée",
          sub is not None and "ir_barème" in sub.noms_sous_traces())


# ============================================================
# TEST 6 — Champ "gagnant" en hypotheses, jamais en label/notes
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Champ Python 'gagnant' en hypotheses['champ_source']")
print("=" * 95)

e_top = trace.get("SCEN_SCENARIO_NET_LE_PLUS_ELEVE")
check("SCEN_SCENARIO_NET_LE_PLUS_ELEVE.hypotheses['champ_source'] == 'gagnant'",
      e_top.hypotheses.get("champ_source") == "gagnant")
check("  Valeur de l'étape = nom du scénario (A / B / égalité)",
      e_top.valeur in ("A", "B", "égalité"))
check("  Valeurs possibles tracées en hypotheses",
      e_top.hypotheses.get("valeurs_possibles") == ["A", "B", "égalité"])


# ============================================================
# TEST 7 — Textes structurants en hypotheses (jamais label/notes)
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — AVERTISSEMENT_SCENARIOS + MENTION_REGIMES en hypotheses")
print("=" * 95)

e_av = trace.get("SCEN_AVERTISSEMENT_SCENARIOS")
check("AVERTISSEMENT_SCENARIOS texte intégral en hypotheses",
      e_av.hypotheses.get("AVERTISSEMENT_SCENARIOS") == AVERTISSEMENT_SCENARIOS)

e_mr = trace.get("SCEN_MENTION_REGIMES")
check("MENTION_REGIMES texte intégral en hypotheses",
      e_mr.hypotheses.get("MENTION_REGIMES") == MENTION_REGIMES)

# Pas de fragment des textes en label/notes
for e in (e_av, e_mr):
    for fragment in ("cadrage stratégique", "Comparateur 2 scénarios",
                      "conformité renforcée", "4 régimes"):
        check(f"  Fragment {fragment!r} absent du label de {e.code}",
              fragment not in e.label)
        check(f"  Fragment {fragment!r} absent des notes de {e.code}",
              fragment not in e.notes)


# ============================================================
# TEST 8 — Cas "égalité" tracé proprement
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Cas 'égalité' (scénarios identiques)")
print("=" * 95)

s_a_id = ScenarioInputs(libelle="A identique", salaire_brut=100000)
s_b_id = ScenarioInputs(libelle="B identique", salaire_brut=100000)
t_eg = TraceAudit(regime="Égalité")
r_eg = calcul_comparaison(s_a_id, s_b_id, audit=t_eg)

check("Cas égalité : gagnant = 'égalité' dans le résultat",
      r_eg.gagnant == "égalité")
e_top_eg = t_eg.get("SCEN_SCENARIO_NET_LE_PLUS_ELEVE")
check("Cas égalité : valeur trace = 'égalité'",
      e_top_eg.valeur == "égalité")
check("Cas égalité : écart total ≈ 0",
      abs(r_eg.ecart_total) < 0.01)


# ============================================================
# TEST 9 — Cohérence valeurs trace vs ResultatComparaison
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Cohérence valeurs trace vs résultat")
print("=" * 95)

mapping = {
    "SCEN_ECART_NET_TOTAL": "ecart_total",
    "SCEN_ECART_POURCENT": "ecart_pourcent",
}
for code, attr in mapping.items():
    v_trace = trace.get(code).valeur
    v_res = getattr(r_avec, attr)
    check(f"{code} ↔ res.{attr}",
          abs(v_trace - v_res) < TOL,
          f"trace={v_trace} res={v_res}")

# SCENARIO_NET_LE_PLUS_ELEVE.valeur == résultat.gagnant
check("SCEN_SCENARIO_NET_LE_PLUS_ELEVE.valeur == résultat.gagnant",
      trace.get("SCEN_SCENARIO_NET_LE_PLUS_ELEVE").valeur == r_avec.gagnant)


# ============================================================
# TEST 10 — Test non-prescriptif RENFORCÉ
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Non-prescriptif RENFORCÉ G3e (14 patterns × graphe complet)")
print("=" * 95)

total_etapes = compter_etapes(trace)
violations = scanner_prescriptif(trace)
if violations:
    for v in violations[:10]:
        print(f"     ⚠ {v[0]} / {v[1]} / {v[3]}: pattern={v[2]} dans {v[4]!r}")
check(f"0 violation sur {total_etapes} étapes × 14 patterns",
      len(violations) == 0,
      f"obtenu {len(violations)}")


# ============================================================
# TEST 11 — Isolation namespaces
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Isolation SCEN_* ⊥ {SYNTH_*, COMP_*, STRAT_*, régimes}")
print("=" * 95)

# Collecter tous les codes du graphe complet
def collecter_codes(t):
    codes = set(t.codes())
    for nom in t.noms_sous_traces():
        codes |= collecter_codes(t.get_sous_trace(nom))
    return codes

tous_codes = collecter_codes(trace)
check(f"Tous codes préfixés SCEN_ ({len(tous_codes)} codes scannés)",
      all(c.startswith("SCEN_") for c in tous_codes))

prefixes_etrangers = ("SYNTH_", "COMP_", "STRAT_", "TNS_", "LIB_BNC_",
                       "LIB_SEL_", "SAL_", "ASSIM_")
intrus = [c for c in tous_codes
          if any(c.startswith(p) for p in prefixes_etrangers)]
check("Aucune intrusion de préfixe étranger",
      not intrus, f"intrus={intrus}")


# ============================================================
# TEST 12 — Résolution doctrinale
# ============================================================
print()
print("=" * 95)
print("  TEST 12 — Doctrine_refs se résolvent (graphe complet)")
print("=" * 95)

refs_uniques = set()
def collecter_refs(t):
    for e in t.etapes:
        refs_uniques.update(e.doctrine_refs)
    for n in t.noms_sous_traces():
        collecter_refs(t.get_sous_trace(n))
collecter_refs(trace)

check(f"{len(refs_uniques)} doctrine_refs uniques cités dans le graphe",
      len(refs_uniques) >= 8)

# Refs minimales attendues
attendus_min = {"IR_PLAFOND_T1", "IR_PLAFOND_T2", "IR_TAUX_T2", "IR_TAUX_T3",
                 "TX_PFU", "TX_IS_REDUIT", "TX_IS_NORMAL"}
check("Refs minimales présentes (IR, IS, PFU)",
      attendus_min.issubset(refs_uniques),
      f"manquantes={attendus_min - refs_uniques}")

erreurs = []
for ref in sorted(refs_uniques):
    try:
        resoudre_doctrine_ref(ref)
    except AttributeError as e:
        erreurs.append((ref, str(e)))
check(f"Toutes les doctrine_refs ({len(refs_uniques)}) se résolvent",
      not erreurs,
      f"échecs={erreurs}")


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Strategy/Scenarios passent (G3e-scenarios)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
