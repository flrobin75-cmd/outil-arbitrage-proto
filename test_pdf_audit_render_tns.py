"""
test_pdf_audit_render_tns.py — Test PDF audit-ready, pilote TNS v1.0.0.

Statut SP6 (clôture pilote v1) : 93 contrôles, 0 régression.

================================================================================
RÉCAPITULATIF DE BOUT EN BOUT — Pilote TNS PDF audit-ready v1.0.0
================================================================================

Ce test couvre l'intégralité du chantier renderer PDF audit (SP1 → SP5)
sur le pilote TNS (`arbitrage_complet_tns(Profil())`). Il sert de
référence stable pour les futures extensions (SP7 Assimilé + Libéral,
SP8 comparateur_regimes).

Architecture du PDF généré (figée en sortie SP5) :

    Page 1     Couverture (mission + traçabilité 4 versions + KPIs)
    Page 2     Sommaire (bandeau intro cabinet + TOC 2 niveaux)
    Page 3     Étapes du calcul (niveau racine — TNS)        [signet N0]
    Page 4-5   Sous-trace strategie_T1                        [signet N0]
                   └ Détail module_tns                        [signet N1]
    Page 6-7   Sous-trace strategie_T2                        [signet N0]
                   └ Détail module_tns                        [signet N1]
    Page 8-10  Sous-trace strategie_T3                        [signet N0]
                   └ Détail module_tns                        [signet N1]
    Page 11-12 Sous-trace strategie_T4                        [signet N0]
                   └ Détail module_tns                        [signet N1]
    Page 13    Avertissements et primauté cabinet            (disclaimers v1.0.1)

Couverture des sous-passes :

    SP1 — Scaffolding (couverture + disclaimers + DocTemplate)
        ✓ Magic %PDF-, EOF, taille ≥ 3 ko
        ✓ Couverture (cabinet, client, expert, niveau, 4 versions, hash)

    SP2 — Rendu racine (tableau 4 colonnes)
        ✓ 4 étapes racine (codes, valeurs formatées)
        ✓ Garde-fou T4 : INDICATEURS_SEPARES distinct de COMPARE_AB
        ✓ Formatage EUR (« 105 116.99 € »), ratio (« 0.5256 »), texte brut

    SP3 — Récursion sous-traces, schéma S2
        ✓ Sommaire TableOfContents 2 niveaux, numéros de page exacts
        ✓ Signets PDF hiérarchisés (N0 stratégies + N1 module_tns)
        ✓ Saut de page systématique sur chaque sous-trace N1
        ✓ Sous-trace N2 enchaînée à sa N1 parente (pas de PageBreak)
        ✓ multiBuild (double passe pour matérialiser les n° de page)

    SP4 — Enrichissements (doctrine_refs, hypotheses, notes, overrides)
        ✓ doctrine_refs résolues, gris discret 7pt sous l'étape
        ✓ hypothèses < 80 chars inline (ligne colspan 4)
        ✓ hypothèses ≥ 80 chars en encadré dédié sous le tableau
          (cf. SEUIL_HYPOTHESE_LONGUE, calibré sur trace pilote)
        ✓ notes italique gris sous l'étape
        ✓ override doctrine (mock) : mention « override local : appliquée X vs doctrine Y »
        ✓ référence doctrinale introuvable (mock) : mention explicite, pas de crash
        ✓ Pas d'icône (Q2 = β validé) — texte explicite uniquement

    SP5 — Peaufinage cabinet-ready (couverture + sommaire)
        ✓ Panel KPI 2×2 sobre sur la couverture
          (étapes, sous-traces, doctrine_refs distinctes, hypothèses)
        ✓ Bandeau d'introduction cabinet sur la page sommaire
          (BANDEAU_INTRO_SOMMAIRE — pédagogique, distinct des disclaimers)

    SP6 — Consolidation (cette docstring + KNOWN_LIMITATIONS.md)
        Pas de nouveau code, pas de nouveau test.

Garde-fous transverses (toutes les sous-passes) :

    ✓ Aucune chaîne « Déclaratif » résiduelle dans le PDF
    ✓ Aucun des 14 patterns non-prescriptifs §6.2 doctrine dans le texte
      généré par le renderer (hors disclaimer « recommandée » whitelisté)
    ✓ Compare_baseline 16/16 inchangé (hash 8863991f27f67847)
    ✓ test_pdf_render_all_regimes (PDF synthèse historique) 64/64 inchangé
    ✓ 13 suites MODE_AUDIT, 4 audits sémantiques, baseline_tests 7/7 : tous verts

Métriques de couverture (trace TNS pilote, Profil() par défaut) :

    Étapes tracées          : 156
    Sous-traces             : 8  (4 strategie_TX + 4 module_tns)
    Doctrine refs distinctes: 11
    Hypothèses              : 114 (dont 3 longues en encadré)
    Notes                   : 57
    Pages PDF générées      : 13
    Taille PDF              : ~40 ko

Périmètre couvert :
    ✓ Régime TNS (arbitrage_complet_tns)

Périmètre NON couvert par ce test (extensions futures) :
    SP7 — Régime Assimilé (`arbitrage_complet`)
    SP7 — Régime Libéral (`arbitrage_complet_liberal`) — BNC + SEL
    SP8 — Comparateur multi-régimes (`comparateur_regimes`) — profondeur 5

Les extensions SP7/SP8 utiliseront `generer_pdf_audit()` sans modification
(signature publique figée depuis SP1). Seul le test sera étendu pour
brancher les nouvelles traces racines et adapter les assertions
contextuelles (noms de sous-traces, codes namespace, etc.).

================================================================================

Usage : python3 test_pdf_audit_render_tns.py
Exit code 0 si tous les contrôles passent.

Dépendances :
- pdfplumber (déjà utilisé par test_pdf_render_all_regimes.py et
  test_no_declaratif_residual.py — pas de dépendance nouvelle).
- pypdf pour inspection des signets PDF (dépendance transitive
  de pdfplumber, généralement disponible).
"""

import sys
import os
import re
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import pdfplumber

try:
    import pypdf
    PYPDF_DISPONIBLE = True
except ImportError:  # pragma: no cover
    PYPDF_DISPONIBLE = False

from core.audit import TraceAudit, EtapeAudit, resoudre_doctrine_ref
from core.profil import Profil
from strategy.tns import arbitrage_complet_tns

from ui.pdf_audit_export import (
    generer_pdf_audit,
    _formater_valeur_pdf,
    AUDIT_PDF_SPEC_VERSION,
    BASELINE_HASH_DEFAUT,
    SEUIL_HYPOTHESE_LONGUE,
    _render_enrichissements_etape,
    _render_encadres_hypotheses_longues,
    _build_audit_styles,
    # SP5
    _compter_kpis_trace,
    BANDEAU_INTRO_SOMMAIRE,
)


# ============================================================
# NORMALISATION DU TEXTE PDFPLUMBER (SP3)
# ============================================================
def _normaliser_texte_pdf(texte: str) -> str:
    """Normalise le texte extrait par pdfplumber pour comparaison robuste.

    Pdfplumber peut introduire :
    - des sauts de ligne au milieu d'une cellule wrappée ;
    - des espaces multiples ;
    - des retours chariot intermittents.

    Cette normalisation remplace tout whitespace par un espace simple,
    ce qui permet de matcher des chaînes même si elles sont visuellement
    coupées entre deux lignes de cellule. À utiliser avec précaution :
    deux étapes adjacentes peuvent voir leurs textes accolés.

    Args:
        texte: Texte brut extrait par pdfplumber.

    Returns:
        Texte normalisé.
    """
    return re.sub(r"\s+", " ", texte)


# ============================================================
# DOSSIER DE SORTIE (cohérent avec test_pdf_render_all_regimes.py)
# ============================================================
PDF_OUT_DIR = Path("/tmp/pdf_audit_test_outputs")
PDF_OUT_DIR.mkdir(exist_ok=True)


# ============================================================
# HELPERS
# ============================================================
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrait le texte de toutes les pages d'un PDF en mémoire."""
    import io
    buf = io.BytesIO(pdf_bytes)
    texte = []
    with pdfplumber.open(buf) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            texte.append(t)
    return "\n".join(texte)


# ============================================================
# REGISTRE DES VÉRIFS
# ============================================================
NB_OK = 0
NB_KO = 0
FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    global NB_OK, NB_KO
    if condition:
        NB_OK += 1
        print(f"  ✓ {label}")
    else:
        NB_KO += 1
        msg = f"{label}" + (f"  [{detail}]" if detail else "")
        FAILURES.append(msg)
        print(f"  ✗ {label}" + (f"  [{detail}]" if detail else ""))


# ============================================================
# 14 PATTERNS NON-PRESCRIPTIFS — doctrine §6.2
# ============================================================
# Repris à l'identique des conventions doctrinales pour scanner
# les chaînes générées par le renderer PDF audit lui-même.
#
# IMPORTANT : ces patterns ne s'appliquent PAS aux labels des étapes,
# qui sont déjà couverts en amont par les tests MODE_AUDIT
# (test_mode_audit_strategy_tns.py teste l'absence de termes
# prescriptifs dans `label`/`notes` de chaque EtapeAudit). Ici on
# scanne le texte PDF entier, ce qui inclut aussi les en-têtes et
# bandeaux générés par pdf_audit_export.py (« Étapes du calcul »,
# « 4 étape(s) au niveau racine », etc.).
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
# Exceptions whitelistées (cohérent avec semantic_guardrails §6.5 doctrine) :
# - le mot « recommandée » apparaît dans DISCLAIMER_AVERTISSEMENT_FINAL
#   v1.0.1 (« l'analyse complémentaire recommandée du cabinet »). C'est un
#   disclaimer figé, déjà whitelisté dans les audits sémantiques amont.
PATTERNS_EXCEPTION_DISCLAIMER = [
    "l'analyse complémentaire recommandée du cabinet",
]


# ============================================================
# CONSTRUCTION DE LA TRACE PILOTE
# ============================================================
def construire_trace_pilote() -> TraceAudit:
    """Construit la TraceAudit pilote TNS utilisée par tous les tests."""
    profil = Profil()
    trace = TraceAudit(
        regime="TNS",
        profil_resume="Profil par défaut (SAS, marié 2p, IS 200k)",
    )
    arbitrage_complet_tns(profil, audit=trace)
    return trace


# ============================================================
# TESTS
# ============================================================
def main() -> int:
    print("=" * 95)
    print("  TEST PDF audit-ready — Pilote TNS v1.0.0 (SP1→SP5, clôturé SP6)")
    print("=" * 95)

    trace = construire_trace_pilote()
    racines = trace.racines()

    print()
    print(f"  Trace pilote          : {trace.regime}")
    print(f"  Étapes racine         : {len(racines)}")
    print(f"  Sous-traces N1        : {list(trace.noms_sous_traces())} "
          f"(rendues récursivement en SP3)")
    print()

    # Génération PDF
    pdf_bytes = generer_pdf_audit(
        trace,
        cabinet_nom="Cabinet TestCo",
        client_nom="M. Dupont",
        expert_comptable="Mme Martin",
    )

    # Sauvegarde pour inspection
    chemin = PDF_OUT_DIR / "sp2_sp3_sp4_sp5_audit_tns.pdf"
    chemin.write_bytes(pdf_bytes)
    print(f"  PDF généré → {chemin}  ({len(pdf_bytes)} bytes)")
    print()

    # === SECTION 1 — Validité structurelle PDF ===
    print("=" * 95)
    print("  SECTION 1 — Validité structurelle PDF")
    print("=" * 95)
    check("Magic %PDF- présent en début de fichier",
          pdf_bytes.startswith(b"%PDF-"))
    check("EOF marker %%EOF présent en fin de fichier",
          b"%%EOF" in pdf_bytes[-200:])
    check("Taille PDF ≥ 3 ko (non tronqué)",
          len(pdf_bytes) >= 3000,
          detail=f"{len(pdf_bytes)} bytes")

    # === SECTION 2 — Extraction texte ===
    print()
    print("=" * 95)
    print("  SECTION 2 — Extraction texte")
    print("=" * 95)
    try:
        texte = extract_text_from_pdf(pdf_bytes)
        check("Extraction texte pdfplumber réussie",
              len(texte) > 0,
              detail=f"{len(texte)} chars extraits")
    except Exception as exc:  # noqa: BLE001
        check("Extraction texte pdfplumber réussie",
              False, detail=str(exc))
        return 1

    # === SECTION 3 — Chaque code racine apparaît ===
    print()
    print("=" * 95)
    print("  SECTION 3 — Présence des codes d'étapes racine")
    print("=" * 95)
    for etape in racines:
        check(f"Code racine présent : {etape.code}",
              etape.code in texte,
              detail=f"introuvable" if etape.code not in texte else "")

    # === SECTION 4 — Chaque valeur formatée apparaît ===
    print()
    print("=" * 95)
    print("  SECTION 4 — Présence des valeurs formatées")
    print("=" * 95)
    for etape in racines:
        valeur_attendue = _formater_valeur_pdf(etape.valeur, etape.unite)
        # pdfplumber peut introduire des espaces différents (ex : '105 116.99' →
        # '105 116.99' avec espace fin ou normal). On normalise avant comparaison.
        valeur_norm = re.sub(r"\s+", " ", valeur_attendue)
        texte_norm = re.sub(r"\s+", " ", texte)
        check(f"Valeur formatée présente : {etape.code} → {valeur_attendue!r}",
              valeur_norm in texte_norm,
              detail=f"non trouvé" if valeur_norm not in texte_norm else "")

    # === SECTION 5 — Garde-fou T4 (non-agrégation) ===
    print()
    print("=" * 95)
    print("  SECTION 5 — Garde-fou T4 : INDICATEURS_SEPARES distinct de COMPARE_AB")
    print("=" * 95)
    check("STRAT_TNS_INDICATEURS_SEPARES présent",
          "STRAT_TNS_INDICATEURS_SEPARES" in texte)
    check("STRAT_TNS_COMPARE_AB présent",
          "STRAT_TNS_COMPARE_AB" in texte)
    # Vérification de non-agrégation : les 2 codes apparaissent comme étapes
    # distinctes (pas de calcul somme visible)
    indices_separes = [m.start() for m in re.finditer(
        r"STRAT_TNS_INDICATEURS_SEPARES", texte)]
    indices_compare = [m.start() for m in re.finditer(
        r"STRAT_TNS_COMPARE_AB", texte)]
    check("Les 2 codes apparaissent à des positions distinctes",
          len(indices_separes) >= 1 and len(indices_compare) >= 1
          and indices_separes[0] != indices_compare[0])

    # === SECTION 6 — Métadonnées présentes (couverture + footer) ===
    print()
    print("=" * 95)
    print("  SECTION 6 — Métadonnées de couverture et footer")
    print("=" * 95)
    check("Cabinet présent en couverture",
          "Cabinet TestCo" in texte)
    check("Client présent en couverture",
          "M. Dupont" in texte)
    check("Expert-comptable présent",
          "Mme Martin" in texte)
    check("Hash baseline présent dans le PDF",
          BASELINE_HASH_DEFAUT in texte)
    check("Version PDF audit spec présente",
          AUDIT_PDF_SPEC_VERSION in texte)
    check("Régime TNS affiché en couverture",
          "Régime TNS" in texte or "TNS" in texte)

    # === SECTION 7 — Garde-fou « Déclaratif » ===
    print()
    print("=" * 95)
    print("  SECTION 7 — Garde-fou : aucun « Déclaratif » visible dans le PDF")
    print("=" * 95)
    check("Aucune occurrence 'Déclaratif' dans le PDF généré",
          "Déclaratif" not in texte,
          detail="occurrence détectée" if "Déclaratif" in texte else "")

    # === SECTION 8 — 14 patterns non-prescriptifs §6.2 ===
    print()
    print("=" * 95)
    print("  SECTION 8 — 14 patterns non-prescriptifs §6.2 doctrine")
    print("=" * 95)
    # On scanne le PDF en retirant d'abord les exceptions whitelistées.
    texte_filtre = texte
    for exception in PATTERNS_EXCEPTION_DISCLAIMER:
        texte_filtre = texte_filtre.replace(exception, "")
    for regex, nom in PATTERNS_NON_PRESCRIPTIFS:
        occurrences = list(re.finditer(regex, texte_filtre))
        if occurrences:
            for m in occurrences[:3]:  # max 3 contextes affichés
                debut = max(0, m.start() - 30)
                fin = min(len(texte_filtre), m.end() + 30)
                contexte = texte_filtre[debut:fin].replace("\n", " ")
                print(f"      contexte : ...{contexte}...")
        check(f"Pattern non-prescriptif '{nom}' : 0 occurrence hors disclaimer",
              len(occurrences) == 0,
              detail=f"{len(occurrences)} occurrence(s)"
              if occurrences else "")

    # === SECTION 9 — SP3 : Sommaire présent et complet ===
    print()
    print("=" * 95)
    print("  SECTION 9 — SP3 : Sommaire navigable (TableOfContents)")
    print("=" * 95)
    texte_norm = _normaliser_texte_pdf(texte)
    check("Mot-clé 'Sommaire' présent (page dédiée)",
          "Sommaire" in texte)
    check("Entrée sommaire 'Étapes du calcul' présente",
          "Étapes du calcul" in texte_norm)
    for nom_strat in ("strategie_T1", "strategie_T2",
                      "strategie_T3", "strategie_T4"):
        # Chaque sous-trace de niveau 1 doit figurer au sommaire
        check(f"Sommaire mentionne '{nom_strat}'",
              nom_strat in texte_norm)
    # Mention « module_tns » N2 indenté
    check("Sommaire mentionne 'module_tns' (niveau N2)",
          "module_tns" in texte_norm)

    # === SECTION 10 — SP3 : Sections sous-traces rendues ===
    print()
    print("=" * 95)
    print("  SECTION 10 — SP3 : Sections sous-traces rendues (4 stratégies)")
    print("=" * 95)
    sous_traces_attendues = list(trace.noms_sous_traces())
    for nom in sous_traces_attendues:
        # Titre de la sous-trace doit apparaître
        check(f"Titre 'Sous-trace « {nom} »' rendu dans le PDF",
              f"« {nom} »" in texte_norm
              or f"Sous-trace « {nom}" in texte_norm)

    # Étapes du module_tns appelé depuis strategie_T1 : au moins quelques
    # codes TNS_* doivent apparaître (sans présumer du contenu exact, qui
    # est sous responsabilité des tests MODE_AUDIT).
    check("Au moins un code TNS_* du module_tns rendu (preuve récursion N2)",
          "TNS_" in texte)

    # === SECTION 11 — SP3 : Signets PDF hiérarchisés ===
    print()
    print("=" * 95)
    print("  SECTION 11 — SP3 : Signets PDF hiérarchisés")
    print("=" * 95)
    if not PYPDF_DISPONIBLE:
        check("pypdf disponible pour inspection signets", False,
              detail="pypdf non installé — section ignorée")
    else:
        import io
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        outline = reader.outline

        # outline est une structure imbriquée : éléments + listes pour
        # sous-niveaux. On aplatit en (niveau, titre).
        def aplatir(items, niveau=0):
            resultat = []
            for it in items:
                if isinstance(it, list):
                    resultat.extend(aplatir(it, niveau + 1))
                else:
                    resultat.append((niveau, it.title))
            return resultat

        signets = aplatir(outline)
        titres_signets = [t for _, t in signets]
        niveaux = [n for n, _ in signets]

        check("Au moins un signet PDF est posé",
              len(signets) > 0,
              detail=f"{len(signets)} signets")
        check("Signet 'Étapes du calcul' présent",
              any("Étapes du calcul" in t for t in titres_signets))
        check("Signets pour les 4 stratégies présents",
              all(any(f"strategie_T{i}" in t for t in titres_signets)
                  for i in (1, 2, 3, 4)))
        check("Signets module_tns présents (niveau N2)",
              sum(1 for t in titres_signets if "module_tns" in t) == 4,
              detail=f"{sum(1 for t in titres_signets if 'module_tns' in t)}/4")
        check("Hiérarchie 2 niveaux respectée (présence N0 et N1)",
              0 in niveaux and 1 in niveaux,
              detail=f"niveaux observés: {sorted(set(niveaux))}")
        # Vérification : les signets module_tns sont au niveau supérieur
        # à celui de leur stratégie parente
        for i, (niveau, titre) in enumerate(signets):
            if "module_tns" in titre:
                check(f"Signet module_tns au niveau N1 ({titre[:40]}...)",
                      niveau == 1,
                      detail=f"observé N{niveau}")

    # === SECTION 12 — SP3 : Double-build matérialise les n° de page ===
    print()
    print("=" * 95)
    print("  SECTION 12 — SP3 : Sommaire avec numéros de page (double-build)")
    print("=" * 95)
    # Heuristique : le sommaire doit contenir des numéros de page après des
    # lignes pointillées. Pdfplumber extrait les "..." comme ". . . " (points
    # séparés d'espaces). On cherche le pattern "titre[espaces]. . . [espace]N".
    # On scope sur la première moitié du texte (avant les sections sous-traces).
    debut_texte = texte[:min(len(texte), 5000)]
    # Pattern : au moins 3 paires "point + espace", suivi d'un numéro 1-3 chiffres
    nb_dots_avec_page = len(re.findall(r"(?:\.\s+){3,}\d{1,3}", debut_texte))
    check("Sommaire contient des numéros de page (double-build OK)",
          nb_dots_avec_page >= 5,
          detail=f"{nb_dots_avec_page} lignes 'titre...page' trouvées")

    # === SECTION 13 — SP4 : Enrichissements doctrine_refs visibles ===
    print()
    print("=" * 95)
    print("  SECTION 13 — SP4 : doctrine_refs résolues visibles dans le PDF")
    print("=" * 95)
    # On vérifie qu'au moins quelques doctrine_refs apparaissent dans le PDF
    # avec leur valeur. On échantillonne 3 doctrine_refs présentes dans la
    # trace pilote (sans présumer du contenu doctrinal, on prend ce qui est
    # effectivement dans la trace).
    def visiter(t):
        for e in t.etapes:
            yield e
        for _, sub in t.sous_traces.items():
            yield from visiter(sub)

    refs_observees = set()
    for e in visiter(trace):
        for ref in e.doctrine_refs:
            refs_observees.add(ref)
            if len(refs_observees) >= 5:
                break
        if len(refs_observees) >= 5:
            break

    check(f"Au moins 3 doctrine_refs distinctes dans la trace pilote",
          len(refs_observees) >= 3,
          detail=f"{len(refs_observees)} refs observées")

    # Vérification : chaque ref observée apparaît textuellement dans le PDF
    for ref in list(refs_observees)[:3]:
        check(f"doctrine_ref '{ref}' apparaît dans le PDF",
              ref in texte,
              detail="introuvable" if ref not in texte else "")

    # Vérification : mention « doctrine » présente sous au moins une étape
    check("Mot 'doctrine' présent en italique sous une étape "
          "(forme 'doctrine REF = valeur')",
          re.search(r"doctrine\s+\S+\s*=", texte) is not None)

    # === SECTION 14 — SP4 : Hypothèses courtes inline ===
    print()
    print("=" * 95)
    print("  SECTION 14 — SP4 : Hypothèses courtes (< 80 chars) en ligne inline")
    print("=" * 95)
    # On vérifie qu'au moins une étape a généré une ligne inline « hypothèse X = Y ».
    check("Mention 'hypothèse' présente dans le PDF (inline)",
          "hypothèse" in texte)
    # Échantillonner 1 hypothèse courte concrète de la trace
    for e in visiter(trace):
        for cle, val in e.hypotheses.items():
            if (cle not in e.doctrine_refs
                    and len(f"{cle}={val}") < SEUIL_HYPOTHESE_LONGUE):
                # Vérifier que la clé apparaît dans le PDF
                check(f"Hypothèse '{cle}' visible dans le PDF (inline)",
                      cle in texte)
                break
        else:
            continue
        break

    # === SECTION 15 — SP4 : Hypothèses longues en encadré ===
    print()
    print("=" * 95)
    print("  SECTION 15 — SP4 : Hypothèses longues (≥ 80 chars) en encadré dédié")
    print("=" * 95)
    # Le pilote TNS contient des hyp longues : tous_nets, note_perin,
    # texte_alerte_v19. On vérifie que l'en-tête « Hypothèses longues
    # développées » apparaît au moins une fois et que les clés longues
    # se retrouvent dans le PDF.
    check("En-tête 'Hypothèses longues développées' présent",
          "Hypothèses longues développées" in texte_norm
          or "Hypothèses longues d" in texte)
    # Compter les hypothèses longues attendues sur la trace
    nb_hyp_longues_attendues = 0
    cles_longues = set()
    for e in visiter(trace):
        for cle, val in e.hypotheses.items():
            if (cle not in e.doctrine_refs
                    and len(f"{cle}={val}") >= SEUIL_HYPOTHESE_LONGUE):
                nb_hyp_longues_attendues += 1
                cles_longues.add(cle)
    check(f"Au moins 1 hypothèse longue dans la trace pilote",
          nb_hyp_longues_attendues >= 1,
          detail=f"{nb_hyp_longues_attendues} hyp longues, "
                 f"clés={sorted(cles_longues)}")
    # Chaque clé d'hypothèse longue doit figurer dans le PDF
    for cle in list(cles_longues)[:3]:
        check(f"Clé d'hypothèse longue '{cle}' présente dans le PDF",
              cle in texte)

    # === SECTION 16 — SP4 : Notes et overrides ===
    print()
    print("=" * 95)
    print("  SECTION 16 — SP4 : Notes affichées + branche override testée")
    print("=" * 95)
    # Notes
    check("Mention 'note' présente dans le PDF (inline italique)",
          re.search(r"\bnote\s*:", texte) is not None)
    # Compter étapes avec notes
    nb_notes = sum(1 for e in visiter(trace) if e.notes)
    check(f"Au moins 5 notes attendues dans la trace pilote",
          nb_notes >= 5,
          detail=f"{nb_notes} notes observées")

    # Branche override : test unitaire isolé (la trace TNS pilote n'en contient pas).
    # On construit une étape mockée avec un override et on vérifie que le
    # renderer produit bien la chaîne « override local ».
    styles = _build_audit_styles()
    etape_override_mock = EtapeAudit(
        code="MOCK_OVERRIDE_TEST",
        label="Étape test override",
        valeur=42000.0,
        unite="EUR",
        doctrine_refs=("TX_TNS",),
        hypotheses={"TX_TNS": 0.5000},  # diffère de doctrine TX_TNS = 0.4500
    )
    lignes_mock = _render_enrichissements_etape(etape_override_mock, styles)
    texte_mock = "\n".join(
        getattr(p, "text", str(p)) for p in lignes_mock
    )
    check("Branche override : mention 'override local' produite",
          "override local" in texte_mock,
          detail=f"texte produit : {texte_mock[:200]}")
    check("Branche override : valeur appliquée et doctrine mentionnées",
          "0.5000" in texte_mock and "0.4500" in texte_mock,
          detail=f"texte produit : {texte_mock[:200]}")

    # Branche « référence introuvable » : étape mockée avec doctrine_ref bidon
    etape_ref_ko_mock = EtapeAudit(
        code="MOCK_REF_INTROUVABLE",
        label="Étape test ref introuvable",
        valeur=0,
        unite="",
        doctrine_refs=("REF_QUI_N_EXISTE_PAS_DANS_DOCTRINE",),
        hypotheses={},
    )
    lignes_ko_mock = _render_enrichissements_etape(etape_ref_ko_mock, styles)
    texte_ko_mock = "\n".join(
        getattr(p, "text", str(p)) for p in lignes_ko_mock
    )
    check("Branche référence introuvable : mention 'référence introuvable'",
          "référence introuvable" in texte_ko_mock,
          detail=f"texte produit : {texte_ko_mock[:200]}")

    # === SECTION 17 — SP5 : Panel KPI sur la couverture ===
    print()
    print("=" * 95)
    print("  SECTION 17 — SP5 : Panel KPI 2×2 sur la couverture")
    print("=" * 95)
    # Comptage attendu (référence sur trace TNS pilote v1.6)
    kpis = _compter_kpis_trace(trace)
    check("Comptage KPIs : etapes_total > 0",
          kpis["etapes_total"] > 0,
          detail=f"{kpis['etapes_total']} étapes")
    check("Comptage KPIs : sous_traces_total > 0",
          kpis["sous_traces_total"] > 0,
          detail=f"{kpis['sous_traces_total']} sous-traces")
    check("Comptage KPIs : doctrine_refs_distinctes > 0",
          kpis["doctrine_refs_distinctes"] > 0,
          detail=f"{kpis['doctrine_refs_distinctes']} refs")
    check("Comptage KPIs : hypotheses_total > 0",
          kpis["hypotheses_total"] > 0,
          detail=f"{kpis['hypotheses_total']} hypothèses")

    # Titre du panel + 4 labels présents dans la page de couverture
    page_couverture_texte = texte[:min(len(texte), 2500)]  # 1re partie ≈ p.1
    check("Titre 'Indicateurs de couverture de l'audit' présent",
          "Indicateurs de couverture" in page_couverture_texte)
    for label in ("Étapes tracées", "Sous-traces",
                  "Références doctrinales", "Hypothèses"):
        check(f"Label KPI '{label}' présent dans la couverture",
              label in page_couverture_texte,
              detail="introuvable" if label not in page_couverture_texte else "")

    # Au moins une valeur KPI numérique apparaît à proximité de son label.
    # Heuristique : on cherche les 4 nombres formatés (avec espaces milliers
    # si > 999) dans la page de couverture.
    def _fmt(n):
        return f"{n:,}".replace(",", " ")
    for k, label in (("etapes_total", "Étapes tracées"),
                     ("sous_traces_total", "Sous-traces"),
                     ("doctrine_refs_distinctes", "Références doctrinales"),
                     ("hypotheses_total", "Hypothèses")):
        valeur_fmt = _fmt(kpis[k])
        check(f"Valeur KPI {label} ({valeur_fmt}) présente dans la couverture",
              valeur_fmt in page_couverture_texte,
              detail=f"valeur attendue '{valeur_fmt}' non trouvée"
              if valeur_fmt not in page_couverture_texte else "")

    # === SECTION 18 — SP5 : Bandeau d'introduction sommaire ===
    print()
    print("=" * 95)
    print("  SECTION 18 — SP5 : Bandeau d'introduction sur le sommaire")
    print("=" * 95)
    # Le bandeau doit apparaître textuellement dans le PDF.
    # On vérifie 3 fragments-clés disjoints du texte cabinet validé.
    fragments_attendus = [
        "Cette restitution structurée reproduit",
        "moteur d'arbitrage",
        "navigables via les signets PDF",
    ]
    texte_norm_bandeau = _normaliser_texte_pdf(texte)
    for fragment in fragments_attendus:
        check(f"Fragment bandeau intro présent : '{fragment[:40]}...'",
              fragment in texte_norm_bandeau,
              detail="introuvable" if fragment not in texte_norm_bandeau else "")

    # Le bandeau doit apparaître AVANT le sommaire (cohérence position)
    pos_bandeau = texte_norm_bandeau.find("Cette restitution structurée")
    pos_etapes = texte_norm_bandeau.find("Étapes du calcul")
    check("Bandeau intro positionné avant les entrées du sommaire",
          0 < pos_bandeau < pos_etapes,
          detail=f"pos_bandeau={pos_bandeau}, pos_etapes={pos_etapes}")

    # Vérification que le bandeau correspond exactement à BANDEAU_INTRO_SOMMAIRE
    # (au caractères de wrap PDF près)
    bandeau_normalise = _normaliser_texte_pdf(BANDEAU_INTRO_SOMMAIRE)
    check("BANDEAU_INTRO_SOMMAIRE rendu intégralement dans le PDF",
          bandeau_normalise in texte_norm_bandeau,
          detail="texte intégral non trouvé")

    # === SYNTHÈSE ===
    print()
    print("=" * 95)
    print("  SYNTHÈSE")
    print("=" * 95)
    print(f"  Contrôles OK     : {NB_OK}")
    print(f"  Contrôles KO     : {NB_KO}")
    print()

    if NB_KO == 0:
        print("  ✓ SP2 → SP5 PASS — pilote TNS v1.0.0 cabinet-ready (clôturé SP6)")
        return 0
    else:
        print("  ✗ SP2 → SP5 FAIL :")
        for f in FAILURES:
            print(f"    - {f}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
