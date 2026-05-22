"""
Regime Engine — Module Salarié (cadre/non-cadre).

Transposition fidèle de l'onglet "10. Salarié" du classeur v19.

Décision validée : périmètre v19 strict (brut sec, sans accessoires modélisés).
Les dispositifs d'épargne salariale (PEE, PER, etc.) sont modélisés dans le
Strategy Engine Assimilé (stratégies C/D), pas dans ce module de référence.

Structure :
    1. Imports et constantes
    2. Dataclass ResultatSalarie
    3. calcul_module_salarie()
"""

# ============================================================
# 1. IMPORTS ET CONSTANTES
# ============================================================
from dataclasses import dataclass

from core.profil import (
    Profil,
    TX_SALARIAL, ASSIETTE_CSG_SAL, TX_CSG_CRDS_ACT,
)
from core.ir_foyer import calcul_ir_foyer

# Constante v19 (codée en dur dans la formule C15, pas en nom défini)
PLAFOND_ABAT_10PCT_SAL = 14_426  # Plafond officiel 2026


# ============================================================
# 2. DATACLASS RÉSULTAT
# ============================================================
@dataclass
class ResultatSalarie:
    """Résultat scénario Salarié."""
    # Inputs
    salaire_brut: float

    # Section 2 - Cotisations & net (formules C8-C11)
    cotis_salariales: float
    csg_crds_totale: float
    csg_deductible: float
    net_avant_impot: float                  # C11

    # Section 3 - IR (formules C14-C30)
    revenu_salarial_imposable: float         # C14
    abattement_10pct: float                  # C15
    revenu_imposable_net: float              # C16
    revenu_imposable_foyer: float            # C17
    ir_foyer: float                          # C23
    cehr: float                              # C25
    cdhr: float                              # C27
    total_impots_foyer: float                # C28
    impots_imputables_rem: float             # C29
    net_apres_impots: float                  # C30


# ============================================================
# 3. CALCUL MODULE SALARIÉ
# ============================================================
def calcul_module_salarie(profil: Profil, salaire_brut: float) -> ResultatSalarie:
    """
    Transposition fidèle du module Salarié (formules C5-C30 onglet 10).

    Note : aucune correction silencieuse - les formules sont propres.
    Le seul input du module est le salaire brut annuel.
    """
    # --- Section 2 : Cotisations & net (formules C8-C11) ---
    cotis_salariales = salaire_brut * TX_SALARIAL                              # C8
    csg_crds_totale = salaire_brut * ASSIETTE_CSG_SAL * TX_CSG_CRDS_ACT        # C9
    csg_deductible = salaire_brut * ASSIETTE_CSG_SAL * 0.068                   # C10
    net_avant_impot = salaire_brut - cotis_salariales - csg_crds_totale        # C11

    # --- Section 3 : IR ---
    # C14 = C11 + C9 - C10 = brut − cotis hors CSG − CSG déductible
    # La CSG non déductible (2,9 %) reste dans la base imposable
    revenu_salarial_imposable = net_avant_impot + csg_crds_totale - csg_deductible

    # C15 - Abattement 10 % plafonné à 14 426 €
    abattement_10pct = min(revenu_salarial_imposable * 0.10, PLAFOND_ABAT_10PCT_SAL)

    # C16 - Revenu imposable net
    revenu_imposable_net = max(0, revenu_salarial_imposable - abattement_10pct)

    # C17 - Revenu imposable foyer
    revenu_imposable_foyer = revenu_imposable_net + profil.autres_revenus

    # Délégation à calcul_ir_foyer pour la chaîne IR + QF + CEHR + CDHR
    impots = calcul_ir_foyer(revenu_imposable_foyer, profil)

    # C29 - Impôts imputables à la rémunération (prorata, formule directe et correcte)
    prorata = revenu_imposable_net / revenu_imposable_foyer if revenu_imposable_foyer > 0 else 1.0
    impots_imputables_rem = impots["total_impots"] * prorata

    # C30 - Net après impôts (sur la base de C11, pas C14)
    net_apres_impots = net_avant_impot - impots_imputables_rem

    return ResultatSalarie(
        salaire_brut=salaire_brut,
        cotis_salariales=cotis_salariales,
        csg_crds_totale=csg_crds_totale,
        csg_deductible=csg_deductible,
        net_avant_impot=net_avant_impot,
        revenu_salarial_imposable=revenu_salarial_imposable,
        abattement_10pct=abattement_10pct,
        revenu_imposable_net=revenu_imposable_net,
        revenu_imposable_foyer=revenu_imposable_foyer,
        ir_foyer=impots["ir_foyer"],
        cehr=impots["cehr"],
        cdhr=impots["cdhr"],
        total_impots_foyer=impots["total_impots"],
        impots_imputables_rem=impots_imputables_rem,
        net_apres_impots=net_apres_impots,
    )
