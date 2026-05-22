"""
test_mode_audit_liberal.py — Tests dédiés à l'instrumentation MODE_AUDIT
du module Libéral (G1a `calcul_module_bnc` + G1b `calcul_module_sel`).

Vérifie pour chaque module :
1. Rétrocompat parfaite (audit=None ⇒ comportement strictement historique)
2. Structure attendue de la trace (codes, hiérarchie, comptage)
3. Cohérence des valeurs tracées avec les attributs du résultat retourné
4. Résolution doctrinale pour tous les doctrine_refs cités
5. Unicité des codes dans la trace
6. Cas limite
7. Rendu console produit du texte non-vide

Usage : python3 test_mode_audit_liberal.py
Exit code 0 si tous les tests passent.
"""

import sys

from core.profil import Profil
from core.audit import TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref
from regime.liberal import calcul_module_bnc, calcul_module_sel
from ui.audit_render import rendre_trace_console


# ============================================================
# REGISTRE DES CODES ATTENDUS — Contrat M2-BNC
# ============================================================
# Snapshot du contrat G1a. Toute modification de regime/liberal.py
# (calcul_module_bnc) doit explicitement mettre à jour ce set.
CODES_ATTENDUS_BNC = {
    # Racines
    "LIB_BNC_RECETTES",
    "LIB_BNC_BENEFICE",
    "LIB_BNC_COTISATIONS",
    "LIB_BNC_REVENU_IMPOSABLE_LIB",
    "LIB_BNC_REVENU_IMPOSABLE_FOYER",
    "LIB_BNC_IR_FOYER_AGGREGE",
    "LIB_BNC_IMPOTS_IMPUTABLES",
    "LIB_BNC_NET_APRES_IMPOTS",
    # Enfants LIB_BNC_BENEFICE
    "LIB_BNC_FRAIS_PRO",
    "LIB_BNC_BENEFICE_NET",
    # Enfants LIB_BNC_COTISATIONS
    "LIB_BNC_COTIS_BASE",
    "LIB_BNC_CSG_NON_DEDUCTIBLE",
    # Enfants LIB_BNC_IR_FOYER_AGGREGE
    "LIB_BNC_IR_FOYER_BRUT",
    "LIB_BNC_CEHR",
    "LIB_BNC_CDHR",
    "LIB_BNC_TAUX_MOYEN_IR",
}

PARENT_ATTENDU = {
    "LIB_BNC_FRAIS_PRO": "LIB_BNC_BENEFICE",
    "LIB_BNC_BENEFICE_NET": "LIB_BNC_BENEFICE",
    "LIB_BNC_COTIS_BASE": "LIB_BNC_COTISATIONS",
    "LIB_BNC_CSG_NON_DEDUCTIBLE": "LIB_BNC_COTISATIONS",
    "LIB_BNC_IR_FOYER_BRUT": "LIB_BNC_IR_FOYER_AGGREGE",
    "LIB_BNC_CEHR": "LIB_BNC_IR_FOYER_AGGREGE",
    "LIB_BNC_CDHR": "LIB_BNC_IR_FOYER_AGGREGE",
    "LIB_BNC_TAUX_MOYEN_IR": "LIB_BNC_IR_FOYER_AGGREGE",
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


# ============================================================
# TEST 1 — RÉTROCOMPAT PARFAITE
# ============================================================
print("=" * 95)
print("  TEST 1 — Rétrocompat parfaite (audit=None ⇒ comportement historique)")
print("=" * 95)

profil = Profil()
r_sans = calcul_module_bnc(profil, recettes=120_000, frais_pro=15_000)

trace = TraceAudit(regime="Libéral BNC")
r_avec = calcul_module_bnc(profil, recettes=120_000, frais_pro=15_000,
                           audit=trace)

check("Résultat identique avec/sans audit", r_sans == r_avec)

import dataclasses
all_eq = True
for f in dataclasses.fields(type(r_sans)):
    v_sans = getattr(r_sans, f.name)
    v_avec = getattr(r_avec, f.name)
    if isinstance(v_sans, float):
        if abs(v_sans - v_avec) >= TOL:
            all_eq = False
            check(f"Attribut {f.name}", False,
                  f"sans={v_sans} vs avec={v_avec}")
    elif v_sans != v_avec:
        all_eq = False
        check(f"Attribut {f.name}", False)
check("Tous les attributs identiques attribut par attribut", all_eq)


# ============================================================
# TEST 2 — STRUCTURE
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure attendue de la trace BNC")
print("=" * 95)

trace = TraceAudit(regime="Libéral BNC")
calcul_module_bnc(profil, recettes=120_000, frais_pro=15_000, audit=trace)

codes_obtenus = set(trace.codes())
check(f"Trace contient exactement les {len(CODES_ATTENDUS_BNC)} codes attendus",
      codes_obtenus == CODES_ATTENDUS_BNC)
manquants = CODES_ATTENDUS_BNC - codes_obtenus
extras = codes_obtenus - CODES_ATTENDUS_BNC
if manquants:
    check("Aucun code manquant", False, f"manquants={manquants}")
if extras:
    check("Aucun code en trop", False, f"extras={extras}")

for code_enfant, parent_attendu in PARENT_ATTENDU.items():
    etape = trace.get(code_enfant)
    if etape is None:
        check(f"Étape {code_enfant} présente", False)
        continue
    check(f"parent_id de {code_enfant}",
          etape.parent_id == parent_attendu,
          f"attendu={parent_attendu}, obtenu={etape.parent_id}")

racines_codes = {e.code for e in trace.racines()}
racines_attendues = CODES_ATTENDUS_BNC - set(PARENT_ATTENDU.keys())
check(f"8 racines attendues", racines_codes == racines_attendues)

check(f"Spec version {AUDIT_SPEC_VERSION}", trace.spec_version == AUDIT_SPEC_VERSION)

# Préfixe LIB_BNC_ systématique
check("Tous les codes BNC sont préfixés LIB_BNC_",
      all(c.startswith("LIB_BNC_") for c in codes_obtenus))


# ============================================================
# TEST 3 — COHÉRENCE VALEURS TRACÉES vs RÉSULTAT
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Cohérence valeurs tracées vs attributs du résultat")
print("=" * 95)

mapping_trace_resultat = {
    "LIB_BNC_RECETTES": "recettes",
    "LIB_BNC_FRAIS_PRO": "frais_pro",
    "LIB_BNC_BENEFICE": "benefice_bnc",
    "LIB_BNC_BENEFICE_NET": "benefice_net_apres_cotis",
    "LIB_BNC_COTIS_BASE": "cotisations",
    "LIB_BNC_CSG_NON_DEDUCTIBLE": "csg_non_deductible",
    "LIB_BNC_REVENU_IMPOSABLE_LIB": "revenu_imposable_lib",
    "LIB_BNC_REVENU_IMPOSABLE_FOYER": "revenu_imposable_foyer",
    "LIB_BNC_IR_FOYER_BRUT": "ir_foyer",
    "LIB_BNC_CEHR": "cehr",
    "LIB_BNC_CDHR": "cdhr",
    "LIB_BNC_IMPOTS_IMPUTABLES": "impots_imputables_libéral",
    "LIB_BNC_NET_APRES_IMPOTS": "net_apres_impots",
}

trace = TraceAudit(regime="Libéral BNC")
res = calcul_module_bnc(profil, recettes=120_000, frais_pro=15_000,
                        audit=trace)

for code_trace, attr_res in mapping_trace_resultat.items():
    v_trace = trace.get(code_trace).valeur
    v_res = getattr(res, attr_res)
    check(f"{code_trace} ↔ res.{attr_res}",
          abs(v_trace - v_res) < TOL,
          f"trace={v_trace}, res={v_res}")


# ============================================================
# TEST 4 — RÉSOLUTION DOCTRINALE
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Tous les doctrine_refs cités se résolvent")
print("=" * 95)

refs_uniques = set()
for etape in trace.etapes:
    refs_uniques.update(etape.doctrine_refs)

check(f"{len(refs_uniques)} doctrine_refs uniques cités",
      len(refs_uniques) > 0,
      f"refs={sorted(refs_uniques)}")

for ref in sorted(refs_uniques):
    try:
        valeur = resoudre_doctrine_ref(ref)
        check(f"Résolution {ref} = {valeur}", True)
    except AttributeError as e:
        check(f"Résolution {ref}", False, str(e))

# Cohérence hypotheses ⇔ doctrine_refs
for etape in trace.etapes:
    for ref in etape.doctrine_refs:
        if ref in etape.hypotheses:
            try:
                valeur_doctrinale = resoudre_doctrine_ref(ref)
                check(f"{etape.code}: hypothèse[{ref}] == doctrine",
                      etape.hypotheses[ref] == valeur_doctrinale,
                      f"hyp={etape.hypotheses[ref]}, doctrine={valeur_doctrinale}")
            except AttributeError:
                pass


# ============================================================
# TEST 5 — UNICITÉ DES CODES
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Unicité des codes dans la trace")
print("=" * 95)

codes = trace.codes()
check(f"Tous les codes uniques ({len(codes)} étapes)",
      len(codes) == len(set(codes)))


# ============================================================
# TEST 6 — CAS LIMITE : FRAIS_PRO NULS
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Cas limite : frais_pro = 0")
print("=" * 95)

trace_sans_frais = TraceAudit(regime="Libéral BNC")
res_sans = calcul_module_bnc(profil, recettes=120_000, frais_pro=0,
                              audit=trace_sans_frais)

check("Trace complète même sans frais",
      len(trace_sans_frais.etapes) == len(CODES_ATTENDUS_BNC))
check("LIB_BNC_FRAIS_PRO = 0",
      abs(trace_sans_frais.get("LIB_BNC_FRAIS_PRO").valeur) < TOL)
check("LIB_BNC_BENEFICE = recettes (frais nuls)",
      abs(trace_sans_frais.get("LIB_BNC_BENEFICE").valeur - 120_000) < TOL)


# ============================================================
# TEST 7 — RENDU CONSOLE
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Rendu console")
print("=" * 95)

rendu = rendre_trace_console(trace)
check("Rendu non-vide", len(rendu) > 1000)
check("En-tête régime", "AUDIT — Régime Libéral BNC" in rendu)
check("Contient LIB_BNC_NET_APRES_IMPOTS", "LIB_BNC_NET_APRES_IMPOTS" in rendu)
check("Doctrine TX_LIB résolue", "TX_LIB=" in rendu)
check("Pas de référence introuvable", "référence introuvable" not in rendu)


# ════════════════════════════════════════════════════════════════════════════
# PARTIE 2 — INSTRUMENTATION SEL (G1b)
# ════════════════════════════════════════════════════════════════════════════

# ============================================================
# REGISTRE DES CODES ATTENDUS — Contrat G1b SEL
# ============================================================
CODES_ATTENDUS_SEL = {
    # Racines
    "LIB_SEL_BENEFICE_AVANT_REM",
    "LIB_SEL_REMUNERATION_DIRIGEANT",
    "LIB_SEL_BENEFICE_IMPOSABLE_IS",
    "LIB_SEL_RESULTAT_NET_DISTRIBUABLE",
    "LIB_SEL_DIVIDENDES_ENVISAGES",
    # Enfants LIB_SEL_BENEFICE_IMPOSABLE_IS
    "LIB_SEL_FRACTION_REDUITE",
    "LIB_SEL_FRACTION_NORMALE",
    "LIB_SEL_IS_DU",
}

PARENT_ATTENDU_SEL = {
    "LIB_SEL_FRACTION_REDUITE": "LIB_SEL_BENEFICE_IMPOSABLE_IS",
    "LIB_SEL_FRACTION_NORMALE": "LIB_SEL_BENEFICE_IMPOSABLE_IS",
    "LIB_SEL_IS_DU": "LIB_SEL_BENEFICE_IMPOSABLE_IS",
}


# ============================================================
# TEST 8 — RÉTROCOMPAT SEL
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Rétrocompat parfaite SEL (audit=None ⇒ historique)")
print("=" * 95)

r_sans = calcul_module_sel(benefice_avant_rem=200_000,
                            remuneration_dirigeant=80_000)
trace_sel = TraceAudit(regime="Libéral SEL")
r_avec = calcul_module_sel(benefice_avant_rem=200_000,
                            remuneration_dirigeant=80_000,
                            audit=trace_sel)
check("Résultat SEL identique avec/sans audit", r_sans == r_avec)


# ============================================================
# TEST 9 — STRUCTURE TRACE SEL
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Structure attendue de la trace SEL")
print("=" * 95)

codes_sel = set(trace_sel.codes())
check(f"Trace SEL contient exactement {len(CODES_ATTENDUS_SEL)} codes attendus",
      codes_sel == CODES_ATTENDUS_SEL)
manquants = CODES_ATTENDUS_SEL - codes_sel
extras = codes_sel - CODES_ATTENDUS_SEL
if manquants:
    check("Aucun code SEL manquant", False, f"manquants={manquants}")
if extras:
    check("Aucun code SEL en trop", False, f"extras={extras}")

for code_enfant, parent_attendu in PARENT_ATTENDU_SEL.items():
    etape = trace_sel.get(code_enfant)
    if etape is None:
        check(f"Étape {code_enfant} présente", False)
        continue
    check(f"parent_id de {code_enfant}",
          etape.parent_id == parent_attendu,
          f"attendu={parent_attendu}, obtenu={etape.parent_id}")

racines_sel = {e.code for e in trace_sel.racines()}
racines_attendues = CODES_ATTENDUS_SEL - set(PARENT_ATTENDU_SEL.keys())
check(f"5 racines SEL attendues", racines_sel == racines_attendues)

check("Tous les codes SEL sont préfixés LIB_SEL_",
      all(c.startswith("LIB_SEL_") for c in codes_sel))


# ============================================================
# TEST 10 — COHÉRENCE VALEURS SEL
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Cohérence valeurs tracées SEL vs attributs du résultat")
print("=" * 95)

mapping_trace_sel = {
    "LIB_SEL_BENEFICE_AVANT_REM": "benefice_avant_rem",
    "LIB_SEL_REMUNERATION_DIRIGEANT": "remuneration_dirigeant",
    "LIB_SEL_BENEFICE_IMPOSABLE_IS": "benefice_imposable_is",
    "LIB_SEL_IS_DU": "is_du",
    "LIB_SEL_RESULTAT_NET_DISTRIBUABLE": "resultat_net_distribuable",
    "LIB_SEL_DIVIDENDES_ENVISAGES": "dividendes_envisages",
}

for code, attr in mapping_trace_sel.items():
    v_trace = trace_sel.get(code).valeur
    v_res = getattr(r_avec, attr)
    check(f"{code} ↔ res.{attr}",
          abs(v_trace - v_res) < TOL,
          f"trace={v_trace}, res={v_res}")

# Cohérence calculée des fractions : somme = bénéfice imposable
fred = trace_sel.get("LIB_SEL_FRACTION_REDUITE").valeur
fnorm = trace_sel.get("LIB_SEL_FRACTION_NORMALE").valeur
benefice_is = trace_sel.get("LIB_SEL_BENEFICE_IMPOSABLE_IS").valeur
check("Fraction réduite + fraction normale = bénéfice imposable IS",
      abs(fred + fnorm - benefice_is) < TOL,
      f"{fred} + {fnorm} = {fred+fnorm} vs {benefice_is}")


# ============================================================
# TEST 11 — RÉSOLUTION DOCTRINALE SEL
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Doctrine_refs SEL se résolvent")
print("=" * 95)

refs_sel = set()
for etape in trace_sel.etapes:
    refs_sel.update(etape.doctrine_refs)

attendues_min = {"IS_PLAF_REDUIT", "TX_IS_REDUIT", "TX_IS_NORMAL"}
check(f"Au moins {len(attendues_min)} doctrine_refs SEL attendues citées",
      attendues_min.issubset(refs_sel),
      f"manquantes={attendues_min - refs_sel}")

for ref in sorted(refs_sel):
    try:
        valeur = resoudre_doctrine_ref(ref)
        check(f"Résolution {ref} = {valeur}", True)
    except AttributeError as e:
        check(f"Résolution {ref}", False, str(e))


# ============================================================
# TEST 12 — CAS LIMITE SEL : bénéfice imposable nul
# ============================================================
print()
print("=" * 95)
print("  TEST 12 — Cas limite SEL : rémunération > bénéfice (imposable IS = 0)")
print("=" * 95)

trace_zero = TraceAudit(regime="Libéral SEL")
res_zero = calcul_module_sel(benefice_avant_rem=50_000,
                              remuneration_dirigeant=80_000,
                              audit=trace_zero)
check("Trace complète même avec imposable IS = 0",
      len(trace_zero.etapes) == len(CODES_ATTENDUS_SEL))
check("LIB_SEL_BENEFICE_IMPOSABLE_IS = 0 (plancher)",
      abs(trace_zero.get("LIB_SEL_BENEFICE_IMPOSABLE_IS").valeur) < TOL)
check("LIB_SEL_IS_DU = 0",
      abs(trace_zero.get("LIB_SEL_IS_DU").valeur) < TOL)


# ============================================================
# TEST 13 — RENDU CONSOLE SEL
# ============================================================
print()
print("=" * 95)
print("  TEST 13 — Rendu console SEL")
print("=" * 95)

rendu_sel = rendre_trace_console(trace_sel)
check("Rendu SEL non-vide", len(rendu_sel) > 500)
check("En-tête régime SEL", "AUDIT — Régime Libéral SEL" in rendu_sel)
check("Contient LIB_SEL_IS_DU", "LIB_SEL_IS_DU" in rendu_sel)
check("Doctrine TX_IS_REDUIT résolue", "TX_IS_REDUIT=" in rendu_sel)
check("Pas de référence introuvable", "référence introuvable" not in rendu_sel)


# ============================================================
# TEST 14 — ISOLATION BNC / SEL (codes ne se croisent pas)
# ============================================================
print()
print("=" * 95)
print("  TEST 14 — Isolation des espaces de codes BNC ↔ SEL")
print("=" * 95)

codes_bnc = CODES_ATTENDUS_BNC
codes_sel_set = CODES_ATTENDUS_SEL
check("Aucun code partagé entre BNC et SEL",
      codes_bnc.isdisjoint(codes_sel_set))
check("Tous les codes BNC préfixés LIB_BNC_",
      all(c.startswith("LIB_BNC_") for c in codes_bnc))
check("Tous les codes SEL préfixés LIB_SEL_",
      all(c.startswith("LIB_SEL_") for c in codes_sel_set))


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Libéral (BNC + SEL) passent")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
