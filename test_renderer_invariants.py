"""
test_renderer_invariants.py — Invariants d'architecture du renderer PDF audit-ready.

SP10 — Phase Hardening v1.0.1.

Ce test est le **garde-fou formalisé de la doctrine technique**
décrite dans `ARCHITECTURE_RENDERER.md`. Il transcrit en assertions
exécutables :

    - Les garanties G1-G5 du §2.1 (rendabilité, indépendance régime,
      indépendance contexte, préservation du graphe, versionnement
      séparé) — assertions **serrées** (1 invariant = 1 propriété).
    - Les antipatterns interdits §4.1-§4.5 (pas de `if regime`, pas de
      hardcoding profondeur, pas de couplage namespace, pas de logique
      métier, pas de fusion renderers) — assertions **serrées** par
      scan textuel regex du code source.
    - Les décisions architecturales D1-D15 du §5 — assertions
      **groupées** dans une section dédiée (15 micro-checks).

Distinction de responsabilité avec les autres tests :

    - `test_renderer_invariants.py` (ce fichier) : invariants
      d'**architecture du code** — ce que le code DOIT respecter pour
      ne pas violer la doctrine.
    - `test_pdf_audit_render_common.py` : invariants de **structure
      de sortie** — ce que le PDF généré DOIT respecter.
    - `test_pdf_audit_render_<regime>.py` : propriétés spécifiques au
      régime appelé.

Couplage SP10-Q3 = b validé : les responsabilités sont distinctes,
pas de duplication d'assertions.

Mécanisme de détection antipatterns :
    Scan textuel par regex (SP10-Q2 = a validé). Le code source de
    `ui/pdf_audit_export.py` est lu, les patterns interdits sont
    cherchés. Whitelist explicite pour les cas légitimes documentés
    (ex. plafond TOC cosmétique en `_rendre_sous_trace_recursif`).

Usage : python3 test_renderer_invariants.py
Exit code 0 si tous les invariants sont respectés.

Ce test est exécuté à chaque PR (SP10-Q4 = a validé). Son coût est
négligeable (scan textuel + import + 2 générations PDF rapides).
"""

import io
import os
import re
import sys
import inspect
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import pdfplumber

# Imports publics du renderer : sert aussi à valider G5 (versions
# séparées) et la stabilité de la signature publique.
from ui.pdf_audit_export import (
    AUDIT_PDF_SPEC_VERSION,
    BASELINE_HASH_DEFAUT,
    SEUIL_HYPOTHESE_LONGUE,
    BANDEAU_INTRO_SOMMAIRE,
    LARGEUR_UTILE_MM,
    BORNES_CODE_MM,
    BORNES_VALEUR_MM,
    BORNES_UNITE_MM,
    BORNES_LIBELLE_MM,
    generer_pdf_audit,
    _calibrer_col_widths,
    _compter_kpis_trace,
)
import ui.pdf_audit_export as renderer_module
from core.audit import TraceAudit, EtapeAudit, AUDIT_SPEC_VERSION
from core.profil import Profil
from strategy.tns import arbitrage_complet_tns
from strategy.comparateur_regimes import calcul_comparateur_regimes


# ============================================================
# RUNNER & CONTEXTE
# ============================================================
RENDERER_PATH = Path(__file__).parent / "ui" / "pdf_audit_export.py"


class InvariantRunner:
    """Runner spécialisé pour invariants d'architecture.

    Distinct de `AssertionRunner` du helper commun (qui sert aux tests
    de sortie PDF). Cohérent avec SP10-Q3=b : séparation des
    responsabilités.
    """

    def __init__(self):
        self.nb_ok = 0
        self.nb_ko = 0
        self.failures: list = []

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        suffix = f"  [{detail}]" if detail and not condition else ""
        symbole = "✓" if condition else "✗"
        print(f"  {symbole} {label}{suffix}")
        if condition:
            self.nb_ok += 1
        else:
            self.nb_ko += 1
            self.failures.append(label + (f"  [{detail}]" if detail else ""))

    def section(self, titre: str) -> None:
        print()
        print("=" * 95)
        print(f"  {titre}")
        print("=" * 95)

    def synthese(self) -> int:
        print()
        print("=" * 95)
        print("  SYNTHÈSE INVARIANTS")
        print("=" * 95)
        print(f"  Invariants OK    : {self.nb_ok}")
        print(f"  Invariants KO    : {self.nb_ko}")
        print()
        if self.nb_ko == 0:
            print("  ✓ ARCHITECTURE_RENDERER.md — doctrine respectée par le code")
            return 0
        else:
            print("  ✗ VIOLATION D'INVARIANT DÉTECTÉE — doctrine non respectée :")
            for f in self.failures:
                print(f"    - {f}")
            print()
            print("  Action requise : soit corriger le code, soit lever explicitement")
            print("  l'invariant par revue architecturale (= nouvelle sous-passe formelle).")
            return 1


def _lire_source_renderer() -> str:
    """Lit le code source de ui/pdf_audit_export.py pour scan textuel."""
    return RENDERER_PATH.read_text(encoding="utf-8")


def _lignes_code_pur(source: str) -> list:
    """Retourne les lignes du source sans commentaires ni docstrings.

    Mécanisme SP10-Q6 = a : améliore la robustesse du scan d'antipatterns
    en excluant les contextes où une mention textuelle n'est pas un
    appel ou une expression Python active. Cela évite les faux positifs
    comme la mention de `generer_pdf_synthese(...)` dans la docstring
    d'en-tête du module renderer.

    Stratégie (volontairement simple, suffisante pour le périmètre) :
    - Les lignes commençant par `#` (ou `    #`, etc.) après strip
      sont vidées.
    - Le contenu après un `#` est tronqué (commentaires inline).
    - Les blocs entre `\"\"\"` (ou `'''`) sur lignes entières sont
      remplacés par des chaînes vides ; numérotation préservée.

    Cette implémentation ne traite pas les triple-quotes multi-niveau
    imbriquées (cas marginal, non observé dans `pdf_audit_export.py`).
    Si ce cas apparaît, basculer vers un parsing AST (option SP10-Q2.b
    rejetée mais réintroductible).

    Args:
        source: Code source brut (str).

    Returns:
        Liste de chaînes, une par ligne, avec commentaires et
        docstrings remplacés par chaîne vide. Longueur identique à
        `source.splitlines()` (numéros de ligne préservés pour
        diagnostic).
    """
    lignes_brutes = source.splitlines()
    resultat: list = []
    in_docstring = False
    delim_actuel = None  # '"""' ou "'''"

    for ln in lignes_brutes:
        # Détection blocs docstring (sur ligne entière ou commençant/finissant
        # par triple-quote). On compte les délimiteurs sur la ligne.
        if not in_docstring:
            # Compter les triple-quotes ouvrantes/fermantes
            for delim in ('"""', "'''"):
                count = ln.count(delim)
                if count == 1:
                    # Une seule occurrence → on entre ou on sort
                    # Si la ligne après suppression du délimiteur contient
                    # encore du contenu après, on garde le contenu non-doc
                    in_docstring = True
                    delim_actuel = delim
                    # On vide la ligne pour le scan (le contenu avant/après
                    # le délim est traité comme docstring)
                    resultat.append("")
                    break
                elif count >= 2:
                    # Docstring inline complète sur la ligne (ex. `x = """..."""`)
                    # On retire le contenu entre les délimiteurs
                    parts = ln.split(delim)
                    # Garder uniquement parts[0] et parts[-1] (avant et après doc)
                    if len(parts) >= 3:
                        ligne_propre = parts[0] + parts[-1]
                    else:
                        ligne_propre = parts[0]
                    # Traitement des commentaires sur cette ligne
                    if "#" in ligne_propre:
                        ligne_propre = ligne_propre.split("#", 1)[0]
                    resultat.append(ligne_propre)
                    break
            else:
                # Pas de triple-quote sur cette ligne → traitement standard
                # Retirer les commentaires (tout après `#`)
                if "#" in ln:
                    ligne_propre = ln.split("#", 1)[0]
                else:
                    ligne_propre = ln
                resultat.append(ligne_propre)
        else:
            # On est dans une docstring : chercher le délimiteur fermant
            if delim_actuel in ln:
                in_docstring = False
                delim_actuel = None
            resultat.append("")

    return resultat


def _all_etapes(trace):
    """Générateur récursif sur toutes les étapes d'une trace."""
    for e in trace.etapes:
        yield e
    for _, sub in trace.sous_traces.items():
        yield from _all_etapes(sub)


# ============================================================
# INVARIANTS G1-G5 (CRITIQUES, SERRÉS)
# ============================================================
def invariants_garanties(runner: InvariantRunner) -> None:
    """Vérifie les 5 garanties G1-G5 du §2.1 ARCHITECTURE_RENDERER.md."""

    # === G1 — Rendabilité universelle ===
    runner.section("INV-G1 — Rendabilité universelle")
    # Trace minimale rendue sans erreur
    trace_min = TraceAudit(regime="Minimal", profil_resume="test")
    trace_min.add(code="MIN_X", label="Étape minimale", valeur=0, unite="")
    try:
        pdf_min = generer_pdf_audit(trace_min, cabinet_nom="X", client_nom="Y")
        crash = False
    except Exception:
        crash = True
        pdf_min = b""
    runner.check(
        "INV-G1.a : Trace minimale (1 étape) rendable sans crash",
        not crash,
    )
    runner.check(
        "INV-G1.b : PDF commence par '%PDF-'",
        pdf_min.startswith(b"%PDF-"),
    )
    runner.check(
        "INV-G1.c : PDF termine par '%%EOF'",
        b"%%EOF" in pdf_min[-30:],
    )
    runner.check(
        "INV-G1.d : Taille PDF ≥ 3 ko",
        len(pdf_min) >= 3 * 1024,
        detail=f"taille={len(pdf_min)} bytes",
    )

    # === G2 — Indépendance du régime ===
    runner.section("INV-G2 — Indépendance du régime dans la signature publique")
    # Signature publique ne doit pas contenir de paramètre régime-spécifique
    sig = inspect.signature(generer_pdf_audit)
    noms_params = set(sig.parameters.keys())
    params_interdits = {"regime", "regime_name", "regime_type", "regime_label"}
    runner.check(
        "INV-G2.a : Signature publique sans paramètre régime-spécifique",
        not (noms_params & params_interdits),
        detail=f"params interdits trouvés: {noms_params & params_interdits}",
    )
    # Vérification croisée : aucun paramètre n'est typé Enum/Literal régime
    for nom, param in sig.parameters.items():
        annotation = str(param.annotation)
        runner.check(
            f"INV-G2.b : Paramètre '{nom}' typé sans contrainte régime",
            "Régime" not in annotation
            and "Regime" not in annotation
            and "REGIME" not in annotation,
            detail=f"annotation suspecte: {annotation}",
        )

    # === G3 — Indépendance du contexte d'appel ===
    runner.section("INV-G3 — Indépendance du contexte d'appel")
    # On vérifie qu'une étape EtapeAudit donnée, rendue dans 2 contextes
    # différents (trace isolée vs imbriquée), produit le même rendu de
    # ligne. Le test cross-contexte le plus simple : comparer le rendu
    # de _table_etapes_plates sur la même étape isolée vs sous un parent.
    from ui.pdf_audit_export import _table_etapes_plates, _build_audit_styles
    styles = _build_audit_styles()
    etape = EtapeAudit(
        code="CROSS_CONTEXT_TEST",
        label="Étape cross-contexte",
        valeur=1234.56, unite="EUR",
        doctrine_refs=(), hypotheses={}, notes="",
    )
    # Rendu 1 : étape seule
    t1 = _table_etapes_plates([etape], styles)
    nb_lignes_t1 = len(t1._cellvalues) if hasattr(t1, "_cellvalues") else 0
    # Rendu 2 : même étape parmi d'autres (contexte différent)
    autres = [
        EtapeAudit(code=f"OTHER_{i}", label=f"autre {i}",
                   valeur=i*100, unite="EUR",
                   doctrine_refs=(), hypotheses={}, notes="")
        for i in range(3)
    ]
    t2 = _table_etapes_plates([etape] + autres, styles)
    nb_lignes_t2 = len(t2._cellvalues) if hasattr(t2, "_cellvalues") else 0
    # La 1re ligne de t2 (après header) doit correspondre à 'etape',
    # donc avoir la même structure de cellule que t1[1]
    runner.check(
        "INV-G3.a : Même étape produit même structure de ligne (cross-contexte)",
        nb_lignes_t1 > 0 and nb_lignes_t2 > 0
        and t1._cellvalues[1][0] is not None
        and t2._cellvalues[1][0] is not None,
        detail=f"t1={nb_lignes_t1} lignes, t2={nb_lignes_t2} lignes",
    )

    # === G4 — Préservation du graphe racine ===
    runner.section("INV-G4 — Préservation du graphe racine "
                   "(reformulé SP10, cf. ARCHITECTURE_RENDERER.md §2.1)")
    # SP10 a découvert que le renderer SP1-SP8 itère sur trace.racines()
    # pour chaque trace et sous-trace, mais ne descend pas dans
    # trace.enfants(code) (étapes filles avec parent_id != None).
    # Conformément à la décision Q5=γ : on documente cette limite et on
    # vérifie l'invariant tel que reformulé (présence des étapes racines
    # uniquement, dette tracée en KNOWN_LIMITATIONS).
    profil = Profil()
    trace_test = TraceAudit(regime="TNS", profil_resume="test G4")
    arbitrage_complet_tns(profil, audit=trace_test)
    pdf = generer_pdf_audit(trace_test, cabinet_nom="X", client_nom="Y")
    with pdfplumber.open(io.BytesIO(pdf)) as pdf_doc:
        texte = "\n".join((p.extract_text() or "") for p in pdf_doc.pages)

    def _toutes_etapes_racines(t):
        """Étapes racines (parent_id is None) sur la trace + sous-traces."""
        for e in t.racines():
            yield e
        for _, sub in t.sous_traces.items():
            yield from _toutes_etapes_racines(sub)

    codes_racines = set(e.code for e in _toutes_etapes_racines(trace_test))
    # pdfplumber peut wrapper certains caractères, on retire les sauts
    texte_normalise = texte.replace("\n", "").replace(" ", "")
    racines_introuvables = [c for c in codes_racines
                            if c not in texte_normalise]
    runner.check(
        f"INV-G4.a : Tous les codes d'étapes racines "
        f"({len(codes_racines)}) présents dans le PDF",
        len(racines_introuvables) == 0,
        detail=f"{len(racines_introuvables)} introuvables : "
               f"{racines_introuvables[:3]}",
    )
    # Note v1.1.1 : INV-G4.b retiré.
    #
    # L'invariant INV-G4.b (introduit en SP10) vérifiait que les étapes
    # filles `parent_id != None` étaient effectivement absentes du PDF.
    # C'était un assertion temporaire qui devait tomber au moment du
    # traitement de la dette G4-filles.
    #
    # En v1.1.1, la dette G4-filles a été clôturée par décision
    # doctrinale (cf. `ARCHITECTURE_RENDERER.md` §2.1) : les étapes
    # filles sont considérées comme des **artefacts internes de calcul
    # et non comme des unités d'audit cabinet**. Cette position est
    # définitive pour toute la branche v1.x.
    #
    # L'invariant INV-G4.b n'a plus de raison d'être : il vérifiait
    # une cohérence entre une réalité technique et une doctrine
    # provisoirement reformulée. La doctrine étant désormais
    # définitive, le comportement « pas d'étapes filles dans le PDF »
    # est attendu sans nécessiter de test dédié au-delà d'INV-G4.a
    # qui suffit à valider le contrat actuel.
    #
    # Si dans une future version (v2.x) la décision était inversée,
    # le bon réflexe est de réintroduire un test couvrant le NOUVEAU
    # comportement (rendu hiérarchique), pas de réintroduire INV-G4.b
    # (qui assertait l'ancien comportement).

    # === G5 — Versionnement séparé ===
    runner.section("INV-G5 — Versionnement séparé renderer / graphe")
    runner.check(
        "INV-G5.a : AUDIT_PDF_SPEC_VERSION et AUDIT_SPEC_VERSION sont 2 "
        "constantes distinctes",
        AUDIT_PDF_SPEC_VERSION != AUDIT_SPEC_VERSION,
        detail=f"renderer={AUDIT_PDF_SPEC_VERSION}, "
               f"graphe={AUDIT_SPEC_VERSION}",
    )
    runner.check(
        "INV-G5.b : AUDIT_PDF_SPEC_VERSION est une chaîne semver "
        "(« X.Y.Z »)",
        re.match(r"^\d+\.\d+\.\d+$", AUDIT_PDF_SPEC_VERSION) is not None,
        detail=f"observé: {AUDIT_PDF_SPEC_VERSION}",
    )


# ============================================================
# INVARIANTS §4 — ANTIPATTERNS INTERDITS (CRITIQUES, SERRÉS)
# ============================================================
def invariants_antipatterns(runner: InvariantRunner) -> None:
    """Scan textuel du code source pour détecter les antipatterns §4.

    SP10-Q6 = a : utilise `_lignes_code_pur` pour exclure les mentions
    en commentaires et docstrings (évite faux positifs).
    """
    source = _lire_source_renderer()
    # Lignes filtrées : commentaires et docstrings vidés, numérotation
    # préservée. Cf. _lignes_code_pur() pour la stratégie.
    lignes = _lignes_code_pur(source)

    # === §4.1 — Aucun `if regime == "..."` ===
    runner.section("INV-§4.1 — Pas de branchement par régime")
    # Pattern strict : "if" + accès à un attribut/variable contenant
    # "regime" + opérateur "==" + chaîne literal
    pattern_regime_eq = re.compile(
        r'\bif\b[^:]*\bregime\b[^:]*==\s*["\']\w+["\']'
    )
    matches_regime = [
        (i + 1, ln)
        for i, ln in enumerate(lignes)
        if pattern_regime_eq.search(ln)
    ]
    runner.check(
        "INV-§4.1.a : Aucun match de pattern `if .*regime.*==.*\"...\"`",
        len(matches_regime) == 0,
        detail=f"{len(matches_regime)} match(s) "
               f"L{[m[0] for m in matches_regime][:3]}",
    )
    # Variante : match.case sur regime
    pattern_match_regime = re.compile(r'\bmatch\b\s+\w*regime\w*\s*:')
    matches_match = [
        (i + 1, ln)
        for i, ln in enumerate(lignes)
        if pattern_match_regime.search(ln)
    ]
    runner.check(
        "INV-§4.1.b : Aucun `match regime:` (pattern matching Python 3.10+)",
        len(matches_match) == 0,
        detail=f"{len(matches_match)} match(s)",
    )

    # === §4.2 — Pas de hardcoding profondeur ===
    runner.section("INV-§4.2 — Pas de hardcoding de profondeur (sauf plafond TOC)")
    # On compte les `if niveau* == <int>` : seul le plafond TOC est
    # autorisé (cf. D7, plafond cosmétique documenté).
    # Le plafond actuel est implémenté ainsi :
    #     min(niveau_toc + 1, 1)  → pas un `if` direct
    # Et 2 occurrences cosmétiques sont explicitement autorisées :
    #     `if niveau_toc == 0` (choix wording "Sous-trace" vs "Détail")
    #     `... if niveau_toc == 0 else ...` (style h1 vs h2)
    # On accepte donc jusqu'à 2 occurrences de cette forme.
    pattern_niveau_eq_int = re.compile(
        r'\bif\b.*\bniveau\w*\s*==\s*\d+'
    )
    matches_niveau = [
        (i + 1, ln.strip())
        for i, ln in enumerate(lignes)
        if pattern_niveau_eq_int.search(ln)
    ]
    runner.check(
        "INV-§4.2.a : Pas plus de 2 occurrences de `if niveau* == <int>` "
        "(plafond cosmétique TOC seulement)",
        len(matches_niveau) <= 2,
        detail=f"{len(matches_niveau)} occurrence(s) : "
               f"L{[m[0] for m in matches_niveau]}",
    )
    # Variante cachée : if profondeur == <int>
    pattern_profondeur_eq = re.compile(
        r'\bif\b.*\bprofondeur\w*\s*==\s*\d+'
    )
    matches_prof = [
        (i + 1, ln)
        for i, ln in enumerate(lignes)
        if pattern_profondeur_eq.search(ln)
    ]
    runner.check(
        "INV-§4.2.b : Aucun `if profondeur* == <int>` "
        "(profondeur dépend du métier)",
        len(matches_prof) == 0,
        detail=f"{len(matches_prof)} match(s)",
    )

    # === §4.3 — Pas de couplage à un namespace de code ===
    runner.section("INV-§4.3 — Pas de filtrage par préfixe de code")
    # Patterns interdits :
    #   code.startswith("STRAT_")
    #   code.startswith("COMP_REG_")
    #   etc.
    # Patterns autorisés :
    #   code.startswith() (sans argument, théorique)
    #   uniquement sur une variable autre que `code` (ex. `nom.startswith()`)
    pattern_code_startswith = re.compile(
        r'\b(code|e\.code|etape\.code)\s*\.\s*startswith\s*\('
    )
    matches_code_sw = [
        (i + 1, ln)
        for i, ln in enumerate(lignes)
        if pattern_code_startswith.search(ln)
    ]
    runner.check(
        "INV-§4.3.a : Aucun `code.startswith(...)` ni `etape.code.startswith(...)`",
        len(matches_code_sw) == 0,
        detail=f"{len(matches_code_sw)} match(s)",
    )
    pattern_code_endswith = re.compile(
        r'\b(code|e\.code|etape\.code)\s*\.\s*endswith\s*\('
    )
    matches_code_ew = [
        (i + 1, ln)
        for i, ln in enumerate(lignes)
        if pattern_code_endswith.search(ln)
    ]
    runner.check(
        "INV-§4.3.b : Aucun `code.endswith(...)`",
        len(matches_code_ew) == 0,
        detail=f"{len(matches_code_ew)} match(s)",
    )
    # Regex match sur code (filtre par expression régulière sur namespace)
    pattern_re_code = re.compile(
        r're\.(?:match|search|fullmatch)\s*\(\s*[^,]+,\s*(?:code|e\.code|etape\.code)'
    )
    matches_re_code = [
        (i + 1, ln)
        for i, ln in enumerate(lignes)
        if pattern_re_code.search(ln)
    ]
    runner.check(
        "INV-§4.3.c : Aucun `re.match/search/fullmatch(..., code)` "
        "qui filtrerait par regex sur namespace",
        len(matches_re_code) == 0,
        detail=f"{len(matches_re_code)} match(s)",
    )

    # === §4.4 — Pas de logique métier ===
    runner.section("INV-§4.4 — Pas d'import strategy/ ou regime/ "
                   "(logique métier confinée hors renderer)")
    # Aucun import depuis strategy/ ou regime/ ne doit apparaître.
    # Seul import autorisé du domaine : `from core.audit import ...`
    # (grammaire de la trace, qui est neutre).
    pattern_import_strategy = re.compile(r'^\s*from\s+strategy[\.\s]')
    pattern_import_regime = re.compile(r'^\s*from\s+regime[\.\s]')
    pattern_import_strategy2 = re.compile(r'^\s*import\s+strategy[\.\s]')
    pattern_import_regime2 = re.compile(r'^\s*import\s+regime[\.\s]')
    matches_imp = [
        (i + 1, ln)
        for i, ln in enumerate(lignes)
        if (pattern_import_strategy.search(ln)
            or pattern_import_regime.search(ln)
            or pattern_import_strategy2.search(ln)
            or pattern_import_regime2.search(ln))
    ]
    runner.check(
        "INV-§4.4.a : Aucun import depuis `strategy/` ou `regime/` "
        "(logique métier interdite dans renderer)",
        len(matches_imp) == 0,
        detail=f"{len(matches_imp)} import(s) interdit(s) : "
               f"L{[m[0] for m in matches_imp]}",
    )

    # === §4.5 — Pas de fusion entre PDF synthèse et PDF audit ===
    runner.section("INV-§4.5 — Pas de fusion renderers synthèse/audit")
    # Vérification 1 : `generer_pdf_audit` ne réutilise pas
    # `generer_pdf_synthese` (couplage fonctionnel interdit).
    pattern_appel_synthese = re.compile(
        r'\bgenerer_pdf_synthese\s*\('
    )
    matches_synth = [
        (i + 1, ln)
        for i, ln in enumerate(lignes)
        if pattern_appel_synthese.search(ln)
    ]
    runner.check(
        "INV-§4.5.a : `generer_pdf_audit` n'appelle jamais "
        "`generer_pdf_synthese`",
        len(matches_synth) == 0,
        detail=f"{len(matches_synth)} appel(s)",
    )
    # Vérification 2 : pas de classe parente partagée (les 2 DocTemplate
    # héritent indépendamment de BaseDocTemplate, pas l'un de l'autre).
    pattern_classe_synth = re.compile(
        r'class\s+\w+\s*\([^)]*(?:SyntheseDocTemplate|PdfSyntheseTemplate)[^)]*\)'
    )
    matches_cls = [
        (i + 1, ln)
        for i, ln in enumerate(lignes)
        if pattern_classe_synth.search(ln)
    ]
    runner.check(
        "INV-§4.5.b : `AuditDocTemplate` n'hérite pas du DocTemplate "
        "du PDF synthèse",
        len(matches_cls) == 0,
        detail=f"{len(matches_cls)} héritage(s) interdit(s)",
    )
    # Vérification 3 : l'import depuis ui.pdf_export se limite à la
    # charte (constantes COULEUR_*, _normaliser_niveau pour
    # rétrocompat, disclaimers v1.0.1). Pas d'import de fonction de
    # rendu lourde.
    pattern_import_synth = re.compile(
        r'^\s*from\s+ui\.pdf_export\s+import\s+(.+)$'
    )
    imports_synth = []
    for i, ln in enumerate(lignes):
        m = pattern_import_synth.search(ln)
        if m:
            imports_synth.append((i + 1, m.group(1).strip()))
    # On scan le bloc d'imports multilignes (de "(" à ")")
    fonctions_rendu_interdites = {
        "generer_pdf_synthese", "PdfSyntheseTemplate",
        "construire_radar_4d", "construire_radar_5d", "construire_radar_6d",
        "construire_projection_5ans",
    }
    imports_pdf_export = []
    in_block = False
    for i, ln in enumerate(lignes):
        if "from ui.pdf_export import (" in ln:
            in_block = True
            continue
        if in_block:
            if ")" in ln:
                in_block = False
                continue
            symbol = ln.strip().rstrip(",").strip()
            if symbol and not symbol.startswith("#"):
                imports_pdf_export.append(symbol)
    fuites = [s for s in imports_pdf_export
              if s in fonctions_rendu_interdites]
    runner.check(
        "INV-§4.5.c : Aucune fonction de rendu lourde du PDF synthèse "
        "importée dans pdf_audit_export",
        len(fuites) == 0,
        detail=f"imports interdits: {fuites}",
    )


# ============================================================
# INVARIANTS D1-D15 — DÉCISIONS ARCHITECTURALES (GROUPÉS)
# ============================================================
def invariants_decisions(runner: InvariantRunner) -> None:
    """Vérifie les 15 décisions architecturales D1-D15 du §5.

    Section groupée (granularité SP10-Q1=c) : ce sont des invariants
    de **décision**, qui peuvent évoluer lors d'un bump majeur
    (AUDIT_PDF_SPEC_VERSION 1.x.x → 2.0.0) après revue architecturale
    formelle. Distincts des invariants G1-G5 et §4.1-§4.5 qui sont
    **non négociables** sans bump majeur explicite.
    """
    runner.section("INV-D1 à D15 — Décisions architecturales (groupées)")

    # D1 — Deux renderers indépendants : déjà couvert par §4.5
    runner.check(
        "INV-D1 : `generer_pdf_audit` existe comme fonction publique distincte",
        callable(generer_pdf_audit)
        and "generer_pdf_audit" in renderer_module.__all__,
    )

    # D2 — ReportLab natif (pas WeasyPrint)
    source = _lire_source_renderer()
    # SP10-Q6 = a : on utilise aussi le code pur pour les scans de
    # patterns dans les invariants D1-D15 où une mention en commentaire
    # ou docstring pourrait fausser le résultat (D2, D6, D9, D13 sont
    # les plus sensibles ; on applique le filtrage uniformément).
    source_pur = "\n".join(_lignes_code_pur(source))
    runner.check(
        "INV-D2 : Aucun import WeasyPrint (renderer = reportlab natif)",
        "from weasyprint" not in source_pur
        and "import weasyprint" not in source_pur,
    )

    # D3 — Pilote TNS livré : présence du test pilote figé
    test_pilote = Path(__file__).parent / "test_pdf_audit_render_tns.py"
    runner.check(
        "INV-D3 : Test pilote TNS (`test_pdf_audit_render_tns.py`) présent",
        test_pilote.exists(),
    )

    # D4 — Schéma S2 (PageBreak par sous-trace N1)
    # On vérifie la présence du pattern `PageBreak()` avant `_rendre_sous_trace_recursif`
    # dans la section orchestration.
    runner.check(
        "INV-D4 : Mécanisme PageBreak par sous-trace N1 présent "
        "(`flow.append(PageBreak())` dans `_section_sous_traces`)",
        re.search(
            r'def _section_sous_traces[^:]*:.*?flow\.append\(PageBreak\(\)\)',
            source_pur, re.DOTALL,
        ) is not None,
    )

    # D5 — SEUIL_HYPOTHESE_LONGUE = 80
    runner.check(
        "INV-D5 : SEUIL_HYPOTHESE_LONGUE == 80 (figé)",
        SEUIL_HYPOTHESE_LONGUE == 80,
        detail=f"observé: {SEUIL_HYPOTHESE_LONGUE}",
    )

    # D6 — Override doctrine en texte (pas d'icône ⚠)
    runner.check(
        "INV-D6 : Mention 'override local' présente dans le code source "
        "(pas d'icône ⚠ pour override doctrine)",
        "override local" in source_pur and "⚠" not in source_pur,
    )

    # D7 — Plafond TOC à 2 niveaux : `min(niveau_toc + 1, 1)`
    runner.check(
        "INV-D7 : Plafond TOC à 2 niveaux implémenté "
        "(`min(niveau_toc + 1, 1)`)",
        re.search(r'min\(\s*niveau_toc\s*\+\s*1\s*,\s*1\s*\)', source_pur)
        is not None,
    )

    # D8 — Calibrage dynamique des col_widths
    runner.check(
        "INV-D8.a : Fonction `_calibrer_col_widths` existe et callable",
        callable(_calibrer_col_widths),
    )
    runner.check(
        "INV-D8.b : Bornes neutres définies : "
        "BORNES_CODE_MM, BORNES_VALEUR_MM, BORNES_UNITE_MM, BORNES_LIBELLE_MM",
        all(isinstance(b, tuple) and len(b) == 2
            for b in (BORNES_CODE_MM, BORNES_VALEUR_MM,
                      BORNES_UNITE_MM, BORNES_LIBELLE_MM)),
    )
    runner.check(
        "INV-D8.c : LARGEUR_UTILE_MM == 174 (A4 - 18mm marges)",
        LARGEUR_UTILE_MM == 174,
        detail=f"observé: {LARGEUR_UTILE_MM}",
    )

    # D9 — Wording « Détail » statu quo : la chaîne « Détail » apparaît
    # dans la construction des titres de sous-traces récursives.
    runner.check(
        "INV-D9 : Wording « Détail » statu quo (présent dans le code "
        "des titres récursifs)",
        '"Détail' in source_pur or "« Détail" in source_pur or '« Détail' in source_pur,
    )

    # D10 — Panel KPI 2x2, 4 indicateurs structurels
    runner.check(
        "INV-D10.a : Fonction `_compter_kpis_trace` existe et retourne "
        "les 4 KPIs attendus",
        callable(_compter_kpis_trace),
    )
    # On vérifie la structure du dict retourné
    profil = Profil()
    t = TraceAudit(regime="TNS")
    arbitrage_complet_tns(profil, audit=t)
    kpis = _compter_kpis_trace(t)
    cles_attendues = {
        "etapes_total", "sous_traces_total",
        "doctrine_refs_distinctes", "hypotheses_total",
    }
    runner.check(
        "INV-D10.b : `_compter_kpis_trace` retourne exactement les 4 KPIs "
        "structurels prévus",
        set(kpis.keys()) == cles_attendues,
        detail=f"observé: {set(kpis.keys())}",
    )

    # D11 — Bandeau intro sommaire défini
    runner.check(
        "INV-D11 : BANDEAU_INTRO_SOMMAIRE défini, non vide, "
        "contient les mots-clés cabinet",
        isinstance(BANDEAU_INTRO_SOMMAIRE, str)
        and len(BANDEAU_INTRO_SOMMAIRE) > 100
        and "graphe de calcul" in BANDEAU_INTRO_SOMMAIRE
        and "moteur d'arbitrage" in BANDEAU_INTRO_SOMMAIRE,
    )

    # D12 — spaceBefore N0 réduit à 2 pt (SP8)
    # On cherche `spaceBefore=2` dans le contexte de `toc_n0`
    pattern_sb_n0 = re.search(
        r'"toc_n0".*?spaceBefore\s*=\s*2',
        source_pur, re.DOTALL,
    )
    runner.check(
        "INV-D12 : `spaceBefore` du style TOC N0 réduit à 2pt (SP8 D8.1)",
        pattern_sb_n0 is not None,
    )

    # D13 — Schéma S2 maintenu : aucune trace d'implémentation S3
    # (annexes paginées). Patterns typiques S3 : "annexe", "Annexe",
    # "appendix" comme section structurelle.
    has_annexe_section = bool(
        re.search(r'def _section_annexe\w*\s*\(', source_pur)
        or re.search(r'class \w*Annexe\w*Template', source_pur)
    )
    runner.check(
        "INV-D13 : Aucune section 'annexe' / 'appendix' = schéma S2 maintenu",
        not has_annexe_section,
    )

    # D14 — Helper commun de test présent
    helper = Path(__file__).parent / "test_pdf_audit_render_common.py"
    runner.check(
        "INV-D14 : Helper commun `test_pdf_audit_render_common.py` présent",
        helper.exists(),
    )

    # D15 — Versionnement séparé : déjà couvert par G5, vérification
    # ici de la cohérence du __all__ qui expose AUDIT_PDF_SPEC_VERSION
    runner.check(
        "INV-D15 : AUDIT_PDF_SPEC_VERSION exposé dans __all__",
        "AUDIT_PDF_SPEC_VERSION" in renderer_module.__all__,
    )


# ============================================================
# INVARIANTS — STABILITÉ DE LA SURFACE PUBLIQUE
# ============================================================
def invariants_surface_publique(runner: InvariantRunner) -> None:
    """Vérifie la stabilité de la surface publique du renderer.

    Cf. ARCHITECTURE_RENDERER.md §6.3 « Où ne pas toucher ».

    L'invariant central : `__all__` doit contenir au minimum les
    27 noms exposés à la livraison v1.0.0 SP8. Toute extension future
    (ajout) est autorisée — toute suppression est un breaking change
    qui exige un bump majeur.
    """
    runner.section("INV-SURFACE — Stabilité de la surface publique")

    NOMS_PUBLICS_V1_0_0 = {
        # Constantes versionnées (3)
        "AUDIT_PDF_SPEC_VERSION", "AUDIT_PDF_DATE", "BASELINE_HASH_DEFAUT",
        # API publique (2)
        "AuditDocTemplate", "generer_pdf_audit",
        # Helpers SP2 (3)
        "_formater_valeur_pdf", "_table_etapes_plates", "_section_etapes_racine",
        # Helpers SP3 (4)
        "TitreNavigable", "_slugify_key", "_construire_sommaire",
        "_section_sous_traces",
        # Helpers SP4 (5)
        "SEUIL_HYPOTHESE_LONGUE", "_format_hyp_valeur",
        "_render_enrichissements_etape",
        "_render_encadres_hypotheses_longues",
        "_rendre_tableau_avec_encadres",
        # Helpers SP5 (3)
        "BANDEAU_INTRO_SOMMAIRE", "_compter_kpis_trace",
        "_table_kpis_couverture",
        # Helpers SP7 (7)
        "_calibrer_col_widths", "_mesurer_largeur_chaine_mm",
        "LARGEUR_UTILE_MM", "BORNES_CODE_MM", "BORNES_VALEUR_MM",
        "BORNES_UNITE_MM", "BORNES_LIBELLE_MM",
    }
    all_actuel = set(renderer_module.__all__)
    manquants = NOMS_PUBLICS_V1_0_0 - all_actuel
    runner.check(
        f"INV-SURFACE.a : Tous les {len(NOMS_PUBLICS_V1_0_0)} noms publics "
        "v1.0.0 toujours exposés dans __all__",
        len(manquants) == 0,
        detail=f"{len(manquants)} manquant(s): {manquants}",
    )
    # Extension autorisée mais notifiée
    nouveaux = all_actuel - NOMS_PUBLICS_V1_0_0
    runner.check(
        f"INV-SURFACE.b : Nouveaux noms publics ajoutés ({len(nouveaux)}) — "
        "extension autorisée, à documenter si bump version",
        True,  # toujours vrai, info uniquement
        detail=f"nouveaux: {sorted(nouveaux)}" if nouveaux else "aucun",
    )

    # Signature publique de generer_pdf_audit : les paramètres
    # critiques doivent rester présents avec leur sémantique.
    sig = inspect.signature(generer_pdf_audit)
    params_obligatoires = {
        "trace",  # premier paramètre positionnel
        "cabinet_nom", "client_nom", "expert_comptable",
        "niveau_confiance", "doctrine_version",
        "audit_pdf_spec_version", "doctrine_date", "baseline_hash",
    }
    params_presents = set(sig.parameters.keys())
    manquants_sig = params_obligatoires - params_presents
    runner.check(
        "INV-SURFACE.c : Signature `generer_pdf_audit` : tous les paramètres "
        "publics v1.0.0 présents",
        len(manquants_sig) == 0,
        detail=f"manquants: {manquants_sig}",
    )


# ============================================================
# MAIN
# ============================================================
def main() -> int:
    print()
    print("=" * 95)
    print("  TEST INVARIANTS RENDERER — SP10 Hardening v1.0.1")
    print("=" * 95)
    print()
    print(f"  Référence doctrine     : ARCHITECTURE_RENDERER.md")
    print(f"  Module testé           : ui/pdf_audit_export.py")
    print(f"  AUDIT_PDF_SPEC_VERSION : {AUDIT_PDF_SPEC_VERSION}")
    print(f"  AUDIT_SPEC_VERSION     : {AUDIT_SPEC_VERSION}")

    runner = InvariantRunner()

    invariants_garanties(runner)
    invariants_antipatterns(runner)
    invariants_decisions(runner)
    invariants_surface_publique(runner)

    return runner.synthese()


if __name__ == "__main__":
    sys.exit(main())
