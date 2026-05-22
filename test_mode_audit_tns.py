"""
test_mode_audit_tns.py — Tests dédiés à l'instrumentation MODE_AUDIT de TNS.

Vérifie :
1. Rétrocompat parfaite (audit=None ⇒ comportement strictement historique)
2. Structure attendue de la trace (codes, hiérarchie, comptage)
3. Cohérence des valeurs tracées avec les attributs du résultat retourné
4. Résolution doctrinale pour tous les doctrine_refs cités
5. Unicité des codes dans la trace
6. Comportement avec dividendes nuls (chemin moins fréquenté)
7. Rendu console produit (smoke test du renderer)

Usage : python3 test_mode_audit_tns.py
Exit code 0 si tous les tests passent.
"""

import sys

from core.profil import Profil, TX_TNS, TX_PFU, SEUIL_DIV_TNS
from core.audit import TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref
from regime.tns import calcul_module_tns
from ui.audit_render import rendre_trace_console


# ============================================================
# REGISTRE DES CODES ATTENDUS DANS LA TRACE TNS
# ============================================================
# Snapshot du contrat M2 : si un code est ajouté/supprimé, ce test doit être
# mis à jour explicitement. Garde-fou contre les renommages silencieux.
CODES_ATTENDUS_TNS = {
    # Racines
    "TNS_REM_BRUTE",
    "TNS_COTIS_SOCIALES",
    "TNS_REVENU_NET_PRO",
    "TNS_REVENU_IMPOSABLE",
    "TNS_REVENU_IMPOSABLE_FOYER",
    "TNS_IR_FOYER_AGGREGE",
    "TNS_NET_APRES_IR",
    "TNS_COUT_SOCIETE",
    "TNS_DIVIDENDES",
    # Enfants TNS_COTIS_SOCIALES
    "TNS_COTIS_TNS_BASE",
    "TNS_CSG_DEDUCTIBLE",
    "TNS_CSG_NON_DEDUCTIBLE",
    # Enfants TNS_IR_FOYER_AGGREGE
    "TNS_IR_FOYER_BRUT",
    "TNS_CEHR",
    "TNS_CDHR",
    "TNS_TAUX_MOYEN_IR",
    "TNS_IMPOTS_IMPUTABLES_REM",
    # Enfants TNS_DIVIDENDES
    "TNS_DIV_SEUIL_10PCT",
    "TNS_DIV_FRACTION_COTIS_TNS",
    "TNS_DIV_COTIS_TNS_SUR_DIV",
    "TNS_DIV_FRACTION_PFU",
    "TNS_DIV_PFU_SUR_FRACTION",
    "TNS_DIV_IR_SUR_FRACTION_TNS",
    "TNS_DIV_NET",
}

# Mapping parent_id attendu pour chaque code-enfant
PARENT_ATTENDU = {
    "TNS_COTIS_TNS_BASE": "TNS_COTIS_SOCIALES",
    "TNS_CSG_DEDUCTIBLE": "TNS_COTIS_SOCIALES",
    "TNS_CSG_NON_DEDUCTIBLE": "TNS_COTIS_SOCIALES",
    "TNS_IR_FOYER_BRUT": "TNS_IR_FOYER_AGGREGE",
    "TNS_CEHR": "TNS_IR_FOYER_AGGREGE",
    "TNS_CDHR": "TNS_IR_FOYER_AGGREGE",
    "TNS_TAUX_MOYEN_IR": "TNS_IR_FOYER_AGGREGE",
    "TNS_IMPOTS_IMPUTABLES_REM": "TNS_IR_FOYER_AGGREGE",
    "TNS_DIV_SEUIL_10PCT": "TNS_DIVIDENDES",
    "TNS_DIV_FRACTION_COTIS_TNS": "TNS_DIVIDENDES",
    "TNS_DIV_COTIS_TNS_SUR_DIV": "TNS_DIVIDENDES",
    "TNS_DIV_FRACTION_PFU": "TNS_DIVIDENDES",
    "TNS_DIV_PFU_SUR_FRACTION": "TNS_DIVIDENDES",
    "TNS_DIV_IR_SUR_FRACTION_TNS": "TNS_DIVIDENDES",
    "TNS_DIV_NET": "TNS_DIVIDENDES",
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
r_sans_audit = calcul_module_tns(profil, rem_nette_souhaitee=80_000,
                                  frais_reels=2_000, div_bruts=20_000)

trace = TraceAudit(regime="TNS")
r_avec_audit = calcul_module_tns(profil, rem_nette_souhaitee=80_000,
                                  frais_reels=2_000, div_bruts=20_000,
                                  audit=trace)

check("Résultat identique avec/sans audit", r_sans_audit == r_avec_audit)

# Vérification fine attribut par attribut
import dataclasses
for f in dataclasses.fields(type(r_sans_audit)):
    v_sans = getattr(r_sans_audit, f.name)
    v_avec = getattr(r_avec_audit, f.name)
    if isinstance(v_sans, float):
        ok = abs(v_sans - v_avec) < TOL
    else:
        ok = v_sans == v_avec
    if not ok:
        check(f"Attribut {f.name}", False,
              f"sans={v_sans} vs avec={v_avec}")
check("Tous les attributs identiques", True)


# ============================================================
# TEST 2 — STRUCTURE DE LA TRACE
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure attendue de la trace")
print("=" * 95)

trace = TraceAudit(regime="TNS", profil_resume="test 2")
calcul_module_tns(profil, rem_nette_souhaitee=80_000, div_bruts=20_000,
                  audit=trace)

codes_obtenus = set(trace.codes())
check(f"Trace contient exactement les {len(CODES_ATTENDUS_TNS)} codes attendus",
      codes_obtenus == CODES_ATTENDUS_TNS,
      f"obtenus={len(codes_obtenus)}")
manquants = CODES_ATTENDUS_TNS - codes_obtenus
extras = codes_obtenus - CODES_ATTENDUS_TNS
if manquants:
    check("Aucun code manquant", False, f"manquants={manquants}")
if extras:
    check("Aucun code en trop", False, f"extras={extras}")

# Hiérarchie
for code_enfant, parent_attendu in PARENT_ATTENDU.items():
    etape = trace.get(code_enfant)
    if etape is None:
        check(f"Étape {code_enfant} présente", False)
        continue
    check(f"parent_id de {code_enfant}",
          etape.parent_id == parent_attendu,
          f"attendu={parent_attendu}, obtenu={etape.parent_id}")

# Racines
racines_codes = {e.code for e in trace.racines()}
racines_attendues = CODES_ATTENDUS_TNS - set(PARENT_ATTENDU.keys())
check(f"9 racines attendues", racines_codes == racines_attendues,
      f"manquantes={racines_attendues - racines_codes}, "
      f"en_trop={racines_codes - racines_attendues}")

check(f"Spec version {AUDIT_SPEC_VERSION}", trace.spec_version == AUDIT_SPEC_VERSION)


# ============================================================
# TEST 3 — COHÉRENCE VALEURS TRACÉES vs RÉSULTAT
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Cohérence valeurs tracées vs attributs du résultat")
print("=" * 95)

mapping_trace_resultat = {
    "TNS_REM_BRUTE": "rem_nette_souhaitee",
    "TNS_COTIS_TNS_BASE": "cotisations_tns",
    "TNS_CSG_DEDUCTIBLE": "csg_deductible",
    "TNS_CSG_NON_DEDUCTIBLE": "csg_non_deductible",
    "TNS_REVENU_NET_PRO": "revenu_net_pro",
    "TNS_REVENU_IMPOSABLE": "revenu_imposable",
    "TNS_REVENU_IMPOSABLE_FOYER": "revenu_imposable_foyer",
    "TNS_IR_FOYER_BRUT": "ir_foyer",
    "TNS_CEHR": "cehr",
    "TNS_CDHR": "cdhr",
    "TNS_TAUX_MOYEN_IR": "taux_moyen_ir",
    "TNS_IMPOTS_IMPUTABLES_REM": "impots_imputables_rem",
    "TNS_NET_APRES_IR": "net_apres_ir",
    "TNS_COUT_SOCIETE": "cout_total_societe",
    "TNS_DIV_SEUIL_10PCT": "seuil_10pct",
    "TNS_DIV_FRACTION_COTIS_TNS": "fraction_cotis_tns",
    "TNS_DIV_COTIS_TNS_SUR_DIV": "cotis_tns_sur_div",
    "TNS_DIV_FRACTION_PFU": "fraction_pfu",
    "TNS_DIV_PFU_SUR_FRACTION": "pfu_sur_fraction",
    "TNS_DIV_IR_SUR_FRACTION_TNS": "ir_sur_fraction_tns",
    "TNS_DIV_NET": "net_dividendes",
}

trace = TraceAudit(regime="TNS")
res = calcul_module_tns(profil, rem_nette_souhaitee=80_000, div_bruts=20_000,
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

trace = TraceAudit(regime="TNS")
calcul_module_tns(profil, rem_nette_souhaitee=80_000, div_bruts=20_000,
                  audit=trace)

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

# Cohérence hypotheses ⇔ doctrine_refs : si une hypothèse cite une doctrine_ref,
# la valeur doit correspondre à la valeur doctrinale courante (pas d'override
# fortuit)
for etape in trace.etapes:
    for ref in etape.doctrine_refs:
        if ref in etape.hypotheses:
            try:
                valeur_doctrinale = resoudre_doctrine_ref(ref)
                check(f"{etape.code}: hypothèse[{ref}] == doctrine",
                      etape.hypotheses[ref] == valeur_doctrinale,
                      f"hyp={etape.hypotheses[ref]}, doctrine={valeur_doctrinale}")
            except AttributeError:
                pass  # déjà couvert ci-dessus


# ============================================================
# TEST 5 — UNICITÉ DES CODES
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Unicité des codes dans la trace")
print("=" * 95)

trace = TraceAudit(regime="TNS")
calcul_module_tns(profil, rem_nette_souhaitee=80_000, div_bruts=20_000,
                  audit=trace)

codes = trace.codes()
check(f"Tous les codes uniques ({len(codes)} étapes)",
      len(codes) == len(set(codes)))


# ============================================================
# TEST 6 — CAS LIMITE : DIVIDENDES NULS
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Cas limite : dividendes = 0 (chemin moins fréquenté)")
print("=" * 95)

trace_sans_div = TraceAudit(regime="TNS")
res_sans_div = calcul_module_tns(profil, rem_nette_souhaitee=80_000,
                                  div_bruts=0, audit=trace_sans_div)

check("Trace existe même sans dividendes",
      len(trace_sans_div.etapes) == len(CODES_ATTENDUS_TNS))
check("TNS_DIV_NET = 0", abs(trace_sans_div.get("TNS_DIV_NET").valeur) < TOL)
check("Cohérence : res.net_dividendes == 0",
      abs(res_sans_div.net_dividendes) < TOL)


# ============================================================
# TEST 7 — RENDU CONSOLE (SMOKE)
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Rendu console produit du texte non-vide et structuré")
print("=" * 95)

trace = TraceAudit(regime="TNS", profil_resume="rem=80k, div=20k")
calcul_module_tns(profil, rem_nette_souhaitee=80_000, div_bruts=20_000,
                  audit=trace)

rendu = rendre_trace_console(trace)
check("Rendu non-vide", len(rendu) > 1000)
check("Rendu contient l'en-tête régime", "AUDIT — Régime TNS" in rendu)
check("Rendu contient TNS_NET_APRES_IR", "TNS_NET_APRES_IR" in rendu)
check("Rendu contient la résolution doctrinale TX_TNS",
      "TX_TNS=0.45" in rendu)
check("Rendu ne contient pas 'référence introuvable'",
      "référence introuvable" not in rendu)


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT TNS passent")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
