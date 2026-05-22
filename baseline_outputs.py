"""
Génération des outputs de référence (PDF, JSON) pour la baseline B.2.

Ces outputs servent à vérifier qu'aucune régression visuelle ou de calcul
ne se produit pendant la refactorisation et les ajouts B.2.
"""

import os, json, hashlib, sys
sys.path.insert(0, ".")

from core.profil import Profil
from strategy.assimile import arbitrage_complet
from strategy.comparateur import calcul_comparateur, ConfigComparateur, FluxEpargne
from strategy.synthese import calcul_synthese, FORFAITS_DEFAUT
from strategy.perin import calcul_perin_mutualise
from strategy.scenarios import ScenarioInputs, calcul_comparaison
from ui.pdf_export import generer_pdf_synthese
from doctrine import DOCTRINE_VERSION


def hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


BASELINE_DIR = "baseline_outputs"
os.makedirs(BASELINE_DIR, exist_ok=True)


def case_assimile_defaut():
    """Cas de référence : profil par défaut Assimilé."""
    profil = Profil()  # 120k€ enveloppe, Assimilé, Marié 2 parts
    arb = arbitrage_complet(profil)
    config = ConfigComparateur(
        pee_actif=True, pereco_actif=True, pero_actif=False, perin_actif=True,
        participation=FluxEpargne(True, 1500, "PEE"),
        interessement=FluxEpargne(True, 2500, "PEE"),
        abondement_pee=FluxEpargne(True, 1500, "PEE"),
        abondement_pereco=FluxEpargne(True, 3000, "PERECO"),
        versement_perin=FluxEpargne(True, 5000, "PERIN"),
    )
    res_comp = calcul_comparateur(profil, config)
    synth = calcul_synthese(profil, arb["strategies"], config,
                            code_retenue="D", forfaits=FORFAITS_DEFAUT,
                            alertes_comparateur=res_comp.alertes)
    return arb, res_comp, synth, profil


def case_perin_mutualise():
    """Cas PERIN mutualisé conjoint."""
    return calcul_perin_mutualise(
        versement_dirigeant=10_000,
        revenu_pro_dirigeant=70_000,
        tmi_dirigeant=0.41,
        situation="Marié / pacsé",
        conjoint_declare=True,
        revenu_pro_conjoint=50_000,
        versement_conjoint=1_000,
    )


def case_scenarios():
    """Cas Scénarios A vs B : avant/après dividendes."""
    sc_a = ScenarioInputs(libelle="Sans dividendes", regime_social="Assimilé salarié",
                          salaire_brut=100_000)
    sc_b = ScenarioInputs(libelle="Avec dividendes 50k", regime_social="Assimilé salarié",
                          salaire_brut=100_000, dividendes_bruts=50_000,
                          epargne_salariale_per=15_000, peripheriques=4_000)
    return calcul_comparaison(sc_a, sc_b)


# ============================================================
# EXTRACTION DES VALEURS NUMÉRIQUES CLÉS
# ============================================================
print("=" * 80)
print("  GÉNÉRATION OUTPUTS BASELINE")
print("=" * 80)
print()
print(f"Version doctrine : v{DOCTRINE_VERSION}")
print()

baseline = {"version_doctrine": DOCTRINE_VERSION, "cases": {}}

# Cas 1 : Arbitrage Assimilé par défaut
arb, res_comp, synth, profil = case_assimile_defaut()
baseline["cases"]["arbitrage_assimile_defaut"] = {
    "strategie_A_net": round(arb["strategies"]["A"]["total_net"], 4),
    "strategie_B_net": round(arb["strategies"]["B"]["total_net"], 4),
    "strategie_C_net": round(arb["strategies"]["C"]["total_net"], 4),
    "strategie_D_net": round(arb["strategies"]["D"]["total_net"], 4),
    "recommandee": arb["recommandee"],
    "tx_ir_moy": round(arb["tx_ir_moy"], 6),
}
print(f"  Arbitrage Assimilé : "
      f"A={arb['strategies']['A']['total_net']:,.2f}  "
      f"B={arb['strategies']['B']['total_net']:,.2f}  "
      f"C={arb['strategies']['C']['total_net']:,.2f}  "
      f"D={arb['strategies']['D']['total_net']:,.2f}")

# Cas 2 : Comparateur Option 2
baseline["cases"]["comparateur_defaut"] = {
    "nb_lignes": len(res_comp.lignes),
    "nb_alertes": len(res_comp.alertes),
    "salaire_net_apres_ir": round(res_comp.lignes[0].net_apres_ir, 4),
    "dividendes_net_apres_ir": round(res_comp.lignes[1].net_apres_ir, 4),
    "perin_montant": round(res_comp.lignes[6].montant_input, 4),
}
print(f"  Comparateur        : {len(res_comp.lignes)} lignes, {len(res_comp.alertes)} alertes")

# Cas 3 : Synthèse
baseline["cases"]["synthese_strategie_D"] = {
    "net_dirigeant_retenu": round(synth.net_dirigeant_retenu, 4),
    "gain_vs_a": round(synth.gain_vs_a, 4),
    "gain_5_ans": round(synth.gain_5_ans, 4),
    "total_couts": round(synth.total_couts, 4),
    "roi_mois": round(synth.roi_mois, 4),
    "nb_scores_radar": len(synth.scores_radar),
    "radar_D_net": round(synth.scores_radar[3].net_dirigeant, 4),
    "radar_D_protection_sociale": round(synth.scores_radar[3].protection_sociale, 4),
    "radar_D_fiscalite": round(synth.scores_radar[3].fiscalite, 4),
    "radar_D_retraite": round(synth.scores_radar[3].preparation_retraite, 4),
}
print(f"  Synthèse           : net={synth.net_dirigeant_retenu:,.2f} ROI={synth.roi_mois:.2f}mois")

# Cas 4 : PERIN mutualisé
res_perin = case_perin_mutualise()
baseline["cases"]["perin_mutualise"] = {
    "plafond_dirigeant": round(res_perin.plafond_dirigeant.plafond_individuel, 4),
    "plafond_conjoint": round(res_perin.plafond_conjoint.plafond_individuel, 4),
    "plafond_mutualise_total": round(res_perin.plafond_mutualise_total, 4),
    "versement_couvert": round(res_perin.versement_dirigeant_couvert, 4),
    "excedent": round(res_perin.versement_excedent, 4),
    "economie_ir": round(res_perin.economie_ir, 4),
}
print(f"  PERIN mutualisé    : plafond={res_perin.plafond_mutualise_total:,.2f} "
      f"économie={res_perin.economie_ir:,.2f}")

# Cas 5 : Scénarios A vs B
res_sc = case_scenarios()
baseline["cases"]["scenarios_avant_apres_dividendes"] = {
    "A_total_net": round(res_sc.scenario_a.total_net, 4),
    "B_total_net": round(res_sc.scenario_b.total_net, 4),
    "ecart_total": round(res_sc.ecart_total, 4),
    "ecart_pourcent": round(res_sc.ecart_pourcent, 6),
    "gagnant": res_sc.gagnant,
}
print(f"  Scénarios A vs B   : écart={res_sc.ecart_total:,.2f} gagnant={res_sc.gagnant}")

# Cas 6 : PDF Synthèse (hash binaire — sensible aux timestamps, donc on
# capture juste la taille à titre indicatif)
pdf_bytes = generer_pdf_synthese(
    synthese=synth, arbitrage=arb, profil=profil,
    cabinet_nom="Cabinet Baseline", client_nom="Client Baseline",
    expert_comptable="EC Baseline",
)
with open(f"{BASELINE_DIR}/synthese_baseline.pdf", "wb") as f:
    f.write(pdf_bytes)
baseline["cases"]["pdf_synthese"] = {
    "taille_bytes": len(pdf_bytes),
    "header_pdf": pdf_bytes[:8].decode("latin-1", errors="ignore"),
    "format_valide": pdf_bytes[:4] == b"%PDF",
}
print(f"  PDF Synthèse       : {len(pdf_bytes):,} octets")

# Sauvegarde JSON baseline
with open(f"{BASELINE_DIR}/baseline_outputs.json", "w") as f:
    json.dump(baseline, f, indent=2, ensure_ascii=False)

print()
print(f"━━━ BASELINE OUTPUTS GÉNÉRÉS ━━━")
print(f"  Dossier : {BASELINE_DIR}/")
print(f"  - baseline_outputs.json (valeurs numériques de référence)")
print(f"  - synthese_baseline.pdf (PDF de référence)")
print(f"\n✓ Étape 0 terminée — refactoring peut commencer en sécurité")
