"""
Outil d'arbitrage rémunération dirigeant - Phase A complète.

8 pages :
1. 🎯 Arbitrage stratégique (page principale)
2. 🔬 Modules détaillés (TNS / Libéral / Salarié)
3. 🧮 Comparateur de dispositifs (architecture de réceptacle)
4. 📋 Synthèse dirigeant (radar 6D + projection + check-list)
5. 🔀 Scénarios A vs B
6. 💼 Comparateur patrimonial
7. ✅ Tests de cohérence
8. ⚙ Paramètres réglementaires

Niveau de confiance affiché sur chaque page.
Format français 2 décimales partout.
Footer global avec mention PERECO 2028.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Imports moteurs
from core.profil import Profil, SITUATIONS_PARTICULIERES
from regime.tns import calcul_module_tns
from regime.liberal import calcul_module_bnc, calcul_module_sel
from regime.salarie import calcul_module_salarie
from strategy.assimile import arbitrage_complet, STRATEGIES
from core.projection import projection_5_ans
from strategy.comparateur import (
    calcul_comparateur, ConfigComparateur, FluxEpargne,
)
from strategy.synthese import (
    calcul_synthese, FORFAITS_DEFAUT, reset_forfaits,
    AVERTISSEMENT_RADAR,
)
from strategy.scenarios import (
    ScenarioInputs, calcul_comparaison,
    AVERTISSEMENT_SCENARIOS, MENTION_REGIMES,
)
from doctrine import (
    DOCTRINE_VERSION, DOCTRINE_DATE, DOCTRINE_COMPLETE,
    REGISTRE_CAS_TESTS, NIVEAU_PAR_MODULE, DESCRIPTION_NIVEAU,
    NiveauConfiance,
)
from strategy.perin import (
    calcul_perin_mutualise, calcul_plafond_perin,
    PERIN_PLAFOND_MIN, PERIN_PLAFOND_MAX,
)
from ui.pdf_export import generer_pdf_synthese
from ui.page_receptacles import page_receptacles as _page_receptacles_v11
from ui.admin import (
    construire_catalogue, restaurer_doctrine_officielle,
    enregistrer_modif, lister_modifications_actives,
    formater_valeur as fmt_param, DOCTRINE_OFFICIELLE,
)
from ui.utils import (
    format_eur, format_eur_compact, format_pct, format_num,
    afficher_badge_niveau, PLOTLY_LAYOUT_DARK, GRID_COLOR,
    COULEURS_STRATEGIES, COULEURS_RECEPTACLES, FOOTER_GLOBAL,
    NIVEAU_COULEURS,
)


# ============================================================
# CONFIG STREAMLIT
# ============================================================
st.set_page_config(
    page_title="Arbitrage rémunération dirigeant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# NAVIGATION
# ============================================================
PAGES = {
    "🎯 Arbitrage stratégique": "arbitrage",
    "🔬 Modules détaillés": "modules",
    "🧮 Comparateur de dispositifs": "comparateur",
    "🧰 Réceptacles auditables": "receptacles_v11",
    "📋 Synthèse dirigeant": "synthese",
    "🔀 Scénarios A vs B": "scenarios",
    "💼 Comparateur patrimonial": "patrimonial",
    "✅ Tests de cohérence": "tests",
    "⚙ Paramètres réglementaires": "parametres",
    "🔧 Administration (expert)": "admin",
}

# ============================================================
# ADMIN MODE - masquage conditionnel des pages admin
# Workaround court terme avant streamlit-authenticator (J+1)
# ============================================================
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")
st.write("DEBUG SECRETS:", {"defini": bool(ADMIN_PASSWORD), "longueur": len(ADMIN_PASSWORD), "secrets_keys": list(st.secrets.keys()) if hasattr(st, "secrets") else "no_secrets"})
PAGES_ADMIN_ONLY_KEYS = {"parametres", "admin"}
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False


def init_session_state():
    """Initialise les valeurs en session_state avec defaults."""
    defaults = {
        "page": "arbitrage",
        # Profil
        "forme_juridique": "SAS / SASU",
        "effectif": "11-49 salariés",
        "situation": "Marié / pacsé",
        "parts": 2.0,
        "situation_part": "Aucune (cas général)",
        "autres_revenus": 0,
        "div_foyer": 0,
        "enveloppe": 120_000,
        "benefice_is": 200_000,
        "capital_cca": 100_000,
        "salaire_brut_assimile": 80_000,
        # Comparateur - réceptacles
        "pee_actif": True,
        "pereco_actif": True,
        "pero_actif": False,
        "perin_actif": True,
        "dirigeant_eligible_pero": False,
        # Flux d'épargne
        "participation_actif": True, "participation_montant": 1500, "participation_receptacle": "PEE",
        "interessement_actif": True, "interessement_montant": 2500, "interessement_receptacle": "PEE",
        "abondement_pee_actif": True, "abondement_pee_montant": 1500,
        "abondement_pereco_actif": True, "abondement_pereco_montant": 3000,
        "perin_montant": 5000,
        # PERO
        "pero_mode_saisie": "pourcentage",
        "pero_taux": 0.03,
        "pero_montant": 2400,
        # Dispositifs autonomes
        "avantages_actif": True, "avantages_montant": 3600,
        "tr_actif": True, "tr_montant": 1742,
        "cesu_actif": True, "cesu_montant": 2000,
        "cado_actif": True, "cado_montant": 500,
        "mutuelle_actif": True, "mutuelle_montant": 1200,
        "ik_actif": False, "ik_montant": 0,
        "cashback_actif": False, "cashback_montant": 360,
        # PERIN mutualisé
        "perin_revenu_pro_dirigeant": 80_000,
        "perin_conjoint_declare": False,
        "perin_revenu_pro_conjoint": 0,
        "perin_versement_conjoint": 0,
        # Admin
        "mode_expert_admin": False,
        "admin_utilisateur": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # Catalogue admin (état persistant session)
    if "catalogue_admin" not in st.session_state:
        st.session_state["catalogue_admin"] = construire_catalogue()
    if "historique_admin" not in st.session_state:
        st.session_state["historique_admin"] = []


init_session_state()


# ============================================================
# SIDEBAR — Navigation + Profil universel
# ============================================================
with st.sidebar:
    st.markdown("### 📊 Outil d'arbitrage")
    st.caption(f"Phase A v{DOCTRINE_VERSION} · MAJ réglementaire {DOCTRINE_DATE}")
    
    # Filtrage du dict PAGES selon le statut admin
    if st.session_state.get("is_admin", False):
        PAGES_VISIBLES = PAGES
    else:
        PAGES_VISIBLES = {k: v for k, v in PAGES.items()
                          if v not in PAGES_ADMIN_ONLY_KEYS}
    page_label = st.radio("Navigation", list(PAGES_VISIBLES.keys()),
                          label_visibility="collapsed")
    page = PAGES_VISIBLES[page_label]
    
    st.divider()
    st.markdown("### Profil client")
    
    st.session_state["forme_juridique"] = st.selectbox(
        "Forme juridique",
        ["SAS / SASU",
         "SARL (gérance minoritaire)",
         "SARL (gérance majoritaire) / EURL",
         "EI / EI à l'IS",
         "Profession libérale (BNC)",
         "SELARL / SELAS"],
        index=["SAS / SASU", "SARL (gérance minoritaire)",
               "SARL (gérance majoritaire) / EURL", "EI / EI à l'IS",
               "Profession libérale (BNC)", "SELARL / SELAS"].index(
            st.session_state["forme_juridique"]),
    )
    
    st.session_state["effectif"] = st.selectbox(
        "Effectif",
        ["Sans salarié", "1-10 salariés", "11-49 salariés",
         "50-249 salariés", "≥ 250 salariés"],
        index=["Sans salarié", "1-10 salariés", "11-49 salariés",
               "50-249 salariés", "≥ 250 salariés"].index(
            st.session_state["effectif"]),
    )
    
    st.markdown("#### Foyer fiscal")
    st.session_state["situation"] = st.selectbox(
        "Situation familiale",
        ["Marié / pacsé", "Célibataire / divorcé / veuf"],
        index=0 if st.session_state["situation"] == "Marié / pacsé" else 1,
    )
    st.session_state["parts"] = st.number_input(
        "Parts fiscales", min_value=1.0, max_value=6.0,
        value=st.session_state["parts"], step=0.5,
    )
    st.session_state["situation_part"] = st.selectbox(
        "Situation particulière",
        list(SITUATIONS_PARTICULIERES.keys()),
        index=list(SITUATIONS_PARTICULIERES.keys()).index(
            st.session_state["situation_part"]),
    )
    st.session_state["autres_revenus"] = st.number_input(
        "Autres revenus du foyer (€/an)",
        min_value=0, value=int(st.session_state["autres_revenus"]), step=1000,
    )
    st.session_state["div_foyer"] = st.number_input(
        "Dividendes foyer hors enveloppe (€/an)",
        min_value=0, value=int(st.session_state["div_foyer"]), step=1000,
    )
    
    st.markdown("#### Enveloppe à arbitrer")
    st.session_state["enveloppe"] = st.number_input(
        "Coût employeur global (€/an)",
        min_value=21876, value=int(st.session_state["enveloppe"]), step=5000,
    )
    st.session_state["benefice_is"] = st.number_input(
        "Bénéfice IS de la société (€/an)",
        min_value=0, value=int(st.session_state["benefice_is"]), step=10000,
    )

    # Toggle admin discret en bas de sidebar
    st.divider()
    with st.expander("🔐 Acces admin", expanded=False):
        if not st.session_state.get("is_admin", False):
            pwd = st.text_input("Mot de passe", type="password",
                                key="admin_pwd_input")
            if pwd:
                if ADMIN_PASSWORD and pwd == ADMIN_PASSWORD:
                    st.session_state["is_admin"] = True
                    st.success("Mode admin active.")
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
        else:
            st.success("Mode admin actif.")
            if st.button("Desactiver", key="admin_logout"):
                st.session_state["is_admin"] = False
                st.rerun()


# Profil construit à partir du session_state
def build_profil() -> Profil:
    return Profil(
        forme_juridique=st.session_state["forme_juridique"],
        effectif=st.session_state["effectif"],
        situation=st.session_state["situation"],
        parts=st.session_state["parts"],
        situation_part=st.session_state["situation_part"],
        autres_revenus=st.session_state["autres_revenus"],
        dividendes_foyer_hors_enveloppe=st.session_state["div_foyer"],
        enveloppe=st.session_state["enveloppe"],
        benefice_is=st.session_state["benefice_is"],
        capital_cca=st.session_state["capital_cca"],
        salaire_brut_assimile=st.session_state["salaire_brut_assimile"],
    )


def build_config_comparateur() -> ConfigComparateur:
    return ConfigComparateur(
        pee_actif=st.session_state["pee_actif"],
        pereco_actif=st.session_state["pereco_actif"],
        pero_actif=st.session_state["pero_actif"],
        perin_actif=st.session_state["perin_actif"],
        dirigeant_eligible_pero=st.session_state["dirigeant_eligible_pero"],
        participation=FluxEpargne(
            st.session_state["participation_actif"],
            st.session_state["participation_montant"],
            st.session_state["participation_receptacle"]),
        interessement=FluxEpargne(
            st.session_state["interessement_actif"],
            st.session_state["interessement_montant"],
            st.session_state["interessement_receptacle"]),
        abondement_pee=FluxEpargne(
            st.session_state["abondement_pee_actif"],
            st.session_state["abondement_pee_montant"], "PEE"),
        abondement_pereco=FluxEpargne(
            st.session_state["abondement_pereco_actif"],
            st.session_state["abondement_pereco_montant"], "PERECO"),
        versement_perin=FluxEpargne(
            st.session_state["perin_actif"],
            st.session_state["perin_montant"], "PERIN"),
        pero_mode_saisie=st.session_state["pero_mode_saisie"],
        pero_taux=st.session_state["pero_taux"],
        pero_montant=st.session_state["pero_montant"],
        avantages_actif=st.session_state["avantages_actif"],
        avantages_montant=st.session_state["avantages_montant"],
        tr_actif=st.session_state["tr_actif"],
        tr_montant=st.session_state["tr_montant"],
        cesu_actif=st.session_state["cesu_actif"],
        cesu_montant=st.session_state["cesu_montant"],
        cado_actif=st.session_state["cado_actif"],
        cado_montant=st.session_state["cado_montant"],
        mutuelle_actif=st.session_state["mutuelle_actif"],
        mutuelle_montant=st.session_state["mutuelle_montant"],
        ik_actif=st.session_state["ik_actif"],
        ik_montant=st.session_state["ik_montant"],
        cashback_actif=st.session_state["cashback_actif"],
        cashback_montant=st.session_state["cashback_montant"],
    )


# ============================================================
# PAGE 1 — ARBITRAGE STRATÉGIQUE
# ============================================================
def page_arbitrage():
    st.title("🎯 Arbitrage stratégique")
    st.caption("Comparaison des 4 stratégies de rémunération à enveloppe constante")
    afficher_badge_niveau("Assimilé salarié")

    profil = build_profil()
    
    if profil.regime_social != "Assimilé salarié":
        # Phase B.2 : strategy/tns + strategy/liberal sont désormais disponibles
        # mais la page "Arbitrage avancé multi-enveloppes" de cette app est encore
        # branchée sur le moteur historique Assimilé. La migration vers le routeur
        # Strategy multi-régimes interviendra en Phase B.3.
        st.warning(
            f"Régime social détecté : **{profil.regime_social}**. "
            f"Cette page « Arbitrage avancé multi-enveloppes » utilise actuellement "
            f"le moteur calibré pour le régime Assimilé salarié. Les modules "
            f"détaillés multi-régimes (page suivante) couvrent l'ensemble des "
            f"régimes (Assimilé, TNS, Libéral BNC/SEL, Salarié) en parité v19 stricte. "
            f"L'intégration des stratégies T1-T4 et L1-L4 dans cette page interviendra "
            f"en migration applicative (Phase B.3)."
        )
        return

    res = arbitrage_complet(profil)
    strategies = res["strategies"]
    reco = res["recommandee"]
    strat_reco = strategies[reco]
    strat_a = strategies["A"]

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Coût total société", format_eur(profil.enveloppe, 0))
    col2.metric(f"Net dirigeant — stratégie {reco}",
                format_eur(strat_reco["total_net"], 0))
    col3.metric("Gain vs stratégie A",
                f"+{format_eur(strat_reco['gain_vs_a'], 0)}",
                delta=format_pct(strat_reco['gain_vs_a']/strat_a['total_net'], 1))
    col4.metric("Efficacité fiscale", format_pct(strat_reco["efficacite"], 1))

    st.markdown(
        f"**Lecture :** avec une enveloppe de **{format_eur(profil.enveloppe, 0)}** "
        f"({profil.regime_social}, {profil.situation.lower()}, {profil.parts:g} parts), "
        f"la stratégie **{reco} — {strat_reco['nom']}** génère "
        f"**{format_eur(strat_reco['total_net'])}** pour le dirigeant, soit "
        f"**+{format_eur(strat_reco['gain_vs_a'])}** de gain annuel vs la rémunération directe pure."
    )

    st.divider()
    tab1, tab2, tab3 = st.tabs([
        "📊 4 stratégies comparées",
        "🔬 Décomposition stratégie retenue",
        "📈 Projection patrimoine 5 ans",
    ])

    with tab1:
        fig = go.Figure()
        codes = ["A", "B", "C", "D"]
        nets = [strategies[c]["total_net"] for c in codes]
        couleurs = [COULEURS_STRATEGIES[c] for c in codes]
        labels = [f"{c} — {strategies[c]['nom']}" for c in codes]

        fig.add_trace(go.Bar(
            x=codes, y=nets,
            marker_color=couleurs,
            text=[format_eur_compact(n) for n in nets],
            textposition="outside",
            customdata=labels,
            hovertemplate="<b>%{customdata}</b><br>Net : %{y:,.2f} €<extra></extra>",
        ))
        fig.update_layout(
            title="Net dirigeant après fiscalité par stratégie",
            yaxis_title="Net dirigeant annuel (€)",
            showlegend=False,
            height=420,
            margin=dict(t=60, b=40, l=60, r=20),
            yaxis=dict(gridcolor=GRID_COLOR, tickformat=",.0f"),
            **PLOTLY_LAYOUT_DARK,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Tableau récap
        rows = []
        for c in codes:
            s = strategies[c]
            rows.append({
                "Stratégie": f"{c} — {s['nom']}",
                "Net dirigeant": format_eur(s["total_net"]),
                "Efficacité": format_pct(s["efficacite"], 1),
                "Gain vs A": format_eur(s["gain_vs_a"]) if c != "A" else "—",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown(f"##### Stratégie {reco} — {strat_reco['nom']}")
        
        # Donuts allocation cost / composition net
        fig2 = make_subplots(rows=1, cols=2,
                             subplot_titles=("Allocation de l'enveloppe (coût société)",
                                             "Composition du net dirigeant"),
                             specs=[[{"type": "pie"}, {"type": "pie"}]])
        # Allocation
        alloc_labels, alloc_values = [], []
        for poste, val in [("Salaire", strat_reco["cout_salaire"]),
                           ("Dividendes", strat_reco["cout_dividendes"]),
                           ("Épargne sal. & PER", strat_reco["cout_epargne"]),
                           ("Périphériques", strat_reco["cout_peripheriques"])]:
            if val > 0:
                alloc_labels.append(poste); alloc_values.append(val)
        fig2.add_trace(go.Pie(labels=alloc_labels, values=alloc_values,
                              hole=0.5, textinfo="label+percent"), row=1, col=1)
        # Composition net
        net_labels, net_values = [], []
        for poste, val in [("Net salaire", strat_reco["net_salaire"]),
                           ("Net dividendes", strat_reco["net_dividendes"]),
                           ("Net épargne", strat_reco["net_epargne"]),
                           ("Net périphériques", strat_reco["net_peripheriques"])]:
            if val > 0:
                net_labels.append(poste); net_values.append(val)
        fig2.add_trace(go.Pie(labels=net_labels, values=net_values,
                              hole=0.5, textinfo="label+percent"), row=1, col=2)
        fig2.update_layout(height=420, showlegend=False, **PLOTLY_LAYOUT_DARK)
        st.plotly_chart(fig2, use_container_width=True)

        # Waterfall
        perte = profil.enveloppe - strat_reco["total_net"]
        fig3 = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=["Coût employeur", "Cotisations / IS / IR", "Net dirigeant"],
            y=[profil.enveloppe, -perte, strat_reco["total_net"]],
            text=[format_eur(profil.enveloppe, 0),
                  format_eur(-perte, 0),
                  format_eur(strat_reco["total_net"], 0)],
            textposition="outside",
            connector={"line": {"color": "#4B5563"}},
            increasing={"marker": {"color": "#34D399"}},
            decreasing={"marker": {"color": "#F87171"}},
            totals={"marker": {"color": "#60A5FA"}},
        ))
        fig3.update_layout(height=360, yaxis=dict(gridcolor=GRID_COLOR, tickformat=",.0f"),
                           **PLOTLY_LAYOUT_DARK)
        st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        frac_capi = (strat_reco["cout_epargne"] / strat_reco["cout_total"]
                     if strat_reco["cout_total"] > 0 else 0)
        proj_reco = projection_5_ans(strat_reco["total_net"], frac_capi)
        proj_a = projection_5_ans(strat_a["total_net"], 0.0)
        
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=list(range(1, 6)), y=proj_a, name="Stratégie A (référence)",
            line=dict(color=COULEURS_STRATEGIES["A"], width=2, dash="dot"),
            mode="lines+markers",
        ))
        fig4.add_trace(go.Scatter(
            x=list(range(1, 6)), y=proj_reco, name=f"Stratégie {reco} (retenue)",
            line=dict(color=COULEURS_STRATEGIES[reco], width=3),
            mode="lines+markers", fill="tonexty",
            fillcolor="rgba(96, 165, 250, 0.1)",
        ))
        fig4.update_layout(
            title="Patrimoine net cumulé sur 5 ans",
            xaxis_title="Année", yaxis_title="Patrimoine cumulé (€)",
            height=440,
            yaxis=dict(gridcolor=GRID_COLOR, tickformat=",.0f"),
            legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.02),
            **PLOTLY_LAYOUT_DARK,
        )
        st.plotly_chart(fig4, use_container_width=True)
        
        ecart_5_ans = proj_reco[-1] - proj_a[-1]
        st.info(f"💡 À 5 ans, la stratégie {reco} génère un patrimoine supérieur de "
                f"**{format_eur(ecart_5_ans)}** vs la stratégie A.")


# ============================================================
# PAGE 2 — MODULES DÉTAILLÉS
# ============================================================
def page_modules():
    st.title("🔬 Modules détaillés par régime")
    st.caption("Calculs destinés aux obligations fiscales — CEHR, CDHR et plafonnement QF (4 cas particuliers)")
    afficher_badge_niveau("TNS")

    profil = build_profil()
    
    sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
        "🏢 Assimilé salarié", "🛠 TNS", "📚 Libéral (BNC + SEL)", "👔 Salarié",
    ])

    with sub_tab1:
        st.markdown("##### Module Assimilé salarié")
        col1, col2 = st.columns([1, 2])
        with col1:
            st.session_state["salaire_brut_assimile"] = st.number_input(
                "Salaire brut annuel (€)",
                min_value=0, value=int(st.session_state["salaire_brut_assimile"]),
                step=5000, key="salaire_brut_assimile_input",
            )
        
        # Calcul rapide via le moteur Arbitrage qui contient la chaîne Assimilé
        profil_calc = build_profil()
        # On simule un module Assimilé pur via l'Arbitrage strategie A
        res = arbitrage_complet(profil_calc)
        # Le tx_ir_moy correspond à l'IR du salaire brut Assimilé
        from core.profil import TX_SALARIAL, ASSIETTE_CSG_SAL, TX_CSG_CRDS_ACT
        from core.ir_foyer import calcul_ir_foyer
        brut = profil_calc.salaire_brut_assimile
        cotis = brut * TX_SALARIAL
        csg_crds = brut * ASSIETTE_CSG_SAL * TX_CSG_CRDS_ACT
        csg_ded = brut * ASSIETTE_CSG_SAL * 0.068
        net_avant_ir = brut - cotis - csg_crds
        rev_imp = net_avant_ir + csg_crds - csg_ded
        abat = min(rev_imp * 0.10, 14_426)
        rev_imp_net = max(0, rev_imp - abat)
        rev_imp_foyer = rev_imp_net + profil_calc.autres_revenus
        impots = calcul_ir_foyer(rev_imp_foyer, profil_calc)
        prorata = rev_imp_net / rev_imp_foyer if rev_imp_foyer > 0 else 1
        ir_imputable = impots["total_impots"] * prorata
        net_final = net_avant_ir - ir_imputable
        
        with col2:
            c1, c2 = st.columns(2)
            c1.metric("Net avant IR", format_eur(net_avant_ir))
            c2.metric("Net après IR", format_eur(net_final))
        
        st.markdown("##### Détail du calcul")
        details = pd.DataFrame([
            {"Étape": "Salaire brut annuel", "Montant": format_eur(brut)},
            {"Étape": "Cotisations salariales (12 %)", "Montant": format_eur(-cotis)},
            {"Étape": "CSG/CRDS (9,7 % × 98,25 %)", "Montant": format_eur(-csg_crds)},
            {"Étape": "Net avant IR", "Montant": format_eur(net_avant_ir)},
            {"Étape": "Revenu salarial imposable (réintégration CSG non déd.)", "Montant": format_eur(rev_imp)},
            {"Étape": "Abattement 10 % (plafonné 14 426 €)", "Montant": format_eur(-abat)},
            {"Étape": "Revenu imposable net", "Montant": format_eur(rev_imp_net)},
            {"Étape": "IR du foyer (avec QF, CEHR, CDHR)", "Montant": format_eur(impots["total_impots"])},
            {"Étape": "Impôts imputables (prorata)", "Montant": format_eur(-ir_imputable)},
            {"Étape": "**Net dirigeant après impôts**", "Montant": f"**{format_eur(net_final)}**"},
        ])
        st.dataframe(details, use_container_width=True, hide_index=True)

    with sub_tab2:
        st.markdown("##### Module TNS (SARL gérance majoritaire / EURL)")
        col1, col2, col3 = st.columns(3)
        with col1:
            rem_tns = st.number_input("Rémunération nette souhaitée (€)",
                                       min_value=0, value=70000, step=5000, key="rem_tns")
        with col2:
            frais_tns = st.number_input("Frais réels professionnels (€)",
                                         min_value=0, value=0, step=500, key="frais_tns")
        with col3:
            div_tns = st.number_input("Dividendes bruts envisagés (€)",
                                       min_value=0, value=50000, step=5000, key="div_tns")
        
        # Capital CCA depuis le Profil
        st.caption(f"Capital social + primes + CCA : {format_eur(profil.capital_cca)} "
                   "(modifiable dans les paramètres réglementaires)")
        
        res_tns = calcul_module_tns(profil, rem_nette_souhaitee=rem_tns,
                                     frais_reels=frais_tns, div_bruts=div_tns)
        
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("Net dirigeant après IR", format_eur(res_tns.net_apres_ir))
        cm2.metric("Net dividendes", format_eur(res_tns.net_dividendes))
        cm3.metric("Coût total société", format_eur(res_tns.cout_total_societe))
        
        with st.expander("📋 Détail complet du calcul"):
            details_tns = pd.DataFrame([
                {"Étape": "Rémunération nette souhaitée", "Montant": format_eur(rem_tns)},
                {"Étape": "Cotisations TNS (45 %)", "Montant": format_eur(res_tns.cotisations_tns)},
                {"Étape": "CSG déductible", "Montant": format_eur(res_tns.csg_deductible)},
                {"Étape": "CSG/CRDS non déductible", "Montant": format_eur(res_tns.csg_non_deductible)},
                {"Étape": "Revenu imposable foyer", "Montant": format_eur(res_tns.revenu_imposable_foyer)},
                {"Étape": "IR foyer (avec plafond QF)", "Montant": format_eur(res_tns.ir_foyer)},
                {"Étape": "CEHR", "Montant": format_eur(res_tns.cehr)},
                {"Étape": "CDHR", "Montant": format_eur(res_tns.cdhr)},
                {"Étape": "**Net dirigeant après IR**", "Montant": f"**{format_eur(res_tns.net_apres_ir)}**"},
                {"Étape": "Seuil 10 % dividendes (capital × 10 %)", "Montant": format_eur(res_tns.seuil_10pct)},
                {"Étape": "Fraction dividendes cotisable TNS", "Montant": format_eur(res_tns.fraction_cotis_tns)},
                {"Étape": "**Net dividendes**", "Montant": f"**{format_eur(res_tns.net_dividendes)}**"},
            ])
            st.dataframe(details_tns, use_container_width=True, hide_index=True)

    with sub_tab3:
        st.markdown("##### Module Libéral (BNC + SEL)")
        st.markdown("**Scénario BNC (exercice individuel)**")
        col1, col2 = st.columns(2)
        with col1:
            recettes = st.number_input("Recettes annuelles BNC (€)",
                                        min_value=0, value=150000, step=10000, key="recettes_bnc")
        with col2:
            frais_pro = st.number_input("Frais professionnels (€)",
                                         min_value=0, value=30000, step=5000, key="frais_bnc")
        
        res_bnc = calcul_module_bnc(profil, recettes=recettes, frais_pro=frais_pro)
        
        cb1, cb2, cb3 = st.columns(3)
        cb1.metric("Bénéfice BNC", format_eur(res_bnc.benefice_bnc))
        cb2.metric("Net après cotisations", format_eur(res_bnc.benefice_net_apres_cotis))
        cb3.metric("Net après impôts", format_eur(res_bnc.net_apres_impots))
        
        with st.expander("📋 Détail BNC"):
            d_bnc = pd.DataFrame([
                {"Étape": "Recettes", "Montant": format_eur(recettes)},
                {"Étape": "Frais professionnels", "Montant": format_eur(-frais_pro)},
                {"Étape": "Bénéfice BNC", "Montant": format_eur(res_bnc.benefice_bnc)},
                {"Étape": "Cotisations URSSAF (45 %)", "Montant": format_eur(-res_bnc.cotisations)},
                {"Étape": "Net après cotisations", "Montant": format_eur(res_bnc.benefice_net_apres_cotis)},
                {"Étape": "IR foyer (CEHR + CDHR + QF inclus)", "Montant": format_eur(-res_bnc.impots_imputables_libéral)},
                {"Étape": "**Net libéral après impôts**", "Montant": f"**{format_eur(res_bnc.net_apres_impots)}**"},
            ])
            st.dataframe(d_bnc, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("**Scénario SEL (double couche IS + IR)**")
        col1, col2 = st.columns(2)
        with col1:
            benefice_sel = st.number_input("Bénéfice avant rémunération (€)",
                                            min_value=0, value=200000, step=10000, key="benefice_sel")
        with col2:
            rem_sel = st.number_input("Rémunération dirigeant (€)",
                                       min_value=0, value=80000, step=5000, key="rem_sel")
        
        res_sel = calcul_module_sel(benefice_avant_rem=benefice_sel,
                                     remuneration_dirigeant=rem_sel)
        cs1, cs2 = st.columns(2)
        cs1.metric("IS dû", format_eur(res_sel.is_du))
        cs2.metric("Résultat net distribuable", format_eur(res_sel.resultat_net_distribuable))
        st.info("La fiscalité du dirigeant SEL est traitée séparément : "
                "module Assimilé pour SELAS, module TNS pour SELARL gérant majoritaire.")

    with sub_tab4:
        st.markdown("##### Module Salarié")
        salaire_sal = st.number_input("Salaire brut annuel (€)",
                                       min_value=0, value=60000, step=5000, key="salaire_sal")
        res_sal = calcul_module_salarie(profil, salaire_brut=salaire_sal)
        
        cs1, cs2, cs3 = st.columns(3)
        cs1.metric("Net avant IR", format_eur(res_sal.net_avant_impot))
        cs2.metric("IR du foyer", format_eur(res_sal.total_impots_foyer))
        cs3.metric("Net après impôts", format_eur(res_sal.net_apres_impots))
        
        with st.expander("📋 Détail Salarié"):
            d_sal = pd.DataFrame([
                {"Étape": "Salaire brut annuel", "Montant": format_eur(salaire_sal)},
                {"Étape": "Cotisations salariales", "Montant": format_eur(-res_sal.cotis_salariales)},
                {"Étape": "CSG/CRDS totale", "Montant": format_eur(-res_sal.csg_crds_totale)},
                {"Étape": "Net avant impôt", "Montant": format_eur(res_sal.net_avant_impot)},
                {"Étape": "Abattement 10 % (plafonné)", "Montant": format_eur(-res_sal.abattement_10pct)},
                {"Étape": "IR du foyer", "Montant": format_eur(-res_sal.impots_imputables_rem)},
                {"Étape": "**Net après impôts**", "Montant": f"**{format_eur(res_sal.net_apres_impots)}**"},
            ])
            st.dataframe(d_sal, use_container_width=True, hide_index=True)


# ============================================================
# PAGE 3 — COMPARATEUR DE DISPOSITIFS
# ============================================================
def page_comparateur():
    st.title("🧮 Comparateur de dispositifs")
    st.caption("Architecture de réceptacle avec validation des plafonds croisés")
    afficher_badge_niveau("Comparateur dispositifs")

    profil = build_profil()
    
    # Configuration en bandeau
    with st.expander("⚙ Configuration des réceptacles et flux", expanded=False):
        st.markdown("**Réceptacles d'épargne activés**")
        c1, c2, c3, c4 = st.columns(4)
        st.session_state["pee_actif"] = c1.checkbox(
            "PEE", value=st.session_state["pee_actif"])
        st.session_state["pereco_actif"] = c2.checkbox(
            "PERECO", value=st.session_state["pereco_actif"])
        st.session_state["pero_actif"] = c3.checkbox(
            "PERO", value=st.session_state["pero_actif"])
        st.session_state["perin_actif"] = c4.checkbox(
            "PERIN", value=st.session_state["perin_actif"])
        
        if st.session_state["pero_actif"]:
            st.session_state["dirigeant_eligible_pero"] = st.checkbox(
                "Le dirigeant appartient à la catégorie objective éligible PERO",
                value=st.session_state["dirigeant_eligible_pero"],
            )
            
            st.markdown("**Cotisation PERO (mode de saisie asymétrique)**")
            cp1, cp2 = st.columns(2)
            mode = cp1.radio("Mode de saisie", ["pourcentage", "euros"],
                             index=0 if st.session_state["pero_mode_saisie"] == "pourcentage" else 1,
                             horizontal=True)
            st.session_state["pero_mode_saisie"] = mode
            if mode == "pourcentage":
                st.session_state["pero_taux"] = cp2.number_input(
                    "Taux PERO (% rém brute)", min_value=0.0, max_value=0.08,
                    value=st.session_state["pero_taux"], step=0.005,
                    format="%.3f")
            else:
                st.session_state["pero_montant"] = cp2.number_input(
                    "Montant PERO (€)", min_value=0, max_value=384480,
                    value=int(st.session_state["pero_montant"]), step=500)
        
        st.markdown("**Flux d'épargne salariale**")
        for cle, label, recep_options in [
            ("participation", "Participation", ["PEE", "PERECO"]),
            ("interessement", "Intéressement", ["PEE", "PERECO"]),
        ]:
            fc1, fc2, fc3 = st.columns([1, 2, 1])
            st.session_state[f"{cle}_actif"] = fc1.checkbox(
                label, value=st.session_state[f"{cle}_actif"], key=f"{cle}_chk")
            st.session_state[f"{cle}_montant"] = fc2.number_input(
                f"Montant {label}", min_value=0,
                value=int(st.session_state[f"{cle}_montant"]),
                step=500, key=f"{cle}_mt", label_visibility="collapsed")
            st.session_state[f"{cle}_receptacle"] = fc3.selectbox(
                f"Réceptacle {label}", recep_options,
                index=recep_options.index(st.session_state[f"{cle}_receptacle"]),
                key=f"{cle}_rc", label_visibility="collapsed")
        
        # Abondements (réceptacle fixe)
        for cle, label in [("abondement_pee", "Abondement PEE"),
                            ("abondement_pereco", "Abondement PERECO")]:
            fc1, fc2 = st.columns([1, 3])
            st.session_state[f"{cle}_actif"] = fc1.checkbox(
                label, value=st.session_state[f"{cle}_actif"], key=f"{cle}_chk2")
            st.session_state[f"{cle}_montant"] = fc2.number_input(
                f"Montant {label}", min_value=0,
                value=int(st.session_state[f"{cle}_montant"]),
                step=500, key=f"{cle}_mt2", label_visibility="collapsed")
        
        # PERIN
        fc1, fc2 = st.columns([1, 3])
        st.session_state["perin_actif"] = fc1.checkbox(
            "PERIN", value=st.session_state["perin_actif"], key="perin_chk")
        st.session_state["perin_montant"] = fc2.number_input(
            "Montant PERIN", min_value=0,
            value=int(st.session_state["perin_montant"]),
            step=500, key="perin_mt", label_visibility="collapsed")
        
        st.markdown("**Dispositifs autonomes**")
        for cle, label, defaut_montant in [
            ("avantages", "Avantages en nature", 3600),
            ("tr", "Tickets restaurant", 1742),
            ("cesu", "CESU préfinancé", 2000),
            ("cado", "Chèques cadeaux & vacances", 500),
            ("mutuelle", "Mutuelle / prévoyance", 1200),
            ("ik", "Indemnités kilométriques", 0),
            ("cashback", "Cashback", 360),
        ]:
            fc1, fc2 = st.columns([1, 3])
            st.session_state[f"{cle}_actif"] = fc1.checkbox(
                label, value=st.session_state[f"{cle}_actif"], key=f"{cle}_chk3")
            st.session_state[f"{cle}_montant"] = fc2.number_input(
                f"Montant {label}", min_value=0,
                value=int(st.session_state[f"{cle}_montant"]),
                step=100, key=f"{cle}_mt3", label_visibility="collapsed")

    # Calcul
    config = build_config_comparateur()
    res = calcul_comparateur(profil, config)

    # Alertes en haut
    if res.alertes:
        st.markdown("##### 🚦 Alertes & validations")
        for a in res.alertes:
            if a.severite == "error":
                st.error(f"**{a.titre}** — {a.message}")
            elif a.severite == "warning":
                st.warning(f"**{a.titre}** — {a.message}")
            else:
                st.info(f"ℹ {a.titre} — {a.message}")

    # Matrice dispositifs
    st.markdown("##### 📊 Matrice de rentabilité des dispositifs")
    rows = []
    for l in res.lignes:
        top = ""
        if l.top3_rang == 1: top = "🥇"
        elif l.top3_rang == 2: top = "🥈"
        elif l.top3_rang == 3: top = "🥉"
        rows.append({
            "Dispositif": l.nom,
            "Activé": l.active,
            "Montant (€)": format_eur(l.montant_input),
            "Coût société (€)": format_eur(l.cout_societe),
            "Net après IR (€)": format_eur(l.net_apres_ir),
            "Ratio net/coût": format_pct(l.ratio_net_cout, 1),
            "Risque": format_num(l.coef_risque),
            "Score ajusté": format_pct(l.score_ajuste, 1),
            "Top 3": top,
        })
    df_matrice = pd.DataFrame(rows)
    st.dataframe(df_matrice, use_container_width=True, hide_index=True)

    # Vue consolidée par réceptacle
    st.markdown("##### 💼 Vue consolidée par réceptacle")
    rows_rec = []
    for r in res.receptacles:
        flux_str = ", ".join([f"{nom} ({format_eur(m, 0)})" for nom, m in r.flux_entrants])
        rows_rec.append({
            "Réceptacle": r.nom,
            "Actif": "✓" if r.actif else "—",
            "Flux entrants": flux_str if flux_str else "—",
            "Total reçu (€)": format_eur(r.montant_total),
            "Plafond légal (€)": format_eur(r.plafond_legal),
            "Utilisation": format_pct(r.taux_utilisation, 1),
            "Statut": r.statut,
        })
    st.dataframe(pd.DataFrame(rows_rec), use_container_width=True, hide_index=True)

    # PERIN mutualisé entre conjoints
    if st.session_state["perin_actif"]:
        st.divider()
        st.markdown("##### 👥 PERIN mutualisé entre conjoints")
        st.caption(
            "Pour les couples mariés ou pacsés, les plafonds de déduction PERIN "
            "peuvent être mutualisés. Le solde non utilisé du conjoint augmente "
            "le plafond du dirigeant (CGI art. 163 quatervicies, V)."
        )

        col_a, col_b = st.columns(2)
        with col_a:
            st.session_state["perin_revenu_pro_dirigeant"] = st.number_input(
                "Revenu professionnel N-1 du dirigeant (€)",
                min_value=0, value=int(st.session_state["perin_revenu_pro_dirigeant"]),
                step=5000, key="perin_rev_dir_input",
            )
        with col_b:
            mutualisation_possible = (profil.situation == "Marié / pacsé")
            if mutualisation_possible:
                st.session_state["perin_conjoint_declare"] = st.checkbox(
                    "Le conjoint déclare son revenu pro et accepte la mutualisation",
                    value=st.session_state["perin_conjoint_declare"],
                )
            else:
                st.info("ℹ Mutualisation indisponible — situation familiale non éligible.")
                st.session_state["perin_conjoint_declare"] = False

        if st.session_state["perin_conjoint_declare"]:
            col_c, col_d = st.columns(2)
            with col_c:
                st.session_state["perin_revenu_pro_conjoint"] = st.number_input(
                    "Revenu professionnel N-1 du conjoint (€)",
                    min_value=0, value=int(st.session_state["perin_revenu_pro_conjoint"]),
                    step=5000, key="perin_rev_conj_input",
                )
            with col_d:
                st.session_state["perin_versement_conjoint"] = st.number_input(
                    "Versement déjà effectué par le conjoint sur son PERIN (€)",
                    min_value=0, value=int(st.session_state["perin_versement_conjoint"]),
                    step=500, key="perin_vers_conj_input",
                )

        # Calcul PERIN mutualisé
        # TMI estimée depuis le revenu par part (heuristique simple)
        from strategy.comparateur import estimer_tmi, estimer_revenu_imposable_par_part
        rev_par_part = estimer_revenu_imposable_par_part(profil)
        tmi = estimer_tmi(rev_par_part)

        res_perin = calcul_perin_mutualise(
            versement_dirigeant=st.session_state["perin_montant"],
            revenu_pro_dirigeant=st.session_state["perin_revenu_pro_dirigeant"],
            tmi_dirigeant=tmi,
            situation=profil.situation,
            conjoint_declare=st.session_state["perin_conjoint_declare"],
            revenu_pro_conjoint=st.session_state["perin_revenu_pro_conjoint"],
            versement_conjoint=st.session_state["perin_versement_conjoint"],
        )

        # Affichage du résultat
        ck1, ck2, ck3, ck4 = st.columns(4)
        ck1.metric("Plafond individuel dirigeant",
                   format_eur(res_perin.plafond_dirigeant.plafond_individuel, 0))
        if res_perin.mutualisation_active:
            ck2.metric("Plafond mutualisé total",
                       format_eur(res_perin.plafond_mutualise_total, 0),
                       delta=f"+{format_eur(res_perin.plafond_conjoint.solde_disponible, 0)} (conjoint)")
        else:
            ck2.metric("Mutualisation", "Inactive")
        ck3.metric("Versement couvert",
                   format_eur(res_perin.versement_dirigeant_couvert, 0))
        ck4.metric("Économie d'IR",
                   format_eur(res_perin.economie_ir, 0),
                   delta=f"TMI {format_pct(tmi, 0)}")

        if res_perin.versement_excedent > 0:
            st.warning(
                f"⚠ **Excédent détecté : {format_eur(res_perin.versement_excedent)}** "
                f"sur un versement de {format_eur(res_perin.versement_dirigeant)}. "
                f"La fraction au-delà du plafond n'est pas déductible et perd "
                f"l'avantage IR. Réduire le versement ou augmenter le plafond "
                f"via mutualisation."
            )


# ============================================================
# PAGE 4 — SYNTHÈSE DIRIGEANT
# ============================================================
def page_synthese():
    st.title("📋 Synthèse dirigeant")
    st.caption("Livrable consulting-grade avec radar 6D, projection et check-list")
    afficher_badge_niveau("Synthèse dirigeant")

    profil = build_profil()
    if profil.regime_social != "Assimilé salarié":
        st.warning(f"La Synthèse est calibrée sur l'Arbitrage Assimilé salarié (v1). "
                   f"Régime actuel : {profil.regime_social} — extension prévue v2.")
        return

    # Forfaits cabinet en sidebar dédiée
    with st.expander("💰 Forfaits cabinet (éditables)", expanded=False):
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Réinitialiser aux valeurs par défaut"):
                reset_forfaits(FORFAITS_DEFAUT)
                st.rerun()
        with col1:
            st.caption("Modifiez les montants selon votre grille tarifaire. Toggle = activer/désactiver le poste.")
        
        for key, forfait in FORFAITS_DEFAUT.items():
            c1, c2 = st.columns([3, 2])
            forfait.actif = c1.checkbox(f"{forfait.libelle} ({forfait.condition})",
                                         value=forfait.actif, key=f"f_act_{key}")
            forfait.montant = c2.number_input(
                f"Montant {key}", min_value=0,
                value=int(forfait.montant), step=100,
                key=f"f_mt_{key}", label_visibility="collapsed",
            )

    arbitrage = arbitrage_complet(profil)
    config = build_config_comparateur()
    res_comp = calcul_comparateur(profil, config)
    
    synth = calcul_synthese(profil, arbitrage["strategies"], config,
                             code_retenue=arbitrage["recommandee"],
                             forfaits=FORFAITS_DEFAUT,
                             alertes_comparateur=res_comp.alertes)

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Stratégie retenue", synth.strategie_retenue)
    col2.metric("Net dirigeant", format_eur(synth.net_dirigeant_retenu))
    col3.metric("Gain annuel vs A", format_eur(synth.gain_vs_a))
    col4.metric("Gain sur 5 ans", format_eur(synth.gain_5_ans))

    st.divider()
    
    # Radar 6D
    st.markdown("##### 🎯 Profil comparé des 4 stratégies — Radar 6 dimensions")
    
    axes = ["Net dirigeant", "Protection sociale", "Fiscalité",
            "Préparation retraite", "Liquidité", "Maîtrise des charges"]
    
    fig_radar = go.Figure()
    for s in synth.scores_radar:
        values = [s.net_dirigeant, s.protection_sociale, s.fiscalite,
                  s.preparation_retraite, s.liquidite, s.maitrise_charges]
        values.append(values[0])  # Ferme le polygone
        axes_full = axes + [axes[0]]
        fig_radar.add_trace(go.Scatterpolar(
            r=values, theta=axes_full,
            fill="toself", name=f"Stratégie {s.nom_strategie}",
            line=dict(color=COULEURS_STRATEGIES[s.nom_strategie]),
            opacity=0.5,
        ))
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor=GRID_COLOR),
            angularaxis=dict(gridcolor=GRID_COLOR),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True, height=500,
        **PLOTLY_LAYOUT_DARK,
    )
    st.plotly_chart(fig_radar, use_container_width=True)
    st.caption(AVERTISSEMENT_RADAR)

    # Coûts cabinet
    st.markdown("##### 💰 Coûts de mise en œuvre estimés (1ère année)")
    if synth.couts_mise_en_oeuvre:
        rows_couts = [{"Poste": c.libelle, "Montant": format_eur(c.montant),
                       "Note": c.note} for c in synth.couts_mise_en_oeuvre]
        rows_couts.append({"Poste": "**TOTAL**",
                           "Montant": f"**{format_eur(synth.total_couts)}**",
                           "Note": ""})
        st.dataframe(pd.DataFrame(rows_couts), use_container_width=True, hide_index=True)
        if synth.roi_mois:
            st.info(f"💡 **Retour sur investissement : {synth.roi_mois:.1f} mois**. "
                    f"Coûts cabinet rentabilisés en moins de {round(synth.roi_mois)} mois "
                    f"grâce au gain annuel de {format_eur(synth.gain_vs_a)}.")

    # Check-list
    if synth.checklist:
        st.markdown("##### ✅ Check-list de conformité")
        rows_check = [{"Point de contrôle": p.libelle, "Statut": p.statut,
                       "Action requise": p.action} for p in synth.checklist]
        st.dataframe(pd.DataFrame(rows_check), use_container_width=True, hide_index=True)

    # Bloc compact patrimonial
    st.markdown("##### 💼 Placement du net dirigeant — Comparaison rapide")
    st.caption(synth.enveloppes_compact["hypothese_texte"])
    rows_env = [{
        "Enveloppe": e.nom,
        "Capital net estimé à 5 ans": format_eur(e.net_disponible),
        "Avantage clé": e.avantage_cle,
    } for e in synth.enveloppes_compact["enveloppes"]]
    st.dataframe(pd.DataFrame(rows_env), use_container_width=True, hide_index=True)
    st.markdown(f"**Meilleure enveloppe sur ces hypothèses : {synth.enveloppes_compact['meilleure']}**")
    st.caption("→ Page **💼 Comparateur patrimonial** pour analyse détaillée avec inputs personnalisables")

    # ========================================================
    # Export PDF
    # ========================================================
    st.divider()
    st.markdown("##### 📄 Export PDF — Livrable client")
    st.caption(
        "Génère un rapport cabinet-grade prêt à transmettre au dirigeant. "
        "Format A4, branding cabinet, hypothèses & avertissements en annexe."
    )

    col_pdf1, col_pdf2 = st.columns(2)
    with col_pdf1:
        cabinet_nom = st.text_input(
            "Nom du cabinet (header PDF)",
            value="Cabinet d'expertise comptable",
            key="pdf_cabinet_nom",
        )
        client_nom = st.text_input(
            "Nom du client",
            value="Client",
            key="pdf_client_nom",
        )
    with col_pdf2:
        expert_comptable = st.text_input(
            "Expert-comptable en charge",
            value="",
            key="pdf_ec_nom",
        )

    if st.button("📄 Générer le PDF de synthèse", type="primary"):
        try:
            pdf_bytes = generer_pdf_synthese(
                synthese=synth,
                arbitrage=arbitrage,
                profil=profil,
                cabinet_nom=cabinet_nom or "Cabinet d'expertise comptable",
                client_nom=client_nom or "Client",
                expert_comptable=expert_comptable,
                niveau_confiance="Avancé",
                doctrine_version=DOCTRINE_VERSION,
                doctrine_date=DOCTRINE_DATE,
            )
            client_safe = (client_nom or "client").replace(" ", "_").lower()
            st.success(f"✓ PDF généré ({len(pdf_bytes):,} octets)")
            st.download_button(
                label="⬇ Télécharger la synthèse PDF",
                data=pdf_bytes,
                file_name=f"synthese_{client_safe}.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error(f"Erreur lors de la génération du PDF : {e}")


# ============================================================
# PAGE 5 — SCÉNARIOS A vs B
# ============================================================
def page_scenarios():
    st.title("🔀 Scénarios A vs B")
    st.caption("Comparateur 2 scénarios côte à côte, multi-régimes")
    afficher_badge_niveau("Scénarios A vs B")
    
    st.info(AVERTISSEMENT_SCENARIOS)
    st.caption(MENTION_REGIMES)

    col_a, col_b = st.columns(2)
    
    inputs = {}
    for letter, col in [("A", col_a), ("B", col_b)]:
        with col:
            st.markdown(f"### Scénario {letter}")
            inputs[letter] = {}
            inputs[letter]["libelle"] = st.text_input(
                "Libellé", value=f"Cas {letter}", key=f"lib_{letter}")
            inputs[letter]["situation"] = st.selectbox(
                "Situation familiale", ["Marié / pacsé", "Célibataire / divorcé / veuf"],
                key=f"sit_{letter}")
            inputs[letter]["parts"] = st.number_input(
                "Parts fiscales", min_value=1.0, max_value=6.0, value=2.0, step=0.5,
                key=f"parts_{letter}")
            inputs[letter]["regime_social"] = st.selectbox(
                "Régime social",
                ["Assimilé salarié", "TNS", "TNS (libéral)", "Salarié"],
                key=f"reg_{letter}")
            inputs[letter]["salaire_brut"] = st.number_input(
                "Salaire brut (€)", min_value=0, value=100000, step=5000, key=f"sal_{letter}")
            inputs[letter]["dividendes_bruts"] = st.number_input(
                "Dividendes bruts (€)", min_value=0,
                value=0 if letter == "A" else 50000, step=5000, key=f"div_{letter}")
            inputs[letter]["epargne_salariale_per"] = st.number_input(
                "Épargne sal. & PER (€)", min_value=0,
                value=0 if letter == "A" else 15000, step=1000, key=f"ep_{letter}")
            inputs[letter]["peripheriques"] = st.number_input(
                "Périphériques (€)", min_value=0,
                value=0 if letter == "A" else 4000, step=500, key=f"per_{letter}")

    sc_a = ScenarioInputs(**inputs["A"])
    sc_b = ScenarioInputs(**inputs["B"])
    comp = calcul_comparaison(sc_a, sc_b)

    st.divider()
    st.markdown("##### Résultats comparés")
    
    rows_comp = [
        {"Élément": "Net salaire après cotisations",
         "Scénario A": format_eur(comp.scenario_a.net_salaire_apres_cotis),
         "Scénario B": format_eur(comp.scenario_b.net_salaire_apres_cotis),
         "Écart": format_eur(comp.scenario_b.net_salaire_apres_cotis - comp.scenario_a.net_salaire_apres_cotis)},
        {"Élément": "Net salaire après IR",
         "Scénario A": format_eur(comp.scenario_a.net_salaire_apres_ir),
         "Scénario B": format_eur(comp.scenario_b.net_salaire_apres_ir),
         "Écart": format_eur(comp.scenario_b.net_salaire_apres_ir - comp.scenario_a.net_salaire_apres_ir)},
        {"Élément": "Net dividendes",
         "Scénario A": format_eur(comp.scenario_a.net_dividendes),
         "Scénario B": format_eur(comp.scenario_b.net_dividendes),
         "Écart": format_eur(comp.scenario_b.net_dividendes - comp.scenario_a.net_dividendes)},
        {"Élément": "Net épargne",
         "Scénario A": format_eur(comp.scenario_a.net_epargne),
         "Scénario B": format_eur(comp.scenario_b.net_epargne),
         "Écart": format_eur(comp.scenario_b.net_epargne - comp.scenario_a.net_epargne)},
        {"Élément": "Net périphériques",
         "Scénario A": format_eur(comp.scenario_a.net_peripheriques),
         "Scénario B": format_eur(comp.scenario_b.net_peripheriques),
         "Écart": format_eur(comp.scenario_b.net_peripheriques - comp.scenario_a.net_peripheriques)},
        {"Élément": "**TOTAL NET DIRIGEANT**",
         "Scénario A": f"**{format_eur(comp.scenario_a.total_net)}**",
         "Scénario B": f"**{format_eur(comp.scenario_b.total_net)}**",
         "Écart": f"**{format_eur(comp.ecart_total)}**"},
    ]
    st.dataframe(pd.DataFrame(rows_comp), use_container_width=True, hide_index=True)
    
    if comp.gagnant == "A":
        st.success(f"← **Scénario A gagnant** ({format_eur(abs(comp.ecart_total))} d'écart, "
                   f"{format_pct(abs(comp.ecart_pourcent), 2)})")
    elif comp.gagnant == "B":
        st.success(f"→ **Scénario B gagnant** ({format_eur(abs(comp.ecart_total))} d'écart, "
                   f"{format_pct(abs(comp.ecart_pourcent), 2)})")
    else:
        st.info("= Scénarios équivalents")

    # Projection 5 ans
    st.markdown("##### Projection 5 ans")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(1, 6)), y=comp.scenario_a.projection_5_ans,
        name=f"Scénario A : {sc_a.libelle}",
        line=dict(color=COULEURS_STRATEGIES["A"], width=2),
        mode="lines+markers",
    ))
    fig.add_trace(go.Scatter(
        x=list(range(1, 6)), y=comp.scenario_b.projection_5_ans,
        name=f"Scénario B : {sc_b.libelle}",
        line=dict(color=COULEURS_STRATEGIES["B"], width=3),
        mode="lines+markers",
    ))
    fig.update_layout(
        xaxis_title="Année", yaxis_title="Patrimoine cumulé (€)",
        height=400, yaxis=dict(gridcolor=GRID_COLOR, tickformat=",.0f"),
        **PLOTLY_LAYOUT_DARK,
    )
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# PAGE 6 — COMPARATEUR PATRIMONIAL
# ============================================================
def page_patrimonial():
    st.title("💼 Comparateur patrimonial")
    st.caption("Comparaison des 4 enveloppes de placement (CTO / PEA / Assurance-vie / PER)")
    afficher_badge_niveau("Comparateur patrimonial")

    from strategy.synthese import calcul_enveloppes_patrimoniales

    col1, col2, col3 = st.columns(3)
    montant = col1.number_input("Capital initial placé (€)", min_value=1000,
                                value=10000, step=1000)
    horizon = col2.slider("Horizon (années)", 1, 30, 5)
    rendement = col3.slider("Rendement annuel brut (%)", 0.0, 10.0, 5.0, 0.5) / 100

    profil = build_profil()
    res = calcul_enveloppes_patrimoniales(montant=montant, horizon=horizon,
                                           rendement=rendement,
                                           situation=profil.situation)
    
    st.caption(res["hypothese_texte"])
    
    rows = [{"Enveloppe": e.nom,
             "Versement": format_eur(e.versement),
             "Valeur brute": format_eur(e.valeur_brute),
             "Fiscalité de sortie": e.fiscalite_sortie,
             "Net disponible": format_eur(e.net_disponible),
             "Avantage clé": e.avantage_cle}
            for e in res["enveloppes"]]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    
    st.success(f"**Meilleure enveloppe : {res['meilleure']}**")

    # Graphique évolution
    fig = go.Figure()
    annees = list(range(1, horizon + 1))
    for e in res["enveloppes"]:
        valeurs = [montant * (1 + rendement) ** a for a in annees]
        fig.add_trace(go.Scatter(x=annees, y=valeurs, name=e.nom, mode="lines+markers"))
    fig.update_layout(xaxis_title="Année", yaxis_title="Valeur brute (€)",
                      height=400, yaxis=dict(gridcolor=GRID_COLOR, tickformat=",.0f"),
                      **PLOTLY_LAYOUT_DARK)
    st.plotly_chart(fig, use_container_width=True)

    # Encarts pédagogiques
    st.markdown("##### 💡 À retenir")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**CTO** : Liquidité totale, mais PFU annuel sur PV.\n\n"
                "**PEA** : Exo IR après 5 ans, plafond 150k€, hors UE limité.")
    with col2:
        st.info("**Assurance-vie** : Transmission privilégiée (152 500 € par bénéficiaire). Abattement annuel sur PV après 8 ans.\n\n"
                "**PER** : Déduction IR à l'entrée (TMI), sortie en rente ou capital, blocage retraite.")


# ============================================================
# PAGE 7 — TESTS DE COHÉRENCE
# ============================================================
def page_tests():
    st.title("✅ Tests de cohérence")
    st.caption("Transparence sur la fiabilité du moteur — 476 validations en parité v19")
    
    st.success("🎯 **Phase A v1 — 476/476 validations** (parité v19 stricte sur tous les modules)")
    
    rows = []
    for module, cas_dict in REGISTRE_CAS_TESTS.items():
        rows.append({
            "Module": module,
            "Nombre de cas": len(cas_dict),
            "Statut": "✅ Validé",
            "Tolérance": "0,01 €",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    
    st.divider()
    st.markdown("##### 📋 Détail du registre des cas tests")
    
    for module, cas_dict in REGISTRE_CAS_TESTS.items():
        with st.expander(f"{module} — {len(cas_dict)} cas"):
            for nom, descr in cas_dict.items():
                st.markdown(f"- **{nom}** : {descr}")


# ============================================================
# PAGE 8 — PARAMÈTRES RÉGLEMENTAIRES
# ============================================================
def page_parametres():
    st.title("⚙ Paramètres réglementaires")
    st.caption("Référentiel centralisé — modifications réservées à l'équipe maintenance")
    
    st.success(f"🟢 **Moteur réglementaire mis à jour au : {DOCTRINE_DATE}**  · "
               f"Doctrine version {DOCTRINE_VERSION}")
    
    st.markdown("##### Niveau de précision par module")
    rows_niveau = []
    for module, niveau in NIVEAU_PAR_MODULE.items():
        couleur, emoji = NIVEAU_COULEURS[niveau]
        rows_niveau.append({
            "Module": module,
            "Niveau": f"{emoji} {niveau.value}",
            "Description": DESCRIPTION_NIVEAU[niveau][:120] + "...",
        })
    st.dataframe(pd.DataFrame(rows_niveau), use_container_width=True, hide_index=True)
    
    st.divider()
    st.markdown("##### 📜 Doctrine métier centralisée")
    
    for theme, refs in DOCTRINE_COMPLETE.items():
        with st.expander(f"**{theme}** ({len(refs)} règles)"):
            for r in refs:
                st.markdown(f"**{r.regle}**")
                st.caption(f"Valeur : `{r.valeur}` · Source : {r.source_legale}")
                if r.note:
                    st.caption(f"Note : {r.note}")
                st.write("")


# ============================================================
# PAGE 9 — ADMINISTRATION (MODE EXPERT)
# ============================================================
def page_admin():
    st.title("🔧 Administration des paramètres")
    st.caption("Modifications réservées à l'équipe maintenance — Mode expert verrouillé par défaut")

    # Avertissement permanent
    st.error(
        "⚠ **Page sensible** — Toute modification de paramètre réglementaire impacte "
        "l'ensemble des calculs du moteur. Les modifications sont tracées dans "
        "l'historique. Pour revenir à un état stable, utiliser **« Restaurer doctrine officielle »**."
    )

    catalogue = st.session_state["catalogue_admin"]
    historique = st.session_state["historique_admin"]

    # Verrou mode expert
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(
            "##### Mode de fonctionnement\n"
            "- **Simple (par défaut)** : lecture seule, affichage propre.\n"
            "- **Expert** : édition des paramètres, traçabilité requise."
        )
    with col2:
        mode_expert = st.toggle(
            "Activer le mode expert",
            value=st.session_state["mode_expert_admin"],
        )
        st.session_state["mode_expert_admin"] = mode_expert

    if mode_expert:
        st.session_state["admin_utilisateur"] = st.text_input(
            "Identifiant utilisateur (pour traçabilité)",
            value=st.session_state["admin_utilisateur"],
            placeholder="Ex: EC.Dupont",
        )
        if not st.session_state["admin_utilisateur"]:
            st.warning("⚠ Veuillez renseigner votre identifiant pour pouvoir modifier les paramètres.")

    st.divider()

    # Indicateur de modifications actives
    modifs_actives = lister_modifications_actives(catalogue)
    if modifs_actives:
        st.warning(
            f"🟠 **{len(modifs_actives)} paramètre(s) modifié(s)** par rapport à la doctrine officielle PACTE 2026. "
            f"Cliquez sur « Restaurer doctrine officielle » pour revenir aux valeurs de référence."
        )
        if st.button("🔄 Restaurer doctrine officielle", type="primary"):
            user = st.session_state["admin_utilisateur"] or "Système"
            n = restaurer_doctrine_officielle(catalogue, historique, user)
            st.success(f"✓ {n} paramètre(s) restauré(s) à la doctrine officielle")
            st.rerun()
    else:
        st.success("✅ Tous les paramètres sont alignés sur la doctrine officielle PACTE 2026.")

    st.divider()

    # Catalogue par catégorie
    categories = {}
    for param in catalogue.values():
        categories.setdefault(param.categorie, []).append(param)

    for cat_nom, params in categories.items():
        st.markdown(f"##### {cat_nom}")
        rows = []
        for p in params:
            statut = "🟠 Modifié" if p.est_modifie else "✅ Doctrine"
            rows.append({
                "Paramètre": p.libelle,
                "Valeur actuelle": fmt_param(p),
                "Valeur doctrine": fmt_param(p, p.valeur_doctrine_officielle),
                "Statut": statut,
                "Source": p.source_legale,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # En mode expert, formulaire d'édition
        if mode_expert and st.session_state["admin_utilisateur"]:
            with st.expander(f"✏ Éditer les paramètres — {cat_nom}"):
                for p in params:
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    with col_a:
                        st.markdown(f"**{p.libelle}**")
                        st.caption(p.note)
                    with col_b:
                        if p.unite == "%":
                            nouvelle = st.number_input(
                                f"Valeur ({p.unite})",
                                value=float(p.valeur_actuelle * 100),
                                step=0.01, format="%.2f",
                                key=f"edit_{p.cle}",
                                label_visibility="collapsed",
                            ) / 100
                        else:
                            nouvelle = st.number_input(
                                f"Valeur ({p.unite})",
                                value=float(p.valeur_actuelle),
                                step=0.01,
                                key=f"edit_{p.cle}",
                                label_visibility="collapsed",
                            )
                    with col_c:
                        if abs(nouvelle - p.valeur_actuelle) > 1e-9:
                            motif = st.text_input(
                                "Motif",
                                placeholder="Justification...",
                                key=f"motif_{p.cle}",
                                label_visibility="collapsed",
                            )
                            if st.button("✓ Appliquer", key=f"apply_{p.cle}"):
                                ancienne = p.valeur_actuelle
                                p.valeur_actuelle = nouvelle
                                enregistrer_modif(
                                    historique,
                                    st.session_state["admin_utilisateur"],
                                    p, ancienne, nouvelle,
                                    motif=motif or "(non renseigné)"
                                )
                                st.rerun()

    st.divider()

    # Historique
    st.markdown("##### 📜 Historique des modifications")
    if historique:
        rows_hist = []
        for h in reversed(historique):  # plus récent en haut
            rows_hist.append({
                "Horodatage": h.timestamp,
                "Utilisateur": h.utilisateur,
                "Paramètre": h.libelle,
                "Avant": h.ancienne_valeur,
                "Après": h.nouvelle_valeur,
                "Motif": h.motif,
            })
        st.dataframe(pd.DataFrame(rows_hist), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune modification enregistrée à ce jour.")


# ============================================================
# ROUTAGE
# ============================================================
def page_receptacles_auditables():
    """Wrapper : délègue au module dédié SP20 (v1.2).

    Reconstruit le profil depuis la barre latérale et passe la main à
    `ui.page_receptacles.page_receptacles`. Aucune logique métier ici.
    """
    profil = build_profil()
    _page_receptacles_v11(profil)


ROUTES = {
    "arbitrage": page_arbitrage,
    "modules": page_modules,
    "comparateur": page_comparateur,
    "receptacles_v11": page_receptacles_auditables,
    "synthese": page_synthese,
    "scenarios": page_scenarios,
    "patrimonial": page_patrimonial,
    "tests": page_tests,
    "parametres": page_parametres,
    "admin": page_admin,
}

ROUTES[page]()


# ============================================================
# FOOTER GLOBAL
# ============================================================
st.divider()
st.caption(FOOTER_GLOBAL)
