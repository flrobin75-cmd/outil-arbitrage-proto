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

MODE_AUDIT (G3c, spec 1.1.0) :
- `_calcul_strategie_l1/l2/l3/l4()` acceptent un paramètre opt-in
  `audit: TraceAudit | None`. Codes émis : `STRAT_LIB_L<X>_*`.
- `arbitrage_complet_liberal()` accepte le même paramètre. Codes émis :
  `STRAT_LIB_*` (niveau méta). Attache des sous-traces nommées
  `strategie_L<X>` pour les 4 stratégies. Chaque stratégie attache une
  sous-trace régime nommée selon le module amont :
    * L1, L2 → `module_bnc` (codes `LIB_BNC_*`)
    * L3, L4 SELARL → `module_tns` (codes `TNS_*`)
    * L3, L4 SELAS → `module_salarie` (codes `SAL_*`)
  L4 attache aussi une sous-trace `strategie_l3_deleguee` (sa propre
  TraceAudit L3 fraîche) pour refléter la délégation sémantique sans
  duplication d'étapes.

Conventions appliquées :
- Vocabulaire factuel : `STRAT_LIB_PLUS_EFFICACE_FISCALEMENT` (terminologie
  doctrine module Libéral §36-38, distincte de `STRAT_TNS_RETENU` /
  `STRAT_ASSIM_RETENU` employés ailleurs).
- Les labels et notes respectent les restrictions terminologiques définies
  dans TERMINOLOGY.md §2. Aucun wording prescriptif.
- Les 3 alertes structurantes (`ALERTE_BNC_VS_SEL`, `ALERTE_L4_V2`,
  `MENTION_RETENTION_V2`) sont placées en `hypotheses` (champ dict, non
  scanné par le test non-prescriptif), pas dans `label` ni `notes`.
- Le critère de sélection est explicité comme hypothèse (`critere`),
  le résultat dérive mécaniquement.
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
from core.audit import TraceAudit
from core.ir_foyer import calcul_ir_foyer
from regime.liberal import calcul_module_bnc, calcul_module_sel, ResultatBNC, ResultatSEL
from regime.tns import calcul_module_tns
from regime.salarie import calcul_module_salarie
from core.profil import PLAFOND_ABAT_10PCT_SAL  # G2a : import direct depuis la doctrine
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
def _calcul_strategie_l1(profil: Profil,
                         *,
                         audit: TraceAudit | None = None) -> ResultatStrategieLib:
    """
    L1 — BNC pur (référence sur même CA).

    Exercice individuel : recettes BNC moins frais professionnels donne
    le bénéfice imposable, taxé directement au barème IR avec cotisations
    TNS Libéral (CARMF, CIPAV, etc.) à ~45%.

    C'est la stratégie de référence pour la comparaison avec L2 (PERIN)
    et avec L3/L4 (SEL).

    Args:
        profil: Profil client (BNC).
        audit: Trace d'audit optionnelle (MODE_AUDIT G3c). Side channel.
            Codes émis : `STRAT_LIB_L1_*`. Attache une sous-trace
            `module_bnc` pour le calcul régime amont.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("STRAT_LIB_L1_" + suffixe, label, valeur, **kw)

    _log("RECETTES_BNC", "Recettes BNC (input)",
         profil.recettes_bnc, unite="EUR",
         hypotheses={"strategie_code": "L1",
                     "strategie_nom": "BNC pur (référence)"})
    _log("FRAIS_PRO_BNC", "Frais professionnels BNC (input)",
         profil.frais_pro_bnc, unite="EUR")
    _log("STRUCTURE", "Structure juridique applicable",
         "BNC", unite="",
         notes="Exercice individuel — référence pour comparaisons L2/L3/L4")

    # Délégation au module Regime existant (parité v19 stricte)
    if audit is not None:
        sous_trace_bnc = TraceAudit(
            regime="Libéral BNC (appel depuis stratégie L1)",
            profil_resume=f"recettes={profil.recettes_bnc:.0f}, "
                          f"frais_pro={profil.frais_pro_bnc:.0f}",
        )
        res_bnc = calcul_module_bnc(
            profil=profil,
            recettes=profil.recettes_bnc,
            frais_pro=profil.frais_pro_bnc,
            audit=sous_trace_bnc,
        )
        audit.attacher_sous_trace("module_bnc", sous_trace_bnc)
    else:
        res_bnc = calcul_module_bnc(
            profil=profil,
            recettes=profil.recettes_bnc,
            frais_pro=profil.frais_pro_bnc,
        )

    _log("BENEFICE_BRUT_BNC",
         "Bénéfice BNC (recettes − frais pro)",
         res_bnc.benefice_bnc, unite="EUR",
         notes="Détails dans sous-trace 'module_bnc'")
    _log("NET_BNC",
         "Net BNC après cotisations + IR (depuis module BNC)",
         res_bnc.net_apres_impots, unite="EUR",
         notes="Détails dans sous-trace 'module_bnc'")

    net_total = res_bnc.net_apres_impots
    efficacite = net_total / profil.recettes_bnc if profil.recettes_bnc > 0 else 0.0

    _log("NET_DIRIGEANT_TOTAL",
         "Net dirigeant total (= net BNC pour L1)",
         net_total, unite="EUR",
         hypotheses={"composantes": "net_apres_impots (BNC uniquement)"})
    _log("EFFICACITE",
         "Ratio net dirigeant / recettes",
         efficacite, unite="ratio")

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
        net_dirigeant_total=net_total,
        efficacite=efficacite,
        alertes=[],
    )


def _calcul_strategie_l2(profil: Profil,
                         *,
                         audit: TraceAudit | None = None) -> ResultatStrategieLib:
    """
    L2 — BNC + PERIN (plafond individuel).

    Identique à L1, plus une déduction PERIN au plafond individuel
    `max(10 % rev_pro, 4 806€)` plafonné à 8 × PASS.

    Économie d'IR calculée par recalcul exact (avec et sans déduction
    PERIN, delta = économie réelle) — méthodologie plus précise que
    l'approximation TMI marginal utilisée en G3b TNS T3.

    Args:
        profil: Profil client (BNC).
        audit: Trace d'audit optionnelle (G3c). Codes émis : `STRAT_LIB_L2_*`.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("STRAT_LIB_L2_" + suffixe, label, valeur, **kw)

    _log("RECETTES_BNC", "Recettes BNC (input)",
         profil.recettes_bnc, unite="EUR",
         hypotheses={"strategie_code": "L2",
                     "strategie_nom": "BNC + PERIN (plafond individuel)"})
    _log("FRAIS_PRO_BNC", "Frais professionnels BNC (input)",
         profil.frais_pro_bnc, unite="EUR")
    _log("STRUCTURE", "Structure juridique applicable",
         "BNC", unite="",
         notes="Identique L1 + déduction PERIN")

    # Étape 1 : calcul L1 de référence (BNC pur) avec sous-trace régime
    if audit is not None:
        sous_trace_bnc = TraceAudit(
            regime="Libéral BNC (appel depuis stratégie L2)",
            profil_resume=f"recettes={profil.recettes_bnc:.0f}, "
                          f"frais_pro={profil.frais_pro_bnc:.0f}",
        )
        res_bnc = calcul_module_bnc(
            profil=profil,
            recettes=profil.recettes_bnc,
            frais_pro=profil.frais_pro_bnc,
            audit=sous_trace_bnc,
        )
        audit.attacher_sous_trace("module_bnc", sous_trace_bnc)
    else:
        res_bnc = calcul_module_bnc(
            profil=profil,
            recettes=profil.recettes_bnc,
            frais_pro=profil.frais_pro_bnc,
        )

    # Étape 2 : versement PERIN au plafond individuel du dirigeant
    revenu_pro = res_bnc.benefice_net_apres_cotis
    plaf_perin = calcul_plafond_perin(
        titulaire="Dirigeant",
        revenu_pro_n_moins_1=revenu_pro,
    )
    versement_perin = plaf_perin.plafond_individuel

    _log("REVENU_PRO_BASE_PERIN",
         "Revenu pro de référence pour calcul plafond PERIN (= bénéfice net BNC après cotis)",
         revenu_pro, unite="EUR")
    _log("VERSEMENT_PERIN",
         "Versement PERIN retenu (= plafond individuel par défaut L2)",
         versement_perin, unite="EUR",
         doctrine_refs=("TX_LIB",),
         hypotheses={"titulaire": "Dirigeant",
                     "type_plafond": "individuel"},
         notes="Convention L2 — versement par défaut au plafond individuel")

    # Étape 3 : économie IR par recalcul exact (méthodologie plus rigoureuse que TMI)
    revenu_imposable_foyer = res_bnc.revenu_imposable_foyer
    impots_sans_perin = calcul_ir_foyer(revenu_imposable_foyer, profil)
    revenu_imposable_avec_perin = max(0.0, revenu_imposable_foyer - versement_perin)
    impots_avec_perin = calcul_ir_foyer(revenu_imposable_avec_perin, profil)
    economie_ir = impots_sans_perin["total_impots"] - impots_avec_perin["total_impots"]

    _log("IMPOTS_FOYER_SANS_PERIN",
         "Impôts foyer sans déduction PERIN (référence)",
         impots_sans_perin["total_impots"], unite="EUR",
         doctrine_refs=("IR_PLAFOND_T1", "IR_PLAFOND_T2",
                        "IR_PLAFOND_T3", "IR_PLAFOND_T4"),
         hypotheses={"revenu_imposable_foyer": revenu_imposable_foyer})
    _log("IMPOTS_FOYER_AVEC_PERIN",
         "Impôts foyer avec déduction PERIN",
         impots_avec_perin["total_impots"], unite="EUR",
         hypotheses={"revenu_imposable_avec_perin": revenu_imposable_avec_perin,
                     "versement_perin_deduit": versement_perin})
    _log("ECONOMIE_IR_PERIN",
         "Économie d'IR effective (recalcul exact, méthode Libéral)",
         economie_ir, unite="EUR",
         hypotheses={"methode": "recalcul_exact",
                     "comparaison_methode": "Différence des total_impots avec et sans PERIN"},
         notes="Méthodologie plus rigoureuse que TMI marginal utilisée en TNS T3")

    # Net dirigeant = net BNC + économie IR (PERIN est de l'épargne du dirigeant)
    net_total = res_bnc.net_apres_impots + economie_ir
    efficacite = net_total / profil.recettes_bnc if profil.recettes_bnc > 0 else 0.0

    _log("NET_BNC",
         "Net BNC après cotisations + IR (depuis module BNC)",
         res_bnc.net_apres_impots, unite="EUR",
         notes="Détails dans sous-trace 'module_bnc'")
    _log("NET_DIRIGEANT_TOTAL",
         "Net dirigeant total (= net BNC + économie IR PERIN)",
         net_total, unite="EUR",
         hypotheses={"composantes": "net_bnc + economie_ir_perin",
                     "note_perin": "Le versement PERIN lui-même n'est pas soustrait — "
                                   "c'est une épargne du dirigeant, pas une charge"})
    _log("EFFICACITE",
         "Ratio net dirigeant / recettes",
         efficacite, unite="ratio")

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
        efficacite=efficacite,
        alertes=[],
    )


def _calcul_strategie_l3(profil: Profil,
                         *,
                         audit: TraceAudit | None = None) -> ResultatStrategieLib:
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

    Args:
        profil: Profil client (BNC, avec forme_sel ∈ {"SELARL", "SELAS"}).
        audit: Trace d'audit optionnelle (G3c). Codes émis : `STRAT_LIB_L3_*`.
            Attache une sous-trace régime dont le nom dépend de forme_sel :
            * SELARL → `module_tns` (codes `TNS_*`)
            * SELAS  → `module_salarie` (codes `SAL_*`)
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("STRAT_LIB_L3_" + suffixe, label, valeur, **kw)

    # --- Validation enum (double sécurité, même si Profil l'a déjà vérifié) ---
    if profil.forme_sel not in FORMES_SEL_VALIDES:
        raise ValueError(f"forme_sel invalide : {profil.forme_sel!r}")

    structure = f"SEL-{profil.forme_sel}"

    _log("RECETTES_BNC",
         "CA de référence (= recettes BNC pour comparabilité)",
         profil.recettes_bnc, unite="EUR",
         hypotheses={"strategie_code": "L3",
                     "strategie_nom": f"SEL IS ({profil.forme_sel})"})
    _log("FRAIS_PRO_SEL",
         "Frais pro SEL (≈ frais_pro_bnc par convention v1)",
         profil.frais_pro_bnc, unite="EUR")
    _log("STRUCTURE", "Structure juridique applicable",
         structure, unite="",
         hypotheses={"forme_sel": profil.forme_sel,
                     "FORMES_SEL_VALIDES": list(FORMES_SEL_VALIDES)})
    _log("REMUNERATION_BRUTE_SEL",
         "Rémunération brute SEL (input EC)",
         profil.remuneration_sel_souhaitee, unite="EUR",
         hypotheses={"source": "profil.remuneration_sel_souhaitee"})

    # --- Étape 1 : bénéfice avant rémunération dirigeant ---
    rem_brute = profil.remuneration_sel_souhaitee

    # Calcul des charges sociales selon forme SEL
    if profil.forme_sel == "SELARL":
        cotisations_sel = rem_brute * TX_TNS
        cout_remuneration = rem_brute + cotisations_sel
        doctrine_cotis = ("TX_TNS",)
        hyp_cotis = {"TX_TNS": TX_TNS,
                     "regime_dirigeant": "TNS (gérant majoritaire)"}
    else:  # SELAS
        cotisations_sel = rem_brute * TX_PATRONAL
        cout_remuneration = rem_brute + cotisations_sel
        doctrine_cotis = ("TX_PATRONAL",)
        hyp_cotis = {"TX_PATRONAL": TX_PATRONAL,
                     "regime_dirigeant": "Assimilé salarié (président)",
                     "note": "Cotisations salariales prélevées sur le brut, "
                             "non ajoutées au coût société"}

    _log("COTISATIONS_SEL",
         "Cotisations sociales SEL côté société",
         cotisations_sel, unite="EUR",
         doctrine_refs=doctrine_cotis,
         hypotheses=hyp_cotis)
    _log("COUT_REMUNERATION_SEL",
         "Coût total société pour la rémunération SEL",
         cout_remuneration, unite="EUR")

    benefice_avant_is = max(0.0, profil.recettes_bnc - profil.frais_pro_bnc - cout_remuneration)
    _log("BENEFICE_AVANT_IS",
         "Bénéfice imposable SEL avant IS",
         benefice_avant_is, unite="EUR",
         notes="Plancher à 0")

    # --- Étape 2 : IS société ---
    is_societe = _calcul_is(benefice_avant_is)
    distribuable = max(0.0, benefice_avant_is - is_societe)
    dividendes_bruts = distribuable  # Distribution intégrale (simplification v1)

    _log("IS_SOCIETE", "IS dû par la SEL",
         is_societe, unite="EUR",
         doctrine_refs=("IS_PLAF_REDUIT", "TX_IS_REDUIT", "TX_IS_NORMAL"),
         hypotheses={"IS_PLAF_REDUIT": IS_PLAF_REDUIT,
                     "TX_IS_REDUIT": TX_IS_REDUIT,
                     "TX_IS_NORMAL": TX_IS_NORMAL,
                     "benefice_avant_is_calcule": benefice_avant_is})
    _log("DIVIDENDES_DISTRIBUES",
         "Dividendes distribués (= distribuable, distribution intégrale v1)",
         dividendes_bruts, unite="EUR",
         hypotheses={"convention_v1": "distribution intégrale post-IS",
                     "alternative_v2": "Voir T4 (TNS Strategy) pour rétention",
                     "MENTION_RETENTION_V2": MENTION_RETENTION_V2})

    # --- Étape 3 : fiscalité personnelle dirigeant (branche dynamique) ---
    if profil.forme_sel == "SELARL":
        if audit is not None:
            sous_trace_regime = TraceAudit(
                regime="TNS (appel depuis stratégie L3 SELARL)",
                profil_resume=f"rem_brute={rem_brute:.0f}, div_bruts={dividendes_bruts:.0f}",
            )
            res_tns = calcul_module_tns(
                profil=profil,
                rem_nette_souhaitee=rem_brute,
                frais_reels=0.0,
                div_bruts=dividendes_bruts,
                audit=sous_trace_regime,
            )
            audit.attacher_sous_trace("module_tns", sous_trace_regime)
        else:
            res_tns = calcul_module_tns(
                profil=profil,
                rem_nette_souhaitee=rem_brute,
                frais_reels=0.0,
                div_bruts=dividendes_bruts,
            )
        net_rem = res_tns.net_apres_ir
        net_div = res_tns.net_dividendes

        _log("NET_REMUNERATION",
             "Net rémunération SELARL après cotis TNS + IR (depuis module TNS)",
             net_rem, unite="EUR",
             notes="Détails dans sous-trace 'module_tns'")
        _log("NET_DIVIDENDES",
             "Net dividendes (depuis module TNS, peut basculer TNS+IR au-delà du seuil 10 %)",
             net_div, unite="EUR",
             notes="Détails dans sous-trace 'module_tns'")

    else:  # SELAS
        if audit is not None:
            sous_trace_regime = TraceAudit(
                regime="Salarié (appel depuis stratégie L3 SELAS)",
                profil_resume=f"salaire_brut={rem_brute:.0f}",
            )
            res_sal = calcul_module_salarie(
                profil=profil,
                salaire_brut=rem_brute,
                audit=sous_trace_regime,
            )
            audit.attacher_sous_trace("module_salarie", sous_trace_regime)
        else:
            res_sal = calcul_module_salarie(profil=profil, salaire_brut=rem_brute)
        net_rem = res_sal.net_apres_impots
        net_div = dividendes_bruts * (1 - TX_PFU)

        _log("NET_REMUNERATION",
             "Net rémunération SELAS après cotis + IR (depuis module Salarié)",
             net_rem, unite="EUR",
             notes="Détails dans sous-trace 'module_salarie'")
        _log("NET_DIVIDENDES",
             "Net dividendes SELAS au PFU 31,4 % (pas de bascule TNS)",
             net_div, unite="EUR",
             doctrine_refs=("TX_PFU",),
             hypotheses={"TX_PFU": TX_PFU,
                         "dividendes_bruts_calcules": dividendes_bruts})

    net_total = net_rem + net_div
    efficacite = net_total / profil.recettes_bnc if profil.recettes_bnc > 0 else 0.0

    _log("NET_DIRIGEANT_TOTAL",
         "Net dirigeant total (net rém + net div)",
         net_total, unite="EUR",
         hypotheses={"composantes": "net_remuneration + net_dividendes",
                     "structure_appliquee": structure})
    _log("EFFICACITE",
         "Ratio net dirigeant / recettes",
         efficacite, unite="ratio")

    # --- Étape 4 : alertes structurantes en hypotheses (préserve wording métier) ---
    _log("ALERTES_NB",
         "Nombre d'alertes structurantes attachées (BNC vs SEL + rétention v2)",
         2.0, unite="count",
         hypotheses={"ALERTE_BNC_VS_SEL": ALERTE_BNC_VS_SEL,
                     "MENTION_RETENTION_V2": MENTION_RETENTION_V2},
         notes="Wording métier intégral préservé en hypotheses")

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
        efficacite=efficacite,
        alertes=alertes,
    )


def _calcul_strategie_l4(profil: Profil,
                         *,
                         audit: TraceAudit | None = None) -> ResultatStrategieLib:
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

    Args:
        profil: Profil client (BNC, avec forme_sel ∈ {"SELARL", "SELAS"}).
        audit: Trace d'audit optionnelle (G3c). Codes émis : `STRAT_LIB_L4_*`
            (3 étapes wrapper uniquement). Attache une sous-trace
            `strategie_l3_deleguee` contenant la trace complète du calcul L3
            sous-jacent — pas de recalcul, reflet fidèle de la délégation
            sémantique « L4 = L3 + alerte structurante ».
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("STRAT_LIB_L4_" + suffixe, label, valeur, **kw)

    # Délégation L3 (même calcul, même structure SEL) — avec sous-trace
    if audit is not None:
        sous_trace_l3 = TraceAudit(
            regime=f"Stratégie L3 SEL ({profil.forme_sel}) déléguée par L4",
            profil_resume=f"recettes={profil.recettes_bnc:.0f}, "
                          f"forme_sel={profil.forme_sel}",
        )
        res_l3 = _calcul_strategie_l3(profil, audit=sous_trace_l3)
        audit.attacher_sous_trace("strategie_l3_deleguee", sous_trace_l3)
    else:
        res_l3 = _calcul_strategie_l3(profil)

    # Étape wrapper L4 : valeurs reportées de L3 + alerte structurante v2
    _log("DELEGATION_L3",
         "Stratégie déléguée à L3 (calcul numérique identique)",
         res_l3.net_dirigeant_total, unite="EUR",
         hypotheses={"strategie_code": "L4",
                     "strategie_nom": "SEL + Structuration patrimoniale (cadrage v1)",
                     "delegation_cible": "L3",
                     "note": "Voir sous-trace 'strategie_l3_deleguee' pour le calcul complet"})
    _log("ALERTE_STRUCTURATION_V2_NB",
         "Alerte structurante L4 attachée (cadrage v1 — leviers non modélisés)",
         1.0, unite="count",
         hypotheses={"ALERTE_L4_V2": ALERTE_L4_V2,
                     "leviers_non_modelises": ["holding patrimoniale",
                                                "démembrement",
                                                "transmission successorale",
                                                "SPFPL"]},
         notes="Wording métier intégral préservé en hypotheses")
    _log("NET_DIRIGEANT_TOTAL",
         "Net dirigeant total (= net L3, pas de recalcul L4)",
         res_l3.net_dirigeant_total, unite="EUR",
         hypotheses={"source": "ResultatStrategieLib L3",
                     "convention_l4": "Pas de recalcul — délégation sémantique pure"})

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


def arbitrage_complet_liberal(profil: Profil,
                              *,
                              audit: TraceAudit | None = None) -> ResultatArbitrageLib:
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
        profil: Profil client (avec forme_sel ∈ {"SELARL", "SELAS"}).
        audit: Trace d'audit optionnelle (MODE_AUDIT G3c, spec 1.1.0).
            Side channel. Si fournie, attache 4 sous-traces nommées
            `strategie_L1`/`L2`/`L3`/`L4`. La sous-trace `strategie_L4`
            contient elle-même une sous-trace `strategie_l3_deleguee` qui
            reflète la délégation sémantique de L4 vers L3.

    Returns:
        ResultatArbitrageLib avec les 4 stratégies + plus_efficace_fiscalement.
    """
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    # --- Calcul des 4 stratégies (chacune dans sa sous-trace) ---
    strategies = {}
    for code_strat, calcul_fn in (
        ("L1", _calcul_strategie_l1),
        ("L2", _calcul_strategie_l2),
        ("L3", _calcul_strategie_l3),
        ("L4", _calcul_strategie_l4),
    ):
        if audit is not None:
            sous_strat = TraceAudit(
                regime=f"Stratégie Libéral/{code_strat}",
                profil_resume=f"recettes_bnc={profil.recettes_bnc:.0f}, "
                              f"forme_sel={profil.forme_sel}",
            )
            strategies[code_strat] = calcul_fn(profil, audit=sous_strat)
            audit.attacher_sous_trace(f"strategie_{code_strat}", sous_strat)
        else:
            strategies[code_strat] = calcul_fn(profil)

    # --- Deltas vs stratégie L1 (référence BNC pur) ---
    net_l1 = strategies["L1"].net_dirigeant_total
    _log("STRAT_LIB_COMPARE_AB",
         "Comparaison delta net par rapport à L1 (agrégat)",
         net_l1, unite="EUR",
         notes="L1 (BNC pur) retenue comme référence")
    for code_strat in ("L2", "L3", "L4"):
        delta = strategies[code_strat].net_dirigeant_total - net_l1
        _log(f"STRAT_LIB_DELTA_{code_strat}_VS_L1",
             f"Écart net_dirigeant_total {code_strat} vs L1",
             delta, unite="EUR",
             parent_id="STRAT_LIB_COMPARE_AB",
             hypotheses={"code_strategie": code_strat,
                         "net_strategie": strategies[code_strat].net_dirigeant_total,
                         "net_reference_L1": net_l1})

    # --- Critère de sélection + avertissement BNC/SEL ---
    critere = "max(net_dirigeant_total)"
    plus_efficace = max(strategies,
                        key=lambda c: strategies[c].net_dirigeant_total)

    _log("STRAT_LIB_AVERTISSEMENT_BNC_SEL",
         "Avertissement BNC vs SEL (attaché systématiquement au résultat)",
         1.0, unite="count",
         hypotheses={"ALERTE_BNC_VS_SEL": ALERTE_BNC_VS_SEL,
                     "portee": "Affichage UI obligatoire",
                     "doctrine_module": "Voir docstring module Libéral §27-39"},
         notes="Wording métier intégral préservé en hypotheses")
    _log("STRAT_LIB_CRITERE_PLUS_EFFICACE",
         "Critère de sélection appliqué",
         critere, unite="",
         notes="Sélection mécanique sur le net dirigeant total — "
               "ne constitue pas un avis sur le choix de structuration juridique")
    _log("STRAT_LIB_PLUS_EFFICACE_FISCALEMENT",
         "Code de la stratégie au plus haut net dirigeant (indicateur fiscal factuel)",
         plus_efficace, unite="",
         hypotheses={"critere": critere,
                     "net_calcule": strategies[plus_efficace].net_dirigeant_total,
                     "tous_nets": {c: strategies[c].net_dirigeant_total
                                   for c in strategies},
                     "convention_terminologique": "PLUS_EFFICACE_FISCALEMENT (pas RETENU)"},
         notes="Terminologie spécifique Libéral — voir docstring module §36-38. "
               "Indicateur factuel — voir avertissement BNC vs SEL.")

    return ResultatArbitrageLib(
        strategies=strategies,
        plus_efficace_fiscalement=plus_efficace,
        avertissement_bnc_sel=ALERTE_BNC_VS_SEL,
        profil=profil,
    )
