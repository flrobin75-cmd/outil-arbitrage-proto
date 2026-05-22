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

MODE_AUDIT (G3e-scenarios, spec 1.1.0) :
- `_ir_barème_pur` / `_calcul_scenario` / `calcul_comparaison` acceptent un
  paramètre opt-in `audit: TraceAudit | None`. Codes émis : `SCEN_*`
  (namespace dédié, distinct de `SYNTH_*` G3e-synthese et des comparateurs G3d).
- Module **100% autonome** : aucun import depuis un module instrumenté.
  `_ir_barème_pur` et `_calcul_scenario` produisent des traces plates.
  `calcul_comparaison` attache 2 sous-traces internes nommées `scenario_a`
  et `scenario_b` (pure composition au sein du module).
- Discipline non-prescriptive renforcée : le champ Python `gagnant`
  ("A" / "B" / "égalité") est préservé tel quel dans le résultat pour
  rétrocompat. Côté trace MODE_AUDIT, ce résultat est exposé sous
  `SCEN_SCENARIO_NET_LE_PLUS_ELEVE` (terminologie factuelle), avec
  `hypotheses["champ_source"] = "gagnant"` pour traçabilité.
- 2 textes structurants (`AVERTISSEMENT_SCENARIOS`, `MENTION_REGIMES`)
  préservés intégralement en `hypotheses`, jamais en label/notes.
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
from core.audit import TraceAudit


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


def _ir_barème_pur(revenu_imposable: float, parts: float,
                   *,
                   audit: TraceAudit | None = None) -> float:
    """IR au barème sans plafonnement QF (formule C19 v19).

    Args:
        revenu_imposable: revenu imposable du foyer
        parts: nombre de parts fiscales
        audit: Trace d'audit optionnelle (G3e-scenarios.1). Side channel.
            Codes émis : `SCEN_IR_*`. Aucune sous-trace.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SCEN_IR_" + suffixe, label, valeur, **kw)

    revenu_par_part = revenu_imposable / parts

    _log("REVENU_PAR_PART",
         "Revenu imposable par part (input / parts)",
         revenu_par_part, unite="EUR",
         doctrine_refs=(),
         hypotheses={"revenu_imposable_input": revenu_imposable,
                     "parts_input": parts})

    # Détermination de la tranche atteinte
    if revenu_par_part <= IR_PLAFOND_T1:
        ir_par_part = 0.0
        tranche_atteinte = "T1"
    elif revenu_par_part <= IR_PLAFOND_T2:
        ir_par_part = (revenu_par_part - IR_PLAFOND_T1) * IR_TAUX_T2
        tranche_atteinte = "T2"
    elif revenu_par_part <= IR_PLAFOND_T3:
        ir_par_part = ((IR_PLAFOND_T2 - IR_PLAFOND_T1) * IR_TAUX_T2
                       + (revenu_par_part - IR_PLAFOND_T2) * IR_TAUX_T3)
        tranche_atteinte = "T3"
    elif revenu_par_part <= IR_PLAFOND_T4:
        ir_par_part = ((IR_PLAFOND_T2 - IR_PLAFOND_T1) * IR_TAUX_T2
                       + (IR_PLAFOND_T3 - IR_PLAFOND_T2) * IR_TAUX_T3
                       + (revenu_par_part - IR_PLAFOND_T3) * IR_TAUX_T4)
        tranche_atteinte = "T4"
    else:
        ir_par_part = ((IR_PLAFOND_T2 - IR_PLAFOND_T1) * IR_TAUX_T2
                       + (IR_PLAFOND_T3 - IR_PLAFOND_T2) * IR_TAUX_T3
                       + (IR_PLAFOND_T4 - IR_PLAFOND_T3) * IR_TAUX_T4
                       + (revenu_par_part - IR_PLAFOND_T4) * IR_TAUX_T5)
        tranche_atteinte = "T5"

    ir_total = parts * ir_par_part

    _log("TRANCHE_ATTEINTE",
         "Tranche du barème IR atteinte par le revenu par part",
         tranche_atteinte, unite="",
         doctrine_refs=("IR_PLAFOND_T1", "IR_PLAFOND_T2",
                        "IR_PLAFOND_T3", "IR_PLAFOND_T4"),
         hypotheses={"IR_PLAFOND_T1": IR_PLAFOND_T1,
                     "IR_PLAFOND_T2": IR_PLAFOND_T2,
                     "IR_PLAFOND_T3": IR_PLAFOND_T3,
                     "IR_PLAFOND_T4": IR_PLAFOND_T4})
    _log("IR_PAR_PART",
         "IR au barème pour une part (formule simplifiée v19, sans plafonnement QF)",
         ir_par_part, unite="EUR",
         doctrine_refs=("IR_TAUX_T2", "IR_TAUX_T3",
                        "IR_TAUX_T4", "IR_TAUX_T5"),
         hypotheses={"IR_TAUX_T2": IR_TAUX_T2,
                     "IR_TAUX_T3": IR_TAUX_T3,
                     "IR_TAUX_T4": IR_TAUX_T4,
                     "IR_TAUX_T5": IR_TAUX_T5,
                     "convention_v19": "Pas de plafonnement QF appliqué"})
    _log("IR_TOTAL",
         "IR total = parts × ir_par_part",
         ir_total, unite="EUR",
         hypotheses={"formule": "parts × ir_par_part"})

    return ir_total


def _calcul_scenario(s: ScenarioInputs,
                     *,
                     audit: TraceAudit | None = None) -> ResultatScenario:
    """Calcule un scénario isolé (formules C17 à E35 v19).

    Args:
        s: Inputs du scénario.
        audit: Trace d'audit optionnelle (G3e-scenarios.1). Side channel.
            Codes émis : `SCEN_*` (à plat). Si fourni, attache la
            sous-trace `ir_barème` pour le calcul IR.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SCEN_" + suffixe, label, valeur, **kw)

    # Ligne 17 - Net salaire après cotisations (selon régime)
    if s.regime_social == "TNS":
        net_apres_cotis = s.salaire_brut * (1 - TX_TNS / (1 + TX_TNS))
        formule_cotis = "salaire × (1 - TX_TNS / (1 + TX_TNS))"
    elif s.regime_social == "TNS (libéral)":
        net_apres_cotis = s.salaire_brut * (1 - TX_LIB / (1 + TX_LIB))
        formule_cotis = "salaire × (1 - TX_LIB / (1 + TX_LIB))"
    else:
        # Assimilé salarié ou Salarié
        net_apres_cotis = s.salaire_brut * (1 - TX_SALARIAL
                                             - ASSIETTE_CSG_SAL * TX_CSG_CRDS_ACT)
        formule_cotis = "salaire × (1 - TX_SALARIAL - ASSIETTE_CSG_SAL × TX_CSG_CRDS_ACT)"

    _log("LIBELLE",
         "Libellé du scénario (input)",
         s.libelle, unite="",
         hypotheses={"regime_social_scenario": s.regime_social,
                     "situation_scenario": s.situation,
                     "parts_scenario": s.parts})
    _log("NET_SALAIRE_APRES_COTIS",
         "Net salaire après cotisations selon régime",
         net_apres_cotis, unite="EUR",
         doctrine_refs=("TX_TNS", "TX_LIB", "TX_SALARIAL",
                        "ASSIETTE_CSG_SAL", "TX_CSG_CRDS_ACT"),
         hypotheses={"regime_applique": s.regime_social,
                     "salaire_brut_input": s.salaire_brut,
                     "formule_appliquee": formule_cotis})

    # Ligne 18 - Revenu imposable approximé (abattement 10 % sans plafond)
    revenu_imposable = net_apres_cotis * 0.9

    _log("REVENU_IMPOSABLE",
         "Revenu imposable (net après cotis × 0.9, abattement 10% uniforme v19)",
         revenu_imposable, unite="EUR",
         hypotheses={"convention_v19": "Abattement 10% uniforme (y compris TNS)",
                     "ratio_abattement_applique": 0.9})

    # Ligne 19 - IR barème pur (avec sous-trace)
    if audit is not None:
        st_ir = TraceAudit(
            regime="IR barème (scénario)",
            profil_resume=f"revenu={revenu_imposable:.0f}, parts={s.parts}",
        )
        ir = _ir_barème_pur(revenu_imposable, s.parts, audit=st_ir)
        audit.attacher_sous_trace("ir_barème", st_ir)
    else:
        ir = _ir_barème_pur(revenu_imposable, s.parts)

    _log("IR_BAREME_RECUPERE",
         "IR au barème (résultat de la sous-trace ir_barème)",
         ir, unite="EUR",
         notes="Détails du calcul dans la sous-trace 'ir_barème'")

    # Ligne 20 - Net salaire après IR
    net_salaire_apres_ir = net_apres_cotis - ir

    _log("NET_SALAIRE_APRES_IR",
         "Net salaire après IR (net cotis − IR)",
         net_salaire_apres_ir, unite="EUR")

    # Ligne 21 - Net dividendes (IS + PFU)
    if s.dividendes_bruts > 0:
        is_reduit = min(s.dividendes_bruts, IS_PLAF_REDUIT) * TX_IS_REDUIT
        is_normal = max(0, s.dividendes_bruts - IS_PLAF_REDUIT) * TX_IS_NORMAL
        distribuable = s.dividendes_bruts - is_reduit - is_normal
        net_dividendes = distribuable * (1 - TX_PFU)
    else:
        net_dividendes = 0

    _log("NET_DIVIDENDES",
         "Net dividendes (IS + PFU appliqués sur dividendes bruts)",
         net_dividendes, unite="EUR",
         doctrine_refs=("TX_IS_REDUIT", "TX_IS_NORMAL", "IS_PLAF_REDUIT", "TX_PFU"),
         hypotheses={"dividendes_bruts_input": s.dividendes_bruts,
                     "TX_IS_REDUIT": TX_IS_REDUIT,
                     "TX_IS_NORMAL": TX_IS_NORMAL,
                     "IS_PLAF_REDUIT": IS_PLAF_REDUIT,
                     "TX_PFU": TX_PFU,
                     "convention_v19": "IS calculé sur 100% des dividendes (pas de soustraction)"})

    # Ligne 22 - Net épargne salariale & PER
    net_epargne = s.epargne_salariale_per / 1.05 * (1 - TX_CSG_CRDS_ACT)

    _log("NET_EPARGNE_SALARIALE",
         "Net épargne salariale et PER (forfait social moyen 5% + CSG/CRDS)",
         net_epargne, unite="EUR",
         doctrine_refs=("TX_CSG_CRDS_ACT",),
         hypotheses={"epargne_input": s.epargne_salariale_per,
                     "forfait_social_moyen_applique": 0.05,
                     "TX_CSG_CRDS_ACT": TX_CSG_CRDS_ACT})

    # Ligne 23 - Net périphériques
    net_peripheriques = s.peripheriques * 0.95

    _log("NET_PERIPHERIQUES",
         "Net périphériques (efficacité 95%)",
         net_peripheriques, unite="EUR",
         hypotheses={"peripheriques_input": s.peripheriques,
                     "ratio_efficacite": 0.95})

    # Total
    total_net = net_salaire_apres_ir + net_dividendes + net_epargne + net_peripheriques

    _log("TOTAL_NET",
         "Somme des 4 composantes nettes (salaire + div + épargne + périph)",
         total_net, unite="EUR")

    # Projection 5 ans - capitalisation avec rendement composite
    total_capitalisable = s.epargne_salariale_per + s.peripheriques
    if total_capitalisable > 0:
        fraction_epargne = s.epargne_salariale_per / total_capitalisable
        rendement = fraction_epargne * RDT_EPARGNE + (1 - fraction_epargne) * RDT_CASH
    else:
        rendement = RDT_CASH

    _log("RENDEMENT_COMPOSITE",
         "Rendement composite pondéré (épargne × RDT_EPARGNE + cash × RDT_CASH)",
         rendement, unite="ratio",
         doctrine_refs=("RDT_EPARGNE", "RDT_CASH"),
         hypotheses={"RDT_EPARGNE": RDT_EPARGNE,
                     "RDT_CASH": RDT_CASH,
                     "total_capitalisable": total_capitalisable,
                     "fraction_epargne_calculee":
                         s.epargne_salariale_per / total_capitalisable
                         if total_capitalisable > 0 else None})

    projection = []
    for n in range(1, 6):
        if rendement > 0:
            val = total_net * ((1 + rendement) ** n - 1) / rendement * (1 + rendement)
        else:
            val = total_net * n
        projection.append(val)

    _log("PROJECTION_5_ANS_NB_VALEURS",
         "Nombre de valeurs de projection calculées",
         float(len(projection)), unite="count",
         hypotheses={"valeurs_cumulees_5ans": projection,
                     "formule_capitalisation":
                         "total_net × ((1+r)^n − 1) / r × (1+r) si r > 0, "
                         "sinon total_net × n"})

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
                       scenario_b: ScenarioInputs,
                       *,
                       audit: TraceAudit | None = None) -> ResultatComparaison:
    """Compare 2 scénarios côte à côte.

    Args:
        scenario_a: Inputs du scénario A.
        scenario_b: Inputs du scénario B.
        audit: Trace d'audit optionnelle (G3e-scenarios.1). Codes émis :
            `SCEN_*` méta (ECART_NET_TOTAL, ECART_POURCENT,
            SCENARIO_NET_LE_PLUS_ELEVE, ECARTS_PROJECTION_NB,
            AVERTISSEMENT_SCENARIOS, MENTION_REGIMES).
            Attache 2 sous-traces nommées `scenario_a` et `scenario_b`
            (composition interne au module).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("SCEN_" + suffixe, label, valeur, **kw)

    # Appel des 2 scénarios avec sous-traces composées
    if audit is not None:
        st_a = TraceAudit(regime="Scénario A",
                          profil_resume=f"libelle={scenario_a.libelle}")
        res_a = _calcul_scenario(scenario_a, audit=st_a)
        audit.attacher_sous_trace("scenario_a", st_a)

        st_b = TraceAudit(regime="Scénario B",
                          profil_resume=f"libelle={scenario_b.libelle}")
        res_b = _calcul_scenario(scenario_b, audit=st_b)
        audit.attacher_sous_trace("scenario_b", st_b)
    else:
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

    # --- Trace méta SCEN_* ---
    _log("ECART_NET_TOTAL",
         "Écart total_net B − A (indicateur factuel)",
         ecart_total, unite="EUR",
         hypotheses={"total_net_a": res_a.total_net,
                     "total_net_b": res_b.total_net,
                     "formule": "B.total_net - A.total_net"})
    _log("ECART_POURCENT",
         "Écart relatif (ecart_total / A.total_net)",
         ecart_pct, unite="ratio",
         hypotheses={"formule": "ecart_total / a.total_net si > 0, sinon 0",
                     "convention_division_zero":
                         "0 par défaut si A.total_net == 0"})
    _log("CRITERE_CLASSEMENT",
         "Critère de classement appliqué",
         "max(total_net)", unite="",
         notes="Classement mécanique sur le total_net. "
               "Ne reflète pas un avis sur le choix de scénario.")
    _log("SCENARIO_NET_LE_PLUS_ELEVE",
         "Scénario au plus haut total_net (indicateur factuel)",
         gagnant, unite="",
         parent_id="SCEN_CRITERE_CLASSEMENT",
         hypotheses={"champ_source": "gagnant",
                     "valeurs_possibles": ["A", "B", "égalité"],
                     "seuil_egalite": 0.01,
                     "ecart_total_calcule": ecart_total},
         notes="Terminologie MODE_AUDIT factuelle. Champ Python "
               "préservé tel quel pour rétrocompat.")
    _log("ECARTS_PROJECTION_NB",
         "Nombre d'écarts de projection calculés (B − A pour chaque année)",
         float(len(ecarts_proj)), unite="count",
         hypotheses={"ecarts_par_annee": ecarts_proj,
                     "annees": list(range(1, 6))})

    # Textes structurants en hypotheses (jamais en label/notes)
    _log("AVERTISSEMENT_SCENARIOS",
         "Texte d'avertissement structurant (1 texte intégral)",
         1.0, unite="count",
         hypotheses={"AVERTISSEMENT_SCENARIOS": AVERTISSEMENT_SCENARIOS},
         notes="Wording métier intégral en hypotheses — pattern G3b/c/d")
    _log("MENTION_REGIMES",
         "Texte de mention multi-régimes structurant (1 texte intégral)",
         1.0, unite="count",
         hypotheses={"MENTION_REGIMES": MENTION_REGIMES},
         notes="Wording métier intégral en hypotheses — pattern G3b/c/d")

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
