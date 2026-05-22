"""
test_mode_audit_strategy_synthese.py — Tests dédiés à l'instrumentation
MODE_AUDIT du strategy/synthese (G3e, spec 1.1.0).

Spécificités G3e-synthese :
- **Namespace dédié `SYNTH_*`** distinct des comparateurs (G3d/G3d-bis).
- **Module multi-fonctions diversifié** : 7 fonctions instrumentées
  + 4 sous-fonctions régime + 1 routeur, chacune avec une nature
  différente (coûts, scoring, projection, waterfall, enveloppes,
  checklist, dispatch).
- **Composition naturelle G3a-G3d-bis confirmée** : `_synthese_assimile`
  compose les 6 sous-traces internes (couts, radar, projection,
  decomposition, enveloppes, checklist), `_synthese_salarie` compose
  `module_salarie`. `_synthese_tns/liberal` sont à trace plate
  (implémentation allégée v1, pas d'appel aux fonctions
  G3e-synthese.1-3).
- **Discipline non-prescriptive renforcée** : G3e a introduit 2 patterns
  supplémentaires (`prioritaire`, `privilégi`). Le test 9 renforcé
  scanne label + notes sur 14 patterns.
- **Champs Python à wording orienté** préservés tels quels pour
  rétrocompat (`meilleure` dans `calcul_enveloppes_patrimoniales`),
  côté trace toujours en `SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE`.

Vérifie :
1. Rétrocompat parfaite — 7 fonctions + routeur + 4 régimes
2. Structure trace `calcul_couts_mise_en_oeuvre` (5 inputs + NB_POSTES + postes + TOTAL)
3. Structure trace `calcul_radar_6d` (4 racines + 6 axes × 4 stratégies)
4. Structure trace `calcul_projection_5_ans` (4 racines + années × 3 + GAIN)
5. Structure trace `calcul_decomposition_gain` (NB_ETAPES + 4 étapes ABCD)
6. Structure trace `calcul_enveloppes_patrimoniales` (terminologie NET_LE_PLUS_ELEVE)
7. Structure trace `calcul_checklist_conformite` (catégoriel, pas de scoring)
8. Structure trace `calcul_synthese` (routeur dispatch)
9. Composition correcte `_synthese_assimile` (6 sous-traces)
10. Composition correcte `_synthese_salarie` (sous-trace `module_salarie`)
11. Garde-fou T4 transversal `SYNTH_TNS_INDICATEURS_SEPARES_T4`
12. **Test non-prescriptif renforcé** (14 patterns × tout le graphe)
13. Isolation `SYNTH_*` ⊥ `COMP_*` ⊥ `COMP_REG_*` ⊥ `STRAT_*`
14. Résolution doctrinale + spec 1.1.0

Usage : python3 test_mode_audit_strategy_synthese.py
Exit code 0 si tous les tests passent.
"""

import sys
import re
import copy

from core.profil import Profil
from core.audit import (
    TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref,
)
from strategy.synthese import (
    reset_forfaits, calcul_couts_mise_en_oeuvre,
    calcul_radar_6d, calcul_projection_5_ans, calcul_decomposition_gain,
    calcul_enveloppes_patrimoniales, calcul_checklist_conformite,
    calcul_synthese,
    _synthese_assimile, _synthese_tns, _synthese_liberal, _synthese_salarie,
    FORFAITS_DEFAUT,
)
from strategy.comparateur import ConfigComparateur, AlertePlafond


# ============================================================
# PATTERNS NON-PRESCRIPTIFS RENFORCÉS G3e (12 base + 2 renforcés)
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
# DONNÉES DE TEST
# ============================================================
def strategies_assim_factices():
    return {
        "A": {"total_net": 80000, "cout_total": 150000,
              "net_salaire": 80000, "net_dividendes": 0, "net_epargne": 0,
              "net_peripheriques": 0, "cout_salaire": 150000,
              "cout_dividendes": 0, "cout_epargne": 0, "cout_peripheriques": 0,
              "net_pero": 0, "net_cashback": 0},
        "B": {"total_net": 85000, "cout_total": 150000,
              "net_salaire": 60000, "net_dividendes": 25000, "net_epargne": 0,
              "net_peripheriques": 0, "cout_salaire": 110000,
              "cout_dividendes": 40000, "cout_epargne": 0, "cout_peripheriques": 0,
              "net_pero": 0, "net_cashback": 0},
        "C": {"total_net": 90000, "cout_total": 150000,
              "net_salaire": 50000, "net_dividendes": 20000, "net_epargne": 20000,
              "net_peripheriques": 0, "cout_salaire": 90000,
              "cout_dividendes": 30000, "cout_epargne": 30000, "cout_peripheriques": 0,
              "net_pero": 0, "net_cashback": 0},
        "D": {"total_net": 95000, "cout_total": 150000,
              "net_salaire": 50000, "net_dividendes": 20000, "net_epargne": 20000,
              "net_peripheriques": 5000, "cout_salaire": 90000,
              "cout_dividendes": 30000, "cout_epargne": 30000, "cout_peripheriques": 5000,
              "net_pero": 0, "net_cashback": 1500},
    }


# ============================================================
# TEST 1 — RÉTROCOMPAT 7 FONCTIONS + ROUTEUR + 4 RÉGIMES
# ============================================================
print("=" * 95)
print("  TEST 1 — Rétrocompat parfaite (7 fonctions + routeur + 4 régimes)")
print("=" * 95)

profil_assim = Profil(forme_juridique="SAS / SASU")
config = ConfigComparateur()
strats = strategies_assim_factices()

# 1.a calcul_couts_mise_en_oeuvre
for strat in ["A", "B", "C", "D"]:
    f1 = copy.deepcopy(FORFAITS_DEFAUT)
    r_sans = calcul_couts_mise_en_oeuvre(profil_assim, strat, f1, config)
    f2 = copy.deepcopy(FORFAITS_DEFAUT)
    t = TraceAudit(regime=f"Couts {strat}")
    r_avec = calcul_couts_mise_en_oeuvre(profil_assim, strat, f2, config, audit=t)
    check(f"calcul_couts_mise_en_oeuvre stratégie {strat}", r_sans == r_avec)

# 1.b calcul_radar_6d
r_sans = calcul_radar_6d(strats)
t = TraceAudit(regime="Radar")
r_avec = calcul_radar_6d(strats, audit=t)
check("calcul_radar_6d", r_sans == r_avec)

# 1.c calcul_projection_5_ans
r_sans = calcul_projection_5_ans(strats, "C")
t = TraceAudit(regime="Projection")
r_avec = calcul_projection_5_ans(strats, "C", audit=t)
check("calcul_projection_5_ans", r_sans == r_avec)

# 1.d calcul_decomposition_gain
r_sans = calcul_decomposition_gain(strats)
t = TraceAudit(regime="Décomposition")
r_avec = calcul_decomposition_gain(strats, audit=t)
check("calcul_decomposition_gain", r_sans == r_avec)

# 1.e calcul_enveloppes_patrimoniales
r_sans = calcul_enveloppes_patrimoniales()
t = TraceAudit(regime="Enveloppes")
r_avec = calcul_enveloppes_patrimoniales(audit=t)
check("calcul_enveloppes_patrimoniales", r_sans == r_avec)

# 1.f calcul_checklist_conformite
r_sans = calcul_checklist_conformite(profil_assim, config, "A", [])
t = TraceAudit(regime="Checklist A")
r_avec = calcul_checklist_conformite(profil_assim, config, "A", [], audit=t)
check("calcul_checklist_conformite stratégie A", r_sans == r_avec)

# 1.g calcul_synthese routeur — 4 régimes
trace_assim = TraceAudit(regime="Routeur Assimilé")
r_sans = calcul_synthese(profil_assim, strats, config)
r_avec = calcul_synthese(profil_assim, strats, config, audit=trace_assim)
check("calcul_synthese Assimilé", r_sans == r_avec)

# TNS
from strategy.tns import arbitrage_complet_tns
profil_tns = Profil(forme_juridique="SARL (gérance majoritaire) / EURL")
arb_tns = arbitrage_complet_tns(profil_tns)
trace_tns = TraceAudit(regime="Routeur TNS")
r_sans = calcul_synthese(profil_tns, arb_tns.strategies, config)
r_avec = calcul_synthese(profil_tns, arb_tns.strategies, config, audit=trace_tns)
check("calcul_synthese TNS", r_sans == r_avec)

# Libéral
from strategy.liberal import arbitrage_complet_liberal
profil_lib = Profil(forme_juridique="SELARL / SELAS")
arb_lib = arbitrage_complet_liberal(profil_lib)
trace_lib = TraceAudit(regime="Routeur Libéral")
r_sans = calcul_synthese(profil_lib, arb_lib.strategies, config)
r_avec = calcul_synthese(profil_lib, arb_lib.strategies, config, audit=trace_lib)
check("calcul_synthese Libéral", r_sans == r_avec)

# Salarié (test direct _synthese_salarie)
trace_sal = TraceAudit(regime="_synthese_salarie direct")
r_sans = _synthese_salarie(profil_assim, strats, config)
r_avec = _synthese_salarie(profil_assim, strats, config, audit=trace_sal)
check("_synthese_salarie", r_sans == r_avec)


# ============================================================
# TEST 2 — Structure calcul_couts_mise_en_oeuvre
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure trace calcul_couts_mise_en_oeuvre")
print("=" * 95)

f = copy.deepcopy(FORFAITS_DEFAUT)
tD = TraceAudit(regime="Couts D")
calcul_couts_mise_en_oeuvre(profil_assim, "D", f, config, audit=tD)
codes_couts_D = set(tD.codes())

inputs_attendus = {
    "SYNTH_COUTS_STRATEGIE_RETENUE",
    "SYNTH_COUTS_NB_FORFAITS_DISPONIBLES",
    "SYNTH_COUTS_NB_FORFAITS_ACTIFS",
    "SYNTH_COUTS_CONFIG_COMPARATEUR_PRESENTE",
    "SYNTH_COUTS_EFFECTIF_PROFIL",
}
check("Stratégie D : 5 codes inputs présents",
      inputs_attendus.issubset(codes_couts_D),
      f"manquants={inputs_attendus - codes_couts_D}")
check("Stratégie D : SYNTH_COUTS_NB_POSTES_RETENUS présent",
      "SYNTH_COUTS_NB_POSTES_RETENUS" in codes_couts_D)
check("Stratégie D : SYNTH_COUTS_TOTAL présent",
      "SYNTH_COUTS_TOTAL" in codes_couts_D)
check("Stratégie D : au moins 1 poste tracé",
      any(c.startswith("SYNTH_COUTS_POSTE_") for c in codes_couts_D))


# ============================================================
# TEST 3 — Structure calcul_radar_6d (6 axes × 4 stratégies)
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Structure calcul_radar_6d (6 axes × 4 stratégies)")
print("=" * 95)

t_radar = TraceAudit(regime="Radar")
calcul_radar_6d(strats, audit=t_radar)
codes_radar = set(t_radar.codes())

# Racines
racines_radar = {"SYNTH_RADAR_NB_AXES", "SYNTH_RADAR_NOTE_INTRA_REGIME",
                 "SYNTH_RADAR_NB_STRATEGIES", "SYNTH_RADAR_NET_MAX_REFERENCE"}
check("Radar : 4 racines présentes (NB_AXES, NOTE_INTRA_REGIME, NB_STRATEGIES, NET_MAX_REFERENCE)",
      racines_radar.issubset(codes_radar),
      f"manquantes={racines_radar - codes_radar}")

# 6 axes × 4 stratégies = 24 codes
axes = ["NET_DIRIGEANT", "PROTECTION_SOCIALE", "FISCALITE",
        "PREPARATION_RETRAITE", "LIQUIDITE", "MAITRISE_CHARGES"]
for axe in axes:
    codes_axe = {c for c in codes_radar
                 if c.startswith(f"SYNTH_RADAR_{axe}_")}
    check(f"  Axe {axe} : 4 stratégies tracées",
          len(codes_axe) == 4,
          f"obtenu {len(codes_axe)} : {codes_axe}")

# Vérif NB_AXES = 6
e_nb = t_radar.get("SYNTH_RADAR_NB_AXES")
check("SYNTH_RADAR_NB_AXES.valeur == 6.0",
      abs(e_nb.valeur - 6.0) < TOL)

# Vérif PONDS_PROTECTION en hypotheses
e_prot_A = t_radar.get("SYNTH_RADAR_PROTECTION_SOCIALE_A")
check("PROTECTION_SOCIALE_A.hypotheses contient PONDS_PROTECTION",
      "PONDS_PROTECTION" in e_prot_A.hypotheses)


# ============================================================
# TEST 4 — Structure calcul_projection_5_ans
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Structure calcul_projection_5_ans (5 années × 3 + gain)")
print("=" * 95)

t_proj = TraceAudit(regime="Projection")
calcul_projection_5_ans(strats, "C", audit=t_proj)
codes_proj = set(t_proj.codes())

racines_proj = {"SYNTH_PROJECTION_CODE_RETENUE",
                "SYNTH_PROJECTION_RDT_CASH",
                "SYNTH_PROJECTION_RDT_EPARGNE",
                "SYNTH_PROJECTION_NB_ANNEES",
                "SYNTH_PROJECTION_GAIN_5_ANS"}
check("Projection : 5 racines présentes",
      racines_proj.issubset(codes_proj))

# 5 années × 3 valeurs (A, RETENUE, ECART)
for annee in range(1, 6):
    for suffixe in ["A", "RETENUE", f"ECART_ANNEE_{annee}"]:
        if suffixe in ("A", "RETENUE"):
            code = f"SYNTH_PROJECTION_ANNEE_{annee}_{suffixe}"
        else:
            code = f"SYNTH_PROJECTION_{suffixe}"
        check(f"  {code} présent", code in codes_proj)


# ============================================================
# TEST 5 — Structure calcul_decomposition_gain (waterfall)
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Structure calcul_decomposition_gain (NB_ETAPES + 4 étapes ABCD)")
print("=" * 95)

t_decomp = TraceAudit(regime="Décomposition")
calcul_decomposition_gain(strats, audit=t_decomp)
codes_decomp = set(t_decomp.codes())

check("SYNTH_DECOMPOSITION_NB_ETAPES présent",
      "SYNTH_DECOMPOSITION_NB_ETAPES" in codes_decomp)
for idx, code in enumerate(["A", "B", "C", "D"]):
    c = f"SYNTH_DECOMPOSITION_ETAPE_{idx}_{code}"
    check(f"  {c} présent", c in codes_decomp)

# Libellés source en hypotheses
e_nb = t_decomp.get("SYNTH_DECOMPOSITION_NB_ETAPES")
check("Libellés source en hypotheses",
      "libelles_source" in e_nb.hypotheses)


# ============================================================
# TEST 6 — Structure calcul_enveloppes_patrimoniales (terminologie factuelle)
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Structure enveloppes (terminologie NET_LE_PLUS_ELEVE)")
print("=" * 95)

t_env = TraceAudit(regime="Enveloppes")
calcul_enveloppes_patrimoniales(audit=t_env)
codes_env = set(t_env.codes())

check("SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE présent (terminologie factuelle)",
      "SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE" in codes_env)
check("Aucun code contenant MEILLEUR",
      not any("MEILLEUR" in c.upper() for c in codes_env))
check("SYNTH_ENV_CRITERE_CLASSEMENT présent",
      "SYNTH_ENV_CRITERE_CLASSEMENT" in codes_env)
check("SYNTH_ENV_NB_ENVELOPPES présent",
      "SYNTH_ENV_NB_ENVELOPPES" in codes_env)
check("4 enveloppes tracées",
      sum(1 for c in codes_env if c.startswith("SYNTH_ENV_NET_DISPONIBLE_")) == 4)

# Vérif que la valeur est bien le nom (factuel), pas "meilleure"
e_top = t_env.get("SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE")
check("Valeur = nom d'enveloppe (string factuel)",
      isinstance(e_top.valeur, str) and "—" in e_top.valeur)


# ============================================================
# TEST 7 — Structure calcul_checklist_conformite (catégoriel, descriptif)
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Structure checklist (catégoriel, descriptif)")
print("=" * 95)

# Stratégie A : 1 point unique
tA = TraceAudit(regime="Checklist A")
calcul_checklist_conformite(profil_assim, config, "A", [], audit=tA)
codes_chA = set(tA.codes())
check("Stratégie A : 3 étapes",
      len(tA.etapes) == 3,
      f"obtenu {len(tA.etapes)}")
check("SYNTH_CHECKLIST_POINT_00_STRATEGIE_A présent",
      "SYNTH_CHECKLIST_POINT_00_STRATEGIE_A" in codes_chA)

# Stratégie D avec dispositifs + alertes
config_d = ConfigComparateur()
config_d.interessement.actif = True
config_d.participation.actif = True
config_d.abondement_pee.actif = True
alertes = [
    AlertePlafond(severite="warning", titre="Plafond test", message="msg"),
    AlertePlafond(severite="error", titre="Plafond critical", message="msg"),
]
tD = TraceAudit(regime="Checklist D")
calcul_checklist_conformite(profil_assim, config_d, "D", alertes, audit=tD)
codes_chD = set(tD.codes())

check("Stratégie D : NB_POINTS_TOTAL présent",
      "SYNTH_CHECKLIST_NB_POINTS_TOTAL" in codes_chD)
check("Stratégie D : NB_POINTS_PAR_STATUT présent",
      "SYNTH_CHECKLIST_NB_POINTS_PAR_STATUT" in codes_chD)

# Au moins 1 alerte Comparateur + 1 check v19
check("Alertes Comparateur tracées",
      any("ALERTE_COMP" in c for c in codes_chD))
check("Checks v19 tracés",
      any("EFFECTIF_PARTICIPATION" in c or "ACCORD_INTERESSEMENT" in c
          or "REGLEMENT_PEE" in c for c in codes_chD))

# Vérifier que les valeurs sont les statuts catégoriels (string), pas des scores
for c in codes_chD:
    if c.startswith("SYNTH_CHECKLIST_POINT_"):
        e = tD.get(c)
        check(f"  {c}.valeur est un statut catégoriel",
              isinstance(e.valeur, str) and e.valeur in ["✅", "⚠", "🔴", "-"])


# ============================================================
# TEST 8 — Structure calcul_synthese (routeur dispatch)
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Structure calcul_synthese (routeur dispatch)")
print("=" * 95)

# Vérif SYNTH_REGIME_DISPATCH dans les 4 traces
for trace_obj, regime_attendu, fonction_attendue in (
    (trace_assim, "Assimilé salarié", "_synthese_assimile"),
    (trace_tns, "TNS", "_synthese_tns"),
    (trace_lib, "TNS (libéral)", "_synthese_liberal"),
):
    check(f"SYNTH_REGIME_DISPATCH présent ({regime_attendu})",
          "SYNTH_REGIME_DISPATCH" in trace_obj.codes())
    e = trace_obj.get("SYNTH_REGIME_DISPATCH")
    if e:
        check(f"  valeur = {fonction_attendue}",
              e.valeur == fonction_attendue)

# Sous-trace synthese_<regime> attachée
check("Assimilé : sous-trace 'synthese_assimile' attachée",
      "synthese_assimile" in trace_assim.noms_sous_traces())
check("TNS : sous-trace 'synthese_tns' attachée",
      "synthese_tns" in trace_tns.noms_sous_traces())
check("Libéral : sous-trace 'synthese_liberal' attachée",
      "synthese_liberal" in trace_lib.noms_sous_traces())


# ============================================================
# TEST 9 — Composition _synthese_assimile (6 sous-traces)
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Composition _synthese_assimile (6 sous-traces internes)")
print("=" * 95)

st_assim = trace_assim.get_sous_trace("synthese_assimile")
sous_traces_assim = set(st_assim.noms_sous_traces())
attendues = {"couts", "radar", "projection", "decomposition",
             "enveloppes", "checklist"}
check(f"6 sous-traces attendues présentes ({attendues})",
      attendues.issubset(sous_traces_assim),
      f"obtenu {sous_traces_assim}")

# Vérif préfixes des sous-traces
verifs = {
    "couts": "SYNTH_COUTS_",
    "radar": "SYNTH_RADAR_",
    "projection": "SYNTH_PROJECTION_",
    "decomposition": "SYNTH_DECOMPOSITION_",
    "enveloppes": "SYNTH_ENV_",
    "checklist": "SYNTH_CHECKLIST_",
}
for nom, prefixe in verifs.items():
    sub = st_assim.get_sous_trace(nom)
    if sub:
        check(f"  {nom}: codes préfixés {prefixe}",
              all(c.startswith(prefixe) for c in sub.codes()))


# ============================================================
# TEST 10 — Composition _synthese_salarie (sous-trace module_salarie)
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Composition _synthese_salarie (sous-trace module_salarie)")
print("=" * 95)

t_sal = TraceAudit(regime="Synthese Salarié")
_synthese_salarie(profil_assim, strats, config, audit=t_sal)
check("Sous-trace 'module_salarie' attachée",
      "module_salarie" in t_sal.noms_sous_traces())
sub_sal = t_sal.get_sous_trace("module_salarie")
if sub_sal:
    check("  codes préfixés SAL_",
          all(c.startswith("SAL_") for c in sub_sal.codes()))


# ============================================================
# TEST 11 — Garde-fou T4 transversal
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Garde-fou T4 transversal (SYNTH_TNS_INDICATEURS_SEPARES_T4)")
print("=" * 95)

st_tns = trace_tns.get_sous_trace("synthese_tns")
codes_tns = set(st_tns.codes()) if st_tns else set()
check("SYNTH_TNS_INDICATEURS_SEPARES_T4 présent",
      "SYNTH_TNS_INDICATEURS_SEPARES_T4" in codes_tns)

if "SYNTH_TNS_INDICATEURS_SEPARES_T4" in codes_tns:
    e_t4 = st_tns.get("SYNTH_TNS_INDICATEURS_SEPARES_T4")
    check("  hypothèses contiennent 'convention' = 'non-agrégation T4'",
          "non-agrégation T4" in e_t4.hypotheses.get("convention", ""))
    check("  hypothèses contiennent règle 'Ne PAS sommer'",
          "Ne PAS sommer" in e_t4.hypotheses.get("regle", ""))


# ============================================================
# TEST 12 — Test non-prescriptif RENFORCÉ G3e (14 patterns × tout graphe)
# ============================================================
print()
print("=" * 95)
print("  TEST 12 — Non-prescriptif RENFORCÉ G3e (14 patterns × tout le graphe)")
print("=" * 95)

total_etapes = 0
total_violations = 0
for trace_obj in [trace_assim, trace_tns, trace_lib, t_sal]:
    n = compter_etapes(trace_obj)
    total_etapes += n
    violations = scanner_prescriptif(trace_obj)
    total_violations += len(violations)
    if violations:
        for v in violations[:5]:
            print(f"     ⚠ {v[0]} / {v[1]} / {v[3]}: pattern={v[2]} dans {v[4]!r}")

check(f"0 violation sur {total_etapes} étapes × 14 patterns",
      total_violations == 0,
      f"obtenu {total_violations}")


# ============================================================
# TEST 13 — Isolation namespaces SYNTH_* ⊥ COMP_* ⊥ STRAT_*
# ============================================================
print()
print("=" * 95)
print("  TEST 13 — Isolation SYNTH_* ⊥ {COMP_*, COMP_REG_*, STRAT_*, régimes plats}")
print("=" * 95)

# Sur trace Assimilé (la plus riche), les étapes du graphe synthese.py
# doivent être en SYNTH_* uniquement. Les codes des modules amont
# (SAL_*, TNS_*, etc.) vivent dans les sous-traces propagées
# correctement (G3a-G3d-bis).

# Au niveau racine de l'Assimilé, uniquement SYNTH_REGIME_DISPATCH
check("Racine routeur : 1 seul code (SYNTH_REGIME_DISPATCH)",
      len(trace_assim.etapes) == 1 and
      trace_assim.codes() == ["SYNTH_REGIME_DISPATCH"])

# Dans synthese_assimile : tous les codes plats sont en SYNTH_ASSIM_*
codes_plats_assim = set(st_assim.codes())
prefixes_etrangers = ("COMP_", "STRAT_", "TNS_", "LIB_BNC_", "LIB_SEL_",
                      "SAL_", "ASSIM_")
intrus = [c for c in codes_plats_assim
          if any(c.startswith(p) for p in prefixes_etrangers)]
check("synthese_assimile : aucun code étranger à plat",
      not intrus, f"intrus={intrus}")

# Tous les codes plats de synthese_assimile préfixés SYNTH_ASSIM_
check("synthese_assimile : tous codes préfixés SYNTH_ASSIM_",
      all(c.startswith("SYNTH_ASSIM_") for c in codes_plats_assim))


# ============================================================
# TEST 14 — Spec version 1.1.0
# ============================================================
print()
print("=" * 95)
print("  TEST 14 — Spec version 1.1.0")
print("=" * 95)

check(f"AUDIT_SPEC_VERSION = 1.1.0",
      AUDIT_SPEC_VERSION == "1.1.0")
check("Trace Assimilé.spec_version = 1.1.0",
      trace_assim.spec_version == "1.1.0")
for nom in trace_assim.noms_sous_traces():
    sub = trace_assim.get_sous_trace(nom)
    check(f"  Sous-trace '{nom}'.spec_version = 1.1.0",
          sub.spec_version == "1.1.0")


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Strategy/Synthese passent (G3e-synthese)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
