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

MODE_AUDIT (G3f-perin, spec 1.1.0) :
- `calcul_plafond_perin` et `calcul_perin_mutualise` acceptent un paramètre
  opt-in `audit: TraceAudit | None`. Codes émis : `PERIN_*` (namespace dédié,
  distinct de tous les autres : régimes, stratégies, comparateurs,
  post-arbitrage).
- Module **100% autonome** : aucun import depuis un module instrumenté.
  `calcul_plafond_perin` produit une trace plate (~7 étapes).
  `calcul_perin_mutualise` attache 1 sous-trace `plafond_dirigeant` (toujours)
  et 1 sous-trace `plafond_conjoint` (si mutualisation effective).
- Pattern de composition interne identique à `_calcul_scenario → ir_barème`
  (G3e-scenarios) : un module autonome peut avoir une composition interne
  riche (jusqu'à 2 niveaux pour PERIN).
- Discipline non-prescriptive renforcée G3e (14 patterns) : 0 occurrence
  dans le source — pas de point de vigilance sémantique particulier.
"""

from dataclasses import dataclass
from typing import Optional
from core.profil import PASS_2026
from core.audit import TraceAudit


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
def calcul_plafond_perin(titulaire: str, revenu_pro_n_moins_1: float,
                          *,
                          audit: TraceAudit | None = None) -> PlafondPERIN:
    """Calcule le plafond individuel PERIN d'un titulaire selon CGI 163 quatervicies.

    Args:
        titulaire: "Dirigeant" ou "Conjoint"
        revenu_pro_n_moins_1: Revenu professionnel N-1 du titulaire
        audit: Trace d'audit optionnelle (G3f-perin.1). Side channel.
            Codes émis : `PERIN_*`. Aucune sous-trace (trace plate).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("PERIN_" + suffixe, label, valeur, **kw)

    plafond_calc = revenu_pro_n_moins_1 * PERIN_TAUX_REV_PRO
    plafond_brut = max(plafond_calc, PERIN_PLAFOND_MIN)
    plafond_indiv = min(plafond_brut, PERIN_PLAFOND_MAX)

    _log("TITULAIRE",
         "Titulaire du plafond (Dirigeant ou Conjoint)",
         titulaire, unite="",
         hypotheses={"valeurs_attendues": ["Dirigeant", "Conjoint"]})
    _log("REVENU_PRO_N_MOINS_1",
         "Revenu professionnel N-1 du titulaire (input)",
         revenu_pro_n_moins_1, unite="EUR")
    _log("PLAFOND_CALCULE",
         "Plafond calculé = revenu_pro × taux",
         plafond_calc, unite="EUR",
         doctrine_refs=("PASS_2026",),
         hypotheses={"PERIN_TAUX_REV_PRO": PERIN_TAUX_REV_PRO,
                     "PASS_2026": PASS_2026,
                     "formule": "revenu_pro_n_moins_1 × PERIN_TAUX_REV_PRO",
                     "cgi_ref": "CGI art. 163 quatervicies, II"})
    _log("PLAFOND_PLANCHER",
         "Plancher = 10% PASS (constante module)",
         PERIN_PLAFOND_MIN, unite="EUR",
         doctrine_refs=("PASS_2026",),
         hypotheses={"formule": "0.10 × PASS_2026",
                     "PASS_2026": PASS_2026})
    _log("PLAFOND_PLAFOND",
         "Plafond absolu = 8 PASS (constante module)",
         PERIN_PLAFOND_MAX, unite="EUR",
         doctrine_refs=("PASS_2026",),
         hypotheses={"formule": "8 × PASS_2026",
                     "PASS_2026": PASS_2026})
    _log("PLAFOND_INDIVIDUEL",
         "Plafond individuel final = min(max(calcule, plancher), plafond)",
         plafond_indiv, unite="EUR",
         hypotheses={"plafond_calcule_intermediaire": plafond_calc,
                     "plafond_brut_apres_plancher": plafond_brut,
                     "formule": "min(max(plafond_calcule, plafond_plancher), plafond_plafond)"})
    _log("SOLDE_DISPONIBLE_INITIAL",
         "Solde disponible initial (= plafond_individuel avant versement)",
         plafond_indiv, unite="EUR",
         hypotheses={"convention": "Initialisé à plafond_individuel, "
                                   "ajusté par calcul_perin_mutualise selon versement_effectif"})

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
    *,
    audit: TraceAudit | None = None,
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
        audit: Trace d'audit optionnelle (G3f-perin.1). Codes émis : `PERIN_*` méta.
            Attache 1 sous-trace `plafond_dirigeant` (toujours) et 1 sous-trace
            `plafond_conjoint` (uniquement si mutualisation effective).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("PERIN_" + suffixe, label, valeur, **kw)

    _log("VERSEMENT_DIRIGEANT",
         "Versement effectif sur PERIN du dirigeant (input)",
         versement_dirigeant, unite="EUR")
    _log("REVENU_PRO_DIRIGEANT",
         "Revenu professionnel N-1 du dirigeant (input)",
         revenu_pro_dirigeant, unite="EUR")
    _log("TMI_DIRIGEANT",
         "TMI marginal estimé du dirigeant (input)",
         tmi_dirigeant, unite="ratio")
    _log("SITUATION_FAMILIALE",
         "Situation familiale (input, détermine éligibilité mutualisation)",
         situation, unite="",
         hypotheses={"valeurs_attendues": ["Marié / pacsé",
                                            "Célibataire / divorcé / veuf"]})
    _log("CONJOINT_DECLARE",
         "Conjoint déclaré dans le calcul (input)",
         1.0 if conjoint_declare else 0.0, unite="bool",
         hypotheses={"valeur_bool": conjoint_declare})
    _log("REVENU_PRO_CONJOINT",
         "Revenu professionnel N-1 du conjoint (input)",
         revenu_pro_conjoint, unite="EUR")

    # --- Plafond individuel dirigeant avec sous-trace composée ---
    if audit is not None:
        st_dir = TraceAudit(
            regime="Plafond PERIN — Dirigeant",
            profil_resume=f"revenu_pro={revenu_pro_dirigeant:.0f}",
        )
        plaf_dir = calcul_plafond_perin("Dirigeant", revenu_pro_dirigeant,
                                         audit=st_dir)
        audit.attacher_sous_trace("plafond_dirigeant", st_dir)
    else:
        plaf_dir = calcul_plafond_perin("Dirigeant", revenu_pro_dirigeant)

    # Condition de mutualisation
    mutualisation_possible = (situation == "Marié / pacsé"
                              and conjoint_declare
                              and revenu_pro_conjoint > 0)

    _log("MUTUALISATION_POSSIBLE",
         "Condition de mutualisation conjoint évaluée",
         1.0 if mutualisation_possible else 0.0, unite="bool",
         hypotheses={"valeur_bool": mutualisation_possible,
                     "condition": "situation == 'Marié / pacsé' AND "
                                   "conjoint_declare AND revenu_pro_conjoint > 0",
                     "situation_evaluee": situation == "Marié / pacsé",
                     "conjoint_declare_evalue": conjoint_declare,
                     "revenu_conjoint_evalue": revenu_pro_conjoint > 0,
                     "cgi_ref": "CGI art. 163 quatervicies, V"})

    if not mutualisation_possible:
        # Cas sans mutualisation : on s'arrête au plafond individuel
        versement_couvert = min(versement_dirigeant, plaf_dir.plafond_individuel)
        excedent = max(0, versement_dirigeant - plaf_dir.plafond_individuel)
        economie_ir = versement_couvert * tmi_dirigeant

        plaf_dir.versement_effectif = versement_dirigeant
        plaf_dir.solde_disponible = max(0, plaf_dir.plafond_individuel - versement_dirigeant)

        _log("PLAFOND_TOTAL_RETENU",
             "Plafond total retenu (= plafond_individuel dirigeant, sans mutualisation)",
             plaf_dir.plafond_individuel, unite="EUR",
             hypotheses={"branche": "sans_mutualisation"})
        _log("VERSEMENT_DIRIGEANT_COUVERT",
             "Part du versement dirigeant couverte par le plafond retenu",
             versement_couvert, unite="EUR",
             hypotheses={"formule": "min(versement_dirigeant, plafond_total)"})
        _log("VERSEMENT_EXCEDENT",
             "Part du versement non couverte (au-delà du plafond)",
             excedent, unite="EUR",
             hypotheses={"formule": "max(0, versement_dirigeant - plafond_total)",
                         "depasse_plafond": excedent > 0})
        _log("ECONOMIE_IR",
             "Économie d'IR sur la part couverte (= versement_couvert × TMI)",
             economie_ir, unite="EUR",
             hypotheses={"formule": "versement_couvert × tmi_dirigeant"})
        _log("MUTUALISATION_ACTIVE",
             "Mutualisation conjoint effectivement appliquée",
             0.0, unite="bool",
             hypotheses={"valeur_bool": False,
                         "branche": "sans_mutualisation"})

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

    # --- Cas avec mutualisation : plafond conjoint avec sous-trace ---
    if audit is not None:
        st_conj = TraceAudit(
            regime="Plafond PERIN — Conjoint",
            profil_resume=f"revenu_pro={revenu_pro_conjoint:.0f}",
        )
        plaf_conj = calcul_plafond_perin("Conjoint", revenu_pro_conjoint,
                                          audit=st_conj)
        audit.attacher_sous_trace("plafond_conjoint", st_conj)
    else:
        plaf_conj = calcul_plafond_perin("Conjoint", revenu_pro_conjoint)

    plaf_conj.versement_effectif = versement_conjoint
    plaf_conj.solde_disponible = max(0, plaf_conj.plafond_individuel - versement_conjoint)

    # Plafond mutualisé = plafond individuel dirigeant + solde du conjoint
    plafond_total = plaf_dir.plafond_individuel + plaf_conj.solde_disponible

    versement_couvert = min(versement_dirigeant, plafond_total)
    excedent = max(0, versement_dirigeant - plafond_total)
    economie_ir = versement_couvert * tmi_dirigeant

    plaf_dir.versement_effectif = versement_dirigeant

    _log("PLAFOND_TOTAL_RETENU",
         "Plafond total retenu (= individuel dirigeant + solde conjoint, avec mutualisation)",
         plafond_total, unite="EUR",
         hypotheses={"branche": "avec_mutualisation",
                     "formule": "plafond_individuel_dirigeant + solde_disponible_conjoint",
                     "plafond_individuel_dirigeant": plaf_dir.plafond_individuel,
                     "solde_disponible_conjoint": plaf_conj.solde_disponible,
                     "versement_conjoint_input": versement_conjoint})
    _log("VERSEMENT_DIRIGEANT_COUVERT",
         "Part du versement dirigeant couverte par le plafond mutualisé",
         versement_couvert, unite="EUR",
         hypotheses={"formule": "min(versement_dirigeant, plafond_total)"})
    _log("VERSEMENT_EXCEDENT",
         "Part du versement non couverte (au-delà du plafond mutualisé)",
         excedent, unite="EUR",
         hypotheses={"formule": "max(0, versement_dirigeant - plafond_total)",
                     "depasse_plafond": excedent > 0})
    _log("ECONOMIE_IR",
         "Économie d'IR sur la part couverte (= versement_couvert × TMI)",
         economie_ir, unite="EUR",
         hypotheses={"formule": "versement_couvert × tmi_dirigeant"})
    _log("MUTUALISATION_ACTIVE",
         "Mutualisation conjoint effectivement appliquée",
         1.0, unite="bool",
         hypotheses={"valeur_bool": True,
                     "branche": "avec_mutualisation"})

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
