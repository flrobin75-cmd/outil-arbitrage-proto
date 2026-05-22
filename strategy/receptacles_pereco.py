"""
strategy/receptacles_pereco.py — Module métier PERECO (v1.1 SP17).

Module d'allocation d'un versement salarié dans le PERECO (Plan
d'Épargne Retraite Collectif d'entreprise, titre 3 du PER), avec
double mécanisme :

  - **Déductibilité IR à l'entrée** (comme PERIN) sur le versement
    salarié, dans la limite du plafond annuel PERIN (art. 154 bis).
  - **Abondement employeur** (comme PEE) plafonné, soumis à
    CSG-CRDS 9,7 % à la source.

C'est l'enveloppe la plus complexe sémantiquement du périmètre v1.1.
Elle **combine** les deux logiques fiscales sans les fusionner :
chaque flux conserve son traitement propre à l'entrée et à la sortie.

Périmètre SP17 (Q1=b validé)
─────────────────────────────
- Versement volontaire salarié, déductible IR au plafond PERIN
- Abondement employeur, plafonné à 8 % PASS (cohérence v1.1 avec PEE
  ; le plafond spécifique PERECO à 16 % PASS sera modélisé en v1.2
  si validé)
- CSG-CRDS sur abondement (9,7 %)
- Capitalisation conventionnelle annuelle simple (D-R8, 2 %)
- Sortie capital uniquement (sortie rente hors périmètre v1.1)
- Fiscalité de sortie distinguée par fraction :
    * Versement salarié (déduit à l'entrée) : reprise IR au TMI
    * Abondement employeur (non déduit, déjà CSG-CRDS entrée) :
      exonéré IR à la sortie
    * Gains : PFU 30 % (12,8 % IR + 17,2 % PS)
- **Hors SP17** :
  - Plafond spécifique 16 % PASS (Q1=b : plafond cohérent PEE 8 %)
  - Transferts inter-PER
  - Multi-compartiments (titre 1, titre 2, titre 3 du PER)
  - Cas de déblocage anticipé

Sémantique économique (Q2=γ hybride validé)
────────────────────────────────────────────
Le PERECO hérite de la logique fiscale du PERIN pour son champ
`economie_fiscale_immediate`. La doctrine SP13 §3 et le pattern
SP16 sont respectés :

  - `flux_entrant_brut` : **versement salarié** (effort patrimonial
    du salarié). Identique à PERIN et PEE.

  - `economie_fiscale_immediate` : **flux_salarié × TMI**. Comme
    PERIN, cette grandeur représente la réduction d'IR immédiate
    découlant de la déductibilité (CGI art. 163 quatervicies).
    **Différent** du PEE où ce champ est à zéro.

  - `effort_reel` : flux_salarié − économie fiscale (comme PERIN).

  - `capital_projete` : (flux_salarié + abondement_net) capitalisé.
    Comme PEE, l'abondement gonfle le capital sans gonfler l'effort.

  - `cout_entreprise` : abondement BRUT (comme PEE).

  - `disponibilite` : retraite (comme PERIN).

Tableau doctrinal transverse v1.1 (cf. ARCHITECTURE_RECEPTACLES.md §3) :

| Dimension              | PERIN     | PEE       | PERECO    |
|------------------------|-----------|-----------|-----------|
| Déduction IR entrée    | Oui       | Non       | Oui       |
| Abondement employeur   | Non       | Oui       | Oui       |
| CSG-CRDS sur abondement| —         | Oui       | Oui       |
| Disponibilité          | Retraite  | 5 ans     | Retraite  |
| Sortie capital         | Oui       | Oui       | Oui       |
| Fiscalité gains sortie | PFU 30 %  | PS 17,2 % | PFU 30 %  |
| Fiscalité versements
  salariés sortie        | IR TMI    | Exonéré   | IR TMI    |
| Fiscalité abondement
  sortie                 | —         | Exonéré   | Exonéré   |
| Coût entreprise        | 0         | > 0       | > 0       |

Cette matrice est **structurante** : toute évolution v1.2 doit
préserver cette orthogonalité. Si une cellule du tableau change de
nature pour une enveloppe, c'est une évolution doctrinale qui mérite
une sous-passe formelle.

Référence doctrinale : ARCHITECTURE_RECEPTACLES.md §3, §6.4, §7.
"""

from typing import Optional

from core.audit import TraceAudit
from core.profil import Profil

# Consommation des providers communs avec PERIN (plafond + TMI). Le
# PERECO utilise le même plafond annuel que le PERIN (art. 154 bis).
from strategy.receptacles_perin import (
    obtenir_plafond_perin,
    obtenir_tmi_dirigeant,
)
# Consommation des constantes PEE pour cohérence v1.1 (Q1=b : on
# retient le plafond PEE 8 % PASS pour PERECO en v1.1, le plafond
# spécifique 16 % PASS sera v1.2).
from strategy.receptacles_pee import (
    PLAFOND_ABONDEMENT_PEE,
    TX_CSG_CRDS_ABONDEMENT_PEE,
)

from strategy.receptacles_orchestrateur import (
    Euros, TauxAnnuel, Annees,
    LigneHorizonReceptacle, ResultatAllocationPereco,
    RENDEMENT_NOMINAL_ANNUEL,
)
from strategy.receptacles_wordings import (
    WORDING_REC_CONVENTION_RENDEMENT,
    WORDING_PERECO_DEDUCTIBILITE_IR_ENTREE,
    WORDING_PERECO_ABONDEMENT_EMPLOYEUR,
    WORDING_PERECO_CSG_CRDS_ABONDEMENT,
    WORDING_PERECO_FISCALITE_SORTIE_CAPITAL,
    WORDING_PERECO_DISPONIBILITE_RETRAITE,
)


# ============================================================
# CONSTANTES SPÉCIFIQUES PERECO
# ============================================================
# Plafond abondement PERECO en v1.1 : aligné sur PEE (8 % PASS) par
# cohérence inter-enveloppes. Le plafond spécifique PERECO 16 % PASS
# (art. L224-13 CMF) sera modélisé en v1.2 si validé.
PLAFOND_ABONDEMENT_PERECO: Euros = PLAFOND_ABONDEMENT_PEE

# CSG-CRDS sur abondement : identique au PEE (9,7 %)
TX_CSG_CRDS_ABONDEMENT_PERECO: TauxAnnuel = TX_CSG_CRDS_ABONDEMENT_PEE

# Fiscalité de sortie capital sur gains : PFU 30 % (comme PERIN, pas
# comme PEE qui n'a que 17,2 % de PS)
TX_PFU_GAINS_PERECO: TauxAnnuel = 0.30


# ============================================================
# PROVIDERS DOCTRINAUX
# ============================================================
def obtenir_plafond_pereco(profil: Profil) -> Euros:
    """Provider doctrinal : plafond annuel PERECO.

    En v1.1 (Q1=b), le plafond annuel PERECO du versement salarié est
    le **plafond PERIN** (CGI art. 154 bis). Délégation au provider
    PERIN existant pour éviter toute redéclaration (G-2).

    Args:
        profil: Profil du dirigeant/salarié.

    Returns:
        Plafond annuel en euros.
    """
    return obtenir_plafond_perin(profil)


def obtenir_taux_abondement_pereco(profil: Profil) -> TauxAnnuel:
    """Provider doctrinal : taux d'abondement employeur PERECO.

    Lecture profil si attribut `taux_abondement_pereco` présent,
    sinon fallback doctrinal 100 % du versement salarié (Q8=a). Note :
    on prévoit un attribut distinct `taux_abondement_pereco`
    (séparé de `taux_abondement_pee`) car un employeur peut configurer
    différemment ses dispositifs PEE et PERECO.

    Args:
        profil: Profil du dirigeant/salarié.

    Returns:
        Taux d'abondement (ex. 1.0 = 100 %).
    """
    taux = getattr(profil, "taux_abondement_pereco", None)
    if taux is None:
        return 1.0  # fallback doctrinal Q8=a
    return float(taux)


def obtenir_plafond_abondement_pereco(profil: Profil) -> Euros:
    """Provider doctrinal : plafond légal annuel de l'abondement PERECO.

    Constante doctrinale 8 % du PASS (cohérence v1.1 avec PEE). Le
    plafond spécifique PERECO à 16 % PASS sera v1.2 si validé.

    Args:
        profil: Profil (non utilisé en SP17, signature cohérente).

    Returns:
        Plafond annuel en euros.
    """
    return PLAFOND_ABONDEMENT_PERECO


def est_eligible_pereco(profil: Profil) -> bool:
    """Provider doctrinal : éligibilité PERECO du profil.

    Comme le PEE, le PERECO est accessible si l'entreprise a mis en
    place le dispositif. v1.1 retient une éligibilité universelle et
    délègue au cabinet l'appréciation cas par cas.

    Returns:
        True systématiquement en SP17.
    """
    return True


# ============================================================
# CALCULS ÉCONOMIQUES (helpers privés)
# ============================================================
def _capitaliser(flux_initial: Euros, taux_annuel: TauxAnnuel,
                 nb_annees: Annees) -> Euros:
    """Capitalisation conventionnelle annuelle simple (D-R8).

    Copie locale pour autonomie du module, formule identique à PERIN
    et PEE.
    """
    if nb_annees < 0:
        return 0.0
    return flux_initial * ((1.0 + taux_annuel) ** nb_annees)


def _calculer_horizon(
    flux_salarie: Euros,
    abondement_brut: Euros,
    abondement_csg_crds: Euros,
    tmi: TauxAnnuel,
    horizon: Annees,
    audit: Optional[TraceAudit] = None,
) -> LigneHorizonReceptacle:
    """Calcule les 8 dimensions économiques PERECO pour un horizon donné.

    Logique économique SP17 hybride :
      1. abondement_net = abondement_brut - abondement_csg_crds
      2. flux_total_versé = flux_salarié + abondement_net
      3. economie_fiscale_immediate = flux_salarié × TMI (déduction IR,
         comme PERIN — Q2=γ)
      4. effort_reel = flux_salarié - economie_fiscale_immediate
         (comme PERIN, l'abondement n'est pas un effort salarié)
      5. capital_projeté = capitalisation de flux_total_versé à 2 %/an
      6. fiscalité de sortie (capital) :
         - Sur flux_salarié (déduit entrée) : reprise IR au TMI
         - Sur abondement_net (non déduit, déjà CSG-CRDS) : exonéré IR
         - Sur gains : PFU 30 %
      7. valeur_nette = capital_projeté - fiscalité_sortie
      8. cout_entreprise = abondement_brut (comme PEE)
      9. disponibilité : retraite (comme PERIN)
    """
    # 1. Abondement net après CSG-CRDS
    abondement_net = abondement_brut - abondement_csg_crds

    # 2. Flux total effectivement versé dans l'enveloppe
    flux_total_verse = flux_salarie + abondement_net

    # 3. Économie fiscale immédiate (déduction IR sur versement salarié)
    economie_fiscale = flux_salarie * tmi
    effort_reel = flux_salarie - economie_fiscale

    # 5. Capital projeté
    capital_projete = _capitaliser(
        flux_total_verse, RENDEMENT_NOMINAL_ANNUEL, horizon,
    )

    # 6. Fiscalité sortie capital
    gains = max(0.0, capital_projete - flux_total_verse)
    # Versement salarié déduit à l'entrée → reprise IR au TMI à la sortie
    fiscalite_versement_salarie = flux_salarie * tmi
    # Abondement non déduit à l'entrée → exonéré IR à la sortie
    fiscalite_abondement = 0.0
    # Gains : PFU 30 %
    fiscalite_gains = gains * TX_PFU_GAINS_PERECO
    fiscalite_sortie = (
        fiscalite_versement_salarie
        + fiscalite_abondement
        + fiscalite_gains
    )

    # 7-8-9. Composition
    cout_entreprise = abondement_brut
    disponibilite_txt = (
        "Bloqué jusqu'à la retraite (sauf cas légaux : invalidité, "
        "surendettement, acquisition résidence principale)."
    )

    # Instrumentation sous-trace horizon (étapes auditables)
    if audit is not None:
        audit.add(
            code=f"REC_PERECO_FLUX_SALARIE_{horizon}ANS",
            label=f"Versement salarié alloué (horizon {horizon} ans)",
            valeur=round(flux_salarie, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PERECO_ECO_FISCALE_ENTREE_{horizon}ANS",
            label="Économie fiscale immédiate (déduction IR sur versement salarié)",
            valeur=round(economie_fiscale, 2), unite="EUR",
            hypotheses={
                "tmi_appliquee": tmi,
                "WORDING_PERECO_DEDUCTIBILITE_IR_ENTREE":
                    WORDING_PERECO_DEDUCTIBILITE_IR_ENTREE,
            },
        )
        audit.add(
            code=f"REC_PERECO_EFFORT_REEL_{horizon}ANS",
            label="Effort réel salarié (versement − économie fiscale)",
            valeur=round(effort_reel, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PERECO_ABONDEMENT_EMPLOYEUR_BRUT_{horizon}ANS",
            label="Abondement employeur brut versé",
            valeur=round(abondement_brut, 2), unite="EUR",
            hypotheses={
                "WORDING_PERECO_ABONDEMENT_EMPLOYEUR":
                    WORDING_PERECO_ABONDEMENT_EMPLOYEUR,
            },
        )
        audit.add(
            code=f"REC_PERECO_CSG_CRDS_ABONDEMENT_{horizon}ANS",
            label="CSG-CRDS prélevée sur abondement (9,7 %)",
            valeur=round(abondement_csg_crds, 2), unite="EUR",
            hypotheses={
                "tx_csg_crds": TX_CSG_CRDS_ABONDEMENT_PERECO,
                "WORDING_PERECO_CSG_CRDS_ABONDEMENT":
                    WORDING_PERECO_CSG_CRDS_ABONDEMENT,
            },
        )
        audit.add(
            code=f"REC_PERECO_ABONDEMENT_EMPLOYEUR_NET_{horizon}ANS",
            label="Abondement employeur net effectivement crédité",
            valeur=round(abondement_net, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PERECO_FLUX_TOTAL_VERSE_{horizon}ANS",
            label="Flux total versé dans l'enveloppe (salarié + abondement net)",
            valeur=round(flux_total_verse, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PERECO_CAPITAL_PROJETE_{horizon}ANS",
            label=f"Capital projeté à {horizon} ans (capitalisation conventionnelle)",
            valeur=round(capital_projete, 2), unite="EUR",
            hypotheses={
                "rendement_annuel": RENDEMENT_NOMINAL_ANNUEL,
                "convention": "Capitalisation annuelle simple, déterministe (D-R8).",
                "WORDING_REC_CONVENTION_RENDEMENT": WORDING_REC_CONVENTION_RENDEMENT,
            },
        )
        audit.add(
            code=f"REC_PERECO_FISC_SORTIE_{horizon}ANS",
            label=f"Fiscalité de sortie (capital) à {horizon} ans",
            valeur=round(fiscalite_sortie, 2), unite="EUR",
            hypotheses={
                "fisc_versement_salarie_ir_tmi": round(fiscalite_versement_salarie, 2),
                "fisc_abondement_exonere": round(fiscalite_abondement, 2),
                "fisc_gains_pfu": round(fiscalite_gains, 2),
                "tx_pfu_gains": TX_PFU_GAINS_PERECO,
                "WORDING_PERECO_FISCALITE_SORTIE_CAPITAL":
                    WORDING_PERECO_FISCALITE_SORTIE_CAPITAL,
            },
        )
        audit.add(
            code=f"REC_PERECO_VALEUR_NETTE_{horizon}ANS",
            label=f"Valeur nette à {horizon} ans",
            valeur=round(capital_projete - fiscalite_sortie, 2), unite="EUR",
        )

    # Arrondi cohérent (cf. retour SP15)
    flux_salarie_arr = round(flux_salarie, 2)
    economie_fiscale_arr = round(economie_fiscale, 2)
    effort_reel_arr = round(flux_salarie_arr - economie_fiscale_arr, 2)
    capital_projete_arr = round(capital_projete, 2)
    fiscalite_sortie_arr = round(fiscalite_sortie, 2)
    valeur_nette_arr = round(capital_projete_arr - fiscalite_sortie_arr, 2)
    cout_entreprise_arr = round(cout_entreprise, 2)

    return LigneHorizonReceptacle(
        horizon_annees=horizon,
        flux_entrant_brut=flux_salarie_arr,
        economie_fiscale_immediate=economie_fiscale_arr,
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
def allocation_pereco(
    profil: Profil,
    *,
    flux_disponible: Euros,
    horizons: tuple = (5, 10, 20),
    audit: Optional[TraceAudit] = None,
) -> ResultatAllocationPereco:
    """Alloue un versement salarié dans le PERECO sur N horizons.

    Signature standardisée D-R5. Module métier consommé par
    l'orchestrateur `allocation_receptacles` ; peut être appelé
    autonomement pour analyse PERECO isolée.

    Logique SP17 :
      1. Éligibilité (provider).
      2. Plafond annuel salarié = plafond PERIN (provider).
      3. Bornage du versement salarié.
      4. TMI (provider, partagé avec PERIN).
      5. Taux + plafond abondement (providers).
      6. Calcul abondement brut + plafonnement + CSG-CRDS.
      7. Pour chaque horizon : calcul des 8 dimensions économiques.
      8. Instrumentation + retour dataclass.

    Args:
        profil: Profil du dirigeant/salarié.
        flux_disponible: Versement salarié à allouer (input, D-R12).
        horizons: Tuple d'années (défaut (5, 10, 20)).
        audit: TraceAudit optionnelle.

    Returns:
        ResultatAllocationPereco avec 1 LigneHorizonReceptacle par horizon.
    """
    # 1. Éligibilité
    eligible = est_eligible_pereco(profil)

    # 2-3. Plafond versement salarié + bornage
    plafond_versement = obtenir_plafond_pereco(profil)
    flux_salarie = min(float(flux_disponible), plafond_versement)
    flux_excedent = max(0.0, float(flux_disponible) - plafond_versement)

    # 4. TMI (provider commun avec PERIN)
    tmi = obtenir_tmi_dirigeant(profil)

    # 5-6. Abondement
    taux_abondement = obtenir_taux_abondement_pereco(profil)
    plafond_abondement = obtenir_plafond_abondement_pereco(profil)
    abondement_theorique = flux_salarie * taux_abondement
    abondement_brut = min(abondement_theorique, plafond_abondement)
    abondement_plafonne = (abondement_theorique > plafond_abondement)
    abondement_csg_crds = abondement_brut * TX_CSG_CRDS_ABONDEMENT_PERECO

    # Instrumentation racine sous-trace
    if audit is not None:
        audit.add(
            code="REC_PERECO_ELIGIBILITE",
            label="Éligibilité PERECO du profil",
            valeur=1 if eligible else 0, unite="bool",
            hypotheses={
                "regle": (
                    "PERECO accessible si l'entreprise a mis en place le "
                    "dispositif. v1.1 retient une éligibilité universelle et "
                    "délègue l'appréciation au cabinet."
                ),
                "WORDING_PERECO_DISPONIBILITE_RETRAITE":
                    WORDING_PERECO_DISPONIBILITE_RETRAITE,
            },
        )
        audit.add(
            code="REC_PERECO_PLAFOND_VERSEMENT_SALARIE",
            label="Plafond annuel du versement salarié (= plafond PERIN art. 154 bis)",
            valeur=round(plafond_versement, 2), unite="EUR",
            doctrine_refs=("PASS_2026",),
            hypotheses={
                "regle_resume": (
                    "Plafond identique PERIN : max(10 % rev. pro. N-1 ; "
                    "10 % PASS), plafonné à 8 PASS. CGI art. 154 bis."
                ),
                "PASS_2026_consomme": True,
            },
        )
        audit.add(
            code="REC_PERECO_FLUX_SALARIE_EFFECTIF",
            label="Flux salarié effectivement versé (borné par plafond)",
            valeur=round(flux_salarie, 2), unite="EUR",
            hypotheses={
                "flux_disponible_input": round(float(flux_disponible), 2),
                "plafond_versement": round(plafond_versement, 2),
                "regle_bornage": "min(flux_disponible, plafond_versement)",
            },
        )
        if flux_excedent > 0.01:
            audit.add(
                code="REC_PERECO_FLUX_EXCEDENT",
                label="Fraction du flux salarié non-versée (au-delà du plafond)",
                valeur=round(flux_excedent, 2), unite="EUR",
            )
        audit.add(
            code="REC_PERECO_TMI_APPLIQUEE",
            label="TMI appliquée pour déductibilité IR",
            valeur=tmi, unite="ratio",
        )
        audit.add(
            code="REC_PERECO_TAUX_ABONDEMENT_APPLIQUE",
            label="Taux d'abondement employeur appliqué",
            valeur=taux_abondement, unite="ratio",
            hypotheses={
                "source": (
                    "Lecture profil si attribut taux_abondement_pereco renseigné, "
                    "sinon fallback doctrinal 100 % (Q8=a SP17)."
                ),
            },
        )
        audit.add(
            code="REC_PERECO_ABONDEMENT_PLAFOND_LEGAL",
            label="Plafond légal annuel de l'abondement PERECO (v1.1 : 8 % PASS)",
            valeur=round(plafond_abondement, 2), unite="EUR",
            hypotheses={
                "regle": (
                    "v1.1 retient 8 % PASS par cohérence avec PEE. Le plafond "
                    "spécifique 16 % PASS sera v1.2 si validé."
                ),
            },
        )
        audit.add(
            code="REC_PERECO_ABONDEMENT_THEORIQUE",
            label="Abondement théorique (taux × flux salarié)",
            valeur=round(abondement_theorique, 2), unite="EUR",
        )
        audit.add(
            code="REC_PERECO_ABONDEMENT_PLAFONNE",
            label="Abondement plafonné par la limite légale ?",
            valeur=1 if abondement_plafonne else 0, unite="bool",
        )

    # 7. Calcul par horizon
    lignes: list = []
    for h in horizons:
        if audit is not None:
            sub_horizon = TraceAudit(
                regime=f"PERECO — Horizon {h} ans",
                profil_resume=(
                    f"Salarié {flux_salarie:.0f} € (TMI {tmi*100:.0f}%) "
                    f"+ abondement brut {abondement_brut:.0f} € "
                    f"(taux {taux_abondement*100:.0f}%), "
                    f"CSG-CRDS {abondement_csg_crds:.0f} €"
                ),
            )
            ligne = _calculer_horizon(
                flux_salarie, abondement_brut, abondement_csg_crds, tmi, h,
                audit=sub_horizon,
            )
            audit.attacher_sous_trace(f"horizon_{h}ans", sub_horizon)
        else:
            ligne = _calculer_horizon(
                flux_salarie, abondement_brut, abondement_csg_crds, tmi, h,
                audit=None,
            )
        lignes.append(ligne)

    # 8. Dataclass de résultat
    return ResultatAllocationPereco(
        enveloppe="PERECO",
        accessible=eligible,
        motif_inaccessibilite="" if eligible else "Non éligible (SP17: cas non rencontré)",
        lignes_par_horizon=lignes,
    )


# ============================================================
# SURFACE PUBLIQUE
# ============================================================
__all__ = [
    # Constantes SP17
    "PLAFOND_ABONDEMENT_PERECO",
    "TX_CSG_CRDS_ABONDEMENT_PERECO",
    "TX_PFU_GAINS_PERECO",
    # Providers doctrinaux
    "obtenir_plafond_pereco",
    "obtenir_taux_abondement_pereco",
    "obtenir_plafond_abondement_pereco",
    "est_eligible_pereco",
    # Fonction principale
    "allocation_pereco",
]
