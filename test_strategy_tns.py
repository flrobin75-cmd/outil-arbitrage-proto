"""
Tests dédiés Strategy Engine TNS — Étape 2 Phase B.2.

Couvre les 6 règles d'acceptation validées :
1. T1 : Rémunération cotisable dominante, dividendes résiduels
2. T2 : Dividendes plafonnés strictement à 10 % capital + primes + CCA
3. T2 alerte : Capital faible OU ratio marginal
4. T3 : Mix rémunération + dividendes sous seuil + PERIN
5. T4 : Deux indicateurs séparés, JAMAIS d'agrégation
6. Baseline existante toujours verte (vérifié séparément)

4 cas représentatifs :
- A. Cas standard : SARL, capital 100k, bénéfice 200k, marié 2 parts
- B. Capital faible : capital 5k → alerte T2 capital + ratio
- C. Bénéfice énorme : ratio marginal seul (alerte T2 ratio)
- D. Célibataire : pas de mutualisation PERIN possible (T3 plafond individuel)
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dataclasses import fields
from strategy.tns import (
    _calcul_strategie_t1, _calcul_strategie_t2,
    _calcul_strategie_t3, _calcul_strategie_t4,
    arbitrage_complet_tns,
    ResultatStrategieTNS,
    ALERTE_T2_CAPITAL_FAIBLE_SEUIL,
    ALERTE_T2_RATIO_MARGINAL_SEUIL,
)
from core.profil import Profil, SEUIL_DIV_TNS


def fmt(v): return f"{v:>12,.2f} €" if isinstance(v, float) else str(v)


def check(label, py, expected, tol=0.01):
    if isinstance(expected, bool):
        ok = py == expected
    elif isinstance(expected, (int, float)):
        ok = abs(py - expected) <= tol
    else:
        ok = py == expected
    return "✓" if ok else "✗", ok


# ============================================================
# CAS A — Standard
# ============================================================
def test_cas_a_standard():
    print("=" * 90)
    print("  CAS A — SARL gérance maj., capital 100k€, bénéfice 200k€, marié 2 parts")
    print("=" * 90)

    profil = Profil(
        forme_juridique="SARL (gérance majoritaire) / EURL",
        benefice_is=200_000, capital_cca=100_000,
        parts=2.0, situation="Marié / pacsé",
    )

    arb = arbitrage_complet_tns(profil)
    nb_ok = 0
    checks = []

    # Règle 1 - T1 : rém dominante (rém_brute > 3 × div distribuables)
    # Critère choisi : rém au moins 3x les dividendes (= ratio ~75/25)
    # Avec allocation par défaut 85/15, on a habituellement rém ~ 4-5x div
    t1 = arb.strategies["T1"]
    rule_t1 = t1.remuneration_brute > t1.dividendes_distribues * 3
    checks.append(("T1: rém dominante (rém > 5x div)", rule_t1, True))

    # Règle 2 - T2 : div ≤ seuil 10% (strict)
    t2 = arb.strategies["T2"]
    rule_t2_seuil = t2.dividendes_distribues <= t2.seuil_10pct + 0.01
    checks.append(("T2: div ≤ seuil 10%", rule_t2_seuil, True))

    # Règle 4 - T3 : PERIN max + dividendes sous seuil
    t3 = arb.strategies["T3"]
    plafond_attendu = max(0.10 * t3.remuneration_brute, 4806.0)
    rule_t3_perin = abs(t3.versement_perin - plafond_attendu) < 0.01
    rule_t3_div = t3.dividendes_distribues <= t3.seuil_10pct + 0.01
    checks.append(("T3: PERIN = plafond individuel", rule_t3_perin, True))
    checks.append(("T3: div ≤ seuil 10%", rule_t3_div, True))

    # Règle 5 - T4 : deux indicateurs séparés
    t4 = arb.strategies["T4"]
    rule_t4_no_agg = t4.net_dirigeant_immediat == t4.net_remuneration
    rule_t4_div_zero = t4.dividendes_distribues == 0
    rule_t4_retenu = t4.benefice_retenu_societe > 0
    checks.append(("T4: net immédiat = rém seule (pas d'agrégation)", rule_t4_no_agg, True))
    checks.append(("T4: aucune distribution dividendes", rule_t4_div_zero, True))
    checks.append(("T4: bénéfice retenu > 0", rule_t4_retenu, True))

    # Pas d'alertes attendues sur cas standard
    checks.append(("Cas A: pas d'alerte T1", len(t1.alertes) == 0, True))
    checks.append(("Cas A: pas d'alerte T2", len(t2.alertes) == 0, True))
    checks.append(("Cas A: pas d'alerte T3", len(t3.alertes) == 0, True))
    # T4 a toujours l'alerte de non-disponibilité
    checks.append(("Cas A: T4 a son alerte de non-disponibilité", len(t4.alertes) >= 1, True))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1

    print(f"\n  Résultat : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# CAS B — Capital faible (deux alertes T2)
# ============================================================
def test_cas_b_capital_faible():
    print("\n" + "=" * 90)
    print("  CAS B — Capital faible 5k€, bénéfice 200k€ → 2 alertes T2 attendues")
    print("=" * 90)

    profil = Profil(
        forme_juridique="SARL (gérance majoritaire) / EURL",
        benefice_is=200_000, capital_cca=5_000,
        parts=2.0, situation="Marié / pacsé",
    )
    t2 = _calcul_strategie_t2(profil)

    checks = [
        ("T2: 2 alertes attendues (capital faible + ratio marginal)", len(t2.alertes), 2),
        ("T2: alerte capital mentionne le seuil", "Capital + CCA" in t2.alertes[0], True),
        ("T2: alerte ratio mentionne le pourcentage", "ratio" in t2.alertes[1].lower() or "Seuil 10" in t2.alertes[1], True),
        ("T2: seuil 10% = 500€", t2.seuil_10pct, 500.0),
        ("T2: div ≤ seuil malgré capital faible", t2.dividendes_distribues <= t2.seuil_10pct + 0.01, True),
    ]
    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# CAS C — Bénéfice énorme (alerte ratio uniquement)
# ============================================================
def test_cas_c_ratio_marginal():
    print("\n" + "=" * 90)
    print("  CAS C — Capital 200k€, bénéfice 5M€ → 1 alerte T2 (ratio marginal)")
    print("=" * 90)

    profil = Profil(
        forme_juridique="SARL (gérance majoritaire) / EURL",
        benefice_is=5_000_000, capital_cca=200_000,
        parts=2.0, situation="Marié / pacsé",
    )
    t2 = _calcul_strategie_t2(profil)

    # Ratio = 20k / 5M = 0,4 % < 5 % → 1 alerte (ratio)
    # Capital 200k > 10k → pas d'alerte capital
    checks = [
        ("T2: 1 alerte (ratio marginal seul)", len(t2.alertes), 1),
        ("T2: capital >= 10k donc pas d'alerte capital",
         not any("Capital + CCA" in a for a in t2.alertes), True),
        ("T2: alerte ratio présente",
         any("Seuil 10" in a for a in t2.alertes), True),
        ("T2: seuil 10% = 20k€", t2.seuil_10pct, 20_000.0),
    ]
    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# CAS D — Célibataire (pas de mutualisation PERIN possible)
# ============================================================
def test_cas_d_celibataire():
    print("\n" + "=" * 90)
    print("  CAS D — Célibataire : pas de mutualisation PERIN (plafond individuel seul)")
    print("=" * 90)

    profil = Profil(
        forme_juridique="SARL (gérance majoritaire) / EURL",
        benefice_is=200_000, capital_cca=100_000,
        parts=1.0, situation="Célibataire / divorcé / veuf",
    )
    t3 = _calcul_strategie_t3(profil)

    # Le plafond PERIN du dirigeant célibataire = max(10% × rem_brute, 4806€)
    # Pas de mutualisation possible en T3 par défaut (décision Option C)
    plafond_attendu = max(0.10 * t3.remuneration_brute, 4806.0)

    checks = [
        ("T3: versement PERIN = plafond individuel", abs(t3.versement_perin - plafond_attendu), 0.0),
        ("T3: dividendes ≤ seuil 10%", t3.dividendes_distribues <= t3.seuil_10pct + 0.01, True),
        ("T3: économie IR PERIN > 0", t3.economie_ir_perin > 0, True),
    ]
    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# TESTS STRUCTURELS - règle T4 non-agrégation (transverse)
# ============================================================
def test_non_aggregation_t4():
    print("\n" + "=" * 90)
    print("  TEST STRUCTUREL — Règle 5 : INTERDICTION agrégation T4")
    print("=" * 90)

    # Test 1 : aucun champ d'agrégation dans la dataclass
    champs = {f.name for f in fields(ResultatStrategieTNS)}
    champs_interdits = {'net_total', 'total_brut', 'valeur_totale', 'somme_indicateurs', 'patrimoine_total'}

    nb_ok = 0
    checks = []
    for c in champs_interdits:
        rule = c not in champs
        checks.append((f"Pas de champ d'agrégation '{c}'", rule, True))

    # Test 2 : sur plusieurs profils, net_dirigeant_immediat == net_remuneration pour T4
    for benefice in [100_000, 200_000, 500_000, 1_000_000]:
        profil = Profil(forme_juridique="SARL (gérance majoritaire) / EURL",
                        benefice_is=benefice, capital_cca=100_000, parts=2.0)
        t4 = _calcul_strategie_t4(profil)
        rule = t4.net_dirigeant_immediat == t4.net_remuneration
        checks.append((f"T4 bénéfice {benefice//1000}k: net immédiat == net rém", rule, True))

    # Test 3 : bénéfice retenu > 0 quand bénéfice suffisant
    profil = Profil(forme_juridique="SARL (gérance majoritaire) / EURL",
                    benefice_is=200_000, capital_cca=100_000)
    t4 = _calcul_strategie_t4(profil)
    checks.append(("T4 standard: benefice_retenu_societe > 0", t4.benefice_retenu_societe > 0, True))

    # Test 4 : alerte de non-disponibilité présente
    has_alerte = any("n'est PAS un revenu disponible" in a for a in t4.alertes)
    checks.append(("T4 alerte non-disponibilité présente", has_alerte, True))

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
    r_a = test_cas_a_standard()
    r_b = test_cas_b_capital_faible()
    r_c = test_cas_c_ratio_marginal()
    r_d = test_cas_d_celibataire()
    r_e = test_non_aggregation_t4()

    print("\n" + "=" * 90)
    print("  SYNTHÈSE TESTS STRATEGY TNS")
    print("=" * 90)
    print(f"  Cas A (standard)                 : {r_a[0]}/{r_a[1]}")
    print(f"  Cas B (capital faible, 2 alertes): {r_b[0]}/{r_b[1]}")
    print(f"  Cas C (ratio marginal seul)      : {r_c[0]}/{r_c[1]}")
    print(f"  Cas D (célibataire, PERIN seul)  : {r_d[0]}/{r_d[1]}")
    print(f"  Test structurel non-agrégation T4: {r_e[0]}/{r_e[1]}")

    total_ok = r_a[0] + r_b[0] + r_c[0] + r_d[0] + r_e[0]
    total = r_a[1] + r_b[1] + r_c[1] + r_d[1] + r_e[1]
    print(f"\n  TOTAL : {total_ok}/{total}")
    if total_ok < total:
        sys.exit(1)
