"""
strategy/receptacles_pero.py — Module métier PERO (v1.3 SP24).

Module d'allocation d'une cotisation employeur PERO (Plan d'Épargne
Retraite Obligatoire) à un horizon donné, avec économie fiscale
immédiate à l'entrée, capitalisation conventionnelle, et fiscalité
de sortie en capital (simplification de simulation B-Q1=β
doctrinalement marquée).

Périmètre SP24 (cadrage validé)
────────────────────────────────
- Cotisation employeur (en % du salaire brut)
- CSG-CRDS sur cotisation employeur (9,7 %, prélevée salarié)
- Forfait social employeur (16 %, valeur doctrinale France 2026)
- Économie fiscale immédiate du salarié (exonération à l'entrée,
  dans la limite globale 8 % rém brute / 8 PASS)
- Effort réel (A-Q1=β) = CSG/CRDS sur cotisation employeur
  − économie fiscale immédiate
- Coût entreprise = cotisation employeur × (1 + forfait social)
- Capitalisation conventionnelle annuelle simple (D-R8, 2 %)
- Sortie capital uniquement (B-Q1=β : simplification de
  simulation, le PERO réel est servi en rente — wording
  WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL joint à la trace)
- Horizons 5/10/20 ans (cohérent SP15-SP17)
- Hypothèses doctrinales France 2026 (à confirmer)

Exclusions explicites (R2 directive + SP23 §3)
───────────────────────────────────────────────
- Rattrapages N-1/N-2/N-3
- Multi-collèges
- Architecture RH avancée (catégories multiples, ancienneté)
- Sortie rente (modélisée par simplification capital, cf. wording)
- Transferts inter-régimes
- Déblocages anticipés au-delà du cas générique
- Solveur de taux automatique
- Recherche de configuration cible
- Scénarios experts

Sémantique économique (résolution A-Q1=β)
──────────────────────────────────────────
PERO partage avec PEE/PERECO la logique « flux employeur principal,
salarié non versant ». SP24 préserve la sémantique du dataclass
`LigneHorizonReceptacle` (verrouillé SP13 §3) sans la déformer :

  - `flux_entrant_brut` : CSG/CRDS prélevée sur la cotisation
    employeur. C'est **le seul flux sortant immédiat du salarié**
    au titre du PERO (A-Q1=β : effort_reel observable, pas spéculatif).
    Cohérent avec l'invariant générique `__post_init__` qui exige
    `effort_reel = flux_entrant_brut - economie_fiscale_immediate`.

  - `economie_fiscale_immediate` : partie de la cotisation employeur
    exonérée d'IR (dans la limite globale 8 % rém / 8 PASS) ×
    TMI. Distincte conceptuellement de l'économie PERIN (qui repose
    sur une déduction du versement individuel).

  - `effort_reel` : CSG/CRDS sur cotisation − économie fiscale.
    Peut être négatif si l'économie fiscale dépasse la CSG/CRDS
    (cas habituel pour TMI > 9,7 %). Cohérent doctrinalement :
    le PERO peut représenter un gain immédiat net pour le salarié,
    indépendamment du capital projeté.

  - `capital_projete` : cotisation employeur capitalisée (rendement
    2 % annuel simple). La capitalisation porte sur la cotisation
    brute, non sur la CSG/CRDS (qui sort du périmètre PERO et va
    au régime général).

  - `cout_entreprise` : cotisation employeur × (1 + forfait social).
    C'est la charge totale supportée par l'entreprise.

  - `valeur_nette` : capital projeté − fiscalité de sortie (en
    sortie capital, B-Q1=β). La simplification capital est marquée
    explicitement dans la trace audit via
    WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL.

  - `disponibilite` : wording WORDING_PERO_DISPONIBILITE_RETRAITE.

Discipline d'implémentation (résultante des arbitrages SP24)
─────────────────────────────────────────────────────────────
- Pattern strict SP15-SP17 copié (3 providers + helpers privés +
  fonction principale `allocation_pero` + sous-traces horizons).
- Zéro magic number (subsidiaire validé) : tous les taux passent
  par les 3 providers doctrinaux. Override possible pour tests
  via le paramètre `_override_taux` (None par défaut).
- D-R10 : aucune étape `parent_id != None`.
- Invariants algébriques `__post_init__` cohérents SP15-SP17
  (D-Q1=β : 4 identités gravées par LigneHorizonReceptacle existant
  + 2 identités PERO-spécifiques validées en helper).

Référence doctrinale : `ARCHITECTURE_PERO.md` §4-§6, §13bis.
"""

from dataclasses import dataclass
from typing import Optional

from core.audit import TraceAudit
from core.profil import Profil, PASS_2026

from strategy.receptacles_orchestrateur import (
    Euros, TauxAnnuel, Annees,
    LigneHorizonReceptacle, ResultatAllocationEnveloppe,
    RENDEMENT_NOMINAL_ANNUEL,
)
from strategy.receptacles_wordings import (
    WORDING_REC_CONVENTION_RENDEMENT,
    WORDING_PERO_REGLE_COTISATION,
    WORDING_PERO_CSG_CRDS_COTISATION,
    WORDING_PERO_FORFAIT_SOCIAL_EMPLOYEUR,
    WORDING_PERO_ECONOMIE_FISCALE_ENTREE,
    WORDING_PERO_DISPONIBILITE_RETRAITE,
    WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL,
)


# ============================================================
# CONSTANTES SPÉCIFIQUES PERO (valeurs doctrinales France 2026)
# ============================================================
# Forfait social employeur sur cotisation PERO obligatoire
# (Code sécurité sociale art. L137-15). Taux conventionnel 16 %
# applicable aux régimes de retraite supplémentaire obligatoires
# d'entreprise. À confirmer selon réglementation en vigueur lors
# d'une mise en production.
TX_FORFAIT_SOCIAL_PERO: TauxAnnuel = 0.16

# CSG-CRDS sur cotisation employeur PERO : 9,7 % (CSG 9,2 % +
# CRDS 0,5 %), prélevée sur le salarié (et non sur l'employeur).
# Code de la sécurité sociale art. L136-1 et L136-2.
TX_CSG_CRDS_PERO: TauxAnnuel = 0.097

# Plafond annuel d'exonération IR pour le salarié au titre du
# PERO. Limite globale PEE/PERECO/PERO : 8 % de la rémunération
# brute annuelle, plafonnée à 8 PASS (CGI art. 83 2°).
# SP24 retient cette limite simplifiée. v1.4+ pourra prendre en
# compte les autres versements imputés sur la même limite.
TX_PLAFOND_EXONERATION_REM: TauxAnnuel = 0.08
PLAFOND_EXONERATION_PASS: float = 8.0  # multiple PASS

# Prélèvements sociaux sur gains à la sortie en capital (PFU
# global 30 % = 12,8 % IR + 17,2 % PS). Aligné PERIN/PERECO en
# simplification capital (B-Q1=β : la fiscalité de rente réelle
# n'est pas modélisée v1.3, cf. wording de simplification).
TX_PFU_GAINS_PERO: TauxAnnuel = 0.30


# ============================================================
# PROVIDERS DOCTRINAUX (subsidiaire validé : providers + override tests)
# ============================================================
def obtenir_taux_forfait_social_pero(
    profil: Profil,
    _override_taux: Optional[dict] = None,
) -> TauxAnnuel:
    """Provider doctrinal : taux de forfait social employeur PERO.

    Constante doctrinale 16 % (France 2026, à confirmer en
    réactivation v1.3+). La signature inclut `profil` pour
    cohérence avec les autres providers et anticipation v1.4+ où
    certaines catégories pourraient avoir des taux différenciés.

    Args:
        profil: Profil du dirigeant/salarié (non utilisé en SP24).
        _override_taux: dict optionnel pour tests, clé
            "forfait_social". None en runtime normal.

    Returns:
        Taux de forfait social (ex. 0.16 = 16 %).
    """
    if _override_taux is not None and "forfait_social" in _override_taux:
        return float(_override_taux["forfait_social"])
    return TX_FORFAIT_SOCIAL_PERO


def obtenir_taux_ps_pero(
    profil: Profil,
    _override_taux: Optional[dict] = None,
) -> TauxAnnuel:
    """Provider doctrinal : taux CSG/CRDS sur cotisation PERO.

    Constante doctrinale 9,7 % (France 2026, à confirmer en
    réactivation v1.3+).

    Args:
        profil: Profil du dirigeant/salarié (non utilisé en SP24).
        _override_taux: dict optionnel pour tests, clé "csg_crds".
            None en runtime normal.

    Returns:
        Taux CSG/CRDS (ex. 0.097 = 9,7 %).
    """
    if _override_taux is not None and "csg_crds" in _override_taux:
        return float(_override_taux["csg_crds"])
    return TX_CSG_CRDS_PERO


def obtenir_plafond_pero(
    profil: Profil,
    salaire_brut_annuel: Euros,
    _override_taux: Optional[dict] = None,
) -> Euros:
    """Provider doctrinal : plafond annuel d'exonération IR pour
    la cotisation employeur PERO.

    Limite globale PEE/PERECO/PERO : 8 % de la rémunération brute
    annuelle, plafonnée à 8 PASS. SP24 retient cette limite
    simplifiée (les autres versements imputés sur la même limite
    ne sont pas pris en compte v1.3).

    Args:
        profil: Profil du dirigeant/salarié (non utilisé en SP24).
        salaire_brut_annuel: salaire brut annuel servant d'assiette.
        _override_taux: dict optionnel pour tests, clés
            "plafond_taux" et/ou "plafond_pass". None en runtime
            normal.

    Returns:
        Plafond annuel d'exonération en euros.
    """
    if _override_taux is not None:
        taux = float(_override_taux.get("plafond_taux",
                                        TX_PLAFOND_EXONERATION_REM))
        mult = float(_override_taux.get("plafond_pass",
                                        PLAFOND_EXONERATION_PASS))
    else:
        taux = TX_PLAFOND_EXONERATION_REM
        mult = PLAFOND_EXONERATION_PASS
    plafond_rem = taux * float(salaire_brut_annuel)
    plafond_pass = mult * float(PASS_2026)
    return min(plafond_rem, plafond_pass)


def est_eligible_pero(profil: Profil) -> bool:
    """Provider doctrinal : éligibilité PERO du profil.

    Le PERO est ouvert aux salariés (notamment dirigeants assimilés
    salariés) appartenant à une catégorie objective définie par
    l'entreprise. Pour SP24, on retient une éligibilité universelle
    pour les profils qui pourraient être assimilés salariés (le
    cabinet apprécie au cas par cas si la catégorie objective
    couvre effectivement le dirigeant).

    Args:
        profil: Profil du dirigeant/salarié.

    Returns:
        True systématiquement en SP24 (cohérent SP16/SP17).
    """
    return True


# ============================================================
# CALCULS ÉCONOMIQUES (helpers privés)
# ============================================================
def _capitaliser(flux_initial: Euros, taux_annuel: TauxAnnuel,
                 nb_annees: Annees) -> Euros:
    """Capitalisation conventionnelle annuelle simple.

    Identique à PERIN/PEE/PERECO (D-R8 : taux fixe 2 % nominal,
    capitalisation annuelle, déterministe).

    Formule : capital = flux_initial × (1 + taux)^nb_annees
    """
    return float(flux_initial) * ((1.0 + float(taux_annuel))
                                  ** int(nb_annees))


def _fiscalite_sortie_capital(capital_projete: Euros,
                              cotisation_cumulee: Euros) -> Euros:
    """Fiscalité de sortie en capital (simplification B-Q1=β).

    Calcul simplifié aligné PERIN/PERECO : les gains
    (capital_projete - cotisation_cumulee) sont soumis au PFU 30 %.
    La cotisation employeur, déjà exonérée à l'entrée dans la
    limite du plafond, est reprise au barème IR si la valeur
    capitalisée est servie en capital (CGI art. 158).

    SP24 simplification : on applique uniquement le PFU sur les
    gains, comme PERIN/PERECO. La reprise IR sur cotisation à la
    sortie n'est pas modélisée (le PERO réel est en rente ; la
    simulation capital est marquée explicitement par le wording
    WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL).

    Args:
        capital_projete: capital constitué à l'horizon.
        cotisation_cumulee: cotisation employeur cumulée à
            l'horizon (avant capitalisation).

    Returns:
        Fiscalité de sortie en euros.
    """
    gains = max(0.0, float(capital_projete) - float(cotisation_cumulee))
    return gains * float(TX_PFU_GAINS_PERO)


# ============================================================
# FONCTION PRINCIPALE
# ============================================================
@dataclass
class ResultatAllocationPero(ResultatAllocationEnveloppe):
    """Résultat spécifique PERO (SP24).

    Hérite de ResultatAllocationEnveloppe (orchestrateur SP18).
    SP24 n'ajoute pas de champs spécifiques au-delà de la base
    commune (cohérent SP15-SP17 qui restent minces).

    Note SP25 : si l'orchestrateur étendu intègre PERO (champ
    `pero: ResultatAllocationPero` dans ResultatAllocationReceptacles),
    cette dataclass pourra être déplacée dans receptacles_orchestrateur.py
    pour cohérence avec ResultatAllocationPerin/Pee/Pereco. SP24
    la définit localement pour ne pas modifier l'orchestrateur.
    """
    pass


def allocation_pero(
    profil: Profil,
    salaire_brut_annuel: Euros,
    taux_cotisation_pero: TauxAnnuel,
    horizons: tuple = (5, 10, 20),
    audit: Optional[TraceAudit] = None,
    _override_taux: Optional[dict] = None,
) -> ResultatAllocationPero:
    """Calcule l'allocation PERO et la trace d'audit.

    Pattern strict SP15-SP17 : étapes racine au niveau enveloppe
    (éligibilité, taux, plafonds, économie fiscale, coût entreprise,
    effort réel) + une sous-trace par horizon (3 horizons × ~6
    étapes par défaut).

    Args:
        profil: Profil du dirigeant assimilé salarié.
        salaire_brut_annuel: salaire brut annuel servant d'assiette
            de cotisation PERO.
        taux_cotisation_pero: taux de cotisation employeur, exprimé
            en fraction (ex. 0.03 = 3 %).
        horizons: horizons de projection en années
            (par défaut 5/10/20, cohérent SP15-SP17).
        audit: trace d'audit cible. Si None, aucune trace n'est
            produite (cohérent SP15-SP17).
        _override_taux: dict optionnel pour tests doctrinaux, passé
            aux 3 providers. None en runtime normal (zéro magic
            number, subsidiaire validé).

    Returns:
        ResultatAllocationPero contenant les 3 lignes horizon.
    """
    # ─── 1. Éligibilité ────────────────────────────────────────
    eligible = est_eligible_pero(profil)
    if audit is not None:
        audit.add(
            code="REC_PERO_ELIGIBILITE",
            label="Éligibilité PERO (catégorie objective présumée)",
            valeur=bool(eligible),
            hypotheses={
                "WORDING_PERO_REGLE_COTISATION":
                    WORDING_PERO_REGLE_COTISATION,
            },
        )

    if not eligible:
        return ResultatAllocationPero(
            enveloppe="PERO",
            accessible=False,
            motif_inaccessibilite=(
                "Catégorie objective non couvrante pour ce profil"
            ),
            lignes_par_horizon=[],
        )

    # ─── 2. Taux de cotisation appliqué ────────────────────────
    if audit is not None:
        audit.add(
            code="REC_PERO_TAUX_COTISATION_APPLIQUE",
            label="Taux de cotisation employeur PERO appliqué",
            valeur=float(taux_cotisation_pero),
        )

    # ─── 3. Flux employeur brut annuel ─────────────────────────
    flux_employeur_brut_annuel = (
        float(salaire_brut_annuel) * float(taux_cotisation_pero)
    )
    if audit is not None:
        audit.add(
            code="REC_PERO_FLUX_EMPLOYEUR_BRUT_ANNUEL",
            label="Flux employeur PERO brut annuel",
            valeur=flux_employeur_brut_annuel, unite="EUR",
        )

    # ─── 4. Plafonnement exonération sociale/IR ────────────────
    plafond_exoneration = obtenir_plafond_pero(
        profil, salaire_brut_annuel, _override_taux=_override_taux,
    )
    if audit is not None:
        audit.add(
            code="REC_PERO_PLAFOND_EXONERATION",
            label="Plafond annuel d'exonération PERO",
            valeur=plafond_exoneration, unite="EUR",
            hypotheses={
                "WORDING_PERO_ECONOMIE_FISCALE_ENTREE":
                    WORDING_PERO_ECONOMIE_FISCALE_ENTREE,
            },
        )

    cotisation_exoneree = min(flux_employeur_brut_annuel,
                              plafond_exoneration)
    cotisation_non_exoneree = (flux_employeur_brut_annuel
                               - cotisation_exoneree)
    if audit is not None:
        audit.add(
            code="REC_PERO_COTISATION_EXONEREE",
            label="Cotisation employeur exonérée d'IR",
            valeur=cotisation_exoneree, unite="EUR",
        )
        if cotisation_non_exoneree > 0.0:
            audit.add(
                code="REC_PERO_COTISATION_NON_EXONEREE",
                label=("Cotisation employeur excédant le plafond "
                       "(reprise IR)"),
                valeur=cotisation_non_exoneree, unite="EUR",
            )

    # ─── 5. Économie fiscale immédiate (salarié) ──────────────
    tmi = float(getattr(profil, "tmi", 0.30))
    if audit is not None:
        audit.add(
            code="REC_PERO_TMI_APPLIQUEE",
            label="TMI appliquée pour l'économie fiscale",
            valeur=tmi,
        )
    economie_fiscale_immediate = cotisation_exoneree * tmi
    if audit is not None:
        audit.add(
            code="REC_PERO_ECONOMIE_FISCALE_IMMEDIATE",
            label="Économie fiscale immédiate (salarié)",
            valeur=economie_fiscale_immediate, unite="EUR",
        )

    # ─── 6. CSG/CRDS sur cotisation employeur (salarié) ───────
    tx_csg_crds = obtenir_taux_ps_pero(
        profil, _override_taux=_override_taux,
    )
    csg_crds_salarie = flux_employeur_brut_annuel * tx_csg_crds
    if audit is not None:
        audit.add(
            code="REC_PERO_CSG_CRDS",
            label="CSG/CRDS sur cotisation employeur (salarié)",
            valeur=csg_crds_salarie, unite="EUR",
            hypotheses={
                "WORDING_PERO_CSG_CRDS_COTISATION":
                    WORDING_PERO_CSG_CRDS_COTISATION,
            },
        )

    # ─── 7. Forfait social employeur ──────────────────────────
    tx_forfait_social = obtenir_taux_forfait_social_pero(
        profil, _override_taux=_override_taux,
    )
    forfait_social = flux_employeur_brut_annuel * tx_forfait_social
    if audit is not None:
        audit.add(
            code="REC_PERO_FORFAIT_SOCIAL",
            label="Forfait social employeur",
            valeur=forfait_social, unite="EUR",
            hypotheses={
                "WORDING_PERO_FORFAIT_SOCIAL_EMPLOYEUR":
                    WORDING_PERO_FORFAIT_SOCIAL_EMPLOYEUR,
            },
        )

    # ─── 8. Coût entreprise ───────────────────────────────────
    cout_entreprise_annuel = flux_employeur_brut_annuel + forfait_social
    if audit is not None:
        audit.add(
            code="REC_PERO_COUT_ENTREPRISE_ANNUEL",
            label="Coût entreprise annuel total",
            valeur=cout_entreprise_annuel, unite="EUR",
        )

    # ─── 9. Effort réel salarié (A-Q1=β) ──────────────────────
    effort_reel_annuel = csg_crds_salarie - economie_fiscale_immediate
    if audit is not None:
        audit.add(
            code="REC_PERO_EFFORT_REEL_ANNUEL",
            label="Effort réel salarié annuel (CSG/CRDS − économie fiscale)",
            valeur=effort_reel_annuel, unite="EUR",
        )

    # ─── 10. Disponibilité (rappel doctrinal) ──────────────────
    if audit is not None:
        audit.add(
            code="REC_PERO_DISPONIBILITE",
            label="Disponibilité PERO",
            valeur="Retraite (cas légaux de déblocage anticipé)",
            hypotheses={
                "WORDING_PERO_DISPONIBILITE_RETRAITE":
                    WORDING_PERO_DISPONIBILITE_RETRAITE,
            },
        )

    # ─── 11. Projection par horizon (sous-traces D-R10) ────────
    lignes_par_horizon: list = []
    for nb_annees in horizons:
        # Sous-trace dédiée (pattern SP15-SP17)
        sous_trace_horizon = None
        if audit is not None:
            sous_trace_horizon = TraceAudit(
                regime=f"PERO — Horizon {int(nb_annees)} ans",
                profil_resume=(
                    f"Cotisation employeur {flux_employeur_brut_annuel:.0f} €, "
                    f"TMI {tmi*100:.1f}%, "
                    f"capitalisation {RENDEMENT_NOMINAL_ANNUEL*100:.0f}%/an"
                ),
            )

        # Capital projeté (capitalisation cotisation annuelle
        # cumulée sur nb_annees, taux 2 % conventionnel)
        # Annuité constante : on capitalise chaque versement annuel
        # depuis l'année de son versement jusqu'à l'horizon.
        # Formule annuité constante : flux × ((1+r)^n - 1) / r
        if RENDEMENT_NOMINAL_ANNUEL > 0.0:
            capital_projete = (
                flux_employeur_brut_annuel
                * (((1.0 + RENDEMENT_NOMINAL_ANNUEL) ** int(nb_annees))
                   - 1.0)
                / RENDEMENT_NOMINAL_ANNUEL
            )
        else:
            # Cas limite r=0 : somme arithmétique
            capital_projete = (flux_employeur_brut_annuel
                               * float(nb_annees))
        if sous_trace_horizon is not None:
            sous_trace_horizon.add(
                code=f"REC_PERO_CAPITAL_PROJETE_{int(nb_annees)}ANS",
                label=f"Capital projeté à {int(nb_annees)} ans",
                valeur=capital_projete, unite="EUR",
                hypotheses={
                    "WORDING_REC_CONVENTION_RENDEMENT":
                        WORDING_REC_CONVENTION_RENDEMENT,
                },
            )

        # Fiscalité de sortie capital (B-Q1=β simplification marquée)
        cotisation_cumulee = (flux_employeur_brut_annuel
                              * float(nb_annees))
        fiscalite_sortie = _fiscalite_sortie_capital(
            capital_projete, cotisation_cumulee,
        )
        if sous_trace_horizon is not None:
            sous_trace_horizon.add(
                code=f"REC_PERO_FISCALITE_SORTIE_{int(nb_annees)}ANS",
                label=(f"Fiscalité de sortie capital à "
                       f"{int(nb_annees)} ans (simulation)"),
                valeur=fiscalite_sortie, unite="EUR",
                hypotheses={
                    "WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL":
                        WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL,
                },
            )

        valeur_nette = capital_projete - fiscalite_sortie
        if sous_trace_horizon is not None:
            sous_trace_horizon.add(
                code=f"REC_PERO_VALEUR_NETTE_{int(nb_annees)}ANS",
                label=f"Valeur nette à {int(nb_annees)} ans",
                valeur=valeur_nette, unite="EUR",
            )

        # Construction LigneHorizonReceptacle
        # Sémantique A-Q1=β :
        #   flux_entrant_brut = CSG/CRDS sur cotisation annuelle
        #     (seul flux sortant du salarié à l'entrée)
        #   economie_fiscale_immediate = exonération × TMI
        #   effort_reel = CSG/CRDS − économie fiscale
        # L'invariant LigneHorizonReceptacle.__post_init__
        #   `effort_reel = flux_entrant_brut - economie_fiscale_immediate`
        # est donc satisfait par construction.
        ligne = LigneHorizonReceptacle(
            horizon_annees=int(nb_annees),
            flux_entrant_brut=csg_crds_salarie,
            economie_fiscale_immediate=economie_fiscale_immediate,
            effort_reel=effort_reel_annuel,
            capital_projete=capital_projete,
            fiscalite_sortie=fiscalite_sortie,
            valeur_nette=valeur_nette,
            cout_entreprise=cout_entreprise_annuel,
            disponibilite=(
                "Bloqué jusqu'à la retraite ; cas légaux de "
                "déblocage anticipé hors acquisition RP."
            ),
        )
        lignes_par_horizon.append(ligne)

        # Attache la sous-trace horizon à la trace racine (pattern
        # SP15-SP17 : cohérent avec PERIN/PEE/PERECO).
        if audit is not None and sous_trace_horizon is not None:
            audit.attacher_sous_trace(
                f"horizon_{int(nb_annees)}ans", sous_trace_horizon,
            )

    return ResultatAllocationPero(
        enveloppe="PERO",
        accessible=True,
        motif_inaccessibilite="",
        lignes_par_horizon=lignes_par_horizon,
    )


# ============================================================
# INVARIANTS ALGÉBRIQUES PERO-SPÉCIFIQUES (D-Q1=β)
# ============================================================
# Les 2 invariants génériques (effort_reel, valeur_nette) sont
# déjà gravés dans LigneHorizonReceptacle.__post_init__
# (cf. orchestrateur SP18). On expose ici les 2 invariants
# PERO-spécifiques (cotisation × forfait social = cout_entreprise,
# et capitalisation géométrique) sous forme de helper testable.
# Cela permet aux tests SP24 et aux futurs goldens de valider
# l'algèbre métier sans dupliquer la logique.

def verifier_invariants_pero(
    flux_employeur_brut_annuel: Euros,
    tx_forfait_social: TauxAnnuel,
    cout_entreprise_annuel: Euros,
    ligne: LigneHorizonReceptacle,
    tolerance: Euros = 0.01,
) -> None:
    """Vérifie les 2 invariants algébriques PERO-spécifiques.

    Complète les 2 invariants génériques de LigneHorizonReceptacle
    (effort_reel et valeur_nette) avec :

    Invariant PERO-1 : cout_entreprise = flux_employeur × (1 + forfait_social)
    Invariant PERO-2 : capital_projete = flux × ((1+r)^n - 1) / r
        (annuité constante, rendement = RENDEMENT_NOMINAL_ANNUEL)

    Args:
        flux_employeur_brut_annuel: cotisation employeur annuelle.
        tx_forfait_social: taux de forfait social appliqué.
        cout_entreprise_annuel: coût entreprise tel que calculé.
        ligne: ligne d'horizon à vérifier.
        tolerance: tolérance flottants (0,01 € par défaut).

    Raises:
        ValueError si un invariant est violé.
    """
    # Invariant PERO-1
    attendu_cout = (float(flux_employeur_brut_annuel)
                    * (1.0 + float(tx_forfait_social)))
    if abs(cout_entreprise_annuel - attendu_cout) > tolerance:
        raise ValueError(
            f"PERO invariant 1 violation : cout_entreprise="
            f"{cout_entreprise_annuel} ≠ flux × (1 + forfait_social) = "
            f"{attendu_cout} (tolérance {tolerance} €)."
        )
    # Invariant PERO-1bis : ligne porte le cout_entreprise
    if abs(ligne.cout_entreprise - attendu_cout) > tolerance:
        raise ValueError(
            f"PERO invariant 1bis violation : ligne.cout_entreprise="
            f"{ligne.cout_entreprise} ≠ "
            f"flux × (1 + forfait_social) = "
            f"{attendu_cout} (tolérance {tolerance} €)."
        )
    # Invariant PERO-2 (capitalisation annuité constante)
    n = int(ligne.horizon_annees)
    if RENDEMENT_NOMINAL_ANNUEL > 0.0:
        attendu_capital = (
            float(flux_employeur_brut_annuel)
            * (((1.0 + RENDEMENT_NOMINAL_ANNUEL) ** n) - 1.0)
            / RENDEMENT_NOMINAL_ANNUEL
        )
    else:
        attendu_capital = float(flux_employeur_brut_annuel) * n
    if abs(ligne.capital_projete - attendu_capital) > tolerance:
        raise ValueError(
            f"PERO invariant 2 violation : capital_projete="
            f"{ligne.capital_projete} ≠ annuité_constante({n} ans) "
            f"= {attendu_capital} (tolérance {tolerance} €)."
        )


# ============================================================
# SURFACE PUBLIQUE
# ============================================================
__all__ = [
    # Constantes doctrinales
    "TX_FORFAIT_SOCIAL_PERO",
    "TX_CSG_CRDS_PERO",
    "TX_PLAFOND_EXONERATION_REM",
    "PLAFOND_EXONERATION_PASS",
    "TX_PFU_GAINS_PERO",
    # Providers
    "obtenir_taux_forfait_social_pero",
    "obtenir_taux_ps_pero",
    "obtenir_plafond_pero",
    "est_eligible_pero",
    # Dataclass résultat
    "ResultatAllocationPero",
    # Fonction principale
    "allocation_pero",
    # Helper d'invariants
    "verifier_invariants_pero",
]
