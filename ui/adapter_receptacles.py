"""
ui/adapter_receptacles.py — Couche d'adaptation moteur → UI (SP20).

Frontière doctrinale matérialisée entre :
  - le moteur métier `strategy/receptacles_*.py` (v1.1.0)
  - la couche Streamlit `ui/page_receptacles.py` + `ui/composants_receptacles.py`

Ce module est conforme aux principes ARCHITECTURE_UI_RECEPTACLES.md §3.1
(décision D-UI-1) :

  - **pur** : pas d'effet de bord, pas de state Streamlit
  - **déterministe** : entrée identique → sortie identique
  - **sans Streamlit** : `import streamlit` est interdit ici
  - **sans pandas magique implicite** : pandas peut être utilisé pour
    produire des DataFrames de sortie, mais aucune transformation
    métier n'est appliquée via pandas (pas de .agg, .pipe, .sort_values
    sur des dimensions économiques, etc.)
  - **sans enrichissement métier** : aucun calcul nouveau, aucune
    agrégation nouvelle, aucun wording nouveau

Toutes les valeurs économiques restituées proviennent **strictement**
du résultat de `allocation_receptacles()` (orchestrateur SP18). Si une
grandeur n'apparaît pas dans `LigneHorizonReceptacle` ou dans la
trace audit, elle n'est pas affichable — pas à recalculer ici.

Invariant transverse SP20 (UI-I1) : ordre fixe doctrinal PERIN → PEE
→ PERECO dans tous les retours de ce module. Aucune fonction de cet
adapter ne renvoie une liste triée selon une dimension économique.

Référence doctrinale : `ARCHITECTURE_UI_RECEPTACLES.md` §3 (architecture
3 couches), §6.1 (invariant UI-I1 ordre fixe), §6.4 (invariant UI-I4
adapter sans Streamlit).
"""

from typing import Optional, Tuple

import pandas as pd

from core.audit import TraceAudit
from strategy.receptacles_orchestrateur import (
    ResultatAllocationReceptacles,
)
# Note : import limité aux types et structures. Aucun module
# `strategy/receptacles_perin.py`, `receptacles_pee.py` ou
# `receptacles_pereco.py` n'est importé directement : la composition
# a déjà été faite par l'orchestrateur, l'adapter ne fait que
# transformer son résultat.


# ============================================================
# CONSTANTES DOCTRINALES
# ============================================================
# Ordre fixe doctrinal — UI-I1.
# Cet ordre est :
#   - aligné avec celui imposé par l'orchestrateur SP18 (étapes RECAP)
#   - aligné avec celui des goldens métier SP15-SP17
#   - aligné avec celui de la doctrine §3.6 cross-enveloppes
# Aucune fonction de l'adapter ne doit retourner les enveloppes dans
# un autre ordre, quel que soit le critère.
#
# SP26 : extension de 3 à 4 enveloppes (PERO en 4e position doctrinale).
# Lève la désynchronisation volontaire SP25 (S-Q1=β) où l'orchestrateur
# avait déjà ENVELOPPES_V1_3 à 4 éléments tandis que l'adapter UI restait
# à 3. L'alignement SP26 est intentionnellement minimal : ajout de
# "PERO" en 4e position, aucune autre modification de l'ordre.
ORDRE_DOCTRINAL_ENVELOPPES: Tuple[str, str, str, str] = (
    "PERIN", "PEE", "PERECO", "PERO",
)


# Labels colonnes du tableau multi-horizon, choisis pour rester
# strictement descriptifs (pas de connotation valeur).
LABELS_DIMENSIONS_ECONOMIQUES = {
    "flux_entrant_brut": "Versement salarié brut (€)",
    "economie_fiscale_immediate": "Économie fiscale immédiate (€)",
    "effort_reel": "Effort réel (€)",
    "capital_projete": "Capital projeté (€)",
    "fiscalite_sortie": "Fiscalité de sortie (€)",
    "valeur_nette": "Valeur nette à terme (€)",
    "cout_entreprise": "Coût entreprise (€)",
    "disponibilite": "Disponibilité",
}


# ============================================================
# PROVIDERS DOCTRINAUX (UI-I1)
# ============================================================
def enveloppes_dans_ordre_doctrinal() -> Tuple[str, str, str, str]:
    """Retourne l'ordre fixe doctrinal PERIN → PEE → PERECO → PERO → PERO.

    Conforme UI-I1 (`ARCHITECTURE_UI_RECEPTACLES.md` §6.1) : aucune
    fonction de l'UI ne doit retourner les enveloppes dans un autre
    ordre. Ce provider est l'unique source d'ordre.

    SP26 : étendu de 3 à 4 enveloppes (ajout PERO en 4e position).

    Returns:
        Tuple immutable ("PERIN", "PEE", "PERECO", "PERO").
    """
    return ORDRE_DOCTRINAL_ENVELOPPES


# ============================================================
# TRANSFORMATIONS PRINCIPALES
# ============================================================
def extraire_tableau_multi_horizon(
    resultat: ResultatAllocationReceptacles,
) -> pd.DataFrame:
    """Transforme le résultat orchestrateur en DataFrame multi-horizon.

    Produit un DataFrame de la forme :

        | Enveloppe | Horizon | flux_entrant_brut | economie_fiscale_immediate | ... |
        |-----------|---------|-------------------|----------------------------|-----|
        | PERIN     | 5 ans   | 4806.0            | 1441.8                     | ... |
        | PERIN     | 10 ans  | 4806.0            | 1441.8                     | ... |
        | PERIN     | 20 ans  | 4806.0            | 1441.8                     | ... |
        | PEE       | 5 ans   | 5000.0            | 0.0                        | ... |
        | ...       |         |                   |                            |     |

    Ordre fixe doctrinal PERIN → PEE → PERECO → PERO (UI-I1).
    Horizons dans l'ordre croissant fourni par l'orchestrateur.

    Cette fonction est **strictement transformationnelle** : elle ne
    calcule rien, n'agrège rien, ne dérive rien. Chaque cellule du
    DataFrame est une copie d'un champ déjà calculé par le moteur.

    Args:
        resultat: Sortie de `allocation_receptacles()`.

    Returns:
        DataFrame avec colonnes ("Enveloppe", "Horizon (ans)",
        "flux_entrant_brut", "economie_fiscale_immediate",
        "effort_reel", "capital_projete", "fiscalite_sortie",
        "valeur_nette", "cout_entreprise", "disponibilite").

    Note : les noms de colonnes restent les noms techniques du
    dataclass `LigneHorizonReceptacle`. Le label affiché à
    l'utilisateur est appliqué côté composant (`composants_receptacles.py`)
    via le mapping `LABELS_DIMENSIONS_ECONOMIQUES`.
    """
    # Mapping nom enveloppe → résultat correspondant
    resultats_par_enveloppe = {
        "PERIN": resultat.perin,
        "PEE": resultat.pee,
        "PERECO": resultat.pereco,
        "PERO": resultat.pero,
    }

    lignes: list = []
    # Itération dans l'ordre doctrinal (UI-I1).
    for nom_env in enveloppes_dans_ordre_doctrinal():
        env_result = resultats_par_enveloppe[nom_env]
        # Les lignes par horizon sont déjà dans l'ordre fourni par le
        # moteur (cohérent avec l'orchestrateur SP18).
        for ligne in env_result.lignes_par_horizon:
            lignes.append({
                "Enveloppe": nom_env,
                "Horizon (ans)": ligne.horizon_annees,
                "flux_entrant_brut": ligne.flux_entrant_brut,
                "economie_fiscale_immediate":
                    ligne.economie_fiscale_immediate,
                "effort_reel": ligne.effort_reel,
                "capital_projete": ligne.capital_projete,
                "fiscalite_sortie": ligne.fiscalite_sortie,
                "valeur_nette": ligne.valeur_nette,
                "cout_entreprise": ligne.cout_entreprise,
                "disponibilite": ligne.disponibilite,
            })

    return pd.DataFrame(lignes)


def extraire_tableau_par_horizon(
    resultat: ResultatAllocationReceptacles,
    horizon_annees: int,
) -> pd.DataFrame:
    """Transforme le résultat orchestrateur en DataFrame pour 1 horizon.

    Format pivoté pour lecture cabinet rapide : une enveloppe par
    ligne, dimensions économiques en colonnes.

        | Enveloppe | Versement | Eco fisc | Effort | Capital | Fisc sortie | Valeur nette | Coût ent. |
        |-----------|-----------|----------|--------|---------|-------------|--------------|-----------|
        | PERIN     | 4806      | 1442     | 3364   | 5306    | 1592        | 3714         | 0         |
        | PEE       | 5000      | 0        | 5000   | 9354    | 152         | 9202         | 3845      |
        | PERECO    | 4806      | 1442     | 3364   | 9139    | 1700        | 7439         | 3845      |

    Ordre fixe doctrinal PERIN → PEE → PERECO → PERO (UI-I1).

    Args:
        resultat: Sortie de `allocation_receptacles()`.
        horizon_annees: Horizon à extraire (doit exister dans
            `resultat.horizons`).

    Returns:
        DataFrame une ligne par enveloppe pour l'horizon donné.

    Raises:
        ValueError: si l'horizon demandé n'existe pas dans le résultat.
    """
    if horizon_annees not in resultat.horizons:
        raise ValueError(
            f"Horizon {horizon_annees} ans absent du résultat "
            f"(horizons disponibles : {resultat.horizons})"
        )

    resultats_par_enveloppe = {
        "PERIN": resultat.perin,
        "PEE": resultat.pee,
        "PERECO": resultat.pereco,
        "PERO": resultat.pero,
    }

    lignes: list = []
    for nom_env in enveloppes_dans_ordre_doctrinal():
        env_result = resultats_par_enveloppe[nom_env]
        # Récupérer la ligne pour l'horizon demandé
        ligne_h = next(
            (l for l in env_result.lignes_par_horizon
             if l.horizon_annees == horizon_annees),
            None,
        )
        if ligne_h is None:
            # Sécurité : si l'orchestrateur a oublié cet horizon pour
            # cette enveloppe, on signale via NaN sans masquer.
            lignes.append({
                "Enveloppe": nom_env,
                "flux_entrant_brut": None,
                "economie_fiscale_immediate": None,
                "effort_reel": None,
                "capital_projete": None,
                "fiscalite_sortie": None,
                "valeur_nette": None,
                "cout_entreprise": None,
                "disponibilite": "—",
            })
        else:
            lignes.append({
                "Enveloppe": nom_env,
                "flux_entrant_brut": ligne_h.flux_entrant_brut,
                "economie_fiscale_immediate":
                    ligne_h.economie_fiscale_immediate,
                "effort_reel": ligne_h.effort_reel,
                "capital_projete": ligne_h.capital_projete,
                "fiscalite_sortie": ligne_h.fiscalite_sortie,
                "valeur_nette": ligne_h.valeur_nette,
                "cout_entreprise": ligne_h.cout_entreprise,
                "disponibilite": ligne_h.disponibilite,
            })

    return pd.DataFrame(lignes)


def extraire_etapes_recapitulatives(
    audit: TraceAudit,
) -> list:
    """Extrait les 9 étapes RECAP de la trace orchestrateur (SP18).

    Pour chaque code `REC_RECAP_<DIM>_<H>ANS`, retourne un dict
    UI-ready avec les 4 valeurs PERIN/PEE/PERECO/PERO dans l'ordre fixe.

    Cette fonction est **strictement transformationnelle** : elle lit
    les étapes RECAP déjà produites par l'orchestrateur. Aucune dérivation.

    Args:
        audit: TraceAudit produite par `allocation_receptacles()`
            avec un audit attaché.

    Returns:
        Liste de dicts (un par étape RECAP) :

            [
                {
                    "code": "REC_RECAP_VALEUR_NETTE_5ANS",
                    "label": "Récapitulatif des valeurs nettes à 5 ans",
                    "horizon_annees": 5,
                    "dimension": "VALEUR_NETTE",
                    "valeurs_par_enveloppe": [
                        ("PERIN", 3714.35),
                        ("PEE", 9201.95),
                        ("PERECO", 7439.15),
                    ],
                },
                ...
            ]

        L'ordre des dicts respecte celui des étapes dans la trace
        (typiquement : VALEUR_NETTE_5, EFFORT_REEL_5, COUT_ENTREPRISE_5,
        VALEUR_NETTE_10, ...). L'ordre des tuples
        `valeurs_par_enveloppe` respecte UI-I1 (PERIN → PEE → PERECO → PERO).
    """
    etapes_recap = []
    for etape in audit.etapes:
        if not etape.code.startswith("REC_RECAP_"):
            continue

        # Extraction de la dimension et de l'horizon depuis le code.
        # Format : REC_RECAP_<DIM>_<H>ANS où <DIM> peut contenir des _
        # (ex. VALEUR_NETTE, EFFORT_REEL, COUT_ENTREPRISE).
        suffixe = etape.code[len("REC_RECAP_"):]  # ex. "VALEUR_NETTE_5ANS"
        # Le dernier segment "_NANS" contient l'horizon
        parts = suffixe.rsplit("_", 1)
        if len(parts) != 2 or not parts[1].endswith("ANS"):
            continue
        dimension = parts[0]  # ex. "VALEUR_NETTE"
        horizon_str = parts[1][:-len("ANS")]  # ex. "5"
        try:
            horizon_annees = int(horizon_str)
        except ValueError:
            continue

        # Construction de la liste ordonnée (UI-I1) des valeurs par
        # enveloppe. On reconstruit le préfixe de clé d'hypothèse à
        # partir du nom de dimension en minuscules : VALEUR_NETTE →
        # valeur_nette.
        prefix_cle = dimension.lower()  # ex. "valeur_nette"
        valeurs_ordonnees = []
        for nom_env in enveloppes_dans_ordre_doctrinal():
            cle = f"{prefix_cle}_{nom_env}"
            valeur = etape.hypotheses.get(cle)
            valeurs_ordonnees.append((nom_env, valeur))

        etapes_recap.append({
            "code": etape.code,
            "label": etape.label,
            "horizon_annees": horizon_annees,
            "dimension": dimension,
            "valeurs_par_enveloppe": valeurs_ordonnees,
        })

    return etapes_recap


def extraire_hypotheses_doctrinales(
    audit: TraceAudit,
) -> dict:
    """Extrait les hypothèses doctrinales conventionnelles présentes
    dans la trace orchestrateur, pour affichage transparent (SP21).

    Cette fonction est **strictement transformationnelle** : elle
    parcourt les étapes méta SP14 + les étapes RECAP et collecte les
    hypothèses doctrinales (rendement, TMI, taux abondement,
    plafonds, etc.) **telles qu'elles ont été figées** par les
    providers du moteur. Aucune dérivation.

    Args:
        audit: TraceAudit produite par `allocation_receptacles()`.

    Returns:
        Dict structuré :

            {
                "rendement_annuel": 0.02,
                "convention_rendement_wording": "...",
                "horizons_demandes": [5, 10, 20],
                "flux_disponible_input": 5000.0,
                "nb_enveloppes_comparees": 4,
                "disclaimers_attaches": 3,
                # détail par enveloppe : tmi, taux abondement, plafond
                # (si retrouvable dans les sous-traces)
                "par_enveloppe": {
                    "PERIN": {...},
                    "PEE": {...},
                    "PERECO": {...},
                    "PERO": {...},
                },
            }

        Les valeurs sont des copies directes des hypothèses moteur.
        Si une hypothèse attendue n'est pas dans la trace, le champ
        correspondant est `None` (pas de fallback inventé côté UI).
    """
    out: dict = {
        "rendement_annuel": None,
        "convention_rendement_wording": None,
        "horizons_demandes": None,
        "flux_disponible_input": None,
        "nb_enveloppes_comparees": None,
        "disclaimers_attaches": None,
        "par_enveloppe": {
            nom: {} for nom in enveloppes_dans_ordre_doctrinal()
        },
    }

    # 1. Étapes méta racine (REC_*)
    for etape in audit.etapes:
        if etape.code == "REC_RENDEMENT_HYPOTHESE":
            out["rendement_annuel"] = etape.valeur
            out["convention_rendement_wording"] = (
                etape.hypotheses.get("WORDING_REC_CONVENTION_RENDEMENT")
            )
        elif etape.code == "REC_FLUX_DISPONIBLE":
            out["flux_disponible_input"] = etape.valeur
        elif etape.code == "REC_HORIZONS_NB":
            # Note SP21 : la clé exposée par l'orchestrateur est
            # `horizons_annees` (cf. strategy/receptacles_orchestrateur.py
            # étape REC_HORIZONS_NB). SP20 utilisait `horizons` par
            # erreur, ce qui retournait None silencieusement.
            out["horizons_demandes"] = etape.hypotheses.get(
                "horizons_annees", None,
            )
        elif etape.code == "REC_NB_ENVELOPPES":
            out["nb_enveloppes_comparees"] = etape.valeur
        elif etape.code == "REC_DISCLAIMERS_NB":
            out["disclaimers_attaches"] = etape.valeur

    # 2. Hypothèses par enveloppe (sous-traces N1)
    # SP26 : extension à 4 enveloppes (ajout PERO).
    sous_traces_attendues = {
        "PERIN": "ligne_perin",
        "PEE": "ligne_pee",
        "PERECO": "ligne_pereco",
        "PERO": "ligne_pero",
    }
    for nom_env, nom_sous_trace in sous_traces_attendues.items():
        try:
            sub = audit.get_sous_trace(nom_sous_trace)
        except (KeyError, AttributeError):
            continue

        for etape in sub.etapes:
            # Codes communs aux 4 enveloppes (suffixe variable, SP26)
            if etape.code.endswith("_TMI_APPLIQUEE"):
                out["par_enveloppe"][nom_env]["tmi"] = etape.valeur
            elif etape.code.endswith("_TAUX_ABONDEMENT_APPLIQUE"):
                out["par_enveloppe"][nom_env]["taux_abondement"] = (
                    etape.valeur
                )
            elif (etape.code.endswith("_PLAFOND_VERSEMENT")
                  or etape.code.endswith("_PLAFOND_VERSEMENT_SALARIE")
                  or etape.code.endswith("_PLAFOND_ANNUEL")):
                out["par_enveloppe"][nom_env]["plafond_versement"] = (
                    etape.valeur
                )
            elif etape.code.endswith("_ABONDEMENT_PLAFOND_LEGAL"):
                out["par_enveloppe"][nom_env]["plafond_abondement"] = (
                    etape.valeur
                )
            elif etape.code.endswith("_ELIGIBILITE"):
                out["par_enveloppe"][nom_env]["eligible"] = (
                    bool(etape.valeur)
                )

    return out


def compter_etapes_pour_pdf(audit: TraceAudit) -> dict:
    """Comptage simple des étapes pour panneau navigation audit (SP22).

    Strictement informatif : nombre d'étapes racine, sous-traces,
    hypothèses. Aucune dérivation économique.

    Args:
        audit: TraceAudit produite par `allocation_receptacles()`.

    Returns:
        Dict {nb_etapes_racine, nb_sous_traces, nb_hypotheses,
        nb_codes_recap}.
    """
    nb_etapes_racine = len(audit.etapes)
    nb_sous_traces = len(list(audit.noms_sous_traces()))
    nb_hypotheses = sum(
        len(e.hypotheses) for e in audit.etapes
    )
    # Sous-traces N2 + leurs hypothèses
    for nom in audit.noms_sous_traces():
        sub = audit.get_sous_trace(nom)
        nb_hypotheses += sum(len(e.hypotheses) for e in sub.etapes)
        for nom_n2 in sub.noms_sous_traces():
            sub_n2 = sub.get_sous_trace(nom_n2)
            nb_hypotheses += sum(len(e.hypotheses) for e in sub_n2.etapes)

    nb_codes_recap = sum(
        1 for e in audit.etapes if e.code.startswith("REC_RECAP_")
    )

    return {
        "nb_etapes_racine": nb_etapes_racine,
        "nb_sous_traces": nb_sous_traces,
        "nb_hypotheses": nb_hypotheses,
        "nb_codes_recap": nb_codes_recap,
    }


# ============================================================
# SURFACE PUBLIQUE
# ============================================================
__all__ = [
    # Constantes doctrinales
    "ORDRE_DOCTRINAL_ENVELOPPES",
    "LABELS_DIMENSIONS_ECONOMIQUES",
    # Provider UI-I1
    "enveloppes_dans_ordre_doctrinal",
    # Transformations
    "extraire_tableau_multi_horizon",
    "extraire_tableau_par_horizon",
    "extraire_etapes_recapitulatives",
    "extraire_hypotheses_doctrinales",
    "compter_etapes_pour_pdf",
]
