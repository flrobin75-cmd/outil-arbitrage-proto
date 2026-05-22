"""
Moteur Synthèse dirigeant - livrable consulting-grade pour EC.

Périmètre v1 Phase A : régime Assimilé salarié uniquement (cohérent avec Arbitrage v1).
Les autres régimes (TNS / Libéral / Salarié) afficheront une note de bascule v2.

Décisions structurantes :
- Radar 6D pédagogique (axes renommés, scoring pondéré pour Protection sociale)
- Forfaits cabinet éditables avec toggle actif/inactif
- Bloc patrimonial compact + drill-down vers page dédiée
- Vocabulaire dirigeant (pas EC) dans les messages principaux
- Réutilisation des alertes du Comparateur Option 2 (factorisation)

Date de dernière mise à jour réglementaire : 01/01/2026.
"""

from dataclasses import dataclass, field
from typing import Optional
from core.profil import Profil, PASS_2026
from strategy.comparateur import AlertePlafond, PLAF_ABO_PEE, PLAF_ABO_PERECO


# ============================================================
# FORFAITS CABINET PAR DÉFAUT (éditables côté UI)
# ============================================================
@dataclass
class ForfaitCabinet:
    """Un poste de coût cabinet, éditable avec toggle actif/inactif."""
    libelle: str
    montant_defaut: float
    montant: float
    actif: bool = True
    condition: str = ""    # Note de condition d'affichage

    def reset(self):
        """Réinitialise au montant par défaut."""
        self.montant = self.montant_defaut


FORFAITS_DEFAUT = {
    "cadrage": ForfaitCabinet("Mission cabinet — cadrage stratégique",
                              1200, 1200, True, "Forfait initial"),
    "interessement": ForfaitCabinet("Mise en place accord intéressement",
                                    800, 800, True, "Si intéressement activé"),
    "pee_per": ForfaitCabinet("Mise en place règlement PEE / PER",
                              1500, 1500, True, "Si PEE ou PER collectif activé"),
    "pero": ForfaitCabinet("Mise en place PERO (catégorie objective)",
                           1200, 1200, True, "Si PERO activé"),
    "teneur_compte_petit": ForfaitCabinet("Frais teneur de compte PEE/PER (annuel)",
                                          600, 600, True, "Si effectif ≤49 salariés"),
    "teneur_compte_grand": ForfaitCabinet("Frais teneur de compte PEE/PER (annuel)",
                                          1200, 1200, True, "Si effectif ≥50 salariés"),
    "audit_peripheriques": ForfaitCabinet("Audit conformité périphériques (TR, CESU, AN)",
                                          600, 600, True, "Si C+ et périphériques activés"),
    "audit_cashback": ForfaitCabinet("Audit cashback mode Conforme",
                                     900, 900, True, "Si cashback Conforme"),
}


def reset_forfaits(forfaits: dict) -> dict:
    """Réinitialise tous les forfaits aux valeurs par défaut."""
    for forfait in forfaits.values():
        forfait.reset()
    return forfaits


# ============================================================
# CALCUL A — COÛTS DE MISE EN ŒUVRE
# ============================================================
@dataclass
class CoutMiseEnOeuvre:
    libelle: str
    montant: float
    note: str


def calcul_couts_mise_en_oeuvre(profil: Profil,
                                strategie_retenue: str,
                                forfaits: dict,
                                config_comparateur=None) -> list:
    """
    Calcule la liste des postes de coûts cabinet applicables.

    Args:
        profil: Profil client
        strategie_retenue: "A", "B", "C" ou "D"
        forfaits: Dict des forfaits cabinet (éditables)
        config_comparateur: ConfigComparateur si disponible (pour conditions)

    Returns:
        Liste de CoutMiseEnOeuvre filtrée selon conditions d'applicabilité.
    """
    couts = []

    # Toujours présent
    if forfaits["cadrage"].actif:
        couts.append(CoutMiseEnOeuvre(
            forfaits["cadrage"].libelle,
            forfaits["cadrage"].montant,
            "Inclut audit du dossier et restitution client"
        ))

    # Conditions selon stratégie + activation dispositifs
    # Stratégie A : aucun dispositif → seul le cadrage
    if strategie_retenue == "A":
        return couts

    # Stratégie B et + : épargne salariale potentielle
    if config_comparateur:
        # Intéressement
        if (forfaits["interessement"].actif
                and config_comparateur.interessement.actif):
            couts.append(CoutMiseEnOeuvre(
                forfaits["interessement"].libelle,
                forfaits["interessement"].montant,
                "Rédaction de l'accord + dépôt DDETSPP + information salariés"
            ))

        # PEE / PER collectif
        if (forfaits["pee_per"].actif
                and (config_comparateur.abondement_pee.actif
                     or config_comparateur.abondement_pereco.actif
                     or config_comparateur.participation.actif)):
            couts.append(CoutMiseEnOeuvre(
                forfaits["pee_per"].libelle,
                forfaits["pee_per"].montant,
                "Conventionnement teneur de compte + rédaction règlement"
            ))

            # Frais teneur de compte selon effectif
            effectif_petit = profil.effectif in ["Sans salarié", "1-10 salariés",
                                                  "11-49 salariés"]
            if effectif_petit and forfaits["teneur_compte_petit"].actif:
                couts.append(CoutMiseEnOeuvre(
                    forfaits["teneur_compte_petit"].libelle,
                    forfaits["teneur_compte_petit"].montant,
                    "Frais récurrents selon prestataire"
                ))
            elif not effectif_petit and forfaits["teneur_compte_grand"].actif:
                couts.append(CoutMiseEnOeuvre(
                    forfaits["teneur_compte_grand"].libelle,
                    forfaits["teneur_compte_grand"].montant,
                    "Frais récurrents selon prestataire"
                ))

        # PERO
        if forfaits["pero"].actif and config_comparateur.pero_actif and config_comparateur.dirigeant_eligible_pero:
            couts.append(CoutMiseEnOeuvre(
                forfaits["pero"].libelle,
                forfaits["pero"].montant,
                "Définition catégorie objective + accord + dépôt URSSAF"
            ))

    # Stratégie C+ : périphériques
    if strategie_retenue in ["C", "D"] and config_comparateur:
        if forfaits["audit_peripheriques"].actif and (
                config_comparateur.tr_actif or config_comparateur.cesu_actif
                or config_comparateur.avantages_actif):
            couts.append(CoutMiseEnOeuvre(
                forfaits["audit_peripheriques"].libelle,
                forfaits["audit_peripheriques"].montant,
                "Vérification plafonds + politique RH + bulletins de paie"
            ))

    # Stratégie D : cashback éventuel
    if (strategie_retenue == "D" and config_comparateur
            and config_comparateur.cashback_actif
            and forfaits["audit_cashback"].actif):
        couts.append(CoutMiseEnOeuvre(
            forfaits["audit_cashback"].libelle,
            forfaits["audit_cashback"].montant,
            "Note méthodologique + suivi + archivage"
        ))

    return couts


# ============================================================
# CALCUL B — RADAR 6D PÉDAGOGIQUE
# ============================================================
@dataclass
class ScoreRadar:
    """Score d'une stratégie sur les 6 axes du radar."""
    nom_strategie: str           # "A", "B", "C", "D"
    net_dirigeant: float          # 0-100
    protection_sociale: float     # 0-100
    fiscalite: float              # 0-100
    preparation_retraite: float   # 0-100
    liquidite: float              # 0-100
    maitrise_charges: float       # 0-100


# Pondérations Protection sociale (validation utilisateur)
# Salaire ouvre tous les droits, PERO crée retraite, épargne sal. très limitée,
# dividendes/cashback ne créent aucun droit social
PONDS_PROTECTION = {
    "salaire": 1.0,
    "pero": 0.6,
    "epargne_salariale": 0.3,
    "dividendes": 0.1,
    "cashback": 0.0,
}


def calcul_radar_6d(strategies: dict) -> list:
    """
    Calcule les scores des 4 stratégies sur les 6 axes du radar.

    Args:
        strategies: Dict {"A": dict, "B": dict, ...} avec pour chaque stratégie :
            - total_net : net total dirigeant
            - cout_total : coût société
            - net_salaire, net_dividendes, net_epargne, net_peripheriques
            - cout_salaire, cout_dividendes, cout_epargne, cout_peripheriques
            - net_pero (0 par défaut, > 0 si PERO activé)
            - net_cashback (0 par défaut)

    Returns:
        Liste de ScoreRadar (un par stratégie).
    """
    net_max = max(s["total_net"] for s in strategies.values())
    scores = []

    for code, s in strategies.items():
        # 1. Net dirigeant - score relatif au net max
        net_dirigeant = (s["total_net"] / net_max * 100) if net_max > 0 else 0

        # 2. Protection sociale - score pondéré
        # Décomposition fictive : net_salaire / net_pero / net_epargne / net_div / net_cashback
        # Si net_pero non fourni, on suppose 0 (cohérent v1 sans PERO dans Arbitrage)
        net_pero = s.get("net_pero", 0)
        net_cashback = s.get("net_cashback", 0)
        protection_brute = (
            s["net_salaire"] * PONDS_PROTECTION["salaire"]
            + net_pero * PONDS_PROTECTION["pero"]
            + s["net_epargne"] * PONDS_PROTECTION["epargne_salariale"]
            + s["net_dividendes"] * PONDS_PROTECTION["dividendes"]
            + net_cashback * PONDS_PROTECTION["cashback"]
        )
        # Normalisation : score max possible si tout en salaire pur
        protection_max_possible = s["total_net"] * PONDS_PROTECTION["salaire"]
        protection_sociale = ((protection_brute / protection_max_possible * 100)
                              if protection_max_possible > 0 else 0)

        # 3. Fiscalité - 100 - (ce qui sort en impôts et cotis) / coût total
        depenses_fiscales = s["cout_total"] - s["total_net"]
        fiscalite = ((1 - depenses_fiscales / s["cout_total"]) * 100
                     if s["cout_total"] > 0 else 0)

        # 4. Préparation retraite - part de l'épargne capitalisable
        retraite_brute = s["net_epargne"] + net_pero
        preparation_retraite = ((retraite_brute / s["total_net"] * 100)
                                if s["total_net"] > 0 else 0)

        # 5. Liquidité - part immédiatement disponible
        liquidite_brute = s["net_salaire"] + s["net_dividendes"]
        liquidite = ((liquidite_brute / s["total_net"] * 100)
                     if s["total_net"] > 0 else 0)

        # 6. Maîtrise des charges - 100 - cotisations / coût total
        # Cotisations = coût total - net brut allocations (i.e. ce qui part en cotis sociales/IS)
        # Approximation : cotisations = total société - somme des montants nets allocations
        # Plus simple : on inverse la fiscalité partiellement
        # Approche pragmatique : on calcule la part "non charges sociales" du coût
        # Dans la stratégie A (100% salaire), les charges sont max
        # Dans la stratégie D (mix avec exonérés), les charges sont min
        # Formule : 100 - (charges sociales / coût total × 100)
        # Charges sociales = coût salaire - net salaire avant IR (estimation)
        # Approximation simple : charges sociales = coût salaire × ratio cotisations
        # Pour l'Arbitrage Assimilé, ratio cotisations ≈ (TX_PATRONAL + TX_SALARIAL × (1-TX_PATRONAL)) ≈ 51%
        # On utilise une approche structurelle : part du coût total qui n'est pas alloué
        # à salaire pur (donc moins de cotisations sociales)
        cout_salaire = s.get("cout_salaire", 0)
        # Estimation des cotisations sociales : ~51 % du coût salaire (TX_PAT 42% + TX_SAL 12% sur 70 %)
        # Pour les autres allocations (dividendes, épargne, périphériques), les cotisations
        # sont marginales ou nulles
        cotisations_estimees = cout_salaire * 0.51
        maitrise_charges = ((1 - cotisations_estimees / s["cout_total"]) * 100
                            if s["cout_total"] > 0 else 0)

        scores.append(ScoreRadar(
            nom_strategie=code,
            net_dirigeant=net_dirigeant,
            protection_sociale=protection_sociale,
            fiscalite=fiscalite,
            preparation_retraite=preparation_retraite,
            liquidite=liquidite,
            maitrise_charges=maitrise_charges,
        ))

    return scores


# ============================================================
# CALCUL C — PROJECTION PATRIMOINE 5 ANS
# ============================================================
def calcul_projection_5_ans(strategies: dict, code_retenue: str = "C") -> dict:
    """
    Projection patrimoine cumulé sur 5 ans pour stratégie A vs retenue.

    Hypothèses :
    - Net cash réinvesti en cash défensif (rdt 2 %)
    - Net épargne salariale & PER capitalisé à 4 %
    - Capitalisation annuelle composée, versement en début d'année
    """
    RDT_CASH = 0.02
    RDT_EPARGNE = 0.04

    def projection_strategie(s, fraction_capitalisable_implicite=0.0):
        """Projection sur 5 ans d'une stratégie."""
        net = s["total_net"]
        # Si l'info net_epargne est dispo, on l'utilise pour fraction réelle
        if s.get("net_epargne", 0) > 0:
            fraction = s["net_epargne"] / net
        else:
            fraction = fraction_capitalisable_implicite

        annees = []
        for annee in range(1, 6):
            # Capitalisation cash défensif
            valeur_cash = net * (1 - fraction) * ((1 + RDT_CASH) ** annee - 1) / RDT_CASH * (1 + RDT_CASH)
            # Capitalisation épargne
            valeur_epargne = net * fraction * ((1 + RDT_EPARGNE) ** annee - 1) / RDT_EPARGNE * (1 + RDT_EPARGNE)
            annees.append(valeur_cash + valeur_epargne)
        return annees

    proj_a = projection_strategie(strategies["A"])
    proj_retenue = projection_strategie(strategies[code_retenue])
    ecarts = [r - a for r, a in zip(proj_retenue, proj_a)]

    return {
        "annees": list(range(1, 6)),
        "strategie_a": proj_a,
        "strategie_retenue": proj_retenue,
        "code_retenue": code_retenue,
        "ecarts": ecarts,
        "gain_5_ans": ecarts[-1],
    }


# ============================================================
# CALCUL D — DÉCOMPOSITION DU GAIN vs A (WATERFALL)
# ============================================================
@dataclass
class EtapeWaterfall:
    libelle: str
    net_dirigeant: float
    contribution: float    # vs étape précédente
    cumul_vs_a: float       # cumul vs stratégie A


def calcul_decomposition_gain(strategies: dict) -> list:
    """Construit la décomposition incrémentale A → B → C → D."""
    ordre = ["A", "B", "C", "D"]
    etapes = []
    net_precedent = strategies["A"]["total_net"]
    net_a = strategies["A"]["total_net"]

    libelles = {
        "A": "Stratégie A — Référence salaire",
        "B": "+ Allocation dividendes",
        "C": "+ Épargne salariale & PER",
        "D": "+ Périphériques & cashback",
    }

    for code in ordre:
        net = strategies[code]["total_net"]
        contribution = net - net_precedent if code != "A" else 0
        cumul = net - net_a
        etapes.append(EtapeWaterfall(
            libelle=libelles[code],
            net_dirigeant=net,
            contribution=contribution,
            cumul_vs_a=cumul,
        ))
        net_precedent = net

    return etapes


# ============================================================
# CALCUL E — ENVELOPPES PATRIMONIALES (bloc compact + détail)
# ============================================================
@dataclass
class EnveloppePatrimoniale:
    nom: str
    versement: float
    valeur_brute: float
    fiscalite_sortie: str
    net_disponible: float
    avantage_cle: str


def calcul_enveloppes_patrimoniales(montant: float = 10_000,
                                     horizon: int = 5,
                                     rendement: float = 0.05,
                                     situation: str = "Marié / pacsé") -> dict:
    """
    Calcule la performance fiscale comparée de 4 enveloppes patrimoniales.

    Args:
        montant: Capital initial placé
        horizon: Horizon de placement (années)
        rendement: Rendement annuel brut (ex: 0.05 = 5 %)
        situation: "Marié / pacsé" ou "Célibataire / divorcé / veuf"
    """
    TX_PFU = 0.314
    PS_TAUX = 0.172
    PFU_AV_REDUIT = 0.075
    ABATTEMENT_AV = 9_200 if situation == "Marié / pacsé" else 4_600

    valeur_brute = montant * (1 + rendement) ** horizon
    plus_value = valeur_brute - montant

    # CTO - PFU 31,4 % sur PV
    net_cto = montant + plus_value * (1 - TX_PFU)

    # PEA - après 5 ans exo IR + PS 17,2 % sur PV
    if horizon >= 5:
        net_pea = montant + plus_value * (1 - PS_TAUX)
    else:
        net_pea = montant + plus_value * (1 - TX_PFU)

    # Assurance-vie - après 8 ans : abattement + PFU réduit + PS
    if horizon >= 8:
        pv_taxable = max(0, plus_value - ABATTEMENT_AV)
        net_av = montant + plus_value * (1 - PS_TAUX) - pv_taxable * PFU_AV_REDUIT
    else:
        # Avant 8 ans : PFU classique
        net_av = montant + plus_value * (1 - TX_PFU)

    # PER individuel - sortie en capital : IR barème sortie + PS sur PV
    # Hypothèse : TMI moyen estimé à 30 % à la sortie (à affiner via TMI réel)
    tmi_sortie = 0.30
    net_per = valeur_brute * (1 - tmi_sortie) - plus_value * PS_TAUX

    enveloppes = [
        EnveloppePatrimoniale(
            nom="CTO — Compte-titres ordinaire",
            versement=montant, valeur_brute=valeur_brute,
            fiscalite_sortie="PFU 31,4 % sur les gains",
            net_disponible=net_cto,
            avantage_cle="Liquidité totale",
        ),
        EnveloppePatrimoniale(
            nom="PEA — après 5 ans",
            versement=montant, valeur_brute=valeur_brute,
            fiscalite_sortie="Exo IR sur PV, PS 17,2 %",
            net_disponible=net_pea,
            avantage_cle="Exo IR après 5 ans",
        ),
        EnveloppePatrimoniale(
            nom="Assurance-vie — après 8 ans",
            versement=montant, valeur_brute=valeur_brute,
            fiscalite_sortie=f"Abattement {ABATTEMENT_AV:,.0f} € + PFU 7,5 % + PS 17,2 %".replace(",", " "),
            net_disponible=net_av,
            avantage_cle="Transmission privilégiée",
        ),
        EnveloppePatrimoniale(
            nom="PER individuel — sortie capital",
            versement=montant, valeur_brute=valeur_brute,
            fiscalite_sortie="IR barème sortie sur capital + PS 17,2 % sur gains",
            net_disponible=net_per,
            avantage_cle="Économie IR à l'entrée",
        ),
    ]

    # Meilleure enveloppe
    meilleure = max(enveloppes, key=lambda e: e.net_disponible)

    return {
        "enveloppes": enveloppes,
        "meilleure": meilleure.nom,
        "hypothese_texte": (f"Hypothèse : rendement annuel moyen {rendement*100:.0f} %, "
                            f"fiscalité en vigueur au 01/01/2026."),
    }


# ============================================================
# CALCUL F — CHECK-LIST CONFORMITÉ FACTORISÉE
# ============================================================
@dataclass
class PointControle:
    libelle: str
    statut: str       # "✅", "⚠", "🔴", "-"
    action: str       # Texte à afficher si statut ≠ ✅


def calcul_checklist_conformite(profil: Profil,
                                config_comparateur,
                                strategie_retenue: str,
                                alertes_comparateur: list) -> list:
    """
    Construit la check-list de conformité de la stratégie retenue.

    Factorisation : on réutilise les alertes du Comparateur Option 2 et on ajoute
    les checks spécifiques v19 manquants (accord intéressement, règlement PEE).

    Args:
        profil: Profil client
        config_comparateur: ConfigComparateur
        strategie_retenue: "A", "B", "C" ou "D"
        alertes_comparateur: Liste d'AlertePlafond du Comparateur

    Returns:
        Liste de PointControle.
    """
    points = []

    # Seules les stratégies B+ activent des dispositifs
    if strategie_retenue == "A":
        points.append(PointControle(
            "Stratégie A — référence salaire pur",
            "-",
            "Aucun dispositif à mettre en place"
        ))
        return points

    # 1. Conversion des alertes du Comparateur en points de contrôle
    for alerte in alertes_comparateur:
        if alerte.severite == "error":
            points.append(PointControle(alerte.titre, "🔴", alerte.message))
        elif alerte.severite == "warning":
            points.append(PointControle(alerte.titre, "⚠", alerte.message))
        # severité "info" : on ne crée pas de point de contrôle (informatif uniquement)

    # 2. Checks v19 spécifiques non couverts par le Comparateur

    # 2a - Effectif compatible avec participation obligatoire
    if config_comparateur.participation.actif:
        effectif_petit = profil.effectif in ["Sans salarié", "1-10 salariés",
                                              "11-49 salariés"]
        if effectif_petit:
            points.append(PointControle(
                "Effectif compatible avec dispositif participation",
                "⚠",
                "Participation obligatoire à partir de 50 salariés. "
                "Mise en place facultative en dessous (encouragée)."
            ))
        else:
            points.append(PointControle(
                "Effectif compatible avec dispositif participation",
                "✅",
                ""
            ))

    # 2b - Accord d'intéressement formalisé (vigilance ≥ 3 ans)
    if config_comparateur.interessement.actif:
        points.append(PointControle(
            "Accord d'intéressement formalisé ≥ 3 ans",
            "⚠",
            "Vérifier l'existence d'un accord triennal déposé à la DDETSPP. "
            "À défaut : à mettre en place."
        ))

    # 2c - Règlement PEE déposé et information salariés
    if (config_comparateur.abondement_pee.actif
            or config_comparateur.participation.actif):
        points.append(PointControle(
            "Règlement PEE déposé et information salariés",
            "⚠",
            "Vérifier dépôt règlement PEE et livret épargne salariale remis."
        ))

    # 2d - Ratio dividendes / capital social pour TNS gérant maj.
    if ("TNS" in profil.regime_social
            and profil.dividendes_foyer_hors_enveloppe > 0):
        points.append(PointControle(
            "Ratio dividendes / capital social (TNS gérant maj.)",
            "⚠",
            "Dividendes > 10 % du capital + primes + CCA soumis à cotisations TNS. "
            "Vérifier le seuil dans le module TNS."
        ))

    # 2e - PERO catégorie objective (point spécifique Option 2)
    if config_comparateur.pero_actif and config_comparateur.dirigeant_eligible_pero:
        points.append(PointControle(
            "PERO — Catégorie objective formalisée",
            "⚠",
            "Vérifier que la catégorie objective éligible PERO est définie par "
            "accord d'entreprise / référendum / DUE (décision unilatérale)."
        ))

    return points


# ============================================================
# AVERTISSEMENT RADAR (texte validé)
# ============================================================
AVERTISSEMENT_RADAR = (
    "Ce radar est un comparateur indicatif destiné à visualiser les équilibres "
    "entre stratégies. Les scores sont calculés à partir de ratios simplifiés "
    "et ne remplacent pas une analyse personnalisée."
)


# ============================================================
# SYNTHÈSE GLOBALE - ASSEMBLAGE FINAL
# ============================================================
@dataclass
class ResultatSynthese:
    """Résultat complet du module Synthèse."""
    # Méta
    profil: Profil
    strategie_retenue: str
    date_reglementaire: str = "01/01/2026"

    # Résultats clés
    net_dirigeant_retenu: float = 0.0
    gain_vs_a: float = 0.0
    gain_5_ans: float = 0.0

    # Sections
    couts_mise_en_oeuvre: list = field(default_factory=list)
    total_couts: float = 0.0
    roi_mois: Optional[float] = None
    scores_radar: list = field(default_factory=list)
    projection: dict = field(default_factory=dict)
    decomposition: list = field(default_factory=list)
    enveloppes_compact: dict = field(default_factory=dict)
    checklist: list = field(default_factory=list)


def _synthese_assimile(profil: Profil,
                       strategies_arbitrage: dict,
                       config_comparateur,
                       code_retenue: Optional[str] = None,
                       forfaits: Optional[dict] = None,
                       alertes_comparateur: Optional[list] = None) -> ResultatSynthese:
    """
    Synthèse Assimilé salarié — implémentation historique (Phase A).

    Cette fonction préserve la logique v19 stricte pour le régime Assimilé.
    Pas de modification de comportement vs Phase A : parité 504/504 garantie.
    """
    if forfaits is None:
        forfaits = FORFAITS_DEFAUT.copy()
    if alertes_comparateur is None:
        alertes_comparateur = []

    # Détermination stratégie retenue (par défaut net max)
    if code_retenue is None:
        code_retenue = max(strategies_arbitrage.keys(),
                           key=lambda c: strategies_arbitrage[c]["total_net"])

    net_retenu = strategies_arbitrage[code_retenue]["total_net"]
    net_a = strategies_arbitrage["A"]["total_net"]
    gain_vs_a = net_retenu - net_a

    # Calculs des sections
    couts = calcul_couts_mise_en_oeuvre(profil, code_retenue, forfaits,
                                         config_comparateur)
    total_couts = sum(c.montant for c in couts)
    roi_mois = (total_couts / gain_vs_a * 12) if gain_vs_a > 0 else None

    scores_radar = calcul_radar_6d(strategies_arbitrage)
    projection = calcul_projection_5_ans(strategies_arbitrage, code_retenue)
    decomposition = calcul_decomposition_gain(strategies_arbitrage)
    enveloppes = calcul_enveloppes_patrimoniales(situation=profil.situation)
    checklist = calcul_checklist_conformite(profil, config_comparateur,
                                             code_retenue, alertes_comparateur)

    return ResultatSynthese(
        profil=profil,
        strategie_retenue=code_retenue,
        net_dirigeant_retenu=net_retenu,
        gain_vs_a=gain_vs_a,
        gain_5_ans=projection["gain_5_ans"],
        couts_mise_en_oeuvre=couts,
        total_couts=total_couts,
        roi_mois=roi_mois,
        scores_radar=scores_radar,
        projection=projection,
        decomposition=decomposition,
        enveloppes_compact=enveloppes,
        checklist=checklist,
    )


# ============================================================
# ROUTEUR PUBLIC — calcul_synthese (Phase B.2 Étape 4a)
# ============================================================
def calcul_synthese(profil: Profil,
                    strategies_arbitrage: dict,
                    config_comparateur,
                    code_retenue: Optional[str] = None,
                    forfaits: Optional[dict] = None,
                    alertes_comparateur: Optional[list] = None) -> ResultatSynthese:
    """
    Construit la Synthèse complète à partir des résultats Arbitrage et Comparateur.

    Routeur multi-régimes (Phase B.2 Étape 4a) : délègue à la sous-fonction
    appropriée selon profil.regime_social.

    - Assimilé salarié → _synthese_assimile (logique Phase A, parité v19 stricte)
    - TNS → _synthese_tns (stratégies T1-T4)
    - TNS (libéral) → _synthese_liberal (stratégies L1-L4, alerte BNC/SEL)
    - autres → _synthese_salarie (référence module détaillé)

    Args:
        profil: Profil client (regime_social détermine la sous-fonction)
        strategies_arbitrage: Dict des stratégies du régime (forme variable)
        config_comparateur: ConfigComparateur
        code_retenue: Stratégie retenue. Si None, on prend la meilleure du régime.
        forfaits: Dict des forfaits cabinet (sinon utilise FORFAITS_DEFAUT)
        alertes_comparateur: Liste d'AlertePlafond (sinon liste vide)
    """
    regime = profil.regime_social
    if regime == "Assimilé salarié":
        return _synthese_assimile(profil, strategies_arbitrage, config_comparateur,
                                   code_retenue, forfaits, alertes_comparateur)
    elif regime == "TNS":
        return _synthese_tns(profil, strategies_arbitrage, config_comparateur,
                              code_retenue, forfaits, alertes_comparateur)
    elif regime == "TNS (libéral)":
        return _synthese_liberal(profil, strategies_arbitrage, config_comparateur,
                                  code_retenue, forfaits, alertes_comparateur)
    else:
        # Cas Salarié (régime non dirigeant) ou inconnu → traitement référence
        return _synthese_salarie(profil, strategies_arbitrage, config_comparateur,
                                  code_retenue, forfaits, alertes_comparateur)


# ============================================================
# SOUS-FONCTIONS PRIVÉES PAR RÉGIME — Phase B.2 Étape 4a
# ============================================================
def _synthese_tns(profil: Profil,
                  strategies_arbitrage: dict,
                  config_comparateur,
                  code_retenue: Optional[str] = None,
                  forfaits: Optional[dict] = None,
                  alertes_comparateur: Optional[list] = None) -> ResultatSynthese:
    """
    Synthèse TNS — stratégies T1-T4.

    GARDE-FOU T4 : net_dirigeant_retenu utilise uniquement net_dirigeant_immediat.
    Le benefice_retenu_societe de T4 n'est PAS additionné. Une mention spécifique
    est ajoutée dans le résultat si T4 est la stratégie retenue.

    Args:
        strategies_arbitrage: dict {"T1": ResultatStrategieTNS, ...} ou équivalent.
            Si dict de dataclasses, on accède aux attributs ; si dict de dicts,
            on accède aux clés.
    """
    if forfaits is None:
        forfaits = FORFAITS_DEFAUT.copy()
    if alertes_comparateur is None:
        alertes_comparateur = []

    # Helper pour accéder uniformément aux champs (dataclass ou dict)
    def get_net_immediat(s):
        return s.net_dirigeant_immediat if hasattr(s, 'net_dirigeant_immediat') else s["net_dirigeant_immediat"]

    def get_benefice_retenu(s):
        return s.benefice_retenu_societe if hasattr(s, 'benefice_retenu_societe') else s.get("benefice_retenu_societe", 0.0)

    def get_alertes(s):
        return s.alertes if hasattr(s, 'alertes') else s.get("alertes", [])

    # Détermination stratégie retenue (par défaut : meilleur net immédiat)
    if code_retenue is None:
        code_retenue = max(strategies_arbitrage.keys(),
                           key=lambda c: get_net_immediat(strategies_arbitrage[c]))

    strat_retenue = strategies_arbitrage[code_retenue]
    net_retenu = get_net_immediat(strat_retenue)

    # Référence T1 (équivalent A pour TNS)
    ref_code = "T1" if "T1" in strategies_arbitrage else code_retenue
    net_ref = get_net_immediat(strategies_arbitrage[ref_code])
    gain_vs_ref = net_retenu - net_ref

    # Projection 5 ans sur le net retenu uniquement (PAS sur bénéfice retenu)
    from core.projection import projection_5_ans
    proj_vals = projection_5_ans(net_retenu, fraction_capitalisable=0.5)
    gain_5_ans = proj_vals[4] - net_retenu * 5

    # Radar 6D : pour TNS, on calcule sur les 4 stratégies T1-T4
    # Adaptation simple : convertir en format compatible avec calcul_radar_6d existant
    # qui attend un dict avec "total_net"
    strategies_pour_radar = {}
    for code, s in strategies_arbitrage.items():
        strategies_pour_radar[code] = {
            "total_net": get_net_immediat(s),
            "code": code,
        }
    # Note : calcul_radar_6d nécessite la structure A/B/C/D, donc on en fait un adaptateur
    # plus simple en attendant l'extension complète du Radar.
    scores_radar = []

    # Checklist conformité : version allégée pour TNS (pas d'historique alertes Comparateur identique)
    checklist = []

    # Alertes spécifiques au régime TNS retenu
    alertes_specifiques = list(get_alertes(strat_retenue))

    # Si T4 retenue, alerte explicite : le net immédiat ne reflète pas la totalité
    if code_retenue == "T4":
        benefice_retenu = get_benefice_retenu(strat_retenue)
        if benefice_retenu > 0:
            alertes_specifiques.append(
                f"Stratégie T4 retenue : bénéfice retenu en société = {benefice_retenu:,.2f} €. "
                f"Cette valeur est conservée par la société et NE FIGURE PAS dans le net dirigeant "
                f"affiché. Sa distribution ultérieure subira la fiscalité applicable au moment de "
                f"la distribution."
            )

    return ResultatSynthese(
        profil=profil,
        strategie_retenue=code_retenue,
        net_dirigeant_retenu=net_retenu,
        gain_vs_a=gain_vs_ref,  # nommé "vs_a" mais = "vs_T1" pour TNS
        gain_5_ans=gain_5_ans,
        couts_mise_en_oeuvre=[],  # Coûts spécifiques TNS à raffiner en B.3
        total_couts=0.0,
        roi_mois=None,
        scores_radar=scores_radar,
        projection={"gain_5_ans": gain_5_ans, "values": proj_vals},
        decomposition=[],
        enveloppes_compact={},
        checklist=checklist + [{"label": "Alertes régime TNS", "items": alertes_specifiques}],
    )


def _synthese_liberal(profil: Profil,
                      strategies_arbitrage: dict,
                      config_comparateur,
                      code_retenue: Optional[str] = None,
                      forfaits: Optional[dict] = None,
                      alertes_comparateur: Optional[list] = None) -> ResultatSynthese:
    """
    Synthèse Libéral — stratégies L1-L4.

    GARDE-FOU BNC/SEL : si L3 ou L4 retenue, alerte BNC/SEL systématiquement
    ajoutée dans la checklist. PAS de marqueur "recommandée" mécanique.
    """
    if forfaits is None:
        forfaits = FORFAITS_DEFAUT.copy()
    if alertes_comparateur is None:
        alertes_comparateur = []

    def get_net_total(s):
        return s.net_dirigeant_total if hasattr(s, 'net_dirigeant_total') else s["net_dirigeant_total"]

    def get_alertes(s):
        return s.alertes if hasattr(s, 'alertes') else s.get("alertes", [])

    if code_retenue is None:
        code_retenue = max(strategies_arbitrage.keys(),
                           key=lambda c: get_net_total(strategies_arbitrage[c]))

    strat_retenue = strategies_arbitrage[code_retenue]
    net_retenu = get_net_total(strat_retenue)

    # Référence L1 (BNC pur)
    ref_code = "L1" if "L1" in strategies_arbitrage else code_retenue
    net_ref = get_net_total(strategies_arbitrage[ref_code])
    gain_vs_ref = net_retenu - net_ref

    from core.projection import projection_5_ans
    proj_vals = projection_5_ans(net_retenu, fraction_capitalisable=0.5)
    gain_5_ans = proj_vals[4] - net_retenu * 5

    # Alertes du résultat L3/L4 (BNC/SEL + rétention v2 + L4 v2)
    alertes_specifiques = list(get_alertes(strat_retenue))

    checklist = []

    return ResultatSynthese(
        profil=profil,
        strategie_retenue=code_retenue,
        net_dirigeant_retenu=net_retenu,
        gain_vs_a=gain_vs_ref,  # nommé "vs_a" mais = "vs_L1" pour Libéral
        gain_5_ans=gain_5_ans,
        couts_mise_en_oeuvre=[],
        total_couts=0.0,
        roi_mois=None,
        scores_radar=[],
        projection={"gain_5_ans": gain_5_ans, "values": proj_vals},
        decomposition=[],
        enveloppes_compact={},
        checklist=checklist + [{"label": "Alertes régime Libéral", "items": alertes_specifiques}],
    )


def _synthese_salarie(profil: Profil,
                      strategies_arbitrage,  # ignoré pour le Salarié
                      config_comparateur,
                      code_retenue: Optional[str] = None,
                      forfaits: Optional[dict] = None,
                      alertes_comparateur: Optional[list] = None) -> ResultatSynthese:
    """
    Synthèse Salarié (référence simple, Option A).

    Le Salarié non-dirigeant n'a pas de Strategy Engine. Sa Synthèse présente
    le net du module détaillé comme valeur de référence, sans matrice de
    stratégies. Sert essentiellement de comparaison dans le Comparateur de
    régimes.
    """
    from regime.salarie import calcul_module_salarie

    res_salarie = calcul_module_salarie(profil, salaire_brut=profil.salaire_brut_assimile)
    net = res_salarie.net_apres_impots

    from core.projection import projection_5_ans
    proj_vals = projection_5_ans(net, fraction_capitalisable=0.5)
    gain_5_ans = proj_vals[4] - net * 5

    return ResultatSynthese(
        profil=profil,
        strategie_retenue="Salarié (référence)",
        net_dirigeant_retenu=net,
        gain_vs_a=0.0,
        gain_5_ans=gain_5_ans,
        couts_mise_en_oeuvre=[],
        total_couts=0.0,
        roi_mois=None,
        scores_radar=[],
        projection={"gain_5_ans": gain_5_ans, "values": proj_vals},
        decomposition=[],
        enveloppes_compact={},
        checklist=[{"label": "Régime Salarié", "items": [
            "Référence salariale : net après IR pour le salaire brut saisi. "
            "Pas de Strategy Engine appliqué (le Salarié n'a pas d'enveloppe dirigeant à arbitrer)."
        ]}],
    )
