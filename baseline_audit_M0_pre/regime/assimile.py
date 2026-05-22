"""
Regime Engine — Module Assimilé salarié.

Helpers de calcul propres au régime Assimilé salarié, consommés par le
Strategy Engine Assimilé (stratégies A/B/C/D).

Décisions méthodologiques (cf. Cadre v1.0.1 §3.1) :
- Taux moyen IR calculé via module Assimilé sur salaire brut de référence
  (par défaut 80 000 € comme dans la v19)
- Application uniforme du tx_ir_moy aux 4 stratégies dans le Strategy Engine
- Forfait social moyen pondéré selon effectif

Module : consomme uniquement core. Aucun import croisé vers regime/* ou strategy/*.
"""

from core.profil import (
    Profil,
    TX_SALARIAL, TX_CSG_CRDS_ACT, ASSIETTE_CSG_SAL,
)
from core.ir_foyer import calcul_ir_foyer


# ============================================================
# CONSTANTE V19 (plafond abattement 10 % salarial 2026)
# ============================================================
# Note : déjà défini dans regime.salarie comme PLAFOND_ABAT_10PCT_SAL.
# Conservé localement pour éviter une dépendance régime <-> régime
# (Assimilé doit pouvoir vivre sans regime.salarie).
PLAFOND_ABAT_10PCT_REF = 14_426


# ============================================================
# HELPER 1 — Taux moyen IR sur salaire de référence
# ============================================================
def calcul_tx_ir_moyen(profil: Profil) -> float:
    """
    TX_IR_MOY_ASS : taux moyen calculé via module Assimilé sur salaire de référence.

    Reproduit fidèlement la formule v19 cellule C33 du module 7.
    Le salaire brut utilisé est celui saisi dans le module Assimilé
    (par défaut 80 000 € comme dans la v19).

    Plancher : 5 % minimum (sécurité v19).
    """
    brut = profil.salaire_brut_assimile
    cotis_salariales = brut * TX_SALARIAL
    csg_crds = brut * ASSIETTE_CSG_SAL * TX_CSG_CRDS_ACT
    csg_deductible = brut * ASSIETTE_CSG_SAL * 0.068
    net_avant_ir = brut - cotis_salariales - csg_crds
    rev_sal_imp = net_avant_ir + csg_crds - csg_deductible
    abat = min(rev_sal_imp * 0.10, PLAFOND_ABAT_10PCT_REF)
    rev_imp_net = max(0, rev_sal_imp - abat)
    rev_imp_foyer = rev_imp_net + profil.autres_revenus

    impots = calcul_ir_foyer(rev_imp_foyer, profil)
    tx_moy = impots["total_impots"] / rev_imp_foyer if rev_imp_foyer > 0 else 0
    return max(tx_moy, 0.05)


# ============================================================
# HELPER 2 — Forfait social moyen selon effectif
# ============================================================
def fs_moyen_epargne(profil: Profil) -> float:
    """
    Forfait social moyen pondéré v19 selon effectif.

    - Sans salarié à 11-49 : 0 %
    - 50-249 salariés : 13,3 % (moyenne pondérée des dispositifs)
    - ≥ 250 salariés : 20 %
    """
    if profil.effectif in ["Sans salarié", "1-10 salariés", "11-49 salariés"]:
        return 0.0
    elif profil.effectif == "50-249 salariés":
        return 0.133
    else:
        return 0.20
