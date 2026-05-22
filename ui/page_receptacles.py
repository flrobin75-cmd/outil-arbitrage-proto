"""
ui/page_receptacles.py — Page Streamlit Réceptacles v1.2 (SP20).

Page entry-point qui orchestre l'expérience utilisateur Réceptacles :

  1. Récupère le profil (déjà construit dans `app.py::build_profil()`)
  2. Affiche les widgets de saisie des paramètres simulation
  3. Délègue le calcul à l'orchestrateur moteur (v1.1.0, SP18)
  4. Passe le résultat à l'adapter (`ui.adapter_receptacles`)
  5. Restitue via les composants (`ui.composants_receptacles`)

Cette page est conforme à `ARCHITECTURE_UI_RECEPTACLES.md` :

  - couche 3 (Streamlit), aucun calcul (D-UI-2)
  - importe uniquement les modules autorisés (§6.3) :
    streamlit, pandas, ui.adapter_receptacles, ui.composants_receptacles,
    strategy.receptacles_orchestrateur (orchestrateur uniquement),
    core.profil, core.audit
  - ordre fixe doctrinal PERIN → PEE → PERECO → PERO (via adapter)
  - aucun mot interdit dans les chaînes affichées
  - aucun composant à connotation valeur (§4.2)
  - aucun emoji valorisant (§4.3)
  - aucune couleur sémantique valorisante (§4.4)

Périmètre SP20 — phase 1 (Lecture cabinet) :
  - Tableau multi-horizon des 4 enveloppes
  - Vue pivotée par horizon (onglets 5/10/20 ans)
  - Disclaimers doctrinaux neutres (périmètre + comparabilité)

Périmètre SP21 (à venir) :
  - Panneau hypothèses doctrinales (rendement, TMI, plafonds)

Périmètre SP22 (à venir) :
  - Navigation audit (lien PDF, trace, étapes structurantes)

Référence doctrinale : `ARCHITECTURE_UI_RECEPTACLES.md` §3 (architecture
3 couches), §6 (invariants UI-I1 à UI-I5).
"""

import streamlit as st

from core.audit import TraceAudit, AUDIT_SPEC_VERSION
from core.profil import Profil
from doctrine import DOCTRINE_VERSION, DOCTRINE_DATE
from strategy.receptacles_orchestrateur import allocation_receptacles

from ui.adapter_receptacles import (
    extraire_tableau_multi_horizon,
    extraire_tableau_par_horizon,
    extraire_hypotheses_doctrinales,
    compter_etapes_pour_pdf,
)
from ui.composants_receptacles import (
    tableau_multi_horizon,
    tableau_par_horizon,
    afficher_disclaimer_perimetre,
    afficher_disclaimer_comparabilite,
    afficher_convention_rendement,
    saisir_inputs_orchestrateur,
    panneau_hypotheses_doctrinales,
    panneau_navigation_audit,
)
from ui.pdf_audit_export import (
    generer_pdf_audit,
    AUDIT_PDF_SPEC_VERSION,
    BASELINE_HASH_DEFAUT,
)


# ============================================================
# CONSTANTES UI
# ============================================================
TITRE_PAGE = "🧰 Réceptacles auditables"
SOUS_TITRE = (
    "Comparaison descriptive PERIN / PEE / PERECO / PERO sur 3 horizons "
    "(v1.1, module Réceptacles)"
)


# ============================================================
# PAGE PRINCIPALE
# ============================================================
def page_receptacles(profil: Profil) -> None:
    """Page Streamlit principale pour le module Réceptacles v1.1.

    Args:
        profil: Profil construit par `app.py::build_profil()` à partir
            de la barre latérale.
    """
    st.title(TITRE_PAGE)
    st.caption(SOUS_TITRE)

    # Disclaimer périmètre (rappel doctrinal neutre)
    afficher_disclaimer_perimetre()

    # === SAISIE INPUTS ===
    with st.expander("Paramètres de simulation", expanded=True):
        inputs = saisir_inputs_orchestrateur()

    flux_disponible = inputs["flux_disponible"]
    horizons = inputs["horizons"]
    # SP26 : taux PERO saisi via le widget, injecté dans le profil
    # avant l'appel orchestrateur. L'orchestrateur SP25 lit
    # `profil.taux_cotisation_pero` (cf. A-Q1=β SP25).
    taux_cotisation_pero = inputs["taux_cotisation_pero"]
    profil.taux_cotisation_pero = taux_cotisation_pero

    # Garde-fou minimal : ne pas appeler le moteur si flux nul ou
    # horizons vides (cas dégénéré, pas d'erreur métier).
    # Note SP26 : un flux nul et un taux PERO nul ensemble laissent
    # toutes les enveloppes à zéro — on garde quand même le garde-fou
    # historique sur le flux pour ne pas exposer un tableau vide au
    # cabinet sans signal explicite.
    if flux_disponible <= 0.0 or not horizons:
        st.info(
            "Renseignez un flux disponible positif et au moins un horizon "
            "pour lancer la projection."
        )
        return

    # === APPEL ORCHESTRATEUR ===
    # Note doctrinale : aucun calcul ici. La page passe simplement les
    # inputs à l'orchestrateur et récupère son résultat + sa trace audit.
    trace = TraceAudit(
        regime="Réceptacles",
        profil_resume="Saisie utilisateur via UI Streamlit",
    )
    resultat = allocation_receptacles(
        profil,
        flux_disponible=flux_disponible,
        horizons=horizons,
        audit=trace,
    )

    # === RESTITUTION VIA L'ADAPTER ===
    # Toutes les transformations sont déléguées à l'adapter pur. La
    # page ne manipule jamais directement les LigneHorizonReceptacle.
    df_multi = extraire_tableau_multi_horizon(resultat)
    hypotheses = extraire_hypotheses_doctrinales(trace)

    st.divider()

    # === VUE 1 : TABLEAU MULTI-HORIZON ===
    tableau_multi_horizon(df_multi)
    afficher_convention_rendement(hypotheses.get("rendement_annuel"))

    st.divider()

    # === VUE 2 : ONGLETS PAR HORIZON ===
    st.subheader("Vue par horizon")
    st.caption(
        "Lecture pivotée : une enveloppe par ligne, dimensions économiques "
        "en colonnes. Ordre fixe PERIN → PEE → PERECO → PERO."
    )
    horizons_disponibles = list(horizons)
    if horizons_disponibles:
        # Labels d'onglets descriptifs (pas de connotation valeur)
        labels_onglets = [f"{h} ans" for h in horizons_disponibles]
        onglets = st.tabs(labels_onglets)
        for onglet, h in zip(onglets, horizons_disponibles):
            with onglet:
                df_h = extraire_tableau_par_horizon(resultat, h)
                tableau_par_horizon(df_h, h)

    st.divider()

    # === VUE 3 : AUDITABILITÉ VISIBLE (SP21) ===
    # Panneau hypothèses doctrinales en st.expander (replié par défaut)
    # conforme A-Q1=β : visible mais non dominant visuellement.
    # cf. ARCHITECTURE_UI_RECEPTACLES.md §4.6 bis, §6.6.
    with st.expander("Hypothèses doctrinales utilisées", expanded=False):
        panneau_hypotheses_doctrinales(hypotheses)

    st.divider()

    # === VUE 4 : NAVIGATION AUDIT (SP22) ===
    # Génération PDF + panneau de téléchargement + compteurs structurels.
    # Conforme §4.9 (navigation ≠ storytelling), §4.10 (bouton non
    # conditionné par valeur économique), §5.4 (composants autorisés).
    #
    # Stratégie B-Q1=α : régénération à chaque rerun. Le coût (~100 ms)
    # est négligeable et la régénération systématique garantit l'absence
    # de divergence silencieuse entre l'écran et le PDF téléchargé.
    #
    # Stratégie cabinet/client : valeurs par défaut neutres en SP22
    # (la personnalisation cabinet/client fera l'objet d'un cadrage
    # ultérieur v1.3+).
    with st.expander("Navigation audit et téléchargement", expanded=False):
        from datetime import datetime
        timestamp_generation = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf_bytes = generer_pdf_audit(
            trace,
            cabinet_nom="Cabinet exemple",
            client_nom="Dirigeant exemple",
            doctrine_version=DOCTRINE_VERSION,
            doctrine_date=DOCTRINE_DATE,
            audit_pdf_spec_version=AUDIT_PDF_SPEC_VERSION,
            baseline_hash=BASELINE_HASH_DEFAUT,
        )
        counts = compter_etapes_pour_pdf(trace)
        panneau_navigation_audit(
            pdf_bytes=pdf_bytes,
            counts=counts,
            doctrine_version=DOCTRINE_VERSION,
            doctrine_date=DOCTRINE_DATE,
            audit_spec_version=AUDIT_SPEC_VERSION,
            audit_pdf_spec_version=AUDIT_PDF_SPEC_VERSION,
            baseline_hash=BASELINE_HASH_DEFAUT,
            timestamp_generation=timestamp_generation,
        )

    st.divider()

    # === DISCLAIMER COMPARABILITÉ (en queue) ===
    afficher_disclaimer_comparabilite()


# ============================================================
# SURFACE PUBLIQUE
# ============================================================
__all__ = [
    "page_receptacles",
    "TITRE_PAGE",
]
