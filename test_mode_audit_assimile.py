"""
test_mode_audit_assimile.py — Tests dédiés à l'instrumentation MODE_AUDIT du
module Assimilé (G2b : helpers `calcul_tx_ir_moyen` + `fs_moyen_epargne`).

Spécificité G2b : le module Assimilé n'a pas de `calcul_module_assimile()`
global comme TNS/BNC/SEL/Salarié. Il expose deux helpers consommés par le
Strategy Engine. La vraie logique stratégique A/B/C/D vit dans
`strategy/assimile.py` (sera instrumentée en G3).

Vérifie pour chaque helper :
1. Rétrocompat parfaite (audit=None ⇒ valeur retournée strictement identique)
2. Structure attendue de la trace (codes, hiérarchie, comptage)
3. Cohérence entre valeur finale tracée et valeur retournée
4. Résolution doctrinale pour tous les doctrine_refs cités
5. Unicité des codes dans la trace
6. Cas limites
7. Rendu console
8. Isolation des espaces de codes

Usage : python3 test_mode_audit_assimile.py
Exit code 0 si tous les tests passent.
"""

import sys

from core.profil import Profil
from core.audit import TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref
from regime.assimile import calcul_tx_ir_moyen, fs_moyen_epargne
from ui.audit_render import rendre_trace_console


# ============================================================
# REGISTRES — Contrat G2b
# ============================================================
CODES_ATTENDUS_TX_IR_MOY = {
    "ASSIM_TX_IR_MOY_BRUT_REF",
    "ASSIM_TX_IR_MOY_COTIS_SALARIALES",
    "ASSIM_TX_IR_MOY_CSG_CRDS",
    "ASSIM_TX_IR_MOY_CSG_DEDUCTIBLE",
    "ASSIM_TX_IR_MOY_NET_AVANT_IR",
    "ASSIM_TX_IR_MOY_REV_SAL_IMP",
    "ASSIM_TX_IR_MOY_ABATTEMENT",
    "ASSIM_TX_IR_MOY_REV_IMP_NET",
    "ASSIM_TX_IR_MOY_REV_IMP_FOYER",
    "ASSIM_TX_IR_MOY_TOTAL_IMPOTS",
    "ASSIM_TX_IR_MOY_RESULTAT",
}

CODES_ATTENDUS_FS = {
    "ASSIM_FS_MOYEN",
}

# Union utile pour tests d'isolation
CODES_ATTENDUS_ASSIM = CODES_ATTENDUS_TX_IR_MOY | CODES_ATTENDUS_FS


# ============================================================
# OUTIL DE TEST
# ============================================================
TOL = 0.0001
echecs = []


def check(label, condition, detail=""):
    marker = "✓" if condition else "✗"
    suffix = f"  ({detail})" if detail else ""
    print(f"  {marker} {label}{suffix}")
    if not condition:
        echecs.append(label)


# ════════════════════════════════════════════════════════════════════════════
# PARTIE 1 — INSTRUMENTATION calcul_tx_ir_moyen
# ════════════════════════════════════════════════════════════════════════════

profil = Profil()


# ============================================================
# TEST 1 — RÉTROCOMPAT calcul_tx_ir_moyen
# ============================================================
print("=" * 95)
print("  TEST 1 — Rétrocompat parfaite calcul_tx_ir_moyen (audit=None ⇒ historique)")
print("=" * 95)

tx_sans = calcul_tx_ir_moyen(profil)
trace_tx = TraceAudit(regime="Assimilé (TX_IR_MOY)")
tx_avec = calcul_tx_ir_moyen(profil, audit=trace_tx)

check("Valeur retournée identique avec/sans audit",
      abs(tx_sans - tx_avec) < TOL,
      f"sans={tx_sans}, avec={tx_avec}")


# ============================================================
# TEST 2 — STRUCTURE TX_IR_MOY
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure attendue de la trace TX_IR_MOY")
print("=" * 95)

codes_obtenus = set(trace_tx.codes())
check(f"Trace contient exactement les {len(CODES_ATTENDUS_TX_IR_MOY)} codes attendus",
      codes_obtenus == CODES_ATTENDUS_TX_IR_MOY)
manquants = CODES_ATTENDUS_TX_IR_MOY - codes_obtenus
extras = codes_obtenus - CODES_ATTENDUS_TX_IR_MOY
if manquants:
    check("Aucun code manquant", False, f"manquants={manquants}")
if extras:
    check("Aucun code en trop", False, f"extras={extras}")

check(f"Spec version {AUDIT_SPEC_VERSION}", trace_tx.spec_version == AUDIT_SPEC_VERSION)

check("Tous les codes TX_IR_MOY préfixés ASSIM_TX_IR_MOY_",
      all(c.startswith("ASSIM_TX_IR_MOY_") for c in codes_obtenus))

# Pour ce helper, toutes les étapes sont à plat (pas de parent_id) — c'est un calcul
# linéaire, pas une agrégation. C'est un choix de design assumé : la hiérarchie ne
# serait pas pertinente ici (chaque étape consomme la précédente).
profondeurs = [0 if e.parent_id is None else 1 for e in trace_tx.etapes]
check("Trace TX_IR_MOY linéaire (toutes étapes racines)",
      all(p == 0 for p in profondeurs))


# ============================================================
# TEST 3 — COHÉRENCE VALEUR FINALE
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Valeur finale tracée vs valeur retournée")
print("=" * 95)

v_finale = trace_tx.get("ASSIM_TX_IR_MOY_RESULTAT").valeur
check("ASSIM_TX_IR_MOY_RESULTAT == valeur retournée",
      abs(v_finale - tx_avec) < TOL,
      f"trace={v_finale}, retour={tx_avec}")

# Vérification de la séquence logique : net = brut - cotis - csg_crds
brut = trace_tx.get("ASSIM_TX_IR_MOY_BRUT_REF").valeur
cotis = trace_tx.get("ASSIM_TX_IR_MOY_COTIS_SALARIALES").valeur
csg = trace_tx.get("ASSIM_TX_IR_MOY_CSG_CRDS").valeur
net = trace_tx.get("ASSIM_TX_IR_MOY_NET_AVANT_IR").valeur
check("Cohérence net_avant_ir = brut − cotis − csg_crds",
      abs(brut - cotis - csg - net) < TOL,
      f"{brut} − {cotis} − {csg} = {brut-cotis-csg} vs {net}")


# ============================================================
# TEST 4 — RÉSOLUTION DOCTRINALE TX_IR_MOY
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Tous les doctrine_refs TX_IR_MOY se résolvent")
print("=" * 95)

refs_uniques = set()
for etape in trace_tx.etapes:
    refs_uniques.update(etape.doctrine_refs)

check(f"{len(refs_uniques)} doctrine_refs uniques",
      len(refs_uniques) > 0,
      f"refs={sorted(refs_uniques)}")

# Les 6 constantes promues + 4 plafonds IR doivent être citables
attendues = {"TX_SALARIAL", "ASSIETTE_CSG_SAL", "TX_CSG_CRDS_ACT",
             "TX_CSG_DEDUCTIBLE", "TX_ABAT_10PCT_SAL", "PLAFOND_ABAT_10PCT_SAL",
             "IR_PLAFOND_T1", "IR_PLAFOND_T2", "IR_PLAFOND_T3", "IR_PLAFOND_T4"}
check("Toutes les constantes attendues sont citées",
      attendues.issubset(refs_uniques),
      f"manquantes={attendues - refs_uniques}")

for ref in sorted(refs_uniques):
    try:
        valeur = resoudre_doctrine_ref(ref)
        check(f"Résolution {ref} = {valeur}", True)
    except AttributeError as e:
        check(f"Résolution {ref}", False, str(e))

# Cohérence hypotheses ⇔ doctrine_refs
for etape in trace_tx.etapes:
    for ref in etape.doctrine_refs:
        if ref in etape.hypotheses:
            try:
                v_doc = resoudre_doctrine_ref(ref)
                check(f"{etape.code}: hyp[{ref}] == doctrine",
                      etape.hypotheses[ref] == v_doc,
                      f"hyp={etape.hypotheses[ref]}, doctrine={v_doc}")
            except AttributeError:
                pass


# ============================================================
# TEST 5 — UNICITÉ
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Unicité des codes")
print("=" * 95)

codes = trace_tx.codes()
check(f"Tous les codes TX_IR_MOY uniques ({len(codes)} étapes)",
      len(codes) == len(set(codes)))


# ============================================================
# TEST 6 — PLANCHER 5 % v19
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Plancher v19 (5 %) tracé via hypotheses")
print("=" * 95)

resultat = trace_tx.get("ASSIM_TX_IR_MOY_RESULTAT")
check("Hypothèse 'plancher_v19' présente",
      "plancher_v19" in resultat.hypotheses,
      f"hypotheses={resultat.hypotheses}")
check("Hypothèse 'tx_moy_avant_plancher' présente",
      "tx_moy_avant_plancher" in resultat.hypotheses)
check("Plancher v19 = 0.05",
      resultat.hypotheses.get("plancher_v19") == 0.05)


# ════════════════════════════════════════════════════════════════════════════
# PARTIE 2 — INSTRUMENTATION fs_moyen_epargne
# ════════════════════════════════════════════════════════════════════════════


# ============================================================
# TEST 7 — RÉTROCOMPAT fs_moyen_epargne
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Rétrocompat fs_moyen_epargne")
print("=" * 95)

fs_sans = fs_moyen_epargne(profil)
trace_fs = TraceAudit(regime="Assimilé (FS)")
fs_avec = fs_moyen_epargne(profil, audit=trace_fs)
check("Valeur retournée identique avec/sans audit", fs_sans == fs_avec)


# ============================================================
# TEST 8 — STRUCTURE FS
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Structure attendue de la trace FS")
print("=" * 95)

codes_fs = set(trace_fs.codes())
check(f"Trace FS contient {len(CODES_ATTENDUS_FS)} code",
      codes_fs == CODES_ATTENDUS_FS)
check("Tous les codes FS préfixés ASSIM_FS_",
      all(c.startswith("ASSIM_FS_") for c in codes_fs))

etape_fs = trace_fs.get("ASSIM_FS_MOYEN")
check("Hypothèse 'effectif_profil' présente",
      "effectif_profil" in etape_fs.hypotheses)
check("Table FS complète en hypotheses (3 paliers)",
      all(k in etape_fs.hypotheses
          for k in ("fs_sans_salarie_11_49", "fs_50_249", "fs_250_plus")))


# ============================================================
# TEST 9 — COMPORTEMENT FS PAR EFFECTIF
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Comportement fs_moyen_epargne selon effectif")
print("=" * 95)

import dataclasses
cas = [
    ("Sans salarié",     0.0),
    ("1-10 salariés",    0.0),
    ("11-49 salariés",   0.0),
    ("50-249 salariés",  0.133),
    ("≥ 250 salariés",   0.20),
]
for effectif, fs_attendu in cas:
    p = dataclasses.replace(profil, effectif=effectif)
    trace_cas = TraceAudit(regime=f"Assimilé (FS test {effectif})")
    fs_obtenu = fs_moyen_epargne(p, audit=trace_cas)
    check(f"effectif={effectif:20s} → fs={fs_attendu}",
          abs(fs_obtenu - fs_attendu) < TOL,
          f"obtenu={fs_obtenu}")
    # Vérifier que la trace renvoie la même valeur
    v_trace = trace_cas.get("ASSIM_FS_MOYEN").valeur
    check(f"  trace cohérente pour {effectif}",
          abs(v_trace - fs_attendu) < TOL)


# ============================================================
# TEST 10 — RENDU CONSOLE
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Rendu console des deux traces")
print("=" * 95)

rendu_tx = rendre_trace_console(trace_tx)
check("Rendu TX_IR_MOY non-vide", len(rendu_tx) > 1000)
check("Contient ASSIM_TX_IR_MOY_RESULTAT", "ASSIM_TX_IR_MOY_RESULTAT" in rendu_tx)
check("Doctrine TX_CSG_DEDUCTIBLE résolue", "TX_CSG_DEDUCTIBLE=" in rendu_tx)
check("Pas de référence introuvable (TX_IR_MOY)",
      "référence introuvable" not in rendu_tx)

rendu_fs = rendre_trace_console(trace_fs)
check("Rendu FS non-vide", len(rendu_fs) > 200)
check("Contient ASSIM_FS_MOYEN", "ASSIM_FS_MOYEN" in rendu_fs)


# ============================================================
# TEST 11 — ISOLATION DES ESPACES DE CODES
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Isolation ASSIM_* ⊥ {TNS_*, LIB_BNC_*, LIB_SEL_*, SAL_*}")
print("=" * 95)

prefixes_etrangers = ("TNS_", "LIB_BNC_", "LIB_SEL_", "SAL_")

check("Aucun code ASSIM_ n'utilise un préfixe étranger",
      all(not any(c.startswith(p) for p in prefixes_etrangers)
          for c in CODES_ATTENDUS_ASSIM))
check("Tous les codes ASSIM_ préfixés ASSIM_",
      all(c.startswith("ASSIM_") for c in CODES_ATTENDUS_ASSIM))
check("Sous-domaines bien distincts",
      CODES_ATTENDUS_TX_IR_MOY.isdisjoint(CODES_ATTENDUS_FS))


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Assimilé passent (G2b)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
