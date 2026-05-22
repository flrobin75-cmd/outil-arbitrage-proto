"""
Strategy Engine — Stratégies Libéral (L1-L4).

Quatre stratégies de structuration pour le régime Libéral (BNC + SEL) :

- L1 : BNC pur
    Exercice individuel, référence sur même CA.
    Cas d'usage : début de carrière, faible besoin patrimonial.

- L2 : BNC + PERIN
    L1 + déduction PERIN individuelle (plafond individuel par défaut).
    Cas d'usage : réduction d'assiette IR, préparation retraite.

- L3 : SEL IS
    Passage en SELARL ou SELAS, double couche IS + IR.
    SELARL : gérant majoritaire TNS (cotisations ~45%)
    SELAS  : président Assimilé salarié (patronales 42% + salariales 12%)
    Distribution intégrale post-IS (simplification v1).
    Cas d'usage : bénéfice élevé, vision long terme.

- L4 : SEL + Structuration patrimoniale (cadrage minimal v1)
    DÉLÉGUÉ À L3 + alerte structurante v2.
    Ne modélise PAS : holding, démembrement, transmission, SPFPL.
    Mention explicite que ces leviers seront traités en v2.

────────────────────────────────────────────────────────────────────────
GARDE-FOU MÉTHODOLOGIQUE CENTRAL
────────────────────────────────────────────────────────────────────────
Sur L3 et L4, alerte permanente BNC vs SEL :

  « La comparaison BNC / SEL constitue un cadrage indicatif.
    Le passage en SEL implique une analyse juridique, sociale, fiscale
    et patrimoniale complète. Le choix ne peut se réduire à l'arbitrage
    du net dirigeant. »

INTERDICTION : utiliser "recommandée" sur le résultat consolidé Libéral.
Terminologie autorisée : "stratégie la plus efficace fiscalement" ou
"stratégie à étudier" — JAMAIS "stratégie recommandée".
────────────────────────────────────────────────────────────────────────

Décisions méthodologiques validées (cf. Cadre v1.0.1 §4.3) :
- L1 = BNC pur sur même CA que SEL
- L2 = L1 + PERIN individuel par défaut
- L3 = SEL IS avec rémunération SEL saisie par l'EC, distribution intégrale post-IS
- L4 = L3 + mention v2 (pas de calcul holding/transmission fictif)
- forme_sel ∈ {"SELARL", "SELAS"} — validé par enum dans Profil

Module : consomme core (profil, ir_foyer) + regime (liberal, tns, assimile, salarie).
Aucun import vers ui/* ou app.
"""

from dataclasses import dataclass, field
from typing import Optional

from core.profil import (
    Profil,
    TX_TNS, TX_LIB,
    TX_PATRONAL, TX_SALARIAL, TX_CSG_CRDS_ACT, ASSIETTE_CSG_SAL,
    TX_PFU, TX_IS_REDUIT, TX_IS_NORMAL, IS_PLAF_REDUIT,
    FORMES_SEL_VALIDES,
)
from core.ir_foyer import calcul_ir_foyer
from regime.liberal import calcul_module_bnc, calcul_module_sel, ResultatBNC, ResultatSEL
from regime.tns import calcul_module_tns
from regime.salarie import calcul_module_salarie, PLAFOND_ABAT_10PCT_SAL
from strategy.perin import calcul_plafond_perin


# ============================================================
# CONSTANTES MÉTIER
# ============================================================

# Alerte permanente BNC vs SEL (utilisée sur L3 et L4)
ALERTE_BNC_VS_SEL = (
    "La comparaison BNC / SEL constitue un cadrage indicatif. "
    "Le passage en SEL implique une analyse juridique, sociale, fiscale et "
    "patrimoniale complète. Le choix ne peut se réduire à l'arbitrage du net "
    "dirigeant."
)

# Alerte L4 : structuration v2 non modélisée
ALERTE_L4_V2 = (
    "Stratégie L4 — cadrage minimal v1. Les leviers de structuration "
    "patrimoniale avancée (holding patrimoniale, démembrement, transmission, "
    "SPFPL) NE SONT PAS modélisés dans cette version. Une étude dédiée par le "
    "cabinet et un CGP est indispensable avant toute mise en œuvre."
)

# Mention v2 sur la rétention SEL
MENTION_RETENTION_V2 = (
    "Simplification v1 : la SEL distribue l'intégralité du bénéfice après IS. "
    "Pour modéliser une rétention de bénéfice en société, utiliser la stratégie T4 "
    "(Arbitrage IS) sur le module TNS (Phase B.2 Étape 2)."
)


# ============================================================
# DATACLASS RÉSULTAT STRATÉGIE LIBÉRAL
# ============================================================
@dataclass
class ResultatStrategieLib:
    """
    Résultat d'une stratégie Libéral unique (L1, L2, L3 ou L4).

    Note : la dataclass n'a PAS de champ "recommandee" ni d'agrégation
    Libéral / BNC car le choix de structuration est qualitatif et hors
    périmètre de l'outil.
    """
    # Identification
    code: str                            # "L1", "L2", "L3", "L4"
    nom: str                             # Libellé long
    structure: str                       # "BNC" ou "SEL-SELARL" ou "SEL-SELAS"

    # Inputs effectifs (selon structure)
    recettes: float                      # CA libéral (commun à toutes)
    frais_pro: float                     # Frais professionnels (BNC pur uniquement, sinon 0)
    benefice_brut: float                 # Pour BNC : recettes - frais. Pour SEL : input bénéfice avant rém.
    remuneration_brute: float = 0.0      # Pour SEL : remuneration_sel_souhaitee
    versement_perin: float = 0.0         # Pour L2 et L3/L4 si activable

    # Résultats SEL (uniquement L3/L4)
    is_societe: float = 0.0              # IS payé par la SEL
    dividendes_distribues: float = 0.0   # Distribution intégrale post-IS (v1)
    cotisations_sel: float = 0.0         # Cotisations sur rémunération SEL

    # Nets ventilés
    net_remuneration: float = 0.0        # Net après cotis + IR (rémunération SEL)
    net_dividendes: float = 0.0          # Net après PFU sur dividendes
    economie_ir_perin: float = 0.0       # Économie IR liée au versement PERIN
    net_bnc: float = 0.0                 # Pour BNC : net après cotisations TNS + IR

    # Indicateur principal
    net_dirigeant_total: float = 0.0     # Total net pour le dirigeant
                                          # = net_bnc (BNC)
                                          # ou net_remuneration + net_dividendes (SEL)
                                          # + economie_ir_perin (si applicable)

    # Métriques
    efficacite: float = 0.0              # net_dirigeant_total / recettes

    # Alertes (incluant l'alerte BNC/SEL permanente pour L3/L4)
    alertes: list = field(default_factory=list)


@dataclass
class ResultatArbitrageLib:
    """
    Résultat consolidé des 4 stratégies Libéral.

    IMPORTANT — Choix de terminologie :
    - Le champ s'appelle 'plus_efficace_fiscalement', PAS 'recommandee'.
    - Indique uniquement la stratégie au meilleur net_dirigeant_total.
    - NE PAS interpréter comme une recommandation de structuration juridique.
    """
    strategies: dict                      # {"L1": ResultatStrategieLib, ...}
    plus_efficace_fiscalement: str        # Code stratégie meilleur net (PAS "recommandee")
    avertissement_bnc_sel: str            # = ALERTE_BNC_VS_SEL (affichage UI obligatoire)
    profil: Profil


# ============================================================
# HELPER - Calcul IS sur résultat société
# ============================================================
def _calcul_is(benefice_imposable: float) -> float:
    """IS dû selon barème (15% jusqu'à 42 500 €, 25% au-delà)."""
    if benefice_imposable <= 0:
        return 0.0
    fraction_reduite = min(benefice_imposable, IS_PLAF_REDUIT)
    fraction_normale = max(0.0, benefice_imposable - IS_PLAF_REDUIT)
    return fraction_reduite * TX_IS_REDUIT + fraction_normale * TX_IS_NORMAL


# ============================================================
# PLACEHOLDERS - Implémentés dans les sous-étapes 3.3-3.7
# ============================================================
def _calcul_strategie_l1(profil: Profil) -> ResultatStrategieLib:
    """
    L1 — BNC pur (référence sur même CA).

    Exercice individuel : recettes BNC moins frais professionnels donne
    le bénéfice imposable, taxé directement au barème IR avec cotisations
    TNS Libéral (CARMF, CIPAV, etc.) à ~45%.

    C'est la stratégie de référence pour la comparaison avec L2 (PERIN)
    et avec L3/L4 (SEL).
    """
    # Délégation au module Regime existant (parité v19 stricte)
    res_bnc = calcul_module_bnc(
        profil=profil,
        recettes=profil.recettes_bnc,
        frais_pro=profil.frais_pro_bnc,
    )

    return ResultatStrategieLib(
        code="L1",
        nom="BNC pur (référence)",
        structure="BNC",
        recettes=profil.recettes_bnc,
        frais_pro=profil.frais_pro_bnc,
        benefice_brut=res_bnc.benefice_bnc,
        remuneration_brute=0.0,
        versement_perin=0.0,
        is_societe=0.0,
        dividendes_distribues=0.0,
        cotisations_sel=0.0,
        net_remuneration=0.0,
        net_dividendes=0.0,
        economie_ir_perin=0.0,
        net_bnc=res_bnc.net_apres_impots,
        net_dirigeant_total=res_bnc.net_apres_impots,
        efficacite=res_bnc.net_apres_impots / profil.recettes_bnc if profil.recettes_bnc > 0 else 0.0,
        alertes=[],
    )


def _calcul_strategie_l2(profil: Profil) -> ResultatStrategieLib:
    """
    L2 — BNC + PERIN (plafond individuel).

    Identique à L1, plus une déduction PERIN au plafond individuel
    `max(10 % rev_pro, 4 806€)` plafonné à 8 × PASS.

    Économie d'IR ≈ versement × TMI marginal du foyer.
    """
    # Étape 1 : calcul L1 de référence (BNC pur)
    res_bnc = calcul_module_bnc(
        profil=profil,
        recettes=profil.recettes_bnc,
        frais_pro=profil.frais_pro_bnc,
    )

    # Étape 2 : versement PERIN au plafond individuel du dirigeant
    # En BNC, le revenu pro est le bénéfice net après cotisations.
    revenu_pro = res_bnc.benefice_net_apres_cotis
    plaf_perin = calcul_plafond_perin(
        titulaire="Dirigeant",
        revenu_pro_n_moins_1=revenu_pro,
    )
    versement_perin = plaf_perin.plafond_individuel

    # Étape 3 : économie IR ≈ versement × TMI marginal
    # On recalcule l'IR foyer avec/sans déduction PERIN pour la précision.
    revenu_imposable_foyer = res_bnc.revenu_imposable_foyer
    impots_sans_perin = calcul_ir_foyer(revenu_imposable_foyer, profil)
    revenu_imposable_avec_perin = max(0.0, revenu_imposable_foyer - versement_perin)
    impots_avec_perin = calcul_ir_foyer(revenu_imposable_avec_perin, profil)
    economie_ir = impots_sans_perin["total_impots"] - impots_avec_perin["total_impots"]

    # Net dirigeant = net BNC + économie IR (PERIN est de l'épargne du dirigeant)
    net_total = res_bnc.net_apres_impots + economie_ir

    return ResultatStrategieLib(
        code="L2",
        nom="BNC + PERIN (plafond individuel)",
        structure="BNC",
        recettes=profil.recettes_bnc,
        frais_pro=profil.frais_pro_bnc,
        benefice_brut=res_bnc.benefice_bnc,
        remuneration_brute=0.0,
        versement_perin=versement_perin,
        is_societe=0.0,
        dividendes_distribues=0.0,
        cotisations_sel=0.0,
        net_remuneration=0.0,
        net_dividendes=0.0,
        economie_ir_perin=economie_ir,
        net_bnc=res_bnc.net_apres_impots,
        net_dirigeant_total=net_total,
        efficacite=net_total / profil.recettes_bnc if profil.recettes_bnc > 0 else 0.0,
        alertes=[],
    )


def _calcul_strategie_l3(profil: Profil) -> ResultatStrategieLib:
    """
    L3 — SEL IS (double couche).

    Branche selon profil.forme_sel :
    - SELARL : gérant majoritaire = TNS (cotisations ~45% sur rémunération)
    - SELAS  : président = Assimilé salarié (patronales 42% + salariales 12%)

    Hypothèses v1 (validées) :
    - CA SEL = profil.recettes_bnc (même CA que BNC pour comparabilité)
    - Frais pro SEL ≈ frais_pro_bnc (charges société assimilables aux frais BNC)
    - Rémunération brute SEL = profil.remuneration_sel_souhaitee (input EC)
    - Distribution intégrale du bénéfice après IS (pas de rétention en v1)

    Pour modéliser une rétention de bénéfice : utiliser T4 (TNS Strategy).
    """
    # --- Validation enum (double sécurité, même si Profil l'a déjà vérifié) ---
    if profil.forme_sel not in FORMES_SEL_VALIDES:
        raise ValueError(f"forme_sel invalide : {profil.forme_sel!r}")

    structure = f"SEL-{profil.forme_sel}"

    # --- Étape 1 : bénéfice avant rémunération dirigeant ---
    # CA - frais pro - charges sociales liées à la rémunération
    rem_brute = profil.remuneration_sel_souhaitee

    # Calcul des charges sociales selon forme SEL
    if profil.forme_sel == "SELARL":
        # SELARL : gérant majoritaire TNS — coût rém = brut × (1 + TX_TNS)
        cotisations_sel = rem_brute * TX_TNS
        cout_remuneration = rem_brute + cotisations_sel
    else:  # SELAS
        # SELAS : président Assimilé — coût rém = brut × (1 + TX_PATRONAL)
        # Les cotisations salariales sont prélevées sur le brut, pas en plus
        cotisations_sel = rem_brute * TX_PATRONAL  # côté société
        cout_remuneration = rem_brute + cotisations_sel

    # Bénéfice imposable SEL avant IS
    benefice_avant_is = max(0.0, profil.recettes_bnc - profil.frais_pro_bnc - cout_remuneration)

    # --- Étape 2 : IS société ---
    is_societe = _calcul_is(benefice_avant_is)
    distribuable = max(0.0, benefice_avant_is - is_societe)

    # Distribution intégrale (simplification v1)
    dividendes_bruts = distribuable

    # --- Étape 3 : fiscalité personnelle dirigeant (selon forme SEL) ---
    if profil.forme_sel == "SELARL":
        # SELARL : la rémunération est calculée comme TNS, avec dividendes
        # potentiellement basculant au-delà du seuil 10% capital
        res_tns = calcul_module_tns(
            profil=profil,
            rem_nette_souhaitee=rem_brute,
            frais_reels=0.0,
            div_bruts=dividendes_bruts,
        )
        net_rem = res_tns.net_apres_ir
        net_div = res_tns.net_dividendes

    else:  # SELAS
        # SELAS : la rémunération est calculée comme Salarié, dividendes au PFU
        res_sal = calcul_module_salarie(profil=profil, salaire_brut=rem_brute)
        net_rem = res_sal.net_apres_impots
        # Dividendes au PFU 31,4 % (Assimilé : pas de bascule TNS car non gérant maj)
        net_div = dividendes_bruts * (1 - TX_PFU)

    net_total = net_rem + net_div

    # --- Étape 4 : alerte permanente BNC vs SEL ---
    alertes = [ALERTE_BNC_VS_SEL, MENTION_RETENTION_V2]

    return ResultatStrategieLib(
        code="L3",
        nom=f"SEL IS ({profil.forme_sel})",
        structure=structure,
        recettes=profil.recettes_bnc,
        frais_pro=profil.frais_pro_bnc,
        benefice_brut=benefice_avant_is,
        remuneration_brute=rem_brute,
        versement_perin=0.0,
        is_societe=is_societe,
        dividendes_distribues=dividendes_bruts,
        cotisations_sel=cotisations_sel,
        net_remuneration=net_rem,
        net_dividendes=net_div,
        economie_ir_perin=0.0,
        net_bnc=0.0,
        net_dirigeant_total=net_total,
        efficacite=net_total / profil.recettes_bnc if profil.recettes_bnc > 0 else 0.0,
        alertes=alertes,
    )


def _calcul_strategie_l4(profil: Profil) -> ResultatStrategieLib:
    """
    L4 — SEL + Structuration patrimoniale (cadrage minimal v1).

    DÉLÉGUÉ à L3 sur le plan numérique. La différence est uniquement
    sémantique : L4 signale au cabinet qu'une analyse patrimoniale étendue
    serait pertinente, sans modéliser cette analyse en v1.

    NE MODÉLISE PAS :
    - Holding patrimoniale
    - Démembrement
    - Transmission successorale
    - SPFPL (Société de participations financières de professions libérales)

    Ces leviers feront l'objet d'une étude dédiée en v2 du cadre méthodologique.

    Rationale : afficher un L4 avec un calcul fictif d'optimisation
    patrimoniale serait trompeur. La simulation honnête est de pointer L4
    comme une "piste à étudier" plutôt qu'une stratégie aboutie.
    """
    # Délégation L3 (même calcul, même structure SEL)
    res_l3 = _calcul_strategie_l3(profil)

    # Adapter le résultat : libellé et code différents, alerte structurante ajoutée
    return ResultatStrategieLib(
        code="L4",
        nom="SEL + Structuration patrimoniale (cadrage v1)",
        structure=res_l3.structure,
        recettes=res_l3.recettes,
        frais_pro=res_l3.frais_pro,
        benefice_brut=res_l3.benefice_brut,
        remuneration_brute=res_l3.remuneration_brute,
        versement_perin=res_l3.versement_perin,
        is_societe=res_l3.is_societe,
        dividendes_distribues=res_l3.dividendes_distribues,
        cotisations_sel=res_l3.cotisations_sel,
        net_remuneration=res_l3.net_remuneration,
        net_dividendes=res_l3.net_dividendes,
        economie_ir_perin=res_l3.economie_ir_perin,
        net_bnc=res_l3.net_bnc,
        net_dirigeant_total=res_l3.net_dirigeant_total,
        efficacite=res_l3.efficacite,
        # Alertes L3 (BNC/SEL + rétention v2) + alerte L4 spécifique
        alertes=res_l3.alertes + [ALERTE_L4_V2],
    )


def arbitrage_complet_liberal(profil: Profil) -> ResultatArbitrageLib:
    """
    Arbitrage Libéral consolidé sur les 4 stratégies L1-L4.

    IMPORTANT — terminologie :
    Le résultat consolidé identifie la stratégie au meilleur net dirigeant
    sous le champ 'plus_efficace_fiscalement', JAMAIS 'recommandee'.

    Rationale : le choix BNC/SEL est une décision structurelle (juridique,
    sociale, fiscale, patrimoniale). L'outil indique l'optimum fiscal mais
    ne formule PAS de recommandation. Le cabinet et le CGP doivent toujours
    procéder à une analyse complète.

    L'avertissement BNC/SEL est systématiquement attaché au résultat.

    Args:
        profil: Profil client (avec forme_sel ∈ {"SELARL", "SELAS"})

    Returns:
        ResultatArbitrageLib avec les 4 stratégies + plus_efficace_fiscalement.
    """
    strategies = {
        "L1": _calcul_strategie_l1(profil),
        "L2": _calcul_strategie_l2(profil),
        "L3": _calcul_strategie_l3(profil),
        "L4": _calcul_strategie_l4(profil),
    }

    # Identification de la stratégie au meilleur net (PAS "recommandée")
    plus_efficace = max(strategies, key=lambda c: strategies[c].net_dirigeant_total)

    return ResultatArbitrageLib(
        strategies=strategies,
        plus_efficace_fiscalement=plus_efficace,
        avertissement_bnc_sel=ALERTE_BNC_VS_SEL,
        profil=profil,
    )
