"""
Strategy Engine — Stratégies Assimilé salarié.

Quatre stratégies d'allocation d'enveloppe à coût société constant :
- A : 100 % rémunération
- B : 60 % rémunération / 40 % dividendes
- C : + Épargne salariale & PER (50/30/20)
- D : + Périphériques & cashback (45/25/20/10)

Décisions méthodologiques (cf. Cadre v1.0.1 §4.1) :
- Allocation à enveloppe constante (coût total société)
- Application uniforme du taux moyen IR (calculé par regime/assimile.py)
- Stratégie « retenue par défaut » = stratégie qui maximise le net dirigeant
  immédiat (clé technique `recommandee` du dict, conservée pour rétrocompat
  Phase A — l'UI / PDF affichent désormais "stratégie retenue" et non
  "recommandée").

Module : consomme core (profil, constantes) + regime/assimile (helpers).
Aucun import vers d'autres strategy/*.
"""

from core.profil import (
    Profil,
    TX_PATRONAL, TX_SALARIAL, TX_CSG_CRDS_ACT, ASSIETTE_CSG_SAL,
    TX_PFU, TX_IS_REDUIT, TX_IS_NORMAL, IS_PLAF_REDUIT,
)
from regime.assimile import calcul_tx_ir_moyen, fs_moyen_epargne


# ============================================================
# DÉFINITION DES STRATÉGIES A/B/C/D
# ============================================================
STRATEGIES = {
    "A": {"nom": "100 % rémunération",
          "salaire": 1.00, "dividendes": 0.00, "epargne": 0.00, "peripheriques": 0.00},
    "B": {"nom": "60 % rém / 40 % dividendes",
          "salaire": 0.60, "dividendes": 0.40, "epargne": 0.00, "peripheriques": 0.00},
    "C": {"nom": "+ Épargne salariale & PER",
          "salaire": 0.50, "dividendes": 0.30, "epargne": 0.20, "peripheriques": 0.00},
    "D": {"nom": "+ Périphériques & cashback",
          "salaire": 0.45, "dividendes": 0.25, "epargne": 0.20, "peripheriques": 0.10},
}


# ============================================================
# CALCUL D'UNE STRATÉGIE
# ============================================================
def calcul_strategie(profil: Profil, code: str, tx_ir_moy: float) -> dict:
    """
    Calcule une stratégie A/B/C/D pour un profil donné.

    Args:
        profil: Profil client (avec enveloppe à arbitrer)
        code: "A", "B", "C" ou "D"
        tx_ir_moy: Taux moyen IR pré-calculé (via regime.assimile)

    Returns:
        dict avec décomposition coûts, nets et efficacité.
    """
    strat = STRATEGIES[code]
    env = profil.enveloppe

    cout_salaire = env * strat["salaire"]
    cout_div = env * strat["dividendes"]
    cout_epargne = env * strat["epargne"]
    cout_periph = env * strat["peripheriques"]
    cout_total = cout_salaire + cout_div + cout_epargne + cout_periph

    # Net salaire (formule C21 v19)
    if cout_salaire > 0:
        brut = cout_salaire / (1 + TX_PATRONAL)
        net_avant_ir = brut * (1 - TX_SALARIAL - ASSIETTE_CSG_SAL * 0.097)
        net_salaire = net_avant_ir * (1 - tx_ir_moy)
    else:
        net_salaire = 0.0

    # Net dividendes (formule C22 v19 branche non-TNS)
    if cout_div > 0:
        is_reduit = min(cout_div, IS_PLAF_REDUIT) * TX_IS_REDUIT
        is_normal = max(0, cout_div - IS_PLAF_REDUIT) * TX_IS_NORMAL
        distribuable = cout_div - is_reduit - is_normal
        net_div = distribuable * (1 - TX_PFU)
    else:
        net_div = 0.0

    # Net épargne (formule C23 v19)
    if cout_epargne > 0:
        fs = fs_moyen_epargne(profil)
        montant_brut = cout_epargne / (1 + fs)
        net_epargne = montant_brut * (1 - TX_CSG_CRDS_ACT)
    else:
        net_epargne = 0.0

    # Net périphériques (formule C24 v19)
    net_periph = cout_periph * 0.95

    total_net = net_salaire + net_div + net_epargne + net_periph
    efficacite = total_net / cout_total if cout_total > 0 else 0

    return {
        "code": code,
        "nom": strat["nom"],
        "cout_salaire": cout_salaire,
        "cout_dividendes": cout_div,
        "cout_epargne": cout_epargne,
        "cout_peripheriques": cout_periph,
        "cout_total": cout_total,
        "net_salaire": net_salaire,
        "net_dividendes": net_div,
        "net_epargne": net_epargne,
        "net_peripheriques": net_periph,
        "total_net": total_net,
        "efficacite": efficacite,
        "gain_vs_a": 0,
        "tx_ir_moy": tx_ir_moy,
    }


# ============================================================
# ARBITRAGE COMPLET (boucle sur les 4 stratégies)
# ============================================================
def arbitrage_complet(profil: Profil) -> dict:
    """
    Calcule les 4 stratégies A/B/C/D et identifie la stratégie au meilleur net.

    Note terminologique : la clé `recommandee` du dict de retour est
    historique (Phase A). Elle référence le code de la stratégie au plus
    haut `total_net`, c'est-à-dire un indicateur **technique**, pas une
    recommandation au sens conseil. L'UI et le PDF utilisent désormais
    « stratégie retenue » dans leur rendu visuel.

    Returns:
        dict avec :
        - strategies: dict {code: résultat}
        - recommandee: code de la stratégie au plus haut net (indicateur technique)
        - tx_ir_moy: taux moyen IR appliqué uniformément
    """
    tx_ir_moy = calcul_tx_ir_moyen(profil)
    strategies = {code: calcul_strategie(profil, code, tx_ir_moy) for code in STRATEGIES}
    net_a = strategies["A"]["total_net"]
    for code in strategies:
        strategies[code]["gain_vs_a"] = strategies[code]["total_net"] - net_a
    recommandee = max(strategies, key=lambda c: strategies[c]["total_net"])
    return {
        "strategies": strategies,
        "recommandee": recommandee,
        "tx_ir_moy": tx_ir_moy,
    }
