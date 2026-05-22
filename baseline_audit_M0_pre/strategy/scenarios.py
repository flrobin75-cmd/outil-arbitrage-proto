"""
Module Scénarios A vs B - transposition fidèle de l'onglet v19.

Comparateur 2 scénarios simplifié, multi-régimes (Assimilé / TNS / Libéral / Salarié).

ATTENTION : modèle volontairement simplifié vs modules détaillés 7-10.
- Pas de plafonnement QF
- Pas de CEHR ni CDHR
- Abattement 10 % appliqué uniformément (y compris TNS - simplification v19)
- IS calculé sur 100 % des dividendes (pas de soustraction bénéfice - rémunération)
- Forfait social moyen 5 % sur épargne salariale & PER

Date de dernière mise à jour réglementaire : 01/01/2026.
"""

from dataclasses import dataclass
from core.profil import (
    TX_PATRONAL, TX_SALARIAL, TX_TNS, TX_LIB,
    TX_CSG_CRDS_ACT, ASSIETTE_CSG_SAL,
    TX_PFU, TX_IS_REDUIT, TX_IS_NORMAL, IS_PLAF_REDUIT,
    IR_PLAFOND_T1, IR_PLAFOND_T2, IR_PLAFOND_T3, IR_PLAFOND_T4,
    IR_TAUX_T2, IR_TAUX_T3, IR_TAUX_T4, IR_TAUX_T5,
    RDT_CASH, RDT_EPARGNE,
)


@dataclass
class ScenarioInputs:
    """Inputs d'un scénario."""
    libelle: str = "Cas de base"
    situation: str = "Marié / pacsé"
    parts: float = 2.0
    regime_social: str = "Assimilé salarié"
    salaire_brut: float = 100_000
    dividendes_bruts: float = 0
    epargne_salariale_per: float = 0
    peripheriques: float = 0


@dataclass
class ResultatScenario:
    """Résultat de calcul d'un scénario."""
    libelle: str
    net_salaire_apres_cotis: float
    revenu_imposable: float
    ir_barème: float
    net_salaire_apres_ir: float
    net_dividendes: float
    net_epargne: float
    net_peripheriques: float
    total_net: float
    projection_5_ans: list   # 5 valeurs cumulées


@dataclass
class ResultatComparaison:
    """Comparaison des 2 scénarios."""
    scenario_a: ResultatScenario
    scenario_b: ResultatScenario
    ecart_total: float
    ecart_pourcent: float
    gagnant: str         # "A", "B" ou "égalité"
    ecarts_projection: list  # écarts B-A pour chaque année
    date_reglementaire: str = "01/01/2026"


def _ir_barème_pur(revenu_imposable: float, parts: float) -> float:
    """IR au barème sans plafonnement QF (formule C19 v19)."""
    revenu_par_part = revenu_imposable / parts

    if revenu_par_part <= IR_PLAFOND_T1:
        ir_par_part = 0.0
    elif revenu_par_part <= IR_PLAFOND_T2:
        ir_par_part = (revenu_par_part - IR_PLAFOND_T1) * IR_TAUX_T2
    elif revenu_par_part <= IR_PLAFOND_T3:
        ir_par_part = ((IR_PLAFOND_T2 - IR_PLAFOND_T1) * IR_TAUX_T2
                       + (revenu_par_part - IR_PLAFOND_T2) * IR_TAUX_T3)
    elif revenu_par_part <= IR_PLAFOND_T4:
        ir_par_part = ((IR_PLAFOND_T2 - IR_PLAFOND_T1) * IR_TAUX_T2
                       + (IR_PLAFOND_T3 - IR_PLAFOND_T2) * IR_TAUX_T3
                       + (revenu_par_part - IR_PLAFOND_T3) * IR_TAUX_T4)
    else:
        ir_par_part = ((IR_PLAFOND_T2 - IR_PLAFOND_T1) * IR_TAUX_T2
                       + (IR_PLAFOND_T3 - IR_PLAFOND_T2) * IR_TAUX_T3
                       + (IR_PLAFOND_T4 - IR_PLAFOND_T3) * IR_TAUX_T4
                       + (revenu_par_part - IR_PLAFOND_T4) * IR_TAUX_T5)

    return parts * ir_par_part


def _calcul_scenario(s: ScenarioInputs) -> ResultatScenario:
    """Calcule un scénario isolé (formules C17 à E35 v19)."""
    # Ligne 17 - Net salaire après cotisations (selon régime)
    if s.regime_social == "TNS":
        net_apres_cotis = s.salaire_brut * (1 - TX_TNS / (1 + TX_TNS))
    elif s.regime_social == "TNS (libéral)":
        net_apres_cotis = s.salaire_brut * (1 - TX_LIB / (1 + TX_LIB))
    else:
        # Assimilé salarié ou Salarié
        net_apres_cotis = s.salaire_brut * (1 - TX_SALARIAL
                                             - ASSIETTE_CSG_SAL * TX_CSG_CRDS_ACT)

    # Ligne 18 - Revenu imposable approximé (abattement 10 % sans plafond)
    # Note : simplification v19 - même pour TNS (qui n'a pas droit à abattement réel)
    revenu_imposable = net_apres_cotis * 0.9

    # Ligne 19 - IR barème pur
    ir = _ir_barème_pur(revenu_imposable, s.parts)

    # Ligne 20 - Net salaire après IR
    net_salaire_apres_ir = net_apres_cotis - ir

    # Ligne 21 - Net dividendes (IS + PFU)
    if s.dividendes_bruts > 0:
        is_reduit = min(s.dividendes_bruts, IS_PLAF_REDUIT) * TX_IS_REDUIT
        is_normal = max(0, s.dividendes_bruts - IS_PLAF_REDUIT) * TX_IS_NORMAL
        distribuable = s.dividendes_bruts - is_reduit - is_normal
        net_dividendes = distribuable * (1 - TX_PFU)
    else:
        net_dividendes = 0

    # Ligne 22 - Net épargne salariale & PER (forfait social moyen 5 % + CSG/CRDS)
    net_epargne = s.epargne_salariale_per / 1.05 * (1 - TX_CSG_CRDS_ACT)

    # Ligne 23 - Net périphériques (efficacité 95 %)
    net_peripheriques = s.peripheriques * 0.95

    # Total
    total_net = net_salaire_apres_ir + net_dividendes + net_epargne + net_peripheriques

    # Projection 5 ans - capitalisation avec rendement composite
    total_capitalisable = s.epargne_salariale_per + s.peripheriques
    if total_capitalisable > 0:
        fraction_epargne = s.epargne_salariale_per / total_capitalisable
        rendement = fraction_epargne * RDT_EPARGNE + (1 - fraction_epargne) * RDT_CASH
    else:
        rendement = RDT_CASH

    projection = []
    for n in range(1, 6):
        # Capitalisation annuelle composée (formule v19 C31:C35)
        if rendement > 0:
            val = total_net * ((1 + rendement) ** n - 1) / rendement * (1 + rendement)
        else:
            val = total_net * n
        projection.append(val)

    return ResultatScenario(
        libelle=s.libelle,
        net_salaire_apres_cotis=net_apres_cotis,
        revenu_imposable=revenu_imposable,
        ir_barème=ir,
        net_salaire_apres_ir=net_salaire_apres_ir,
        net_dividendes=net_dividendes,
        net_epargne=net_epargne,
        net_peripheriques=net_peripheriques,
        total_net=total_net,
        projection_5_ans=projection,
    )


def calcul_comparaison(scenario_a: ScenarioInputs,
                       scenario_b: ScenarioInputs) -> ResultatComparaison:
    """Compare 2 scénarios côte à côte."""
    res_a = _calcul_scenario(scenario_a)
    res_b = _calcul_scenario(scenario_b)

    ecart_total = res_b.total_net - res_a.total_net
    ecart_pct = (ecart_total / res_a.total_net) if res_a.total_net > 0 else 0

    if abs(ecart_total) < 0.01:
        gagnant = "égalité"
    elif ecart_total > 0:
        gagnant = "B"
    else:
        gagnant = "A"

    ecarts_proj = [b - a for a, b in zip(res_a.projection_5_ans,
                                          res_b.projection_5_ans)]

    return ResultatComparaison(
        scenario_a=res_a,
        scenario_b=res_b,
        ecart_total=ecart_total,
        ecart_pourcent=ecart_pct,
        gagnant=gagnant,
        ecarts_projection=ecarts_proj,
    )


# Avertissement utilisateur (reformulé selon validation)
AVERTISSEMENT_SCENARIOS = (
    "Comparateur 2 scénarios — Outil de cadrage stratégique destiné à comparer "
    "rapidement différents équilibres de rémunération. Pour les calculs "
    "destinés aux obligations fiscales (CEHR, plafonnement QF, régularisations "
    "spécifiques), utiliser les modules de conformité renforcée."
)

# Mention sur le périmètre multi-régimes (mise à jour Phase B.2)
MENTION_REGIMES = (
    "Le comparateur de scénarios est disponible sur les 4 régimes "
    "(Assimilé, TNS, Libéral, Salarié). Chaque régime dispose désormais "
    "de ses propres stratégies d'arbitrage (A/B/C/D, T1-T4, L1-L4)."
)
