"""
test_mode_audit_salarie.py — Tests dédiés à l'instrumentation MODE_AUDIT
de `calcul_module_salarie()` (G2a).

Vérifie :
1. Rétrocompat parfaite (audit=None ⇒ comportement strictement historique)
2. Structure attendue de la trace (codes, hiérarchie, comptage)
3. Cohérence des valeurs tracées avec les attributs du résultat retourné
4. Résolution doctrinale pour tous les doctrine_refs cités
5. Unicité des codes dans la trace
6. Cas limite : salaire_brut nul
7. Rendu console produit du texte non-vide

Usage : python3 test_mode_audit_salarie.py
Exit code 0 si tous les tests passent.
"""

import sys

from core.profil import Profil
from core.audit import TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref
from regime.salarie import calcul_module_salarie
from ui.audit_render import rendre_trace_console


# ============================================================
# REGISTRE DES CODES ATTENDUS — Contrat G2a
# ============================================================
CODES_ATTENDUS_SAL = {
    # Racines
    "SAL_SALAIRE_BRUT",
    "SAL_COTISATIONS",
    "SAL_NET_AVANT_IMPOT",
    "SAL_REVENU_SALARIAL_IMPOSABLE",
    "SAL_ABATTEMENT_10PCT",
    "SAL_REVENU_IMPOSABLE_NET",
    "SAL_REVENU_IMPOSABLE_FOYER",
    "SAL_IR_FOYER_AGGREGE",
    "SAL_IMPOTS_IMPUTABLES_REM",
    "SAL_NET_APRES_IMPOTS",
    # Enfants SAL_COTISATIONS
    "SAL_COTIS_SALARIALES",
    "SAL_CSG_CRDS_TOTALE",
    "SAL_CSG_DEDUCTIBLE",
    # Enfants SAL_IR_FOYER_AGGREGE
    "SAL_IR_FOYER_BRUT",
    "SAL_CEHR",
    "SAL_CDHR",
    "SAL_TAUX_MOYEN_IR",
}

PARENT_ATTENDU = {
    "SAL_COTIS_SALARIALES": "SAL_COTISATIONS",
    "SAL_CSG_CRDS_TOTALE": "SAL_COTISATIONS",
    "SAL_CSG_DEDUCTIBLE": "SAL_COTISATIONS",
    "SAL_IR_FOYER_BRUT": "SAL_IR_FOYER_AGGREGE",
    "SAL_CEHR": "SAL_IR_FOYER_AGGREGE",
    "SAL_CDHR": "SAL_IR_FOYER_AGGREGE",
    "SAL_TAUX_MOYEN_IR": "SAL_IR_FOYER_AGGREGE",
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
r_sans = calcul_module_salarie(profil, salaire_brut=80_000)

trace = TraceAudit(regime="Salarié")
r_avec = calcul_module_salarie(profil, salaire_brut=80_000, audit=trace)

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
check("Tous les attributs identiques", all_eq)


# ============================================================
# TEST 2 — STRUCTURE
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure attendue de la trace Salarié")
print("=" * 95)

trace = TraceAudit(regime="Salarié")
calcul_module_salarie(profil, salaire_brut=80_000, audit=trace)

codes_obtenus = set(trace.codes())
check(f"Trace contient exactement les {len(CODES_ATTENDUS_SAL)} codes attendus",
      codes_obtenus == CODES_ATTENDUS_SAL)
manquants = CODES_ATTENDUS_SAL - codes_obtenus
extras = codes_obtenus - CODES_ATTENDUS_SAL
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
racines_attendues = CODES_ATTENDUS_SAL - set(PARENT_ATTENDU.keys())
check(f"10 racines attendues", racines_codes == racines_attendues)

check(f"Spec version {AUDIT_SPEC_VERSION}", trace.spec_version == AUDIT_SPEC_VERSION)

check("Tous les codes Salarié sont préfixés SAL_",
      all(c.startswith("SAL_") for c in codes_obtenus))


# ============================================================
# TEST 3 — COHÉRENCE VALEURS TRACÉES vs RÉSULTAT
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Cohérence valeurs tracées vs attributs du résultat")
print("=" * 95)

mapping_trace_resultat = {
    "SAL_SALAIRE_BRUT": "salaire_brut",
    "SAL_COTIS_SALARIALES": "cotis_salariales",
    "SAL_CSG_CRDS_TOTALE": "csg_crds_totale",
    "SAL_CSG_DEDUCTIBLE": "csg_deductible",
    "SAL_NET_AVANT_IMPOT": "net_avant_impot",
    "SAL_REVENU_SALARIAL_IMPOSABLE": "revenu_salarial_imposable",
    "SAL_ABATTEMENT_10PCT": "abattement_10pct",
    "SAL_REVENU_IMPOSABLE_NET": "revenu_imposable_net",
    "SAL_REVENU_IMPOSABLE_FOYER": "revenu_imposable_foyer",
    "SAL_IR_FOYER_BRUT": "ir_foyer",
    "SAL_CEHR": "cehr",
    "SAL_CDHR": "cdhr",
    "SAL_IMPOTS_IMPUTABLES_REM": "impots_imputables_rem",
    "SAL_NET_APRES_IMPOTS": "net_apres_impots",
}

trace = TraceAudit(regime="Salarié")
res = calcul_module_salarie(profil, salaire_brut=80_000, audit=trace)

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

# G2a a promu 3 nouvelles constantes — au moins l'une d'elles doit être citée
attendues_g2a = {"TX_CSG_DEDUCTIBLE", "TX_ABAT_10PCT_SAL", "PLAFOND_ABAT_10PCT_SAL"}
check("Au moins une constante promue G2a est citée",
      bool(attendues_g2a & refs_uniques),
      f"intersection={attendues_g2a & refs_uniques}")

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
# TEST 6 — CAS LIMITE : SALAIRE NUL
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Cas limite : salaire_brut = 0")
print("=" * 95)

trace_zero = TraceAudit(regime="Salarié")
res_zero = calcul_module_salarie(profil, salaire_brut=0, audit=trace_zero)

check("Trace complète même sans salaire",
      len(trace_zero.etapes) == len(CODES_ATTENDUS_SAL))
check("SAL_SALAIRE_BRUT = 0",
      abs(trace_zero.get("SAL_SALAIRE_BRUT").valeur) < TOL)
check("SAL_NET_APRES_IMPOTS = 0",
      abs(trace_zero.get("SAL_NET_APRES_IMPOTS").valeur) < TOL)


# ============================================================
# TEST 7 — RENDU CONSOLE
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Rendu console")
print("=" * 95)

rendu = rendre_trace_console(trace)
check("Rendu non-vide", len(rendu) > 1000)
check("En-tête régime", "AUDIT — Régime Salarié" in rendu)
check("Contient SAL_NET_APRES_IMPOTS", "SAL_NET_APRES_IMPOTS" in rendu)
check("Doctrine TX_SALARIAL résolue", "TX_SALARIAL=" in rendu)
check("Doctrine PLAFOND_ABAT_10PCT_SAL résolue (constante promue G2a)",
      "PLAFOND_ABAT_10PCT_SAL=14426" in rendu)
check("Pas de référence introuvable", "référence introuvable" not in rendu)


# ============================================================
# TEST 8 — ISOLATION DES ESPACES DE CODES
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Isolation des espaces de codes (SAL_* ⊥ {TNS_*, LIB_BNC_*, LIB_SEL_*})")
print("=" * 95)

# Tous les codes Salarié sont préfixés SAL_, donc disjoints des autres préfixes
check("Aucun code SAL_ ne commence par TNS_/LIB_",
      all(not c.startswith(("TNS_", "LIB_BNC_", "LIB_SEL_"))
          for c in CODES_ATTENDUS_SAL))

# Inversement : aucun autre préfixe ne se trouve dans nos codes
prefixes_autres = ("TNS_", "LIB_BNC_", "LIB_SEL_")
codes_avec_prefixe_etranger = [
    c for c in CODES_ATTENDUS_SAL
    if any(c.startswith(p) for p in prefixes_autres)
]
check("Aucun code Salarié n'utilise un préfixe étranger",
      not codes_avec_prefixe_etranger)


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Salarié passent")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
