"""
Module PERIN — Plan d'Épargne Retraite Individuel.

Gère :
- Plafond individuel du dirigeant
- Plafond du conjoint (si applicable)
- Mutualisation des plafonds entre conjoints (CGI art. 163 quatervicies, V)

Décisions doctrinales :
- Plafond individuel = max(10 % rev. pro. N-1 ; 10 % PASS)
- Plafond mutualisé = somme des plafonds individuels non utilisés du conjoint
- Mutualisation conditionnelle : situation = "Marié / pacsé" ET conjoint déclaré
"""

from dataclasses import dataclass
from typing import Optional
from core.profil import PASS_2026


# ============================================================
# CONSTANTES PERIN
# ============================================================
PERIN_PLAFOND_MIN = 0.10 * PASS_2026       # 4 806,00 € (10 % PASS)
PERIN_PLAFOND_MAX = 8 * PASS_2026          # 384 480,00 € (8 PASS)
PERIN_TAUX_REV_PRO = 0.10                  # 10 % des revenus pro


# ============================================================
# DATACLASSES
# ============================================================
@dataclass
class PlafondPERIN:
    """Détail du plafond PERIN d'un titulaire."""
    titulaire: str                     # "Dirigeant" ou "Conjoint"
    revenu_pro_n_moins_1: float        # Revenu professionnel N-1
    plafond_calculé: float              # 10 % rev. pro. N-1
    plafond_plancher: float             # 10 % PASS
    plafond_plafond: float              # 8 PASS
    plafond_individuel: float           # max(calculé, plancher) limité à plafond_plafond
    versement_effectif: float = 0.0
    solde_disponible: float = 0.0       # plafond_individuel - versement_effectif


@dataclass
class ResultatPERINMutualise:
    """Résultat consolidé PERIN avec mutualisation conjoint."""
    # Détails par titulaire
    plafond_dirigeant: PlafondPERIN
    plafond_conjoint: Optional[PlafondPERIN] = None

    # Versement effectif du dirigeant
    versement_dirigeant: float = 0.0

    # Mutualisation
    mutualisation_active: bool = False
    plafond_mutualise_total: float = 0.0      # individuel dirigeant + solde conjoint
    versement_dirigeant_couvert: float = 0.0   # part couverte par plafond mutualisé
    versement_excedent: float = 0.0            # part non couverte (alerte)

    # Économie d'IR
    tmi_dirigeant: float = 0.0
    economie_ir: float = 0.0


# ============================================================
# CALCUL DU PLAFOND INDIVIDUEL
# ============================================================
def calcul_plafond_perin(titulaire: str, revenu_pro_n_moins_1: float) -> PlafondPERIN:
    """Calcule le plafond individuel PERIN d'un titulaire selon CGI 163 quatervicies."""
    plafond_calc = revenu_pro_n_moins_1 * PERIN_TAUX_REV_PRO
    plafond_brut = max(plafond_calc, PERIN_PLAFOND_MIN)
    plafond_indiv = min(plafond_brut, PERIN_PLAFOND_MAX)

    return PlafondPERIN(
        titulaire=titulaire,
        revenu_pro_n_moins_1=revenu_pro_n_moins_1,
        plafond_calculé=plafond_calc,
        plafond_plancher=PERIN_PLAFOND_MIN,
        plafond_plafond=PERIN_PLAFOND_MAX,
        plafond_individuel=plafond_indiv,
        versement_effectif=0.0,
        solde_disponible=plafond_indiv,
    )


# ============================================================
# CALCUL AVEC MUTUALISATION
# ============================================================
def calcul_perin_mutualise(
    versement_dirigeant: float,
    revenu_pro_dirigeant: float,
    tmi_dirigeant: float,
    situation: str = "Marié / pacsé",
    conjoint_declare: bool = False,
    revenu_pro_conjoint: float = 0.0,
    versement_conjoint: float = 0.0,
) -> ResultatPERINMutualise:
    """
    Calcule le plafond PERIN du dirigeant avec mutualisation conjoint si applicable.

    Args:
        versement_dirigeant: Montant versé sur le PERIN du dirigeant (€/an)
        revenu_pro_dirigeant: Revenu professionnel N-1 du dirigeant
        tmi_dirigeant: TMI marginal estimé du dirigeant
        situation: "Marié / pacsé" ou "Célibataire / divorcé / veuf"
        conjoint_declare: True si le conjoint déclare ses revenus pro et accepte la mutualisation
        revenu_pro_conjoint: Revenu pro N-1 du conjoint
        versement_conjoint: Montant déjà versé sur le PERIN du conjoint
    """
    # Plafond individuel dirigeant
    plaf_dir = calcul_plafond_perin("Dirigeant", revenu_pro_dirigeant)

    # Cas sans mutualisation
    mutualisation_possible = (situation == "Marié / pacsé"
                              and conjoint_declare
                              and revenu_pro_conjoint > 0)

    if not mutualisation_possible:
        # Pas de mutualisation : on s'arrête au plafond individuel
        versement_couvert = min(versement_dirigeant, plaf_dir.plafond_individuel)
        excedent = max(0, versement_dirigeant - plaf_dir.plafond_individuel)
        economie_ir = versement_couvert * tmi_dirigeant

        plaf_dir.versement_effectif = versement_dirigeant
        plaf_dir.solde_disponible = max(0, plaf_dir.plafond_individuel - versement_dirigeant)

        return ResultatPERINMutualise(
            plafond_dirigeant=plaf_dir,
            plafond_conjoint=None,
            versement_dirigeant=versement_dirigeant,
            mutualisation_active=False,
            plafond_mutualise_total=plaf_dir.plafond_individuel,
            versement_dirigeant_couvert=versement_couvert,
            versement_excedent=excedent,
            tmi_dirigeant=tmi_dirigeant,
            economie_ir=economie_ir,
        )

    # Cas avec mutualisation
    plaf_conj = calcul_plafond_perin("Conjoint", revenu_pro_conjoint)
    plaf_conj.versement_effectif = versement_conjoint
    plaf_conj.solde_disponible = max(0, plaf_conj.plafond_individuel - versement_conjoint)

    # Plafond mutualisé = plafond individuel dirigeant + solde du conjoint
    plafond_total = plaf_dir.plafond_individuel + plaf_conj.solde_disponible

    versement_couvert = min(versement_dirigeant, plafond_total)
    excedent = max(0, versement_dirigeant - plafond_total)
    economie_ir = versement_couvert * tmi_dirigeant

    plaf_dir.versement_effectif = versement_dirigeant

    return ResultatPERINMutualise(
        plafond_dirigeant=plaf_dir,
        plafond_conjoint=plaf_conj,
        versement_dirigeant=versement_dirigeant,
        mutualisation_active=True,
        plafond_mutualise_total=plafond_total,
        versement_dirigeant_couvert=versement_couvert,
        versement_excedent=excedent,
        tmi_dirigeant=tmi_dirigeant,
        economie_ir=economie_ir,
    )
