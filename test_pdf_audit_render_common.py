"""
test_pdf_audit_render_common.py — Helper commun pour les tests PDF audit-ready.

Factorise les assertions **neutres vis-à-vis du régime** utilisées par :
- test_pdf_audit_render_tns.py       (pilote de référence, SP1-SP5, 93 contrôles)
- test_pdf_audit_render_assimile.py  (extension SP7)
- test_pdf_audit_render_liberal.py   (extension SP7, couvre SELARL + SELAS)

Ce helper EST le contrat de neutralité structurelle du renderer :
chaque test régime appelle les mêmes vérifications, et le renderer doit
les satisfaire pour n'importe quelle `TraceAudit` valide. Si une
assertion devient régime-spécifique, c'est qu'elle ne devrait PAS être
ici — elle appartient au test dédié du régime concerné.

Conventions :
- Toutes les fonctions ici prennent un `cas_test` (dataclass-like dict)
  contenant les éléments communs : trace, pdf_bytes, texte, etc.
- Aucune fonction ne fait de `if regime == "...":` — elles itèrent
  sur ce que la trace expose (sous-traces, étapes, doctrine_refs,
  hypothèses, notes).
- Les fonctions retournent (nb_ok, nb_ko, failures) et n'impriment pas
  directement — l'orchestration de l'affichage reste au test appelant.

Usage type dans un test régime :

    from test_pdf_audit_render_common import (
        AssertionRunner, faire_cas_test,
        section_pdf_valide, section_no_declaratif,
        section_14_patterns_non_prescriptifs,
        section_kpis_couverture,
        section_bandeau_intro_sommaire,
        section_signets_hierarchises,
        section_sommaire_pagine,
    )

    runner = AssertionRunner()
    cas = faire_cas_test(trace, pdf_bytes)
    section_pdf_valide(runner, cas)
    section_no_declaratif(runner, cas)
    ...
    runner.synthese()
"""

import io
import re
from dataclasses import dataclass

import pdfplumber

try:
    import pypdf
    PYPDF_DISPONIBLE = True
except ImportError:  # pragma: no cover
    PYPDF_DISPONIBLE = False

from core.audit import TraceAudit
from ui.pdf_audit_export import (
    _compter_kpis_trace,
    BANDEAU_INTRO_SOMMAIRE,
)


# ============================================================
# DATA TYPES
# ============================================================
@dataclass
class CasTest:
    """Conteneur léger des éléments partagés par toutes les assertions.

    Attributes:
        trace: La TraceAudit racine rendue dans le PDF.
        pdf_bytes: Le PDF généré.
        texte: Texte brut extrait via pdfplumber.
        texte_norm: Texte normalisé (whitespace → espace simple) pour
            comparaisons robustes aux wraps PDF.
        kpis: Dict des 4 KPIs comptés sur la trace.
        regime_attendu: Libellé exact du régime que l'on doit retrouver
            dans le titre de couverture (ex. « TNS », « Assimilé »).
        nb_sous_traces_n1: Nombre attendu de sous-traces de niveau 1
            (utilisé pour vérifier la présence dans le sommaire).
    """
    trace: TraceAudit
    pdf_bytes: bytes
    texte: str
    texte_norm: str
    kpis: dict
    regime_attendu: str
    nb_sous_traces_n1: int


def faire_cas_test(trace: TraceAudit, pdf_bytes: bytes,
                   regime_attendu: str) -> CasTest:
    """Construit un CasTest complet à partir d'une trace + PDF.

    Centralise les opérations communes (extraction pdfplumber, comptage
    KPIs, normalisation texte) pour ne pas les répéter dans chaque test.

    Args:
        trace: TraceAudit racine rendue dans le PDF.
        pdf_bytes: PDF généré.
        regime_attendu: Libellé exact à chercher dans la couverture
            (« TNS », « Assimilé », « Libéral », etc.).

    Returns:
        CasTest prêt à être passé aux fonctions section_*.
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        texte = "\n".join((p.extract_text() or "") for p in pdf.pages)
    texte_norm = re.sub(r"\s+", " ", texte)
    kpis = _compter_kpis_trace(trace)
    nb_sous_traces_n1 = len(trace.noms_sous_traces())
    return CasTest(
        trace=trace, pdf_bytes=pdf_bytes,
        texte=texte, texte_norm=texte_norm,
        kpis=kpis, regime_attendu=regime_attendu,
        nb_sous_traces_n1=nb_sous_traces_n1,
    )


class AssertionRunner:
    """Petit runner d'assertions identique au pattern du test pilote TNS.

    Permet à plusieurs tests d'utiliser la même mécanique de comptage
    (ok / ko / failures) sans dépendance globale.
    """

    def __init__(self):
        self.nb_ok = 0
        self.nb_ko = 0
        self.failures: list = []

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        """Enregistre un contrôle, affiche le résultat."""
        suffix = f"  [{detail}]" if detail and not condition else ""
        symbole = "✓" if condition else "✗"
        print(f"  {symbole} {label}{suffix}")
        if condition:
            self.nb_ok += 1
        else:
            self.nb_ko += 1
            self.failures.append(label + (f"  [{detail}]" if detail else ""))

    def section(self, titre: str) -> None:
        """Affiche un en-tête de section."""
        print()
        print("=" * 95)
        print(f"  {titre}")
        print("=" * 95)

    def synthese(self, nom_test: str) -> int:
        """Affiche la synthèse et retourne le code de sortie (0/1)."""
        print()
        print("=" * 95)
        print("  SYNTHÈSE")
        print("=" * 95)
        print(f"  Contrôles OK     : {self.nb_ok}")
        print(f"  Contrôles KO     : {self.nb_ko}")
        print()
        if self.nb_ko == 0:
            print(f"  ✓ {nom_test} PASS")
            return 0
        else:
            print(f"  ✗ {nom_test} FAIL :")
            for f in self.failures:
                print(f"    - {f}")
            return 1


# ============================================================
# PATTERNS NON-PRESCRIPTIFS — réimport depuis le test pilote
# ============================================================
# Ces patterns sont la doctrine §6.2 figée. Toute extension du
# vocabulaire interdit doit se faire dans `semantic_guardrails.py`
# (référence unique), pas ici.
PATTERNS_NON_PRESCRIPTIFS = [
    (r'\boptim\w*\b', 'optimal/optimisation'),
    (r'\bmeilleur(?:e|s|es)?\b', 'meilleur'),
    (r'\bgagnant(?:e|s|es)?\b', 'gagnant'),
    (r'\bperdant(?:e|s|es)?\b', 'perdant'),
    (r'\bavantageu(?:x|se|ses)\b', 'avantageux'),
    (r'\brecommand(?:é|ée|és|ées|er|ation|ations)\b', 'recommandation'),
    (r'\bpréconis(?:é|ée|er|ation)\b', 'préconisation'),
    (r'\bconseill(?:é|ée|er)\b', 'conseil'),
    (r'\bidéal(?:e|s|es)?\b', 'idéal'),
    (r'\bparfait(?:e|s|es)?\b', 'parfait'),
    (r'\bsupérieur(?:e|s|es)?\b', 'supérieur'),
    (r'\binférieur(?:e|s|es)?\b', 'inférieur'),
    (r'\bprioritaire(?:s)?\b', 'prioritaire'),
    (r'\bprivilégi\w*\b', 'privilégier'),
]

# Exceptions whitelistées : termes qui peuvent apparaître légitimement
# dans le PDF (disclaimers v1.0.1 figés, mentions de cadre cabinet,
# wordings anti-prescriptifs explicites portés par les traces).
#
# Discipline :
# - Toute exception ajoutée ici doit pointer une chaîne **exacte**
#   issue d'une trace MODE_AUDIT existante, où le pattern apparaît
#   dans un contexte qui est lui-même non-prescriptif (mention de
#   « non recommandée », « pas de recommandation automatique », etc.).
# - L'objectif est de ne pas masquer un vrai pattern non-prescriptif
#   ajouté par le renderer, qui resterait scannable.
# - Référence croisée : ces mêmes chaînes sont autorisées au niveau
#   du dépôt par `semantic_guardrails.py` (voir patterns « recommandée »
#   et « meilleur régime » avec leurs contextes whitelistés).
PATTERNS_EXCEPTION_DISCLAIMER = [
    # Mention figée dans DISCLAIMER_AVERTISSEMENT_FINAL v1.0.1 :
    # « l'analyse complémentaire recommandée du cabinet »
    "l'analyse complémentaire recommandée du cabinet",
    "analyse complémentaire recommandée",
    # SP8 — Mentions anti-prescriptives portées par `comparateur_regimes` :
    # le comparateur multi-régimes émet explicitement des notes
    # « non recommandée » et « pas de recommandation automatique » pour
    # rappeler la primauté cabinet. Ces wordings apparaissent dans les
    # hypothèses `note_source` et `NOTE_RECOMMANDATION` des étapes
    # COMP_REG_*. Ils sont eux-mêmes la mise en œuvre de la doctrine
    # non-prescriptive, donc à whitelister précisément.
    "meilleur net dirigeant",  # libellé interne note_source comparateur
    "recommandation automatique de changement de statut",  # disclaimer comparateur
    "(non recommandée)",  # mention explicite « stratégie non recommandée »
]


# ============================================================
# SECTIONS TRANSVERSES — communes à TOUS les régimes
# ============================================================
def section_pdf_valide(runner: AssertionRunner, cas: CasTest) -> None:
    """Vérifie la validité fondamentale du PDF (magic, taille, EOF)."""
    runner.section("Validité PDF (magic %PDF-, taille, EOF)")
    runner.check("Magic header '%PDF-' présent",
                 cas.pdf_bytes.startswith(b"%PDF-"))
    runner.check("Taille raisonnable (≥ 3 ko)",
                 len(cas.pdf_bytes) >= 3 * 1024,
                 detail=f"taille={len(cas.pdf_bytes)} bytes")
    # EOF reportlab : '%%EOF' à la fin (avec éventuel newline)
    fin = cas.pdf_bytes[-20:]
    runner.check("Marqueur EOF '%%EOF' présent en fin de fichier",
                 b"%%EOF" in fin)


def section_couverture(runner: AssertionRunner, cas: CasTest,
                       client_attendu: str = "M. Dupont",
                       expert_attendu: str = "Mme Martin") -> None:
    """Vérifie la présence des métadonnées de couverture."""
    runner.section("Couverture (mission + traçabilité + KPIs)")
    runner.check("Titre 'Audit MODE_AUDIT' présent",
                 "Audit MODE_AUDIT" in cas.texte)
    runner.check(f"Régime attendu '{cas.regime_attendu}' dans la couverture",
                 cas.regime_attendu in cas.texte)
    runner.check(f"Client '{client_attendu}' présent",
                 client_attendu in cas.texte)
    runner.check(f"Expert-comptable '{expert_attendu}' présent",
                 expert_attendu in cas.texte)
    runner.check("Hash baseline présent",
                 "8863991f27f67847" in cas.texte)


def section_kpis_couverture(runner: AssertionRunner, cas: CasTest) -> None:
    """Vérifie le panel KPI de la couverture (4 indicateurs + valeurs)."""
    runner.section("Panel KPI couverture (4 indicateurs)")
    # Scope : 1re partie du texte (couverture est en page 1)
    page1_texte = cas.texte[:min(len(cas.texte), 2500)]
    runner.check("Titre 'Indicateurs de couverture' présent",
                 "Indicateurs de couverture" in page1_texte)
    for label in ("Étapes tracées", "Sous-traces",
                  "Références doctrinales", "Hypothèses"):
        runner.check(f"Label KPI '{label}' présent",
                     label in page1_texte)
    # Valeurs formatées avec espace milliers
    def _fmt(n):
        return f"{n:,}".replace(",", " ")
    for k, label in (("etapes_total", "Étapes tracées"),
                     ("sous_traces_total", "Sous-traces"),
                     ("doctrine_refs_distinctes", "Références doctrinales"),
                     ("hypotheses_total", "Hypothèses")):
        valeur_fmt = _fmt(cas.kpis[k])
        runner.check(f"Valeur KPI {label} ({valeur_fmt}) présente",
                     valeur_fmt in page1_texte,
                     detail=f"valeur attendue '{valeur_fmt}' non trouvée"
                     if valeur_fmt not in page1_texte else "")


def section_bandeau_intro_sommaire(runner: AssertionRunner,
                                   cas: CasTest) -> None:
    """Vérifie la présence et la position du bandeau d'introduction."""
    runner.section("Bandeau d'introduction sommaire (SP5)")
    fragments = [
        "Cette restitution structurée reproduit",
        "moteur d'arbitrage",
        "navigables via les signets PDF",
    ]
    for fragment in fragments:
        runner.check(f"Fragment '{fragment[:40]}...' présent",
                     fragment in cas.texte_norm)
    # Positionnement : avant les entrées du sommaire
    pos_bandeau = cas.texte_norm.find("Cette restitution structurée")
    pos_etapes = cas.texte_norm.find("Étapes du calcul")
    runner.check("Bandeau positionné avant les entrées du sommaire",
                 0 < pos_bandeau < pos_etapes,
                 detail=f"pos_bandeau={pos_bandeau}, pos_etapes={pos_etapes}")
    # Reproduction intégrale
    bandeau_norm = re.sub(r"\s+", " ", BANDEAU_INTRO_SOMMAIRE)
    runner.check("BANDEAU_INTRO_SOMMAIRE rendu intégralement",
                 bandeau_norm in cas.texte_norm)


def section_sommaire_pagine(runner: AssertionRunner, cas: CasTest) -> None:
    """Vérifie que le sommaire contient les sous-traces + numéros de page.

    Neutre : itère sur `trace.noms_sous_traces()` au lieu de hardcoder
    les noms (`strategie_T1`, etc.).
    """
    runner.section("Sommaire navigable et paginé (SP3 + SP5)")
    runner.check("Mot-clé 'Sommaire' présent",
                 "Sommaire" in cas.texte)
    runner.check("Entrée 'Étapes du calcul' dans le sommaire",
                 "Étapes du calcul" in cas.texte_norm)
    # Chaque sous-trace de niveau 1 doit apparaître
    for nom in cas.trace.noms_sous_traces():
        runner.check(f"Sommaire mentionne sous-trace '{nom}'",
                     nom in cas.texte_norm)
    # Numéros de page : pdfplumber extrait les pointillés comme ". . ."
    # → cherche pattern (« . » + espace) × 3+ suivi de chiffres
    debut = cas.texte[:min(len(cas.texte), 5000)]
    nb_lignes_paginees = len(re.findall(r"(?:\.\s+){3,}\d{1,3}", debut))
    nb_attendu = max(1, cas.nb_sous_traces_n1)
    runner.check(f"Sommaire contient ≥ {nb_attendu} lignes avec numéros de page",
                 nb_lignes_paginees >= nb_attendu,
                 detail=f"{nb_lignes_paginees} lignes 'titre...page' observées")


def section_signets_hierarchises(runner: AssertionRunner, cas: CasTest) -> None:
    """Vérifie la présence et hiérarchie des signets PDF.

    Neutre : compte les signets sans présumer du contenu, vérifie qu'un
    signet existe pour chaque sous-trace de niveau 1 de la trace.
    """
    runner.section("Signets PDF hiérarchisés (SP3)")
    if not PYPDF_DISPONIBLE:
        runner.check("pypdf disponible", False,
                     detail="pypdf manquant — section ignorée")
        return
    reader = pypdf.PdfReader(io.BytesIO(cas.pdf_bytes))
    outline = reader.outline

    def aplatir(items, niveau=0):
        for it in items:
            if isinstance(it, list):
                yield from aplatir(it, niveau + 1)
            else:
                yield (niveau, it.title)

    signets = list(aplatir(outline))
    titres = [t for _, t in signets]
    niveaux = sorted(set(n for n, _ in signets))

    runner.check("Au moins 1 signet posé", len(signets) > 0,
                 detail=f"{len(signets)} signets")
    runner.check("Signet 'Étapes du calcul' présent",
                 any("Étapes du calcul" in t for t in titres))
    # Chaque sous-trace N1 doit avoir son signet
    for nom in cas.trace.noms_sous_traces():
        runner.check(f"Signet présent pour sous-trace '{nom}'",
                     any(nom in t for t in titres),
                     detail=f"titres observés: {titres[:3]}..."
                     if not any(nom in t for t in titres) else "")
    # Hiérarchie : au moins le niveau 0 doit exister. Si la trace a
    # des sous-sous-traces (profondeur ≥ 2), niveau 1 doit aussi exister.
    runner.check("Niveau 0 présent dans les signets",
                 0 in niveaux,
                 detail=f"niveaux observés: {niveaux}")
    # Si profondeur ≥ 2, niveau 1 attendu
    a_profondeur_2 = any(
        len(cas.trace.get_sous_trace(n).noms_sous_traces()) > 0
        for n in cas.trace.noms_sous_traces()
    )
    if a_profondeur_2:
        runner.check("Niveau 1 présent dans les signets (profondeur ≥ 2)",
                     1 in niveaux,
                     detail=f"niveaux observés: {niveaux}")


def section_no_declaratif(runner: AssertionRunner, cas: CasTest) -> None:
    """Vérifie qu'aucune chaîne 'Déclaratif' ne subsiste (garde-fou critique)."""
    runner.section("Garde-fou : aucun 'Déclaratif' visible")
    runner.check("Aucune occurrence 'Déclaratif' dans le PDF",
                 "Déclaratif" not in cas.texte,
                 detail="occurrence détectée"
                 if "Déclaratif" in cas.texte else "")


def section_14_patterns_non_prescriptifs(runner: AssertionRunner,
                                         cas: CasTest) -> None:
    """Vérifie qu'aucun des 14 patterns §6.2 doctrine n'apparaît hors disclaimer.

    Neutre : le scan est indépendant du régime. Le résultat ne dépend
    que du contenu textuel généré par le renderer (titres, libellés,
    bandeaux ajoutés par le PDF).
    """
    runner.section("14 patterns non-prescriptifs §6.2 doctrine")
    texte_filtre = cas.texte
    for exception in PATTERNS_EXCEPTION_DISCLAIMER:
        texte_filtre = texte_filtre.replace(exception, "")
    for regex, nom in PATTERNS_NON_PRESCRIPTIFS:
        occurrences = list(re.finditer(regex, texte_filtre))
        runner.check(f"Pattern '{nom}' : 0 occurrence hors disclaimer",
                     len(occurrences) == 0,
                     detail=f"{len(occurrences)} occurrence(s)"
                     if occurrences else "")


def section_neutralite_structurelle(runner: AssertionRunner,
                                    cas: CasTest) -> None:
    """Méta-assertion : le rendu honore la structure de la trace sans hardcode.

    Vérifie 3 propriétés clés qui actent la neutralité :
    1. Le titre de section racine intègre le régime exact de la trace.
    2. Chaque sous-trace N1 a sa propre section navigable.
    3. Les KPIs reflètent fidèlement le comptage récursif de la trace.
    """
    runner.section("Neutralité structurelle (méta-assertion)")
    # 1. Le titre racine doit intégrer le régime tel quel
    runner.check(
        f"Titre racine intègre le régime '{cas.trace.regime}'",
        f"niveau racine — {cas.trace.regime}" in cas.texte_norm
        or f"niveau racine\u00a0— {cas.trace.regime}" in cas.texte_norm,
        detail=f"régime de la trace = '{cas.trace.regime}'",
    )
    # 2. Chaque sous-trace N1 a son titre rendu dans le PDF
    for nom in cas.trace.noms_sous_traces():
        runner.check(
            f"Sous-trace '{nom}' rendue comme section navigable",
            f"« {nom} »" in cas.texte_norm,
        )
    # 3. KPIs cohérents avec comptage récursif (vérification croisée)
    kpis_recompte = _compter_kpis_trace(cas.trace)
    for k in ("etapes_total", "sous_traces_total",
              "doctrine_refs_distinctes", "hypotheses_total"):
        runner.check(
            f"KPI '{k}' cohérent avec comptage récursif",
            cas.kpis[k] == kpis_recompte[k],
            detail=f"observé={cas.kpis[k]}, attendu={kpis_recompte[k]}",
        )


def section_calibrage_dynamique(runner: AssertionRunner, cas: CasTest) -> None:
    """Vérifie que le calibrage dynamique a évité les wraps sur codes longs.

    Heuristique : pour chaque étape ayant un code de 35+ chars, le code
    doit apparaître dans le texte PDF en une seule séquence (sans saut
    de ligne au milieu). Pdfplumber peut introduire un \\n entre les
    parties d'un code wrappé.
    """
    runner.section("Calibrage dynamique des col_widths (SP7)")
    # Collecter tous les codes longs (≥ 35 chars) de la trace
    def all_etapes(t):
        for e in t.etapes:
            yield e
        for _, sub in t.sous_traces.items():
            yield from all_etapes(sub)

    codes_longs = sorted(
        set(e.code for e in all_etapes(cas.trace) if len(e.code) >= 35)
    )
    if not codes_longs:
        runner.check("Aucun code ≥ 35 chars dans la trace (calibrage non testé)",
                     True, detail="N/A — trace courte")
        return

    runner.check(f"Au moins 1 code ≥ 35 chars dans la trace ({len(codes_longs)} codes)",
                 True, detail=", ".join(codes_longs[:3]))
    # Pour chaque code long, il doit apparaître intact dans le texte
    nb_codes_intacts = 0
    nb_codes_casses = 0
    for code in codes_longs:
        if code in cas.texte.replace("\n", ""):
            # Vérifier qu'il n'apparaît pas découpé par \n
            # On cherche une séquence où le code apparaît sans \n au milieu
            if code in cas.texte:
                nb_codes_intacts += 1
            else:
                nb_codes_casses += 1
    runner.check(
        f"Tous les codes ≥ 35 chars rendus sans wrap "
        f"({nb_codes_intacts}/{len(codes_longs)} intacts)",
        nb_codes_casses == 0,
        detail=f"{nb_codes_casses} code(s) wrappé(s) détecté(s)",
    )
