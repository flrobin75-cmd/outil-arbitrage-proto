"""
Regime Engine — Module Libéral (BNC + SEL).

Transposition fidèle de l'onglet "9. Libéral" du classeur v19.

Décisions validées (cf. Cadre méthodologique v1.0.1 §3.3) :
- Fiscalité dirigeant SEL : périmètre v19 conservé (uniquement IS société dans ce module)
- Dissymétrie CSG non déductible (Libéral sur bénéfice seul vs TNS sur net+cot) : reproduite
- Taux réduit IS appliqué jusqu'à 42 500 € sans vérification éligibilité PME : reproduit

Structure :
    1. Imports et constantes
    2. Dataclasses résultats BNC / SEL
    3. calcul_module_bnc()
    4. calcul_module_sel()
"""

# ============================================================
# 1. IMPORTS
# ============================================================
from dataclasses import dataclass

from core.profil import (
    Profil, TX_LIB,
    TX_IS_REDUIT, TX_IS_NORMAL, IS_PLAF_REDUIT,
)
from core.ir_foyer import calcul_ir_foyer


# ============================================================
# 2. DATACLASSES RÉSULTATS BNC / SEL
# ============================================================
@dataclass
class ResultatBNC:
    """Résultat scénario BNC (exercice individuel)."""
    # Inputs
    recettes: float
    frais_pro: float

    # Section BNC (formules C7-C25)
    benefice_bnc: float
    cotisations: float
    csg_non_deductible: float
    benefice_net_apres_cotis: float       # C10 - base du net cash
    revenu_imposable_lib: float           # C11 - réintégration CSG non déd.
    revenu_imposable_foyer: float         # C12
    ir_foyer: float
    cehr: float
    cdhr: float
    total_impots_foyer: float
    impots_imputables_libéral: float       # C24
    net_apres_impots: float                # C25


@dataclass
class ResultatSEL:
    """Résultat scénario SEL (SELARL/SELAS - double couche IS + IR)."""
    # Inputs
    benefice_avant_rem: float
    remuneration_dirigeant: float

    # Section SEL (formules C28-C33)
    benefice_imposable_is: float
    is_du: float
    resultat_net_distribuable: float
    dividendes_envisages: float


# ============================================================
# 3. CALCUL SCÉNARIO BNC (formules C5-C25)
# ============================================================
def calcul_module_bnc(profil: Profil,
                      recettes: float,
                      frais_pro: float = 0.0) -> ResultatBNC:
    """
    Transposition fidèle du scénario BNC (formules C5-C25 onglet 9).

    Note : aucune correction silencieuse n'est nécessaire ici.
    La formule C24 est mathématiquement correcte (contrairement au TNS C32).
    """
    # --- Section calcul du bénéfice et des cotisations ---
    benefice_bnc = recettes - frais_pro                              # C7
    cotisations = benefice_bnc * TX_LIB                              # C8 - inclut CSG/CRDS selon E8
    csg_non_deductible = benefice_bnc * 0.029                        # C9 - sur bénéfice (pas sur net+cot, différence avec TNS)
    benefice_net_apres_cotis = benefice_bnc - cotisations            # C10 - cash réellement perçu

    # --- Section IR ---
    revenu_imposable_lib = benefice_net_apres_cotis + csg_non_deductible   # C11 - réintégration CSG
    revenu_imposable_foyer = revenu_imposable_lib + profil.autres_revenus  # C12

    # Délégation à calcul_ir_foyer pour la chaîne IR + QF + CEHR + CDHR
    impots = calcul_ir_foyer(revenu_imposable_foyer, profil)

    # Impôts imputables à l'activité libérale (formule C24 - mathématiquement correcte)
    # C24 = C23 × (C11/C12) = total_impots × (rev_lib / rev_foyer)
    prorata_lib = revenu_imposable_lib / revenu_imposable_foyer if revenu_imposable_foyer > 0 else 1.0
    impots_imputables = impots["total_impots"] * prorata_lib

    # Net libéral après impôts (formule C25)
    # = bénéfice net cash (C10) − impôts imputables
    net_apres_impots = benefice_net_apres_cotis - impots_imputables

    return ResultatBNC(
        recettes=recettes,
        frais_pro=frais_pro,
        benefice_bnc=benefice_bnc,
        cotisations=cotisations,
        csg_non_deductible=csg_non_deductible,
        benefice_net_apres_cotis=benefice_net_apres_cotis,
        revenu_imposable_lib=revenu_imposable_lib,
        revenu_imposable_foyer=revenu_imposable_foyer,
        ir_foyer=impots["ir_foyer"],
        cehr=impots["cehr"],
        cdhr=impots["cdhr"],
        total_impots_foyer=impots["total_impots"],
        impots_imputables_libéral=impots_imputables,
        net_apres_impots=net_apres_impots,
    )


# ============================================================
# 4. CALCUL SCÉNARIO SEL (formules C28-C33)
# ============================================================
def calcul_module_sel(benefice_avant_rem: float,
                      remuneration_dirigeant: float) -> ResultatSEL:
    """
    Transposition fidèle du scénario SEL (formules C28-C33 onglet 9).

    Périmètre v19 : uniquement IS société (la fiscalité du dirigeant SEL
    est traitée dans le module 7 Assimilé pour SELAS ou module 8 TNS pour SELARL).

    Note : applique systématiquement le taux IS réduit 15 % jusqu'à 42 500 €
    sans vérifier l'éligibilité PME — simplification v19 reproduite.
    """
    # Bénéfice imposable IS (formule C30)
    benefice_imposable_is = max(0, benefice_avant_rem - remuneration_dirigeant)

    # IS dû (formule C31)
    fraction_reduite = min(benefice_imposable_is, IS_PLAF_REDUIT)
    fraction_normale = max(0, benefice_imposable_is - IS_PLAF_REDUIT)
    is_du = fraction_reduite * TX_IS_REDUIT + fraction_normale * TX_IS_NORMAL

    # Résultat net distribuable (formule C32)
    resultat_net_distribuable = benefice_imposable_is - is_du

    # Dividendes envisagés - par défaut = totalité du résultat net (formule C33)
    dividendes_envisages = resultat_net_distribuable

    return ResultatSEL(
        benefice_avant_rem=benefice_avant_rem,
        remuneration_dirigeant=remuneration_dirigeant,
        benefice_imposable_is=benefice_imposable_is,
        is_du=is_du,
        resultat_net_distribuable=resultat_net_distribuable,
        dividendes_envisages=dividendes_envisages,
    )
