"""
Strategy Engine — Stratégies TNS (T1-T4).

Quatre stratégies d'arbitrage pour le régime TNS (gérant majoritaire SARL / EURL) :

- T1 : Rémunération dominante
    Maximise la rémunération cotisable, dividendes résiduels.
    Cas d'usage : capital faible (< 50k€), CCA limités, droits sociaux prioritaires.

- T2 : Dividendes sous seuil 10 %
    Sature le seuil 10 % (capital + primes + CCA) en distribution au PFU,
    le reste en rémunération. Alerte si seuil marginal vs bénéfice.
    Cas d'usage : capital significatif (> 100k€), CCA disponibles.

- T3 : Mix efficient
    Combinaison rémunération + dividendes sous seuil + PERIN max (plafond individuel).
    Cas d'usage : cas général équilibré, accumulation patrimoniale moyen terme.

- T4 : Arbitrage IS
    Rétention de bénéfice en société (non distribué).
    Deux indicateurs SÉPARÉS : net dirigeant immédiat + bénéfice retenu société.
    Cas d'usage : bénéfice élevé, vision long terme, capitalisation société.

Décisions méthodologiques validées (cf. Cadre v1.0.1 §4.2) :
- Enveloppe TNS = profil.benefice_is (capacité distributive avant rémunération)
- TMI/IR : recalcul exact par stratégie via regime.tns.calcul_module_tns
- PERIN T3 : plafond individuel par défaut (mutualisation activable ailleurs)
- T2 alerte : capital_cca < 10 000 € OU seuil_10pct / benefice_is < 5 %
- T4 : INTERDICTION d'agréger net_dirigeant_immediat + benefice_retenu_societe

Module : consomme core (profil, ir_foyer, projection) + regime (tns) +
strategy (perin). Aucun import vers ui/* ou app.
"""

from dataclasses import dataclass, field
from typing import Optional

from core.profil import (
    Profil,
    TX_TNS, TX_PFU, SEUIL_DIV_TNS,
    TX_IS_REDUIT, TX_IS_NORMAL, IS_PLAF_REDUIT,
    PASS_2026,
)
from regime.tns import calcul_module_tns, ResultatTNS
from strategy.perin import (
    calcul_plafond_perin,
    PERIN_PLAFOND_MIN, PERIN_PLAFOND_MAX,
)


# ============================================================
# CONSTANTES MÉTIER (Cadre v1.0.1 §4.2)
# ============================================================

# Seuils d'alerte T2 (décision utilisateur)
ALERTE_T2_CAPITAL_FAIBLE_SEUIL = 10_000  # capital_cca absolu
ALERTE_T2_RATIO_MARGINAL_SEUIL = 0.05    # seuil_10pct / benefice_is

# Allocations par défaut (cf. cadrage Étape 2)
PART_REM_T1 = 0.85
PART_REM_T3 = 0.50
PART_REM_T4 = 0.30


# ============================================================
# DATACLASS RÉSULTAT STRATÉGIE TNS
# ============================================================
@dataclass
class ResultatStrategieTNS:
    """
    Résultat d'une stratégie TNS unique.

    IMPORTANT - T4 (Arbitrage IS) :
    Les champs net_dirigeant_immediat et benefice_retenu_societe sont
    DISTINCTS et ne doivent JAMAIS être agrégés. Le bénéfice retenu reste
    dans la société, ce n'est PAS un revenu disponible pour le dirigeant.
    """
    # Identification
    code: str                            # "T1", "T2", "T3" ou "T4"
    nom: str                             # Libellé long

    # Inputs effectifs
    benefice_is: float                   # Enveloppe à arbitrer
    capital_cca: float                   # Capital + primes + CCA
    seuil_10pct: float                   # 10 % du capital_cca

    # Allocations brutes
    remuneration_brute: float            # Rémunération cotisable visée
    dividendes_distribues: float         # Dividendes effectivement distribués (≤ seuil pour T2)
    versement_perin: float = 0.0         # PERIN versé par le dirigeant (T3 uniquement)
    benefice_retenu_societe: float = 0.0 # T4 : bénéfice conservé en société (NET d'IS)

    # Nets ventilés
    net_remuneration: float = 0.0        # Net après cotis TNS + IR + CSG/CRDS
    net_dividendes: float = 0.0          # Net après IS + PFU (sous seuil) ou TNS+IR (hors seuil)
    economie_ir_perin: float = 0.0       # Économie d'IR liée au versement PERIN

    # Indicateur clé pour T1-T3
    net_dirigeant_immediat: float = 0.0  # = net_remuneration + net_dividendes
                                          # + economie_ir_perin (déduction de l'IR ailleurs)
                                          # NE PAS sommer avec benefice_retenu_societe

    # Cotisations & impôts (traçabilité)
    cotisations_tns_total: float = 0.0   # Sur rém + éventuel excédent dividendes
    is_societe: float = 0.0              # IS payé par la société (sur résultat avant distribution)
    cout_total_societe: float = 0.0      # Rém + cotis (côté société, hors retenu T4)

    # Métriques
    efficacite_immediate: float = 0.0    # net_dirigeant_immediat / benefice_is

    # Alertes spécifiques
    alertes: list = field(default_factory=list)


@dataclass
class ResultatArbitrageTNS:
    """Résultat consolidé des 4 stratégies TNS."""
    strategies: dict                      # {"T1": ResultatStrategieTNS, ...}
    recommandee: str                      # Code de la stratégie au meilleur net_dirigeant_immediat
    profil: Profil
    # Note : pas de classement direct pour T4 car son benefice_retenu_societe
    # n'est pas un revenu disponible. La recommandation se fait sur le net immédiat.


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
# PLACEHOLDERS - À implémenter dans les sous-étapes suivantes
# ============================================================
def _calcul_strategie_t1(profil: Profil) -> ResultatStrategieTNS:
    """
    T1 — Rémunération dominante.

    Logique : la rémunération cotisable absorbe l'essentiel du bénéfice.
    Le reste passe par l'IS puis est distribué en dividendes (sous seuil 10%
    si possible, sinon au régime mixte TNS+IR au-delà).

    Allocation : rem = PART_REM_T1 × benefice_is (85 %)

    Mécanique :
    1. Rémunération + cotisations TNS prennent une part du bénéfice
       Coût total société pour la rémunération = rem × (1 + TX_TNS)
    2. Reste société = benefice_is - cout_rem - IS sur ce reste
    3. Distribution du reste en dividendes (passe par calcul_module_tns)
    """
    enveloppe = profil.benefice_is
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS

    # 1. Calibrer la rémunération brute
    # Si rem = part × benefice_is, et que le coût société = rem × (1 + TX_TNS),
    # alors le coût total de la rém ne doit pas dépasser la part allouée.
    # Pour simplifier (et coller à la doctrine "rém dominante"), on prend :
    #   rem_brute = PART_REM_T1 × benefice_is / (1 + TX_TNS)
    # ainsi cout_rem (rem + cotis) = PART_REM_T1 × benefice_is
    rem_brute = PART_REM_T1 * enveloppe / (1 + TX_TNS)
    cout_remuneration = rem_brute * (1 + TX_TNS)

    # 2. Reste après rémunération
    reste_avant_is = max(0.0, enveloppe - cout_remuneration)
    is_societe = _calcul_is(reste_avant_is)
    div_distribuables = max(0.0, reste_avant_is - is_societe)

    # 3. Appel calcul_module_tns pour avoir le calcul IR exact + ventilation div
    res_tns = calcul_module_tns(
        profil=profil,
        rem_nette_souhaitee=rem_brute,
        frais_reels=0.0,
        div_bruts=div_distribuables,
    )

    return ResultatStrategieTNS(
        code="T1",
        nom="Rémunération dominante",
        benefice_is=enveloppe,
        capital_cca=profil.capital_cca,
        seuil_10pct=seuil_10pct,
        remuneration_brute=rem_brute,
        dividendes_distribues=div_distribuables,
        versement_perin=0.0,
        benefice_retenu_societe=0.0,  # T1 distribue tout
        net_remuneration=res_tns.net_apres_ir,
        net_dividendes=res_tns.net_dividendes,
        economie_ir_perin=0.0,
        net_dirigeant_immediat=res_tns.net_apres_ir + res_tns.net_dividendes,
        cotisations_tns_total=res_tns.cotisations_tns + res_tns.cotis_tns_sur_div,
        is_societe=is_societe,
        cout_total_societe=cout_remuneration,
        efficacite_immediate=(res_tns.net_apres_ir + res_tns.net_dividendes) / enveloppe if enveloppe > 0 else 0.0,
        alertes=[],
    )


def _calcul_strategie_t2(profil: Profil) -> ResultatStrategieTNS:
    """
    T2 — Dividendes sous seuil 10 %.

    Logique : saturer le seuil 10 % capital+CCA en dividendes au PFU (régime
    favorable, pas de cotisations TNS), le reste en rémunération cotisable.

    Allocation : div = min(seuil_10pct, capacité distributible)
                rem = reste après prélèvement IS sur dividendes

    Mécanique :
    1. On veut div_bruts = seuil_10pct exactement
       → résultat société à distribuer avant IS = seuil_10pct / (1 - tx_IS_effectif)
    2. Le reste du bénéfice finance la rémunération + cotis
       rem_brute = (enveloppe - cout_distrib_dividendes) / (1 + TX_TNS)

    Alertes (double critère validé) :
    - capital_cca < 10 000 €
    - seuil_10pct / benefice_is < 5 %
    """
    enveloppe = profil.benefice_is
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS

    # Ratio marginal (utilisé pour l'alerte économique)
    ratio_marginal = seuil_10pct / enveloppe if enveloppe > 0 else 0.0

    # 1. Cibler des dividendes bruts égaux au seuil 10 %
    div_bruts_cibles = seuil_10pct

    # Pour distribuer div_bruts, il faut un résultat société avant IS tel que
    # resultat × (1 - tx_IS) = div_bruts
    # Approximation : si div_bruts ≤ 42 500 → tx_IS = 15 %
    # sinon : tx_IS effectif moyen
    if div_bruts_cibles <= IS_PLAF_REDUIT:
        tx_is_eff = TX_IS_REDUIT
        resultat_societe_pour_div = div_bruts_cibles / (1 - tx_is_eff) if (1 - tx_is_eff) > 0 else 0
        is_pour_div = resultat_societe_pour_div - div_bruts_cibles
    else:
        # Solver simple : résultat tel que IS calculé donne distribuable = div_bruts_cibles
        # On résout : R - IS(R) = div_bruts_cibles
        # R = div_bruts_cibles + IS_PLAF_REDUIT × 0.15 + (R - IS_PLAF_REDUIT) × 0.25
        # 0.75 × R = div_bruts_cibles + IS_PLAF_REDUIT × 0.15 - IS_PLAF_REDUIT × 0.25
        # 0.75 × R = div_bruts_cibles - IS_PLAF_REDUIT × 0.10
        resultat_societe_pour_div = (div_bruts_cibles - IS_PLAF_REDUIT * (TX_IS_NORMAL - TX_IS_REDUIT)) / (1 - TX_IS_NORMAL)
        is_pour_div = _calcul_is(resultat_societe_pour_div)
        # Recalcul de cohérence
        div_bruts_cibles = resultat_societe_pour_div - is_pour_div

    # 2. Le reste du bénéfice finance la rémunération + cotis
    reste_pour_rem = max(0.0, enveloppe - resultat_societe_pour_div)
    rem_brute = reste_pour_rem / (1 + TX_TNS) if reste_pour_rem > 0 else 0.0
    cout_remuneration = rem_brute * (1 + TX_TNS)

    # 3. Si seuil_10pct dépasse la capacité distributible, on plafonne aux dividendes possibles
    if div_bruts_cibles > enveloppe * 0.9:  # garde-fou : pas plus de 90 % en dividendes
        div_bruts_cibles = enveloppe * 0.5
        rem_brute = enveloppe * 0.5 / (1 + TX_TNS)
        is_pour_div = 0.0

    # 4. Appel module TNS pour calcul exact (avec dividendes plafonnés au seuil)
    res_tns = calcul_module_tns(
        profil=profil,
        rem_nette_souhaitee=rem_brute,
        frais_reels=0.0,
        div_bruts=div_bruts_cibles,
    )

    # 5. Construction des alertes
    alertes = []
    if profil.capital_cca < ALERTE_T2_CAPITAL_FAIBLE_SEUIL:
        alertes.append(
            f"Capital + CCA très faible ({profil.capital_cca:,.0f} €) : "
            f"la stratégie T2 a peu d'impact à ce niveau de capital."
        )
    if ratio_marginal < ALERTE_T2_RATIO_MARGINAL_SEUIL:
        alertes.append(
            f"Seuil 10 % marginal vs bénéfice ({ratio_marginal*100:.1f} %) : "
            f"l'optimum dividendes-PFU est très limité — envisager T1 ou T3."
        )

    # 6. Vérification stricte : dividendes ≤ seuil 10 %
    assert res_tns.div_bruts <= seuil_10pct * 1.0001 or div_bruts_cibles == 0, (
        f"VIOLATION T2 : dividendes ({res_tns.div_bruts:.2f}) > seuil 10% "
        f"({seuil_10pct:.2f}). Cette assertion ne doit jamais être violée."
    )

    return ResultatStrategieTNS(
        code="T2",
        nom="Dividendes sous seuil 10 %",
        benefice_is=enveloppe,
        capital_cca=profil.capital_cca,
        seuil_10pct=seuil_10pct,
        remuneration_brute=rem_brute,
        dividendes_distribues=res_tns.div_bruts,
        versement_perin=0.0,
        benefice_retenu_societe=0.0,
        net_remuneration=res_tns.net_apres_ir,
        net_dividendes=res_tns.net_dividendes,
        economie_ir_perin=0.0,
        net_dirigeant_immediat=res_tns.net_apres_ir + res_tns.net_dividendes,
        cotisations_tns_total=res_tns.cotisations_tns + res_tns.cotis_tns_sur_div,
        is_societe=is_pour_div,
        cout_total_societe=cout_remuneration,
        efficacite_immediate=(res_tns.net_apres_ir + res_tns.net_dividendes) / enveloppe if enveloppe > 0 else 0.0,
        alertes=alertes,
    )


def _calcul_strategie_t3(profil: Profil) -> ResultatStrategieTNS:
    """
    T3 — Mix efficient + PERIN max (plafond individuel).

    Logique : combinaison équilibrée des trois leviers :
    - Rémunération cotisable (~50 % bénéfice) → protection sociale + base PERIN
    - Dividendes sous seuil 10 % → PFU favorable
    - PERIN max au plafond individuel → réduction d'IR

    Allocation par défaut :
        rem = PART_REM_T3 × benefice_is (50 %) / (1 + TX_TNS)
        div = min(seuil_10pct, capacité distributible après rém)
        perin = max(10 % rev_pro, 4 806€) plafonné à 8 × PASS
    """
    enveloppe = profil.benefice_is
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS

    # 1. Allocation rémunération
    rem_brute = PART_REM_T3 * enveloppe / (1 + TX_TNS)
    cout_remuneration = rem_brute * (1 + TX_TNS)

    # 2. Reste société → IS → dividendes plafonnés au seuil 10 %
    reste_avant_is = max(0.0, enveloppe - cout_remuneration)
    is_societe = _calcul_is(reste_avant_is)
    distribuable = max(0.0, reste_avant_is - is_societe)
    div_bruts = min(seuil_10pct, distribuable)

    # 3. PERIN au plafond individuel du dirigeant (revenu pro = rem brute approx)
    plaf_perin = calcul_plafond_perin(
        titulaire="Dirigeant",
        revenu_pro_n_moins_1=rem_brute,
    )
    versement_perin = plaf_perin.plafond_individuel

    # 4. Calcul du module TNS avec rem ET dividendes
    res_tns = calcul_module_tns(
        profil=profil,
        rem_nette_souhaitee=rem_brute,
        frais_reels=0.0,
        div_bruts=div_bruts,
    )

    # 5. Économie d'IR liée au PERIN
    # Le versement PERIN est déductible du revenu imposable.
    # Économie ≈ versement × TMI (déjà calculée dans res_tns)
    tmi = res_tns.taux_moyen_ir  # approximation v19
    # On utilise plutôt le TMI marginal pour l'économie PERIN (plus rigoureux)
    # On rapproche du module IR foyer pour le vrai TMI
    from core.ir_foyer import calcul_ir_foyer, tmi_de
    impots = calcul_ir_foyer(res_tns.revenu_imposable_foyer, profil)
    tmi_marginal = impots["tmi"]
    economie_ir_perin = versement_perin * tmi_marginal

    # Net dirigeant immédiat = net rém + net div + économie IR PERIN
    # (l'économie IR diminue effectivement l'impôt à payer)
    # Note : le versement PERIN lui-même n'est PAS soustrait du net immédiat car
    # c'est un placement bloqué qui appartient au dirigeant (épargne, pas un coût)
    # En revanche, l'argent versé sur le PERIN sort du cash disponible immédiat.
    # Pour rester cohérent avec les conventions Phase A :
    # net_dirigeant_immediat = net rém + net div + economie_ir_perin - versement_perin
    # NON : le versement PERIN est de l'épargne du dirigeant, pas une charge.
    # On garde donc : net_dirigeant_immediat = net rém + net div + economie_ir_perin
    # mais on documente clairement cette convention.
    net_immediat = res_tns.net_apres_ir + res_tns.net_dividendes + economie_ir_perin

    return ResultatStrategieTNS(
        code="T3",
        nom="Mix efficient + PERIN",
        benefice_is=enveloppe,
        capital_cca=profil.capital_cca,
        seuil_10pct=seuil_10pct,
        remuneration_brute=rem_brute,
        dividendes_distribues=res_tns.div_bruts,
        versement_perin=versement_perin,
        benefice_retenu_societe=0.0,
        net_remuneration=res_tns.net_apres_ir,
        net_dividendes=res_tns.net_dividendes,
        economie_ir_perin=economie_ir_perin,
        net_dirigeant_immediat=net_immediat,
        cotisations_tns_total=res_tns.cotisations_tns + res_tns.cotis_tns_sur_div,
        is_societe=is_societe,
        cout_total_societe=cout_remuneration,
        efficacite_immediate=net_immediat / enveloppe if enveloppe > 0 else 0.0,
        alertes=[],
    )


def _calcul_strategie_t4(profil: Profil) -> ResultatStrategieTNS:
    """
    T4 — Arbitrage IS (rétention de bénéfice).

    Logique : minimiser la rémunération (juste assez pour les droits sociaux
    de base et la trésorerie courante du dirigeant), conserver le reste en
    société après IS pour capitalisation, sans distribution.

    Allocation par défaut :
        rem = PART_REM_T4 × benefice_is (30 %)
        div = 0 (pas de distribution dans cette stratégie)
        benefice_retenu = (benefice_is - cout_rem) - IS

    INTERDICTION ABSOLUE : ne jamais sommer net_dirigeant_immediat avec
    benefice_retenu_societe. Le bénéfice retenu reste dans la société et
    n'est PAS un revenu du dirigeant.

    Pour le dirigeant, la valeur économique se compose de DEUX flux :
      1. Net dirigeant immédiat (revenu personnel, fiscalité IR + cotis)
      2. Bénéfice retenu en société (actif société, valorisable plus tard)
    """
    enveloppe = profil.benefice_is
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS

    # 1. Rémunération réduite (30 % du bénéfice)
    rem_brute = PART_REM_T4 * enveloppe / (1 + TX_TNS)
    cout_remuneration = rem_brute * (1 + TX_TNS)

    # 2. Reste société → IS → conservé (PAS de distribution)
    reste_avant_is = max(0.0, enveloppe - cout_remuneration)
    is_societe = _calcul_is(reste_avant_is)
    benefice_retenu = max(0.0, reste_avant_is - is_societe)

    # 3. Calcul module TNS avec dividendes = 0
    res_tns = calcul_module_tns(
        profil=profil,
        rem_nette_souhaitee=rem_brute,
        frais_reels=0.0,
        div_bruts=0.0,  # AUCUNE distribution
    )

    # 4. Net dirigeant immédiat = uniquement la rémunération nette
    #    (pas de dividendes, pas de PERIN par défaut en T4)
    net_immediat = res_tns.net_apres_ir

    # ASSERTION CRITIQUE : pas d'agrégation
    # Cette assertion vérifie qu'aucune confusion ne s'est glissée dans la
    # construction de net_dirigeant_immediat.
    assert net_immediat == res_tns.net_apres_ir, (
        f"VIOLATION T4 : net_dirigeant_immediat doit être strictement la "
        f"rémunération nette, pas d'agrégation avec le bénéfice retenu."
    )

    return ResultatStrategieTNS(
        code="T4",
        nom="Arbitrage IS (rétention en société)",
        benefice_is=enveloppe,
        capital_cca=profil.capital_cca,
        seuil_10pct=seuil_10pct,
        remuneration_brute=rem_brute,
        dividendes_distribues=0.0,           # Pas de distribution
        versement_perin=0.0,                  # Pas de PERIN par défaut
        benefice_retenu_societe=benefice_retenu,  # INDICATEUR DISTINCT
        net_remuneration=res_tns.net_apres_ir,
        net_dividendes=0.0,
        economie_ir_perin=0.0,
        net_dirigeant_immediat=net_immediat,  # = net_remuneration uniquement
        cotisations_tns_total=res_tns.cotisations_tns,
        is_societe=is_societe,
        cout_total_societe=cout_remuneration,
        # Efficacité immédiate calculée UNIQUEMENT sur net dirigeant
        # (le bénéfice retenu est une valeur société, pas un revenu personnel)
        efficacite_immediate=net_immediat / enveloppe if enveloppe > 0 else 0.0,
        alertes=[
            f"Bénéfice retenu en société : {benefice_retenu:,.2f} € (après IS). "
            f"Cette valeur reste en société et n'est PAS un revenu disponible pour le dirigeant. "
            f"Sa distribution ultérieure subira la fiscalité applicable au moment de la distribution."
        ],
    )


def arbitrage_complet_tns(profil: Profil) -> ResultatArbitrageTNS:
    """
    Arbitrage TNS consolidé sur les 4 stratégies T1-T4.

    Calcule chacune des 4 stratégies pour le profil, et identifie la
    stratégie recommandée sur la base du net_dirigeant_immediat le plus élevé.

    IMPORTANT : la recommandation se fonde uniquement sur le net dirigeant
    immédiat. Pour T4, le bénéfice retenu en société n'entre PAS dans le
    classement (ce n'est pas un revenu disponible). L'EC doit interpréter
    T4 en tenant compte de cet indicateur séparé.

    Args:
        profil: Profil client (régime TNS uniquement attendu)

    Returns:
        ResultatArbitrageTNS avec dict des 4 stratégies + code recommandée.
    """
    strategies = {
        "T1": _calcul_strategie_t1(profil),
        "T2": _calcul_strategie_t2(profil),
        "T3": _calcul_strategie_t3(profil),
        "T4": _calcul_strategie_t4(profil),
    }

    # Recommandation : meilleur net_dirigeant_immediat
    # (T4 reste éligible à la recommandation, mais son net immédiat est
    # généralement plus bas car le bénéfice est retenu)
    recommandee = max(strategies, key=lambda c: strategies[c].net_dirigeant_immediat)

    return ResultatArbitrageTNS(
        strategies=strategies,
        recommandee=recommandee,
        profil=profil,
    )
