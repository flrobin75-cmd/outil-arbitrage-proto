"""
Tests PERIN mutualisé - validation par cohérence interne.

4 cas représentatifs :
- Cas 1 : Célibataire (pas de mutualisation possible)
- Cas 2 : Marié sans conjoint déclaré (pas de mutualisation)
- Cas 3 : Marié avec conjoint déclaré, versement sous plafond mutualisé
- Cas 4 : Marié avec conjoint déclaré, versement dépassant plafond mutualisé (excédent)
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from strategy.perin import (
    calcul_plafond_perin, calcul_perin_mutualise,
    PERIN_PLAFOND_MIN, PERIN_PLAFOND_MAX,
)


def fmt(v):
    if isinstance(v, float):
        return f"{v:,.2f}".replace(",", " ")
    return str(v)


def check(label, py, expected, tol=0.01):
    if isinstance(expected, bool):
        ok = py == expected
    elif isinstance(expected, (int, float)):
        ok = abs(py - expected) <= tol
    else:
        ok = py == expected
    return "✓" if ok else "✗", ok


# ============================================================
# CAS 1 : Célibataire - pas de mutualisation possible
# ============================================================
def test_1_celibataire():
    print("=" * 100)
    print("  CAS 1 — Célibataire (pas de mutualisation possible)")
    print("=" * 100)

    res = calcul_perin_mutualise(
        versement_dirigeant=5_000,
        revenu_pro_dirigeant=60_000,
        tmi_dirigeant=0.30,
        situation="Célibataire / divorcé / veuf",
        conjoint_declare=False,
    )

    # Plafond individuel attendu : max(10% × 60k=6000 ; 10% PASS=4806) = 6 000 €
    plafond_attendu = 6_000.00
    economie_attendue = 5_000 * 0.30   # 1 500 €

    checks = [
        ("Plafond individuel dirigeant", res.plafond_dirigeant.plafond_individuel, plafond_attendu),
        ("Mutualisation active", res.mutualisation_active, False),
        ("Plafond mutualisé = individuel", res.plafond_mutualise_total, plafond_attendu),
        ("Versement couvert", res.versement_dirigeant_couvert, 5_000),
        ("Excédent", res.versement_excedent, 0),
        ("Économie IR", res.economie_ir, economie_attendue),
        ("Conjoint absent", res.plafond_conjoint, None),
    ]

    ok_count = 0
    for label, py, expected in checks:
        marker, is_ok = check(label, py, expected)
        py_str = fmt(py) if py is not None else "None"
        exp_str = fmt(expected) if expected is not None else "None"
        print(f"  {marker} {label:42s} obtenu={py_str:>15s}  attendu={exp_str:>15s}")
        if is_ok: ok_count += 1
    print(f"\n  Résultat : {ok_count}/{len(checks)}\n")
    return ok_count, len(checks)


# ============================================================
# CAS 2 : Marié sans conjoint déclaré
# ============================================================
def test_2_marie_sans_conjoint():
    print("=" * 100)
    print("  CAS 2 — Marié sans conjoint déclaré (pas de mutualisation)")
    print("=" * 100)

    res = calcul_perin_mutualise(
        versement_dirigeant=8_000,
        revenu_pro_dirigeant=70_000,
        tmi_dirigeant=0.30,
        situation="Marié / pacsé",
        conjoint_declare=False,
    )

    # Plafond individuel attendu : max(10% × 70k=7000 ; 4806) = 7 000 €
    plafond_indiv = 7_000.00
    # Versement 8 000 > plafond 7 000 → 1 000 € d'excédent
    excedent_attendu = 1_000.00
    economie_attendue = 7_000 * 0.30   # versement couvert × TMI

    checks = [
        ("Plafond individuel dirigeant", res.plafond_dirigeant.plafond_individuel, plafond_indiv),
        ("Mutualisation active", res.mutualisation_active, False),
        ("Versement couvert (limite plafond)", res.versement_dirigeant_couvert, 7_000),
        ("Excédent détecté", res.versement_excedent, excedent_attendu),
        ("Économie IR sur couvert", res.economie_ir, economie_attendue),
    ]

    ok_count = 0
    for label, py, expected in checks:
        marker, is_ok = check(label, py, expected)
        print(f"  {marker} {label:42s} obtenu={fmt(py):>15s}  attendu={fmt(expected):>15s}")
        if is_ok: ok_count += 1
    print(f"\n  Résultat : {ok_count}/{len(checks)}\n")
    return ok_count, len(checks)


# ============================================================
# CAS 3 : Mutualisation conjoint, versement sous plafond mutualisé
# ============================================================
def test_3_mutualisation_sous_plafond():
    print("=" * 100)
    print("  CAS 3 — Marié avec conjoint, versement sous plafond mutualisé")
    print("=" * 100)

    # Dirigeant : rev. pro 70k → plafond 7 000 €
    # Conjoint : rev. pro 50k → plafond 5 000 €, déjà versé 1 000 € → solde 4 000 €
    # Plafond mutualisé : 7 000 + 4 000 = 11 000 €
    # Versement dirigeant 10 000 € < 11 000 € → entièrement couvert
    res = calcul_perin_mutualise(
        versement_dirigeant=10_000,
        revenu_pro_dirigeant=70_000,
        tmi_dirigeant=0.41,
        situation="Marié / pacsé",
        conjoint_declare=True,
        revenu_pro_conjoint=50_000,
        versement_conjoint=1_000,
    )

    plafond_dir = 7_000.00
    plafond_conj = 5_000.00
    solde_conj = 4_000.00
    plafond_mut = 11_000.00
    economie_attendue = 10_000 * 0.41   # 4 100 €

    checks = [
        ("Plafond individuel dirigeant", res.plafond_dirigeant.plafond_individuel, plafond_dir),
        ("Plafond individuel conjoint", res.plafond_conjoint.plafond_individuel, plafond_conj),
        ("Versement conjoint", res.plafond_conjoint.versement_effectif, 1_000),
        ("Solde disponible conjoint", res.plafond_conjoint.solde_disponible, solde_conj),
        ("Mutualisation active", res.mutualisation_active, True),
        ("Plafond mutualisé total", res.plafond_mutualise_total, plafond_mut),
        ("Versement couvert", res.versement_dirigeant_couvert, 10_000),
        ("Excédent", res.versement_excedent, 0),
        ("Économie IR", res.economie_ir, economie_attendue),
    ]

    ok_count = 0
    for label, py, expected in checks:
        marker, is_ok = check(label, py, expected)
        print(f"  {marker} {label:42s} obtenu={fmt(py):>15s}  attendu={fmt(expected):>15s}")
        if is_ok: ok_count += 1
    print(f"\n  Résultat : {ok_count}/{len(checks)}\n")
    return ok_count, len(checks)


# ============================================================
# CAS 4 : Mutualisation conjoint, versement dépassant plafond mutualisé
# ============================================================
def test_4_mutualisation_excedent():
    print("=" * 100)
    print("  CAS 4 — Marié avec conjoint, versement dépassant plafond mutualisé")
    print("=" * 100)

    # Dirigeant rev pro 80k → plafond 8 000 €
    # Conjoint rev pro 40k → plafond 4 806 € (plancher 10% PASS car 10%×40k=4000<4806)
    # Conjoint a déjà versé 2 000 € → solde 2 806 €
    # Plafond mutualisé = 8 000 + 2 806 = 10 806 €
    # Versement 15 000 € > 10 806 € → excédent 4 194 €
    res = calcul_perin_mutualise(
        versement_dirigeant=15_000,
        revenu_pro_dirigeant=80_000,
        tmi_dirigeant=0.41,
        situation="Marié / pacsé",
        conjoint_declare=True,
        revenu_pro_conjoint=40_000,
        versement_conjoint=2_000,
    )

    plafond_dir = 8_000.00
    plafond_conj = 4_806.00       # plancher 10 % PASS
    solde_conj = 2_806.00
    plafond_mut = 10_806.00
    excedent_attendu = 4_194.00
    economie_attendue = 10_806 * 0.41   # versement couvert × TMI

    checks = [
        ("Plafond individuel dirigeant", res.plafond_dirigeant.plafond_individuel, plafond_dir),
        ("Plafond individuel conjoint (plancher)", res.plafond_conjoint.plafond_individuel, plafond_conj),
        ("Solde disponible conjoint", res.plafond_conjoint.solde_disponible, solde_conj),
        ("Plafond mutualisé total", res.plafond_mutualise_total, plafond_mut),
        ("Versement couvert (limite mut.)", res.versement_dirigeant_couvert, plafond_mut),
        ("Excédent détecté", res.versement_excedent, excedent_attendu),
        ("Économie IR sur couvert", res.economie_ir, economie_attendue),
    ]

    ok_count = 0
    for label, py, expected in checks:
        marker, is_ok = check(label, py, expected)
        print(f"  {marker} {label:42s} obtenu={fmt(py):>15s}  attendu={fmt(expected):>15s}")
        if is_ok: ok_count += 1
    print(f"\n  Résultat : {ok_count}/{len(checks)}\n")
    return ok_count, len(checks)


# ============================================================
# EXÉCUTION
# ============================================================
if __name__ == "__main__":
    r1 = test_1_celibataire()
    r2 = test_2_marie_sans_conjoint()
    r3 = test_3_mutualisation_sous_plafond()
    r4 = test_4_mutualisation_excedent()

    print("=" * 100)
    print("  SYNTHÈSE TESTS PERIN MUTUALISÉ")
    print("=" * 100)
    print(f"  Cas 1 (célibataire)                 : {r1[0]}/{r1[1]}")
    print(f"  Cas 2 (marié sans conjoint déclaré) : {r2[0]}/{r2[1]}")
    print(f"  Cas 3 (mutualisation sous plafond)  : {r3[0]}/{r3[1]}")
    print(f"  Cas 4 (mutualisation excédent)      : {r4[0]}/{r4[1]}")
    total_ok = r1[0]+r2[0]+r3[0]+r4[0]
    total = r1[1]+r2[1]+r3[1]+r4[1]
    print(f"\n  TOTAL : {total_ok}/{total}")
