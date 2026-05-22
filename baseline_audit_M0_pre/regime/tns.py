"""
Regime Engine — Module TNS (gérant majoritaire / EURL).

Transposition fidèle de l'onglet "8. TNS" du classeur v19, avec corrections
documentées des anomalies identifiées en phase d'audit.

Décisions validées (cf. Cadre méthodologique v1.0.1 §3.2) :
- Anomalie A (C32 buggué utilisant C31 au lieu de C29) → CORRIGÉE silencieusement
- Anomalie B (doublon capital social Profil/Module) → INPUT PROFIL unique
- Anomalie C (TMI approximé sur fraction TNS-imposée) → REPRODUITE telle quelle pour parité

Module : consomme uniquement core (Profil, IR foyer). Aucun import croisé vers
d'autres regimes ou strategies.
"""

from dataclasses import dataclass

from core.profil import Profil, TX_TNS, TX_PFU, SEUIL_DIV_TNS
from core.ir_foyer import calcul_ir_foyer


# ============================================================
# RÉSULTAT TNS
# ============================================================
@dataclass
class ResultatTNS:
    """Résultat complet d'un calcul TNS pour une rémunération souhaitée."""
    # Inputs
    rem_nette_souhaitee: float
    frais_reels: float

    # Section 2 - Cotisations TNS (formules C9-C12)
    cotisations_tns: float
    csg_deductible: float
    csg_non_deductible: float

    # Section 3 - IR (formules C15-C32)
    revenu_net_pro: float
    revenu_imposable: float
    revenu_imposable_foyer: float
    ir_foyer: float
    cehr: float
    cdhr: float
    total_impots_foyer: float
    taux_moyen_ir: float
    impots_imputables_rem: float

    # Section 4 - Net (formule C35)
    net_apres_ir: float

    # Section 5 - Coût (formules C38-C39)
    cout_total_societe: float
    ratio_net_cout: float

    # Section 6 - Dividendes TNS gérant maj. (formules C42-C50)
    capital_cca: float
    seuil_10pct: float
    div_bruts: float
    fraction_cotis_tns: float
    cotis_tns_sur_div: float
    fraction_pfu: float
    pfu_sur_fraction: float
    ir_sur_fraction_tns: float
    net_dividendes: float


# ============================================================
# CALCUL MODULE TNS
# ============================================================
def calcul_module_tns(profil: Profil,
                      rem_nette_souhaitee: float,
                      frais_reels: float = 0.0,
                      div_bruts: float = 0.0) -> ResultatTNS:
    """
    Transposition fidèle du module "8. TNS" v19.

    Correction silencieuse de l'anomalie A : formule C32 corrigée pour utiliser
    le bon taux moyen IR (C29) au lieu du bug de double division (C31).

    Args:
        profil: Profil client (avec capital_cca pris du Profil, décision B)
        rem_nette_souhaitee: Rémunération nette annuelle souhaitée (€)
        frais_reels: Frais réels professionnels déductibles (€)
        div_bruts: Dividendes bruts envisagés (€)
    """
    # --- Section 2 : Cotisations TNS (formules C9-C12) ---
    cotisations_tns = rem_nette_souhaitee * TX_TNS
    csg_deductible = (rem_nette_souhaitee + cotisations_tns) * 0.068
    csg_non_deductible = (rem_nette_souhaitee + cotisations_tns) * 0.029

    # --- Section 3 : IR (formules C15-C32) ---
    revenu_net_pro = rem_nette_souhaitee - frais_reels
    revenu_imposable = revenu_net_pro + csg_non_deductible  # formule C16
    revenu_imposable_foyer = revenu_imposable + profil.autres_revenus  # formule C17

    # Délégation à calcul_ir_foyer pour la chaîne IR + QF + CEHR + CDHR
    impots = calcul_ir_foyer(revenu_imposable_foyer, profil)

    # Impôts imputables à la rémunération (prorata)
    # CORRECTION ANOMALIE A : utilisation du vrai taux moyen (C29) et non C31 buggué
    prorata = revenu_imposable / revenu_imposable_foyer if revenu_imposable_foyer > 0 else 0.0
    impots_imputables_rem = impots["taux_moyen"] * revenu_imposable_foyer * prorata

    # --- Section 4 : Net dirigeant après IR (formule C35) ---
    net_apres_ir = rem_nette_souhaitee - impots_imputables_rem

    # --- Section 5 : Coût pour la société (formules C38-C39) ---
    cout_total_societe = rem_nette_souhaitee + cotisations_tns
    ratio_net_cout = net_apres_ir / cout_total_societe if cout_total_societe > 0 else 0.0

    # --- Section 6 : Dividendes TNS gérant majoritaire (formules C42-C50) ---
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS
    fraction_cotis_tns = max(0, div_bruts - seuil_10pct)
    cotis_tns_sur_div = fraction_cotis_tns * TX_TNS
    fraction_pfu = div_bruts - fraction_cotis_tns
    pfu_sur_fraction = fraction_pfu * TX_PFU

    # IR sur fraction TNS-imposée : approximation v19 (TMI selon revenu par part)
    # Anomalie C - reproduite telle quelle (décision C)
    tmi = impots["tmi"]
    ir_sur_fraction_tns = fraction_cotis_tns * tmi

    net_dividendes = div_bruts - cotis_tns_sur_div - pfu_sur_fraction - ir_sur_fraction_tns

    return ResultatTNS(
        rem_nette_souhaitee=rem_nette_souhaitee,
        frais_reels=frais_reels,
        cotisations_tns=cotisations_tns,
        csg_deductible=csg_deductible,
        csg_non_deductible=csg_non_deductible,
        revenu_net_pro=revenu_net_pro,
        revenu_imposable=revenu_imposable,
        revenu_imposable_foyer=revenu_imposable_foyer,
        ir_foyer=impots["ir_foyer"],
        cehr=impots["cehr"],
        cdhr=impots["cdhr"],
        total_impots_foyer=impots["total_impots"],
        taux_moyen_ir=impots["taux_moyen"],
        impots_imputables_rem=impots_imputables_rem,
        net_apres_ir=net_apres_ir,
        cout_total_societe=cout_total_societe,
        ratio_net_cout=ratio_net_cout,
        capital_cca=profil.capital_cca,
        seuil_10pct=seuil_10pct,
        div_bruts=div_bruts,
        fraction_cotis_tns=fraction_cotis_tns,
        cotis_tns_sur_div=cotis_tns_sur_div,
        fraction_pfu=fraction_pfu,
        pfu_sur_fraction=pfu_sur_fraction,
        ir_sur_fraction_tns=ir_sur_fraction_tns,
        net_dividendes=net_dividendes,
    )
