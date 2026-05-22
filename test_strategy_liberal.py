"""
Tests dédiés Strategy Engine Libéral — Étape 3 Phase B.2.

Couvre les 4 règles d'acceptation validées :
1. L1 : BNC pur = référence sur même CA
2. L2 : BNC + PERIN = L1 + déduction PERIN individuelle par défaut
3. L3 : SEL IS = même CA, rémunération SEL saisie par l'EC (branche SELARL/SELAS)
4. L4 : SEL patrimonial minimal = L3 + mention "structuration avancée v2"

Garde-fous validés :
- forme_sel enum contrôlé (SELARL / SELAS)
- Pas de champ "recommandee" sur Libéral, utilisation de "plus_efficace_fiscalement"
- Alerte BNC/SEL permanente sur L3 et L4

4 cas représentatifs :
- A. BNC standard : recettes 150k, frais 30k, marié 2 parts → comparaison L1/L2
- B. SELARL : profession libérale gérante TNS
- C. SELAS : profession libérale dirigeante Assimilé
- D. Comparaison L1 vs L3 : même CA, validation Option B (comparabilité)
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dataclasses import fields
from strategy.liberal import (
    _calcul_strategie_l1, _calcul_strategie_l2,
    _calcul_strategie_l3, _calcul_strategie_l4,
    arbitrage_complet_liberal,
    ResultatStrategieLib, ResultatArbitrageLib,
    ALERTE_BNC_VS_SEL, ALERTE_L4_V2, MENTION_RETENTION_V2,
)
from core.profil import Profil, FORMES_SEL_VALIDES


def check(label, py, expected, tol=0.01):
    if isinstance(expected, bool):
        ok = py == expected
    elif isinstance(expected, (int, float)):
        ok = abs(py - expected) <= tol
    else:
        ok = py == expected
    return "✓" if ok else "✗", ok


# ============================================================
# CAS A — BNC standard : L1/L2 sur recettes 150k
# ============================================================
def test_cas_a_bnc_standard():
    print("=" * 90)
    print("  CAS A — BNC standard : recettes 150k, frais 30k, marié 2 parts")
    print("=" * 90)

    profil = Profil(
        forme_juridique="Profession libérale (BNC)",
        recettes_bnc=150_000, frais_pro_bnc=30_000,
        parts=2.0, situation="Marié / pacsé",
    )
    l1 = _calcul_strategie_l1(profil)
    l2 = _calcul_strategie_l2(profil)

    checks = [
        # L1 - règle 1 : référence sur même CA
        ("L1: structure = BNC", l1.structure, "BNC"),
        ("L1: recettes = recettes_bnc", l1.recettes, profil.recettes_bnc),
        ("L1: bénéfice brut = recettes - frais", l1.benefice_brut, 120_000.0),
        ("L1: pas d'IS (BNC sans société)", l1.is_societe, 0.0),
        ("L1: pas de dividendes", l1.dividendes_distribues, 0.0),
        ("L1: net dirigeant > 0", l1.net_dirigeant_total > 0, True),
        # L2 - règle 2 : L1 + PERIN
        ("L2: structure = BNC (même)", l2.structure, "BNC"),
        ("L2: versement PERIN > 0", l2.versement_perin > 0, True),
        ("L2: économie IR > 0", l2.economie_ir_perin > 0, True),
        ("L2: net >= L1 (PERIN apporte un gain)", l2.net_dirigeant_total >= l1.net_dirigeant_total, True),
        ("L2 = L1 + économie PERIN",
         l2.net_dirigeant_total, l1.net_dirigeant_total + l2.economie_ir_perin),
    ]
    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# CAS B — SELARL (gérant TNS)
# ============================================================
def test_cas_b_selarl():
    print("\n" + "=" * 90)
    print("  CAS B — SELARL : recettes 300k, frais 50k, rém SEL 80k (gérant TNS)")
    print("=" * 90)

    profil = Profil(
        forme_juridique="SELARL / SELAS",
        recettes_bnc=300_000, frais_pro_bnc=50_000,
        remuneration_sel_souhaitee=80_000,
        forme_sel="SELARL",
        capital_cca=100_000,
    )
    l3 = _calcul_strategie_l3(profil)

    # Cotisations attendues : 80k × 45% = 36k
    cotis_attendues = 80_000 * 0.45
    # Bénéfice avant IS = 300k - 50k - (80k + 36k) = 300k - 50k - 116k = 134k
    benefice_attendu = 300_000 - 50_000 - 80_000 - cotis_attendues

    checks = [
        ("L3 SELARL: structure", l3.structure, "SEL-SELARL"),
        ("L3 SELARL: cotisations = 45% × rém", l3.cotisations_sel, cotis_attendues),
        ("L3 SELARL: bénéfice avant IS", l3.benefice_brut, benefice_attendu),
        ("L3 SELARL: IS > 0", l3.is_societe > 0, True),
        ("L3 SELARL: dividendes = bénéfice - IS", l3.dividendes_distribues, benefice_attendu - l3.is_societe),
        ("L3 SELARL: alerte BNC/SEL présente",
         any("BNC / SEL" in a for a in l3.alertes), True),
        ("L3 SELARL: mention rétention v2 présente",
         any("Simplification v1" in a for a in l3.alertes), True),
        ("L3 SELARL: 2 alertes (BNC/SEL + rétention)", len(l3.alertes), 2),
    ]
    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# CAS C — SELAS (président Assimilé)
# ============================================================
def test_cas_c_selas():
    print("\n" + "=" * 90)
    print("  CAS C — SELAS : recettes 300k, frais 50k, rém SEL 80k (président Assimilé)")
    print("=" * 90)

    profil = Profil(
        forme_juridique="SELARL / SELAS",
        recettes_bnc=300_000, frais_pro_bnc=50_000,
        remuneration_sel_souhaitee=80_000,
        forme_sel="SELAS",
    )
    l3 = _calcul_strategie_l3(profil)

    # Cotisations patronales SELAS : 80k × 42% = 33,6k (PAS 45%)
    cotis_attendues = 80_000 * 0.42

    checks = [
        ("L3 SELAS: structure", l3.structure, "SEL-SELAS"),
        ("L3 SELAS: cotisations patronales = 42% × rém", l3.cotisations_sel, cotis_attendues),
        ("L3 SELAS: cotisations ≠ SELARL (45%)", l3.cotisations_sel != 80_000 * 0.45, True),
        ("L3 SELAS: net rémunération > 0", l3.net_remuneration > 0, True),
        ("L3 SELAS: dividendes au PFU > 0", l3.net_dividendes > 0, True),
    ]
    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# CAS D — Comparabilité L1 vs L3 (Option B)
# ============================================================
def test_cas_d_comparabilite_bnc_sel():
    print("\n" + "=" * 90)
    print("  CAS D — Comparabilité L1 vs L3 sur MÊME CA (Option B validée)")
    print("=" * 90)

    profil = Profil(
        forme_juridique="SELARL / SELAS",
        recettes_bnc=300_000, frais_pro_bnc=50_000,
        remuneration_sel_souhaitee=80_000,
        forme_sel="SELARL",
    )
    arb = arbitrage_complet_liberal(profil)

    l1, l2, l3, l4 = arb.strategies["L1"], arb.strategies["L2"], arb.strategies["L3"], arb.strategies["L4"]

    checks = [
        # Même CA pour les 4 stratégies (Option B)
        ("L1.recettes = L2.recettes", l1.recettes, l2.recettes),
        ("L1.recettes = L3.recettes", l1.recettes, l3.recettes),
        ("L1.recettes = L4.recettes", l1.recettes, l4.recettes),
        # L4 = L3 numériquement
        ("L4 net dirigeant = L3 net dirigeant", l4.net_dirigeant_total, l3.net_dirigeant_total),
        ("L4 IS = L3 IS", l4.is_societe, l3.is_societe),
        # L4 a 3 alertes (L3 + alerte v2)
        ("L4: 3 alertes (L3 alertes + v2)", len(l4.alertes), 3),
        ("L4: alerte L4 v2 présente",
         any("L4 — cadrage minimal v1" in a for a in l4.alertes), True),
    ]
    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# TESTS STRUCTURELS — Garde-fous méthodologiques
# ============================================================
def test_garde_fous_methodologiques():
    print("\n" + "=" * 90)
    print("  TESTS GARDE-FOUS méthodologiques")
    print("=" * 90)

    nb_ok = 0
    checks = []

    # Garde-fou 1 : forme_sel enum contrôlé
    try:
        Profil(forme_sel="INVALID")
        checks.append(("forme_sel rejette valeurs invalides", False, True))
    except ValueError:
        checks.append(("forme_sel rejette valeurs invalides", True, True))

    checks.append(("FORMES_SEL_VALIDES = ('SELARL', 'SELAS')", FORMES_SEL_VALIDES, ("SELARL", "SELAS")))

    # Garde-fou 2 : pas de champ 'recommandee' dans ResultatArbitrageLib
    champs_arb = {f.name for f in fields(ResultatArbitrageLib)}
    checks.append(("ResultatArbitrageLib: pas de champ 'recommandee'",
                   "recommandee" not in champs_arb, True))
    checks.append(("ResultatArbitrageLib: champ 'plus_efficace_fiscalement' présent",
                   "plus_efficace_fiscalement" in champs_arb, True))
    checks.append(("ResultatArbitrageLib: champ 'avertissement_bnc_sel' présent",
                   "avertissement_bnc_sel" in champs_arb, True))

    # Garde-fou 3 : avertissement BNC/SEL sur tous les arbitrages consolidés
    profil_bnc = Profil(forme_juridique="Profession libérale (BNC)")
    profil_selarl = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELARL")
    profil_selas = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELAS")

    for label_p, profil_p in [("BNC", profil_bnc), ("SELARL", profil_selarl), ("SELAS", profil_selas)]:
        arb_p = arbitrage_complet_liberal(profil_p)
        checks.append((f"Profil {label_p}: avertissement BNC/SEL renseigné",
                       arb_p.avertissement_bnc_sel == ALERTE_BNC_VS_SEL, True))

    # Garde-fou 4 : alerte BNC/SEL présente sur TOUS les résultats L3 et L4
    arb = arbitrage_complet_liberal(profil_selarl)
    l3_has = any("BNC / SEL" in a for a in arb.strategies["L3"].alertes)
    l4_has = any("BNC / SEL" in a for a in arb.strategies["L4"].alertes)
    checks.append(("L3: alerte BNC/SEL présente", l3_has, True))
    checks.append(("L4: alerte BNC/SEL présente", l4_has, True))

    # Garde-fou 5 : L1 et L2 N'ONT PAS d'alerte BNC/SEL (car ce sont du BNC pur)
    l1_no = not any("BNC / SEL" in a for a in arb.strategies["L1"].alertes)
    l2_no = not any("BNC / SEL" in a for a in arb.strategies["L2"].alertes)
    checks.append(("L1: pas d'alerte BNC/SEL (BNC pur)", l1_no, True))
    checks.append(("L2: pas d'alerte BNC/SEL (BNC pur)", l2_no, True))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:60s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# EXÉCUTION
# ============================================================
if __name__ == "__main__":
    r_a = test_cas_a_bnc_standard()
    r_b = test_cas_b_selarl()
    r_c = test_cas_c_selas()
    r_d = test_cas_d_comparabilite_bnc_sel()
    r_g = test_garde_fous_methodologiques()

    print("\n" + "=" * 90)
    print("  SYNTHÈSE TESTS STRATEGY LIBÉRAL")
    print("=" * 90)
    print(f"  Cas A (BNC standard L1/L2)        : {r_a[0]}/{r_a[1]}")
    print(f"  Cas B (SELARL, gérant TNS)        : {r_b[0]}/{r_b[1]}")
    print(f"  Cas C (SELAS, président Assimilé) : {r_c[0]}/{r_c[1]}")
    print(f"  Cas D (Comparabilité L1 vs L3)    : {r_d[0]}/{r_d[1]}")
    print(f"  Garde-fous méthodologiques        : {r_g[0]}/{r_g[1]}")

    total_ok = sum(r[0] for r in [r_a, r_b, r_c, r_d, r_g])
    total = sum(r[1] for r in [r_a, r_b, r_c, r_d, r_g])
    print(f"\n  TOTAL : {total_ok}/{total}")
    sys.exit(0 if total_ok == total else 1)
