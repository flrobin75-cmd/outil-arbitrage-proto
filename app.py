"""
Outil d'arbitrage rémunération dirigeant - Prototype v19 → Streamlit
Application web pour test EC. Aucune formule Excel exposée.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from moteur import (
    Profil, arbitrage_complet, projection_5_ans, STRATEGIES,
    FS_PART, FS_INT, FS_ABO
)

# ============================================================
# CONFIG PAGE
# ============================================================
st.set_page_config(
    page_title="Outil d'arbitrage rémunération dirigeant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Palette discrète et professionnelle
COULEURS = {
    "A": "#94A3B8",  # gris : référence
    "B": "#60A5FA",  # bleu
    "C": "#34D399",  # vert
    "D": "#A78BFA",  # violet
}

# ============================================================
# EN-TÊTE
# ============================================================
st.title("Outil d'arbitrage rémunération dirigeant")
st.caption("Prototype v19 — test expert-comptable · session enregistrée")

# ============================================================
# SIDEBAR — INPUTS EC
# ============================================================
with st.sidebar:
    st.subheader("Profil client")

    forme = st.selectbox(
        "Forme juridique",
        ["SAS / SASU",
         "SARL (gérance minoritaire)",
         "SARL (gérance majoritaire) / EURL",
         "EI / EI à l'IS",
         "Profession libérale (BNC)",
         "SELARL / SELAS"],
        index=0,
    )

    effectif = st.selectbox(
        "Effectif",
        ["Sans salarié", "1-10 salariés", "11-49 salariés",
         "50-249 salariés", "≥ 250 salariés"],
        index=2,
    )

    st.divider()
    st.subheader("Foyer fiscal")

    situation = st.selectbox(
        "Situation familiale",
        ["Marié / pacsé", "Célibataire / divorcé / veuf"],
        index=0,
    )

    parts = st.number_input("Parts fiscales", min_value=1.0, max_value=6.0,
                            value=2.0, step=0.5)

    autres_rev = st.number_input("Autres revenus du foyer (€/an)",
                                 min_value=0, value=0, step=1000)

    div_foyer = st.number_input("Dividendes foyer hors enveloppe (€/an)",
                                min_value=0, value=0, step=1000)

    st.divider()
    st.subheader("Enveloppe à arbitrer")

    enveloppe = st.number_input("Coût employeur global (€/an)",
                                min_value=21876, value=120000, step=5000,
                                help="≥ 1 SMIC annuel (21 876 €)")

    benefice = st.number_input("Bénéfice IS de la société (€/an)",
                               min_value=0, value=200000, step=10000,
                               help="Bénéfice avant rémunération du dirigeant")

    st.divider()
    if st.button("🔄 Recalculer", use_container_width=True, type="primary"):
        st.session_state["recalcule"] = True

# ============================================================
# CALCUL
# ============================================================
profil = Profil(
    forme_juridique=forme,
    effectif=effectif,
    situation=situation,
    parts=parts,
    autres_revenus=autres_rev,
    dividendes_foyer_hors_enveloppe=div_foyer,
    enveloppe=enveloppe,
    benefice_is=benefice,
)

if profil.regime_social != "Assimilé salarié":
    st.warning(
        f"⚠ Régime social détecté : **{profil.regime_social}**. "
        "Le prototype ne couvre que l'Assimilé salarié pour cette version de test. "
        "Les modules TNS / Libéral / Salarié seront ajoutés en v2 après validation visuelle."
    )

res = arbitrage_complet(profil)
strategies = res["strategies"]
reco = res["recommandee"]

# ============================================================
# BANDEAU KPIs
# ============================================================
strat_reco = strategies[reco]
strat_a = strategies["A"]
gain = strat_reco["total_net"] - strat_a["total_net"]
efficacite = strat_reco["efficacite"] * 100

col1, col2, col3, col4 = st.columns(4)
col1.metric("Coût total société", f"{enveloppe:,.0f} €".replace(",", " "))
col2.metric(f"Net dirigeant — stratégie {reco}",
            f"{strat_reco['total_net']:,.0f} €".replace(",", " "))
col3.metric("Gain vs stratégie A",
            f"+{gain:,.0f} €".replace(",", " "),
            delta=f"{gain / strat_a['total_net'] * 100:+.1f} %")
col4.metric("Efficacité fiscale", f"{efficacite:.1f} %")

st.markdown(
    f"**Lecture :** avec une enveloppe de {enveloppe:,.0f} € "
    .replace(",", " ") +
    f"({profil.regime_social}, {situation.lower()}, {parts:g} parts), "
    f"la stratégie **{reco} — {strat_reco['nom']}** génère "
    f"**{strat_reco['total_net']:,.0f} € nets**".replace(",", " ") +
    f" pour le dirigeant, soit **{gain:+,.0f} € de gain annuel**".replace(",", " ") +
    " vs la rémunération directe pure."
)

st.divider()

# ============================================================
# ONGLETS
# ============================================================
tab1, tab2, tab3 = st.tabs(["📊 4 stratégies comparées",
                            "🔬 Décomposition stratégie retenue",
                            "📈 Projection patrimoine 5 ans"])

# --- TAB 1 : Comparatif 4 stratégies ---
with tab1:
    fig = go.Figure()

    codes = ["A", "B", "C", "D"]
    nets = [strategies[c]["total_net"] for c in codes]
    noms = [f"{c} — {strategies[c]['nom']}" for c in codes]
    couleurs_barres = [COULEURS[c] for c in codes]

    fig.add_trace(go.Bar(
        x=codes, y=nets,
        marker_color=couleurs_barres,
        text=[f"{n:,.0f} €".replace(",", " ") for n in nets],
        textposition="outside",
        hovertemplate="<b>%{customdata}</b><br>Net dirigeant : %{y:,.0f} €<extra></extra>",
        customdata=noms,
    ))

    fig.update_layout(
    title="Net dirigeant après fiscalité par stratégie",
    xaxis_title=None,
    yaxis_title="Net dirigeant annuel (€)",
    showlegend=False,
    height=420,
    margin=dict(t=60, b=40, l=60, r=20),
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(gridcolor="#2A2D34", tickformat=",.0f"),
    font=dict(color="#E5E7EB"),
)
    st.plotly_chart(fig, use_container_width=True)

    # Tableau de synthèse
    st.markdown("##### Détail des stratégies")
    import pandas as pd
    rows = []
    for code in codes:
        s = strategies[code]
        rows.append({
            "Stratégie": f"{code} — {s['nom']}",
            "Net dirigeant (€)": f"{s['total_net']:,.0f}".replace(",", " "),
            "Efficacité fiscale": f"{s['efficacite']*100:.1f} %",
            "Gain vs A (€)": f"{s['gain_vs_a']:+,.0f}".replace(",", " ") if code != "A" else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# --- TAB 2 : Décomposition stratégie retenue ---
with tab2:
    st.markdown(f"##### Stratégie {reco} — {strat_reco['nom']}")

    fig2 = make_subplots(rows=1, cols=2,
                         subplot_titles=("Allocation de l'enveloppe (coût société)",
                                         "Composition du net dirigeant"),
                         specs=[[{"type": "pie"}, {"type": "pie"}]])

    labels_alloc = []
    values_alloc = []
    for poste, val in [("Salaire", strat_reco["cout_salaire"]),
                       ("Dividendes", strat_reco["cout_dividendes"]),
                       ("Épargne sal. & PER", strat_reco["cout_epargne"]),
                       ("Périphériques", strat_reco["cout_peripheriques"])]:
        if val > 0:
            labels_alloc.append(poste)
            values_alloc.append(val)

    fig2.add_trace(go.Pie(
        labels=labels_alloc, values=values_alloc,
        hole=0.5,
        marker=dict(colors=["#94A3B8", "#60A5FA", "#34D399", "#A78BFA"]),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} €<extra></extra>",
    ), row=1, col=1)

    labels_net = []
    values_net = []
    for poste, val in [("Net salaire", strat_reco["net_salaire"]),
                       ("Net dividendes", strat_reco["net_dividendes"]),
                       ("Net épargne", strat_reco["net_epargne"]),
                       ("Net périphériques", strat_reco["net_peripheriques"])]:
        if val > 0:
            labels_net.append(poste)
            values_net.append(val)

    fig2.add_trace(go.Pie(
        labels=labels_net, values=values_net,
        hole=0.5,
        marker=dict(colors=["#94A3B8", "#60A5FA", "#34D399", "#A78BFA"]),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} €<extra></extra>",
    ), row=1, col=2)

fig2.update_layout(height=420, margin=dict(t=60, b=20, l=20, r=20),
                   showlegend=False,
                   template="plotly_dark",
                   paper_bgcolor="rgba(0,0,0,0)",
                   plot_bgcolor="rgba(0,0,0,0)",
                   font=dict(color="#E5E7EB"))
    st.plotly_chart(fig2, use_container_width=True)

    # Waterfall coût → net
    st.markdown("##### Du coût société au net dirigeant")
    perte = enveloppe - strat_reco["total_net"]
    fig3 = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["Coût employeur", "Cotisations / IS / IR", "Net dirigeant"],
        y=[enveloppe, -perte, strat_reco["total_net"]],
        text=[f"{enveloppe:,.0f} €".replace(",", " "),
              f"-{perte:,.0f} €".replace(",", " "),
              f"{strat_reco['total_net']:,.0f} €".replace(",", " ")],
        textposition="outside",
        connector={"line": {"color": "#D1D5DB"}},
        increasing={"marker": {"color": "#34D399"}},
        decreasing={"marker": {"color": "#F87171"}},
        totals={"marker": {"color": "#60A5FA"}},
    ))
    fig3.update_layout(height=360, margin=dict(t=40, b=40, l=60, r=20),
                   template="plotly_dark",
                   paper_bgcolor="rgba(0,0,0,0)",
                   plot_bgcolor="rgba(0,0,0,0)",
                   yaxis=dict(gridcolor="#2A2D34", tickformat=",.0f"),
                   font=dict(color="#E5E7EB"))
    st.plotly_chart(fig3, use_container_width=True)

# --- TAB 3 : Projection patrimoine 5 ans ---
with tab3:
    # Fraction capitalisable = épargne salariale + PER / total
    frac_capi_reco = (strat_reco["cout_epargne"] / strat_reco["cout_total"]
                      if strat_reco["cout_total"] > 0 else 0)
    proj_reco = projection_5_ans(strat_reco["total_net"], frac_capi_reco)
    proj_a = projection_5_ans(strat_a["total_net"], 0.0)

    fig4 = go.Figure()
    fig4.add_trace(go.Scatter(
        x=list(range(1, 6)), y=proj_a,
        name="Stratégie A (référence)",
        line=dict(color="#94A3B8", width=2, dash="dot"),
        mode="lines+markers",
        hovertemplate="Année %{x}<br>%{y:,.0f} €<extra></extra>",
    ))
    fig4.add_trace(go.Scatter(
        x=list(range(1, 6)), y=proj_reco,
        name=f"Stratégie {reco} (retenue)",
        line=dict(color=COULEURS[reco], width=3),
        mode="lines+markers",
        fill="tonexty",
        fillcolor="rgba(96, 165, 250, 0.1)",
        hovertemplate="Année %{x}<br>%{y:,.0f} €<extra></extra>",
    ))
    fig4.update_layout(
    title=f"Patrimoine net cumulé sur 5 ans (rendements : cash 2 %, épargne 4 %)",
    xaxis_title="Année",
    yaxis_title="Patrimoine cumulé (€)",
    height=440,
    margin=dict(t=60, b=40, l=60, r=20),
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(gridcolor="#2A2D34", tickformat=",.0f"),
    font=dict(color="#E5E7EB"),
    legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.02),
)
    st.plotly_chart(fig4, use_container_width=True)

    ecart_5_ans = proj_reco[-1] - proj_a[-1]
    st.info(f"💡 À 5 ans, la stratégie {reco} génère un patrimoine supérieur de "
            f"**{ecart_5_ans:+,.0f} €**".replace(",", " ") +
            f" vs la stratégie de référence (capitalisation composée).")

# ============================================================
# FOOTER
# ============================================================
st.divider()
col_left, col_right = st.columns([3, 1])
with col_left:
    st.caption(
        "Outil indicatif à usage professionnel — ne se substitue pas à un conseil personnalisé. "
        "Référentiel fiscal & social 2026 (cellules paramétrables non exposées dans cette interface). "
        "Prototype de test EC — les scénarios joués durant cette session sont journalisés pour analyse."
    )
with col_right:
    st.caption(f"v19 → proto Streamlit  ·  régime : {profil.regime_social}")
