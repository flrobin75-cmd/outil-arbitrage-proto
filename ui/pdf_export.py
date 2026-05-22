"""
Export PDF du livrable Synthèse dirigeant.

Génère un rapport cabinet-grade :
- Page de garde avec branding cabinet
- Synthèse exécutive (1 page)
- Détail des 4 stratégies + radar
- Coûts cabinet + ROI
- Check-list conformité
- Comparateur patrimonial
- Annexe : hypothèses & avertissements (mention version doctrine)

Décisions design :
- Format A4, marges 18 mm
- Police principale : Helvetica
- Couleurs cohérentes avec l'UI (palette discrète professionnelle)
- Tous les montants en format français 2 décimales
- Mention version doctrine et niveau confiance en footer chaque page
"""

import io
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, PageBreak,
    KeepTogether, FrameBreak,
)
from reportlab.pdfgen.canvas import Canvas


# ============================================================
# CHARTE GRAPHIQUE
# ============================================================
COULEUR_PRIMAIRE = HexColor("#1E40AF")        # bleu profond
COULEUR_SECONDAIRE = HexColor("#3B82F6")       # bleu standard
COULEUR_ACCENT = HexColor("#10B981")           # vert validation
COULEUR_TEXTE = HexColor("#1F2937")            # gris foncé
COULEUR_GRIS = HexColor("#6B7280")             # gris moyen
COULEUR_FOND_TABLEAU = HexColor("#F3F4F6")     # gris très clair
COULEUR_LIGNE = HexColor("#E5E7EB")            # gris ligne

NIVEAU_COULEURS_PDF = {
    "Conformité renforcée": HexColor("#10B981"),
    "Avancé": HexColor("#3B82F6"),
    "Cadrage": HexColor("#F59E0B"),
    "Indicatif": HexColor("#8B5CF6"),
}


# ============================================================
# ALIAS HISTORIQUES — Migration v1.0.1
# ============================================================
# Mapping interne pour normaliser d'éventuels niveaux legacy lus depuis :
# - anciens enregistrements de mission stockés en base
# - JSONs de session Streamlit antérieurs au renommage
# - tests historiques
#
# RÈGLE STRICTE : aucun de ces alias ne doit ressortir dans :
# - le texte d'un PDF
# - un log visible
# - une UI utilisateur
# - un export client
#
# Toute lecture d'un niveau passe par _normaliser_niveau() qui résout
# l'alias en silence, sans jamais conserver la forme historique.
_ALIASES_NIVEAUX = {
    "Déclaratif": "Conformité renforcée",
}


def _normaliser_niveau(niveau: str) -> str:
    """
    Normalise un niveau de confiance en résolvant les alias historiques.

    Garde-fou central pour la migration v1.0.1 : tout niveau passé au PDF
    transite par cette fonction, ce qui garantit qu'aucun terme legacy
    n'arrive jusqu'au rendu final, même si appelé depuis un ancien code
    ou un enregistrement persistant.

    Args:
        niveau: Niveau de confiance, éventuellement legacy ("Déclaratif")

    Returns:
        Niveau normalisé selon la doctrine v1.0.1.
    """
    return _ALIASES_NIVEAUX.get(niveau, niveau)


# ============================================================
# FORMATAGE FRANÇAIS
# ============================================================
def fmt_eur(v, decimales=2):
    if v is None: return "—"
    formatted = f"{v:,.{decimales}f}".replace(",", " ").replace(".", ",")
    return f"{formatted} €"


def fmt_pct(v, decimales=2):
    if v is None: return "—"
    return f"{v*100:.{decimales}f}".replace(".", ",") + " %"


# ============================================================
# STYLES PARAGRAPH
# ============================================================
def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "title", parent=base["Title"],
            fontSize=22, leading=26, textColor=COULEUR_PRIMAIRE,
            fontName="Helvetica-Bold", spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"],
            fontSize=12, leading=14, textColor=COULEUR_GRIS,
            fontName="Helvetica", spaceAfter=20,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"],
            fontSize=16, leading=20, textColor=COULEUR_PRIMAIRE,
            fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"],
            fontSize=13, leading=16, textColor=COULEUR_TEXTE,
            fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=10, leading=14, textColor=COULEUR_TEXTE,
            fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"],
            fontSize=8, leading=11, textColor=COULEUR_GRIS,
            fontName="Helvetica", alignment=TA_LEFT,
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label", parent=base["Normal"],
            fontSize=9, leading=11, textColor=COULEUR_GRIS,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
        "kpi_value": ParagraphStyle(
            "kpi_value", parent=base["Normal"],
            fontSize=18, leading=22, textColor=COULEUR_PRIMAIRE,
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "callout": ParagraphStyle(
            "callout", parent=base["Normal"],
            fontSize=10, leading=14, textColor=COULEUR_TEXTE,
            fontName="Helvetica-Oblique", alignment=TA_LEFT,
            leftIndent=10, rightIndent=10, spaceBefore=6, spaceAfter=6,
        ),
        "footer_small": ParagraphStyle(
            "footer_small", parent=base["Normal"],
            fontSize=7, leading=9, textColor=COULEUR_GRIS,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
    }
    return styles


# ============================================================
# DOCUMENT TEMPLATE — Header + Footer sur toutes les pages
# ============================================================
class SyntheseDocTemplate(BaseDocTemplate):
    """Template avec header/footer automatiques."""

    def __init__(self, filename, cabinet_nom, client_nom,
                 niveau_confiance, doctrine_version, doctrine_date, **kwargs):
        self.cabinet_nom = cabinet_nom
        self.client_nom = client_nom
        # Normalisation des niveaux legacy ("Déclaratif" → "Conformité renforcée")
        # Garantit qu'aucun terme historique ne ressort dans le PDF généré.
        self.niveau_confiance = _normaliser_niveau(niveau_confiance)
        self.doctrine_version = doctrine_version
        self.doctrine_date = doctrine_date
        BaseDocTemplate.__init__(self, filename, pagesize=A4,
                                  leftMargin=18*mm, rightMargin=18*mm,
                                  topMargin=22*mm, bottomMargin=20*mm, **kwargs)
        frame = Frame(self.leftMargin, self.bottomMargin,
                      self.width, self.height, id="normal")
        template = PageTemplate(id="main", frames=[frame],
                                onPage=self._draw_decorations)
        self.addPageTemplates([template])

    def _draw_decorations(self, canvas: Canvas, doc):
        """Header + footer sur chaque page."""
        canvas.saveState()

        # === HEADER ===
        # Trait coloré en haut
        canvas.setFillColor(COULEUR_PRIMAIRE)
        canvas.rect(0, A4[1] - 8*mm, A4[0], 8*mm, fill=1, stroke=0)
        # Cabinet à gauche, page à droite
        canvas.setFillColor(COULEUR_TEXTE)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(18*mm, A4[1] - 14*mm, self.cabinet_nom)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(COULEUR_GRIS)
        canvas.drawRightString(A4[0] - 18*mm, A4[1] - 14*mm,
                               f"Synthèse — {self.client_nom}")

        # === FOOTER ===
        # Trait fin séparateur
        canvas.setStrokeColor(COULEUR_LIGNE)
        canvas.setLineWidth(0.5)
        canvas.line(18*mm, 18*mm, A4[0] - 18*mm, 18*mm)
        # Bandeau d'info en footer (compactés pour éviter collision)
        canvas.setFillColor(COULEUR_GRIS)
        canvas.setFont("Helvetica", 7)
        date_str = datetime.now().strftime("%d/%m/%Y")
        # Ligne 1 du footer : trace doctrinale enrichie B.2.5 + niveau + page
        # « Doctrine v{x} — France 2026 » (option A : footer enrichi, pas de
        # bloc lourd en couverture)
        from ui.disclaimers import TRACE_DOCTRINALE_FOOTER
        canvas.drawString(18*mm, 14*mm, TRACE_DOCTRINALE_FOOTER)
        canvas.drawCentredString(A4[0]/2, 14*mm,
                                  f"Niveau : {self.niveau_confiance}")
        canvas.drawRightString(A4[0] - 18*mm, 14*mm,
                                f"Page {canvas.getPageNumber()} — {date_str}")
        # Mention obligatoire (ligne 2)
        canvas.setFont("Helvetica-Oblique", 6)
        canvas.drawCentredString(A4[0]/2, 10*mm,
                                  "Outil indicatif à usage professionnel — Ne se substitue pas "
                                  "à un conseil personnalisé.")

        canvas.restoreState()


# ============================================================
# COMPOSANTS DE CONSTRUCTION DU FLOW
# ============================================================
def _kpi_table(kpis: list, styles) -> Table:
    """Tableau de 4 KPIs en ligne avec valeur grosse + label dessous."""
    cells = []
    labels = []
    for label, value in kpis:
        cells.append(Paragraph(f"<b>{value}</b>", styles["kpi_value"]))
        labels.append(Paragraph(label, styles["kpi_label"]))

    col_widths = [(A4[0] - 36*mm) / len(kpis)] * len(kpis)
    t = Table([cells, labels], colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COULEUR_FOND_TABLEAU),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
        ("BOX", (0, 0), (-1, -1), 0.5, COULEUR_LIGNE),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, COULEUR_LIGNE),
    ]))
    return t


def _data_table(rows: list, styles, headers: Optional[list] = None,
                col_widths: Optional[list] = None, highlight_last_row: bool = False) -> Table:
    """Tableau de données standard avec mise en forme cabinet."""
    if headers:
        data = [headers] + rows
    else:
        data = rows

    nb_cols = len(data[0])
    if col_widths is None:
        usable_width = A4[0] - 36*mm
        col_widths = [usable_width / nb_cols] * nb_cols

    t = Table(data, colWidths=col_widths)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), COULEUR_TEXTE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, COULEUR_LIGNE),
    ]
    if headers:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), COULEUR_PRIMAIRE),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("LINEBELOW", (0, 0), (-1, 0), 0, white),
        ])
    if highlight_last_row:
        style.extend([
            ("BACKGROUND", (0, -1), (-1, -1), COULEUR_FOND_TABLEAU),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEABOVE", (0, -1), (-1, -1), 1, COULEUR_PRIMAIRE),
        ])
    t.setStyle(TableStyle(style))
    return t


def _badge_niveau(niveau: str, styles) -> Table:
    """Badge coloré pour le niveau de confiance."""
    # Normalisation systématique des niveaux legacy avant affichage
    niveau = _normaliser_niveau(niveau)
    couleur = NIVEAU_COULEURS_PDF.get(niveau, COULEUR_GRIS)
    t = Table([[Paragraph(f"<font color='white'><b>NIVEAU : {niveau.upper()}</b></font>",
                          styles["small"])]],
              colWidths=[60*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), couleur),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ============================================================
# GÉNÉRATION DU PDF
# ============================================================
def _build_pdf_assimile(
    synthese,
    arbitrage,
    profil,
    cabinet_nom: str = "Cabinet d'expertise comptable",
    client_nom: str = "Client",
    expert_comptable: str = "",
    niveau_confiance: str = "Avancé",
    doctrine_version: str = "1.0.0",
    doctrine_date: str = "01/01/2026",
) -> bytes:
    """
    Génère le PDF Assimilé salarié — implémentation historique Phase A.

    Sections :
    - Couverture : "Arbitrage de rémunération — Dirigeant assimilé salarié"
    - Section principale : "Stratégies d'allocation A/B/C/D"
    - Page Coûts cabinet + ROI + check-list conformité
    - Page Comparateur patrimonial
    - Annexe : hypothèses & avertissements

    Cette fonction conserve la logique v19 stricte du PDF Phase A.
    Aucune modification du comportement vs version précédente.
    """
    # Normalisation niveau (résolution alias historiques, garde-fou v1.0.1)
    niveau_confiance = _normaliser_niveau(niveau_confiance)

    buffer = io.BytesIO()
    doc = SyntheseDocTemplate(buffer,
                               cabinet_nom=cabinet_nom, client_nom=client_nom,
                               niveau_confiance=niveau_confiance,
                               doctrine_version=doctrine_version,
                               doctrine_date=doctrine_date)
    styles = _build_styles()
    flow = []

    # ============================================================
    # PAGE 1 — Couverture + Synthèse exécutive
    # ============================================================
    flow.append(Paragraph(
        "Arbitrage de rémunération — Dirigeant assimilé salarié",
        styles["title"]))
    flow.append(Paragraph(
        f"Cadrage indicatif — outil d'aide à la décision — {profil.regime_social}",
        styles["subtitle"]))

    flow.append(_badge_niveau(niveau_confiance, styles))
    flow.append(Spacer(1, 8*mm))

    # Bloc identité dossier
    flow.append(Paragraph("Dossier client", styles["h2"]))
    dossier_rows = [
        ["Client", client_nom],
        ["Forme juridique", profil.forme_juridique],
        ["Régime social", profil.regime_social],
        ["Effectif", profil.effectif],
        ["Foyer fiscal", f"{profil.situation} — {profil.parts:g} parts"],
        ["Enveloppe arbitrée", fmt_eur(profil.enveloppe, 0)],
        ["Date de simulation", datetime.now().strftime("%d/%m/%Y")],
    ]
    if expert_comptable:
        dossier_rows.append(["Expert-comptable en charge", expert_comptable])
    flow.append(_data_table(dossier_rows, styles, col_widths=[60*mm, 114*mm]))

    flow.append(Spacer(1, 8*mm))

    # KPIs de synthèse
    flow.append(Paragraph("Résultats clés", styles["h2"]))
    kpis = [
        (f"Stratégie retenue", synthese.strategie_retenue),
        ("Net dirigeant annuel", fmt_eur(synthese.net_dirigeant_retenu, 0)),
        ("Gain vs stratégie A", fmt_eur(synthese.gain_vs_a, 0)),
        ("Gain cumulé sur 5 ans", fmt_eur(synthese.gain_5_ans, 0)),
    ]
    flow.append(_kpi_table(kpis, styles))

    flow.append(Spacer(1, 8*mm))

    # Lecture textuelle (cadrage indicatif, pas de recommandation opposable)
    flow.append(Paragraph("Lecture de la stratégie retenue", styles["h2"]))
    strat_reco = arbitrage["strategies"][synthese.strategie_retenue]
    recommandation = (
        f"Sur la base d'une enveloppe employeur globale de "
        f"<b>{fmt_eur(profil.enveloppe, 0)}</b>, la stratégie <b>{synthese.strategie_retenue} — "
        f"{strat_reco['nom']}</b> dégage un net dirigeant après fiscalité de "
        f"<b>{fmt_eur(synthese.net_dirigeant_retenu)}</b>, soit "
        f"<b>{fmt_eur(synthese.gain_vs_a)} d'écart annuel</b> "
        f"vs la rémunération directe pure (stratégie A). "
        f"L'efficacité fiscale (net / coût) s'établit à "
        f"<b>{fmt_pct(strat_reco['efficacite'], 1)}</b>. "
        f"Ce cadrage indicatif est destiné à appuyer l'analyse en cabinet ; "
        f"il ne constitue pas une recommandation juridique ou patrimoniale."
    )
    flow.append(Paragraph(recommandation, styles["body"]))

    if synthese.roi_mois:
        flow.append(Paragraph(
            f"<b>Projection indicative de retour sur coût de mission :</b> "
            f"{synthese.roi_mois:.1f} mois, sur la base d'un total de coûts "
            f"cabinet estimé à {fmt_eur(synthese.total_couts, 0)}. "
            f"Cette projection repose sur les hypothèses de la simulation ; "
            f"elle ne constitue pas un engagement commercial.",
            styles["callout"]))

    flow.append(PageBreak())

    # ============================================================
    # PAGE 2 — Stratégies d'allocation A/B/C/D
    # ============================================================
    flow.append(Paragraph("Stratégies d'allocation A/B/C/D", styles["h1"]))

    flow.append(Paragraph(
        "Quatre allocations de l'enveloppe employeur sont modélisées à coût "
        "société constant. Le passage de la stratégie A à la stratégie D dégage "
        "le gain maximal mais mobilise davantage de dispositifs (épargne salariale, "
        "PER, périphériques exonérés).",
        styles["body"]))

    rows = []
    for code in ["A", "B", "C", "D"]:
        s = arbitrage["strategies"][code]
        rows.append([
            f"{code} — {s['nom']}",
            fmt_eur(s["total_net"]),
            fmt_pct(s["efficacite"], 1),
            fmt_eur(s["gain_vs_a"]) if code != "A" else "—",
        ])
    flow.append(Spacer(1, 4*mm))
    flow.append(_data_table(
        rows, styles,
        headers=["Stratégie", "Net dirigeant", "Efficacité", "Gain vs A"],
        col_widths=[78*mm, 35*mm, 25*mm, 36*mm],
    ))

    flow.append(Spacer(1, 6*mm))

    # Décomposition stratégie retenue
    flow.append(Paragraph(
        f"Décomposition de la stratégie {synthese.strategie_retenue}",
        styles["h2"]))

    decomp = []
    if strat_reco["net_salaire"] > 0:
        decomp.append(["Net salaire après IR",
                       fmt_eur(strat_reco["net_salaire"])])
    if strat_reco["net_dividendes"] > 0:
        decomp.append(["Net dividendes (après IS + PFU)",
                       fmt_eur(strat_reco["net_dividendes"])])
    if strat_reco["net_epargne"] > 0:
        decomp.append(["Net épargne salariale & PER",
                       fmt_eur(strat_reco["net_epargne"])])
    if strat_reco["net_peripheriques"] > 0:
        decomp.append(["Net périphériques (TR, CESU, AN…)",
                       fmt_eur(strat_reco["net_peripheriques"])])
    decomp.append(["TOTAL NET DIRIGEANT",
                   fmt_eur(strat_reco["total_net"])])
    flow.append(_data_table(decomp, styles, col_widths=[114*mm, 60*mm],
                             highlight_last_row=True))

    flow.append(PageBreak())

    # ============================================================
    # PAGE 3 — Coûts cabinet + ROI + Check-list
    # ============================================================
    flow.append(Paragraph("Coûts de mise en œuvre", styles["h1"]))
    flow.append(Paragraph(
        "Estimation des coûts cabinet pour la première année. Forfaits "
        "indicatifs adaptables selon la grille tarifaire en vigueur.",
        styles["body"]))

    cout_rows = [[c.libelle, fmt_eur(c.montant)]
                  for c in synthese.couts_mise_en_oeuvre]
    cout_rows.append(["TOTAL coûts cabinet", fmt_eur(synthese.total_couts)])
    flow.append(_data_table(cout_rows, styles,
                             headers=["Poste", "Montant"],
                             col_widths=[124*mm, 50*mm],
                             highlight_last_row=True))

    if synthese.roi_mois:
        flow.append(Spacer(1, 4*mm))
        flow.append(Paragraph(
            f"<b>Estimation indicative du délai de couverture des coûts "
            f"de mission :</b> {synthese.roi_mois:.1f} mois. "
            f"Calcul indicatif rapportant les coûts de mission estimés "
            f"({fmt_eur(synthese.total_couts, 0)}) à l'écart annuel de "
            f"net dirigeant projeté ({fmt_eur(synthese.gain_vs_a)}). "
            f"Cette projection dépend des hypothèses retenues et ne "
            f"préjuge pas du résultat effectif de la mission.",
            styles["callout"]))

    flow.append(Spacer(1, 8*mm))

    # Check-list de conformité
    if synthese.checklist:
        flow.append(Paragraph("Check-list de conformité", styles["h1"]))
        flow.append(Paragraph(
            "Points de contrôle réglementaires liés à la stratégie retenue. "
            "Les actions à entreprendre sont indiquées pour les points en "
            "<b>vigilance</b> ou en <b>non-conformité</b>.",
            styles["body"]))

        # Conversion emoji → libellé texte (Helvetica ne supporte pas les emoji)
        def _statut_label(emoji):
            mapping = {
                "✅": ("OK", COULEUR_ACCENT),
                "⚠": ("Vigilance", HexColor("#F59E0B")),
                "⚠️": ("Vigilance", HexColor("#F59E0B")),
                "🔴": ("Non-conforme", HexColor("#DC2626")),
                "-": ("—", COULEUR_GRIS),
            }
            label, couleur = mapping.get(emoji, ("—", COULEUR_GRIS))
            return f"<font color='{couleur.hexval()}'><b>{label}</b></font>"

        check_rows = [[Paragraph(p.libelle, styles["small"]),
                       Paragraph(_statut_label(p.statut), styles["small"]),
                       Paragraph(p.action, styles["small"])]
                      for p in synthese.checklist]
        flow.append(_data_table(check_rows, styles,
                                 headers=["Point de contrôle", "Statut", "Action requise"],
                                 col_widths=[60*mm, 24*mm, 90*mm]))

    flow.append(PageBreak())

    # ============================================================
    # PAGE 4 — Comparateur patrimonial
    # ============================================================
    flow.append(Paragraph("Placement du net dirigeant", styles["h1"]))
    flow.append(Paragraph(
        synthese.enveloppes_compact["hypothese_texte"],
        styles["body"]))
    flow.append(Paragraph(
        "Comparaison de quatre enveloppes patrimoniales pour le placement "
        "du net dirigeant disponible. Hypothèse de capitalisation annuelle "
        "composée. Le choix final dépend de l'horizon, des objectifs de "
        "transmission, et du besoin de liquidité.",
        styles["body"]))

    env_rows = [[e.nom, fmt_eur(e.net_disponible),
                 Paragraph(e.fiscalite_sortie, styles["small"]),
                 e.avantage_cle]
                for e in synthese.enveloppes_compact["enveloppes"]]
    flow.append(Spacer(1, 4*mm))
    flow.append(_data_table(env_rows, styles,
                             headers=["Enveloppe", "Net à 5 ans",
                                      "Fiscalité sortie", "Avantage clé"],
                             col_widths=[50*mm, 32*mm, 52*mm, 40*mm]))

    flow.append(Spacer(1, 4*mm))
    flow.append(Paragraph(
        f"<b>Meilleure enveloppe sur ces hypothèses :</b> "
        f"{synthese.enveloppes_compact['meilleure']}",
        styles["callout"]))

    flow.append(PageBreak())

    # ============================================================
    # PAGE 5 — Annexe : hypothèses & avertissements
    # ============================================================
    flow.append(Paragraph("Annexe — Hypothèses & avertissements", styles["h1"]))

    # B.2.5 — Trace doctrinale enrichie (option C, fiche méthodo consultable)
    _section_trace_doctrinale_annexe(flow, styles, niveau_confiance)

    flow.append(Paragraph("Référentiel réglementaire", styles["h2"]))
    flow.append(Paragraph(
        f"<b>Doctrine version {doctrine_version}</b> mise à jour au "
        f"<b>{doctrine_date}</b>. Le moteur intègre les paramètres "
        f"fiscaux et sociaux applicables à cette date : PASS 2026 "
        f"(48 060 €), barème IR 2026, taux PFU 31,4 %, plafonds "
        f"d'abondement PEE/PERECO/PERO, seuils CEHR/CDHR, abattements "
        f"foyer fiscal selon plafonnement du quotient familial.",
        styles["body"]))

    flow.append(Paragraph("Niveau de précision", styles["h2"]))
    flow.append(Paragraph(
        f"Cette synthèse est produite au niveau <b>{niveau_confiance}</b>. "
        f"Elle consolide les modules détaillés (Assimilé salarié, TNS, "
        f"Libéral, Salarié) qui intègrent CEHR, CDHR, plafonnement QF "
        f"et quatre cas particuliers (parent isolé, personne seule case L, "
        f"veuf avec enfants, invalide ou ancien combattant). La lecture "
        f"des plafonds d'épargne sociale est consolidée prudemment selon "
        f"la doctrine URSSAF 2024.",
        styles["body"]))

    flow.append(Paragraph("Hypothèses spécifiques", styles["h2"]))
    hypo_rows = [
        ["Forfait social PERECO",
         "0 % (régime PACTE applicable jusqu'à fin 2027 — à réévaluer pour 2028)"],
        ["Forfait social PERO",
         "8 % (paramètre expert modifiable)"],
        ["Rendement cash défensif (projection)", "2 % par an"],
        ["Rendement épargne capitalisable",       "4 % par an"],
        ["Capitalisation",
         "Annuelle composée, versement en début d'année"],
        ["Taux moyen IR Arbitrage",
         "Calculé sur module Assimilé puis appliqué uniformément (méthodologie v19)"],
    ]
    flow.append(_data_table(hypo_rows, styles, col_widths=[74*mm, 100*mm]))

    flow.append(Spacer(1, 6*mm))

    flow.append(Paragraph("Limites & avertissements", styles["h2"]))

    # ──────────── Disclaimer obligatoire v1.0.1 — Primauté cabinet ────────────
    flow.append(Paragraph(
        "<b>Primauté de l'analyse cabinet.</b> Cet outil produit un cadrage "
        "indicatif. Toute décision d'arbitrage de rémunération, de "
        "structuration juridique ou de mise en œuvre d'un dispositif "
        "d'épargne doit être validée par le cabinet en charge du dossier, "
        "qui dispose de la vue complète sur la situation du dirigeant, "
        "sa société, sa trésorerie et ses objectifs patrimoniaux.",
        styles["body"]))

    flow.append(Paragraph(
        "<b>Limite 1 — Régimes couverts.</b> L'arbitrage stratégique avancé "
        "couvre les régimes Assimilé salarié, TNS, Libéral (BNC et SEL) et "
        "Salarié comme référence comparative. Chaque régime applique ses "
        "propres stratégies (A/B/C/D, T1-T4, L1-L4). Les structures "
        "patrimoniales avancées (holding, démembrement, SPFPL) ne sont pas "
        "modélisées en v1 et feront l'objet d'une étude dédiée en cabinet.",
        styles["body"]))
    flow.append(Paragraph(
        "<b>Limite 2 — Article 83 historique.</b> Seuls les flux PERO "
        "post-2019 sont modélisés. Les contrats article 83 antérieurs "
        "(en sommeil ou transférés) ne sont pas pris en compte.",
        styles["body"]))
    flow.append(Paragraph(
        "<b>Limite 3 — Évolutions réglementaires.</b> Les paramètres "
        "fiscaux et sociaux sont susceptibles d'évoluer en cours d'année "
        "(LFI, LFSS, circulaires URSSAF). Le moteur sera mis à jour à "
        "chaque évolution structurante.",
        styles["body"]))

    # ──────────── Disclaimer obligatoire v1.0.1 — AMF Comparateur patrimonial ────────────
    flow.append(Paragraph(
        "<b>Comparateur patrimonial — information AMF.</b> La page "
        "« Placement du net dirigeant » présente une comparaison "
        "d'enveloppes patrimoniales à titre indicatif. Elle ne constitue "
        "ni un conseil en investissement, ni une recommandation de "
        "souscription, ni une analyse d'adéquation au sens de la directive "
        "MIF II / AMF. Le choix d'une enveloppe d'épargne ou d'assurance "
        "doit être validé par un conseiller en investissements financiers "
        "(CIF) ou un courtier en assurance habilité, après évaluation du "
        "profil de risque et des objectifs du dirigeant.",
        styles["body"]))

    flow.append(Spacer(1, 8*mm))
    flow.append(Paragraph(
        "Ce document constitue un cadrage indicatif et un outil d'aide "
        "à la décision. Il n'engage pas la responsabilité de l'éditeur "
        "du logiciel et ne saurait se substituer à l'analyse complémentaire "
        "recommandée du cabinet, au regard de la situation complète du "
        "dirigeant et de sa société, incluant notamment la trésorerie "
        "disponible, les ratios bancaires, les covenants, et les objectifs "
        "patrimoniaux à long terme.",
        styles["callout"]))

    doc.build(flow)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ============================================================
# DISCLAIMERS PERMANENTS v1.0.1
# ============================================================
# Phase B.2 Étape 6 : disclaimers introduits localement.
# Phase B.2.5 : centralisés dans ui/disclaimers.py. On les ré-exporte ici
# pour ne pas casser les éventuels imports historiques.
from ui.disclaimers import (
    DISCLAIMER_PRIMAUTE_CABINET,
    DISCLAIMER_AMF_COMPARATEUR_PATRIMONIAL,
    DISCLAIMER_AVERTISSEMENT_FINAL,
)


# ============================================================
# LIBELLÉS PAR RÉGIME (Phase B.2 Étape 6, validés utilisateur)
# ============================================================
LIBELLES_REGIME = {
    "Assimilé salarié": {
        "titre_couverture": "Arbitrage de rémunération — Dirigeant assimilé salarié",
        "section_principale": "Stratégies d'allocation A/B/C/D",
    },
    "TNS": {
        "titre_couverture": "Arbitrage de rémunération — Dirigeant TNS",
        "section_principale": "Stratégies rémunération / dividendes T1-T4",
    },
    "TNS (libéral) — BNC": {
        "titre_couverture": "Cadrage de structuration — Profession libérale BNC",
        "section_principale": "Stratégies BNC L1-L2",
    },
    "TNS (libéral) — SEL": {
        "titre_couverture": "Cadrage de structuration — SELARL / SELAS",
        "section_principale": "Stratégies SEL L1-L4",
    },
    "Salarié": {
        "titre_couverture": "Référence comparative — Salarié non-dirigeant",
        "section_principale": "Référence salariale",
    },
}


def _libelles_for_profil(profil) -> dict:
    """
    Retourne le couple (titre couverture, section principale) selon le profil.

    Pour les libéraux, on distingue BNC vs SEL via forme_juridique.
    """
    regime = profil.regime_social

    if regime == "TNS (libéral)":
        if profil.forme_juridique == "SELARL / SELAS":
            return LIBELLES_REGIME["TNS (libéral) — SEL"]
        else:
            return LIBELLES_REGIME["TNS (libéral) — BNC"]

    if regime in LIBELLES_REGIME:
        return LIBELLES_REGIME[regime]

    # Fallback Salarié
    return LIBELLES_REGIME["Salarié"]


# ============================================================
# HELPER COMMUN — Couverture adaptative
# ============================================================
def _section_couverture(flow, styles, profil, client_nom, expert_comptable,
                        niveau_confiance, libelles):
    """
    Construit la page de garde adaptée au régime.

    Garde-fous :
    - Régime affiché EXPLICITEMENT (titre + ligne "Régime social")
    - Branding cabinet préservé (passé via header de doc, non touché ici)
    - Sous-titre prudent : "cadrage indicatif"
    """
    flow.append(Paragraph(libelles["titre_couverture"], styles["title"]))
    flow.append(Paragraph(
        f"Cadrage indicatif — outil d'aide à la décision — {profil.regime_social}",
        styles["subtitle"]))

    flow.append(_badge_niveau(niveau_confiance, styles))
    flow.append(Spacer(1, 8*mm))

    flow.append(Paragraph("Dossier client", styles["h2"]))
    dossier_rows = [
        ["Client", client_nom],
        ["Forme juridique", profil.forme_juridique],
        ["Régime social", profil.regime_social],
        ["Effectif", profil.effectif],
        ["Foyer fiscal", f"{profil.situation} — {profil.parts:g} parts"],
        ["Date de simulation", datetime.now().strftime("%d/%m/%Y")],
    ]
    if expert_comptable:
        dossier_rows.append(["Expert-comptable en charge", expert_comptable])
    flow.append(_data_table(dossier_rows, styles, col_widths=[60*mm, 114*mm]))


# ============================================================
# HELPER COMMUN — Section disclaimers v1.0.1 (toujours présents)
# ============================================================
def _section_disclaimers_v1_0_1(flow, styles):
    """Insère les 2 disclaimers v1.0.1 obligatoires + avertissement final."""
    flow.append(Paragraph(DISCLAIMER_PRIMAUTE_CABINET, styles["body"]))
    flow.append(Spacer(1, 4*mm))
    flow.append(Paragraph(DISCLAIMER_AMF_COMPARATEUR_PATRIMONIAL, styles["body"]))
    flow.append(Spacer(1, 6*mm))
    flow.append(Paragraph(DISCLAIMER_AVERTISSEMENT_FINAL, styles["callout"]))


# ============================================================
# HELPER COMMUN — Trace doctrinale enrichie (Phase B.2.5, option C)
# ============================================================
def _section_trace_doctrinale_annexe(flow, styles, niveau_confiance: str):
    """Insère la fiche méthodo consultable en début d'annexe.

    Option C de B.2.5 : annexe enrichie présentant la version de doctrine,
    le niveau du module, la grille des 4 niveaux v1.0.1, et le rappel des
    garde-fous structurels permanents.

    À appeler en début de chaque annexe « Cadre méthodologique » /
    « Hypothèses & avertissements », avant les sections « Référentiel »,
    « Niveau de précision », etc., qui restent dans les builders existants.
    """
    from ui.disclaimers import trace_doctrinale_annexe_complete
    flow.append(Paragraph("Trace doctrinale", styles["h2"]))
    flow.append(Paragraph(
        trace_doctrinale_annexe_complete(niveau_confiance),
        styles["body"]))
    flow.append(Spacer(1, 4*mm))


# ============================================================
# BUILDER TNS — Stratégies T1-T4 (Phase B.2 Étape 6)
# ============================================================
def _build_pdf_tns(synthese, arbitrage, profil,
                   cabinet_nom, client_nom, expert_comptable,
                   niveau_confiance, doctrine_version, doctrine_date) -> bytes:
    """
    Génère le PDF TNS — stratégies T1-T4.

    GARDE-FOU CRITIQUE T4 :
    Les indicateurs net_dirigeant_immediat et benefice_retenu_societe
    sont AFFICHÉS SÉPARÉMENT. JAMAIS additionnés. Pas de champ "total".

    Sections :
    - Couverture "Arbitrage de rémunération — Dirigeant TNS"
    - Lecture stratégie retenue (avec mention spéciale T4 si applicable)
    - Tableau comparatif T1-T4 (colonnes : Net immédiat | Bénéfice retenu | Alertes)
    - Annexe disclaimers v1.0.1
    """
    # Le routeur garantit que strategies_arbitrage est un dict de
    # ResultatStrategieTNS (objets dataclass)
    strategies = arbitrage.strategies if hasattr(arbitrage, 'strategies') else arbitrage

    # Normalisation niveau (résolution alias historiques, garde-fou v1.0.1)
    niveau_confiance = _normaliser_niveau(niveau_confiance)

    buffer = io.BytesIO()
    doc = SyntheseDocTemplate(buffer,
                               cabinet_nom=cabinet_nom, client_nom=client_nom,
                               niveau_confiance=niveau_confiance,
                               doctrine_version=doctrine_version,
                               doctrine_date=doctrine_date)
    styles = _build_styles()
    flow = []

    libelles = _libelles_for_profil(profil)

    # ──────────── PAGE 1 — Couverture ────────────
    _section_couverture(flow, styles, profil, client_nom,
                        expert_comptable, niveau_confiance, libelles)
    flow.append(Spacer(1, 8*mm))

    # KPIs clés (sans agrégation T4 - garde-fou critique)
    flow.append(Paragraph("Résultats clés", styles["h2"]))
    code_retenu = synthese.strategie_retenue
    strat_retenue = strategies[code_retenu]

    # Net dirigeant immédiat (commun à T1-T4)
    net_immediat = strat_retenue.net_dirigeant_immediat
    benefice_retenu = getattr(strat_retenue, 'benefice_retenu_societe', 0.0)

    kpis = [
        ("Stratégie retenue", f"{code_retenu} — {strat_retenue.nom}"),
        ("Net dirigeant immédiat (revenu personnel)", fmt_eur(net_immediat, 0)),
    ]
    # Bénéfice retenu affiché SÉPARÉMENT si applicable (T4)
    if benefice_retenu > 0:
        kpis.append(("Bénéfice retenu en société (T4)", fmt_eur(benefice_retenu, 0)))
    flow.append(_kpi_table(kpis, styles))

    flow.append(Spacer(1, 6*mm))

    # Lecture textuelle
    flow.append(Paragraph("Lecture de la stratégie retenue", styles["h2"]))
    lecture = (
        f"Sur la base d'un bénéfice avant rémunération de "
        f"<b>{fmt_eur(profil.benefice_is, 0)}</b>, la stratégie "
        f"<b>{code_retenu} — {strat_retenue.nom}</b> dégage un net dirigeant "
        f"immédiat de <b>{fmt_eur(net_immediat)}</b>."
    )
    flow.append(Paragraph(lecture, styles["body"]))

    # Mention spéciale T4 (garde-fou critique)
    if code_retenu == "T4" and benefice_retenu > 0:
        flow.append(Spacer(1, 3*mm))
        flow.append(Paragraph(
            f"<b>Stratégie T4 retenue — indicateur séparé.</b> "
            f"Un montant de <b>{fmt_eur(benefice_retenu, 0)}</b> est conservé "
            f"en société après IS. Cette valeur n'est <b>pas un revenu "
            f"disponible</b> pour le dirigeant : elle reste à l'actif de "
            f"la société. Sa distribution ultérieure subira la fiscalité "
            f"applicable au moment de la distribution. Elle ne doit pas "
            f"être additionnée au net dirigeant immédiat.",
            styles["callout"]))

    flow.append(Spacer(1, 4*mm))
    flow.append(Paragraph(
        "Ce cadrage indicatif est destiné à appuyer l'analyse en cabinet ; "
        "il ne constitue pas une recommandation juridique ou patrimoniale.",
        styles["body"]))

    flow.append(PageBreak())

    # ──────────── PAGE 2 — Stratégies T1-T4 ────────────
    flow.append(Paragraph(libelles["section_principale"], styles["h1"]))
    flow.append(Paragraph(
        "Quatre stratégies de frontière rémunération / dividendes sont "
        "modélisées à bénéfice avant rémunération constant. T1 maximise "
        "la rémunération cotisable, T2 sature le seuil 10 % capital+CCA "
        "en dividendes, T3 combine les leviers avec un versement PERIN "
        "au plafond individuel, T4 conserve une part du bénéfice en "
        "société (deux indicateurs séparés affichés ci-dessous).",
        styles["body"]))

    flow.append(Spacer(1, 4*mm))

    # Tableau T1-T4 avec colonnes séparées (jamais d'agrégation)
    rows = []
    for code in ["T1", "T2", "T3", "T4"]:
        if code not in strategies:
            continue
        s = strategies[code]
        s_net_imm = s.net_dirigeant_immediat
        s_benef_ret = getattr(s, 'benefice_retenu_societe', 0.0)
        rows.append([
            f"{code} — {s.nom}",
            fmt_eur(s_net_imm),
            fmt_eur(s_benef_ret) if s_benef_ret > 0 else "—",
            f"{len(getattr(s, 'alertes', []))} alerte(s)",
        ])
    flow.append(_data_table(
        rows, styles,
        headers=["Stratégie", "Net dirigeant immédiat",
                 "Bénéfice retenu société", "Alertes"],
        col_widths=[58*mm, 40*mm, 40*mm, 36*mm],
    ))

    flow.append(Spacer(1, 6*mm))

    # Alertes spécifiques de la stratégie retenue
    if hasattr(strat_retenue, 'alertes') and strat_retenue.alertes:
        flow.append(Paragraph(
            f"Alertes spécifiques — stratégie {code_retenu}",
            styles["h2"]))
        for alerte in strat_retenue.alertes:
            flow.append(Paragraph(f"• {alerte}", styles["body"]))
            flow.append(Spacer(1, 2*mm))

    flow.append(PageBreak())

    # ──────────── PAGE 3 — Annexe : disclaimers v1.0.1 ────────────
    flow.append(Paragraph("Annexe — Cadre méthodologique", styles["h1"]))

    # B.2.5 — Trace doctrinale enrichie (option C)
    _section_trace_doctrinale_annexe(flow, styles, niveau_confiance)

    flow.append(Paragraph("Référentiel doctrinal", styles["h2"]))
    flow.append(Paragraph(
        f"<b>Doctrine version {doctrine_version}</b> mise à jour au "
        f"<b>{doctrine_date}</b>. Paramètres fiscaux et sociaux 2026 : "
        f"PASS 48 060 €, barème IR, PFU 31,4 %, seuils CEHR/CDHR, "
        f"plafonnement QF. Cotisations TNS calibrées sur la rémunération "
        f"nette (méthodologie URSSAF prudente).",
        styles["body"]))

    flow.append(Spacer(1, 4*mm))
    flow.append(Paragraph("Limites & avertissements", styles["h2"]))
    _section_disclaimers_v1_0_1(flow, styles)

    doc.build(flow)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ============================================================
# BUILDER LIBÉRAL — Stratégies L1-L4 (Phase B.2 Étape 6)
# ============================================================
def _build_pdf_liberal(synthese, arbitrage, profil,
                       cabinet_nom, client_nom, expert_comptable,
                       niveau_confiance, doctrine_version, doctrine_date) -> bytes:
    """
    Génère le PDF Libéral — stratégies L1-L4.

    GARDE-FOUS :
    - L3/L4 retenue → alerte BNC/SEL systématiquement affichée
    - Terminologie "stratégie la plus efficace fiscalement" (pas "recommandée")
    - Cadrage de structuration (libellé prudent)
    """
    strategies = arbitrage.strategies if hasattr(arbitrage, 'strategies') else arbitrage

    # Normalisation niveau (résolution alias historiques, garde-fou v1.0.1)
    niveau_confiance = _normaliser_niveau(niveau_confiance)

    buffer = io.BytesIO()
    doc = SyntheseDocTemplate(buffer,
                               cabinet_nom=cabinet_nom, client_nom=client_nom,
                               niveau_confiance=niveau_confiance,
                               doctrine_version=doctrine_version,
                               doctrine_date=doctrine_date)
    styles = _build_styles()
    flow = []

    libelles = _libelles_for_profil(profil)

    # ──────────── PAGE 1 — Couverture ────────────
    _section_couverture(flow, styles, profil, client_nom,
                        expert_comptable, niveau_confiance, libelles)
    flow.append(Spacer(1, 8*mm))

    # KPIs
    flow.append(Paragraph("Résultats clés", styles["h2"]))
    code_retenu = synthese.strategie_retenue
    strat_retenue = strategies[code_retenu]
    net_total = strat_retenue.net_dirigeant_total
    structure = strat_retenue.structure

    kpis = [
        ("Stratégie retenue", f"{code_retenu} — {strat_retenue.nom}"),
        ("Structure", structure),
        ("Net dirigeant", fmt_eur(net_total, 0)),
        ("Recettes BNC (base)", fmt_eur(profil.recettes_bnc, 0)),
    ]
    flow.append(_kpi_table(kpis, styles))

    flow.append(Spacer(1, 6*mm))

    # Lecture textuelle (terminologie prudente)
    flow.append(Paragraph("Lecture de la stratégie retenue", styles["h2"]))
    lecture = (
        f"Sur la base d'un chiffre d'affaires libéral de "
        f"<b>{fmt_eur(profil.recettes_bnc, 0)}</b>, la stratégie "
        f"<b>{code_retenu} — {strat_retenue.nom}</b> "
        f"({structure}) dégage un net dirigeant de "
        f"<b>{fmt_eur(net_total)}</b>. Il s'agit de la "
        f"<b>stratégie présentant le niveau de net le plus élevé dans le "
        f"cadre des hypothèses retenues</b> parmi L1-L4 — non d'une "
        f"recommandation de structuration. Le choix entre BNC et SEL "
        f"implique une analyse juridique, sociale, fiscale et "
        f"patrimoniale complète."
    )
    flow.append(Paragraph(lecture, styles["body"]))

    flow.append(PageBreak())

    # ──────────── PAGE 2 — Stratégies L1-L4 ────────────
    flow.append(Paragraph(libelles["section_principale"], styles["h1"]))
    flow.append(Paragraph(
        "Quatre stratégies de structuration sont modélisées à chiffre "
        "d'affaires constant. L1 et L2 maintiennent l'exercice en BNC. "
        "L3 introduit une SEL (SELARL ou SELAS selon la forme retenue). "
        "L4 prolonge L3 avec un cadrage minimal des leviers patrimoniaux "
        "(holding, démembrement, transmission), dont la modélisation "
        "détaillée relève d'une étude dédiée en v2.",
        styles["body"]))

    flow.append(Spacer(1, 4*mm))

    rows = []
    for code in ["L1", "L2", "L3", "L4"]:
        if code not in strategies:
            continue
        s = strategies[code]
        rows.append([
            f"{code} — {s.nom}",
            s.structure,
            fmt_eur(s.net_dirigeant_total),
            f"{len(getattr(s, 'alertes', []))} alerte(s)",
        ])
    flow.append(_data_table(
        rows, styles,
        headers=["Stratégie", "Structure", "Net dirigeant", "Alertes"],
        col_widths=[68*mm, 32*mm, 38*mm, 36*mm],
    ))

    flow.append(Spacer(1, 6*mm))

    # Alertes spécifiques (BNC/SEL si L3/L4)
    if hasattr(strat_retenue, 'alertes') and strat_retenue.alertes:
        flow.append(Paragraph(
            f"Alertes spécifiques — stratégie {code_retenu}",
            styles["h2"]))
        for alerte in strat_retenue.alertes:
            flow.append(Paragraph(f"• {alerte}", styles["body"]))
            flow.append(Spacer(1, 2*mm))

    flow.append(PageBreak())

    # ──────────── PAGE 3 — Annexe ────────────
    flow.append(Paragraph("Annexe — Cadre méthodologique", styles["h1"]))

    # B.2.5 — Trace doctrinale enrichie (option C)
    _section_trace_doctrinale_annexe(flow, styles, niveau_confiance)

    flow.append(Paragraph("Référentiel doctrinal", styles["h2"]))
    flow.append(Paragraph(
        f"<b>Doctrine version {doctrine_version}</b> mise à jour au "
        f"<b>{doctrine_date}</b>. Cotisations Libérales calibrées sur "
        f"la base 2026. Pour les SEL : SELARL = gérant TNS, SELAS = "
        f"président Assimilé. La distribution intégrale du bénéfice "
        f"après IS est une simplification v1 ; les modèles de "
        f"rétention de bénéfice (T4 TNS) sont disponibles séparément.",
        styles["body"]))

    flow.append(Spacer(1, 4*mm))
    flow.append(Paragraph("Limites & avertissements", styles["h2"]))
    _section_disclaimers_v1_0_1(flow, styles)

    doc.build(flow)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ============================================================
# BUILDER SALARIÉ — Référence comparative (Phase B.2 Étape 6)
# ============================================================
def _build_pdf_salarie(synthese, arbitrage, profil,
                       cabinet_nom, client_nom, expert_comptable,
                       niveau_confiance, doctrine_version, doctrine_date) -> bytes:
    """
    Génère le PDF Salarié — référence comparative (pas de Strategy Engine).

    GARDE-FOUS :
    - Libellé "Référence comparative" (pas "Synthèse d'arbitrage")
    - Mention explicite : le salarié non-dirigeant n'a pas d'enveloppe à arbitrer
    """
    # Normalisation niveau (résolution alias historiques, garde-fou v1.0.1)
    niveau_confiance = _normaliser_niveau(niveau_confiance)

    buffer = io.BytesIO()
    doc = SyntheseDocTemplate(buffer,
                               cabinet_nom=cabinet_nom, client_nom=client_nom,
                               niveau_confiance=niveau_confiance,
                               doctrine_version=doctrine_version,
                               doctrine_date=doctrine_date)
    styles = _build_styles()
    flow = []

    libelles = LIBELLES_REGIME["Salarié"]  # Forcé : le builder Salarié sait toujours quel libellé utiliser

    # ──────────── PAGE 1 — Couverture ────────────
    _section_couverture(flow, styles, profil, client_nom,
                        expert_comptable, niveau_confiance, libelles)
    flow.append(Spacer(1, 8*mm))

    # KPIs
    flow.append(Paragraph("Résultats clés", styles["h2"]))
    kpis = [
        ("Salaire brut", fmt_eur(profil.salaire_brut_assimile, 0)),
        ("Net après IR", fmt_eur(synthese.net_dirigeant_retenu, 0)),
    ]
    flow.append(_kpi_table(kpis, styles))

    flow.append(Spacer(1, 6*mm))

    # Lecture textuelle
    flow.append(Paragraph("Lecture", styles["h2"]))
    lecture = (
        f"Cette page constitue une <b>référence comparative</b> pour le "
        f"régime du salarié non-dirigeant. Sur la base d'un salaire brut "
        f"de <b>{fmt_eur(profil.salaire_brut_assimile, 0)}</b>, le net "
        f"après IR s'établit à <b>{fmt_eur(synthese.net_dirigeant_retenu)}</b>."
    )
    flow.append(Paragraph(lecture, styles["body"]))

    flow.append(Spacer(1, 3*mm))
    flow.append(Paragraph(
        "<b>Le salarié non-dirigeant n'a pas d'enveloppe dirigeant à "
        "arbitrer.</b> Les dispositifs PEE / PERECO / PERO dépendent de "
        "la politique RH de l'employeur ; ils ne sont donc pas modélisés "
        "comme leviers d'arbitrage personnel dans ce document. Cette "
        "page sert essentiellement de point de comparaison dans la "
        "lecture inter-régimes.",
        styles["callout"]))

    flow.append(PageBreak())

    # ──────────── PAGE 2 — Annexe ────────────
    flow.append(Paragraph("Annexe — Cadre méthodologique", styles["h1"]))

    # B.2.5 — Trace doctrinale enrichie (option C)
    _section_trace_doctrinale_annexe(flow, styles, niveau_confiance)

    flow.append(Paragraph("Référentiel doctrinal", styles["h2"]))
    flow.append(Paragraph(
        f"<b>Doctrine version {doctrine_version}</b> mise à jour au "
        f"<b>{doctrine_date}</b>. Calcul net salarié : abattement 10% "
        f"sur revenu professionnel (plafonné 2026), CSG/CRDS sur "
        f"assiette 98,25%, barème IR avec quotient familial.",
        styles["body"]))

    flow.append(Spacer(1, 4*mm))
    flow.append(Paragraph("Limites & avertissements", styles["h2"]))
    _section_disclaimers_v1_0_1(flow, styles)

    doc.build(flow)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ============================================================
# ROUTEUR PUBLIC — generer_pdf_synthese (Phase B.2 Étape 6)
# ============================================================
def generer_pdf_synthese(
    synthese,
    arbitrage,
    profil,
    cabinet_nom: str = "Cabinet d'expertise comptable",
    client_nom: str = "Client",
    expert_comptable: str = "",
    niveau_confiance: str = "Avancé",
    doctrine_version: str = "1.0.1",
    doctrine_date: str = "01/01/2026",
) -> bytes:
    """
    Génère le PDF de Synthèse adapté au régime du profil.

    Routeur multi-régimes (Phase B.2 Étape 6) :
    - Assimilé salarié → _build_pdf_assimile (Phase A préservée)
    - TNS → _build_pdf_tns (stratégies T1-T4, garde-fou T4)
    - TNS (libéral) → _build_pdf_liberal (L1-L4, alerte BNC/SEL)
    - Salarié → _build_pdf_salarie (référence comparative)

    Préserve la signature publique d'origine : app.py n'a aucune
    modification à effectuer.

    Args:
        synthese: ResultatSynthese (output de calcul_synthese)
        arbitrage: dict (Assimilé) ou ResultatArbitrage* (TNS/Libéral)
        profil: Profil client (regime_social détermine le builder)
        cabinet_nom, client_nom, expert_comptable: branding
        niveau_confiance: niveau de précision affiché
        doctrine_version, doctrine_date: traçabilité doctrine

    Returns:
        Bytes du PDF généré.
    """
    regime = profil.regime_social

    common_args = dict(
        cabinet_nom=cabinet_nom,
        client_nom=client_nom,
        expert_comptable=expert_comptable,
        niveau_confiance=niveau_confiance,
        doctrine_version=doctrine_version,
        doctrine_date=doctrine_date,
    )

    if regime == "Assimilé salarié":
        return _build_pdf_assimile(synthese, arbitrage, profil, **common_args)
    elif regime == "TNS":
        return _build_pdf_tns(synthese, arbitrage, profil, **common_args)
    elif regime == "TNS (libéral)":
        return _build_pdf_liberal(synthese, arbitrage, profil, **common_args)
    else:
        # Cas Salarié non-dirigeant ou inconnu → builder référence
        return _build_pdf_salarie(synthese, arbitrage, profil, **common_args)
