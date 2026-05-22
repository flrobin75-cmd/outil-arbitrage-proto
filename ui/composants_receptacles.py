"""
ui/composants_receptacles.py — Composants Streamlit Réceptacles v1.2 (SP20).

Phase 1 du cadrage v1.2 : Lecture cabinet (tableau multi-horizon).

Ce module rassemble les composants Streamlit réutilisables qui
restituent les données du moteur Réceptacles (v1.1.0). Il est conforme
à `ARCHITECTURE_UI_RECEPTACLES.md` :

  - couche 3 (Streamlit), aucun calcul (D-UI-2)
  - consomme uniquement les structures produites par `ui.adapter_receptacles`
  - n'importe AUCUN module `strategy/receptacles_perin.py`,
    `receptacles_pee.py` ou `receptacles_pereco.py` directement
  - respecte l'ordre fixe doctrinal PERIN → PEE → PERECO (UI-I1)
  - utilise uniquement les composants Streamlit autorisés en §5.1
  - n'utilise AUCUN composant à connotation valeur (§4.2 : pas de
    st.success, st.balloons, st.toast, st.snow)
  - n'utilise AUCUN emoji valorisant (§4.3) ni couleur sémantique
    valorisante (§4.4)

Périmètre SP20 :
  - Fonction principale : `tableau_multi_horizon(df)` — affiche le
    DataFrame produit par `adapter_receptacles.extraire_tableau_multi_horizon`
  - Fonction secondaire : `tableau_par_horizon(df, h)` — affiche le
    pivot enveloppe par horizon
  - Fonctions utilitaires : `formater_euro`, `formater_pourcentage`

Composants Streamlit utilisés (§5.1 autorisés) :
  - st.subheader, st.caption, st.markdown, st.dataframe, st.columns,
    st.expander, st.info, st.tabs

Composants Streamlit INTERDITS et non utilisés ici :
  - st.success, st.error (sauf erreur technique), st.warning sur
    valeur économique, st.balloons, st.toast, st.snow, st.metric
    avec delta colorée (§4.2)

Référence doctrinale : `ARCHITECTURE_UI_RECEPTACLES.md` §3, §4, §5, §6.
"""

from typing import Optional

import pandas as pd
import streamlit as st

from ui.adapter_receptacles import (
    LABELS_DIMENSIONS_ECONOMIQUES,
    enveloppes_dans_ordre_doctrinal,
    compter_etapes_pour_pdf,
)


# ============================================================
# FORMATAGE NUMÉRIQUE (neutre, descriptif)
# ============================================================
def formater_euro(valeur: Optional[float], precision: int = 2) -> str:
    """Formate un nombre en euros avec espace séparateur de milliers.

    Format français standard : « 4 806,00 € ».

    Args:
        valeur: Valeur numérique ou None/NaN.
        precision: Nombre de décimales (par défaut 2).

    Returns:
        Chaîne formatée. Retourne « — » si valeur est None ou NaN.
    """
    if valeur is None:
        return "—"
    try:
        if pd.isna(valeur):
            return "—"
    except (TypeError, ValueError):
        pass
    try:
        montant = float(valeur)
    except (TypeError, ValueError):
        return "—"
    # Format français : espace fine séparatrice + virgule décimale
    fmt = f"{montant:,.{precision}f}"
    fmt = fmt.replace(",", " ").replace(".", ",")
    return f"{fmt} €"


def formater_pourcentage(valeur: Optional[float], precision: int = 1) -> str:
    """Formate un ratio en pourcentage.

    Args:
        valeur: Ratio (ex. 0.30 pour 30 %).
        precision: Nombre de décimales (par défaut 1).

    Returns:
        Chaîne formatée. Retourne « — » si valeur est None ou NaN.
    """
    if valeur is None:
        return "—"
    try:
        if pd.isna(valeur):
            return "—"
    except (TypeError, ValueError):
        pass
    try:
        ratio = float(valeur)
    except (TypeError, ValueError):
        return "—"
    return f"{ratio * 100:.{precision}f} %".replace(".", ",")


# ============================================================
# COMPOSANT PRINCIPAL : TABLEAU MULTI-HORIZON
# ============================================================
def tableau_multi_horizon(df: pd.DataFrame) -> None:
    """Affiche le tableau multi-horizon des 3 enveloppes (SP20 phase 1).

    Format : une ligne par couple (enveloppe, horizon), colonnes
    = dimensions économiques renommées avec libellés français.

    L'ordre des enveloppes est figé (PERIN → PEE → PERECO, UI-I1).
    Aucun tri par valeur économique. Aucun highlight conditionnel.
    Aucune coloration de cellule.

    Args:
        df: DataFrame produit par
            `ui.adapter_receptacles.extraire_tableau_multi_horizon`.
    """
    st.subheader("Tableau multi-horizon des 3 enveloppes")
    st.caption(
        "Ordre fixe doctrinal PERIN → PEE → PERECO. "
        "Valeurs issues du moteur v1.1.0 (orchestrateur SP18)."
    )

    if df is None or df.empty:
        st.info("Aucune donnée disponible.")
        return

    # Renommage des colonnes pour affichage français
    df_affiche = df.copy()
    df_affiche = df_affiche.rename(columns=LABELS_DIMENSIONS_ECONOMIQUES)

    # Formatage des colonnes numériques en euros
    colonnes_euros = [
        LABELS_DIMENSIONS_ECONOMIQUES[k] for k in [
            "flux_entrant_brut", "economie_fiscale_immediate",
            "effort_reel", "capital_projete", "fiscalite_sortie",
            "valeur_nette", "cout_entreprise",
        ]
        if LABELS_DIMENSIONS_ECONOMIQUES[k] in df_affiche.columns
    ]
    for col in colonnes_euros:
        df_affiche[col] = df_affiche[col].apply(
            lambda v: formater_euro(v)
        )

    # st.dataframe SANS styling conditionnel (§4.4 : pas de
    # highlight_max, background_gradient, etc.). Largeur native.
    st.dataframe(
        df_affiche,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# COMPOSANT SECONDAIRE : TABLEAU PAR HORIZON (pivot)
# ============================================================
def tableau_par_horizon(df: pd.DataFrame, horizon_annees: int) -> None:
    """Affiche le tableau pivoté pour un horizon donné.

    Format : une ligne par enveloppe (PERIN, PEE, PERECO), colonnes
    = dimensions économiques. Pratique pour la lecture cabinet
    « à 5 ans, quel effort vs quel capital ? ».

    Ordre fixe PERIN → PEE → PERECO (UI-I1).

    Args:
        df: DataFrame produit par
            `ui.adapter_receptacles.extraire_tableau_par_horizon`.
        horizon_annees: Horizon pour le titre.
    """
    st.subheader(f"Vue par enveloppe — Horizon {horizon_annees} ans")

    if df is None or df.empty:
        st.info("Aucune donnée disponible pour cet horizon.")
        return

    df_affiche = df.copy()
    df_affiche = df_affiche.rename(columns=LABELS_DIMENSIONS_ECONOMIQUES)

    colonnes_euros = [
        LABELS_DIMENSIONS_ECONOMIQUES[k] for k in [
            "flux_entrant_brut", "economie_fiscale_immediate",
            "effort_reel", "capital_projete", "fiscalite_sortie",
            "valeur_nette", "cout_entreprise",
        ]
        if LABELS_DIMENSIONS_ECONOMIQUES[k] in df_affiche.columns
    ]
    for col in colonnes_euros:
        df_affiche[col] = df_affiche[col].apply(
            lambda v: formater_euro(v)
        )

    st.dataframe(
        df_affiche,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# COMPOSANT INFORMATIF : DISCLAIMER COMPARABILITÉ
# ============================================================
def afficher_disclaimer_perimetre() -> None:
    """Affiche un rappel doctrinal neutre sur le périmètre v1.1.

    Utilise st.info (composant autorisé §5.1, rappel neutre sans
    connotation valeur).

    Wording strict : informatif, descriptif, sans prescription.
    """
    st.info(
        "Périmètre v1.1 : 3 enveloppes comparées (PERIN, PEE, PERECO) "
        "sur 3 horizons (5, 10, 20 ans). Hors périmètre : assurance-vie, "
        "CTO, immobilier, transferts inter-PER, déblocages anticipés. "
        "L'outil restitue les valeurs économiques de manière strictement "
        "descriptive ; l'arbitrage reste cabinet."
    )


def afficher_disclaimer_comparabilite() -> None:
    """Affiche un rappel doctrinal neutre sur la comparabilité.

    Rappelle que les 3 enveloppes ont des logiques fiscales et sociales
    différentes : conditions d'accès, plafonds, déductibilité,
    fiscalité de sortie, conditions de déblocage.
    """
    st.info(
        "Les 3 enveloppes ont des logiques fiscales et sociales "
        "différentes : conditions d'accès, plafonds annuels, "
        "déductibilité à l'entrée, fiscalité à la sortie, conditions "
        "de déblocage. La comparaison s'effectue sur des bases "
        "non strictement substituables."
    )


def afficher_convention_rendement(rendement_annuel: Optional[float]) -> None:
    """Affiche la convention de rendement utilisée.

    Args:
        rendement_annuel: Valeur du rendement annuel (ex. 0.02 pour 2 %).
    """
    if rendement_annuel is None:
        return
    st.caption(
        f"Convention de rendement appliquée : "
        f"{formater_pourcentage(rendement_annuel)} par an, "
        f"capitalisation annuelle simple et déterministe (D-R8)."
    )


# ============================================================
# COMPOSANT NAVIGATION INPUTS (saisie utilisateur)
# ============================================================
def saisir_inputs_orchestrateur() -> dict:
    """Affiche les widgets de saisie pour l'appel orchestrateur.

    Saisies :
      - flux disponible (€)
      - horizons à projeter (multi-select sur 5/10/20 ans)
      - taux de cotisation PERO (%, SP26)

    Returns:
        Dict {flux_disponible: float, horizons: tuple,
              taux_cotisation_pero: float}.

    Note : la saisie du profil reste pilotée par la barre latérale
    existante de `app.py` (build_profil()), pour cohérence avec les
    autres pages. SP20 n'introduit pas de nouvelle saisie profil.

    SP26 : ajout du widget `taux_cotisation_pero`. Valeur par défaut
    0 % (cohérent b1 SP25 : pas de signal prescriptif). La page
    appelante injecte cette valeur dans `profil.taux_cotisation_pero`
    avant l'appel orchestrateur (l'orchestrateur lit depuis le profil).
    """
    st.markdown("**Paramètres de simulation**")
    col1, col2 = st.columns([1, 2])

    flux_disponible = col1.number_input(
        "Flux disponible (€)",
        min_value=0.0,
        max_value=100_000.0,
        value=5_000.0,
        step=500.0,
        format="%.2f",
        help="Montant à allouer dans les enveloppes (versement salarié).",
    )

    horizons_disponibles = [5, 10, 20]
    horizons_choisis = col2.multiselect(
        "Horizons à projeter (années)",
        options=horizons_disponibles,
        default=horizons_disponibles,
        help="Horizons temporels pour la projection économique.",
    )

    # SP26 : widget taux PERO (4e enveloppe). Valeur par défaut 0 %.
    # Saisie en pourcentage côté UI (plus lisible), conversion en
    # fraction (0..1) côté retour (cohérent avec la convention des
    # autres taux dans le moteur).
    taux_cotisation_pero_pct = st.number_input(
        "Taux de cotisation PERO (%)",
        min_value=0.0,
        max_value=10.0,
        value=0.0,
        step=0.25,
        format="%.2f",
        help=("Taux de cotisation employeur PERO appliqué au salaire brut "
              "assimilé du profil. 0 % = PERO non actif. Plage typique : "
              "1-8 %."),
    )

    return {
        "flux_disponible": float(flux_disponible),
        "horizons": tuple(sorted(horizons_choisis)),
        "taux_cotisation_pero": float(taux_cotisation_pero_pct) / 100.0,
    }


# ============================================================
# COMPOSANTS HYPOTHÈSES DOCTRINALES (SP21)
# ============================================================
# Phase 2 du cadrage v1.2 : Auditabilité visible.
#
# Position doctrinale (votre formulation SP21) :
#   « Les hypothèses doivent être visibles, mais non dominantes
#     visuellement. »
#   « Aucune phrase interprétative autour des tableaux. »
#   « Les hypothèses doivent rester purement paramétriques. »
#
# Structure choisie (B-Q2=a, variante hybride validée) :
#   Bloc 1 — conventions transverses (rendement, capitalisation, horizons)
#   Bloc 2 — hypothèses par enveloppe (TMI, abondement, plafonds), format
#            tableau long PERIN → PEE → PERECO
#
# Référence : ARCHITECTURE_UI_RECEPTACLES.md §4.6 bis, §4.4 bis, §6.6.
# ============================================================


# Labels descriptifs des hypothèses par enveloppe (strictement
# paramétriques, sans qualification subjective). Utilisés pour
# nommer chaque ligne du tableau long.
LABELS_HYPOTHESES_ENVELOPPES = {
    "eligible": "Éligibilité",
    "tmi": "TMI appliquée",
    "taux_abondement": "Taux d'abondement employeur",
    "plafond_versement": "Plafond annuel de versement",
    "plafond_abondement": "Plafond d'abondement",
}


def _formater_valeur_hypothese(cle: str, valeur) -> str:
    """Formate la valeur d'une hypothèse selon sa nature.

    Args:
        cle: Nom de l'hypothèse (cf. LABELS_HYPOTHESES_ENVELOPPES).
        valeur: Valeur à formater (peut être None, bool, float, etc.).

    Returns:
        Chaîne de caractères formatée. « — » si valeur absente.
    """
    if valeur is None:
        return "—"
    if cle == "eligible":
        return "Oui" if bool(valeur) else "Non"
    if cle in ("tmi", "taux_abondement"):
        return formater_pourcentage(valeur)
    if cle in ("plafond_versement", "plafond_abondement"):
        return formater_euro(valeur)
    # Valeur inconnue : on tente euro par défaut
    return formater_euro(valeur)


def tableau_conventions_transverses(hypotheses: dict) -> None:
    """Affiche le tableau des conventions de simulation transverses.

    Conventions communes aux 3 enveloppes (rendement, capitalisation,
    horizons demandés, flux disponible). Format compact : 2 colonnes
    (Convention / Valeur). Aucune phrase d'introduction interprétative
    (cf. ARCHITECTURE_UI_RECEPTACLES.md §4.6 bis).

    Args:
        hypotheses: dict produit par
            `ui.adapter_receptacles.extraire_hypotheses_doctrinales`.
    """
    st.markdown("**Conventions de simulation transverses**")

    rendement = hypotheses.get("rendement_annuel")
    horizons = hypotheses.get("horizons_demandes")
    flux = hypotheses.get("flux_disponible_input")
    nb_enveloppes = hypotheses.get("nb_enveloppes_comparees")

    # Construction stricte ligne par ligne — pas de logique conditionnelle
    # sur la valeur (qui pourrait introduire un biais).
    lignes = []
    lignes.append({
        "Convention": "Rendement annuel",
        "Valeur": (formater_pourcentage(rendement)
                   if rendement is not None else "—"),
    })
    lignes.append({
        "Convention": "Méthode de capitalisation",
        "Valeur": "Annuelle, simple et déterministe",
    })
    if horizons is not None:
        horizons_str = " / ".join(f"{h} ans" for h in horizons)
        lignes.append({
            "Convention": "Horizons demandés",
            "Valeur": horizons_str,
        })
    if flux is not None:
        lignes.append({
            "Convention": "Flux salarié disponible saisi",
            "Valeur": formater_euro(flux),
        })
    if nb_enveloppes is not None:
        lignes.append({
            "Convention": "Nombre d'enveloppes comparées",
            "Valeur": str(int(nb_enveloppes)),
        })

    df = pd.DataFrame(lignes)
    st.dataframe(df, use_container_width=True, hide_index=True)


def tableau_hypotheses_par_enveloppe(hypotheses: dict) -> None:
    """Affiche le tableau long des hypothèses par enveloppe.

    Format : 3 colonnes (Enveloppe / Hypothèse / Valeur). Une ligne
    par couple (enveloppe × hypothèse présente). Ordre fixe doctrinal
    PERIN → PEE → PERECO (UI-I1).

    Aucune comparaison inter-enveloppes implicite : chaque ligne est
    une fiche descriptive autonome.

    Args:
        hypotheses: dict produit par
            `ui.adapter_receptacles.extraire_hypotheses_doctrinales`.
    """
    st.markdown("**Hypothèses appliquées par enveloppe**")

    par_env = hypotheses.get("par_enveloppe", {})

    lignes = []
    # Ordre fixe doctrinal PERIN → PEE → PERECO
    for nom_env in enveloppes_dans_ordre_doctrinal():
        env_hyp = par_env.get(nom_env, {})
        # Ordre stable des hypothèses : on suit l'ordre des clés
        # dans LABELS_HYPOTHESES_ENVELOPPES (déterministe par
        # construction du dict Python 3.7+).
        for cle, label in LABELS_HYPOTHESES_ENVELOPPES.items():
            valeur = env_hyp.get(cle)
            if valeur is None:
                # On n'affiche pas les hypothèses absentes (ex. PEE
                # n'a pas de TMI à l'entrée, pas de plafond_versement
                # propre car flux libre). Ne pas inventer de valeur
                # par défaut côté UI (D-UI-2 : couche muette).
                continue
            lignes.append({
                "Enveloppe": nom_env,
                "Hypothèse": label,
                "Valeur": _formater_valeur_hypothese(cle, valeur),
            })

    df = pd.DataFrame(lignes)
    if df.empty:
        st.caption("Aucune hypothèse spécifique disponible.")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def panneau_hypotheses_doctrinales(hypotheses: dict) -> None:
    """Affiche le panneau complet d'auditabilité (SP21 phase 2).

    Structure :
      - Phrase d'introduction strictement descriptive
      - Bloc 1 : conventions transverses
      - Bloc 2 : hypothèses par enveloppe (tableau long)

    Args:
        hypotheses: dict produit par
            `ui.adapter_receptacles.extraire_hypotheses_doctrinales`.
    """
    # Phrase d'introduction strictement descriptive (cf. §4.6 bis :
    # aucune interprétation autour des tableaux).
    st.caption(
        "Hypothèses doctrinales utilisées pour les calculs."
    )
    tableau_conventions_transverses(hypotheses)
    tableau_hypotheses_par_enveloppe(hypotheses)


# ============================================================
# COMPOSANTS NAVIGATION AUDIT (SP22)
# ============================================================
# Phase 3 du cadrage v1.2 : Navigation audit.
#
# Principe directeur (votre formulation SP22) :
#   « Navigation audit ≠ storytelling. L'UI doit permettre
#     l'inspection, la lecture, la traçabilité. Mais jamais guider
#     la décision. »
#
# Contraintes structurelles SP22 :
#   - Navigation passive uniquement (pas d'« explorer »,
#     « approfondir », « analyser »)
#   - Boutons fonctionnels uniquement (« Télécharger PDF audit »)
#   - Ordre stable PERIN → PEE → PERECO (étendu aux signets,
#     boutons de navigation enveloppe)
#   - Aucun bouton conditionné par valeur économique (A10)
#   - Aucun aperçu RECAP en zone navigation (A9 : duplique l'info,
#     crée surface narrative supplémentaire)
#
# Référence : ARCHITECTURE_UI_RECEPTACLES.md §4.9, §4.10, §5.4.
# ============================================================


# Label fonctionnel unique et neutre du bouton téléchargement (§5.4 :
# « Composants panneau navigation audit autorisés »).
LABEL_TELECHARGER_PDF = "Télécharger le PDF audit"


# Labels descriptifs des compteurs structurels d'audit. Strictement
# paramétriques, sans qualification (cf. §4.9).
LABELS_COMPTEURS_AUDIT = {
    "nb_etapes_racine": "Étapes racine",
    "nb_sous_traces": "Sous-traces (par enveloppe)",
    "nb_hypotheses": "Hypothèses tracées",
    "nb_codes_recap": "Étapes récapitulatives",
    "taille_pdf_bytes": "Taille du PDF (octets)",
}


def tableau_structure_audit(counts: dict,
                             taille_pdf_bytes: Optional[int] = None) -> None:
    """Affiche le tableau des compteurs structurels de l'audit.

    Format : 2 colonnes (Élément / Valeur). Compteurs strictement
    descriptifs : aucune mise en avant économique.

    Conforme §4.9 : seuls les compteurs structurels neutres sont
    affichés. Pas d'aperçu de valeurs économiques.

    Args:
        counts: dict produit par
            `ui.adapter_receptacles.compter_etapes_pour_pdf`.
        taille_pdf_bytes: taille du PDF généré en octets, ajoutée
            comme dernière ligne du tableau. None si non disponible.
    """
    st.markdown("**Structure de l'audit**")

    lignes = []
    for cle in ["nb_etapes_racine", "nb_sous_traces",
                "nb_hypotheses", "nb_codes_recap"]:
        valeur = counts.get(cle)
        if valeur is None:
            continue
        lignes.append({
            "Élément": LABELS_COMPTEURS_AUDIT[cle],
            "Valeur": str(int(valeur)),
        })
    if taille_pdf_bytes is not None:
        lignes.append({
            "Élément": LABELS_COMPTEURS_AUDIT["taille_pdf_bytes"],
            "Valeur": f"{int(taille_pdf_bytes):,}".replace(",", " "),
        })

    df = pd.DataFrame(lignes)
    if df.empty:
        st.caption("Compteurs indisponibles.")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)


def afficher_metadonnees_doctrinales(
    doctrine_version: str,
    doctrine_date: str,
    audit_spec_version: str,
    audit_pdf_spec_version: str,
    baseline_hash: str,
    timestamp_generation: Optional[str] = None,
) -> None:
    """Affiche les métadonnées doctrinales du PDF généré.

    Caption strictement descriptive (§4.9 : descriptif, traçable, non
    interprétatif). Cohérent avec la mention « PDF généré avec
    doctrine v1.0.1 » validée en SP22.

    Args:
        doctrine_version: cf. `doctrine.DOCTRINE_VERSION`.
        doctrine_date: cf. `doctrine.DOCTRINE_DATE`.
        audit_spec_version: cf. `core.audit.AUDIT_SPEC_VERSION`.
        audit_pdf_spec_version: cf.
            `ui.pdf_audit_export.AUDIT_PDF_SPEC_VERSION`.
        baseline_hash: hash baseline numérique (cf.
            `ui.pdf_audit_export.BASELINE_HASH_DEFAUT`).
        timestamp_generation: instant ISO 8601 de génération PDF.
            None si non disponible.
    """
    elements = [
        f"Doctrine v{doctrine_version} ({doctrine_date})",
        f"Spec audit v{audit_spec_version}",
        f"Renderer v{audit_pdf_spec_version}",
        f"Baseline {baseline_hash}",
    ]
    if timestamp_generation:
        elements.append(f"Généré le {timestamp_generation}")
    st.caption(" · ".join(elements))


def panneau_navigation_audit(
    pdf_bytes: bytes,
    counts: dict,
    doctrine_version: str,
    doctrine_date: str,
    audit_spec_version: str,
    audit_pdf_spec_version: str,
    baseline_hash: str,
    timestamp_generation: Optional[str] = None,
    file_name: str = "audit_receptacles.pdf",
) -> None:
    """Affiche le panneau complet de navigation audit (SP22 phase 3).

    Structure imposée par §4.9 (navigation passive uniquement) :
      1. Bouton de téléchargement PDF, label fonctionnel unique
      2. Tableau des compteurs structurels (pas de valeurs économiques)
      3. Métadonnées doctrinales en caption

    Conforme :
      - §4.9 (A9) : navigation ≠ storytelling
      - §4.10 (A10) : bouton non conditionné par valeur économique
      - §5.4 : composants panneau navigation autorisés
      - §6.1 (UI-I1) : ordre stable doctrinal (rien à ordonner ici,
        mais le bouton reste unique et non conditionné)

    Args:
        pdf_bytes: PDF généré par `ui.pdf_audit_export.generer_pdf_audit`.
        counts: dict produit par `ui.adapter_receptacles.compter_etapes_pour_pdf`.
        doctrine_version, doctrine_date, audit_spec_version,
        audit_pdf_spec_version, baseline_hash, timestamp_generation:
            métadonnées doctrinales (cf. `afficher_metadonnees_doctrinales`).
        file_name: nom de fichier proposé au téléchargement.
    """
    # 1. Bouton téléchargement : unique, non conditionné, label fonctionnel
    # st.download_button est listé en §5.4 comme composant autorisé du
    # panneau navigation. Le label est figé via LABEL_TELECHARGER_PDF
    # pour éviter toute reformulation interprétative au fil du temps.
    st.download_button(
        label=LABEL_TELECHARGER_PDF,
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
    )

    # 2. Tableau des compteurs structurels (cohérent SP21)
    taille_pdf = len(pdf_bytes) if pdf_bytes else None
    tableau_structure_audit(counts, taille_pdf_bytes=taille_pdf)

    # 3. Métadonnées doctrinales (descriptif, traçable)
    afficher_metadonnees_doctrinales(
        doctrine_version=doctrine_version,
        doctrine_date=doctrine_date,
        audit_spec_version=audit_spec_version,
        audit_pdf_spec_version=audit_pdf_spec_version,
        baseline_hash=baseline_hash,
        timestamp_generation=timestamp_generation,
    )


# ============================================================
# SURFACE PUBLIQUE
# ============================================================
__all__ = [
    # Formatage
    "formater_euro",
    "formater_pourcentage",
    # Composants principaux
    "tableau_multi_horizon",
    "tableau_par_horizon",
    # Disclaimers neutres
    "afficher_disclaimer_perimetre",
    "afficher_disclaimer_comparabilite",
    "afficher_convention_rendement",
    # Saisie
    "saisir_inputs_orchestrateur",
    # SP21 — Auditabilité visible
    "tableau_conventions_transverses",
    "tableau_hypotheses_par_enveloppe",
    "panneau_hypotheses_doctrinales",
    # SP22 — Navigation audit
    "LABEL_TELECHARGER_PDF",
    "tableau_structure_audit",
    "afficher_metadonnees_doctrinales",
    "panneau_navigation_audit",
]
