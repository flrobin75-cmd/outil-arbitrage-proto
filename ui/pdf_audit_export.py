"""
ui/pdf_audit_export.py — Renderer PDF audit-ready pour TraceAudit (MODE_AUDIT).

Cette couche **présentation** consomme un objet `core.audit.TraceAudit` et
produit un PDF cabinet-grade dédié à la restitution de l'audit (graphe
d'étapes, sous-traces, doctrine_refs, hypotheses, notes).

Le renderer PDF audit est **indépendant** du renderer PDF synthèse
(`ui/pdf_export.py`). Les deux coexistent comme produits documentaires
distincts :

- `generer_pdf_synthese(synthese, arbitrage, profil, ...)` → PDF métier
  (synthèse dirigeant, comparateur, KPIs, radar) — Phase A + B.2 Étape 6.
- `generer_pdf_audit(trace, ...)` → PDF audit (graphe MODE_AUDIT
  intégral, navigable par signets, source unique = `TraceAudit`).

Principes :

1. **Source unique** : le renderer ne calcule rien, il formate. Toute
   valeur affichée vient directement de la trace (cf. `ui/audit_render.py`).
2. **Résolution doctrinale paresseuse** : les `doctrine_ref` sont résolues
   au moment du rendu via `core.audit.resoudre_doctrine_ref`. Permet de
   visualiser un éventuel override (`hypotheses[ref] != doctrine`).
3. **Vocabulaire prudent** : le renderer applique les restrictions
   terminologiques (14 patterns non-prescriptifs §6.2 doctrine). Aucune
   chaîne générée par ce module ne contient de terme proscrit.
4. **Charte commune** : couleurs, fonts, marges importées depuis
   `ui/pdf_export.py` (continuité produit cabinet, pas de duplication).
5. **Traçabilité** : pied de page enrichi avec `Audit baseline hash`,
   version doctrine, version PDF audit spec, niveau de confiance.

Versions :

- `AUDIT_PDF_SPEC_VERSION` : version propre au renderer PDF audit
  (pagination, signets, conventions de présentation). Évolue
  indépendamment de `AUDIT_SPEC_VERSION` (spec graphe `core/audit.py`).

Statut SP1 (scaffolding) :

- DocTemplate audit, charte importée, styles 9 pt.
- Stub `generer_pdf_audit()` : génère un PDF valide (magic %PDF-,
  taille minimale, couverture minimaliste).
- Pas encore de rendu de trace — SP2 ajoutera les étapes plates.
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas

from core.audit import TraceAudit, EtapeAudit, resoudre_doctrine_ref
from ui.pdf_export import (
    COULEUR_PRIMAIRE,
    COULEUR_SECONDAIRE,
    COULEUR_ACCENT,
    COULEUR_TEXTE,
    COULEUR_GRIS,
    COULEUR_FOND_TABLEAU,
    COULEUR_LIGNE,
    NIVEAU_COULEURS_PDF,
    _normaliser_niveau,
)
from ui.disclaimers import (
    DISCLAIMER_PRIMAUTE_CABINET,
    DISCLAIMER_AVERTISSEMENT_FINAL,
    TRACE_DOCTRINALE_FOOTER,
)


# ============================================================
# VERSIONS
# ============================================================
AUDIT_PDF_SPEC_VERSION = "1.0.0"
"""Version de la spec du renderer PDF audit.

Indépendante de :
- `core.audit.AUDIT_SPEC_VERSION` (spec du graphe d'audit, actuellement 1.1.0)
- `doctrine.DOCTRINE_VERSION` (doctrine métier, actuellement 1.0.1)
- `ui.disclaimers.DISCLAIMERS_VERSION` (disclaimers, actuellement 1.0.1)

Évolue lors de changements de pagination, conventions de signets, styles,
annexes, etc.
"""

AUDIT_PDF_DATE = "2026-05-20"
"""Date de figement de la spec PDF audit courante."""


# ============================================================
# CONSTANTES BASELINE (pour pied de page)
# ============================================================
BASELINE_HASH_DEFAUT = "8863991f27f67847"
"""Hash baseline conservé bout-en-bout (MODE_AUDIT v1.6 / G3g).

Affiché en pied de page de chaque PDF audit pour traçabilité cabinet.
Toute régression de cette baseline est un blocker (cf. compare_baseline.py).
"""


# ============================================================
# STYLES — base 9 pt (densité audit cabinet)
# ============================================================
# Le renderer audit utilise une typographie plus dense que le renderer
# synthèse (corps 9 pt vs 10 pt) pour absorber le volume d'étapes (jusqu'à
# ~1187 étapes structurées sur le périmètre v1.6) en restant lisible.
def _build_audit_styles() -> dict:
    """Construit le set de styles dédié au PDF audit.

    Les styles ne sont **pas importés** de ui/pdf_export.py : le PDF audit
    a ses propres contraintes (densité, encadrés métier, lignes doctrinales
    discrètes). Seuls les **couleurs** sont partagées (charte commune).
    """
    base = getSampleStyleSheet()
    return {
        # Couverture
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
        # Hiérarchie des sections (sous-traces)
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"],
            fontSize=15, leading=19, textColor=COULEUR_PRIMAIRE,
            fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"],
            fontSize=12, leading=15, textColor=COULEUR_TEXTE,
            fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "h3", parent=base["Heading3"],
            fontSize=10, leading=13, textColor=COULEUR_SECONDAIRE,
            fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=4,
        ),
        # Corps : 9 pt (densité audit)
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, leading=12, textColor=COULEUR_TEXTE,
            fontName="Helvetica", alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        # Étapes : 9 pt (cellules de tableau)
        "etape_cell": ParagraphStyle(
            "etape_cell", parent=base["Normal"],
            fontSize=9, leading=11, textColor=COULEUR_TEXTE,
            fontName="Helvetica", alignment=TA_LEFT,
        ),
        # Doctrine_refs : gris discret, taille réduite (Q5 — arbitrage validé)
        "doctrine_ref": ParagraphStyle(
            "doctrine_ref", parent=base["Normal"],
            fontSize=7, leading=9, textColor=COULEUR_GRIS,
            fontName="Helvetica-Oblique", alignment=TA_LEFT,
            leftIndent=4,
        ),
        # Hypothèses inline (< 80 chars)
        "hypothese_inline": ParagraphStyle(
            "hypothese_inline", parent=base["Normal"],
            fontSize=8, leading=10, textColor=COULEUR_TEXTE,
            fontName="Helvetica-Oblique", alignment=TA_LEFT,
            leftIndent=4,
        ),
        # Hypothèses encadrées (≥ 80 chars) — wording métier verbatim
        "hypothese_encadre": ParagraphStyle(
            "hypothese_encadre", parent=base["Normal"],
            fontSize=9, leading=12, textColor=COULEUR_TEXTE,
            fontName="Helvetica", alignment=TA_JUSTIFY,
            leftIndent=10, rightIndent=10,
            spaceBefore=4, spaceAfter=4,
            backColor=COULEUR_FOND_TABLEAU,
            borderColor=COULEUR_LIGNE, borderWidth=0.5,
            borderPadding=6,
        ),
        # Notes : italique gris
        "note": ParagraphStyle(
            "note", parent=base["Normal"],
            fontSize=8, leading=10, textColor=COULEUR_GRIS,
            fontName="Helvetica-Oblique", alignment=TA_LEFT,
            leftIndent=4, spaceAfter=2,
        ),
        # Disclaimers
        "callout": ParagraphStyle(
            "callout", parent=base["Normal"],
            fontSize=9, leading=12, textColor=COULEUR_TEXTE,
            fontName="Helvetica", alignment=TA_JUSTIFY,
            leftIndent=8, rightIndent=8,
            spaceBefore=4, spaceAfter=4,
        ),
        # Footer
        "footer_small": ParagraphStyle(
            "footer_small", parent=base["Normal"],
            fontSize=7, leading=9, textColor=COULEUR_GRIS,
            fontName="Helvetica", alignment=TA_CENTER,
        ),
    }


# ============================================================
# FORMATAGE D'UNE VALEUR D'ÉTAPE
# ============================================================
# Variante PDF de `_formater_valeur` (cf. ui/audit_render.py).
#
# Choix d'isolation : le renderer PDF a son propre formateur, sans
# padding visuel de largeur fixe (les colonnes du Table reportlab gèrent
# l'alignement). Évite un couplage entre renderer console et renderer
# PDF, et permet à chacun d'évoluer indépendamment (cf. doctrine §1
# « source unique = trace, pas formatage »).
def _formater_valeur_pdf(valeur, unite: str) -> str:
    """Formate une valeur d'étape pour rendu PDF.

    Conventions de formatage :

    - `EUR` : 2 décimales, espaces milliers (FR), suffixe « € »
      → 105 116.99 €
    - `%` : 4 décimales, suffixe « % »
      → 24.0000 %
    - `ratio` : 4 décimales, sans suffixe
      → 0.4500
    - `PASS` : valeur affichée telle quelle, suffixe « PASS »
      (plafond annuel sécurité sociale, cf. doctrine)
      → 47 100.00 PASS
    - autres numériques avec unité : 2 décimales + unité textuelle
      → 1.50 années
    - autres numériques sans unité : 2 décimales
      → 109 250.00
    - non-numériques : str() de la valeur (booléens, codes, libellés)
      → « max(net_dirigeant_immediat) », « T2 », « True »

    Args:
        valeur: Valeur à formater. Numérique ou non.
        unite: Unité doctrinale de l'étape (`EtapeAudit.unite`).

    Returns:
        Chaîne formatée prête à être injectée dans une cellule de Table.
    """
    if isinstance(valeur, bool):
        # bool est sous-classe de int → traiter avant
        return "Vrai" if valeur else "Faux"
    if isinstance(valeur, (int, float)):
        if unite == "EUR":
            return f"{valeur:,.2f} €".replace(",", " ")
        if unite == "%":
            return f"{valeur:.4f} %"
        if unite == "ratio":
            return f"{valeur:.4f}"
        if unite == "PASS":
            return f"{valeur:,.2f} PASS".replace(",", " ")
        if unite:
            return f"{valeur:,.2f} {unite}".replace(",", " ")
        return f"{valeur:,.2f}".replace(",", " ")
    # Non-numérique : str() suffit (codes stratégies, critères textuels, etc.)
    return str(valeur)


# ============================================================
# ENRICHISSEMENTS D'ÉTAPE — doctrine_refs, hypotheses, notes, overrides
# ============================================================
# Seuil pour basculer une hypothèse en encadré dédié sous le tableau.
# Calibré sur la trace TNS pilote (3 hypothèses ≥ 80 chars, toutes des
# wordings métier figés type texte_alerte_v19, note_perin, tous_nets).
# Cf. doctrine §6.4 « wording métier en hypotheses ».
SEUIL_HYPOTHESE_LONGUE = 80


def _format_hyp_valeur(valeur) -> str:
    """Formate une valeur d'hypothèse pour affichage en ligne d'enrichissement.

    Conventions plus laxistes que `_formater_valeur_pdf` (les hypothèses
    n'ont pas d'unité native ; ce sont des snapshots de constantes ou de
    paramètres calculés). Les chaînes longues sont tronquées pour
    affichage inline (le rendu encadré complet est géré par
    `_render_encadres_hypotheses_longues`).
    """
    if isinstance(valeur, bool):
        return "Vrai" if valeur else "Faux"
    if isinstance(valeur, float):
        # Hypothèses numériques : éviter la notation 1e-06, garder
        # 4 décimales max pour les ratios, espaces milliers pour gros nombres.
        if 0 < abs(valeur) < 1:
            return f"{valeur:.4f}"
        return f"{valeur:,.2f}".replace(",", " ")
    if isinstance(valeur, int):
        return f"{valeur:,}".replace(",", " ")
    return str(valeur)


def _render_enrichissements_etape(etape: EtapeAudit, styles: dict) -> list:
    """Construit les lignes additionnelles à insérer dans le tableau d'étapes.

    Pour une étape donnée, produit jusqu'à 4 types de lignes
    additionnelles, chacune étant une fusion `colspan=4` :

    1. **Doctrine_refs résolues** : pour chaque ref, une ligne « doctrine: REF=valeur ».
       En cas d'override (hypotheses[ref] != doctrine), mention explicite
       « override local : valeur appliquée X vs doctrine Y » (Q2 = β validé).
       Style : gris discret 7pt italique.

    2. **Référence introuvable** : si `resoudre_doctrine_ref(ref)` lève
       `AttributeError`, affiche « doctrine: REF (référence introuvable) »
       en gris discret. Note : sur le périmètre TNS pilote, ce cas est
       garanti absent par `test_mode_audit_strategy_tns.py`.

    3. **Hypothèses courtes orphelines** (< SEUIL_HYPOTHESE_LONGUE
       caractères, et hors doctrine_refs) : « hypothèse: clé = valeur ».
       Style : gris foncé 8pt italique. Les hypothèses ≥ SEUIL sont
       renvoyées en encadré séparé sous le tableau (cf.
       `_render_encadres_hypotheses_longues`).

    4. **Notes** : « note: texte » en italique gris 8pt.

    Chaque ligne est un `Paragraph` qui sera placé dans une cellule
    fusionnée (`SPAN`) couvrant les 4 colonnes du tableau.

    Args:
        etape: L'EtapeAudit dont on tire les enrichissements.
        styles: Dict de styles audit.

    Returns:
        Liste de `Paragraph` (peut être vide si l'étape n'a aucun
        enrichissement). Chaque Paragraph correspond à une ligne
        additionnelle dans le tableau.
    """
    lignes = []

    # 1. Doctrine_refs (résolues ou non, override ou non)
    for ref in etape.doctrine_refs:
        try:
            valeur_doctrinale = resoudre_doctrine_ref(ref)
            valeur_appliquee = etape.hypotheses.get(ref)
            if valeur_appliquee is not None and valeur_appliquee != valeur_doctrinale:
                # Override local : mention explicite (Q2 = β validé)
                texte = (
                    f"doctrine <b>{ref}</b> = "
                    f"{_format_hyp_valeur(valeur_doctrinale)} — "
                    f"<b>override local</b> : valeur appliquée "
                    f"{_format_hyp_valeur(valeur_appliquee)} "
                    f"vs doctrine {_format_hyp_valeur(valeur_doctrinale)}"
                )
            else:
                texte = (
                    f"doctrine <b>{ref}</b> = "
                    f"{_format_hyp_valeur(valeur_doctrinale)}"
                )
        except AttributeError:
            # Référence doctrinale introuvable — gris discret, sans icône
            texte = (
                f"doctrine <b>{ref}</b> : référence introuvable "
                f"(dans doctrine.py)"
            )
        lignes.append(Paragraph(texte, styles["doctrine_ref"]))

    # 2. Hypothèses courtes orphelines (hors doctrine_refs, < SEUIL)
    hyp_orphelines_courtes = {
        k: v for k, v in etape.hypotheses.items()
        if k not in etape.doctrine_refs
        and len(f"{k}={v}") < SEUIL_HYPOTHESE_LONGUE
    }
    for cle, val in hyp_orphelines_courtes.items():
        texte = f"hypothèse <b>{cle}</b> = {_format_hyp_valeur(val)}"
        lignes.append(Paragraph(texte, styles["hypothese_inline"]))

    # 3. Notes (toujours sous l'étape, jamais en encadré)
    if etape.notes:
        # Échappement minimal des chars HTML-sensibles pour Paragraph
        notes_safe = (etape.notes
                      .replace("&", "&amp;")
                      .replace("<", "&lt;")
                      .replace(">", "&gt;"))
        lignes.append(Paragraph(f"note : {notes_safe}", styles["note"]))

    return lignes


def _render_encadres_hypotheses_longues(etape: EtapeAudit, styles: dict) -> list:
    """Construit les encadrés dédiés aux hypothèses longues (≥ SEUIL chars).

    Les hypothèses longues sont typiquement des wordings métier figés
    (alertes, mentions réglementaires, disclaimers in-trace) qui
    appartiennent à `hypotheses` par convention doctrine §6.4
    (« non scannés par les tests non-prescriptifs »).

    Présentation cabinet :
    - encadré sur fond gris très clair, bordure fine 0.5pt
    - en-tête « [CODE_ETAPE] hypothèse: clé » en bold
    - contenu reproduit verbatim (échappement HTML minimal)
    - police 9pt, justifié

    Args:
        etape: L'étape dont on extrait les hypothèses longues.
        styles: Dict de styles audit.

    Returns:
        Liste de flowables (Paragraph + Spacer) à insérer sous le
        tableau. Peut être vide.
    """
    flowables: list = []
    hyp_longues = [
        (cle, val) for cle, val in etape.hypotheses.items()
        if cle not in etape.doctrine_refs
        and len(f"{cle}={val}") >= SEUIL_HYPOTHESE_LONGUE
    ]
    for cle, val in hyp_longues:
        val_str = str(val)
        # Échappement minimal HTML pour Paragraph reportlab
        val_safe = (val_str
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))
        cle_safe = (cle
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))
        en_tete = (
            f"<b><font face='Courier' size='8'>{etape.code}</font></b> — "
            f"hypothèse <b>{cle_safe}</b>"
        )
        texte_complet = f"{en_tete}<br/>{val_safe}"
        flowables.append(Paragraph(texte_complet, styles["hypothese_encadre"]))
        flowables.append(Spacer(1, 2*mm))
    return flowables


# ============================================================
# CALIBRAGE DYNAMIQUE DES LARGEURS DE COLONNES (SP7)
# ============================================================
# Avant SP7, les largeurs étaient figées à [60, 51, 50, 13] mm — calibrage
# empirique sur la trace TNS pilote (codes max 38 chars). Le diagnostic
# SP7 sur Assimilé + Libéral a révélé :
#   - Libéral L4 introduit `STRAT_LIB_L4_ALERTE_STRUCTURATION_V2_NB` (39 chars)
#     → wrap sur 2 lignes en col Code 60mm @ Courier 7pt.
#
# Le calibrage dynamique mesure la largeur réelle des contenus à rendre
# (via `pdfmetrics.stringWidth`) et alloue les colonnes en conséquence,
# avec des bornes min/max pour éviter qu'un cas extrême n'écrase une
# colonne. Le helper est neutre vis-à-vis du régime : il itère sur les
# `EtapeAudit` passées sans connaître leur namespace.
#
# Bornes assumées :
#   - Code   : [45, 75] mm — protège libellé d'un code trop long
#   - Valeur : [30, 60] mm — protège libellé d'une valeur trop longue
#   - Unité  : [12, 18] mm — quasi figé (les unités sont courtes)
#   - Libellé: [35, 80] mm — reçoit le reste après les 3 autres allocations
#
# Marges techniques constantes :
#   - Padding cellulaire : LEFTPADDING + RIGHTPADDING = 5 + 5 = 10 mm
#   - Marge de sécurité  : 3 mm (absorbe les arrondis stringWidth)
LARGEUR_UTILE_MM = 174  # A4 - 18mm marges gauche/droite (cf. AuditDocTemplate)
PADDING_CELLULAIRE_MM = 10  # somme LEFTPADDING + RIGHTPADDING dans TableStyle
MARGE_SECURITE_MM = 3
BORNES_CODE_MM = (45, 75)
BORNES_VALEUR_MM = (30, 60)
BORNES_UNITE_MM = (12, 18)
BORNES_LIBELLE_MM = (35, 80)


def _mesurer_largeur_chaine_mm(chaine: str, font: str, taille_pt: float) -> float:
    """Mesure la largeur d'une chaîne dans une police donnée, en mm.

    Utilise `pdfmetrics.stringWidth` (résultat en points typographiques)
    et convertit en millimètres (1 mm = 2.834646 pt).

    Args:
        chaine: La chaîne à mesurer.
        font: Nom de police (« Helvetica », « Courier », etc.).
        taille_pt: Taille de police en points.

    Returns:
        Largeur en mm.
    """
    if not chaine:
        return 0.0
    largeur_pt = pdfmetrics.stringWidth(chaine, font, taille_pt)
    return largeur_pt / 2.834646


def _borner(valeur: float, bornes: tuple) -> float:
    """Borne une valeur dans l'intervalle [bornes[0], bornes[1]]."""
    return max(bornes[0], min(bornes[1], valeur))


def _calibrer_col_widths(etapes: list) -> list:
    """Calibre dynamiquement les 4 largeurs de colonnes à partir des étapes.

    Stratégie :
      1. Mesurer la largeur effective du code le plus long en Courier 7pt
         (police effective utilisée par `_table_etapes_plates`).
      2. Mesurer la largeur effective de la valeur formatée la plus longue
         en Helvetica 9pt.
      3. Mesurer la largeur de l'unité la plus longue en Helvetica 9pt.
      4. Ajouter padding cellulaire (10 mm) + marge de sécurité (3 mm)
         à chacune des 3 largeurs.
      5. Borner chaque largeur dans son intervalle min/max neutre.
      6. Allouer le reste à la colonne Libellé, lui-même borné.
      7. Si la somme dépasse `LARGEUR_UTILE_MM`, réduire proportionnellement
         (rare en pratique sur les graphes attendus).

    Le calibrage est **totalement neutre** vis-à-vis du régime : il
    n'examine que les longueurs littérales des chaînes, pas leur namespace.

    Args:
        etapes: Liste d'EtapeAudit à rendre dans le tableau.

    Returns:
        Liste de 4 floats représentant les largeurs en mm :
        [Code, Libellé, Valeur, Unité].
    """
    if not etapes:
        # Fallback prudent (ne devrait pas arriver — _table_etapes_plates
        # valide l'entrée non vide en amont)
        return [60.0, 51.0, 50.0, 13.0]

    # Largeurs « contenu » mesurées
    largeur_code = max(
        _mesurer_largeur_chaine_mm(e.code, "Courier", 7)
        for e in etapes
    )
    largeur_valeur = max(
        _mesurer_largeur_chaine_mm(
            _formater_valeur_pdf(e.valeur, e.unite), "Helvetica", 9)
        for e in etapes
    )
    largeur_unite = max(
        _mesurer_largeur_chaine_mm(e.unite or "", "Helvetica", 9)
        for e in etapes
    )

    # Ajout padding + marge sécurité, puis bornage
    code_mm = _borner(
        largeur_code + PADDING_CELLULAIRE_MM + MARGE_SECURITE_MM,
        BORNES_CODE_MM,
    )
    valeur_mm = _borner(
        largeur_valeur + PADDING_CELLULAIRE_MM + MARGE_SECURITE_MM,
        BORNES_VALEUR_MM,
    )
    unite_mm = _borner(
        largeur_unite + PADDING_CELLULAIRE_MM + MARGE_SECURITE_MM,
        BORNES_UNITE_MM,
    )

    # Libellé = reste de la largeur utile, lui-même borné
    libelle_mm = _borner(
        LARGEUR_UTILE_MM - code_mm - valeur_mm - unite_mm,
        BORNES_LIBELLE_MM,
    )

    # Vérification cohérence : somme ne doit pas dépasser LARGEUR_UTILE_MM.
    # Si elle dépasse (cas extrême où toutes les colonnes butent sur leur
    # min cumulé > utile), on rabote proportionnellement.
    total = code_mm + libelle_mm + valeur_mm + unite_mm
    if total > LARGEUR_UTILE_MM:
        facteur = LARGEUR_UTILE_MM / total
        code_mm *= facteur
        libelle_mm *= facteur
        valeur_mm *= facteur
        unite_mm *= facteur

    return [code_mm * mm, libelle_mm * mm, valeur_mm * mm, unite_mm * mm]


# ============================================================
# TABLEAU DES ÉTAPES PLATES — niveau racine
# ============================================================
def _table_etapes_plates(etapes: list, styles: dict,
                         titre_colonnes: tuple = ("Code", "Libellé",
                                                   "Valeur", "Unité")) -> Table:
    """Construit un `Table` reportlab à 4 colonnes pour une liste d'étapes.

    Convention de présentation :

    - Colonne 1 (Code)    : SCREAMING_SNAKE_CASE, police monospace-like
      (Courier) pour distinguer du libellé.
    - Colonne 2 (Libellé) : prose française du label de l'étape.
    - Colonne 3 (Valeur)  : valeur formatée selon l'unité
      (via `_formater_valeur_pdf`).
    - Colonne 4 (Unité)   : unité brute (`EUR`, `%`, etc.), vide si
      `unite == ""`.

    Style :

    - En-tête : fond `COULEUR_PRIMAIRE`, texte blanc, bold.
    - Lignes alternées : fond légèrement gris une ligne sur deux pour
      lisibilité sur 5–25 étapes (densité audit).
    - Bordures fines : `LINEBELOW` 0.3 pt en `COULEUR_LIGNE`.
    - Valeur alignée à droite pour les numériques.

    Args:
        etapes: Liste de `EtapeAudit` à rendre (typiquement
            `trace.racines()` au niveau 0, ou les enfants d'une étape
            parent en SP3).
        styles: Dict de styles (utilisé pour `etape_cell`).
        titre_colonnes: 4-tuple des entêtes (paramétrable pour
            internationalisation future, défaut FR).

    Returns:
        `Table` reportlab prêt à être ajouté à un flow.

    Raises:
        ValueError: Si `etapes` est vide. SP3 traitera le cas trace vide
            au niveau de l'appelant.
    """
    if not etapes:
        raise ValueError(
            "_table_etapes_plates appelée sur une liste vide. "
            "L'appelant doit vérifier `if etapes:` en amont."
        )

    # Largeurs colonnes : calibrage dynamique neutre (SP7).
    # Mesure stringWidth réelle + bornes min/max pour garantir un rendu
    # propre quels que soient le régime, la profondeur et la longueur des
    # codes/valeurs. Cf. _calibrer_col_widths() pour la stratégie.
    col_widths = _calibrer_col_widths(etapes)

    # Construction des lignes :
    # data[0]   = header
    # data[1..] = lignes d'étape + lignes d'enrichissement intercalées
    #
    # On garde trace des plages [debut, fin] de chaque étape (pour la
    # zébrure par étape et pour les SPAN colspan=4 des enrichissements).
    data: list = [list(titre_colonnes)]
    # Liste de tuples (idx_debut_etape, idx_fin_enrichissements)
    # — utilisée pour appliquer la zébrure et les SPAN.
    plages_etapes: list = []
    # Lignes d'enrichissement à fusionner colspan : liste de int (index ligne)
    indices_enrichissements: list = []

    for etape in etapes:
        idx_debut = len(data)

        # Ligne principale de l'étape
        code_para = Paragraph(
            f'<font face="Courier" size="7">{etape.code}</font>',
            styles["etape_cell"],
        )
        label_para = Paragraph(etape.label, styles["etape_cell"])
        valeur_str = _formater_valeur_pdf(etape.valeur, etape.unite)
        valeur_para = Paragraph(valeur_str, styles["etape_cell"])
        unite_para = Paragraph(etape.unite or "", styles["etape_cell"])
        data.append([code_para, label_para, valeur_para, unite_para])

        # Lignes d'enrichissement (doctrine_refs, hypothèses courtes, notes).
        # Chacune est une ligne de tableau dont la première cellule contient
        # le Paragraph d'enrichissement, et les 3 autres sont vides (fusion
        # via SPAN dans le TableStyle).
        enrichissements = _render_enrichissements_etape(etape, styles)
        for para in enrichissements:
            indices_enrichissements.append(len(data))
            data.append([para, "", "", ""])

        idx_fin = len(data) - 1
        plages_etapes.append((idx_debut, idx_fin))

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        # En-tête
        ("BACKGROUND", (0, 0), (-1, 0), COULEUR_PRIMAIRE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),  # Valeur centrée à droite
        # Corps (toutes les lignes sauf header)
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), COULEUR_TEXTE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    # Bordure fine sous chaque étape (et non sous chaque ligne) pour ne
    # pas couper le bloc enrichissement de sa ligne d'étape parente.
    style.append(("LINEBELOW", (0, 0), (-1, 0), 0.3, COULEUR_LIGNE))  # sous header
    for _, idx_fin in plages_etapes:
        style.append(("LINEBELOW", (0, idx_fin), (-1, idx_fin), 0.3, COULEUR_LIGNE))

    # Alignement valeur à droite UNIQUEMENT sur les lignes d'étape principales
    # (pas sur les lignes enrichissement qui sont colspan 4)
    for idx_debut, _ in plages_etapes:
        style.append(("ALIGN", (2, idx_debut), (2, idx_debut), "RIGHT"))
        style.append(("ALIGN", (3, idx_debut), (3, idx_debut), "LEFT"))

    # SPAN sur les lignes d'enrichissement : fusion des 4 colonnes
    for idx in indices_enrichissements:
        style.append(("SPAN", (0, idx), (3, idx)))
        # Padding réduit en haut pour rapprocher de l'étape parente
        style.append(("TOPPADDING", (0, idx), (-1, idx), 1))
        style.append(("BOTTOMPADDING", (0, idx), (-1, idx), 2))
        # Léger retrait visuel à gauche pour signaler le sous-niveau
        style.append(("LEFTPADDING", (0, idx), (0, idx), 12))

    # Zébrure par ÉTAPE (pas par ligne) : un fond légèrement gris sur
    # toute la plage de la 2e, 4e, 6e... étape pour la lisibilité audit.
    for i, (idx_debut, idx_fin) in enumerate(plages_etapes):
        if i % 2 == 1:  # 1, 3, 5… (la 2e, 4e étape…)
            style.append(("BACKGROUND", (0, idx_debut), (-1, idx_fin),
                          COULEUR_FOND_TABLEAU))

    t.setStyle(TableStyle(style))
    return t


# ============================================================
# NAVIGATION — Sommaire + signets PDF
# ============================================================
# Mécanisme reportlab pour le couplage sommaire + signets :
#
# 1. `TitreNavigable` est un Paragraph qui, lors de son `draw()` :
#    - notifie l'évènement `TOCEntry` au DocTemplate (alimente le sommaire) ;
#    - pose un signet PDF (`bookmarkPage`) ;
#    - ajoute une entrée d'outline au lecteur PDF (`addOutlineEntry`).
#
# 2. `AuditDocTemplate.afterFlowable()` intercepte ces flowables et émet
#    le `notify('TOCEntry', ...)` que le TableOfContents écoute.
#
# 3. La numérotation des pages dans le sommaire nécessite un **double
#    build** (`doc.multiBuild()` au lieu de `doc.build()`) : la première
#    passe collecte les pages, la seconde matérialise le sommaire avec
#    les bons numéros.
#
# Le `key` doit être unique par section (sinon collision dans les
# signets). On le génère via `_slugify_key()`.

def _slugify_key(*parts: str) -> str:
    """Construit une clé de signet stable à partir de fragments.

    Exemples :
        _slugify_key("racine") → "sec_racine"
        _slugify_key("strategie_T1") → "sec_strategie_t1"
        _slugify_key("strategie_T1", "module_tns") → "sec_strategie_t1_module_tns"

    Les caractères non-ASCII et la ponctuation sont remplacés par `_`.
    Le préfixe `sec_` évite toute collision avec d'éventuelles clés
    d'autres familles de signets.
    """
    import re as _re
    slug = "_".join(parts).lower()
    slug = _re.sub(r"[^a-z0-9_]+", "_", slug)
    slug = _re.sub(r"_+", "_", slug).strip("_")
    return f"sec_{slug}"


class TitreNavigable(Paragraph):
    """Paragraph qui s'inscrit au sommaire et pose un signet PDF.

    Utilisation :
        flow.append(TitreNavigable("Stratégie T1", styles["h1"],
                                   level=0, key="sec_strategie_t1"))

    Comportement au moment du `draw()` :
        - `bookmarkPage(key)` : ancre nommée sur la page courante.
        - `addOutlineEntry(text, key, level)` : entrée dans l'arbre de
          signets du lecteur PDF (Acrobat/Foxit/etc.).
        - le DocTemplate l'intercepte via `afterFlowable()` et émet
          l'évènement TOCEntry consommé par le TableOfContents.

    Conventions de niveaux (cohérence cabinet) :
        - level 0 : section principale (sous-trace de niveau 1, ou
          « Étapes du calcul (racine) »).
        - level 1 : sous-section (sous-trace de niveau 2, ou bloc interne).
    """

    def __init__(self, text: str, style, *, level: int, key: str):
        super().__init__(text, style)
        # Attributs publics consommés par AuditDocTemplate.afterFlowable
        self.toc_level = level
        self.toc_key = key
        self.toc_text = text

    def draw(self):
        # Pose du signet PDF + outline AVANT le rendu du texte
        # (sinon le signet pointerait sur la page suivante en cas de wrap)
        self.canv.bookmarkPage(self.toc_key)
        self.canv.addOutlineEntry(self.toc_text, self.toc_key,
                                  level=self.toc_level)
        super().draw()


def _styles_toc() -> list:
    """Styles d'affichage pour les 2 niveaux du sommaire.

    Niveau 0 : bold, taille 10pt, sans indentation.
    Niveau 1 : regular, taille 9pt, indentation 8 mm.

    Note SP8 : `spaceBefore` de N0 réduit de 4 → 2 pt pour absorber
    les sommaires denses (cas `comparateur_regimes` : ~33 entrées).
    Le pilote TNS (9 entrées) et Assimilé/Libéral (≤14 entrées) ne
    sont pas dégradés visuellement par cette réduction marginale.
    """
    base = getSampleStyleSheet()
    return [
        ParagraphStyle(
            "toc_n0", parent=base["Normal"],
            fontSize=10, leading=14,
            textColor=COULEUR_TEXTE, fontName="Helvetica-Bold",
            leftIndent=0, spaceBefore=2, spaceAfter=2,
        ),
        ParagraphStyle(
            "toc_n1", parent=base["Normal"],
            fontSize=9, leading=12,
            textColor=COULEUR_TEXTE, fontName="Helvetica",
            leftIndent=8*mm, spaceBefore=0, spaceAfter=2,
        ),
    ]


def _construire_sommaire() -> TableOfContents:
    """Construit l'objet TableOfContents reportlab.

    Le contenu sera renseigné automatiquement par notify(TOCEntry, ...)
    lors du premier build. Le second build matérialise le sommaire avec
    les numéros de page corrects.

    Configuration :
        - dotsMinLevel=0 : ligne pointillée entre titre et numéro de page
          à tous les niveaux (lisibilité cabinet).
        - 2 niveaux de hiérarchie (N0 bold, N1 indenté).
    """
    toc = TableOfContents()
    toc.levelStyles = _styles_toc()
    toc.dotsMinLevel = 0
    return toc


# ============================================================
# SECTION — RENDU DES ÉTAPES RACINE D'UNE TRACE
# ============================================================
def _section_etapes_racine(flow: list, styles: dict, trace: TraceAudit) -> None:
    """Ajoute au flow le tableau des étapes plates de niveau 0.

    SP2 → SP3 : devient une **section navigable** (titre inscrit au
    sommaire + signet PDF). Les étapes plates restent rendues en
    tableau 4 colonnes (parité SP2 conservée).

    Si la trace n'a aucune étape racine (cas pathologique mais possible
    pour une trace racine purement composite), affiche un message
    descriptif et passe la main aux sous-traces (rendues ensuite par
    `_section_sous_traces`).

    Args:
        flow: Liste de flowables reportlab (modifiée en place).
        styles: Dict de styles.
        trace: TraceAudit dont on rend les étapes racines.
    """
    titre = f"Étapes du calcul (niveau racine — {trace.regime})"
    flow.append(TitreNavigable(
        titre, styles["h1"], level=0,
        key=_slugify_key("racine", trace.regime),
    ))

    racines = trace.racines()
    if not racines:
        # Cas trace racine sans étape plate (rare — par ex. trace purement
        # composite dont tout le contenu est dans les sous-traces).
        flow.append(Paragraph(
            "Aucune étape de niveau racine. Le contenu de cette trace est "
            "porté par les sous-traces attachées (rendues ci-après).",
            styles["body"],
        ))
        return

    # Compteurs descriptifs (factuels, non-prescriptifs)
    nb_racines = len(racines)
    nb_avec_doctrine = sum(1 for e in racines if e.doctrine_refs)
    nb_avec_hypotheses = sum(1 for e in racines if e.hypotheses)

    bandeau = (
        f"<b>{nb_racines}</b> étape(s) au niveau racine — "
        f"{nb_avec_doctrine} avec doctrine_ref, "
        f"{nb_avec_hypotheses} avec hypotheses."
    )
    flow.append(Paragraph(bandeau, styles["body"]))
    flow.append(Spacer(1, 3*mm))

    # Tableau 4 colonnes (parité SP2) + encadrés hypothèses longues (SP4)
    _rendre_tableau_avec_encadres(flow, styles, racines)


def _rendre_tableau_avec_encadres(flow: list, styles: dict, etapes: list) -> None:
    """Helper de présentation : ajoute le tableau d'étapes + ses encadrés.

    Factorise le pattern utilisé par `_section_etapes_racine` et
    `_rendre_sous_trace_recursif` : tableau d'étapes plates suivi des
    encadrés d'hypothèses longues (≥ SEUIL_HYPOTHESE_LONGUE chars),
    repérés par le code d'étape.

    Les encadrés ne sont insérés que si au moins une hypothèse longue
    existe dans le bloc d'étapes — sinon le tableau suffit.

    Args:
        flow: Liste de flowables (modifiée en place).
        styles: Dict de styles.
        etapes: Liste d'EtapeAudit à rendre.
    """
    flow.append(_table_etapes_plates(etapes, styles))

    # Collecte des encadrés pour toutes les étapes ayant des hypothèses longues
    encadres_total: list = []
    for etape in etapes:
        encadres_total.extend(_render_encadres_hypotheses_longues(etape, styles))

    if encadres_total:
        flow.append(Spacer(1, 4*mm))
        flow.append(Paragraph(
            "<b>Hypothèses longues développées</b> "
            f"(wordings métier ≥ {SEUIL_HYPOTHESE_LONGUE} caractères, "
            "reproduits verbatim) :",
            styles["body"],
        ))
        flow.append(Spacer(1, 2*mm))
        flow.extend(encadres_total)


# ============================================================
# SECTION — RENDU RÉCURSIF DES SOUS-TRACES
# ============================================================
def _section_sous_traces(flow: list, styles: dict, trace: TraceAudit) -> None:
    """Rend récursivement toutes les sous-traces attachées à `trace`.

    Schéma S2 (Q4 arbitrage validé) :
        - Saut de page systématique avant chaque sous-trace de niveau 1
          (sections « Stratégie T1 », « Stratégie T2 », etc.).
        - Sous-traces de niveau 2 (module_tns, module_assimile…) rendues
          en continu sous leur sous-trace parente, sans PageBreak
          (cohérence cabinet : « un module = détail de sa stratégie »).
        - Récursion à profondeur arbitraire pour absorber les futures
          compositions (v3 comparateur_regimes, profondeur 5).

    Pour chaque sous-trace :
        - titre TitreNavigable (level 0 pour N1, level 1 pour N2+) ;
        - bandeau descriptif (étapes, profil_resume) ;
        - tableau des étapes plates de la sous-trace (parité SP2) ;
        - récursion sur les sous-sous-traces.

    Args:
        flow: Liste de flowables reportlab (modifiée en place).
        styles: Dict de styles.
        trace: TraceAudit racine dont on rend les sous-traces (le
            propre contenu de `trace` n'est pas re-rendu ici — c'est
            la responsabilité de `_section_etapes_racine`).
    """
    noms = list(trace.noms_sous_traces())
    if not noms:
        return  # Trace plate (pas de sous-trace) — rien à faire

    for nom in noms:
        sous_trace = trace.get_sous_trace(nom)
        # Saut de page systématique pour chaque sous-trace de niveau 1
        flow.append(PageBreak())
        _rendre_sous_trace_recursif(flow, styles, sous_trace, nom,
                                    chemin=[nom], niveau_toc=0)


def _rendre_sous_trace_recursif(flow: list, styles: dict,
                                 trace: TraceAudit, nom_attachement: str,
                                 *, chemin: list, niveau_toc: int) -> None:
    """Helper récursif pour rendre une sous-trace et ses descendantes.

    Args:
        flow: Liste de flowables.
        styles: Dict de styles.
        trace: La TraceAudit (sous-trace) à rendre.
        nom_attachement: Clé symbolique sous laquelle elle est attachée
            à sa parente (ex. "strategie_T1", "module_tns").
        chemin: Liste cumulative des noms d'attachement depuis la racine
            (sert à générer une clé de signet unique).
        niveau_toc: Niveau d'inscription au sommaire :
            - 0 : section principale (N1 dans la grammaire S2).
            - 1 : sous-section (N2 — module_tns, module_assimile, etc.).
            Au-delà de 1, on plafonne à 1 pour ne pas surcharger le
            sommaire (les profondeurs > 2 restent visibles via les
            signets mais pas dans le sommaire — voir SP8 si le pilote
            comparateur_regimes l'exige).
    """
    # Titre + signet + entrée sommaire
    titre = (
        f"Sous-trace « {nom_attachement} » — Régime {trace.regime}"
        if niveau_toc == 0
        else f"Détail « {nom_attachement} » (régime {trace.regime})"
    )
    style_titre = styles["h1"] if niveau_toc == 0 else styles["h2"]
    flow.append(TitreNavigable(
        titre, style_titre,
        level=niveau_toc,
        key=_slugify_key(*chemin),
    ))

    # Bandeau descriptif factuel
    racines = trace.racines()
    nb_etapes_totales = len(trace.etapes)
    nb_racines = len(racines)
    bandeau_lignes = [
        f"<b>Spec version :</b> {trace.spec_version}",
        f"<b>Étapes plates :</b> {nb_etapes_totales} au total, "
        f"{nb_racines} au niveau racine de cette sous-trace.",
    ]
    if trace.profil_resume:
        bandeau_lignes.append(f"<b>Profil tracé :</b> {trace.profil_resume}")
    nb_sous_sous = len(list(trace.noms_sous_traces()))
    if nb_sous_sous:
        noms_enfants = list(trace.noms_sous_traces())
        bandeau_lignes.append(
            f"<b>Sous-traces attachées :</b> {nb_sous_sous} "
            f"({', '.join(noms_enfants)})"
        )
    for ligne in bandeau_lignes:
        flow.append(Paragraph(ligne, styles["body"]))

    flow.append(Spacer(1, 3*mm))

    # Tableau des étapes plates + encadrés hypothèses longues (SP4)
    if racines:
        _rendre_tableau_avec_encadres(flow, styles, racines)
    else:
        flow.append(Paragraph(
            "Aucune étape plate à ce niveau (sous-trace purement composite).",
            styles["body"],
        ))

    # Récursion sur les sous-sous-traces (sans PageBreak en N2 — schéma S2)
    for nom_enfant in trace.noms_sous_traces():
        sous_sous = trace.get_sous_trace(nom_enfant)
        flow.append(Spacer(1, 4*mm))
        _rendre_sous_trace_recursif(
            flow, styles, sous_sous, nom_enfant,
            chemin=chemin + [nom_enfant],
            # Plafond TOC à 1 — au-delà, les signets continuent mais
            # le sommaire reste à 2 niveaux pour rester lisible.
            niveau_toc=min(niveau_toc + 1, 1),
        )


# ============================================================
# DOCUMENT TEMPLATE — Header + Footer enrichi pour PDF audit
# ============================================================
class AuditDocTemplate(BaseDocTemplate):
    """Template PDF audit avec header/footer automatiques.

    Différences avec SyntheseDocTemplate :
    - Footer enrichi avec `Audit baseline hash` (Q6d — arbitrage validé)
    - Mention `Audit PDF spec v{x}` dans le footer (traçabilité PDF)
    - Header signale `Audit MODE_AUDIT — {client}` (pas « Synthèse »)
    """

    def __init__(self, filename, *,
                 cabinet_nom: str,
                 client_nom: str,
                 niveau_confiance: str,
                 doctrine_version: str,
                 doctrine_date: str,
                 audit_pdf_spec_version: str,
                 baseline_hash: str,
                 **kwargs):
        self.cabinet_nom = cabinet_nom
        self.client_nom = client_nom
        # Normalisation des niveaux legacy (« Déclaratif » → « Conformité renforcée »).
        # Garantit qu'aucun terme historique ne ressort dans le PDF audit.
        self.niveau_confiance = _normaliser_niveau(niveau_confiance)
        self.doctrine_version = doctrine_version
        self.doctrine_date = doctrine_date
        self.audit_pdf_spec_version = audit_pdf_spec_version
        self.baseline_hash = baseline_hash

        BaseDocTemplate.__init__(
            self, filename, pagesize=A4,
            leftMargin=18*mm, rightMargin=18*mm,
            topMargin=22*mm, bottomMargin=22*mm,  # +2 mm vs synthèse pour footer 2 lignes
            **kwargs,
        )
        frame = Frame(self.leftMargin, self.bottomMargin,
                      self.width, self.height, id="normal")
        template = PageTemplate(id="main", frames=[frame],
                                onPage=self._draw_decorations)
        self.addPageTemplates([template])

    def _draw_decorations(self, canvas: Canvas, doc):
        """Header + footer sur chaque page."""
        canvas.saveState()

        # === HEADER ===
        # Trait coloré en haut (charte commune)
        canvas.setFillColor(COULEUR_PRIMAIRE)
        canvas.rect(0, A4[1] - 8*mm, A4[0], 8*mm, fill=1, stroke=0)
        # Cabinet à gauche
        canvas.setFillColor(COULEUR_TEXTE)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(18*mm, A4[1] - 14*mm, self.cabinet_nom)
        # « Audit — {client} » à droite (différencie du PDF synthèse,
        # distinction documentaire seulement, pas graphique — cf. Q6a)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(COULEUR_GRIS)
        canvas.drawRightString(A4[0] - 18*mm, A4[1] - 14*mm,
                               f"Audit MODE_AUDIT — {self.client_nom}")

        # === FOOTER ===
        # Trait fin séparateur
        canvas.setStrokeColor(COULEUR_LIGNE)
        canvas.setLineWidth(0.5)
        canvas.line(18*mm, 18*mm, A4[0] - 18*mm, 18*mm)

        canvas.setFillColor(COULEUR_GRIS)
        canvas.setFont("Helvetica", 7)
        date_str = datetime.now().strftime("%d/%m/%Y")

        # Ligne 1 : doctrine + niveau + page
        canvas.drawString(18*mm, 14*mm, TRACE_DOCTRINALE_FOOTER)
        canvas.drawCentredString(A4[0]/2, 14*mm,
                                 f"Niveau : {self.niveau_confiance}")
        canvas.drawRightString(A4[0] - 18*mm, 14*mm,
                               f"Page {canvas.getPageNumber()} — {date_str}")

        # Ligne 2 : traçabilité audit (hash + version PDF audit spec)
        # Format gris discret (arbitrage Q6d).
        canvas.setFont("Helvetica", 6)
        canvas.drawString(
            18*mm, 10*mm,
            f"Audit baseline hash : {self.baseline_hash}",
        )
        canvas.drawRightString(
            A4[0] - 18*mm, 10*mm,
            f"Audit PDF spec v{self.audit_pdf_spec_version}",
        )

        # Ligne 3 : mention de cadre (italique)
        canvas.setFont("Helvetica-Oblique", 6)
        canvas.drawCentredString(
            A4[0]/2, 10*mm,
            "Document d'audit à usage cabinet — Traçabilité MODE_AUDIT.",
        )

        canvas.restoreState()

    def afterFlowable(self, flowable):
        """Hook BaseDocTemplate : intercepte TitreNavigable pour le sommaire.

        À chaque flowable rendu, si c'est un `TitreNavigable`, on émet
        un évènement `TOCEntry` consommé par le `TableOfContents` ajouté
        au flow. Cette boucle de feedback nécessite un double build
        (`multiBuild`) : la première passe alimente le TOC, la seconde
        matérialise le sommaire avec les bons numéros de page.
        """
        if isinstance(flowable, TitreNavigable):
            self.notify("TOCEntry", (
                flowable.toc_level,
                flowable.toc_text,
                self.page,
                flowable.toc_key,
            ))


# ============================================================
# COMPTAGE DES KPIs DE COUVERTURE (SP5)
# ============================================================
# Comptage récursif sur la TraceAudit pour produire les 4 indicateurs
# du panel KPI cabinet (couverture). Aucune logique métier ici — pure
# présentation. Voir _table_kpis_couverture() pour le rendu.
def _compter_kpis_trace(trace: TraceAudit) -> dict:
    """Compte les 4 KPIs de présentation pour la couverture.

    Convention : on n'inclut pas la « trace racine » dans le compte des
    sous-traces (seules les sous-traces attachées sont comptées —
    `noms_sous_traces()` au sens spec 1.1.0).

    Conventions de comptage :
        - `etapes_total` : somme des `len(t.etapes)` sur la racine et
          toutes les sous-traces (profondeur arbitraire).
        - `sous_traces_total` : nombre de sous-traces attachées
          (profondeur arbitraire), hors racine.
        - `doctrine_refs_distinctes` : taille du set des refs uniques
          rencontrées sur tout le graphe.
        - `hypotheses_total` : somme des `len(e.hypotheses)` sur toutes
          les étapes du graphe.

    Args:
        trace: TraceAudit racine.

    Returns:
        Dict avec 4 clés : `etapes_total`, `sous_traces_total`,
        `doctrine_refs_distinctes`, `hypotheses_total`.
    """
    etapes_total = 0
    sous_traces_total = 0
    doctrine_refs: set = set()
    hypotheses_total = 0

    def _visiter(t: TraceAudit) -> None:
        nonlocal etapes_total, sous_traces_total, hypotheses_total
        for etape in t.etapes:
            etapes_total += 1
            for ref in etape.doctrine_refs:
                doctrine_refs.add(ref)
            hypotheses_total += len(etape.hypotheses)
        for _, sous in t.sous_traces.items():
            sous_traces_total += 1
            _visiter(sous)

    _visiter(trace)
    return {
        "etapes_total": etapes_total,
        "sous_traces_total": sous_traces_total,
        "doctrine_refs_distinctes": len(doctrine_refs),
        "hypotheses_total": hypotheses_total,
    }


def _table_kpis_couverture(kpis: dict, styles: dict) -> Table:
    """Construit un panel KPI 2×2 sobre pour la couverture.

    Style cabinet EY/KPMG-like :
    - 2 colonnes, 2 lignes (4 KPIs).
    - Mini-label gris au-dessus du chiffre.
    - Chiffre en gros, sobre, sans icône.
    - Fond très discret (gris très clair), bordure fine.
    - Pas d'effets visuels (gradients, ombres, etc.).

    Args:
        kpis: Dict produit par `_compter_kpis_trace`.
        styles: Dict de styles audit.

    Returns:
        Table reportlab 2×2 prêt à insérer dans le flow.
    """
    # Style local : libellé KPI (gris discret, 8pt)
    style_label_kpi = ParagraphStyle(
        "kpi_label_couverture", parent=styles["body"],
        fontSize=8, leading=10, textColor=COULEUR_GRIS,
        fontName="Helvetica", alignment=TA_LEFT, spaceAfter=2,
    )
    # Style local : valeur KPI (sobre, 14pt Bold, couleur texte)
    style_valeur_kpi = ParagraphStyle(
        "kpi_valeur_couverture", parent=styles["body"],
        fontSize=14, leading=17, textColor=COULEUR_TEXTE,
        fontName="Helvetica-Bold", alignment=TA_LEFT, spaceAfter=0,
    )

    def _cellule(label: str, valeur: int):
        """Construit une cellule KPI (label + valeur empilés)."""
        return [
            Paragraph(label, style_label_kpi),
            Paragraph(f"{valeur:,}".replace(",", " "), style_valeur_kpi),
        ]

    # Layout 2×2 : on emboîte chaque cellule dans son propre Paragraph
    # via une liste, ce que Table reportlab accepte (« cellule = flowable
    # ou liste de flowables »).
    data = [
        [_cellule("Étapes tracées", kpis["etapes_total"]),
         _cellule("Sous-traces", kpis["sous_traces_total"])],
        [_cellule("Références doctrinales", kpis["doctrine_refs_distinctes"]),
         _cellule("Hypothèses", kpis["hypotheses_total"])],
    ]

    # Largeurs : 2 colonnes égales sur 100 mm utiles (laisse une marge
    # naturelle sur la couverture, pas pleine largeur — c'est plus sobre)
    col_widths = [50*mm, 50*mm]

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COULEUR_FOND_TABLEAU),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        # Ligne fine de séparation interne (verticale + horizontale)
        ("LINEAFTER", (0, 0), (0, -1), 0.3, COULEUR_LIGNE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.3, COULEUR_LIGNE),
        # Bordure externe très discrète
        ("BOX", (0, 0), (-1, -1), 0.3, COULEUR_LIGNE),
    ]))
    return t


# ============================================================
# BANDEAU D'INTRODUCTION DU SOMMAIRE (SP5)
# ============================================================
# Texte cabinet validé (SP5-Q3). Pédagogique/méthodologique — distinct
# des disclaimers juridiques (qui restent en clôture).
BANDEAU_INTRO_SOMMAIRE = (
    "Cette restitution structurée reproduit le graphe de calcul exécuté "
    "par le moteur d'arbitrage. Chaque étape est identifiée par un code "
    "stable et documentée avec ses valeurs calculées, hypothèses "
    "appliquées et références doctrinales associées. Les sections sont "
    "navigables via les signets PDF et le sommaire."
)


# ============================================================
# COUVERTURE (minimaliste SP1, enrichie SP5)
# ============================================================
def _section_couverture(flow: list, styles: dict, *,
                        trace: TraceAudit,
                        client_nom: str,
                        cabinet_nom: str,
                        expert_comptable: str,
                        niveau_confiance: str,
                        doctrine_version: str,
                        doctrine_date: str,
                        audit_pdf_spec_version: str,
                        baseline_hash: str) -> None:
    """Ajoute la couverture au flow.

    SP1 : titre + sous-titre + bloc méta + traçabilité + profil.
    SP5 : ajout d'un panel KPI 2×2 discret en bas de couverture
    (4 indicateurs : étapes, sous-traces, doctrine_refs, hypothèses).
    """
    flow.append(Paragraph("Audit MODE_AUDIT", styles["title"]))
    flow.append(Paragraph(
        f"Restitution structurée de la trace de calcul — Régime "
        f"{trace.regime}",
        styles["subtitle"],
    ))
    flow.append(Spacer(1, 8*mm))

    # Bloc méta
    flow.append(Paragraph("Identification de la mission", styles["h2"]))
    meta_lignes = [
        f"<b>Cabinet :</b> {cabinet_nom}",
        f"<b>Client :</b> {client_nom}",
    ]
    if expert_comptable:
        meta_lignes.append(f"<b>Expert-comptable :</b> {expert_comptable}")
    meta_lignes += [
        f"<b>Date d'édition :</b> {datetime.now().strftime('%d/%m/%Y')}",
        f"<b>Niveau de confiance :</b> {_normaliser_niveau(niveau_confiance)}",
    ]
    for ligne in meta_lignes:
        flow.append(Paragraph(ligne, styles["body"]))

    flow.append(Spacer(1, 6*mm))

    # Bloc traçabilité (toutes les versions visibles)
    flow.append(Paragraph("Traçabilité doctrinale et technique", styles["h2"]))
    traca_lignes = [
        f"<b>Doctrine appliquée :</b> v{doctrine_version} "
        f"(figement {doctrine_date})",
        f"<b>Spec MODE_AUDIT (graphe) :</b> v{trace.spec_version}",
        f"<b>Spec PDF audit (renderer) :</b> v{audit_pdf_spec_version}",
        f"<b>Hash baseline :</b> {baseline_hash}",
    ]
    for ligne in traca_lignes:
        flow.append(Paragraph(ligne, styles["body"]))

    if trace.profil_resume:
        flow.append(Spacer(1, 4*mm))
        flow.append(Paragraph("Profil tracé", styles["h2"]))
        flow.append(Paragraph(trace.profil_resume, styles["body"]))

    # SP5 — Panel KPI cabinet, 2×2 sobre
    flow.append(Spacer(1, 6*mm))
    flow.append(Paragraph("Indicateurs de couverture de l'audit",
                          styles["h2"]))
    kpis = _compter_kpis_trace(trace)
    flow.append(_table_kpis_couverture(kpis, styles))


# ============================================================
# DISCLAIMERS (annexe simple SP1)
# ============================================================
def _section_disclaimers(flow: list, styles: dict) -> None:
    """Ajoute les disclaimers obligatoires v1.0.1 en fin de PDF audit.

    Reprise stricte de la discipline `ui/disclaimers.py` (cf. Q6e). Pas
    de disclaimer additionnel spécifique à l'audit en v1.0.0.
    """
    flow.append(Paragraph("Avertissements et primauté cabinet", styles["h1"]))
    flow.append(Paragraph(DISCLAIMER_PRIMAUTE_CABINET, styles["callout"]))
    flow.append(Spacer(1, 4*mm))
    flow.append(Paragraph(DISCLAIMER_AVERTISSEMENT_FINAL, styles["callout"]))


# ============================================================
# POINT D'ENTRÉE PUBLIC
# ============================================================
def generer_pdf_audit(
    trace: TraceAudit,
    *,
    cabinet_nom: str = "Cabinet d'expertise comptable",
    client_nom: str = "Client",
    expert_comptable: str = "",
    niveau_confiance: str = "Avancé",
    doctrine_version: str = "1.0.1",
    audit_pdf_spec_version: str = AUDIT_PDF_SPEC_VERSION,
    doctrine_date: str | None = None,
    baseline_hash: str = BASELINE_HASH_DEFAUT,
) -> bytes:
    """Génère un PDF audit-ready à partir d'une `TraceAudit`.

    Le PDF audit est un **produit documentaire distinct** du PDF
    synthèse : il restitue le graphe d'étapes complet (étapes plates +
    sous-traces récursives + doctrine_refs + hypotheses + notes), avec
    sommaire navigable et signets PDF.

    Args:
        trace: La `TraceAudit` à formater. Doit être une trace racine
            (les sous-traces internes sont rendues récursivement). Aucune
            modification de la trace n'est faite (lecture seule).
        cabinet_nom: Nom du cabinet en charge de la mission (header).
        client_nom: Nom du client (header).
        expert_comptable: Nom de l'expert-comptable signataire (couverture).
        niveau_confiance: Niveau de confiance affiché. Les alias legacy
            sont silencieusement normalisés (« Déclaratif » → « Conformité renforcée »).
        doctrine_version: Version de la doctrine appliquée (footer).
        audit_pdf_spec_version: Version de la spec du renderer PDF audit
            (footer). Par défaut, valeur courante `AUDIT_PDF_SPEC_VERSION`.
        doctrine_date: Date de figement de la doctrine. Si `None`,
            résolution interne automatique : date du jour (cohérence avec
            la convention « doctrine vivante au jour d'édition »).
        baseline_hash: Hash baseline à inscrire en pied de page (Q6d).
            Par défaut, valeur courante v1.6 (`BASELINE_HASH_DEFAUT`).

    Returns:
        Bytes du PDF généré.

    Architecture du PDF (SP3) :
        1. Couverture (mission + traçabilité 4 versions)
        2. Sommaire navigable (TableOfContents 2 niveaux, signets PDF)
        3. Étapes racine (tableau 4 colonnes — parité SP2)
        4. Sous-traces récursives (schéma S2 : saut de page systématique
           par sous-trace N1, sous-traces N2+ en continu)
        5. Disclaimers v1.0.1 (Primauté cabinet + Avertissement final)

        Le PDF est généré via `multiBuild()` (double passe) pour que le
        sommaire affiche les numéros de page corrects.
    """
    # Résolution paresseuse de doctrine_date (ajustement B validé)
    if doctrine_date is None:
        doctrine_date = datetime.now().strftime("%d/%m/%Y")

    buffer = io.BytesIO()
    doc = AuditDocTemplate(
        buffer,
        cabinet_nom=cabinet_nom,
        client_nom=client_nom,
        niveau_confiance=niveau_confiance,
        doctrine_version=doctrine_version,
        doctrine_date=doctrine_date,
        audit_pdf_spec_version=audit_pdf_spec_version,
        baseline_hash=baseline_hash,
    )
    styles = _build_audit_styles()

    flow: list = []

    # 1. Couverture
    _section_couverture(
        flow, styles,
        trace=trace,
        client_nom=client_nom,
        cabinet_nom=cabinet_nom,
        expert_comptable=expert_comptable,
        niveau_confiance=niveau_confiance,
        doctrine_version=doctrine_version,
        doctrine_date=doctrine_date,
        audit_pdf_spec_version=audit_pdf_spec_version,
        baseline_hash=baseline_hash,
    )

    # 2. Sommaire (SP3) — page dédiée, alimentée par notify(TOCEntry, ...)
    #    + bandeau d'introduction pédagogique (SP5).
    flow.append(PageBreak())
    flow.append(Paragraph("Sommaire", styles["h1"]))
    flow.append(Spacer(1, 3*mm))
    # SP5 — Bandeau d'introduction cabinet (pédagogique, non juridique).
    # Texte distinct des disclaimers v1.0.1 conservés en clôture.
    flow.append(Paragraph(BANDEAU_INTRO_SOMMAIRE, styles["callout"]))
    flow.append(Spacer(1, 5*mm))
    flow.append(_construire_sommaire())

    # 3. Étapes plates de niveau racine (SP2 — section navigable depuis SP3)
    flow.append(PageBreak())
    _section_etapes_racine(flow, styles, trace)

    # 4. Sous-traces récursives (SP3) — schéma S2, saut de page par N1
    _section_sous_traces(flow, styles, trace)

    # 5. SP4 ajoutera ici les enrichissements hypotheses/doctrine_refs
    # 6. SP5 enrichira la couverture

    # N. Disclaimers (toujours en clôture)
    flow.append(PageBreak())
    _section_disclaimers(flow, styles)

    # multiBuild : double passe pour matérialiser le sommaire avec les
    # numéros de page corrects (cf. TitreNavigable + afterFlowable).
    doc.multiBuild(flow)
    return buffer.getvalue()


# ============================================================
# EXPORTS PUBLICS
# ============================================================
__all__ = [
    "AUDIT_PDF_SPEC_VERSION",
    "AUDIT_PDF_DATE",
    "BASELINE_HASH_DEFAUT",
    "AuditDocTemplate",
    "generer_pdf_audit",
    # Helpers internes exposés pour les tests SP6 et pour SP3+
    "_formater_valeur_pdf",
    "_table_etapes_plates",
    "_section_etapes_racine",
    # SP3 : navigation et récursion sous-traces
    "TitreNavigable",
    "_slugify_key",
    "_construire_sommaire",
    "_section_sous_traces",
    # SP4 : enrichissements (doctrine_refs, hypotheses, notes, overrides)
    "SEUIL_HYPOTHESE_LONGUE",
    "_format_hyp_valeur",
    "_render_enrichissements_etape",
    "_render_encadres_hypotheses_longues",
    "_rendre_tableau_avec_encadres",
    # SP5 : couverture enrichie + bandeau sommaire
    "BANDEAU_INTRO_SOMMAIRE",
    "_compter_kpis_trace",
    "_table_kpis_couverture",
    # SP7 : calibrage dynamique des largeurs de colonnes
    "_calibrer_col_widths",
    "_mesurer_largeur_chaine_mm",
    "LARGEUR_UTILE_MM",
    "BORNES_CODE_MM",
    "BORNES_VALEUR_MM",
    "BORNES_UNITE_MM",
    "BORNES_LIBELLE_MM",
]
