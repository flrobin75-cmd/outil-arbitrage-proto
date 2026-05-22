"""
Core Engine — Calcul IR foyer complet.

Reproduit la chaîne IR + plafonnement QF (4 cas) + CEHR + CDHR.
Transposition fidèle des formules C19 à C29 de l'onglet "8. TNS" v19
(identiques aux modules 7 Salarié, 9 Libéral, 10 Assimilé).

Module pivot : consommé par tous les modules de calcul net.
"""

from .profil import (
    Profil, SITUATIONS_PARTICULIERES,
    IR_PLAFOND_T1, IR_PLAFOND_T2, IR_PLAFOND_T3, IR_PLAFOND_T4,
    IR_TAUX_T2, IR_TAUX_T3, IR_TAUX_T4, IR_TAUX_T5,
    PLAF_QF_DEMI_PART,
    CEHR_SEUIL_C1, CEHR_SEUIL_C2, CEHR_SEUIL_M1, CEHR_SEUIL_M2,
    CEHR_TX_1, CEHR_TX_2,
    CDHR_TAUX_PLANCHER, CDHR_SEUIL_C, CDHR_SEUIL_M,
    CDHR_SEUIL_C_HAUT, CDHR_SEUIL_M_HAUT,
    TX_PFU_IR,
)


def ir_par_tranche(revenu_par_part: float) -> float:
    """Barème progressif appliqué à un revenu par part."""
    if revenu_par_part <= IR_PLAFOND_T1:
        return 0.0
    if revenu_par_part <= IR_PLAFOND_T2:
        return (revenu_par_part - IR_PLAFOND_T1) * IR_TAUX_T2
    if revenu_par_part <= IR_PLAFOND_T3:
        return ((IR_PLAFOND_T2 - IR_PLAFOND_T1) * IR_TAUX_T2
                + (revenu_par_part - IR_PLAFOND_T2) * IR_TAUX_T3)
    if revenu_par_part <= IR_PLAFOND_T4:
        return ((IR_PLAFOND_T2 - IR_PLAFOND_T1) * IR_TAUX_T2
                + (IR_PLAFOND_T3 - IR_PLAFOND_T2) * IR_TAUX_T3
                + (revenu_par_part - IR_PLAFOND_T3) * IR_TAUX_T4)
    return ((IR_PLAFOND_T2 - IR_PLAFOND_T1) * IR_TAUX_T2
            + (IR_PLAFOND_T3 - IR_PLAFOND_T2) * IR_TAUX_T3
            + (IR_PLAFOND_T4 - IR_PLAFOND_T3) * IR_TAUX_T4
            + (revenu_par_part - IR_PLAFOND_T4) * IR_TAUX_T5)


def tmi_de(revenu_par_part: float) -> float:
    """Renvoie le taux marginal applicable à un revenu par part."""
    if revenu_par_part <= IR_PLAFOND_T1:
        return 0.0
    if revenu_par_part <= IR_PLAFOND_T2:
        return IR_TAUX_T2
    if revenu_par_part <= IR_PLAFOND_T3:
        return IR_TAUX_T3
    if revenu_par_part <= IR_PLAFOND_T4:
        return IR_TAUX_T4
    return IR_TAUX_T5


def calcul_ir_foyer(revenu_imposable_foyer: float, profil: Profil) -> dict:
    """
    Reproduit la chaîne IR + plafonnement QF (4 cas) + CEHR + CDHR.

    Transposition fidèle des formules C19 à C29 de l'onglet "8. TNS"
    (identiques aux modules 7, 9, 10).
    """
    # Parts de référence (sans demi-parts excédentaires)
    parts_ref = 2 if profil.situation == "Marié / pacsé" else 1

    # IR avec QF (formule C19, C20)
    revenu_par_part = revenu_imposable_foyer / profil.parts
    ir_par_part = ir_par_tranche(revenu_par_part)
    ir_avec_qf = ir_par_part * profil.parts

    # IR sans QF (formule C21 - référence pour plafonnement)
    revenu_par_part_ref = revenu_imposable_foyer / parts_ref
    ir_sans_qf = ir_par_tranche(revenu_par_part_ref) * parts_ref

    # Plafonnement QF (formule C22 - cas général + 4 cas particuliers)
    demi_parts_excedentaires = (profil.parts - parts_ref) * 2

    if demi_parts_excedentaires <= 0:
        plaf = 0.0
    else:
        situation_part_info = SITUATIONS_PARTICULIERES.get(profil.situation_part)
        if situation_part_info is None:
            # Cas général : 1 807 € par demi-part excédentaire
            plaf = PLAF_QF_DEMI_PART * demi_parts_excedentaires
        else:
            # Cas particuliers : plafond spécifique sur la 1ère demi-part,
            # puis PLAF_QF_DEMI_PART pour le reste
            type_situation, plaf_special = situation_part_info
            if demi_parts_excedentaires >= 1:
                plaf = plaf_special + max(0, demi_parts_excedentaires - 1) * PLAF_QF_DEMI_PART
            else:
                plaf = 0.0

    excedent_qf = max(0, (ir_sans_qf - ir_avec_qf) - plaf)
    ir_foyer = ir_avec_qf + excedent_qf

    # RFR élargi = revenu imposable + dividendes hors enveloppe au PFU
    rfr = revenu_imposable_foyer + profil.dividendes_foyer_hors_enveloppe

    # CEHR (formule C25)
    if profil.situation == "Marié / pacsé":
        s1, s2 = CEHR_SEUIL_M1, CEHR_SEUIL_M2
    else:
        s1, s2 = CEHR_SEUIL_C1, CEHR_SEUIL_C2
    if rfr <= s1:
        cehr = 0.0
    elif rfr <= s2:
        cehr = (rfr - s1) * CEHR_TX_1
    else:
        cehr = (s2 - s1) * CEHR_TX_1 + (rfr - s2) * CEHR_TX_2

    # IR forfaitaire sur dividendes (PFU 12,8 %) - formule C26
    ir_pfu_div = profil.dividendes_foyer_hors_enveloppe * TX_PFU_IR

    # CDHR (formule C27)
    cdhr_seuil_bas = CDHR_SEUIL_M if profil.situation == "Marié / pacsé" else CDHR_SEUIL_C
    cdhr_seuil_haut = CDHR_SEUIL_M_HAUT if profil.situation == "Marié / pacsé" else CDHR_SEUIL_C_HAUT
    if rfr <= cdhr_seuil_bas:
        cdhr = 0.0
    else:
        deficit = max(0, CDHR_TAUX_PLANCHER * rfr - (ir_foyer + ir_pfu_div + cehr))
        coeff_lissage = min(1, max(0, (rfr - cdhr_seuil_bas) / (cdhr_seuil_haut - cdhr_seuil_bas)))
        cdhr = deficit * coeff_lissage

    total_impots = ir_foyer + cehr + cdhr
    taux_moyen = total_impots / revenu_imposable_foyer if revenu_imposable_foyer > 0 else 0.0

    return {
        "ir_avec_qf": ir_avec_qf,
        "ir_sans_qf": ir_sans_qf,
        "plaf_qf": plaf,
        "ir_foyer": ir_foyer,
        "cehr": cehr,
        "cdhr": cdhr,
        "ir_pfu_div": ir_pfu_div,
        "total_impots": total_impots,
        "taux_moyen": taux_moyen,
        "revenu_par_part": revenu_par_part,
        "tmi": tmi_de(revenu_par_part),
    }
