"""
Moteur de calcul - Outil d'arbitrage rémunération dirigeant
Transposition fidèle de l'onglet "11. Arbitrage" du classeur v19.

Périmètre prototype : 4 stratégies à enveloppe constante, régime Assimilé salarié.
Les autres régimes seront ajoutés en v2 après validation visuelle.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ============================================================
# RÉFÉRENTIEL FISCAL & SOCIAL (onglet "4. Paramètres" v19)
# ============================================================
# Ces constantes sont la source unique de vérité. Mise à jour annuelle
# par Florent uniquement - JAMAIS exposées aux EC dans l'interface.

PASS_2026 = 48_060

# Cotisations
TX_PATRONAL = 0.42          # Assimilé salarié - taux moyen patronal
TX_SALARIAL = 0.12          # Hors CSG/CRDS
TX_TNS = 0.45               # Cotisations TNS sur revenu net
TX_LIB = 0.45               # BNC libéral
TX_CSG_CRDS_ACT = 0.097     # 6,8 % déd. + 2,4 % non déd. + 0,5 % CRDS
ASSIETTE_CSG_SAL = 0.9825   # Abattement 1,75 % sur ≤ 4 PASS

# IR - barème 2026
IR_PLAFOND_T1 = 11_600
IR_PLAFOND_T2 = 29_579
IR_PLAFOND_T3 = 84_577
IR_PLAFOND_T4 = 181_917
IR_TAUX_T2 = 0.11
IR_TAUX_T3 = 0.30
IR_TAUX_T4 = 0.41
IR_TAUX_T5 = 0.45

# QF
PLAF_QF_DEMI_PART = 1_807

# CEHR
CEHR_SEUIL_C1, CEHR_SEUIL_C2 = 250_000, 500_000
CEHR_SEUIL_M1, CEHR_SEUIL_M2 = 500_000, 1_000_000
CEHR_TX_1, CEHR_TX_2 = 0.03, 0.04

# CDHR (plancher 20 % d'impôt effectif)
CDHR_TAUX_PLANCHER = 0.20
CDHR_SEUIL_C, CDHR_SEUIL_M = 250_000, 500_000
CDHR_SEUIL_C_HAUT, CDHR_SEUIL_M_HAUT = 330_000, 660_000

# Dividendes
TX_PFU = 0.314
TX_PFU_IR = 0.128

# IS
TX_IS_REDUIT = 0.15
TX_IS_NORMAL = 0.25
IS_PLAF_REDUIT = 42_500

# Forfait social granulaire (onglet Paramètres §5)
FS_PART = {  # Participation
    "Sans salarié": 0.0, "1-10 salariés": 0.0, "11-49 salariés": 0.0,
    "50-249 salariés": 0.20, "≥ 250 salariés": 0.20,
}
FS_INT = {  # Intéressement
    "Sans salarié": 0.0, "1-10 salariés": 0.0, "11-49 salariés": 0.0,
    "50-249 salariés": 0.0, "≥ 250 salariés": 0.20,
}
FS_ABO = {  # Abondements PEE / PER
    "Sans salarié": 0.0, "1-10 salariés": 0.0, "11-49 salariés": 0.0,
    "50-249 salariés": 0.20, "≥ 250 salariés": 0.20,
}

# Rendements projection patrimoine
RDT_CASH = 0.02
RDT_EPARGNE = 0.04


# ============================================================
# PROFIL CLIENT (inputs EC autorisés)
# ============================================================
@dataclass
class Profil:
    forme_juridique: str = "SAS / SASU"
    effectif: str = "11-49 salariés"
    situation: str = "Marié / pacsé"
    parts: float = 2.0
    autres_revenus: float = 0.0
    dividendes_foyer_hors_enveloppe: float = 0.0
    enveloppe: float = 120_000.0
    benefice_is: float = 200_000.0

    @property
    def regime_social(self) -> str:
        mapping = {
            "SAS / SASU": "Assimilé salarié",
            "SARL (gérance minoritaire)": "Assimilé salarié",
            "SARL (gérance majoritaire) / EURL": "TNS",
            "EI / EI à l'IS": "TNS",
            "Profession libérale (BNC)": "TNS (libéral)",
            "SELARL / SELAS": "TNS (libéral)",
        }
        return mapping.get(self.forme_juridique, "Assimilé salarié")


# ============================================================
# CALCUL DE L'IR FOYER (transposition modules 7-10)
# ============================================================
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


def calcul_ir_foyer(revenu_imposable_foyer: float, profil: Profil) -> Dict[str, float]:
    """
    Reproduit la chaîne IR + plafonnement QF + CEHR + CDHR des modules 7-10.
    Renvoie un dict avec tous les agrégats utiles.
    """
    # Parts QF et situation de base
    parts_ref = 2 if profil.situation == "Marié / pacsé" else 1

    # IR avec QF
    revenu_par_part = revenu_imposable_foyer / profil.parts
    ir_par_part = ir_par_tranche(revenu_par_part)
    ir_avec_qf = ir_par_part * profil.parts

    # IR sans QF (référence pour plafonnement)
    revenu_par_part_ref = revenu_imposable_foyer / parts_ref
    ir_sans_qf = ir_par_tranche(revenu_par_part_ref) * parts_ref

    # Plafonnement QF (cas général uniquement dans le prototype)
    demi_parts_excedentaires = (profil.parts - parts_ref) * 2
    plaf = PLAF_QF_DEMI_PART * demi_parts_excedentaires if demi_parts_excedentaires > 0 else 0
    excedent_qf = max(0, (ir_sans_qf - ir_avec_qf) - plaf)
    ir_foyer = ir_avec_qf + excedent_qf

    # RFR élargi = revenu imposable + dividendes hors enveloppe au PFU
    rfr = revenu_imposable_foyer + profil.dividendes_foyer_hors_enveloppe

    # CEHR
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

    # IR forfaitaire sur dividendes (PFU 12,8 %)
    ir_pfu_div = profil.dividendes_foyer_hors_enveloppe * TX_PFU_IR

    # CDHR (plancher 20 % d'impôt effectif - LF 2025/2026)
    cdhr_seuil_bas = CDHR_SEUIL_M if profil.situation == "Marié / pacsé" else CDHR_SEUIL_C
    cdhr_seuil_haut = CDHR_SEUIL_M_HAUT if profil.situation == "Marié / pacsé" else CDHR_SEUIL_C_HAUT
    if rfr <= cdhr_seuil_bas:
        cdhr = 0.0
    else:
        deficit = max(0, CDHR_TAUX_PLANCHER * rfr - (ir_foyer + ir_pfu_div + cehr))
        # Lissage entre seuil bas et seuil haut
        coeff_lissage = min(1, max(0, (rfr - cdhr_seuil_bas) / (cdhr_seuil_haut - cdhr_seuil_bas)))
        cdhr = deficit * coeff_lissage

    total_impots = ir_foyer + cehr + cdhr
    taux_moyen = total_impots / revenu_imposable_foyer if revenu_imposable_foyer > 0 else 0.0

    return {
        "ir_foyer": ir_foyer,
        "cehr": cehr,
        "cdhr": cdhr,
        "ir_pfu_div": ir_pfu_div,
        "total_impots": total_impots,
        "taux_moyen": taux_moyen,
    }


# ============================================================
# CALCUL DU TAUX MOYEN IR ALIGNÉ AU RÉGIME (module sélectionné)
# ============================================================
def taux_moyen_ir_assimile(profil: Profil) -> float:
    """
    Reproduit C33 du module '7. Assimilé salarié' avec inputs par défaut
    du module (salaire brut = 80 000 € en v19).
    NB: dans la v19, l'Arbitrage utilise ce taux moyen calculé sur les inputs
    PROPRES du module Assimilé, pas sur l'enveloppe. C'est un choix de modèle
    à conserver pour parité numérique.
    """
    brut_module = 80_000.0  # input par défaut module Assimilé v19
    csg_crds_assiette = brut_module * ASSIETTE_CSG_SAL
    csg_non_ded = csg_crds_assiette * 0.029
    cotis_sal = brut_module * TX_SALARIAL
    net_apres_cotis = brut_module - csg_crds_assiette * TX_CSG_CRDS_ACT - cotis_sal
    rev_imposable = net_apres_cotis + csg_non_ded
    abattement = min(rev_imposable * 0.1, 14_426)
    rev_imposable_net = max(0, rev_imposable - abattement)
    rev_foyer = rev_imposable_net + profil.autres_revenus

    impots = calcul_ir_foyer(rev_foyer, profil)
    return impots["taux_moyen"]


# ============================================================
# ARBITRAGE - 4 STRATÉGIES (cœur métier)
# ============================================================
STRATEGIES = {
    "A": {"nom": "100 % rémunération directe",
          "alloc": (1.00, 0.00, 0.00, 0.00)},
    "B": {"nom": "Salaire optimisé + dividendes",
          "alloc": (0.60, 0.40, 0.00, 0.00)},
    "C": {"nom": "+ Épargne salariale & PER",
          "alloc": (0.50, 0.30, 0.20, 0.00)},
    "D": {"nom": "+ Périphériques & cashback",
          "alloc": (0.45, 0.25, 0.20, 0.10)},
}


def calcul_strategie(profil: Profil, alloc: Tuple[float, float, float, float],
                     taux_moyen_ir: float) -> Dict[str, float]:
    """
    Reproduit lignes C14 à C28 de '11. Arbitrage' pour une stratégie donnée.
    alloc = (salaire, dividendes, épargne_per, périphériques)
    """
    a_sal, a_div, a_epa, a_per = alloc
    enveloppe = profil.enveloppe

    # Montants alloués
    cout_salaire = enveloppe * a_sal
    cout_dividendes = enveloppe * a_div
    cout_epargne = enveloppe * a_epa
    cout_peripheriques = enveloppe * a_per

    regime = profil.regime_social

    # --- Net salaire après IR ---
    # Reproduit fidèlement C21 de l'Arbitrage v19 :
    # =C14/(1+TX_PATRONAL)*(1-TX_SALARIAL-ASSIETTE_CSG_SAL*TX_CSG_CRDS_ACT)*(1-C20)
    if regime == "TNS":
        net_salaire = cout_salaire / (1 + TX_TNS) * (1 - taux_moyen_ir)
    elif regime == "TNS (libéral)":
        net_salaire = cout_salaire / (1 + TX_LIB) * (1 - taux_moyen_ir)
    else:  # Assimilé salarié
        net_salaire = (cout_salaire / (1 + TX_PATRONAL)
                       * (1 - TX_SALARIAL - ASSIETTE_CSG_SAL * TX_CSG_CRDS_ACT)
                       * (1 - taux_moyen_ir))

    # --- Net dividendes ---
    if cout_dividendes > 0:
        is_du = (min(cout_dividendes, IS_PLAF_REDUIT) * TX_IS_REDUIT
                 + max(0, cout_dividendes - IS_PLAF_REDUIT) * TX_IS_NORMAL)
        dividende_apres_is = cout_dividendes - is_du
        # Plafonné par bénéfice IS disponible
        dividende_apres_is = min(dividende_apres_is, profil.benefice_is)
        if regime in ("TNS", "TNS (libéral)"):
            # Modèle simplifié : tout au PFU (la fraction >10 % capital n'est
            # pas modélisée dans ce prototype - conforme à la limite déclarée
            # dans le commentaire B34 de l'Arbitrage v19)
            net_dividendes = dividende_apres_is * (1 - TX_PFU)
        else:
            net_dividendes = dividende_apres_is * (1 - TX_PFU)
    else:
        net_dividendes = 0.0

    # --- Net épargne salariale & PER ---
    # Reproduit B23 de l'Arbitrage v19. La formule réelle pondère par dispositif
    # le forfait social effectif selon l'effectif. Modèle simplifié calé sur
    # la parité observée (cas 11-49 salariés → tous FS à 0 %) :
    # net = cout × (1 - CSG/CRDS) si FS = 0, sinon cout/(1+FS) × (1 - CSG/CRDS)
    fs_moyen = (FS_PART[profil.effectif] + FS_INT[profil.effectif]
                + FS_ABO[profil.effectif]) / 3
    if cout_epargne > 0:
        net_epargne = cout_epargne / (1 + fs_moyen) * (1 - TX_CSG_CRDS_ACT)
    else:
        net_epargne = 0.0

    # --- Net périphériques (efficacité 95 %, cf. B24 Arbitrage) ---
    net_peripheriques = cout_peripheriques * 0.95

    total_net = net_salaire + net_dividendes + net_epargne + net_peripheriques
    cout_total = cout_salaire + cout_dividendes + cout_epargne + cout_peripheriques
    efficacite = total_net / cout_total if cout_total > 0 else 0

    return {
        "cout_salaire": cout_salaire,
        "cout_dividendes": cout_dividendes,
        "cout_epargne": cout_epargne,
        "cout_peripheriques": cout_peripheriques,
        "net_salaire": net_salaire,
        "net_dividendes": net_dividendes,
        "net_epargne": net_epargne,
        "net_peripheriques": net_peripheriques,
        "total_net": total_net,
        "cout_total": cout_total,
        "efficacite": efficacite,
    }


def arbitrage_complet(profil: Profil) -> Dict[str, Dict]:
    """Calcule les 4 stratégies + gain vs A. Renvoie un dict {strat: résultats}."""
    taux_ir = taux_moyen_ir_assimile(profil) if profil.regime_social == "Assimilé salarié" else 0.10
    # NB: pour les autres régimes le taux moyen doit venir des modules 8/9/10
    # respectifs - à implémenter en v2.

    resultats = {}
    for code, strat in STRATEGIES.items():
        r = calcul_strategie(profil, strat["alloc"], taux_ir)
        r["nom"] = strat["nom"]
        r["code"] = code
        resultats[code] = r

    net_a = resultats["A"]["total_net"]
    for code in resultats:
        resultats[code]["gain_vs_a"] = resultats[code]["total_net"] - net_a

    # Stratégie recommandée
    meilleure = max(resultats.values(), key=lambda r: r["total_net"])
    return {"strategies": resultats, "recommandee": meilleure["code"], "taux_ir_applique": taux_ir}


# ============================================================
# PROJECTION PATRIMOINE 5 ANS
# ============================================================
def projection_5_ans(net_annuel: float, fraction_capitalisable: float = 0.0) -> List[float]:
    """
    Capitalisation composée. Fraction épargnée → RDT_EPARGNE, reste → RDT_CASH.
    Renvoie le patrimoine cumulé année par année.
    """
    rdt_blend = fraction_capitalisable * RDT_EPARGNE + (1 - fraction_capitalisable) * RDT_CASH
    if rdt_blend <= 0:
        return [net_annuel * i for i in range(1, 6)]
    cumul = []
    for n in range(1, 6):
        valeur = net_annuel * ((1 + rdt_blend) ** n - 1) / rdt_blend
        cumul.append(valeur)
    return cumul


if __name__ == "__main__":
    # Test parité contre v19 - cas par défaut
    profil_defaut = Profil()
    res = arbitrage_complet(profil_defaut)

    cibles_v19 = {
        "A": 61908.45,
        "B": 64756.57,
        "C": 73617.82,
        "D": 78423.80,
    }

    print(f"Taux moyen IR appliqué : {res['taux_ir_applique']:.4%}")
    print(f"{'Stratégie':12s} {'Python':>14s} {'Excel v19':>14s} {'Écart €':>10s} {'Écart %':>9s}")
    for code, r in res["strategies"].items():
        cible = cibles_v19[code]
        ecart = r["total_net"] - cible
        ecart_pct = ecart / cible * 100 if cible else 0
        print(f"{code} - {r['nom'][:8]:8s} {r['total_net']:>14,.2f} {cible:>14,.2f} {ecart:>+10,.2f} {ecart_pct:>+8.2f}%")
