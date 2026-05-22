"""
Strategy Engine — Comparateur de régimes (Phase B.2 Étape 4b).

Page dédiée comparant les meilleurs nets dirigeants entre régimes pour
un même profil client :
- Assimilé : meilleure stratégie A/B/C/D
- TNS      : meilleure stratégie T1-T4 (net immédiat, bénéfice retenu T4 séparé)
- Libéral  : meilleure stratégie L1-L4 (terminologie "plus efficace fiscalement")
- Salarié  : module détaillé (référence simple)

────────────────────────────────────────────────────────────────────────
GARDE-FOUS MÉTHODOLOGIQUES CENTRAUX
────────────────────────────────────────────────────────────────────────

1. DISCLAIMER 1 — Changement de régime ≠ simple arbitrage net
   « Cette comparaison constitue un cadrage indicatif. Un changement de
     régime ne se résume pas à un écart de net : il suppose une analyse
     juridique, sociale, fiscale et patrimoniale complète. Les résultats
     affichés n'intègrent pas les coûts de transition, les formalités,
     ni les impacts éventuels liés à une restructuration. »

2. DISCLAIMER 2 — Comparabilité limitée des grandeurs
   « Les régimes sont comparés à partir d'hypothèses économiques
     rapprochées, mais non strictement équivalentes : coût société pour
     l'assimilé, bénéfice avant rémunération pour le TNS, recettes BNC
     pour le libéral, salaire brut pour le salarié. Les écarts doivent
     donc être interprétés comme des ordres de grandeur, et non comme
     une recommandation automatique de changement de statut. »

3. INTERDICTIONS strictes :
   - PAS de "régime recommandé" automatique
   - PAS de classement inter-régimes fondé sur le radar 6D
   - PAS d'agrégation T4 (net immédiat + bénéfice retenu séparés)
   - Alerte BNC/SEL systématique pour le Libéral
────────────────────────────────────────────────────────────────────────

Module : consomme core (profil) + strategy (assimile, tns, liberal) +
regime (salarie). Aucun import vers ui/* ou app.

MODE_AUDIT (G3d-bis, spec 1.1.0) :
- `_ligne_<regime>()` et `calcul_comparateur_regimes()` acceptent un
  paramètre opt-in `audit: TraceAudit | None`. Codes émis :
  `COMP_REG_*` (namespace dédié, distinct de `COMP_*` du comparateur
  de dispositifs G3d).
- Composition naturelle conformément à §9.2 du MODE_AUDIT : ce module
  appelle réellement les 3 stratégies G3a/b/c + le module Salarié G2a,
  donc il attache leurs traces comme sous-traces nommées :
    * `_ligne_assimile`  → sous-trace `arbitrage_assimile`
    * `_ligne_tns`       → sous-trace `arbitrage_tns`
    * `_ligne_liberal`   → sous-trace `arbitrage_liberal`
    * `_ligne_salarie`   → sous-trace `module_salarie`
- Au routeur, 4 sous-traces nommées `ligne_<regime>` agrégent ces appels.
- Profondeur d'imbrication maximale atteinte : 5 niveaux sur la branche
  `ligne_liberal → arbitrage_liberal → strategie_L4 → strategie_l3_deleguee
  → module_tns/salarie`.
- Discipline non-prescriptive renforcée : ce module est l'endroit du
  codebase au plus fort risque de prescription implicite (comparaison
  inter-régimes). Le critère méta est explicité par `COMP_REG_CRITERE_NET`
  ; le résultat sous `COMP_REG_NET_LE_PLUS_ELEVE` (terminologie factuelle,
  pas `RETENU` ni `MEILLEUR`). Tous les disclaimers (`DISCLAIMER_CHANGEMENT_REGIME`,
  `DISCLAIMER_COMPARABILITE`, `NOTE_RADAR_INTRA_REGIME`) et les notes
  source des helpers (qui contiennent le mot « meilleur » au sens
  rédactionnel) sont placés en `hypotheses` selon le pattern G3b/G3c.
"""

from dataclasses import dataclass, field
from typing import Optional

from core.profil import Profil
from core.audit import TraceAudit
from regime.salarie import calcul_module_salarie
from strategy.assimile import arbitrage_complet
from strategy.tns import arbitrage_complet_tns
from strategy.liberal import arbitrage_complet_liberal


# ============================================================
# DISCLAIMERS PERMANENTS (validés par l'utilisateur)
# ============================================================
DISCLAIMER_CHANGEMENT_REGIME = (
    "Cette comparaison constitue un cadrage indicatif. Un changement de régime "
    "ne se résume pas à un écart de net : il suppose une analyse juridique, "
    "sociale, fiscale et patrimoniale complète. Les résultats affichés n'intègrent "
    "pas les coûts de transition, les formalités, ni les impacts éventuels liés à "
    "une restructuration."
)

DISCLAIMER_COMPARABILITE = (
    "Les régimes sont comparés à partir d'hypothèses économiques rapprochées, "
    "mais non strictement équivalentes : coût société pour l'assimilé, bénéfice "
    "avant rémunération pour le TNS, recettes BNC pour le libéral, salaire brut "
    "pour le salarié. Les écarts doivent donc être interprétés comme des ordres "
    "de grandeur, et non comme une recommandation automatique de changement de "
    "statut."
)

# Note radar : le radar 6D ne doit PAS être utilisé pour classer entre régimes
NOTE_RADAR_INTRA_REGIME = (
    "Le radar 6D, lorsqu'il est affiché, reste un outil de comparaison "
    "INTRA-régime ou descriptif. Il ne doit pas être utilisé pour classer "
    "les régimes entre eux : les axes sont calibrés différemment selon le "
    "régime considéré."
)


# ============================================================
# DATACLASSES
# ============================================================
@dataclass
class LigneRegime:
    """Ligne du comparateur pour un régime donné."""
    regime: str                          # "Assimilé", "TNS", "Libéral BNC", "Libéral SEL", "Salarié"
    strategie_meilleur: str              # Code stratégie au meilleur net (ex: "D", "T2", "L3")
    nom_strategie: str                   # Libellé long
    net_dirigeant: float                 # Net du régime (= net dirigeant immédiat pour TNS)
    grandeur_entree: str                 # "Coût société", "Bénéfice IS", "Recettes BNC", "Salaire brut"
    montant_entree: float                # Valeur de la grandeur d'entrée
    # Champ spécifique T4 (jamais agrégé)
    benefice_retenu_societe: float = 0.0
    # Alertes propres au régime / à la stratégie retenue
    alertes: list = field(default_factory=list)
    # Indicateur informatif (PAS une recommandation)
    note: str = ""


@dataclass
class ResultatComparateurRegimes:
    """
    Résultat consolidé du Comparateur de régimes.

    IMPORTANT — terminologie :
    - 'meilleur_net' : régime au meilleur net dirigeant (informatif uniquement)
    - PAS de champ 'regime_recommande' (interdit méthodologique)
    - Les 2 disclaimers permanents sont systématiquement présents.
    """
    profil: Profil
    lignes: list                          # Liste de LigneRegime, une par régime testé
    meilleur_net: str                     # Régime au plus haut net dirigeant (INDICATIF)
    # Disclaimers permanents
    disclaimer_changement_regime: str = DISCLAIMER_CHANGEMENT_REGIME
    disclaimer_comparabilite: str = DISCLAIMER_COMPARABILITE
    note_radar: str = NOTE_RADAR_INTRA_REGIME


# ============================================================
# HELPERS — Construction d'une ligne par régime
# ============================================================
def _ligne_assimile(profil: Profil,
                    *,
                    audit: TraceAudit | None = None) -> LigneRegime:
    """Ligne Assimilé : meilleure stratégie A/B/C/D.

    Args:
        profil: Profil client.
        audit: Trace d'audit optionnelle (G3d-bis). Codes émis :
            `COMP_REG_ASSIM_*`. Attache une sous-trace `arbitrage_assimile`
            (codes `STRAT_ASSIM_*`).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("COMP_REG_ASSIM_" + suffixe, label, valeur, **kw)

    if audit is not None:
        sous_trace_arb = TraceAudit(
            regime="Stratégie Assimilé (appel depuis comparateur_regimes)",
            profil_resume=f"enveloppe={profil.enveloppe:.0f}",
        )
        arb = arbitrage_complet(profil, audit=sous_trace_arb)
        audit.attacher_sous_trace("arbitrage_assimile", sous_trace_arb)
    else:
        arb = arbitrage_complet(profil)
    meilleur_code = arb["recommandee"]
    meilleur_strat = arb["strategies"][meilleur_code]

    _log("REGIME", "Régime considéré pour cette ligne",
         "Assimilé salarié", unite="")
    _log("CODE_STRATEGIE_TOP_NET",
         "Code stratégie au plus haut total_net (depuis arbitrage Assimilé)",
         meilleur_code, unite="",
         notes="Détails dans sous-trace 'arbitrage_assimile'")
    _log("NET_DIRIGEANT",
         "Net dirigeant de la stratégie retenue",
         meilleur_strat["total_net"], unite="EUR",
         hypotheses={"strategie_appliquee": meilleur_code,
                     "nom_strategie": meilleur_strat["nom"],
                     "note_source": "Stratégie au meilleur net dirigeant parmi A/B/C/D"})
    _log("GRANDEUR_ENTREE",
         "Grandeur d'entrée caractéristique du régime (non équivalente aux autres régimes)",
         "Coût société (enveloppe)", unite="",
         notes="Comparabilité limitée — voir disclaimer_comparabilite au niveau méta")
    _log("MONTANT_ENTREE",
         "Montant de la grandeur d'entrée",
         profil.enveloppe, unite="EUR")
    _log("BENEFICE_RETENU_SOCIETE",
         "Bénéfice retenu en société (non applicable au régime Assimilé)",
         0.0, unite="EUR",
         hypotheses={"applicable": False,
                     "specifique_a": "TNS (stratégie T4 uniquement)"})
    _log("ALERTES_NB",
         "Nombre d'alertes de la stratégie retenue",
         0.0, unite="count")

    return LigneRegime(
        regime="Assimilé salarié",
        strategie_meilleur=meilleur_code,
        nom_strategie=meilleur_strat["nom"],
        net_dirigeant=meilleur_strat["total_net"],
        grandeur_entree="Coût société (enveloppe)",
        montant_entree=profil.enveloppe,
        benefice_retenu_societe=0.0,
        alertes=[],
        note="Stratégie au meilleur net dirigeant parmi A/B/C/D.",
    )


def _ligne_tns(profil: Profil,
               *,
               audit: TraceAudit | None = None) -> LigneRegime:
    """
    Ligne TNS : meilleure stratégie T1-T4 (net immédiat).

    GARDE-FOU T4 : benefice_retenu_societe affiché séparément, JAMAIS agrégé
    avec net_dirigeant.

    Args:
        profil: Profil client.
        audit: Trace d'audit optionnelle (G3d-bis). Codes émis :
            `COMP_REG_TNS_*`. Attache une sous-trace `arbitrage_tns`.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("COMP_REG_TNS_" + suffixe, label, valeur, **kw)

    if audit is not None:
        sous_trace_arb = TraceAudit(
            regime="Stratégie TNS (appel depuis comparateur_regimes)",
            profil_resume=f"benefice_is={profil.benefice_is:.0f}",
        )
        arb = arbitrage_complet_tns(profil, audit=sous_trace_arb)
        audit.attacher_sous_trace("arbitrage_tns", sous_trace_arb)
    else:
        arb = arbitrage_complet_tns(profil)
    meilleur_code = arb.recommandee
    meilleur_strat = arb.strategies[meilleur_code]

    alertes_ligne = list(meilleur_strat.alertes)
    # Si T4 meilleur, indication explicite (texte métier conservé en hypotheses)
    texte_alerte_t4_ajoute = None
    if meilleur_code == "T4" and meilleur_strat.benefice_retenu_societe > 0:
        texte_alerte_t4_ajoute = (
            f"T4 retenue : un montant supplémentaire est conservé en société "
            f"({meilleur_strat.benefice_retenu_societe:,.2f} €) — affiché séparément, "
            f"non additionné au net dirigeant."
        )
        alertes_ligne.append(texte_alerte_t4_ajoute)

    _log("REGIME", "Régime considéré pour cette ligne",
         "TNS", unite="")
    _log("CODE_STRATEGIE_TOP_NET",
         "Code stratégie au plus haut net_dirigeant_immediat (depuis arbitrage TNS)",
         meilleur_code, unite="",
         notes="Détails dans sous-trace 'arbitrage_tns'")
    _log("NET_DIRIGEANT",
         "Net dirigeant immédiat de la stratégie retenue",
         meilleur_strat.net_dirigeant_immediat, unite="EUR",
         hypotheses={"strategie_appliquee": meilleur_code,
                     "nom_strategie": meilleur_strat.nom,
                     "note_source": "Stratégie au meilleur net dirigeant immédiat parmi T1-T4"})
    _log("GRANDEUR_ENTREE",
         "Grandeur d'entrée caractéristique du régime",
         "Bénéfice avant rémunération (IS)", unite="",
         notes="Comparabilité limitée — voir disclaimer_comparabilite au niveau méta")
    _log("MONTANT_ENTREE",
         "Montant de la grandeur d'entrée",
         profil.benefice_is, unite="EUR")
    _log("BENEFICE_RETENU_SOCIETE",
         "Bénéfice retenu en société (indicateur SÉPARÉ, jamais agrégé avec net dirigeant)",
         meilleur_strat.benefice_retenu_societe, unite="EUR",
         hypotheses={"applicable": True,
                     "convention_t4": "non-agrégation",
                     "regle": "Ne PAS sommer avec net_dirigeant",
                     "actif_si_strategie_retenue": meilleur_code == "T4"},
         notes="Convention de non-agrégation T4 préservée au niveau ligne régime")
    _log("ALERTES_NB",
         "Nombre d'alertes attachées (alertes de la stratégie retenue + garde-fou T4 si applicable)",
         float(len(alertes_ligne)), unite="count",
         hypotheses={"textes_alertes": alertes_ligne,
                     "alerte_t4_ajoutee": texte_alerte_t4_ajoute is not None})

    return LigneRegime(
        regime="TNS",
        strategie_meilleur=meilleur_code,
        nom_strategie=meilleur_strat.nom,
        net_dirigeant=meilleur_strat.net_dirigeant_immediat,
        grandeur_entree="Bénéfice avant rémunération (IS)",
        montant_entree=profil.benefice_is,
        benefice_retenu_societe=meilleur_strat.benefice_retenu_societe,
        alertes=alertes_ligne,
        note="Stratégie au meilleur net dirigeant immédiat parmi T1-T4.",
    )


def _ligne_liberal(profil: Profil,
                   *,
                   audit: TraceAudit | None = None) -> LigneRegime:
    """
    Ligne Libéral : stratégie la plus efficace fiscalement L1-L4.

    GARDE-FOU BNC/SEL : alerte permanente attachée à la ligne. Pas de
    formulation "recommandée".

    Args:
        profil: Profil client.
        audit: Trace d'audit optionnelle (G3d-bis). Codes émis :
            `COMP_REG_LIB_*`. Attache une sous-trace `arbitrage_liberal`.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("COMP_REG_LIB_" + suffixe, label, valeur, **kw)

    if audit is not None:
        sous_trace_arb = TraceAudit(
            regime="Stratégie Libéral (appel depuis comparateur_regimes)",
            profil_resume=f"recettes_bnc={profil.recettes_bnc:.0f}, "
                          f"forme_sel={profil.forme_sel}",
        )
        arb = arbitrage_complet_liberal(profil, audit=sous_trace_arb)
        audit.attacher_sous_trace("arbitrage_liberal", sous_trace_arb)
    else:
        arb = arbitrage_complet_liberal(profil)
    meilleur_code = arb.plus_efficace_fiscalement  # PAS "recommandee"
    meilleur_strat = arb.strategies[meilleur_code]

    # Adapter le libellé de régime selon la structure
    if meilleur_strat.structure == "BNC":
        regime_label = "Libéral BNC"
    else:
        regime_label = f"Libéral SEL ({profil.forme_sel})"

    # Reprendre les alertes de la stratégie (BNC/SEL pour L3/L4, v2 pour L4)
    alertes_ligne = list(meilleur_strat.alertes)
    # Ajouter systématiquement l'avertissement de l'arbitrage (au cas où L1/L2)
    avert_ajoute_explicitement = False
    if arb.avertissement_bnc_sel not in alertes_ligne and meilleur_code in ("L3", "L4"):
        alertes_ligne.insert(0, arb.avertissement_bnc_sel)
        avert_ajoute_explicitement = True

    _log("REGIME", "Régime considéré pour cette ligne (libellé dynamique selon structure)",
         regime_label, unite="",
         hypotheses={"structure_appliquee": meilleur_strat.structure,
                     "forme_sel_profil": profil.forme_sel})
    _log("CODE_STRATEGIE_PLUS_EFFICACE",
         "Code stratégie au plus haut net_dirigeant_total (depuis arbitrage Libéral)",
         meilleur_code, unite="",
         notes="Détails dans sous-trace 'arbitrage_liberal'. "
               "Terminologie spécifique Libéral — voir doctrine module §36-38.")
    _log("NET_DIRIGEANT",
         "Net dirigeant total de la stratégie retenue",
         meilleur_strat.net_dirigeant_total, unite="EUR",
         hypotheses={"strategie_appliquee": meilleur_code,
                     "nom_strategie": meilleur_strat.nom,
                     "note_source": "Stratégie la plus efficace fiscalement parmi L1-L4 "
                                    "(non recommandée)"})
    _log("GRANDEUR_ENTREE",
         "Grandeur d'entrée caractéristique du régime",
         "Recettes BNC (CA libéral)", unite="",
         notes="Comparabilité limitée — voir disclaimer_comparabilite au niveau méta")
    _log("MONTANT_ENTREE",
         "Montant de la grandeur d'entrée",
         profil.recettes_bnc, unite="EUR")
    _log("BENEFICE_RETENU_SOCIETE",
         "Bénéfice retenu en société (non applicable au régime Libéral en v1)",
         0.0, unite="EUR",
         hypotheses={"applicable": False,
                     "convention_v1": "Distribution intégrale post-IS pour les stratégies SEL",
                     "alternative": "Voir T4 (TNS Strategy) pour rétention"})
    _log("ALERTES_NB",
         "Nombre d'alertes attachées (alertes de la stratégie retenue + avertissement BNC/SEL si L3/L4)",
         float(len(alertes_ligne)), unite="count",
         hypotheses={"textes_alertes": alertes_ligne,
                     "avertissement_bnc_sel_ajoute_explicitement": avert_ajoute_explicitement,
                     "code_strategie_concernee": meilleur_code})

    return LigneRegime(
        regime=regime_label,
        strategie_meilleur=meilleur_code,
        nom_strategie=meilleur_strat.nom,
        net_dirigeant=meilleur_strat.net_dirigeant_total,
        grandeur_entree="Recettes BNC (CA libéral)",
        montant_entree=profil.recettes_bnc,
        benefice_retenu_societe=0.0,
        alertes=alertes_ligne,
        # PAS de formulation "recommandée" — utiliser "plus efficace fiscalement"
        note="Stratégie la plus efficace fiscalement parmi L1-L4 (non recommandée).",
    )


def _ligne_salarie(profil: Profil,
                   *,
                   audit: TraceAudit | None = None) -> LigneRegime:
    """
    Ligne Salarié : module détaillé (référence simple, Option A validée).

    Le Salarié n'a pas de Strategy Engine — sa ligne sert de référence
    comparative dans le Comparateur de régimes.

    Args:
        profil: Profil client.
        audit: Trace d'audit optionnelle (G3d-bis). Codes émis :
            `COMP_REG_SAL_*`. Attache une sous-trace `module_salarie`.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("COMP_REG_SAL_" + suffixe, label, valeur, **kw)

    if audit is not None:
        sous_trace_sal = TraceAudit(
            regime="Salarié (appel depuis comparateur_regimes, référence)",
            profil_resume=f"salaire_brut_assimile={profil.salaire_brut_assimile:.0f}",
        )
        res = calcul_module_salarie(profil,
                                    salaire_brut=profil.salaire_brut_assimile,
                                    audit=sous_trace_sal)
        audit.attacher_sous_trace("module_salarie", sous_trace_sal)
    else:
        res = calcul_module_salarie(profil, salaire_brut=profil.salaire_brut_assimile)

    _log("REGIME", "Régime considéré pour cette ligne",
         "Salarié (référence)", unite="")
    _log("CODE_STRATEGIE_TOP_NET",
         "Code stratégie (—) — pas de Strategy Engine appliqué au Salarié",
         "—", unite="",
         hypotheses={"justification": "Le salarié non dirigeant n'a pas d'enveloppe à arbitrer",
                     "note_source": "Référence salariale, pas de Strategy Engine"})
    _log("NET_DIRIGEANT",
         "Net après impôts (depuis module Salarié, valeur de référence)",
         res.net_apres_impots, unite="EUR",
         notes="Détails dans sous-trace 'module_salarie'")
    _log("GRANDEUR_ENTREE",
         "Grandeur d'entrée caractéristique du régime",
         "Salaire brut", unite="",
         notes="Comparabilité limitée — voir disclaimer_comparabilite au niveau méta")
    _log("MONTANT_ENTREE",
         "Montant de la grandeur d'entrée",
         profil.salaire_brut_assimile, unite="EUR")
    _log("BENEFICE_RETENU_SOCIETE",
         "Bénéfice retenu en société (non applicable au régime Salarié)",
         0.0, unite="EUR",
         hypotheses={"applicable": False})
    _log("ALERTES_NB",
         "Nombre d'alertes (aucune pour la référence Salarié)",
         0.0, unite="count")

    return LigneRegime(
        regime="Salarié (référence)",
        strategie_meilleur="—",
        nom_strategie="Salarié non dirigeant (référence)",
        net_dirigeant=res.net_apres_impots,
        grandeur_entree="Salaire brut",
        montant_entree=profil.salaire_brut_assimile,
        benefice_retenu_societe=0.0,
        alertes=[],
        note="Référence salariale. Pas de Strategy Engine appliqué : "
             "le salarié non-dirigeant n'a pas d'enveloppe à arbitrer.",
    )


# ============================================================
# API PRINCIPALE
# ============================================================
def calcul_comparateur_regimes(profil: Profil,
                               *,
                               audit: TraceAudit | None = None) -> ResultatComparateurRegimes:
    """
    Compare les meilleurs nets dirigeants entre régimes pour un même profil.

    Calcule pour chaque régime :
    - la stratégie au meilleur net (selon les conventions du régime)
    - le net dirigeant correspondant
    - les alertes propres
    - les grandeurs d'entrée (non équivalentes entre régimes)

    Returns :
        ResultatComparateurRegimes avec 4 lignes (Assimilé/TNS/Libéral/Salarié)
        + 2 disclaimers permanents + note radar intra-régime.

    Args:
        profil: Profil client.
        audit: Trace d'audit optionnelle (MODE_AUDIT G3d-bis). Side channel.
            Codes émis : `COMP_REG_*` (méta). Attache 4 sous-traces nommées
            `ligne_assimile`, `ligne_tns`, `ligne_liberal`, `ligne_salarie`,
            qui contiennent elles-mêmes des sous-traces régime ou stratégie
            instrumentées (jusqu'à 5 niveaux d'imbrication sur la branche
            ligne_liberal → arbitrage_liberal → strategie_L4 →
            strategie_l3_deleguee → module_tns/salarie).
    """
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    # --- Construction des 4 lignes (chacune dans sa sous-trace) ---
    lignes = []
    for nom_attach, fn in (("ligne_assimile", _ligne_assimile),
                            ("ligne_tns", _ligne_tns),
                            ("ligne_liberal", _ligne_liberal),
                            ("ligne_salarie", _ligne_salarie)):
        if audit is not None:
            sous_ligne = TraceAudit(
                regime=f"Comparateur régimes — {nom_attach}",
                profil_resume=f"enveloppe={profil.enveloppe:.0f}, "
                              f"benefice_is={profil.benefice_is:.0f}",
            )
            lignes.append(fn(profil, audit=sous_ligne))
            audit.attacher_sous_trace(nom_attach, sous_ligne)
        else:
            lignes.append(fn(profil))

    # --- Identification du net le plus élevé (informatif, PAS prescriptif) ---
    meilleur_idx = max(range(len(lignes)), key=lambda i: lignes[i].net_dirigeant)
    meilleur_net_regime = lignes[meilleur_idx].regime

    # --- Trace méta : disclaimers, critère, garde-fou T4, net le plus élevé ---
    _log("COMP_REG_NB_LIGNES",
         "Nombre de lignes régimes construites",
         float(len(lignes)), unite="count",
         hypotheses={"regimes_couverts": [l.regime for l in lignes]})

    # Disclaimers permanents : textes intégraux en hypotheses (pattern G3b/G3c)
    _log("COMP_REG_DISCLAIMERS_NB",
         "Nombre de disclaimers permanents attachés au résultat",
         3.0, unite="count",
         hypotheses={
             "DISCLAIMER_CHANGEMENT_REGIME": DISCLAIMER_CHANGEMENT_REGIME,
             "DISCLAIMER_COMPARABILITE": DISCLAIMER_COMPARABILITE,
             "NOTE_RADAR_INTRA_REGIME": NOTE_RADAR_INTRA_REGIME,
         },
         notes="Wording métier intégral préservé en hypotheses — pattern G3b/G3c "
               "appliqué pour ne pas polluer label/notes")

    # Garde-fou T4 : indicateur séparé, jamais agrégé
    ligne_tns_obj = next(l for l in lignes if l.regime == "TNS")
    _log("COMP_REG_INDICATEURS_SEPARES_T4",
         "Bénéfice retenu T4 (indicateur séparé, jamais agrégé au critère de classement)",
         ligne_tns_obj.benefice_retenu_societe, unite="EUR",
         hypotheses={"convention": "non-agrégation T4 (transversale aux niveaux)",
                     "applicable_a_la_ligne_retenue": ligne_tns_obj.strategie_meilleur == "T4",
                     "regle": "Ne PAS sommer avec net_dirigeant pour le classement",
                     "code_strategie_tns_retenue": ligne_tns_obj.strategie_meilleur},
         notes="Convention de non-agrégation T4 transversale au comparateur "
               "régimes (héritée du module TNS)")

    # Critère de classement + résultat
    critere = "max(net_dirigeant)"
    _log("COMP_REG_CRITERE_NET",
         "Critère de classement inter-régimes appliqué",
         critere, unite="",
         notes="Classement mécanique sur le net dirigeant. Comparabilité "
               "limitée entre régimes — interprétation par l'EC, voir disclaimers.")
    _log("COMP_REG_NET_LE_PLUS_ELEVE",
         "Régime au net dirigeant le plus élevé (indicateur factuel)",
         meilleur_net_regime, unite="",
         hypotheses={"critere": critere,
                     "net_calcule": lignes[meilleur_idx].net_dirigeant,
                     "tous_nets": {l.regime: l.net_dirigeant for l in lignes},
                     "convention_terminologique": "NET_LE_PLUS_ELEVE (factuel)",
                     "interdiction_doctrinale": "Pas de champ 'regime_recommande' (cf. doctrine §30-34)"},
         notes="Indicateur factuel. Ne constitue pas un avis sur le choix de régime — "
               "voir disclaimer_changement_regime au niveau méta.")

    return ResultatComparateurRegimes(
        profil=profil,
        lignes=lignes,
        meilleur_net=meilleur_net_regime,
        # Disclaimers attachés automatiquement par dataclass defaults
    )
