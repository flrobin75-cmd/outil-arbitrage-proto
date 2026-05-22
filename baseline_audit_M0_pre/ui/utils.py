"""
Utilitaires partagés pour l'app Streamlit.

- Formatage français 2 décimales (€, %, etc.)
- Badges niveau de confiance
- Constantes UI partagées
"""

import streamlit as st
from doctrine import NIVEAU_PAR_MODULE, DESCRIPTION_NIVEAU, NiveauConfiance


# ============================================================
# FORMATAGE FRANÇAIS
# ============================================================
def format_eur(valeur, decimales=2):
    """Format français : 1 234,56 €"""
    if valeur is None:
        return "—"
    formatted = f"{valeur:,.{decimales}f}"
    # Remplacer , (séparateur milliers anglais) par espace, et . par ,
    formatted = formatted.replace(",", " ").replace(".", ",")
    return f"{formatted} €"


def format_pct(valeur, decimales=2):
    """Format français : 42,00 %"""
    if valeur is None:
        return "—"
    formatted = f"{valeur*100:.{decimales}f}".replace(".", ",")
    return f"{formatted} %"


def format_num(valeur, decimales=2):
    """Format français sans unité : 1 234,56"""
    if valeur is None:
        return "—"
    formatted = f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")
    return formatted


def format_eur_compact(valeur):
    """Format compact pour KPIs : 78 424 € (sans décimales si entier rond)"""
    if valeur is None:
        return "—"
    if abs(valeur - round(valeur)) < 0.005:
        return f"{int(round(valeur)):,}".replace(",", " ") + " €"
    return format_eur(valeur)


# ============================================================
# BADGES NIVEAU DE CONFIANCE
# ============================================================
NIVEAU_COULEURS = {
    NiveauConfiance.CONFORMITE_RENFORCEE: ("#10B981", "🟢"),   # vert
    NiveauConfiance.AVANCE: ("#3B82F6", "🔵"),                  # bleu
    NiveauConfiance.CADRAGE: ("#F59E0B", "🟡"),                 # ambre
    NiveauConfiance.INDICATIF: ("#8B5CF6", "🟣"),               # violet
}


def afficher_badge_niveau(nom_module: str):
    """Affiche un badge de niveau de confiance pour un module."""
    niveau = NIVEAU_PAR_MODULE.get(nom_module)
    if not niveau:
        return
    couleur, emoji = NIVEAU_COULEURS[niveau]
    desc = DESCRIPTION_NIVEAU[niveau]
    
    st.markdown(
        f"""
        <div style="display: inline-flex; align-items: center; gap: 8px;
                    background: rgba(255,255,255,0.05); border-left: 3px solid {couleur};
                    padding: 8px 12px; border-radius: 4px; margin-bottom: 12px;">
            <span style="font-size: 14px;">{emoji}</span>
            <div>
                <strong style="color: {couleur};">Niveau : {niveau.value}</strong>
                <div style="font-size: 12px; color: #94A3B8; margin-top: 2px;">{desc}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# STYLE PLOTLY COMMUN (thème sombre intégré)
# ============================================================
PLOTLY_LAYOUT_DARK = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#E5E7EB"),
)

GRID_COLOR = "#2A2D34"

COULEURS_STRATEGIES = {
    "A": "#94A3B8",   # gris - référence
    "B": "#60A5FA",   # bleu
    "C": "#34D399",   # vert
    "D": "#A78BFA",   # violet
}

COULEURS_RECEPTACLES = {
    "PEE": "#60A5FA",
    "PERECO": "#34D399",
    "PERO": "#F59E0B",
    "PERIN": "#A78BFA",
}


# ============================================================
# AVERTISSEMENT GLOBAL DE PIED DE PAGE
# ============================================================
FOOTER_GLOBAL = (
    "Outil indicatif à usage professionnel — ne se substitue pas à un conseil "
    "personnalisé. Moteur réglementaire mis à jour au 01/01/2026. "
    "Hypothèse : forfait social PERECO à 0 % conformément au régime PACTE "
    "actuellement applicable. Vérifier l'évolution du dispositif à compter de 2028."
)
