"""
test_mode_audit_strategy_tns.py — Tests dédiés à l'instrumentation
MODE_AUDIT du strategy/tns (G3b, spec 1.1.0).

Spécificités G3b :
- Premier usage des **sous-traces imbriquées sur 2 niveaux** :
    arbitrage_complet_tns (méta)
    ├── strategie_T<X>        (sous-trace stratégie)
    │     └── module_tns      (sous-sous-trace régime, codes TNS_*)
- 4 stratégies T1/T2/T3/T4 avec logiques très différentes (assertion
  stricte T2, convention de non-agrégation T4, calcul PERIN T3).
- Textes d'alertes métier conservés en `hypotheses` (non-prescriptif).
- Indicateur séparé T4 explicitement tracé au niveau méta.

Vérifie :
1. Rétrocompat parfaite des 4 stratégies + arbitrage_complet_tns
2. Structure trace méta (codes STRAT_TNS_*, deltas, critère, retenu)
3. Structure trace stratégie pour chaque T1/T2/T3/T4
4. Sous-traces imbriquées 2 niveaux (strategie_T<X> → module_tns)
5. Aucune duplication, aucune collision (STRAT_TNS_* ⊥ TNS_*)
6. Convention non-agrégation T4 : indicateurs séparés
7. Résolution doctrinale sur tout le graphe
8. Texte d'alertes T2 préservé en hypotheses (non scanné par test 9)
9. **Test non-prescriptif** : 0 wording prescriptif dans labels/notes
10. Rendu console complet
11. Isolation espaces de codes STRAT_TNS_* ⊥ STRAT_ASSIM_*

Usage : python3 test_mode_audit_strategy_tns.py
Exit code 0 si tous les tests passent.
"""

import sys
import re

from core.profil import Profil
from core.audit import (
    TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref,
)
from strategy.tns import (
    _calcul_strategie_t1, _calcul_strategie_t2,
    _calcul_strategie_t3, _calcul_strategie_t4,
    arbitrage_complet_tns,
)
from ui.audit_render import rendre_trace_console


# ============================================================
# REGISTRES — Contrat G3b
# ============================================================
CODES_ATTENDUS_META = {
    "STRAT_TNS_COMPARE_AB",
    "STRAT_TNS_DELTA_T2_VS_T1",
    "STRAT_TNS_DELTA_T3_VS_T1",
    "STRAT_TNS_DELTA_T4_VS_T1",
    "STRAT_TNS_INDICATEURS_SEPARES",
    "STRAT_TNS_CRITERE_RETENU",
    "STRAT_TNS_RETENU",
}

CODES_COMMUNS_PAR_STRATEGIE = {
    "ENVELOPPE", "SEUIL_10PCT", "REMUNERATION_BRUTE", "COUT_REMUNERATION",
    "NET_REMUNERATION", "NET_DIRIGEANT_IMMEDIAT", "EFFICACITE_IMMEDIATE",
}

# Codes spécifiques à chaque stratégie (en plus des communs)
CODES_SPECIFIQUES = {
    "T1": {"PART_REM_APPLIQUEE", "RESTE_AVANT_IS", "IS_SOCIETE",
           "DIVIDENDES_DISTRIBUABLES", "NET_DIVIDENDES"},
    "T2": {"RATIO_MARGINAL", "RESULTAT_SOCIETE_POUR_DIV", "IS_POUR_DIV",
           "DIV_BRUTS_CIBLES", "GARDE_FOU_90PCT", "ALERTES_NB",
           "NET_DIVIDENDES"},
    "T3": {"PART_REM_APPLIQUEE", "RESTE_AVANT_IS", "IS_SOCIETE",
           "DIVIDENDES_PLAFONNES", "PLAFOND_PERIN_INDIVIDUEL",
           "VERSEMENT_PERIN", "TMI_MARGINAL", "ECONOMIE_IR_PERIN",
           "NET_DIVIDENDES"},
    "T4": {"PART_REM_APPLIQUEE", "RESTE_AVANT_IS", "IS_SOCIETE",
           "BENEFICE_RETENU_SOCIETE"},
}


def codes_attendus_strategie(code_strat):
    """Construit le set complet des codes attendus pour une stratégie."""
    prefix = f"STRAT_TNS_{code_strat}_"
    return {prefix + s for s in (CODES_COMMUNS_PAR_STRATEGIE | CODES_SPECIFIQUES[code_strat])}


NOMS_SOUS_TRACES_META = {"strategie_T1", "strategie_T2",
                          "strategie_T3", "strategie_T4"}


# ============================================================
# VOCABULAIRE PRESCRIPTIF INTERDIT (test 9, repris de G3a)
# ============================================================
TERMES_INTERDITS = [
    # Élargi G3b : capture optimal/optimale/optimisation/optimum/optimisé/optime…
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

profil = Profil()

# Chaque stratégie individuelle
for code_strat, fn in (("T1", _calcul_strategie_t1),
                       ("T2", _calcul_strategie_t2),
                       ("T3", _calcul_strategie_t3),
                       ("T4", _calcul_strategie_t4)):
    r_sans = fn(profil)
    t = TraceAudit(regime=f"Stratégie TNS/{code_strat}")
    r_avec = fn(profil, audit=t)
    # ResultatStrategieTNS est une dataclass — comparaison directe
    check(f"_calcul_strategie_{code_strat.lower()}: dataclass identique avec/sans audit",
          r_sans == r_avec)

# arbitrage_complet_tns
r_sans_arb = arbitrage_complet_tns(profil)
trace_arb = TraceAudit(regime="Strategy/TNS/arbitrage_complet")
r_avec_arb = arbitrage_complet_tns(profil, audit=trace_arb)
check("arbitrage_complet_tns: même stratégie retenue avec/sans audit",
      r_sans_arb.recommandee == r_avec_arb.recommandee)
check("arbitrage_complet_tns: 4 stratégies identiques avec/sans audit",
      all(r_sans_arb.strategies[c] == r_avec_arb.strategies[c]
          for c in ("T1", "T2", "T3", "T4")))


# ============================================================
# TEST 2 — STRUCTURE TRACE MÉTA
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure trace méta (codes STRAT_TNS_*)")
print("=" * 95)

codes_meta = set(trace_arb.codes())
check(f"Trace méta contient les {len(CODES_ATTENDUS_META)} codes attendus",
      codes_meta == CODES_ATTENDUS_META,
      f"manquants={CODES_ATTENDUS_META - codes_meta}, "
      f"extras={codes_meta - CODES_ATTENDUS_META}")

# Hiérarchie : DELTA_T<X>_VS_T1 doivent avoir COMPARE_AB pour parent
for c in ("STRAT_TNS_DELTA_T2_VS_T1",
          "STRAT_TNS_DELTA_T3_VS_T1",
          "STRAT_TNS_DELTA_T4_VS_T1"):
    e = trace_arb.get(c)
    check(f"parent_id de {c} = STRAT_TNS_COMPARE_AB",
          e.parent_id == "STRAT_TNS_COMPARE_AB")


# ============================================================
# TEST 3 — STRUCTURE TRACES STRATÉGIE (chacune)
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Structure attendue de chaque sous-trace stratégie")
print("=" * 95)

for code_strat in ("T1", "T2", "T3", "T4"):
    sub = trace_arb.get_sous_trace(f"strategie_{code_strat}")
    check(f"Sous-trace 'strategie_{code_strat}' attachée", sub is not None)
    if sub is None:
        continue
    codes_obtenus = set(sub.codes())
    attendus = codes_attendus_strategie(code_strat)
    check(f"  → {code_strat} contient les {len(attendus)} codes attendus",
          codes_obtenus == attendus,
          f"manquants={attendus - codes_obtenus}, "
          f"extras={codes_obtenus - attendus}")


# ============================================================
# TEST 4 — IMBRICATION 2 NIVEAUX
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Sous-traces imbriquées sur 2 niveaux (méta → stratégie → régime)")
print("=" * 95)

noms_niveau1 = set(trace_arb.noms_sous_traces())
check(f"Niveau 1 : {NOMS_SOUS_TRACES_META}",
      noms_niveau1 == NOMS_SOUS_TRACES_META)

# Chaque stratégie doit avoir UNE sous-trace 'module_tns' (niveau 2)
for code_strat in ("T1", "T2", "T3", "T4"):
    sub_strat = trace_arb.get_sous_trace(f"strategie_{code_strat}")
    noms_niveau2 = set(sub_strat.noms_sous_traces())
    check(f"  strategie_{code_strat}: une seule sous-trace 'module_tns'",
          noms_niveau2 == {"module_tns"})

    sub_tns = sub_strat.get_sous_trace("module_tns")
    check(f"  module_tns({code_strat}): contient des codes TNS_*",
          all(c.startswith("TNS_") for c in sub_tns.codes()))
    check(f"  module_tns({code_strat}): 24 étapes (TNS complet)",
          len(sub_tns.etapes) == 24,
          f"obtenu={len(sub_tns.etapes)}")


# ============================================================
# TEST 5 — AUCUNE DUPLICATION / COLLISION
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Aucune duplication entre méta, stratégies et module_tns")
print("=" * 95)

# Codes méta ne doivent pas contenir de codes spécifiques aux stratégies
collisions_strat = set()
for code_strat in ("T1", "T2", "T3", "T4"):
    collisions_strat |= codes_attendus_strategie(code_strat) & codes_meta
check("Méta ne contient AUCUN code STRAT_TNS_T<X>_*",
      not collisions_strat,
      f"collisions={collisions_strat}")

# Codes TNS_* (niveau régime) ne doivent jamais apparaître dans une trace stratégie
for code_strat in ("T1", "T2", "T3", "T4"):
    sub_strat = trace_arb.get_sous_trace(f"strategie_{code_strat}")
    codes_strat = set(sub_strat.codes())
    intrusions_tns = [c for c in codes_strat if c.startswith("TNS_")]
    check(f"strategie_{code_strat}: aucune intrusion TNS_* à plat",
          not intrusions_tns,
          f"intrusions={intrusions_tns}")


# ============================================================
# TEST 6 — CONVENTION NON-AGRÉGATION T4
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Convention de non-agrégation T4 (indicateurs séparés)")
print("=" * 95)

# 6.a Au niveau méta : étape STRAT_TNS_INDICATEURS_SEPARES présente
ind = trace_arb.get("STRAT_TNS_INDICATEURS_SEPARES")
check("STRAT_TNS_INDICATEURS_SEPARES présent au niveau méta", ind is not None)
check("  valeur = benefice_retenu T4",
      abs(ind.valeur - r_avec_arb.strategies["T4"].benefice_retenu_societe) < TOL)
check("  hypothèse 'convention' = non-agrégation T4",
      ind.hypotheses.get("convention") == "non-agrégation T4")

# 6.b Dans la sous-trace strategie_T4 : BENEFICE_RETENU et NET_DIRIGEANT séparés
sub_t4 = trace_arb.get_sous_trace("strategie_T4")
e_ben = sub_t4.get("STRAT_TNS_T4_BENEFICE_RETENU_SOCIETE")
e_net = sub_t4.get("STRAT_TNS_T4_NET_DIRIGEANT_IMMEDIAT")
check("T4: BENEFICE_RETENU_SOCIETE existe", e_ben is not None)
check("T4: NET_DIRIGEANT_IMMEDIAT existe", e_net is not None)
check("T4: les deux étapes sont structurellement séparées (parent_id distincts)",
      e_ben.parent_id != e_net.parent_id or
      (e_ben.parent_id is None and e_net.parent_id is None))

# 6.c Net dirigeant T4 = uniquement net rémunération (convention assertée dans le code)
res_t4 = r_avec_arb.strategies["T4"]
check("T4: net_dirigeant_immediat = net_remuneration exactement",
      abs(res_t4.net_dirigeant_immediat - res_t4.net_remuneration) < TOL)


# ============================================================
# TEST 7 — RÉSOLUTION DOCTRINALE
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Doctrine_refs (méta + sous-traces) se résolvent")
print("=" * 95)

refs_uniques = set()
def collecter_refs(t):
    for e in t.etapes:
        refs_uniques.update(e.doctrine_refs)
    for n in t.noms_sous_traces():
        collecter_refs(t.get_sous_trace(n))
collecter_refs(trace_arb)

check(f"{len(refs_uniques)} doctrine_refs uniques dans le graphe",
      len(refs_uniques) >= 8)

attendues_minimales = {
    "SEUIL_DIV_TNS", "TX_TNS",
    "IS_PLAF_REDUIT", "TX_IS_REDUIT", "TX_IS_NORMAL",
    "PASS_2026",
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
# TEST 8 — TEXTES D'ALERTES T2 PRÉSERVÉS EN HYPOTHESES
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Textes d'alertes T2 préservés en hypotheses (pas en label/notes)")
print("=" * 95)

# Forcer un profil qui déclenche les alertes T2
import dataclasses
profil_alerte = dataclasses.replace(profil, capital_cca=5_000)  # < 10 000 € seuil
trace_t2_alerte = TraceAudit(regime="Test T2 alertes")
_calcul_strategie_t2(profil_alerte, audit=trace_t2_alerte)

etape_alertes = trace_t2_alerte.get("STRAT_TNS_T2_ALERTES_NB")
check("STRAT_TNS_T2_ALERTES_NB présente", etape_alertes is not None)
if etape_alertes is not None:
    check("Au moins 1 alerte déclenchée par profil à capital faible",
          etape_alertes.valeur >= 1.0)
    check("Textes d'alertes en hypotheses['textes_alertes'] (pas en label/notes)",
          "textes_alertes" in etape_alertes.hypotheses)
    # Le label et les notes ne doivent PAS contenir les textes d'alertes métier
    label_clean = etape_alertes.label
    notes_clean = etape_alertes.notes
    check("Label ne contient PAS le mot métier 'optimum'",
          "optimum" not in label_clean.lower())
    check("Notes ne contient PAS le mot métier 'optimum'",
          "optimum" not in notes_clean.lower())
    # En revanche, hypotheses peut contenir le texte original (non scanné)
    textes = etape_alertes.hypotheses.get("textes_alertes", [])
    check("Texte d'alerte métier intégral préservé dans hypotheses",
          any("optimum" in t.lower() for t in textes) or len(textes) == 1,
          f"textes={textes}")


# ============================================================
# TEST 9 — NON-PRESCRIPTIF (scan automatique de tout le graphe)
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Aucun wording prescriptif dans labels ou notes (scan récursif)")
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

violations = scanner_prescriptif(trace_arb)
n_total = compter_etapes(trace_arb)
if violations:
    check(f"Aucun wording prescriptif détecté", False,
          f"{len(violations)} violation(s) sur {n_total} étapes scannées")
    for chemin, code, pattern, champ, texte in violations[:5]:
        print(f"       ⚠ {chemin} / {code} / {champ} : pattern={pattern} dans {texte!r}")
else:
    check(f"Aucun wording prescriptif dans tout le graphe", True,
          f"{n_total} étapes scannées sur 12 patterns")


# ============================================================
# TEST 10 — RENDU CONSOLE COMPLET (méta + 2 niveaux sous-traces)
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Rendu console (méta + sous-traces récursives)")
print("=" * 95)

rendu = rendre_trace_console(trace_arb)
check("Rendu non-vide", len(rendu) > 5000)
check("En-tête racine TNS", "Strategy/TNS" in rendu)
check("Contient STRAT_TNS_RETENU", "STRAT_TNS_RETENU" in rendu)
check("Contient STRAT_TNS_INDICATEURS_SEPARES",
      "STRAT_TNS_INDICATEURS_SEPARES" in rendu)
check("Sous-traces niveau 1 rendues (4 stratégies)",
      "Sous-traces attachées (4)" in rendu)
for c in ("strategie_T1", "strategie_T2", "strategie_T3", "strategie_T4"):
    check(f"  rendu sous-trace {c!r}",
          f"nom d'attachement : {c!r}" in rendu)
check("Sous-traces niveau 2 (module_tns) rendues",
      rendu.count("nom d'attachement : 'module_tns'") == 4)
check("Pas de référence introuvable", "référence introuvable" not in rendu)


# ============================================================
# TEST 11 — ISOLATION ESPACES DE CODES
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Isolation STRAT_TNS_* ⊥ STRAT_ASSIM_* / TNS_* / autres")
print("=" * 95)

# Méta : tous préfixés STRAT_TNS_
check("Méta : tous codes préfixés STRAT_TNS_",
      all(c.startswith("STRAT_TNS_") for c in codes_meta))
# Aucune intrusion STRAT_ASSIM_*
check("Méta : aucune intrusion STRAT_ASSIM_*",
      not any(c.startswith("STRAT_ASSIM_") for c in codes_meta))

# Pour chaque stratégie : tous préfixés STRAT_TNS_T<X>_
for code_strat in ("T1", "T2", "T3", "T4"):
    sub = trace_arb.get_sous_trace(f"strategie_{code_strat}")
    check(f"strategie_{code_strat}: tous préfixés STRAT_TNS_{code_strat}_",
          all(c.startswith(f"STRAT_TNS_{code_strat}_") for c in sub.codes()))

# Sous-sous-traces module_tns : tous préfixés TNS_
for code_strat in ("T1", "T2", "T3", "T4"):
    sub = trace_arb.get_sous_trace(f"strategie_{code_strat}").get_sous_trace("module_tns")
    check(f"module_tns({code_strat}): tous préfixés TNS_ (régime)",
          all(c.startswith("TNS_") for c in sub.codes()))


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Strategy/TNS passent (G3b)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
