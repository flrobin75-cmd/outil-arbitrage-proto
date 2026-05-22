"""
strategy/receptacles_orchestrateur.py — Orchestrateur passif d'allocation de flux.

Module v1.1 SP14 — scaffolding initial (mock fonctionnel).

Implémente les décisions **D-R4, D-R5, D-R6** de `ARCHITECTURE_RECEPTACLES.md` :

    D-R4 : 5 modules distincts (3 enveloppes + orchestrateur + wordings)
    D-R5 : Signature standardisée (profil, *, flux_disponible, horizons, audit)
    D-R6 : Orchestrateur PASSIF — composition seulement, ZÉRO logique métier

Périmètre SP14 — Mock fonctionnel
─────────────────────────────────
Le présent code constitue un **mock** au sens où :

  - La signature publique est définitive (D-R5)
  - La structure de la trace racine est définitive (cf. doctrine §6.4)
  - Les dataclass de résultat sont définitives (D-R4)
  - Les wordings transverses sont figés (D-R3, SP14)

…mais le **contenu calculé** est mocké :

  - Les 3 modules enveloppe `receptacles_perin`, `receptacles_pee`,
    `receptacles_pereco` ne sont pas encore implémentés (SP15-SP17).
  - L'orchestrateur SP14 produit donc des valeurs de **placeholder**
    (zéros, listes vides) pour démontrer que le pipeline complet
    (signature → trace → PDF audit) fonctionne **structurellement**.

Cela permet à SP14 de **valider immédiatement** :

  1. La signature publique est consommable
  2. La trace produite est rendable par `generer_pdf_audit`
  3. Les 51 invariants `test_renderer_invariants` restent verts
  4. Les 5 goldens existants restent conformes (preuve forte que v1.1
     n'altère pas le framework)

SP18 remplacera le mock par l'orchestration réelle des 3 modules
enveloppe (qui auront été implémentés par SP15-SP17).

Pattern conceptuel
──────────────────
L'analogie la plus proche dans le code existant est
`calcul_comparateur_regimes` de `strategy/comparateur_regimes.py` :

  - signature similaire `(profil, *, audit)`
  - produit une trace racine "Comparateur Régimes"
  - attache 4 sous-traces (une par régime)
  - ne calcule rien lui-même, délègue aux 4 modules métier

L'orchestrateur réceptacles fonctionne sur le même principe avec
3 enveloppes au lieu de 4 régimes.
"""

from dataclasses import dataclass, field
from typing import Optional

from core.audit import TraceAudit
from core.profil import Profil

from strategy.receptacles_wordings import (
    WORDING_REC_CONVENTION_RENDEMENT,
    WORDING_REC_DISCLAIMER_COMPARABILITE,
    WORDING_REC_DISCLAIMER_PERIMETRE,
)


# ============================================================
# TYPE-ALIASES DOCUMENTAIRES (SP15, Q7=b)
# ============================================================
# Verrouillage sémantique du vocabulaire économique au niveau du
# typage. Aucun runtime check ici (Q7=b) — les invariants algébriques
# évidents sont vérifiés ailleurs par dataclass __post_init__ (Q7=c
# partiel). Référence doctrinale : ARCHITECTURE_RECEPTACLES.md §3.
#
# Convention : utiliser ces alias dans les signatures et docstrings
# des fonctions et dataclass métier pour expliciter l'unité de mesure
# et la sémantique attendue.
Euros = float          # montant en euros nominaux (cf. D-R14)
TauxAnnuel = float     # ratio sans dimension, ex. 0.02 = 2 %/an
Annees = int           # horizon en années pleines (cf. §3.4)


# ============================================================
# CONSTANTES TRANSVERSES
# ============================================================
# Horizons par défaut (D-R9). Cohérence : disponibilité PEE (5 ans),
# moyen terme (10 ans), horizon retraite (20 ans).
HORIZONS_DEFAUT: tuple = (5, 10, 20)

# Hypothèse de rendement conventionnelle (D-R8).
RENDEMENT_NOMINAL_ANNUEL: TauxAnnuel = 0.02

# Liste des 3 enveloppes du périmètre v1.1 (D-R11).
# Conservée pour rétrocompatibilité historique (référencée par les
# anciens imports). Le périmètre v1.3 SP25 ajoute PERO en 4e
# position via ENVELOPPES_V1_3.
ENVELOPPES_V1_1: tuple = ("PERIN", "PEE", "PERECO")

# Liste des 4 enveloppes du périmètre v1.3 (SP25 : ajout PERO).
# Ordre doctrinal strict PERIN → PEE → PERECO → PERO.
ENVELOPPES_V1_3: tuple = ("PERIN", "PEE", "PERECO", "PERO")


# ============================================================
# DATACLASS HIÉRARCHIQUE (Q1=b validé SP14)
# ============================================================
@dataclass
class LigneHorizonReceptacle:
    """Métriques d'une enveloppe à un horizon donné.

    8 dimensions économiques verrouillées par `ARCHITECTURE_RECEPTACLES.md` §2.3 et §3.

    Note SP14 : ce dataclass est définitif. Les modules SP15-SP17
    remplissent leurs propres instances, l'orchestrateur les agrège
    via les `ResultatAllocation<Enveloppe>` ci-dessous.

    SP15 — Q7=c partiel : __post_init__ valide les invariants
    algébriques évidents (effort réel, valeur nette). Aucune
    validation interprétative ou métier complexe (conforme à la
    discipline « validations structurelles, pas interprétatives »).
    Tolérance numérique : 0,01 € pour absorber les flottants.
    """
    horizon_annees: Annees                 # 5, 10, 20
    # Dimensions économiques (cf. §3 vocabulaire verrouillé)
    flux_entrant_brut: Euros = 0.0         # EUR — versement nominal en année 0
    economie_fiscale_immediate: Euros = 0.0  # EUR — réduction IR/IS en année 0
    effort_reel: Euros = 0.0               # EUR — flux brut - économie fiscale
    capital_projete: Euros = 0.0           # EUR — stock à l'horizon
    fiscalite_sortie: Euros = 0.0          # EUR — IR + PS à la sortie
    valeur_nette: Euros = 0.0              # EUR — capital projeté - fiscalité sortie
    cout_entreprise: Euros = 0.0           # EUR — coût employeur (cotisations, abondement)
    # Dimension qualitative
    disponibilite: str = ""                # Texte court résumant les conditions de retrait

    def __post_init__(self) -> None:
        """Invariants algébriques évidents (Q7=c partiel).

        Validés uniquement si les 3 valeurs sources sont non-nulles.
        Tolérance 0,01 € pour absorber les arrondis flottants.

        Note discipline : ces vérifications sont **structurelles**
        (cohérence d'identités algébriques), pas **interprétatives**
        (qui détecteraient des « valeurs suspectes »). Les modules
        SP15-SP17 peuvent donc remplir partiellement la dataclass
        sans déclencher de faux positifs.
        """
        # Invariant 1 : effort_reel == flux_entrant_brut - economie_fiscale_immediate
        if (self.flux_entrant_brut != 0.0
                and self.effort_reel != 0.0):
            attendu_effort = (
                self.flux_entrant_brut - self.economie_fiscale_immediate
            )
            if abs(self.effort_reel - attendu_effort) > 0.01:
                raise ValueError(
                    f"LigneHorizonReceptacle invariant violation : "
                    f"effort_reel={self.effort_reel} ≠ "
                    f"flux_entrant_brut - economie_fiscale_immediate = "
                    f"{attendu_effort} (tolérance 0,01 €)."
                )
        # Invariant 2 : valeur_nette == capital_projete - fiscalite_sortie
        if (self.capital_projete != 0.0
                and self.valeur_nette != 0.0):
            attendu_nette = (
                self.capital_projete - self.fiscalite_sortie
            )
            if abs(self.valeur_nette - attendu_nette) > 0.01:
                raise ValueError(
                    f"LigneHorizonReceptacle invariant violation : "
                    f"valeur_nette={self.valeur_nette} ≠ "
                    f"capital_projete - fiscalite_sortie = "
                    f"{attendu_nette} (tolérance 0,01 €)."
                )


@dataclass
class ResultatAllocationEnveloppe:
    """Résultat d'une enveloppe sur les 3 horizons.

    Base commune aux 3 dataclass spécialisés (PERIN, PEE, PERECO).
    Chaque module enveloppe (SP15-SP17) peut étendre cette structure
    avec des champs spécifiques sans casser le contrat.
    """
    enveloppe: str                         # "PERIN" | "PEE" | "PERECO"
    accessible: bool = True                # False si non accessible pour le profil
    motif_inaccessibilite: str = ""        # Si accessible=False, raison
    lignes_par_horizon: list = field(default_factory=list)  # list[LigneHorizonReceptacle]


@dataclass
class ResultatAllocationPerin(ResultatAllocationEnveloppe):
    """Résultat spécifique PERIN (SP15).

    SP14 : héritage simple, pas de champs spécifiques au mock.
    SP15 ajoutera potentiellement : plafond_annuel_applique,
    plafonds_anterieurs_consommes, etc.
    """
    pass


@dataclass
class ResultatAllocationPee(ResultatAllocationEnveloppe):
    """Résultat spécifique PEE (SP16).

    SP16 ajoutera potentiellement : abondement_employeur,
    plafond_abondement_atteint, etc.
    """
    pass


@dataclass
class ResultatAllocationPereco(ResultatAllocationEnveloppe):
    """Résultat spécifique PERECO (SP17)."""
    pass


@dataclass
class ResultatAllocationReceptacles:
    """Résultat consolidé de l'allocation réceptacles.

    Structure hiérarchique (Q1=b validé SP14, étendu SP25) :
      - 1 ResultatAllocationReceptacles
        └── 4 ResultatAllocationEnveloppe (PERIN, PEE, PERECO, PERO)
            └── 3 LigneHorizonReceptacle (5, 10, 20 ans) par enveloppe

    Soit 4 × 3 = 12 cellules de comparaison cabinet (SP25 :
    extension de 9 à 12 cellules, PERO en 4e position doctrinal).

    Disclaimers permanents en champs par défaut (pattern hérité de
    ResultatComparateurRegimes).

    Note SP25 : le champ `pero` est en 4e position dans l'ordre
    doctrinal PERIN → PEE → PERECO → PERO. Sa valeur par défaut
    est construite dynamiquement dans `allocation_receptacles`
    selon le `taux_cotisation_pero` du profil (0 % par défaut →
    PERO calculé à zéro, b1 validé SP25).
    """
    profil: Profil
    flux_disponible: float                 # EUR — input
    horizons: tuple                         # ex. (5, 10, 20)
    perin: ResultatAllocationPerin
    pee: ResultatAllocationPee
    pereco: ResultatAllocationPereco
    pero: "ResultatAllocationPero" = None   # SP25 — 4e enveloppe (cf. allocation_receptacles)
    # Disclaimers permanents (D-R3, SP14)
    disclaimer_perimetre: str = WORDING_REC_DISCLAIMER_PERIMETRE
    disclaimer_comparabilite: str = WORDING_REC_DISCLAIMER_COMPARABILITE
    convention_rendement: str = WORDING_REC_CONVENTION_RENDEMENT


# ============================================================
# ORCHESTRATEUR PASSIF — SIGNATURE DÉFINITIVE SP14
# ============================================================
def allocation_receptacles(
    profil: Profil,
    *,
    flux_disponible: float,
    horizons: tuple = HORIZONS_DEFAUT,
    audit: Optional[TraceAudit] = None,
) -> ResultatAllocationReceptacles:
    """Orchestrateur passif : compose les 3 modules enveloppe.

    Signature définitive SP14 (D-R5) :

      - `profil` : Profil du dirigeant (existant)
      - `flux_disponible` : EUR — montant à comparer entre enveloppes (input,
         pas de dimensionnement, cf. D-R12)
      - `horizons` : tuple d'années (défaut (5, 10, 20), cf. D-R9)
      - `audit` : TraceAudit optionnelle (MODE_AUDIT) — side channel

    Logique SP14 (mock) :

      1. Construit le squelette de trace racine "Réceptacles" + 5 étapes méta
      2. Pour chaque enveloppe, appelle le module dédié (SP15-SP17). En SP14,
         appelle un placeholder qui produit un résultat à zéro.
      3. Compose les 3 résultats dans `ResultatAllocationReceptacles`.
      4. Aucune logique métier (D-R6).

    Args:
        profil: Profil du dirigeant.
        flux_disponible: Flux à allouer (EUR).
        horizons: Horizons en années.
        audit: Trace d'audit optionnelle.

    Returns:
        ResultatAllocationReceptacles avec 3 enveloppes × N horizons.
    """
    if audit is not None:
        _instrumenter_etapes_meta(
            audit, flux_disponible=flux_disponible,
            horizons=horizons,
        )

    # Appels modules enveloppe.
    # SP15 : PERIN réel (allocation_perin de strategy.receptacles_perin).
    # SP16-SP17 : PEE et PERECO restent mockés en attendant leurs propres
    #             sous-passes. Cohérence du pattern progressif.
    #
    # Import paresseux pour éviter le cycle import :
    #   receptacles_perin.py importe depuis receptacles_orchestrateur.py
    #   (Euros, LigneHorizonReceptacle, ResultatAllocationPerin).
    #   L'import à l'intérieur de la fonction casse ce cycle proprement
    #   et ne pénalise pas les performances (import Python mémoïsé).
    # 1/3 — PERIN (SP15 réel via allocation_perin, import paresseux pour cycle).
    from strategy.receptacles_perin import allocation_perin
    if audit is not None:
        sub_perin = TraceAudit(
            regime="Réceptacle PERIN",
            profil_resume=(
                f"Flux disponible {float(flux_disponible):.0f} €, "
                f"horizons {horizons}"
            ),
        )
        resultat_perin = allocation_perin(
            profil, flux_disponible=flux_disponible,
            horizons=horizons, audit=sub_perin,
        )
        audit.attacher_sous_trace("ligne_perin", sub_perin)
    else:
        resultat_perin = allocation_perin(
            profil, flux_disponible=flux_disponible,
            horizons=horizons, audit=None,
        )

    # 2/3 — PEE (SP16 réel via allocation_pee, import paresseux pour cycle).
    from strategy.receptacles_pee import allocation_pee
    if audit is not None:
        sub_pee = TraceAudit(
            regime="Réceptacle PEE",
            profil_resume=(
                f"Flux salarié {float(flux_disponible):.0f} €, "
                f"horizons {horizons}"
            ),
        )
        resultat_pee = allocation_pee(
            profil, flux_disponible=flux_disponible,
            horizons=horizons, audit=sub_pee,
        )
        audit.attacher_sous_trace("ligne_pee", sub_pee)
    else:
        resultat_pee = allocation_pee(
            profil, flux_disponible=flux_disponible,
            horizons=horizons, audit=None,
        )

    # 3/3 — PERECO (SP17 réel, hybride PERIN+PEE).
    from strategy.receptacles_pereco import allocation_pereco
    if audit is not None:
        sub_pereco = TraceAudit(
            regime="Réceptacle PERECO",
            profil_resume=(
                f"Flux salarié {float(flux_disponible):.0f} €, "
                f"horizons {horizons}"
            ),
        )
        resultat_pereco = allocation_pereco(
            profil, flux_disponible=flux_disponible,
            horizons=horizons, audit=sub_pereco,
        )
        audit.attacher_sous_trace("ligne_pereco", sub_pereco)
    else:
        resultat_pereco = allocation_pereco(
            profil, flux_disponible=flux_disponible,
            horizons=horizons, audit=None,
        )

    # 4/4 — PERO (SP25 réel, 4e enveloppe doctrinale).
    # Lecture des inputs depuis le profil (A-Q1=β validé SP25) :
    #   - assiette = profil.salaire_brut_assimile (champ existant)
    #   - taux = profil.taux_cotisation_pero (nouveau champ SP25,
    #     défaut 0 % → PERO calculé à zéro, b1 validé SP25)
    from strategy.receptacles_pero import allocation_pero
    salaire_brut_pero = float(profil.salaire_brut_assimile)
    taux_pero = float(profil.taux_cotisation_pero)

    # Étape compacte de traçabilité (subsidiaire 2 validée SP25) :
    # documente explicitement la source des inputs PERO.
    if audit is not None:
        audit.add(
            code="REC_PERO_INPUTS_LUS_PROFIL",
            label=("Inputs PERO lus depuis le profil "
                   "(salaire brut assimilé + taux de cotisation)"),
            valeur=taux_pero,
            unite="taux",
            hypotheses={
                "salaire_brut_assimile_pero": salaire_brut_pero,
                "taux_cotisation_pero": taux_pero,
            },
        )

    if audit is not None:
        sub_pero = TraceAudit(
            regime="Réceptacle PERO",
            profil_resume=(
                f"Salaire brut {salaire_brut_pero:.0f} €, "
                f"taux cotisation {taux_pero*100:.2f}%, "
                f"horizons {horizons}"
            ),
        )
        resultat_pero = allocation_pero(
            profil,
            salaire_brut_annuel=salaire_brut_pero,
            taux_cotisation_pero=taux_pero,
            horizons=horizons,
            audit=sub_pero,
        )
        audit.attacher_sous_trace("ligne_pero", sub_pero)
    else:
        resultat_pero = allocation_pero(
            profil,
            salaire_brut_annuel=salaire_brut_pero,
            taux_cotisation_pero=taux_pero,
            horizons=horizons,
            audit=None,
        )

    # SP18 — Étapes méta récapitulatives par horizon (Q1=c validé,
    # étendu SP25 avec PERO en 4e position).
    # Pure alignement factuel cross-enveloppes — aucune prescription,
    # aucun classement, aucun score. L'ordre
    # PERIN → PEE → PERECO → PERO est strict dans les hypothèses.
    # Le `valeur` de chaque étape récapitulative est neutre (nombre
    # d'enveloppes alignées = 4 depuis SP25, contre 3 en SP18-SP24) ;
    # les vraies valeurs économiques vivent dans `hypotheses` pour
    # rester lisibles sans induire de comparaison numérique implicite.
    if audit is not None:
        _instrumenter_etapes_recapitulatives(
            audit,
            resultat_perin=resultat_perin,
            resultat_pee=resultat_pee,
            resultat_pereco=resultat_pereco,
            resultat_pero=resultat_pero,
            horizons=horizons,
        )

    return ResultatAllocationReceptacles(
        profil=profil,
        flux_disponible=flux_disponible,
        horizons=horizons,
        perin=resultat_perin,
        pee=resultat_pee,
        pereco=resultat_pereco,
        pero=resultat_pero,
    )


# ============================================================
# INSTRUMENTATION MODE_AUDIT — TRACE RACINE
# ============================================================
def _instrumenter_etapes_meta(audit: TraceAudit, *,
                              flux_disponible: float,
                              horizons: tuple) -> None:
    """Ajoute les étapes méta au niveau racine de la trace.

    Conformément à la doctrine §6.4 : 5 étapes méta + 4 sous-traces
    enveloppe (SP25 : extension de 3 à 4 avec PERO). Cette fonction
    ne pose que les étapes méta.

    Étapes méta produites :
      - REC_NB_ENVELOPPES : nombre d'enveloppes comparées (4 depuis SP25)
      - REC_FLUX_DISPONIBLE : input flux à allouer
      - REC_HORIZONS_NB : nombre d'horizons retenus
      - REC_DISCLAIMERS_NB : nombre de disclaimers permanents (3)
      - REC_RENDEMENT_HYPOTHESE : taux de rendement conventionnel

    Toutes les étapes sont des **étapes racines** (parent_id=None),
    conformément à D-R10 (préservation G4).
    """
    audit.add(
        code="REC_NB_ENVELOPPES",
        label="Nombre d'enveloppes comparées",
        valeur=len(ENVELOPPES_V1_3),
        unite="count",
        hypotheses={
            "enveloppes_couvertes": list(ENVELOPPES_V1_3),
            "regle": ("Périmètre v1.3 (SP25) : "
                      "PERIN + PEE + PERECO + PERO"),
        },
    )
    audit.add(
        code="REC_FLUX_DISPONIBLE",
        label="Flux disponible à allouer (input)",
        valeur=flux_disponible,
        unite="EUR",
        hypotheses={
            "convention": "Le flux est fourni en input. Le module ne dimensionne pas (D-R12).",
        },
    )
    audit.add(
        code="REC_HORIZONS_NB",
        label="Nombre d'horizons projetés",
        valeur=len(horizons),
        unite="count",
        hypotheses={
            "horizons_annees": list(horizons),
            "default": list(HORIZONS_DEFAUT),
        },
    )
    audit.add(
        code="REC_RENDEMENT_HYPOTHESE",
        label="Taux de rendement nominal annuel (hypothèse conventionnelle)",
        valeur=RENDEMENT_NOMINAL_ANNUEL,
        unite="ratio",
        hypotheses={
            "convention": "Capitalisation annuelle, déterministe, identique sur les 3 enveloppes.",
            "WORDING_REC_CONVENTION_RENDEMENT": WORDING_REC_CONVENTION_RENDEMENT,
        },
    )
    audit.add(
        code="REC_DISCLAIMERS_NB",
        label="Nombre de disclaimers permanents attachés au résultat",
        valeur=3,
        unite="count",
        hypotheses={
            "DISCLAIMER_PERIMETRE": WORDING_REC_DISCLAIMER_PERIMETRE,
            "DISCLAIMER_COMPARABILITE": WORDING_REC_DISCLAIMER_COMPARABILITE,
            "CONVENTION_RENDEMENT": WORDING_REC_CONVENTION_RENDEMENT,
        },
    )


# ============================================================
# INSTRUMENTATION SP18 — ÉTAPES RÉCAPITULATIVES CROSS-ENVELOPPES
# ============================================================
def _instrumenter_etapes_recapitulatives(
    audit: TraceAudit, *,
    resultat_perin: "ResultatAllocationPerin",
    resultat_pee: "ResultatAllocationPee",
    resultat_pereco: "ResultatAllocationPereco",
    resultat_pero: "ResultatAllocationPero",
    horizons: tuple,
) -> None:
    """Ajoute des étapes méta récapitulatives par horizon (SP18,
    étendu SP25 à 4 enveloppes).

    Pour chaque horizon, produit 3 étapes méta cross-enveloppes alignant
    de manière **strictement descriptive** les valeurs économiques des
    4 enveloppes (SP25 : ajout PERO en 4e position) : valeur nette,
    effort réel, coût entreprise.

    Discipline doctrinale SP18 préservée intégralement (SP25 = ajout
    d'une enveloppe, pas refonte) :

      - **Aucun classement**, aucun score, aucune notion de
        « meilleure enveloppe ». Pure alignement factuel.
      - **Stabilité d'ordre stricte** : PERIN → PEE → PERECO → PERO
        toujours dans cet ordre (SP25), dans les codes étapes ET
        dans les hypothèses.
      - Le `valeur` de chaque étape est neutre (= 4 depuis SP25,
        nombre d'enveloppes alignées). Les valeurs économiques vivent
        dans `hypotheses` pour rester lisibles sans induire de
        comparaison numérique implicite sur le champ `valeur`.

    Étapes produites par horizon h (inchangées vs SP18 — B-Q1=α
    validé : pas de nouvelle dimension RECAP en SP25) :
      - REC_RECAP_VALEUR_NETTE_{h}ANS
      - REC_RECAP_EFFORT_REEL_{h}ANS
      - REC_RECAP_COUT_ENTREPRISE_{h}ANS

    Soit 3 étapes × N horizons = 9 étapes méta en configuration par
    défaut (3 horizons), toutes au niveau racine de la trace
    (préservation D-R10 : aucune étape `parent_id != None`).

    Args:
        audit: TraceAudit racine sur laquelle attacher les étapes.
        resultat_perin: ResultatAllocationPerin (déjà calculé).
        resultat_pee: ResultatAllocationPee (déjà calculé).
        resultat_pereco: ResultatAllocationPereco (déjà calculé).
        resultat_pero: ResultatAllocationPero (déjà calculé, SP25).
        horizons: Tuple d'années à récapituler.
    """
    # Indexation par horizon pour lookup O(1) — l'ordre des lignes
    # par horizon est garanti identique entre les 4 enveloppes
    # (chacun applique la même boucle `for h in horizons`).
    perin_par_horizon = {
        l.horizon_annees: l for l in resultat_perin.lignes_par_horizon
    }
    pee_par_horizon = {
        l.horizon_annees: l for l in resultat_pee.lignes_par_horizon
    }
    pereco_par_horizon = {
        l.horizon_annees: l for l in resultat_pereco.lignes_par_horizon
    }
    pero_par_horizon = {
        l.horizon_annees: l for l in resultat_pero.lignes_par_horizon
    }

    for h in horizons:
        ligne_perin = perin_par_horizon.get(h)
        ligne_pee = pee_par_horizon.get(h)
        ligne_pereco = pereco_par_horizon.get(h)
        ligne_pero = pero_par_horizon.get(h)

        # Sécurité : si une enveloppe n'a pas la ligne pour cet horizon
        # (cas pathologique), on skip — le calcul de l'orchestrateur
        # serait alors structurellement inconsistant et la trace le
        # signalerait via les sous-traces enveloppe.
        # SP25 : PERO peut légitimement avoir lignes_par_horizon=[] si
        # le profil n'est pas éligible (cf. allocation_pero). On ne
        # skip pas dans ce cas : on documente PERO comme None dans
        # les hypothèses pour préserver la stabilité d'ordre.
        if ligne_perin is None or ligne_pee is None or ligne_pereco is None:
            continue

        # 1. Récap valeur nette (alignement factuel)
        audit.add(
            code=f"REC_RECAP_VALEUR_NETTE_{h}ANS",
            label=f"Récapitulatif des valeurs nettes à {h} ans (alignement descriptif)",
            valeur=4,  # nombre d'enveloppes alignées SP25, pas une métrique économique
            unite="count",
            hypotheses={
                "valeur_nette_PERIN": round(ligne_perin.valeur_nette, 2),
                "valeur_nette_PEE": round(ligne_pee.valeur_nette, 2),
                "valeur_nette_PERECO": round(ligne_pereco.valeur_nette, 2),
                "valeur_nette_PERO": (round(ligne_pero.valeur_nette, 2)
                                      if ligne_pero is not None else None),
                "ordre_stable": "PERIN → PEE → PERECO → PERO (SP25)",
                "nature": ("Alignement factuel descriptif des 4 "
                           "enveloppes du périmètre v1.3 (SP25)."),
            },
        )

        # 2. Récap effort réel salarié
        audit.add(
            code=f"REC_RECAP_EFFORT_REEL_{h}ANS",
            label=f"Récapitulatif des efforts réels salariés à {h} ans",
            valeur=4, unite="count",
            hypotheses={
                "effort_reel_PERIN": round(ligne_perin.effort_reel, 2),
                "effort_reel_PEE": round(ligne_pee.effort_reel, 2),
                "effort_reel_PERECO": round(ligne_pereco.effort_reel, 2),
                "effort_reel_PERO": (round(ligne_pero.effort_reel, 2)
                                     if ligne_pero is not None else None),
                "ordre_stable": "PERIN → PEE → PERECO → PERO (SP25)",
            },
        )

        # 3. Récap coût entreprise
        audit.add(
            code=f"REC_RECAP_COUT_ENTREPRISE_{h}ANS",
            label=f"Récapitulatif des coûts entreprise à {h} ans",
            valeur=4, unite="count",
            hypotheses={
                "cout_entreprise_PERIN": round(ligne_perin.cout_entreprise, 2),
                "cout_entreprise_PEE": round(ligne_pee.cout_entreprise, 2),
                "cout_entreprise_PERECO": round(ligne_pereco.cout_entreprise, 2),
                "cout_entreprise_PERO": (round(ligne_pero.cout_entreprise, 2)
                                         if ligne_pero is not None else None),
                "ordre_stable": "PERIN → PEE → PERECO → PERO (SP25)",
            },
        )


# ============================================================
# MOCKS — REMPLACÉS PAR SP15-SP17
# ============================================================
def _mock_allocation_perin(
    profil: Profil, *,
    flux_disponible: float,
    horizons: tuple,
    audit: Optional[TraceAudit] = None,
) -> ResultatAllocationPerin:
    """Mock SP14 du module PERIN.

    OBSOLÈTE depuis SP15 : `allocation_receptacles` appelle directement
    `strategy.receptacles_perin.allocation_perin`. Cette fonction est
    conservée pour permettre des tests isolés du squelette ou des
    régressions diagnostiquées. Ne pas l'utiliser en production.
    """
    if audit is not None:
        sub = TraceAudit(
            regime="Réceptacle PERIN (mock SP14)",
            profil_resume=f"Flux={flux_disponible}, horizons={horizons}",
        )
        sub.add(
            code="REC_PERIN_MOCK",
            label="Placeholder SP14 — module PERIN à implémenter en SP15",
            valeur=0.0, unite="EUR",
            hypotheses={
                "statut": "mock SP14",
                "implementation_prevue": "SP15",
            },
            notes="Mock fonctionnel — sera remplacé par module métier SP15.",
        )
        audit.attacher_sous_trace("ligne_perin", sub)

    return ResultatAllocationPerin(
        enveloppe="PERIN",
        accessible=True,
        lignes_par_horizon=[
            LigneHorizonReceptacle(horizon_annees=h)
            for h in horizons
        ],
    )


def _mock_allocation_pee(
    profil: Profil, *,
    flux_disponible: float,
    horizons: tuple,
    audit: Optional[TraceAudit] = None,
) -> ResultatAllocationPee:
    """Mock SP14 du module PEE.

    OBSOLÈTE depuis SP16 : `allocation_receptacles` appelle directement
    `strategy.receptacles_pee.allocation_pee`. Conservée pour tests
    isolés du squelette.
    """
    if audit is not None:
        sub = TraceAudit(
            regime="Réceptacle PEE (mock SP14)",
            profil_resume=f"Flux={flux_disponible}, horizons={horizons}",
        )
        sub.add(
            code="REC_PEE_MOCK",
            label="Placeholder SP14 — module PEE à implémenter en SP16",
            valeur=0.0, unite="EUR",
            hypotheses={
                "statut": "mock SP14",
                "implementation_prevue": "SP16",
            },
            notes="Mock fonctionnel — sera remplacé par module métier SP16.",
        )
        audit.attacher_sous_trace("ligne_pee", sub)

    return ResultatAllocationPee(
        enveloppe="PEE",
        accessible=True,
        lignes_par_horizon=[
            LigneHorizonReceptacle(horizon_annees=h)
            for h in horizons
        ],
    )


def _mock_allocation_pereco(
    profil: Profil, *,
    flux_disponible: float,
    horizons: tuple,
    audit: Optional[TraceAudit] = None,
) -> ResultatAllocationPereco:
    """Mock SP14 du module PERECO.

    OBSOLÈTE depuis SP17 : `allocation_receptacles` appelle directement
    `strategy.receptacles_pereco.allocation_pereco`. Conservée pour
    tests isolés du squelette.
    """
    if audit is not None:
        sub = TraceAudit(
            regime="Réceptacle PERECO (mock SP14)",
            profil_resume=f"Flux={flux_disponible}, horizons={horizons}",
        )
        sub.add(
            code="REC_PERECO_MOCK",
            label="Placeholder SP14 — module PERECO à implémenter en SP17",
            valeur=0.0, unite="EUR",
            hypotheses={
                "statut": "mock SP14",
                "implementation_prevue": "SP17",
            },
            notes="Mock fonctionnel — sera remplacé par module métier SP17.",
        )
        audit.attacher_sous_trace("ligne_pereco", sub)

    return ResultatAllocationPereco(
        enveloppe="PERECO",
        accessible=True,
        lignes_par_horizon=[
            LigneHorizonReceptacle(horizon_annees=h)
            for h in horizons
        ],
    )


# ============================================================
# SURFACE PUBLIQUE
# ============================================================
__all__ = [
    # Constantes
    "HORIZONS_DEFAUT",
    "RENDEMENT_NOMINAL_ANNUEL",
    "ENVELOPPES_V1_1",
    # Dataclass
    "LigneHorizonReceptacle",
    "ResultatAllocationEnveloppe",
    "ResultatAllocationPerin",
    "ResultatAllocationPee",
    "ResultatAllocationPereco",
    "ResultatAllocationReceptacles",
    # Fonction principale
    "allocation_receptacles",
]
