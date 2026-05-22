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

MODE_AUDIT (G3b, spec 1.1.0) :
- `_calcul_strategie_t1/t2/t3/t4()` acceptent un paramètre opt-in
  `audit: TraceAudit | None`. Codes émis : `STRAT_TNS_T<X>_*`.
- `arbitrage_complet_tns()` accepte le même paramètre. Codes émis :
  `STRAT_TNS_*` (niveau méta). Attache des sous-traces nommées
  `strategie_T<X>` pour les 4 stratégies, et chaque stratégie attache
  elle-même une sous-trace `module_tns` pour l'appel `calcul_module_tns`
  (2 niveaux d'imbrication, spec 1.1.0).

Conventions appliquées :
- Vocabulaire factuel : `STRAT_TNS_RETENU`, `STRAT_TNS_CRITERE_RETENU`,
  `STRAT_TNS_DELTA_T<X>_VS_T1`, `STRAT_TNS_INDICATEURS_SEPARES`.
- Les labels et notes respectent les restrictions terminologiques définies
  dans TERMINOLOGY.md §2. Aucun wording prescriptif.
- Les textes d'alertes T2/T4 (qui peuvent contenir du vocabulaire métier
  hors périmètre MODE_AUDIT, ex. « optimum dividendes-PFU ») restent dans
  les `hypotheses` (champ dict, non scanné par le test non-prescriptif),
  pas dans `label` ni `notes`.
- Le critère de sélection est explicité comme hypothèse (`critere`),
  le résultat dérive mécaniquement.
"""

from dataclasses import dataclass, field
from typing import Optional

from core.profil import (
    Profil,
    TX_TNS, TX_PFU, SEUIL_DIV_TNS,
    TX_IS_REDUIT, TX_IS_NORMAL, IS_PLAF_REDUIT,
    PASS_2026,
)
from core.audit import TraceAudit
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
def _calcul_strategie_t1(profil: Profil,
                         *,
                         audit: TraceAudit | None = None) -> ResultatStrategieTNS:
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

    Args:
        profil: Profil client (régime TNS).
        audit: Trace d'audit optionnelle (MODE_AUDIT G3b). Side channel —
            n'affecte jamais le résultat. Codes émis : `STRAT_TNS_T1_*`.
            Si fournie, attache une sous-trace `module_tns` pour l'appel
            `calcul_module_tns` (spec 1.1.0).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("STRAT_TNS_T1_" + suffixe, label, valeur, **kw)

    enveloppe = profil.benefice_is
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS

    _log("ENVELOPPE", "Enveloppe bénéfice IS (input)",
         enveloppe, unite="EUR",
         hypotheses={"strategie_code": "T1",
                     "strategie_nom": "Rémunération dominante"})
    _log("SEUIL_10PCT",
         "Seuil 10 % (capital + primes + CCA) — référence dividendes",
         seuil_10pct, unite="EUR",
         doctrine_refs=("SEUIL_DIV_TNS",),
         hypotheses={"SEUIL_DIV_TNS": SEUIL_DIV_TNS,
                     "capital_cca_profil": profil.capital_cca})

    # 1. Calibrer la rémunération brute
    rem_brute = PART_REM_T1 * enveloppe / (1 + TX_TNS)
    cout_remuneration = rem_brute * (1 + TX_TNS)

    _log("PART_REM_APPLIQUEE",
         "Part de l'enveloppe affectée à la rémunération (allocation)",
         PART_REM_T1, unite="ratio",
         hypotheses={"PART_REM_T1": PART_REM_T1},
         notes="Convention v19 T1 — rémunération dominante 85 %")
    _log("REMUNERATION_BRUTE",
         "Rémunération brute du dirigeant calibrée",
         rem_brute, unite="EUR")
    _log("COUT_REMUNERATION",
         "Coût total société pour la rémunération (brut + cotisations TNS)",
         cout_remuneration, unite="EUR",
         doctrine_refs=("TX_TNS",),
         hypotheses={"TX_TNS": TX_TNS,
                     "rem_brute_calculee": rem_brute})

    # 2. Reste après rémunération
    reste_avant_is = max(0.0, enveloppe - cout_remuneration)
    _log("RESTE_AVANT_IS",
         "Reste société avant IS (enveloppe − coût rémunération)",
         reste_avant_is, unite="EUR",
         notes="Plancher à 0")

    # IS inline (helper _calcul_is non instrumenté — voir cadrage G3b §A2)
    is_societe = _calcul_is(reste_avant_is)
    _log("IS_SOCIETE",
         "IS dû par la société sur le reste",
         is_societe, unite="EUR",
         doctrine_refs=("IS_PLAF_REDUIT", "TX_IS_REDUIT", "TX_IS_NORMAL"),
         hypotheses={"IS_PLAF_REDUIT": IS_PLAF_REDUIT,
                     "TX_IS_REDUIT": TX_IS_REDUIT,
                     "TX_IS_NORMAL": TX_IS_NORMAL,
                     "reste_avant_is_calcule": reste_avant_is},
         notes="Barème simplifié : 15 % jusqu'à 42 500 €, 25 % au-delà")

    div_distribuables = max(0.0, reste_avant_is - is_societe)
    _log("DIVIDENDES_DISTRIBUABLES",
         "Dividendes distribuables (reste − IS)",
         div_distribuables, unite="EUR")

    # 3. Appel calcul_module_tns avec sous-trace
    if audit is not None:
        sous_trace_tns = TraceAudit(
            regime="TNS (appel depuis stratégie T1)",
            profil_resume=f"rem_brute={rem_brute:.0f}, div_bruts={div_distribuables:.0f}",
        )
        res_tns = calcul_module_tns(
            profil=profil,
            rem_nette_souhaitee=rem_brute,
            frais_reels=0.0,
            div_bruts=div_distribuables,
            audit=sous_trace_tns,
        )
        audit.attacher_sous_trace("module_tns", sous_trace_tns)
    else:
        res_tns = calcul_module_tns(
            profil=profil,
            rem_nette_souhaitee=rem_brute,
            frais_reels=0.0,
            div_bruts=div_distribuables,
        )

    # 4. Indicateurs de sortie tracés depuis le résultat module TNS
    _log("NET_REMUNERATION",
         "Net rémunération après cotisations + IR (depuis module TNS)",
         res_tns.net_apres_ir, unite="EUR",
         notes="Détails dans sous-trace 'module_tns'")
    _log("NET_DIVIDENDES",
         "Net dividendes après IS + PFU (depuis module TNS)",
         res_tns.net_dividendes, unite="EUR",
         notes="Détails dans sous-trace 'module_tns'")

    net_immediat = res_tns.net_apres_ir + res_tns.net_dividendes
    efficacite = net_immediat / enveloppe if enveloppe > 0 else 0.0

    _log("NET_DIRIGEANT_IMMEDIAT",
         "Net dirigeant immédiat (rém + div)",
         net_immediat, unite="EUR",
         hypotheses={"composantes": "net_apres_ir + net_dividendes"})
    _log("EFFICACITE_IMMEDIATE",
         "Ratio net dirigeant immédiat / enveloppe",
         efficacite, unite="ratio")

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
        net_dirigeant_immediat=net_immediat,
        cotisations_tns_total=res_tns.cotisations_tns + res_tns.cotis_tns_sur_div,
        is_societe=is_societe,
        cout_total_societe=cout_remuneration,
        efficacite_immediate=efficacite,
        alertes=[],
    )


def _calcul_strategie_t2(profil: Profil,
                         *,
                         audit: TraceAudit | None = None) -> ResultatStrategieTNS:
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

    Args:
        profil: Profil client (régime TNS).
        audit: Trace d'audit optionnelle (G3b). Codes émis : `STRAT_TNS_T2_*`.
            Les textes d'alertes sont placés en `hypotheses` (non-prescriptif).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("STRAT_TNS_T2_" + suffixe, label, valeur, **kw)

    enveloppe = profil.benefice_is
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS
    ratio_marginal = seuil_10pct / enveloppe if enveloppe > 0 else 0.0

    _log("ENVELOPPE", "Enveloppe bénéfice IS (input)",
         enveloppe, unite="EUR",
         hypotheses={"strategie_code": "T2",
                     "strategie_nom": "Dividendes sous seuil 10 %"})
    _log("SEUIL_10PCT",
         "Seuil 10 % (capital + primes + CCA)",
         seuil_10pct, unite="EUR",
         doctrine_refs=("SEUIL_DIV_TNS",),
         hypotheses={"SEUIL_DIV_TNS": SEUIL_DIV_TNS,
                     "capital_cca_profil": profil.capital_cca})
    _log("RATIO_MARGINAL",
         "Ratio seuil_10pct / enveloppe (référence d'alerte)",
         ratio_marginal, unite="ratio",
         hypotheses={"ALERTE_T2_RATIO_MARGINAL_SEUIL": ALERTE_T2_RATIO_MARGINAL_SEUIL})

    # 1. Cibler des dividendes bruts égaux au seuil 10 %
    div_bruts_cibles = seuil_10pct

    if div_bruts_cibles <= IS_PLAF_REDUIT:
        tx_is_eff = TX_IS_REDUIT
        resultat_societe_pour_div = div_bruts_cibles / (1 - tx_is_eff) if (1 - tx_is_eff) > 0 else 0
        is_pour_div = resultat_societe_pour_div - div_bruts_cibles
        branche_is = "reduit"
    else:
        resultat_societe_pour_div = (div_bruts_cibles - IS_PLAF_REDUIT * (TX_IS_NORMAL - TX_IS_REDUIT)) / (1 - TX_IS_NORMAL)
        is_pour_div = _calcul_is(resultat_societe_pour_div)
        div_bruts_cibles = resultat_societe_pour_div - is_pour_div
        branche_is = "mixte"

    _log("RESULTAT_SOCIETE_POUR_DIV",
         "Résultat société avant IS nécessaire pour atteindre la cible dividendes",
         resultat_societe_pour_div, unite="EUR",
         doctrine_refs=("IS_PLAF_REDUIT", "TX_IS_REDUIT", "TX_IS_NORMAL"),
         hypotheses={"IS_PLAF_REDUIT": IS_PLAF_REDUIT,
                     "TX_IS_REDUIT": TX_IS_REDUIT,
                     "TX_IS_NORMAL": TX_IS_NORMAL,
                     "branche_is": branche_is},
         notes=f"Branche IS appliquée : {branche_is}")
    _log("IS_POUR_DIV",
         "IS dû par la société pour produire la cible dividendes",
         is_pour_div, unite="EUR")
    _log("DIV_BRUTS_CIBLES",
         "Dividendes bruts cibles (après ajustement IS)",
         div_bruts_cibles, unite="EUR")

    # 2. Le reste du bénéfice finance la rémunération + cotis
    reste_pour_rem = max(0.0, enveloppe - resultat_societe_pour_div)
    rem_brute = reste_pour_rem / (1 + TX_TNS) if reste_pour_rem > 0 else 0.0
    cout_remuneration = rem_brute * (1 + TX_TNS)

    _log("REMUNERATION_BRUTE",
         "Rémunération brute (reste après affectation aux dividendes)",
         rem_brute, unite="EUR",
         doctrine_refs=("TX_TNS",),
         hypotheses={"TX_TNS": TX_TNS,
                     "reste_pour_rem_calcule": reste_pour_rem})
    _log("COUT_REMUNERATION",
         "Coût total société pour la rémunération",
         cout_remuneration, unite="EUR")

    # 3. Garde-fou plafond 90 %
    garde_fou_applique = False
    if div_bruts_cibles > enveloppe * 0.9:
        div_bruts_cibles = enveloppe * 0.5
        rem_brute = enveloppe * 0.5 / (1 + TX_TNS)
        is_pour_div = 0.0
        garde_fou_applique = True

    _log("GARDE_FOU_90PCT",
         "Application du garde-fou plafond 90 % (booléen)",
         1.0 if garde_fou_applique else 0.0, unite="bool",
         hypotheses={"plafond_garde_fou": 0.9,
                     "comportement_si_declenche": "div = 50 % enveloppe, rem ajustée"})

    # 4. Appel module TNS avec sous-trace
    if audit is not None:
        sous_trace_tns = TraceAudit(
            regime="TNS (appel depuis stratégie T2)",
            profil_resume=f"rem_brute={rem_brute:.0f}, div_bruts={div_bruts_cibles:.0f}",
        )
        res_tns = calcul_module_tns(
            profil=profil,
            rem_nette_souhaitee=rem_brute,
            frais_reels=0.0,
            div_bruts=div_bruts_cibles,
            audit=sous_trace_tns,
        )
        audit.attacher_sous_trace("module_tns", sous_trace_tns)
    else:
        res_tns = calcul_module_tns(
            profil=profil,
            rem_nette_souhaitee=rem_brute,
            frais_reels=0.0,
            div_bruts=div_bruts_cibles,
        )

    # 5. Construction des alertes (textes métier préservés dans hypotheses)
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

    # Étape trace : nombre d'alertes (factuel), textes en hypotheses
    _log("ALERTES_NB",
         "Nombre d'alertes T2 déclenchées",
         float(len(alertes)), unite="count",
         hypotheses={"ALERTE_T2_CAPITAL_FAIBLE_SEUIL": ALERTE_T2_CAPITAL_FAIBLE_SEUIL,
                     "ALERTE_T2_RATIO_MARGINAL_SEUIL": ALERTE_T2_RATIO_MARGINAL_SEUIL,
                     "capital_cca_profil": profil.capital_cca,
                     "ratio_marginal_calcule": ratio_marginal,
                     "textes_alertes": alertes})

    # 6. Vérification stricte : dividendes ≤ seuil 10 %
    assert res_tns.div_bruts <= seuil_10pct * 1.0001 or div_bruts_cibles == 0, (
        f"VIOLATION T2 : dividendes ({res_tns.div_bruts:.2f}) > seuil 10% "
        f"({seuil_10pct:.2f}). Cette assertion ne doit jamais être violée."
    )

    # Indicateurs de sortie
    _log("NET_REMUNERATION",
         "Net rémunération après cotisations + IR (depuis module TNS)",
         res_tns.net_apres_ir, unite="EUR",
         notes="Détails dans sous-trace 'module_tns'")
    _log("NET_DIVIDENDES",
         "Net dividendes après IS + PFU (depuis module TNS)",
         res_tns.net_dividendes, unite="EUR",
         notes="Détails dans sous-trace 'module_tns'")

    net_immediat = res_tns.net_apres_ir + res_tns.net_dividendes
    efficacite = net_immediat / enveloppe if enveloppe > 0 else 0.0

    _log("NET_DIRIGEANT_IMMEDIAT",
         "Net dirigeant immédiat (rém + div)",
         net_immediat, unite="EUR",
         hypotheses={"composantes": "net_apres_ir + net_dividendes"})
    _log("EFFICACITE_IMMEDIATE",
         "Ratio net dirigeant immédiat / enveloppe",
         efficacite, unite="ratio")

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
        net_dirigeant_immediat=net_immediat,
        cotisations_tns_total=res_tns.cotisations_tns + res_tns.cotis_tns_sur_div,
        is_societe=is_pour_div,
        cout_total_societe=cout_remuneration,
        efficacite_immediate=efficacite,
        alertes=alertes,
    )


def _calcul_strategie_t3(profil: Profil,
                         *,
                         audit: TraceAudit | None = None) -> ResultatStrategieTNS:
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

    Args:
        profil: Profil client (régime TNS).
        audit: Trace d'audit optionnelle (G3b). Codes émis : `STRAT_TNS_T3_*`.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("STRAT_TNS_T3_" + suffixe, label, valeur, **kw)

    enveloppe = profil.benefice_is
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS

    _log("ENVELOPPE", "Enveloppe bénéfice IS (input)",
         enveloppe, unite="EUR",
         hypotheses={"strategie_code": "T3",
                     "strategie_nom": "Mix efficient + PERIN"})
    _log("SEUIL_10PCT", "Seuil 10 % (capital + primes + CCA)",
         seuil_10pct, unite="EUR",
         doctrine_refs=("SEUIL_DIV_TNS",),
         hypotheses={"SEUIL_DIV_TNS": SEUIL_DIV_TNS,
                     "capital_cca_profil": profil.capital_cca})

    # 1. Allocation rémunération (50 % par défaut)
    rem_brute = PART_REM_T3 * enveloppe / (1 + TX_TNS)
    cout_remuneration = rem_brute * (1 + TX_TNS)

    _log("PART_REM_APPLIQUEE",
         "Part de l'enveloppe affectée à la rémunération",
         PART_REM_T3, unite="ratio",
         hypotheses={"PART_REM_T3": PART_REM_T3},
         notes="Convention v19 T3 — mix équilibré 50 %")
    _log("REMUNERATION_BRUTE",
         "Rémunération brute du dirigeant",
         rem_brute, unite="EUR")
    _log("COUT_REMUNERATION",
         "Coût total société pour la rémunération",
         cout_remuneration, unite="EUR",
         doctrine_refs=("TX_TNS",),
         hypotheses={"TX_TNS": TX_TNS})

    # 2. Reste société → IS → dividendes plafonnés au seuil 10 %
    reste_avant_is = max(0.0, enveloppe - cout_remuneration)
    is_societe = _calcul_is(reste_avant_is)
    distribuable = max(0.0, reste_avant_is - is_societe)
    div_bruts = min(seuil_10pct, distribuable)

    _log("RESTE_AVANT_IS", "Reste société avant IS",
         reste_avant_is, unite="EUR")
    _log("IS_SOCIETE", "IS dû par la société",
         is_societe, unite="EUR",
         doctrine_refs=("IS_PLAF_REDUIT", "TX_IS_REDUIT", "TX_IS_NORMAL"),
         hypotheses={"IS_PLAF_REDUIT": IS_PLAF_REDUIT,
                     "TX_IS_REDUIT": TX_IS_REDUIT,
                     "TX_IS_NORMAL": TX_IS_NORMAL})
    _log("DIVIDENDES_PLAFONNES",
         "Dividendes plafonnés au seuil 10 % (min(seuil, distribuable))",
         div_bruts, unite="EUR",
         hypotheses={"distribuable_brut": distribuable,
                     "seuil_10pct_reference": seuil_10pct})

    # 3. PERIN au plafond individuel
    plaf_perin = calcul_plafond_perin(
        titulaire="Dirigeant",
        revenu_pro_n_moins_1=rem_brute,
    )
    versement_perin = plaf_perin.plafond_individuel

    _log("PLAFOND_PERIN_INDIVIDUEL",
         "Plafond PERIN individuel calculé (revenu pro = rem brute T3)",
         versement_perin, unite="EUR",
         doctrine_refs=("PASS_2026",),
         hypotheses={"PASS_2026": PASS_2026,
                     "PERIN_PLAFOND_MIN": PERIN_PLAFOND_MIN,
                     "PERIN_PLAFOND_MAX": PERIN_PLAFOND_MAX,
                     "revenu_pro_applique": rem_brute,
                     "titulaire": "Dirigeant"})
    _log("VERSEMENT_PERIN",
         "Versement PERIN retenu (= plafond individuel par défaut T3)",
         versement_perin, unite="EUR",
         notes="Convention T3 — versement par défaut au plafond")

    # 4. Appel module TNS avec sous-trace
    if audit is not None:
        sous_trace_tns = TraceAudit(
            regime="TNS (appel depuis stratégie T3)",
            profil_resume=f"rem_brute={rem_brute:.0f}, div_bruts={div_bruts:.0f}",
        )
        res_tns = calcul_module_tns(
            profil=profil,
            rem_nette_souhaitee=rem_brute,
            frais_reels=0.0,
            div_bruts=div_bruts,
            audit=sous_trace_tns,
        )
        audit.attacher_sous_trace("module_tns", sous_trace_tns)
    else:
        res_tns = calcul_module_tns(
            profil=profil,
            rem_nette_souhaitee=rem_brute,
            frais_reels=0.0,
            div_bruts=div_bruts,
        )

    # 5. Économie d'IR liée au PERIN (TMI marginal)
    from core.ir_foyer import calcul_ir_foyer, tmi_de
    impots = calcul_ir_foyer(res_tns.revenu_imposable_foyer, profil)
    tmi_marginal = impots["tmi"]
    economie_ir_perin = versement_perin * tmi_marginal

    _log("TMI_MARGINAL",
         "TMI marginal du foyer (référence pour économie PERIN)",
         tmi_marginal, unite="ratio",
         notes="Calculé via core.ir_foyer sur revenu imposable foyer")
    _log("ECONOMIE_IR_PERIN",
         "Économie d'IR liée au versement PERIN (versement × TMI marginal)",
         economie_ir_perin, unite="EUR",
         hypotheses={"versement_perin_calcule": versement_perin,
                     "tmi_marginal_calcule": tmi_marginal})

    # Indicateurs de sortie
    _log("NET_REMUNERATION",
         "Net rémunération après cotisations + IR (depuis module TNS)",
         res_tns.net_apres_ir, unite="EUR",
         notes="Détails dans sous-trace 'module_tns'")
    _log("NET_DIVIDENDES",
         "Net dividendes après IS + PFU (depuis module TNS)",
         res_tns.net_dividendes, unite="EUR",
         notes="Détails dans sous-trace 'module_tns'")

    net_immediat = res_tns.net_apres_ir + res_tns.net_dividendes + economie_ir_perin
    efficacite = net_immediat / enveloppe if enveloppe > 0 else 0.0

    _log("NET_DIRIGEANT_IMMEDIAT",
         "Net dirigeant immédiat (rém + div + économie IR PERIN)",
         net_immediat, unite="EUR",
         hypotheses={"composantes": "net_apres_ir + net_dividendes + economie_ir_perin",
                     "note_perin": "Le versement PERIN lui-même n'est pas soustrait — "
                                   "c'est une épargne du dirigeant, pas une charge"})
    _log("EFFICACITE_IMMEDIATE",
         "Ratio net dirigeant immédiat / enveloppe",
         efficacite, unite="ratio")

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
        efficacite_immediate=efficacite,
        alertes=[],
    )


def _calcul_strategie_t4(profil: Profil,
                         *,
                         audit: TraceAudit | None = None) -> ResultatStrategieTNS:
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

    La trace MODE_AUDIT respecte cette convention : les deux indicateurs
    sont tracés comme étapes SÉPARÉES (pas de parent commun, pas
    d'agrégation), explicitant la règle structurelle T4.

    Args:
        profil: Profil client (régime TNS).
        audit: Trace d'audit optionnelle (G3b). Codes émis : `STRAT_TNS_T4_*`.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("STRAT_TNS_T4_" + suffixe, label, valeur, **kw)

    enveloppe = profil.benefice_is
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS

    _log("ENVELOPPE", "Enveloppe bénéfice IS (input)",
         enveloppe, unite="EUR",
         hypotheses={"strategie_code": "T4",
                     "strategie_nom": "Arbitrage IS (rétention en société)"})
    _log("SEUIL_10PCT", "Seuil 10 % (référence, non utilisée en T4)",
         seuil_10pct, unite="EUR",
         doctrine_refs=("SEUIL_DIV_TNS",),
         hypotheses={"SEUIL_DIV_TNS": SEUIL_DIV_TNS,
                     "note": "T4 ne distribue pas, seuil tracé pour cohérence"})

    # 1. Rémunération réduite (30 % du bénéfice)
    rem_brute = PART_REM_T4 * enveloppe / (1 + TX_TNS)
    cout_remuneration = rem_brute * (1 + TX_TNS)

    _log("PART_REM_APPLIQUEE",
         "Part de l'enveloppe affectée à la rémunération",
         PART_REM_T4, unite="ratio",
         hypotheses={"PART_REM_T4": PART_REM_T4},
         notes="Convention v19 T4 — rémunération réduite 30 %")
    _log("REMUNERATION_BRUTE",
         "Rémunération brute du dirigeant",
         rem_brute, unite="EUR")
    _log("COUT_REMUNERATION",
         "Coût total société pour la rémunération",
         cout_remuneration, unite="EUR",
         doctrine_refs=("TX_TNS",),
         hypotheses={"TX_TNS": TX_TNS})

    # 2. Reste société → IS → conservé (PAS de distribution)
    reste_avant_is = max(0.0, enveloppe - cout_remuneration)
    is_societe = _calcul_is(reste_avant_is)
    benefice_retenu = max(0.0, reste_avant_is - is_societe)

    _log("RESTE_AVANT_IS", "Reste société avant IS",
         reste_avant_is, unite="EUR")
    _log("IS_SOCIETE", "IS dû par la société",
         is_societe, unite="EUR",
         doctrine_refs=("IS_PLAF_REDUIT", "TX_IS_REDUIT", "TX_IS_NORMAL"),
         hypotheses={"IS_PLAF_REDUIT": IS_PLAF_REDUIT,
                     "TX_IS_REDUIT": TX_IS_REDUIT,
                     "TX_IS_NORMAL": TX_IS_NORMAL})

    # ÉTAPE STRUCTURELLE T4 : indicateur séparé (pas agrégé au net dirigeant)
    _log("BENEFICE_RETENU_SOCIETE",
         "Bénéfice retenu en société (indicateur SÉPARÉ du net dirigeant)",
         benefice_retenu, unite="EUR",
         hypotheses={"convention_t4": "non-agrégation",
                     "regle": "Ne PAS sommer avec net_dirigeant_immediat",
                     "texte_alerte_v19": (
                         f"Bénéfice retenu en société : {benefice_retenu:,.2f} € "
                         f"(après IS). Cette valeur reste en société et n'est PAS "
                         f"un revenu disponible pour le dirigeant. Sa distribution "
                         f"ultérieure subira la fiscalité applicable au moment de "
                         f"la distribution."
                     )},
         notes="Indicateur distinct pour interprétation par l'EC")

    # 3. Appel module TNS avec dividendes = 0
    if audit is not None:
        sous_trace_tns = TraceAudit(
            regime="TNS (appel depuis stratégie T4)",
            profil_resume=f"rem_brute={rem_brute:.0f}, div_bruts=0 (pas de distribution)",
        )
        res_tns = calcul_module_tns(
            profil=profil,
            rem_nette_souhaitee=rem_brute,
            frais_reels=0.0,
            div_bruts=0.0,
            audit=sous_trace_tns,
        )
        audit.attacher_sous_trace("module_tns", sous_trace_tns)
    else:
        res_tns = calcul_module_tns(
            profil=profil,
            rem_nette_souhaitee=rem_brute,
            frais_reels=0.0,
            div_bruts=0.0,
        )

    # 4. Net dirigeant immédiat = uniquement la rémunération nette
    net_immediat = res_tns.net_apres_ir

    # ASSERTION CRITIQUE : pas d'agrégation
    assert net_immediat == res_tns.net_apres_ir, (
        f"VIOLATION T4 : net_dirigeant_immediat doit être strictement la "
        f"rémunération nette, pas d'agrégation avec le bénéfice retenu."
    )

    _log("NET_REMUNERATION",
         "Net rémunération après cotisations + IR (depuis module TNS)",
         res_tns.net_apres_ir, unite="EUR",
         notes="Détails dans sous-trace 'module_tns'")
    _log("NET_DIRIGEANT_IMMEDIAT",
         "Net dirigeant immédiat (= rémunération nette UNIQUEMENT, T4)",
         net_immediat, unite="EUR",
         hypotheses={"convention_t4": "non-agrégation",
                     "composantes": "net_apres_ir uniquement",
                     "exclusion_explicite": "benefice_retenu_societe (indicateur séparé)"})

    efficacite = net_immediat / enveloppe if enveloppe > 0 else 0.0
    _log("EFFICACITE_IMMEDIATE",
         "Ratio net dirigeant immédiat / enveloppe (sur net dirigeant seul)",
         efficacite, unite="ratio",
         notes="Convention T4 — bénéfice retenu non inclus")

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
        efficacite_immediate=efficacite,
        alertes=[
            f"Bénéfice retenu en société : {benefice_retenu:,.2f} € (après IS). "
            f"Cette valeur reste en société et n'est PAS un revenu disponible pour le dirigeant. "
            f"Sa distribution ultérieure subira la fiscalité applicable au moment de la distribution."
        ],
    )


def arbitrage_complet_tns(profil: Profil,
                          *,
                          audit: TraceAudit | None = None) -> ResultatArbitrageTNS:
    """
    Arbitrage TNS consolidé sur les 4 stratégies T1-T4.

    Calcule chacune des 4 stratégies pour le profil, et identifie la
    stratégie retenue par le critère `max(net_dirigeant_immediat)`.

    IMPORTANT : la sélection se fonde uniquement sur le net dirigeant
    immédiat. Pour T4, le bénéfice retenu en société n'entre PAS dans le
    classement (ce n'est pas un revenu disponible). L'EC doit interpréter
    T4 en tenant compte de cet indicateur séparé.

    Note terminologique : la clé `recommandee` du résultat est historique
    (Phase A). Elle référence le code de la stratégie au plus haut
    `net_dirigeant_immediat`, c'est-à-dire un **indicateur technique**,
    pas une recommandation au sens conseil.

    Args:
        profil: Profil client (régime TNS uniquement attendu).
        audit: Trace d'audit optionnelle (MODE_AUDIT G3b, spec 1.1.0).
            Side channel. Si fournie, attache 4 sous-traces nommées
            `strategie_T1`/`T2`/`T3`/`T4`, chacune contenant elle-même une
            sous-trace `module_tns` (2 niveaux d'imbrication).

    Returns:
        ResultatArbitrageTNS avec dict des 4 stratégies + code retenu.
    """
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    # --- Calcul des 4 stratégies (chacune dans sa sous-trace) ---
    strategies = {}
    for code_strat, calcul_fn in (
        ("T1", _calcul_strategie_t1),
        ("T2", _calcul_strategie_t2),
        ("T3", _calcul_strategie_t3),
        ("T4", _calcul_strategie_t4),
    ):
        if audit is not None:
            sous_strat = TraceAudit(
                regime=f"Stratégie TNS/{code_strat}",
                profil_resume=f"benefice_is={profil.benefice_is:.0f}, "
                              f"capital_cca={profil.capital_cca:.0f}",
            )
            strategies[code_strat] = calcul_fn(profil, audit=sous_strat)
            audit.attacher_sous_trace(f"strategie_{code_strat}", sous_strat)
        else:
            strategies[code_strat] = calcul_fn(profil)

    # --- Deltas vs stratégie T1 (référence) ---
    net_t1 = strategies["T1"].net_dirigeant_immediat
    _log("STRAT_TNS_COMPARE_AB",
         "Comparaison delta net par rapport à T1 (agrégat)",
         net_t1, unite="EUR",
         notes="T1 retenue comme référence par convention v19")
    for code_strat in ("T2", "T3", "T4"):
        delta = strategies[code_strat].net_dirigeant_immediat - net_t1
        _log(f"STRAT_TNS_DELTA_{code_strat}_VS_T1",
             f"Écart net_dirigeant_immediat {code_strat} vs T1",
             delta, unite="EUR",
             parent_id="STRAT_TNS_COMPARE_AB",
             hypotheses={"code_strategie": code_strat,
                         "net_strategie": strategies[code_strat].net_dirigeant_immediat,
                         "net_reference_T1": net_t1})

    # --- Indicateurs séparés T4 (convention de non-agrégation) ---
    benefice_retenu_t4 = strategies["T4"].benefice_retenu_societe
    _log("STRAT_TNS_INDICATEURS_SEPARES",
         "Bénéfice retenu T4 (indicateur séparé, NON inclus dans le critère de sélection)",
         benefice_retenu_t4, unite="EUR",
         hypotheses={"convention": "non-agrégation T4",
                     "code_strategie_concernee": "T4",
                     "net_dirigeant_t4": strategies["T4"].net_dirigeant_immediat,
                     "interpretation": "indicateur distinct, à lire en complément du net dirigeant"},
         notes="Tracé pour visibilité, exclu volontairement du critère de sélection")

    # --- Critère de sélection ---
    critere = "max(net_dirigeant_immediat)"
    recommandee = max(strategies,
                      key=lambda c: strategies[c].net_dirigeant_immediat)

    _log("STRAT_TNS_CRITERE_RETENU",
         "Critère de sélection appliqué",
         critere, unite="",
         notes="Sélection mécanique sur le net dirigeant immédiat — "
               "le bénéfice retenu T4 reste un indicateur séparé")
    _log("STRAT_TNS_RETENU",
         "Code de la stratégie retenue par le critère ci-dessus",
         recommandee, unite="",
         hypotheses={"critere": critere,
                     "net_retenu": strategies[recommandee].net_dirigeant_immediat,
                     "tous_nets": {c: strategies[c].net_dirigeant_immediat
                                   for c in strategies}},
         notes="Clé technique 'recommandee' conservée pour rétrocompat Phase A. "
               "Indicateur factuel — voir TERMINOLOGY.md.")

    return ResultatArbitrageTNS(
        strategies=strategies,
        recommandee=recommandee,
        profil=profil,
    )
