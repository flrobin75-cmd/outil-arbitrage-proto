"""
ui/disclaimers.py — Disclaimers de présentation (PDF, UI)

Ce module centralise les disclaimers **de présentation** affichés dans les PDF
cabinet et dans l'UI Streamlit. Ils répondent à des obligations de communication
(primauté cabinet, mention AMF, avertissement final) et **n'interviennent pas
dans les calculs**.

╔════════════════════════════════════════════════════════════════════╗
║  RÈGLE DE PARTAGE — Phase B.2.5                                    ║
║                                                                    ║
║  Ce module contient UNIQUEMENT les disclaimers de présentation.    ║
║                                                                    ║
║  Les ALERTES MÉTIER (alertes émises pendant le calcul et qui       ║
║  modifient ou conditionnent les résultats restitués) restent       ║
║  dans `strategy/` car elles sont nécessaires aux moteurs :         ║
║                                                                    ║
║    - strategy.liberal.ALERTE_BNC_VS_SEL                            ║
║    - strategy.liberal.ALERTE_L4_V2                                 ║
║    - strategy.comparateur_regimes.DISCLAIMER_CHANGEMENT_REGIME     ║
║    - strategy.comparateur_regimes.DISCLAIMER_COMPARABILITE         ║
║    - strategy.comparateur_regimes.NOTE_RADAR_INTRA_REGIME          ║
║                                                                    ║
║  Pour ajouter un nouveau disclaimer, trancher d'abord :            ║
║    - sert-il à un calcul ou à filtrer un résultat ? → strategy/    ║
║    - est-il purement informatif côté lecteur ? → ui/disclaimers.py ║
╚════════════════════════════════════════════════════════════════════╝

Versioning : aligné sur DOCTRINE_VERSION (doctrine.py).
"""

from doctrine import DOCTRINE_VERSION, DOCTRINE_DATE


# ============================================================
# VERSIONING EXPLICITE DES DISCLAIMERS
# ============================================================
DISCLAIMERS_VERSION = "1.0.1"
DISCLAIMERS_DATE = "2026-05-01"
DISCLAIMERS_DOCTRINE_LIEN = DOCTRINE_VERSION  # toujours aligné


# ============================================================
# DISCLAIMERS PERMANENTS — Présentation
# ============================================================

DISCLAIMER_PRIMAUTE_CABINET = (
    "<b>Primauté de l'analyse cabinet.</b> Cet outil produit un cadrage "
    "indicatif. Toute décision d'arbitrage de rémunération, de "
    "structuration juridique ou de mise en œuvre d'un dispositif "
    "d'épargne doit être validée par le cabinet en charge du dossier, "
    "qui dispose de la vue complète sur la situation du dirigeant, "
    "sa société, sa trésorerie et ses objectifs patrimoniaux."
)
"""Disclaimer principal — primauté du cabinet sur l'outil.

Obligatoire dans chaque PDF généré, en page d'annexe.
Verrouillé par test_pdf_render_all_regimes.py.
"""


DISCLAIMER_AMF_COMPARATEUR_PATRIMONIAL = (
    "<b>Comparateur patrimonial — information AMF.</b> La comparaison "
    "d'enveloppes patrimoniales est présentée à titre indicatif. Elle ne "
    "constitue ni un conseil en investissement, ni une recommandation de "
    "souscription, ni une analyse d'adéquation au sens de la directive "
    "MIF II / AMF. Le choix d'une enveloppe d'épargne ou d'assurance doit "
    "être validé par un conseiller en investissements financiers (CIF) ou "
    "un courtier en assurance habilité."
)
"""Disclaimer AMF pour le Comparateur patrimonial.

Obligatoire dans chaque PDF généré contenant le Comparateur patrimonial.
Verrouillé par test_pdf_render_all_regimes.py.
"""


DISCLAIMER_AVERTISSEMENT_FINAL = (
    "Ce document constitue un cadrage indicatif et un outil d'aide à la "
    "décision. Il n'engage pas la responsabilité de l'éditeur du logiciel "
    "et ne saurait se substituer à l'analyse complémentaire recommandée "
    "du cabinet, au regard de la situation complète du dirigeant et de "
    "sa société."
)
"""Avertissement final.

Obligatoire dans chaque PDF généré, en bas de page d'annexe.
Verrouillé par test_pdf_render_all_regimes.py.
"""


# ============================================================
# TRACE DOCTRINALE (B.2.5)
# ============================================================

TRACE_DOCTRINALE_FOOTER = f"Doctrine v{DOCTRINE_VERSION} — France 2026"
"""Mention courte affichée dans le footer enrichi (option A).

Présentée à gauche du footer, à côté de la date doctrine et de la mention
« Outil indicatif à usage professionnel ».
"""


TRACE_DOCTRINALE_ANNEXE_INTRO = (
    f"<b>Cadre méthodologique appliqué.</b> Cette synthèse repose sur la "
    f"doctrine métier <b>v{DOCTRINE_VERSION}</b> (mise à jour au "
    f"<b>{DOCTRINE_DATE}</b>), calée sur les paramètres fiscaux et sociaux "
    f"applicables en France en 2026. La doctrine fixe les hypothèses "
    f"retenues pour le PASS, le barème IR, le PFU, les plafonds d'épargne "
    f"salariale, les seuils CEHR/CDHR, ainsi que les conventions de calcul "
    f"transverses (TNS hors agrégation T4, alerte BNC/SEL, niveaux de "
    f"précision)."
)
"""Intro de l'annexe enrichie (option C) — trace doctrinale détaillée.

Insérée en début d'annexe « Cadre méthodologique » dans chaque PDF.
"""


def trace_doctrinale_annexe_complete(niveau_confiance: str) -> str:
    """Texte d'annexe enrichi (option C) — fiche méthodo consultable.

    Renvoie une seule chaîne HTML (compatible ReportLab Paragraph) qui décrit :
    - la version de doctrine
    - le niveau de précision du module générant le PDF
    - la liste des 4 niveaux disponibles
    - le rappel des garde-fous structurels

    Args:
        niveau_confiance: niveau du PDF en cours (ex. "Conformité renforcée").
    """
    return (
        f"<b>Cadre méthodologique appliqué.</b> Doctrine "
        f"v{DOCTRINE_VERSION} (mise à jour au {DOCTRINE_DATE}), "
        f"paramètres France 2026.<br/><br/>"
        f"<b>Niveau de précision du présent module :</b> "
        f"<i>{niveau_confiance}</i>.<br/><br/>"
        f"<b>Les quatre niveaux de précision v1.0.1 :</b><br/>"
        f"• <b>Conformité renforcée</b> — modules calibrés sur les "
        f"règles fiscales et sociales applicables au 01/01/2026 "
        f"(CEHR, CDHR, plafonnement QF). Précision suffisante pour la "
        f"préparation des obligations fiscales, sous validation cabinet.<br/>"
        f"• <b>Avancé</b> — modèle complet consolidant les modules "
        f"de conformité renforcée. Lecture consolidée prudente des "
        f"plafonds sociaux. Adapté à l'arbitrage stratégique et à la "
        f"formalisation de la mission cabinet.<br/>"
        f"• <b>Cadrage</b> — modèle simplifié sans CEHR/CDHR ni "
        f"plafonnement QF, destiné à comparer rapidement plusieurs "
        f"équilibres. Pour les calculs destinés aux obligations fiscales, "
        f"utiliser les modules de conformité renforcée.<br/>"
        f"• <b>Indicatif</b> — projection reposant sur des hypothèses "
        f"externes (rendements, fiscalité future, durée de placement), "
        f"à ajuster selon le dossier. Ne constitue pas un engagement "
        f"de performance.<br/><br/>"
        f"<b>Garde-fous structurels permanents :</b><br/>"
        f"• <b>TNS</b> — pas d'agrégation du net dirigeant immédiat "
        f"avec le bénéfice retenu en société : deux indicateurs séparés.<br/>"
        f"• <b>Libéral</b> — alerte de comparabilité BNC/SEL "
        f"systématique en présence de niveaux mixtes ; aucun « régime "
        f"recommandé » n'est jamais affiché.<br/>"
        f"• <b>Vocabulaire</b> — l'outil émet un cadrage indicatif et "
        f"jamais une recommandation, une optimisation, ou une garantie "
        f"de performance."
    )


# ============================================================
# RECENSEMENT — Listes pour audits
# ============================================================

DISCLAIMERS_PRESENTATION = (
    DISCLAIMER_PRIMAUTE_CABINET,
    DISCLAIMER_AMF_COMPARATEUR_PATRIMONIAL,
    DISCLAIMER_AVERTISSEMENT_FINAL,
)
"""Tuple de tous les disclaimers de présentation, pour itération en tests."""


__all__ = [
    # Versioning
    "DISCLAIMERS_VERSION",
    "DISCLAIMERS_DATE",
    "DISCLAIMERS_DOCTRINE_LIEN",
    # Disclaimers permanents
    "DISCLAIMER_PRIMAUTE_CABINET",
    "DISCLAIMER_AMF_COMPARATEUR_PATRIMONIAL",
    "DISCLAIMER_AVERTISSEMENT_FINAL",
    # Trace doctrinale B.2.5
    "TRACE_DOCTRINALE_FOOTER",
    "TRACE_DOCTRINALE_ANNEXE_INTRO",
    "trace_doctrinale_annexe_complete",
    # Recensement
    "DISCLAIMERS_PRESENTATION",
]
