"""
test_pdf_audit_render_goldens.py — Snapshots JSON structurels du PDF audit.

SP11 — Phase Hardening v1.0.1.

Mécanisme de détection des **micro-régressions visuelles ou structurelles**
du renderer PDF audit-ready. Complète les tests de structure existants
(`test_pdf_audit_render_*.py`) en figeant des **invariants extraits**
des PDF de référence pour les 5 cas du périmètre v1.0.0 :

    - TNS (pilote figé)
    - Assimilé
    - Libéral SELARL
    - Libéral SELAS
    - Comparateur Régimes

Justification : le PDF n'est pas reproductible bit-à-bit (ReportLab
embarque un timestamp interne, la date d'édition est dynamique).
Hasher le binaire est donc impossible. À la place, on extrait
5 familles d'invariants structurels (Q2=b) :

    1. KPIs (4 indicateurs panel couverture)
    2. Codes d'étapes racines présents
    3. Structure des signets PDF (niveau + titre)
    4. Texte normalisé page par page (dates remplacées par placeholder)
    5. Largeurs de colonnes calibrées (mm arrondi 1 décimale)

Format : 1 JSON par cas (Q1=a) dans `golden_pdfs/`.

Modes d'usage :

    # Mode vérification (défaut) — bloque si écart vs golden enregistré
    python3 test_pdf_audit_render_goldens.py

    # Mode mise à jour — regénère les goldens (Q3=a, avec confirmation)
    python3 test_pdf_audit_render_goldens.py --update

Le mode vérification est conçu pour tourner à chaque PR (Q4=a-like,
cohérent SP10). Le mode update est explicite pour éviter les
mises à jour silencieuses.

Couverture (Q4=b) : 5 cas, dont le Comparateur (412 étapes,
profondeur 5) qui maximise la surface d'écart possible.

Référence doctrine : ARCHITECTURE_RENDERER.md §2.2 N4 (« stabilité
binaire non garantie »).
"""

import io
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import pdfplumber

try:
    import pypdf
    PYPDF_DISPONIBLE = True
except ImportError:  # pragma: no cover
    PYPDF_DISPONIBLE = False

from core.audit import TraceAudit
from core.profil import Profil
from strategy.tns import arbitrage_complet_tns
from strategy.assimile import arbitrage_complet
from strategy.liberal import arbitrage_complet_liberal
from strategy.comparateur_regimes import calcul_comparateur_regimes
from strategy.receptacles_orchestrateur import allocation_receptacles

from ui.pdf_audit_export import (
    generer_pdf_audit,
    _compter_kpis_trace,
    _calibrer_col_widths,
    AUDIT_PDF_SPEC_VERSION,
    BASELINE_HASH_DEFAUT,
)
from reportlab.lib.units import mm


# ============================================================
# CONFIGURATION
# ============================================================
GOLDEN_DIR = Path(__file__).parent / "golden_pdfs"
GOLDEN_SPEC_VERSION = "1.0.0"

# Date fixe utilisée pour la génération afin de garantir des goldens
# stables. Cohérent avec la date de figement v1.0.1 (cf.
# ARCHITECTURE_RENDERER.md). N'affecte pas la signature publique
# de `generer_pdf_audit` — seul le paramètre `doctrine_date` est forcé.
DATE_GOLDEN = "20/05/2026"


# ============================================================
# CONSTRUCTION DES 5 CAS DE RÉFÉRENCE
# ============================================================
def construire_trace_tns() -> TraceAudit:
    profil = Profil()
    trace = TraceAudit(regime="TNS",
                       profil_resume="Profil par défaut (SAS, marié 2p, IS 200k)")
    arbitrage_complet_tns(profil, audit=trace)
    return trace


def construire_trace_assimile() -> TraceAudit:
    profil = Profil()
    trace = TraceAudit(regime="Assimilé",
                       profil_resume="Profil par défaut (SAS, marié 2p, IS 200k)")
    arbitrage_complet(profil, audit=trace)
    return trace


def construire_trace_liberal_selarl() -> TraceAudit:
    profil = Profil(forme_sel="SELARL")
    trace = TraceAudit(regime="Libéral SELARL",
                       profil_resume="Profil Libéral (SELARL)")
    arbitrage_complet_liberal(profil, audit=trace)
    return trace


def construire_trace_liberal_selas() -> TraceAudit:
    profil = Profil(forme_sel="SELAS")
    trace = TraceAudit(regime="Libéral SELAS",
                       profil_resume="Profil Libéral (SELAS)")
    arbitrage_complet_liberal(profil, audit=trace)
    return trace


def construire_trace_comparateur() -> TraceAudit:
    profil = Profil()
    trace = TraceAudit(regime="Comparateur Régimes",
                       profil_resume="Profil par défaut (SAS, marié 2p, IS 200k)")
    calcul_comparateur_regimes(profil, audit=trace)
    return trace


def construire_trace_receptacles() -> TraceAudit:
    """Trace orchestrateur Réceptacles pour golden PDF (SP19).

    Cas figé identique au mini-golden orchestrateur `composition_5000`
    (SP18, cf. test_strategy_receptacles_goldens.py) :
      - Profil par défaut (SAS, marié 2p, IS 200k)
      - Flux disponible 5 000 €
      - Horizons par défaut (5, 10, 20 ans)
      - 3 modules réels PERIN/PEE/PERECO + étapes méta orchestrateur SP18

    Volumétrie attendue : ~109 étapes racine + 12 sous-traces, PDF ~75 ko.
    """
    profil = Profil()
    trace = TraceAudit(
        regime="Réceptacles",
        profil_resume=(
            "Profil par défaut (SAS), flux 5 000 €, horizons (5, 10, 20)"
        ),
    )
    allocation_receptacles(
        profil,
        flux_disponible=5000.0,
        horizons=(5, 10, 20),
        audit=trace,
    )
    return trace


CAS_GOLDEN = [
    ("tns", construire_trace_tns),
    ("assimile", construire_trace_assimile),
    ("liberal_selarl", construire_trace_liberal_selarl),
    ("liberal_selas", construire_trace_liberal_selas),
    ("comparateur_regimes", construire_trace_comparateur),
    ("receptacles", construire_trace_receptacles),
]


# ============================================================
# EXTRACTION DES INVARIANTS (5 FAMILLES Q2=b)
# ============================================================
# Pattern de date dd/mm/yyyy à neutraliser dans le texte extrait pour
# stabilité du snapshot. ReportLab génère des dates dynamiques dans la
# couverture et le footer ; on les remplace par un placeholder.
PATTERN_DATE_FR = re.compile(r'\b\d{2}/\d{2}/\d{4}\b')
PLACEHOLDER_DATE = "<DATE>"


def _normaliser_texte_pour_golden(texte: str) -> str:
    """Normalise le texte extrait pour snapshot stable.

    Opérations :
        1. Remplacement des dates dd/mm/yyyy par `<DATE>` (footer, couverture)
        2. Réduction des whitespace multiples en espace simple
        3. Suppression des espaces en début/fin de ligne
        4. Suppression des lignes vides

    Args:
        texte: Texte brut extrait par pdfplumber.

    Returns:
        Texte normalisé, stable entre exécutions.
    """
    # 1. Neutraliser les dates dynamiques
    texte = PATTERN_DATE_FR.sub(PLACEHOLDER_DATE, texte)
    # 2-4. Normaliser les whitespace par ligne
    lignes = []
    for ln in texte.split("\n"):
        ln_norm = re.sub(r"\s+", " ", ln).strip()
        if ln_norm:
            lignes.append(ln_norm)
    return "\n".join(lignes)


def _all_etapes(trace: TraceAudit):
    """Générateur récursif sur toutes les étapes du graphe."""
    for e in trace.etapes:
        yield e
    for _, sub in trace.sous_traces.items():
        yield from _all_etapes(sub)


def _toutes_etapes_racines(trace: TraceAudit):
    """Étapes racines (parent_id is None) sur toute la hiérarchie de traces.

    Conforme à G4 reformulé SP10 : le PDF rend les étapes racines de
    chaque (sous-)trace, pas les étapes filles `parent_id != None`.
    """
    for e in trace.racines():
        yield e
    for _, sub in trace.sous_traces.items():
        yield from _toutes_etapes_racines(sub)


def _extraire_invariants(trace: TraceAudit, pdf_bytes: bytes,
                        regime_label: str) -> dict:
    """Extrait les 5 familles d'invariants d'un PDF pour snapshot golden.

    Args:
        trace: TraceAudit ayant servi à générer le PDF.
        pdf_bytes: PDF généré par `generer_pdf_audit`.
        regime_label: Libellé du régime (clé du snapshot).

    Returns:
        Dict prêt à être sérialisé en JSON.
    """
    # === 1. KPIs ===
    kpis = _compter_kpis_trace(trace)

    # === 2. Codes d'étapes racines (triés pour comparaison déterministe) ===
    codes_racines = sorted(set(
        e.code for e in _toutes_etapes_racines(trace)
    ))

    # === 3. Signets PDF aplatis (niveau + titre) ===
    # Note : pypdf retourne les titres en `TextStringObject` (sous-classe
    # de str). On caste explicitement en str natif pour garantir la
    # cohérence du snapshot JSON (sérialisation/désérialisation
    # idempotente et comparaisons cross-types évitées).
    signets = []
    if PYPDF_DISPONIBLE:
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))

            def _aplatir(items, niveau=0):
                for it in items:
                    if isinstance(it, list):
                        yield from _aplatir(it, niveau + 1)
                    else:
                        yield {"niveau": niveau, "titre": str(it.title)}

            signets = list(_aplatir(reader.outline))
        except Exception as exc:  # pragma: no cover
            signets = [{"erreur": str(exc)}]

    # === 4. Texte normalisé page par page ===
    texte_par_page = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf_doc:
        for p in pdf_doc.pages:
            texte_brut = p.extract_text() or ""
            texte_par_page.append(_normaliser_texte_pour_golden(texte_brut))

    # === 5. Largeurs de colonnes calibrées ===
    etapes_pour_calibrage = list(_all_etapes(trace))
    col_widths = _calibrer_col_widths(etapes_pour_calibrage)
    col_widths_mm = {
        "code": round(col_widths[0] / mm, 1),
        "libelle": round(col_widths[1] / mm, 1),
        "valeur": round(col_widths[2] / mm, 1),
        "unite": round(col_widths[3] / mm, 1),
    }

    return {
        "spec_golden_version": GOLDEN_SPEC_VERSION,
        "regime": regime_label,
        "audit_pdf_spec_version": AUDIT_PDF_SPEC_VERSION,
        "baseline_hash": BASELINE_HASH_DEFAUT,
        "kpis": kpis,
        "codes_etapes_racines": codes_racines,
        "signets": signets,
        "nb_pages": len(texte_par_page),
        "texte_par_page": texte_par_page,
        "col_widths_mm": col_widths_mm,
    }


def _generer_pdf_pour_golden(trace: TraceAudit) -> bytes:
    """Génère un PDF avec date forcée pour stabilité du snapshot."""
    return generer_pdf_audit(
        trace,
        cabinet_nom="Cabinet TestCo",
        client_nom="M. Dupont",
        expert_comptable="Mme Martin",
        doctrine_date=DATE_GOLDEN,
    )


# ============================================================
# COMPARAISON GOLDEN vs OBSERVÉ
# ============================================================
def _comparer_invariants(observe: dict, golden: dict) -> list:
    """Compare 2 dicts d'invariants, retourne liste de divergences.

    Chaque divergence est un tuple (chemin, valeur_golden, valeur_observe).
    Comparaison récursive structurelle. Le champ `audit_pdf_spec_version`
    est vérifié pour détecter un bump de version (signal explicite).

    Args:
        observe: Invariants extraits du PDF en cours.
        golden: Invariants chargés depuis le snapshot enregistré.

    Returns:
        Liste de divergences. Vide si correspondance complète.
    """
    divergences = []

    def _compare(chemin, vg, vo):
        # Vérification de type structurelle UNIQUEMENT pour les containers
        # (dict, list). Pour les valeurs scalaires, on s'appuie sur `==`
        # qui supporte les comparaisons cross-types compatibles (ex.
        # `pypdf.generic.TextStringObject` vs `str`, `int` vs `float`).
        # Sans cette nuance, le chargement JSON (qui convertit tout en
        # types natifs Python) divergeait systématiquement des valeurs
        # extraites par pypdf (qui retourne des sous-classes spécifiques).
        if isinstance(vg, dict) != isinstance(vo, dict):
            divergences.append((chemin, vg, vo))
            return
        if isinstance(vg, list) != isinstance(vo, list):
            divergences.append((chemin, vg, vo))
            return
        if isinstance(vg, dict):
            cles_communes = set(vg) | set(vo)
            for c in sorted(cles_communes):
                if c not in vg:
                    divergences.append((f"{chemin}.{c}", "<absent>", vo[c]))
                elif c not in vo:
                    divergences.append((f"{chemin}.{c}", vg[c], "<absent>"))
                else:
                    _compare(f"{chemin}.{c}", vg[c], vo[c])
        elif isinstance(vg, list):
            if len(vg) != len(vo):
                divergences.append(
                    (f"{chemin}[len]", len(vg), len(vo))
                )
                # Continuer la comparaison jusqu'au min
            for i in range(min(len(vg), len(vo))):
                _compare(f"{chemin}[{i}]", vg[i], vo[i])
        else:
            if vg != vo:
                divergences.append((chemin, vg, vo))

    _compare("", observe, golden)
    return divergences


# ============================================================
# MAIN — MODES VERIFY ET UPDATE
# ============================================================
def mode_verify() -> int:
    """Mode vérification : compare observés vs goldens enregistrés.

    Returns:
        0 si tous les goldens correspondent.
        1 si au moins une divergence détectée.
        2 si un golden est manquant (jamais initialisé).
    """
    print()
    print("=" * 95)
    print("  GOLDEN PDFs — Mode VÉRIFICATION (SP11)")
    print("=" * 95)
    print()
    print(f"  Répertoire goldens   : {GOLDEN_DIR}")
    print(f"  Cas couverts         : {len(CAS_GOLDEN)}")
    print(f"  Spec golden version  : {GOLDEN_SPEC_VERSION}")
    print(f"  Spec PDF version     : {AUDIT_PDF_SPEC_VERSION}")
    print()

    if not GOLDEN_DIR.exists():
        print(f"  ✗ Répertoire goldens absent : {GOLDEN_DIR}")
        print(f"    Lancer `python3 {Path(__file__).name} --update` "
              "pour l'initialiser.")
        return 2

    nb_ok = 0
    nb_ko = 0
    nb_manquants = 0

    for cle, fn_constructeur in CAS_GOLDEN:
        chemin_golden = GOLDEN_DIR / f"golden_{cle}.json"
        print("-" * 95)
        print(f"  Cas : {cle}")
        print("-" * 95)

        if not chemin_golden.exists():
            print(f"  ✗ Golden manquant : {chemin_golden.name}")
            nb_manquants += 1
            continue

        # Génération et extraction des observés
        trace = fn_constructeur()
        pdf = _generer_pdf_pour_golden(trace)
        observe = _extraire_invariants(trace, pdf, trace.regime)

        # Chargement du golden
        with open(chemin_golden, "r", encoding="utf-8") as f:
            golden = json.load(f)

        # Comparaison
        divergences = _comparer_invariants(observe, golden)

        if not divergences:
            print(f"  ✓ Golden conforme — {observe['nb_pages']} pages, "
                  f"{observe['kpis']['etapes_total']} étapes, "
                  f"{len(observe['codes_etapes_racines'])} codes racines, "
                  f"{len(observe['signets'])} signets")
            nb_ok += 1
        else:
            print(f"  ✗ {len(divergences)} divergence(s) détectée(s) :")
            for chemin, val_g, val_o in divergences[:5]:
                # Tronquer les valeurs très longues
                def _trunc(v, n=80):
                    s = repr(v)
                    return s if len(s) <= n else s[:n] + "..."
                print(f"      {chemin}")
                print(f"        golden  = {_trunc(val_g)}")
                print(f"        observé = {_trunc(val_o)}")
            if len(divergences) > 5:
                print(f"      ... et {len(divergences) - 5} autre(s)")
            nb_ko += 1

    print()
    print("=" * 95)
    print("  SYNTHÈSE GOLDEN")
    print("=" * 95)
    print(f"  Conformes        : {nb_ok}/{len(CAS_GOLDEN)}")
    print(f"  Divergents       : {nb_ko}")
    print(f"  Manquants        : {nb_manquants}")
    print()

    if nb_ko == 0 and nb_manquants == 0:
        print("  ✓ Tous les goldens conformes — aucune micro-régression détectée")
        return 0
    elif nb_manquants > 0 and nb_ko == 0:
        print(f"  ⓘ {nb_manquants} golden(s) à initialiser via --update")
        return 2
    else:
        print("  ✗ Régression détectée. Actions possibles :")
        print("    1. Investiguer la cause (modification renderer/trace).")
        print("    2. Si la divergence est attendue (changement validé) :")
        print(f"       `python3 {Path(__file__).name} --update`")
        return 1


def mode_update() -> int:
    """Mode mise à jour : regénère les goldens après confirmation interactive.

    Q3=a validé : confirmation interactive obligatoire pour éviter une
    mise à jour silencieuse. Non-interactive (CI) : refuse de tourner
    sauf si la variable d'env `GOLDEN_UPDATE_FORCE=1` est définie.

    Returns:
        0 après mise à jour complète.
        1 si annulation utilisateur.
    """
    print()
    print("=" * 95)
    print("  GOLDEN PDFs — Mode MISE À JOUR (SP11)")
    print("=" * 95)
    print()
    print(f"  Répertoire goldens   : {GOLDEN_DIR}")
    print(f"  Cas à mettre à jour  : {len(CAS_GOLDEN)}")
    for cle, _ in CAS_GOLDEN:
        existant = (GOLDEN_DIR / f"golden_{cle}.json").exists()
        print(f"    - {cle:25} {'(remplacement)' if existant else '(création)'}")
    print()

    # Confirmation interactive — Q3=a validé
    if sys.stdin.isatty():
        reponse = input("  Confirmer la mise à jour des goldens ci-dessus ? "
                        "[y/N] ").strip().lower()
        if reponse not in ("y", "yes", "o", "oui"):
            print()
            print("  ✗ Mise à jour annulée par l'utilisateur.")
            return 1
    else:
        # Mode non-interactif : refus sauf force explicite
        if os.environ.get("GOLDEN_UPDATE_FORCE") != "1":
            print()
            print("  ✗ Mode non-interactif détecté (pas de TTY).")
            print("    Pour forcer en CI : "
                  "export GOLDEN_UPDATE_FORCE=1")
            return 1
        print("  ⓘ Mode non-interactif avec GOLDEN_UPDATE_FORCE=1 — "
              "mise à jour autorisée.")

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    for cle, fn_constructeur in CAS_GOLDEN:
        chemin_golden = GOLDEN_DIR / f"golden_{cle}.json"
        trace = fn_constructeur()
        pdf = _generer_pdf_pour_golden(trace)
        invariants = _extraire_invariants(trace, pdf, trace.regime)
        with open(chemin_golden, "w", encoding="utf-8") as f:
            json.dump(invariants, f, ensure_ascii=False, indent=2)
        kpi = invariants["kpis"]
        print(f"  ✓ {chemin_golden.name} — "
              f"{invariants['nb_pages']} pages, "
              f"{kpi['etapes_total']} étapes, "
              f"{len(invariants['codes_etapes_racines'])} codes racines, "
              f"{len(invariants['signets'])} signets")

    print()
    print(f"  ✓ {len(CAS_GOLDEN)} golden(s) écrit(s) dans {GOLDEN_DIR}")
    return 0


def main() -> int:
    if "--update" in sys.argv:
        return mode_update()
    return mode_verify()


if __name__ == "__main__":
    sys.exit(main())
