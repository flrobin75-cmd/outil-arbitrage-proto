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
"""

from dataclasses import dataclass, field
from typing import Optional

from core.profil import Profil
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
def _ligne_assimile(profil: Profil) -> LigneRegime:
    """Ligne Assimilé : meilleure stratégie A/B/C/D."""
    arb = arbitrage_complet(profil)
    meilleur_code = arb["recommandee"]
    meilleur_strat = arb["strategies"][meilleur_code]

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


def _ligne_tns(profil: Profil) -> LigneRegime:
    """
    Ligne TNS : meilleure stratégie T1-T4 (net immédiat).

    GARDE-FOU T4 : benefice_retenu_societe affiché séparément, JAMAIS agrégé
    avec net_dirigeant.
    """
    arb = arbitrage_complet_tns(profil)
    meilleur_code = arb.recommandee
    meilleur_strat = arb.strategies[meilleur_code]

    alertes_ligne = list(meilleur_strat.alertes)
    # Si T4 meilleur, indication explicite
    if meilleur_code == "T4" and meilleur_strat.benefice_retenu_societe > 0:
        alertes_ligne.append(
            "T4 retenue : un montant supplémentaire est conservé en société "
            f"({meilleur_strat.benefice_retenu_societe:,.2f} €) — affiché séparément, "
            "non additionné au net dirigeant."
        )

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


def _ligne_liberal(profil: Profil) -> LigneRegime:
    """
    Ligne Libéral : stratégie la plus efficace fiscalement L1-L4.

    GARDE-FOU BNC/SEL : alerte permanente attachée à la ligne. Pas de
    formulation "recommandée".
    """
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
    if arb.avertissement_bnc_sel not in alertes_ligne and meilleur_code in ("L3", "L4"):
        alertes_ligne.insert(0, arb.avertissement_bnc_sel)

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


def _ligne_salarie(profil: Profil) -> LigneRegime:
    """
    Ligne Salarié : module détaillé (référence simple, Option A validée).

    Le Salarié n'a pas de Strategy Engine — sa ligne sert de référence
    comparative dans le Comparateur de régimes.
    """
    res = calcul_module_salarie(profil, salaire_brut=profil.salaire_brut_assimile)
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
def calcul_comparateur_regimes(profil: Profil) -> ResultatComparateurRegimes:
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
    """
    # Construction des 4 lignes
    lignes = [
        _ligne_assimile(profil),
        _ligne_tns(profil),
        _ligne_liberal(profil),
        _ligne_salarie(profil),
    ]

    # Identification du meilleur net (informatif uniquement, PAS "recommandé")
    meilleur_idx = max(range(len(lignes)), key=lambda i: lignes[i].net_dirigeant)
    meilleur_net_regime = lignes[meilleur_idx].regime

    return ResultatComparateurRegimes(
        profil=profil,
        lignes=lignes,
        meilleur_net=meilleur_net_regime,
        # Disclaimers attachés automatiquement par dataclass defaults
    )
