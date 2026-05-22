"""
Tests Synthèse - validation par cohérence interne.

Pas de parité v19 stricte ici car la Synthèse dépend de l'Arbitrage qui est
limité Assimilé en v1, et nous avons enrichi les axes du radar par rapport à v19.

3 cas testés :
- Cas 1 : Stratégie retenue C, profil standard
- Cas 2 : Stratégie A retenue (cas dégradé - aucun dispositif)
- Cas 3 : Stratégie D avec PERO activé
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.profil import Profil
from strategy.comparateur import calcul_comparateur, ConfigComparateur, FluxEpargne
from strategy.synthese import (
    calcul_synthese, FORFAITS_DEFAUT, reset_forfaits,
    calcul_radar_6d, calcul_enveloppes_patrimoniales,
    PONDS_PROTECTION, AVERTISSEMENT_RADAR,
)


# Stratégies factices reproduisant les valeurs Arbitrage v19 cas par défaut
# (validées 78 424 € en stratégie D dans le prototype actuel)
STRATEGIES_DEFAUT = {
    "A": {
        "total_net": 61_908.45,
        "cout_total": 120_000.00,
        "net_salaire": 61_908.45,
        "net_dividendes": 0,
        "net_epargne": 0,
        "net_peripheriques": 0,
        "cout_salaire": 120_000.00,
        "cout_dividendes": 0,
        "cout_epargne": 0,
        "cout_peripheriques": 0,
    },
    "B": {
        "total_net": 64_756.57,
        "cout_total": 120_000.00,
        "net_salaire": 37_145.07,
        "net_dividendes": 27_611.50,
        "net_epargne": 0,
        "net_peripheriques": 0,
        "cout_salaire": 72_000,
        "cout_dividendes": 48_000,
        "cout_epargne": 0,
        "cout_peripheriques": 0,
    },
    "C": {
        "total_net": 73_617.82,
        "cout_total": 120_000.00,
        "net_salaire": 30_954.22,
        "net_dividendes": 20_991.60,
        "net_epargne": 21_672.00,
        "net_peripheriques": 0,
        "cout_salaire": 60_000,
        "cout_dividendes": 36_000,
        "cout_epargne": 24_000,
        "cout_peripheriques": 0,
    },
    "D": {
        "total_net": 78_423.80,
        "cout_total": 120_000.00,
        "net_salaire": 27_858.80,
        "net_dividendes": 17_493.00,
        "net_epargne": 21_672.00,
        "net_peripheriques": 11_400.00,
        "cout_salaire": 54_000,
        "cout_dividendes": 30_000,
        "cout_epargne": 24_000,
        "cout_peripheriques": 12_000,
    },
}


def fmt(v):
    if v is None: return "None"
    if isinstance(v, float): return f"{v:,.2f}".replace(",", " ")
    return str(v)


# ============================================================
# TEST 1 — Stratégie retenue C (cas standard)
# ============================================================
def test_1_synthese_strategie_c():
    print("=" * 110)
    print("  TEST 1 — SYNTHÈSE STRATÉGIE C (cas par défaut)")
    print("=" * 110)

    profil = Profil(
        forme_juridique="SAS / SASU",
        effectif="11-49 salariés",
        situation="Marié / pacsé",
        parts=2.0,
        enveloppe=120_000,
    )

    config = ConfigComparateur(
        pee_actif=True, pereco_actif=True, pero_actif=False,
        participation=FluxEpargne(True, 1500, "PEE"),
        interessement=FluxEpargne(True, 2500, "PEE"),
        abondement_pee=FluxEpargne(True, 1500, "PEE"),
        abondement_pereco=FluxEpargne(True, 3000, "PERECO"),
        versement_perin=FluxEpargne(True, 5000, "PERIN"),
        tr_actif=True, tr_montant=1742,
        cesu_actif=True, cesu_montant=2000,
    )

    synth = calcul_synthese(profil, STRATEGIES_DEFAUT, config, code_retenue="C")

    checks = []

    # Validation 1 : Stratégie retenue
    if synth.strategie_retenue == "C":
        checks.append(("✓", "Stratégie retenue = C", "C"))
    else:
        checks.append(("✗", "Stratégie retenue = C", synth.strategie_retenue))

    # Validation 2 : Net dirigeant retenu = 73 617,82
    if abs(synth.net_dirigeant_retenu - 73_617.82) <= 0.01:
        checks.append(("✓", "Net dirigeant retenu", fmt(synth.net_dirigeant_retenu)))
    else:
        checks.append(("✗", "Net dirigeant retenu", fmt(synth.net_dirigeant_retenu)))

    # Validation 3 : Gain vs A = 73 617,82 - 61 908,45 = 11 709,37
    gain_attendu = 11_709.37
    if abs(synth.gain_vs_a - gain_attendu) <= 0.01:
        checks.append(("✓", "Gain vs A", fmt(synth.gain_vs_a)))
    else:
        checks.append(("✗", "Gain vs A", fmt(synth.gain_vs_a)))

    # Validation 4 : Coûts cabinet - en stratégie C avec PEE+PER+TR+CESU+participation
    # = cadrage (1200) + intéressement (800) + PEE/PER (1500) + teneur petit (600)
    # + audit_peripheriques (600) = 4 700
    cout_attendu = 1200 + 800 + 1500 + 600 + 600  # 4 700
    if abs(synth.total_couts - cout_attendu) <= 0.01:
        checks.append(("✓", f"Total coûts ({cout_attendu} € attendus)", fmt(synth.total_couts)))
    else:
        checks.append(("✗", f"Total coûts ({cout_attendu} € attendus)", fmt(synth.total_couts)))

    # Validation 5 : ROI en mois = 4700 / 11709 * 12 ≈ 4,82
    if synth.roi_mois and abs(synth.roi_mois - 4.82) <= 0.1:
        checks.append(("✓", "ROI en mois (~4,82)", f"{synth.roi_mois:.2f}"))
    else:
        checks.append(("✗", "ROI en mois (~4,82)", str(synth.roi_mois)))

    # Validation 6 : Radar 6D - 4 scores
    if len(synth.scores_radar) == 4:
        checks.append(("✓", "Radar : 4 scores produits", "4"))
    else:
        checks.append(("✗", "Radar : 4 scores produits", len(synth.scores_radar)))

    # Validation 7 : Score Net dirigeant - D doit être à 100 (le max), A < 100
    score_a = next(s for s in synth.scores_radar if s.nom_strategie == "A")
    score_d = next(s for s in synth.scores_radar if s.nom_strategie == "D")
    if abs(score_d.net_dirigeant - 100) <= 0.01:
        checks.append(("✓", "Radar Net D = 100", fmt(score_d.net_dirigeant)))
    else:
        checks.append(("✗", "Radar Net D = 100", fmt(score_d.net_dirigeant)))
    if score_a.net_dirigeant < 100:
        checks.append(("✓", "Radar Net A < 100", fmt(score_a.net_dirigeant)))
    else:
        checks.append(("✗", "Radar Net A < 100", fmt(score_a.net_dirigeant)))

    # Validation 8 : Score Protection sociale - A doit être à 100 (que du salaire)
    if abs(score_a.protection_sociale - 100) <= 0.01:
        checks.append(("✓", "Radar Protection A = 100", fmt(score_a.protection_sociale)))
    else:
        checks.append(("✗", "Radar Protection A = 100", fmt(score_a.protection_sociale)))
    # D doit être < A (mixte avec dividendes faiblement protecteurs)
    if score_d.protection_sociale < score_a.protection_sociale:
        checks.append(("✓", "Radar Protection D < A", fmt(score_d.protection_sociale)))
    else:
        checks.append(("✗", "Radar Protection D < A",
                       f"D={fmt(score_d.protection_sociale)} A={fmt(score_a.protection_sociale)}"))

    # Validation 9 : Score Maîtrise des charges - D doit être > A
    if score_d.maitrise_charges > score_a.maitrise_charges:
        checks.append(("✓", "Radar Maîtrise charges D > A",
                       f"D={fmt(score_d.maitrise_charges)} A={fmt(score_a.maitrise_charges)}"))
    else:
        checks.append(("✗", "Radar Maîtrise charges D > A",
                       f"D={fmt(score_d.maitrise_charges)} A={fmt(score_a.maitrise_charges)}"))

    # Validation 10 : Score Préparation retraite - A = 0, D > 0
    if score_a.preparation_retraite == 0:
        checks.append(("✓", "Radar Retraite A = 0", fmt(score_a.preparation_retraite)))
    else:
        checks.append(("✗", "Radar Retraite A = 0", fmt(score_a.preparation_retraite)))
    if score_d.preparation_retraite > 0:
        checks.append(("✓", "Radar Retraite D > 0", fmt(score_d.preparation_retraite)))
    else:
        checks.append(("✗", "Radar Retraite D > 0", fmt(score_d.preparation_retraite)))

    # Validation 11 : Projection 5 ans
    if len(synth.projection["annees"]) == 5:
        checks.append(("✓", "Projection 5 années", "5"))
    else:
        checks.append(("✗", "Projection 5 années", len(synth.projection["annees"])))

    # Validation 12 : Gain 5 ans > gain annuel × 5 (effet capitalisation)
    if synth.gain_5_ans > synth.gain_vs_a * 5:
        checks.append(("✓", "Gain 5 ans > gain annuel × 5 (capitalisation)",
                       f"5 ans={fmt(synth.gain_5_ans)} 5× ann={fmt(synth.gain_vs_a*5)}"))
    else:
        checks.append(("✗", "Gain 5 ans > gain annuel × 5",
                       f"5 ans={fmt(synth.gain_5_ans)} 5× ann={fmt(synth.gain_vs_a*5)}"))

    # Validation 13 : Décomposition waterfall - 4 étapes
    if len(synth.decomposition) == 4:
        checks.append(("✓", "Waterfall : 4 étapes", "4"))
    else:
        checks.append(("✗", "Waterfall : 4 étapes", len(synth.decomposition)))

    # Validation 14 : Cumul vs A pour D = gain_vs_a
    waterfall_d = synth.decomposition[3]
    expected_cumul = STRATEGIES_DEFAUT["D"]["total_net"] - STRATEGIES_DEFAUT["A"]["total_net"]
    if abs(waterfall_d.cumul_vs_a - expected_cumul) <= 0.01:
        checks.append(("✓", "Waterfall D cumul = gain D-A", fmt(waterfall_d.cumul_vs_a)))
    else:
        checks.append(("✗", "Waterfall D cumul = gain D-A", fmt(waterfall_d.cumul_vs_a)))

    # Validation 15 : Enveloppes patrimoniales - 4 enveloppes
    if len(synth.enveloppes_compact["enveloppes"]) == 4:
        checks.append(("✓", "Enveloppes : 4 lignes", "4"))
    else:
        checks.append(("✗", "Enveloppes : 4 lignes",
                       len(synth.enveloppes_compact["enveloppes"])))

    # Validation 16 : Check-list présente
    if len(synth.checklist) > 0:
        checks.append(("✓", "Check-list non vide",
                       f"{len(synth.checklist)} points"))
    else:
        checks.append(("✗", "Check-list non vide", "0"))

    print("\n  Validations :")
    ok_count = 0
    for marker, label, val in checks:
        print(f"  {marker} {label:55s} → {val}")
        if marker == "✓": ok_count += 1
    print(f"\n  RÉSULTAT TEST 1 : {ok_count}/{len(checks)}")
    return ok_count, len(checks), synth


# ============================================================
# TEST 2 — Stratégie A retenue (cas dégradé)
# ============================================================
def test_2_synthese_strategie_a():
    print("\n" + "=" * 110)
    print("  TEST 2 — SYNTHÈSE STRATÉGIE A (référence pure, aucun dispositif)")
    print("=" * 110)

    profil = Profil(forme_juridique="SAS / SASU", effectif="11-49 salariés",
                    situation="Marié / pacsé", parts=2.0, enveloppe=120_000)
    config = ConfigComparateur(pee_actif=False, pereco_actif=False, pero_actif=False,
                                participation=FluxEpargne(False, 0, "PEE"),
                                interessement=FluxEpargne(False, 0, "PEE"),
                                abondement_pee=FluxEpargne(False, 0, "PEE"),
                                abondement_pereco=FluxEpargne(False, 0, "PERECO"),
                                versement_perin=FluxEpargne(False, 0, "PERIN"),
                                tr_actif=False, cesu_actif=False, cado_actif=False,
                                mutuelle_actif=False, ik_actif=False,
                                cashback_actif=False, avantages_actif=False)

    synth = calcul_synthese(profil, STRATEGIES_DEFAUT, config, code_retenue="A")

    checks = []

    if synth.strategie_retenue == "A":
        checks.append(("✓", "Stratégie retenue = A", "A"))
    else:
        checks.append(("✗", "Stratégie retenue = A", synth.strategie_retenue))

    if synth.gain_vs_a == 0:
        checks.append(("✓", "Gain vs A = 0 (référence elle-même)", "0"))
    else:
        checks.append(("✗", "Gain vs A = 0", fmt(synth.gain_vs_a)))

    # En stratégie A, seul le cadrage cabinet est facturé
    if synth.total_couts == 1200:
        checks.append(("✓", "Coûts = cadrage seul (1 200 €)", fmt(synth.total_couts)))
    else:
        checks.append(("✗", "Coûts = cadrage seul (1 200 €)", fmt(synth.total_couts)))

    # ROI infini ou None (gain nul)
    if synth.roi_mois is None:
        checks.append(("✓", "ROI = None (pas de gain)", "None"))
    else:
        checks.append(("✗", "ROI = None (pas de gain)", str(synth.roi_mois)))

    # Check-list courte : juste "Stratégie A - référence"
    if len(synth.checklist) == 1 and synth.checklist[0].statut == "-":
        checks.append(("✓", "Check-list : 1 entrée référence", "1"))
    else:
        checks.append(("✗", "Check-list : 1 entrée référence", len(synth.checklist)))

    print("\n  Validations :")
    ok_count = 0
    for marker, label, val in checks:
        print(f"  {marker} {label:55s} → {val}")
        if marker == "✓": ok_count += 1
    print(f"\n  RÉSULTAT TEST 2 : {ok_count}/{len(checks)}")
    return ok_count, len(checks), synth


# ============================================================
# TEST 3 — Stratégie D avec PERO activé (cohérence radar étendue)
# ============================================================
def test_3_synthese_strategie_d_pero():
    print("\n" + "=" * 110)
    print("  TEST 3 — SYNTHÈSE STRATÉGIE D AVEC PERO ACTIVÉ")
    print("=" * 110)

    profil = Profil(forme_juridique="SAS / SASU", effectif="11-49 salariés",
                    situation="Marié / pacsé", parts=2.0, enveloppe=120_000)
    config = ConfigComparateur(
        pee_actif=True, pereco_actif=True, pero_actif=True, perin_actif=True,
        dirigeant_eligible_pero=True,
        participation=FluxEpargne(True, 1500, "PEE"),
        interessement=FluxEpargne(True, 2500, "PEE"),
        abondement_pee=FluxEpargne(True, 1000, "PEE"),
        abondement_pereco=FluxEpargne(True, 2000, "PERECO"),
        versement_perin=FluxEpargne(True, 5000, "PERIN"),
        pero_mode_saisie="pourcentage", pero_taux=0.03,
        tr_actif=True, cesu_actif=True, cashback_actif=True, cashback_montant=360,
    )

    synth = calcul_synthese(profil, STRATEGIES_DEFAUT, config, code_retenue="D")

    checks = []

    if synth.strategie_retenue == "D":
        checks.append(("✓", "Stratégie retenue = D", "D"))
    else:
        checks.append(("✗", "Stratégie retenue = D", synth.strategie_retenue))

    # Coûts D avec tous dispositifs activés + PERO :
    # cadrage 1200 + intéressement 800 + PEE/PER 1500 + PERO 1200 + teneur 600
    # + audit_peripheriques 600 + audit_cashback 900 = 6 800
    cout_attendu_d = 1200 + 800 + 1500 + 1200 + 600 + 600 + 900  # 6800
    if abs(synth.total_couts - cout_attendu_d) <= 0.01:
        checks.append(("✓", f"Total coûts D ({cout_attendu_d} €)", fmt(synth.total_couts)))
    else:
        checks.append(("✗", f"Total coûts D ({cout_attendu_d} €)", fmt(synth.total_couts)))

    # PERO doit créer un poste de coût
    pero_dans_couts = any("PERO" in c.libelle for c in synth.couts_mise_en_oeuvre)
    if pero_dans_couts:
        checks.append(("✓", "Poste PERO présent dans coûts", "Oui"))
    else:
        checks.append(("✗", "Poste PERO présent dans coûts", "Non"))

    # Cashback Conforme à 900 €
    cashback_dans_couts = any("cashback" in c.libelle.lower()
                              for c in synth.couts_mise_en_oeuvre)
    if cashback_dans_couts:
        checks.append(("✓", "Poste cashback présent dans coûts", "Oui"))
    else:
        checks.append(("✗", "Poste cashback présent dans coûts", "Non"))

    # Test forfait personnalisé - on modifie le cadrage
    forfaits_custom = {k: v for k, v in FORFAITS_DEFAUT.items()}
    forfaits_custom["cadrage"].montant = 2500  # custom
    synth_custom = calcul_synthese(profil, STRATEGIES_DEFAUT, config,
                                    code_retenue="D", forfaits=forfaits_custom)
    if synth_custom.total_couts == synth.total_couts + 1300:  # 2500 - 1200 = 1300
        checks.append(("✓", "Forfait personnalisé impacte le total",
                       f"+1 300 € confirmé"))
    else:
        checks.append(("✗", "Forfait personnalisé impacte le total",
                       f"écart={synth_custom.total_couts - synth.total_couts}"))

    # Reset au défaut
    forfaits_custom["cadrage"].reset()
    if forfaits_custom["cadrage"].montant == 1200:
        checks.append(("✓", "Reset forfait OK", "1 200"))
    else:
        checks.append(("✗", "Reset forfait OK", forfaits_custom["cadrage"].montant))

    print("\n  Validations :")
    ok_count = 0
    for marker, label, val in checks:
        print(f"  {marker} {label:55s} → {val}")
        if marker == "✓": ok_count += 1
    print(f"\n  RÉSULTAT TEST 3 : {ok_count}/{len(checks)}")
    return ok_count, len(checks), synth


if __name__ == "__main__":
    # Restaurer forfaits au cas où
    FORFAITS_DEFAUT["cadrage"].reset()
    r1 = test_1_synthese_strategie_c()
    FORFAITS_DEFAUT["cadrage"].reset()
    r2 = test_2_synthese_strategie_a()
    FORFAITS_DEFAUT["cadrage"].reset()
    r3 = test_3_synthese_strategie_d_pero()

    print("\n" + "=" * 110)
    print("  SYNTHÈSE TESTS MODULE SYNTHÈSE")
    print("=" * 110)
    print(f"  Test 1 (Stratégie C cas par défaut)     : {r1[0]}/{r1[1]}")
    print(f"  Test 2 (Stratégie A référence pure)     : {r2[0]}/{r2[1]}")
    print(f"  Test 3 (Stratégie D avec PERO + Custom) : {r3[0]}/{r3[1]}")
    print(f"  TOTAL : {r1[0]+r2[0]+r3[0]}/{r1[1]+r2[1]+r3[1]}")
