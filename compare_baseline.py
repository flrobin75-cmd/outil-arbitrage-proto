"""
Compare l'état actuel à la baseline outputs.

Permet de vérifier rapidement qu'aucune valeur n'a dérivé pendant le refactoring.
À exécuter après chaque modification structurelle.
"""

import json, sys
sys.path.insert(0, ".")

# Recharger les imports — couches canoniques (post-B.3)
from core.profil import Profil
from strategy.assimile import arbitrage_complet
from strategy.comparateur import calcul_comparateur, ConfigComparateur, FluxEpargne
from strategy.synthese import calcul_synthese, FORFAITS_DEFAUT
from strategy.perin import calcul_perin_mutualise
from strategy.scenarios import ScenarioInputs, calcul_comparaison

BASELINE_FILE = "baseline_outputs/baseline_outputs.json"
TOL = 0.01  # tolérance € pour valeurs monétaires
TOL_PCT = 0.0001  # tolérance pour pourcentages


def check(label, actuel, attendu, tol=TOL):
    if isinstance(attendu, bool):
        ok = actuel == attendu
    elif isinstance(attendu, (int, float)):
        ok = abs(actuel - attendu) <= tol
    else:
        ok = str(actuel) == str(attendu)
    marker = "✓" if ok else "✗"
    return ok, marker


print("=" * 80)
print("  COMPARAISON ÉTAT ACTUEL vs BASELINE")
print("=" * 80)
print()

with open(BASELINE_FILE) as f:
    baseline = json.load(f)

print(f"Baseline doctrine v{baseline['version_doctrine']}\n")

nb_ok = 0
nb_diff = 0

# Cas 1 : Arbitrage Assimilé
print("→ Arbitrage Assimilé par défaut")
profil = Profil()
arb = arbitrage_complet(profil)
base = baseline["cases"]["arbitrage_assimile_defaut"]
for code, key in [("A", "strategie_A_net"), ("B", "strategie_B_net"),
                  ("C", "strategie_C_net"), ("D", "strategie_D_net")]:
    actuel = arb["strategies"][code]["total_net"]
    attendu = base[key]
    ok, m = check(key, actuel, attendu)
    print(f"  {m} {code}: {actuel:>12,.4f} vs baseline {attendu:>12,.4f}")
    if ok: nb_ok += 1
    else: nb_diff += 1

# Cas 2 : Comparateur
print("\n→ Comparateur Option 2")
config = ConfigComparateur(
    pee_actif=True, pereco_actif=True, pero_actif=False, perin_actif=True,
    participation=FluxEpargne(True, 1500, "PEE"),
    interessement=FluxEpargne(True, 2500, "PEE"),
    abondement_pee=FluxEpargne(True, 1500, "PEE"),
    abondement_pereco=FluxEpargne(True, 3000, "PERECO"),
    versement_perin=FluxEpargne(True, 5000, "PERIN"),
)
res_comp = calcul_comparateur(profil, config)
base = baseline["cases"]["comparateur_defaut"]
ok, m = check("nb_lignes", len(res_comp.lignes), base["nb_lignes"])
print(f"  {m} nb_lignes: {len(res_comp.lignes)} vs {base['nb_lignes']}")
if ok: nb_ok += 1
else: nb_diff += 1

# Cas 3 : Synthèse
print("\n→ Synthèse stratégie D")
synth = calcul_synthese(profil, arb["strategies"], config,
                         code_retenue="D", forfaits=FORFAITS_DEFAUT,
                         alertes_comparateur=res_comp.alertes)
base = baseline["cases"]["synthese_strategie_D"]
for key, actuel in [("net_dirigeant_retenu", synth.net_dirigeant_retenu),
                    ("gain_vs_a", synth.gain_vs_a),
                    ("gain_5_ans", synth.gain_5_ans),
                    ("total_couts", synth.total_couts),
                    ("roi_mois", synth.roi_mois)]:
    attendu = base[key]
    ok, m = check(key, actuel, attendu)
    print(f"  {m} {key}: {actuel:>12,.4f} vs {attendu:>12,.4f}")
    if ok: nb_ok += 1
    else: nb_diff += 1

# Cas 4 : PERIN
print("\n→ PERIN mutualisé")
res_perin = calcul_perin_mutualise(
    versement_dirigeant=10_000,
    revenu_pro_dirigeant=70_000,
    tmi_dirigeant=0.41,
    situation="Marié / pacsé",
    conjoint_declare=True,
    revenu_pro_conjoint=50_000,
    versement_conjoint=1_000,
)
base = baseline["cases"]["perin_mutualise"]
for key, actuel in [
    ("plafond_mutualise_total", res_perin.plafond_mutualise_total),
    ("versement_couvert", res_perin.versement_dirigeant_couvert),
    ("economie_ir", res_perin.economie_ir),
]:
    attendu = base[key]
    ok, m = check(key, actuel, attendu)
    print(f"  {m} {key}: {actuel:>12,.4f} vs {attendu:>12,.4f}")
    if ok: nb_ok += 1
    else: nb_diff += 1

# Cas 5 : Scénarios
print("\n→ Scénarios A vs B (avant/après dividendes)")
sc_a = ScenarioInputs(libelle="Sans dividendes", regime_social="Assimilé salarié",
                      salaire_brut=100_000)
sc_b = ScenarioInputs(libelle="Avec dividendes 50k", regime_social="Assimilé salarié",
                      salaire_brut=100_000, dividendes_bruts=50_000,
                      epargne_salariale_per=15_000, peripheriques=4_000)
res_sc = calcul_comparaison(sc_a, sc_b)
base = baseline["cases"]["scenarios_avant_apres_dividendes"]
for key, actuel in [("A_total_net", res_sc.scenario_a.total_net),
                    ("B_total_net", res_sc.scenario_b.total_net),
                    ("ecart_total", res_sc.ecart_total)]:
    attendu = base[key]
    ok, m = check(key, actuel, attendu)
    print(f"  {m} {key}: {actuel:>12,.4f} vs {attendu:>12,.4f}")
    if ok: nb_ok += 1
    else: nb_diff += 1

# Synthèse
print()
print(f"━━━ RÉSULTAT ━━━")
print(f"  Validations OK     : {nb_ok}")
print(f"  Divergences        : {nb_diff}")

if nb_diff == 0:
    print(f"\n  ✓ AUCUNE RÉGRESSION DÉTECTÉE — refactoring sécurisé")
    sys.exit(0)
else:
    print(f"\n  ✗ RÉGRESSIONS DÉTECTÉES — corriger avant de continuer")
    sys.exit(1)
