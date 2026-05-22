"""
strategy/receptacles_pee.py — Module métier PEE (v1.1 SP16).

Module d'allocation d'un versement salarié dans le PEE (Plan d'Épargne
Entreprise), avec prise en compte de l'abondement employeur, des
prélèvements sociaux à l'entrée (CSG-CRDS sur abondement), de la
capitalisation conventionnelle, et de la fiscalité de sortie au-delà
de 5 ans (exonération IR, PFU 17,2 % sur gains uniquement).

Périmètre SP16 (Q1=b validé)
─────────────────────────────
- Versement volontaire salarié
- Abondement employeur (Q2=c : lecture profil si présent, fallback
  doctrinal 100 % du versement plafonné à 8 % PASS = 3 844,80 €)
- CSG-CRDS sur abondement (Q6=b : prélèvement explicite, étape audit
  dédiée)
- Capitalisation conventionnelle annuelle simple (D-R8, 2 %)
- Sortie au-delà de 5 ans : versement + abondement nets exonérés
  d'IR, gains soumis à PS 17,2 %
- **Hors SP16** :
  - Cas de déblocage anticipé (Q7=a : on suppose tous horizons ≥ 5 ans)
  - Intéressement / participation (mentionnés à titre informatif dans
    le wording d'abondement mais pas modélisés en calcul)
  - Scénarios d'abondement variable / plafond complémentaire 3× versement

Sémantique économique (résolution de tension Q4 / Q5)
──────────────────────────────────────────────────────
PEE introduit une dualité que PERIN ne connaît pas : flux mixte
salarié / employeur. La doctrine SP13 §3 verrouille le vocabulaire
du dataclass `LigneHorizonReceptacle` ; SP16 préserve cette
sémantique sans la déformer pour PEE :

  - `flux_entrant_brut` : **ce que le salarié verse depuis son
    patrimoine net** (versement salarié, hors abondement).
    Cohérent avec PERIN où c'est le versement du dirigeant.

  - `economie_fiscale_immediate` : **0 pour PEE**. Le PEE n'offre
    pas de déductibilité IR à l'entrée (Q5=ii). L'avantage
    économique PEE est l'abondement, qui est instrumenté
    séparément et reflété dans `capital_projete`.

  - `effort_reel` : flux salarié (égal à `flux_entrant_brut`
    puisque économie nulle). Invariant `__post_init__` satisfait.

  - `capital_projete` : (flux_salarié + abondement_net) capitalisé.
    L'abondement vient augmenter le capital sans augmenter l'effort.

  - `cout_entreprise` : abondement BRUT versé par l'employeur
    (avant CSG-CRDS prélevée à la source).

L'abondement et ses frottements (CSG-CRDS) sont **visibles dans les
étapes audit** (codes dédiés `REC_PEE_ABONDEMENT_EMPLOYEUR_BRUT`,
`REC_PEE_CSG_CRDS_ABONDEMENT`, `REC_PEE_ABONDEMENT_EMPLOYEUR_NET`,
`REC_PEE_FLUX_TOTAL_VERSE`), conformément au principe « la
décomposition vit dans la trace, pas dans le dataclass ».

Référence doctrinale : ARCHITECTURE_RECEPTACLES.md §3, §6.4, §7.
"""

from typing import Optional

from core.audit import TraceAudit
from core.profil import Profil, PASS_2026

from strategy.receptacles_orchestrateur import (
    Euros, TauxAnnuel, Annees,
    LigneHorizonReceptacle, ResultatAllocationPee,
    RENDEMENT_NOMINAL_ANNUEL,
)
from strategy.receptacles_wordings import (
    WORDING_REC_CONVENTION_RENDEMENT,
    WORDING_PEE_ABONDEMENT_EMPLOYEUR,
    WORDING_PEE_CSG_CRDS_ABONDEMENT,
    WORDING_PEE_DISPONIBILITE_5ANS,
    WORDING_PEE_EXONERATION_PV_SORTIE,
)


# ============================================================
# CONSTANTES SPÉCIFIQUES PEE
# ============================================================
# Plafond légal annuel de l'abondement employeur (Code travail
# art. L3332-11) : 8 % du PASS, soit 3 844,80 € en 2026.
PLAFOND_ABONDEMENT_PEE: Euros = 0.08 * PASS_2026

# Plafond complémentaire : 3 fois le versement individuel (hors
# périmètre SP16, on retient seulement le plafond absolu 8 % PASS
# combiné au plafond 100 % du versement par défaut).

# CSG-CRDS sur abondement : 9,7 % (CSG 9,2 % + CRDS 0,5 %)
# Code de la sécurité sociale art. L136-1 et L136-2
TX_CSG_CRDS_ABONDEMENT_PEE: TauxAnnuel = 0.097

# Prélèvements sociaux sur gains à la sortie (au-delà de 5 ans)
# Référence : CGI art. 81 bis. Pas d'IR sur les versements et
# abondement à la sortie au-delà de 5 ans (exonération PV).
TX_PS_GAINS_PEE: TauxAnnuel = 0.172


# ============================================================
# PROVIDERS DOCTRINAUX (Q2=c, G-2)
# ============================================================
def obtenir_taux_abondement_pee(profil: Profil) -> TauxAnnuel:
    """Provider doctrinal : taux d'abondement employeur PEE.

    Lecture profil si attribut `taux_abondement_pee` présent, sinon
    fallback doctrinal **100 % du versement salarié** (Q8=a). Le
    fallback est doctrinal mais explicite : il sera tracé dans les
    hypothèses audit avec wording dédié.

    Note : ce taux représente l'abondement BRUT en pourcentage du
    versement salarié. Il sera ensuite plafonné par
    `PLAFOND_ABONDEMENT_PEE` au moment du calcul, et la CSG-CRDS sera
    prélevée pour obtenir le montant net effectivement crédité.

    Args:
        profil: Profil du dirigeant/salarié.

    Returns:
        Taux d'abondement (ex. 1.0 = 100 %).
    """
    taux = getattr(profil, "taux_abondement_pee", None)
    if taux is None:
        return 1.0  # fallback doctrinal Q8=a : 100 % du versement
    return float(taux)


def obtenir_plafond_abondement_pee(profil: Profil) -> Euros:
    """Provider doctrinal : plafond légal annuel de l'abondement PEE.

    Constante doctrinale 8 % du PASS (art. L3332-11), retournée
    indépendamment du profil. La signature inclut `profil` pour
    cohérence avec les autres providers et anticipation v1.2 (où
    certains profils pourraient avoir des règles spécifiques).

    Args:
        profil: Profil (non utilisé en SP16, signature cohérente).

    Returns:
        Plafond annuel en euros.
    """
    return PLAFOND_ABONDEMENT_PEE


def est_eligible_pee(profil: Profil) -> bool:
    """Provider doctrinal : éligibilité PEE du profil.

    Le PEE est en principe ouvert aux salariés des entreprises ayant
    mis en place le dispositif. Pour v1.1, on retient une éligibilité
    universelle (l'outil simule le comportement économique en
    supposant que le dispositif existe). Le cabinet apprécie au cas
    par cas si le PEE est effectivement accessible au profil étudié.

    Args:
        profil: Profil du dirigeant/salarié.

    Returns:
        True systématiquement en SP16.
    """
    return True


# ============================================================
# CALCULS ÉCONOMIQUES (helpers privés)
# ============================================================
def _capitaliser(flux_initial: Euros, taux_annuel: TauxAnnuel,
                 nb_annees: Annees) -> Euros:
    """Capitalisation conventionnelle annuelle simple.

    Identique à PERIN (D-R8 : taux fixe 2 % nominal, capitalisation
    annuelle déterministe). Pas de duplication doctrinale : le
    helper est local au module pour autonomie, mais la formule et la
    convention sont les mêmes.
    """
    if nb_annees < 0:
        return 0.0
    return flux_initial * ((1.0 + taux_annuel) ** nb_annees)


def _calculer_horizon(
    flux_salarie: Euros,
    abondement_brut: Euros,
    abondement_csg_crds: Euros,
    horizon: Annees,
    audit: Optional[TraceAudit] = None,
) -> LigneHorizonReceptacle:
    """Calcule les 8 dimensions économiques PEE pour un horizon donné.

    Logique économique SP16 :
      1. abondement_net = abondement_brut - abondement_csg_crds
      2. flux_total_verse = flux_salarié + abondement_net
      3. economie_fiscale_immediate = 0 (Q5=ii, PEE n'a pas de
         déductibilité IR à l'entrée).
      4. effort_reel = flux_salarié (Q4=III : le salarié n'a engagé
         que son propre versement, l'abondement est un cadeau).
      5. capital_projeté = capitalisation de flux_total_verse à 2 %/an.
      6. fiscalité de sortie (horizon ≥ 5 ans) :
         - Versements + abondement nets : exonérés d'IR (déjà nets)
         - Gains : PS 17,2 % (pas d'IR)
      7. valeur_nette = capital_projeté - fiscalité_sortie.
      8. cout_entreprise = abondement_brut (l'employeur a payé brut
         avant prélèvement à la source de la CSG-CRDS).
      9. disponibilité : 5 ans (texte qualitatif).

    Args:
        flux_salarie: Versement volontaire du salarié.
        abondement_brut: Abondement employeur brut versé.
        abondement_csg_crds: CSG-CRDS prélevée sur l'abondement.
        horizon: Années avant sortie.
        audit: TraceAudit pour instrumentation par horizon.

    Returns:
        LigneHorizonReceptacle pour cet horizon PEE.
    """
    # 1. Abondement net après CSG-CRDS
    abondement_net = abondement_brut - abondement_csg_crds

    # 2. Flux total effectivement versé dans l'enveloppe
    flux_total_verse = flux_salarie + abondement_net

    # 3-4. Sémantique dataclass (cf. docstring module)
    economie_fiscale = 0.0  # Q5=ii
    effort_reel = flux_salarie  # Q4=III : seul l'effort salarié compte

    # 5. Capital projeté (capitalise le total versé, pas le flux salarié seul)
    capital_projete = _capitaliser(
        flux_total_verse, RENDEMENT_NOMINAL_ANNUEL, horizon,
    )

    # 6. Fiscalité sortie (≥ 5 ans : exonération IR, PS sur gains seuls)
    gains = max(0.0, capital_projete - flux_total_verse)
    fiscalite_sortie = gains * TX_PS_GAINS_PEE

    # 7-8-9. Composition
    cout_entreprise = abondement_brut  # employeur a payé brut
    disponibilite_txt = (
        "Indisponible 5 ans à compter de chaque versement, puis "
        "sortie libre sans condition."
    )

    # Instrumentation sous-trace horizon (4 étapes structurées + audit)
    if audit is not None:
        audit.add(
            code=f"REC_PEE_FLUX_SALARIE_{horizon}ANS",
            label=f"Versement salarié alloué (horizon {horizon} ans)",
            valeur=round(flux_salarie, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PEE_ABONDEMENT_EMPLOYEUR_BRUT_{horizon}ANS",
            label="Abondement employeur brut versé",
            valeur=round(abondement_brut, 2), unite="EUR",
            hypotheses={
                "WORDING_PEE_ABONDEMENT_EMPLOYEUR":
                    WORDING_PEE_ABONDEMENT_EMPLOYEUR,
            },
        )
        audit.add(
            code=f"REC_PEE_CSG_CRDS_ABONDEMENT_{horizon}ANS",
            label="CSG-CRDS prélevée sur abondement (9,7 %)",
            valeur=round(abondement_csg_crds, 2), unite="EUR",
            hypotheses={
                "tx_csg_crds": TX_CSG_CRDS_ABONDEMENT_PEE,
                "WORDING_PEE_CSG_CRDS_ABONDEMENT":
                    WORDING_PEE_CSG_CRDS_ABONDEMENT,
            },
        )
        audit.add(
            code=f"REC_PEE_ABONDEMENT_EMPLOYEUR_NET_{horizon}ANS",
            label="Abondement employeur net effectivement crédité",
            valeur=round(abondement_net, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PEE_FLUX_TOTAL_VERSE_{horizon}ANS",
            label="Flux total versé dans l'enveloppe (salarié + abondement net)",
            valeur=round(flux_total_verse, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PEE_EFFORT_REEL_{horizon}ANS",
            label="Effort réel salarié (= versement salarié, l'abondement est un cadeau)",
            valeur=round(effort_reel, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PEE_CAPITAL_PROJETE_{horizon}ANS",
            label=f"Capital projeté à {horizon} ans (capitalisation conventionnelle)",
            valeur=round(capital_projete, 2), unite="EUR",
            hypotheses={
                "rendement_annuel": RENDEMENT_NOMINAL_ANNUEL,
                "convention": "Capitalisation annuelle simple, déterministe (D-R8).",
                "WORDING_REC_CONVENTION_RENDEMENT": WORDING_REC_CONVENTION_RENDEMENT,
            },
        )
        audit.add(
            code=f"REC_PEE_FISC_SORTIE_{horizon}ANS",
            label=f"Fiscalité de sortie à {horizon} ans (PS 17,2 % sur gains seuls)",
            valeur=round(fiscalite_sortie, 2), unite="EUR",
            hypotheses={
                "tx_ps_gains": TX_PS_GAINS_PEE,
                "gains_taxables": round(gains, 2),
                "WORDING_PEE_EXONERATION_PV_SORTIE":
                    WORDING_PEE_EXONERATION_PV_SORTIE,
            },
        )
        audit.add(
            code=f"REC_PEE_VALEUR_NETTE_{horizon}ANS",
            label=f"Valeur nette à {horizon} ans",
            valeur=round(capital_projete - fiscalite_sortie, 2), unite="EUR",
        )

    # Arrondi cohérent (cf. retour d'expérience SP15 : arrondir
    # avant composition pour éviter divergence d'un cent qui
    # déclencherait l'invariant __post_init__)
    flux_salarie_arr = round(flux_salarie, 2)
    economie_fiscale_arr = round(economie_fiscale, 2)
    effort_reel_arr = round(flux_salarie_arr - economie_fiscale_arr, 2)
    capital_projete_arr = round(capital_projete, 2)
    fiscalite_sortie_arr = round(fiscalite_sortie, 2)
    valeur_nette_arr = round(capital_projete_arr - fiscalite_sortie_arr, 2)
    cout_entreprise_arr = round(cout_entreprise, 2)

    return LigneHorizonReceptacle(
        horizon_annees=horizon,
        flux_entrant_brut=flux_salarie_arr,  # = effort salarié, pas le total
        economie_fiscale_immediate=economie_fiscale_arr,  # = 0 pour PEE
        effort_reel=effort_reel_arr,
        capital_projete=capital_projete_arr,
        fiscalite_sortie=fiscalite_sortie_arr,
        valeur_nette=valeur_nette_arr,
        cout_entreprise=cout_entreprise_arr,
        disponibilite=disponibilite_txt,
    )


# ============================================================
# FONCTION PUBLIQUE — SIGNATURE D-R5
# ============================================================
def allocation_pee(
    profil: Profil,
    *,
    flux_disponible: Euros,
    horizons: tuple = (5, 10, 20),
    audit: Optional[TraceAudit] = None,
) -> ResultatAllocationPee:
    """Alloue un versement salarié dans le PEE sur N horizons.

    Signature standardisée D-R5. Module métier consommé par
    l'orchestrateur `allocation_receptacles` ; peut être appelé
    autonomement pour analyse PEE isolée.

    Logique SP16 :
      1. Éligibilité (provider).
      2. Lire taux d'abondement (provider, lecture profil + fallback
         doctrinal Q8=a).
      3. Lire plafond légal abondement (provider, 8 % PASS).
      4. Calculer abondement brut = min(flux_disponible × taux, plafond).
      5. Calculer CSG-CRDS = abondement_brut × 9,7 %.
      6. Pour chaque horizon : calculer les 8 dimensions économiques.
      7. Instrumenter trace + retourner dataclass.

    Note : v1.1 ne gère pas le cas horizon < 5 ans (Q7=a). Si fourni,
    le calcul s'exécute mais le résultat est sémantiquement
    inapproprié (le PEE n'est pas disponible avant 5 ans hors cas
    légaux). Une étape audit explicite signale ce cas.

    Args:
        profil: Profil du dirigeant/salarié.
        flux_disponible: Versement salarié à allouer (D-R12 : pas
            dimensionné, juste input).
        horizons: Tuple d'années (défaut (5, 10, 20)).
        audit: TraceAudit optionnelle.

    Returns:
        ResultatAllocationPee contenant 1 LigneHorizonReceptacle par horizon.
    """
    # 1. Éligibilité
    eligible = est_eligible_pee(profil)
    flux_salarie = float(flux_disponible)

    # 2-3. Abondement brut + plafond
    taux_abondement = obtenir_taux_abondement_pee(profil)
    plafond_abondement = obtenir_plafond_abondement_pee(profil)
    abondement_theorique = flux_salarie * taux_abondement
    abondement_brut = min(abondement_theorique, plafond_abondement)
    abondement_plafonne = (abondement_theorique > plafond_abondement)

    # 5. CSG-CRDS
    abondement_csg_crds = abondement_brut * TX_CSG_CRDS_ABONDEMENT_PEE

    # Détection horizons hors période disponibilité (Q7=a : signalement
    # uniquement, pas d'erreur)
    horizons_inferieurs_5 = [h for h in horizons if h < 5]

    # Instrumentation racine de la sous-trace enveloppe
    if audit is not None:
        audit.add(
            code="REC_PEE_ELIGIBILITE",
            label="Éligibilité PEE du profil",
            valeur=1 if eligible else 0, unite="bool",
            hypotheses={
                "regle": (
                    "PEE accessible si l'entreprise a mis en place le "
                    "dispositif. v1.1 retient une éligibilité universelle "
                    "et délègue l'appréciation au cabinet."
                ),
                "WORDING_PEE_DISPONIBILITE_5ANS": WORDING_PEE_DISPONIBILITE_5ANS,
            },
        )
        audit.add(
            code="REC_PEE_FLUX_SALARIE_INPUT",
            label="Versement salarié à allouer (input)",
            valeur=round(flux_salarie, 2), unite="EUR",
        )
        audit.add(
            code="REC_PEE_TAUX_ABONDEMENT_APPLIQUE",
            label="Taux d'abondement employeur appliqué",
            valeur=taux_abondement, unite="ratio",
            hypotheses={
                "source": (
                    "Lecture profil si attribut taux_abondement_pee renseigné, "
                    "sinon fallback doctrinal 100 % (Q8=a SP16)."
                ),
            },
        )
        audit.add(
            code="REC_PEE_ABONDEMENT_PLAFOND_LEGAL",
            label="Plafond légal annuel de l'abondement PEE (8 % PASS)",
            valeur=round(plafond_abondement, 2), unite="EUR",
            doctrine_refs=("PASS_2026",),
            hypotheses={
                "regle": "Code travail art. L3332-11 : 8 % du PASS, soit 3 844,80 € en 2026.",
                "PASS_2026_consomme": True,
            },
        )
        audit.add(
            code="REC_PEE_ABONDEMENT_THEORIQUE",
            label="Abondement théorique (taux × flux salarié, avant plafonnement)",
            valeur=round(abondement_theorique, 2), unite="EUR",
        )
        audit.add(
            code="REC_PEE_ABONDEMENT_PLAFONNE",
            label="Abondement plafonné par la limite légale ?",
            valeur=1 if abondement_plafonne else 0, unite="bool",
            hypotheses={
                "abondement_theorique": round(abondement_theorique, 2),
                "plafond_legal": round(plafond_abondement, 2),
            },
        )
        if horizons_inferieurs_5:
            audit.add(
                code="REC_PEE_HORIZONS_AVANT_DISPONIBILITE",
                label="Horizons < 5 ans détectés (hors période disponibilité)",
                valeur=len(horizons_inferieurs_5), unite="count",
                hypotheses={
                    "horizons_concernes": horizons_inferieurs_5,
                    "alerte": (
                        "Le PEE est indisponible avant 5 ans hors cas légaux. "
                        "v1.1 ne modélise pas les déblocages anticipés (Q7=a). "
                        "Le calcul s'exécute mais le résultat est "
                        "directionnel uniquement pour ces horizons."
                    ),
                },
            )

    # 6. Calcul par horizon (sous-traces dédiées)
    lignes: list = []
    for h in horizons:
        if audit is not None:
            sub_horizon = TraceAudit(
                regime=f"PEE — Horizon {h} ans",
                profil_resume=(
                    f"Salarié {flux_salarie:.0f} € + abondement brut "
                    f"{abondement_brut:.0f} € (taux {taux_abondement*100:.0f}%), "
                    f"CSG-CRDS {abondement_csg_crds:.0f} €"
                ),
            )
            ligne = _calculer_horizon(
                flux_salarie, abondement_brut, abondement_csg_crds, h,
                audit=sub_horizon,
            )
            audit.attacher_sous_trace(f"horizon_{h}ans", sub_horizon)
        else:
            ligne = _calculer_horizon(
                flux_salarie, abondement_brut, abondement_csg_crds, h,
                audit=None,
            )
        lignes.append(ligne)

    # 7. Dataclass de résultat
    return ResultatAllocationPee(
        enveloppe="PEE",
        accessible=eligible,
        motif_inaccessibilite="" if eligible else "Non éligible (SP16: cas non rencontré)",
        lignes_par_horizon=lignes,
    )


# ============================================================
# SURFACE PUBLIQUE
# ============================================================
__all__ = [
    # Constantes SP16
    "PLAFOND_ABONDEMENT_PEE",
    "TX_CSG_CRDS_ABONDEMENT_PEE",
    "TX_PS_GAINS_PEE",
    # Providers doctrinaux
    "obtenir_taux_abondement_pee",
    "obtenir_plafond_abondement_pee",
    "est_eligible_pee",
    # Fonction principale
    "allocation_pee",
]
