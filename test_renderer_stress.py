"""
test_renderer_stress.py — Matrice de stress du renderer PDF audit-ready.

SP12 — Phase Hardening v1.0.1 (dernière sous-passe).

Pousse volontairement le renderer dans des cas que les tests de
parcours normal (TNS / Assimilé / Libéral / Comparateur) n'exercent
pas. Le but n'est PAS d'élargir la couverture fonctionnelle mais de
**qualifier les limites** du renderer.

8 cas (4 réalistes + 4 pathologiques) :

    R1 — 1000 étapes (volumétrie extrême, anticipe PERIN/réceptacles)
    R2 — Profondeur 8 (imbrication maximale, dépasse comparateur N5)
    R3 — Hypothèse 300 chars (wording métier exhaustif)
    R4 — 40 doctrine_refs sur une étape (consolidation paramétrique)

    P1 — Sous-trace vide (trace mal construite côté métier)
    P2 — Unicode exotique (émoji, RTL arabe, combining chars)
    P3 — Valeurs anormales (None, list, dict, NaN, ±Inf)
    P4 — Code 200 chars (dépasse les bornes de calibrage SP7)

Critères de succès (Q2 = b validé) :

    - Cas réalistes (R*)  → PDF valide exigé : %PDF-, ≥ 3 ko, %%EOF,
      KPIs cohérents avec la trace.
    - Cas pathologiques (P*) → absence de crash exigée : la
      génération doit retourner des bytes ; le rendu peut être dégradé.

Discipline Q3 = γ : tout défaut bloquant cabinet serait corrigé
immédiatement ; tout défaut acceptable est tracé en dette v1.1+.
Diagnostic SP12 Phase 1 : aucun défaut bloquant observé, 1 dette
cosmétique (Unicode → rectangles noirs pour glyphes manquants).

Usage : python3 test_renderer_stress.py
Exit code 0 si tous les contrôles passent.
"""

import io
import os
import sys
import math
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import pdfplumber

from core.audit import TraceAudit, EtapeAudit
from ui.pdf_audit_export import (
    generer_pdf_audit,
    _compter_kpis_trace,
    _calibrer_col_widths,
    BORNES_CODE_MM,
    LARGEUR_UTILE_MM,
)
from reportlab.lib.units import mm


# ============================================================
# RUNNER
# ============================================================
class StressRunner:
    """Runner spécialisé pour la matrice de stress.

    Distingue les cas réalistes (R*) — exigence PDF valide complet —
    des cas pathologiques (P*) — exigence absence de crash seulement.
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
        print("  SYNTHÈSE MATRICE DE STRESS")
        print("=" * 95)
        print(f"  Contrôles OK     : {self.nb_ok}")
        print(f"  Contrôles KO     : {self.nb_ko}")
        print()
        if self.nb_ko == 0:
            print("  ✓ SP12 PASS — renderer résiste à la matrice de stress complète")
            return 0
        else:
            print("  ✗ SP12 FAIL :")
            for f in self.failures:
                print(f"    - {f}")
            return 1


# ============================================================
# HELPERS — VÉRIFICATIONS COMMUNES
# ============================================================
def _verifier_pdf_valide(runner: StressRunner, pdf_bytes: bytes,
                         prefix: str, taille_min: int = 3 * 1024) -> bool:
    """Vérifications standard de validité PDF (G1).

    Args:
        runner: StressRunner pour enregistrer les contrôles.
        pdf_bytes: PDF à vérifier.
        prefix: Préfixe pour les labels (ex. "R1").
        taille_min: Taille minimale en bytes (défaut 3 ko).

    Returns:
        True si toutes les vérifications passent.
    """
    ok_magic = pdf_bytes.startswith(b"%PDF-")
    ok_taille = len(pdf_bytes) >= taille_min
    ok_eof = b"%%EOF" in pdf_bytes[-30:]
    runner.check(f"{prefix}.PDF.1 : Magic header '%PDF-'", ok_magic)
    runner.check(f"{prefix}.PDF.2 : Taille ≥ {taille_min} bytes",
                 ok_taille,
                 detail=f"observé: {len(pdf_bytes)} bytes")
    runner.check(f"{prefix}.PDF.3 : Marqueur EOF '%%EOF'", ok_eof)
    return ok_magic and ok_taille and ok_eof


def _verifier_absence_crash(runner: StressRunner, prefix: str,
                            pdf_bytes: bytes, exception: Exception = None) -> bool:
    """Vérification minimale pour cas pathologiques (Q2=b).

    Args:
        runner: StressRunner.
        prefix: Préfixe pour le label.
        pdf_bytes: PDF généré (peut être None si crash).
        exception: Exception capturée si crash (None sinon).

    Returns:
        True si pas de crash et bytes non vides.
    """
    ok = (exception is None) and (pdf_bytes is not None) and len(pdf_bytes) > 0
    detail = f"exception={type(exception).__name__}" if exception else ""
    runner.check(f"{prefix}.NOCRASH : Génération sans exception",
                 ok, detail=detail)
    if ok:
        # Bonus : on vérifie aussi que c'est un PDF "vaguement valide"
        ok_magic = pdf_bytes.startswith(b"%PDF-")
        runner.check(f"{prefix}.PDFMAGIC : Magic header '%PDF-'", ok_magic)
    return ok


def _generer_safe(trace: TraceAudit) -> tuple:
    """Génère un PDF en capturant toute exception.

    Returns:
        (pdf_bytes, exception). L'un des deux est None.
    """
    try:
        pdf = generer_pdf_audit(
            trace, cabinet_nom="Cabinet TestCo", client_nom="M. Dupont",
            expert_comptable="Mme Martin", doctrine_date="20/05/2026",
        )
        return pdf, None
    except Exception as exc:  # noqa: BLE001
        return None, exc


# ============================================================
# CAS R1 — 1000 ÉTAPES
# ============================================================
def cas_r1_volumetrie_extreme(runner: StressRunner) -> None:
    """R1 — Volumétrie extrême : 1000 étapes.

    Anticipe PERIN / réceptacles / scénarios où un graphe complet peut
    dépasser largement le périmètre v1.0.0 actuel (412 étapes max).

    Construction : 100 étapes racines + 5 sous-traces × 180 étapes
    chacune = 1000 étapes au total.
    """
    runner.section("R1 — Volumétrie extrême : 1000 étapes (réaliste)")

    t = TraceAudit(regime="STRESS_R1",
                   profil_resume="Stress 1000 étapes")
    for i in range(100):
        t.add(code=f"R1_RACINE_{i:04d}",
              label=f"Étape racine {i}",
              valeur=float(i * 100), unite="EUR")
    for s in range(5):
        sub = TraceAudit(regime=f"Sub{s}", profil_resume="")
        for i in range(180):
            sub.add(code=f"R1_S{s}_ETAPE_{i:04d}",
                    label=f"Étape S{s}-{i}",
                    valeur=float(i * 10), unite="EUR")
        t.attacher_sous_trace(f"sub_{s}", sub)

    kpis = _compter_kpis_trace(t)
    runner.check("R1.TRACE.1 : 1000 étapes au total",
                 kpis["etapes_total"] == 1000,
                 detail=f"observé: {kpis['etapes_total']}")
    runner.check("R1.TRACE.2 : 5 sous-traces attachées",
                 kpis["sous_traces_total"] == 5,
                 detail=f"observé: {kpis['sous_traces_total']}")

    pdf, exc = _generer_safe(t)
    runner.check("R1.GEN : Génération PDF sans exception",
                 exc is None, detail=f"exception={exc}")
    if exc is None:
        # R = réaliste → PDF valide complet exigé
        _verifier_pdf_valide(runner, pdf, "R1", taille_min=50 * 1024)
        # Vérification : nombre de pages raisonnable
        with pdfplumber.open(io.BytesIO(pdf)) as pdf_doc:
            nb_pages = len(pdf_doc.pages)
        runner.check(f"R1.PAGES : ≥ 20 pages ({nb_pages} observées)",
                     nb_pages >= 20)
        # Vérification calibrage absorbe la volumétrie. Le total peut
        # être légèrement inférieur à LARGEUR_UTILE_MM si toutes les
        # colonnes butent sur leurs bornes min/max (cas où la borne
        # max de la colonne Libellé est atteinte sans pouvoir absorber
        # le reste). Comportement prévu et acceptable.
        etapes_pour_calibrage = list(t.etapes) + [
            e for s in range(5) for e in t.get_sous_trace(f"sub_{s}").etapes
        ]
        col_widths = _calibrer_col_widths(etapes_pour_calibrage)
        total_mm = sum(w / mm for w in col_widths)
        runner.check("R1.CALIBRAGE : Total col_widths ≤ LARGEUR_UTILE_MM "
                     "(pas de dépassement)",
                     total_mm <= LARGEUR_UTILE_MM + 0.1,
                     detail=f"total={total_mm:.1f} mm")


# ============================================================
# CAS R2 — PROFONDEUR 8
# ============================================================
def cas_r2_profondeur_extreme(runner: StressRunner) -> None:
    """R2 — Profondeur extrême : 8 niveaux d'imbrication.

    Dépasse le comparateur_regimes (profondeur 5) du périmètre v1.0.0.
    Anticipe une éventuelle imbrication comparateur → ligne →
    arbitrage → strategie → module → sub-module.
    """
    runner.section("R2 — Profondeur extrême : 8 niveaux (réaliste)")

    t = TraceAudit(regime="STRESS_R2",
                   profil_resume="Stress profondeur 8")
    t.add(code="R2_RACINE", label="Étape racine N0",
          valeur=0.0, unite="EUR")
    courant = t
    for niveau in range(1, 8):
        sub = TraceAudit(regime=f"N{niveau}", profil_resume="")
        sub.add(code=f"R2_N{niveau}_ETAPE", label=f"Étape N{niveau}",
                valeur=float(niveau), unite="count")
        courant.attacher_sous_trace(f"st_n{niveau}", sub)
        courant = sub

    # Calcul de profondeur effective
    def _profondeur(tr, niveau=0):
        noms = list(tr.noms_sous_traces())
        if not noms:
            return niveau
        return max(_profondeur(tr.get_sous_trace(n), niveau + 1)
                   for n in noms)

    runner.check("R2.TRACE.1 : Profondeur effective = 7 niveaux",
                 _profondeur(t) == 7,
                 detail=f"observé: {_profondeur(t)}")

    pdf, exc = _generer_safe(t)
    runner.check("R2.GEN : Génération PDF sans exception",
                 exc is None, detail=f"exception={exc}")
    if exc is None:
        _verifier_pdf_valide(runner, pdf, "R2")
        # Vérification : plafond TOC à 2 niveaux respecté (D7) même à
        # profondeur 8 (les sous-traces N2-N7 doivent toutes apparaître
        # comme N1 dans le sommaire et les signets).
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf))

            def _niveaux(items, niveau=0):
                for it in items:
                    if isinstance(it, list):
                        yield from _niveaux(it, niveau + 1)
                    else:
                        yield niveau

            niveaux_signets = set(_niveaux(reader.outline))
            runner.check("R2.TOC : Plafond signets respecté (max ≤ 1)",
                         max(niveaux_signets) <= 1,
                         detail=f"niveaux observés: {sorted(niveaux_signets)}")
        except ImportError:
            pass


# ============================================================
# CAS R3 — HYPOTHÈSE 300 CHARS
# ============================================================
def cas_r3_hypothese_longue(runner: StressRunner) -> None:
    """R3 — Hypothèse 300 chars : wording métier exhaustif.

    Anticipe des wordings doctrinaux très détaillés (alertes,
    explications réglementaires).
    """
    runner.section("R3 — Hypothèse 300 chars (réaliste)")

    long_text = ("Cette hypothèse contient un wording métier très long pour "
                 "tester la robustesse du rendu en encadré séparé. Il s'agit "
                 "d'un cas limite réaliste rencontré en pratique sur certaines "
                 "alertes doctrinales nécessitant un wording exhaustif et "
                 "didactique pour le cabinet, par exemple une mention "
                 "explicative pour le cabinet. Total environ 300 caractères.")
    assert len(long_text) >= 300, f"long_text trop court: {len(long_text)}"

    t = TraceAudit(regime="STRESS_R3", profil_resume="Stress hypothèse 300 chars")
    t.add(code="R3_HYP_LONGUE",
          label="Étape avec hypothèse longue",
          valeur=1234.56, unite="EUR",
          hypotheses={"WORDING_LONG": long_text})

    pdf, exc = _generer_safe(t)
    runner.check("R3.GEN : Génération PDF sans exception",
                 exc is None, detail=f"exception={exc}")
    if exc is None:
        _verifier_pdf_valide(runner, pdf, "R3")
        # Vérification : l'hypothèse est rendue en encadré séparé
        with pdfplumber.open(io.BytesIO(pdf)) as pdf_doc:
            texte = "\n".join((p.extract_text() or "") for p in pdf_doc.pages)
        runner.check("R3.ENCADRE : En-tête 'Hypothèses longues développées' présent",
                     "Hypothèses longues développées" in texte)
        runner.check("R3.CONTENU : Texte intégral de l'hypothèse rendu",
                     "alertes doctrinales nécessitant" in texte
                     or "alertes\ndoctrinales\nnécessitant" in texte
                     or "alertes doctrinales" in texte.replace("\n", " "))


# ============================================================
# CAS R4 — 40 DOCTRINE_REFS
# ============================================================
def cas_r4_quarante_doctrine_refs(runner: StressRunner) -> None:
    """R4 — 40 doctrine_refs sur une étape (consolidation paramétrique).

    Anticipe des étapes qui consolident de nombreuses références
    réglementaires (ex. plafonds IR avec toutes leurs sources doctrinales).
    """
    runner.section("R4 — 40 doctrine_refs sur une étape (réaliste)")

    refs = tuple(f"REF_DOCTRINE_{i:02d}" for i in range(40))
    t = TraceAudit(regime="STRESS_R4", profil_resume="Stress 40 doctrine_refs")
    t.add(code="R4_CONSOLIDATION",
          label="Étape de consolidation paramétrique",
          valeur=999999.99, unite="EUR",
          doctrine_refs=refs)

    runner.check("R4.TRACE : Étape porte bien 40 doctrine_refs",
                 len(t.etapes[0].doctrine_refs) == 40,
                 detail=f"observé: {len(t.etapes[0].doctrine_refs)}")

    pdf, exc = _generer_safe(t)
    runner.check("R4.GEN : Génération PDF sans exception",
                 exc is None, detail=f"exception={exc}")
    if exc is None:
        _verifier_pdf_valide(runner, pdf, "R4")
        # Vérification : toutes les refs sont rendues
        with pdfplumber.open(io.BytesIO(pdf)) as pdf_doc:
            texte = "\n".join((p.extract_text() or "") for p in pdf_doc.pages)
        texte_norm = texte.replace("\n", "").replace(" ", "")
        nb_refs_trouvees = sum(
            1 for ref in refs if ref in texte_norm
        )
        runner.check(f"R4.REFS : Toutes les 40 doctrine_refs présentes "
                     f"({nb_refs_trouvees}/40 observées)",
                     nb_refs_trouvees == 40,
                     detail=f"manquantes: {40 - nb_refs_trouvees}")


# ============================================================
# CAS P1 — SOUS-TRACE VIDE
# ============================================================
def cas_p1_sous_trace_vide(runner: StressRunner) -> None:
    """P1 — Sous-trace vide (aucune étape).

    Cas pathologique : un module métier mal codé pourrait attacher une
    sous-trace sans y ajouter d'étape. Le renderer doit gérer
    élégamment cette situation.
    """
    runner.section("P1 — Sous-trace vide (pathologique)")

    t = TraceAudit(regime="STRESS_P1",
                   profil_resume="Stress sous-trace vide")
    t.add(code="P1_RACINE", label="Étape racine", valeur=0.0, unite="EUR")
    sub_vide = TraceAudit(regime="VIDE", profil_resume="")
    # Aucune étape ajoutée à sub_vide
    t.attacher_sous_trace("sub_vide", sub_vide)

    pdf, exc = _generer_safe(t)
    _verifier_absence_crash(runner, "P1", pdf, exc)
    if pdf:
        # Bonus pour P1 : le renderer affiche un message dédié pour
        # signaler la sous-trace composite (comportement observé en
        # diagnostic Phase 1).
        with pdfplumber.open(io.BytesIO(pdf)) as pdf_doc:
            texte = "\n".join((p.extract_text() or "") for p in pdf_doc.pages)
        runner.check("P1.FALLBACK : Message dédié pour sous-trace composite",
                     "Aucune étape plate" in texte
                     or "sous-trace purement composite" in texte
                     or "0 au niveau racine" in texte)


# ============================================================
# CAS P2 — UNICODE EXOTIQUE
# ============================================================
def cas_p2_unicode_exotique(runner: StressRunner) -> None:
    """P2 — Unicode exotique : émoji, RTL arabe, combining chars.

    Position doctrinale v1.1.1 (clôture de la dette Unicode v1.1+ tracée
    en SP12) : *« Le renderer garantit la stabilité du PDF en présence
    de glyphes non supportés, mais pas leur restitution visuelle. »*

    Ce comportement est désormais **assumé** comme choix d'architecture
    et non comme une limite à corriger. Le produit cible un contexte
    cabinet français avec police PDF standard (Helvetica/Courier) ; les
    glyphes non-latins (émojis, scripts non-latins) sortent du périmètre
    de restitution visuelle.

    Le test ci-dessous formalise les 3 garanties contractuelles :

      1. **Pas de crash** : le PDF est produit sans exception, quelle
         que soit la nature des caractères passés en entrée.
      2. **PDF structurellement valide** : magic %PDF-, %%EOF, taille
         raisonnable.
      3. **Codes ASCII préservés** : les codes des étapes (qui sont
         toujours ASCII en pratique : namespaces `REC_`, `TNS_`, etc.)
         restent extractibles par pdfplumber, indépendamment de la
         présence de glyphes non-latins dans les labels.

    Les garanties NON tenues (explicitement documentées) :
      - Restitution visuelle des émojis : les caractères non couverts
        par la fonte sont remplacés par des rectangles noirs.
      - Restitution des scripts RTL : direction et glyphes non garantis.
      - Préservation des combining characters : peuvent être désassemblés.

    Pour un rendu propre des glyphes non-latins, il faudrait embedder
    une fonte Unicode complète (DejaVuSans, ~300 ko/PDF) et clarifier
    les licences. C'est une **bascule majeure v2.x**, pas un patch v1.x.
    """
    runner.section("P2 — Unicode exotique (comportement assumé v1.x)")

    t = TraceAudit(regime="STRESS_P2",
                   profil_resume="Stress Unicode 🎯")
    t.add(code="P2_EMOJI", label="Étape avec émoji 🎯 🇫🇷 ✓",
          valeur=100.0, unite="EUR")
    t.add(code="P2_ARABE", label="Étape العربية avec RTL",
          valeur=200.0, unite="EUR")
    t.add(code="P2_COMBINING", label="Étape avec combining e\u0301\u0303 (é̃)",
          valeur=300.0, unite="EUR")

    pdf, exc = _generer_safe(t)

    # === Garantie 1 : pas de crash ===
    _verifier_absence_crash(runner, "P2", pdf, exc)

    # === Garantie 2 : PDF structurellement valide ===
    # Si la génération a réussi, on valide aussi la structure minimale.
    if pdf is not None:
        runner.check(
            "P2.struct.1 — PDF commence par magic %PDF-",
            pdf.startswith(b"%PDF-"),
            detail=f"observé: {pdf[:8]!r}",
        )
        runner.check(
            "P2.struct.2 — PDF termine par %%EOF (tolérance trailing whitespace)",
            b"%%EOF" in pdf[-32:],
            detail=f"observé: ...{pdf[-32:]!r}",
        )
        runner.check(
            "P2.struct.3 — PDF de taille raisonnable (≥ 1 ko)",
            len(pdf) >= 1024,
            detail=f"observé: {len(pdf)} bytes",
        )

        # === Garantie 3 : codes ASCII préservés ===
        # Les codes d'étape (P2_EMOJI, P2_ARABE, P2_COMBINING) sont
        # purement ASCII et doivent rester extractibles, indépendamment
        # de la présence de glyphes non-latins dans les labels.
        import pdfplumber as _pp
        from io import BytesIO as _BytesIO
        try:
            with _pp.open(_BytesIO(pdf)) as pdf_doc:
                texte = "\n".join((p.extract_text() or "")
                                  for p in pdf_doc.pages)
            texte_normalise = texte.replace(" ", "").replace("\n", "")
            runner.check(
                "P2.contrat.1 — Code ASCII 'P2_EMOJI' extractible "
                "(la présence d'émojis dans le label n'empêche pas "
                "l'extraction du code)",
                "P2_EMOJI" in texte_normalise,
                detail="code introuvable dans le texte extrait",
            )
            runner.check(
                "P2.contrat.2 — Code ASCII 'P2_ARABE' extractible "
                "(la présence de RTL dans le label n'empêche pas "
                "l'extraction du code)",
                "P2_ARABE" in texte_normalise,
            )
            runner.check(
                "P2.contrat.3 — Code ASCII 'P2_COMBINING' extractible "
                "(la présence de combining chars dans le label n'empêche "
                "pas l'extraction du code)",
                "P2_COMBINING" in texte_normalise,
            )
        except Exception as e:
            runner.check(
                "P2.contrat.X — Extraction pdfplumber sans crash sur "
                "PDF avec Unicode exotique",
                False, detail=f"exception: {e}",
            )


# ============================================================
# CAS P3 — VALEURS ANORMALES
# ============================================================
def cas_p3_valeurs_anormales(runner: StressRunner) -> None:
    """P3 — Valeurs typées non prévues : None, list, dict, NaN, ±Inf.

    Cas pathologique : la spec EtapeAudit attend valeur: float|int|str.
    Mais un module métier mal codé pourrait passer d'autres types.
    Le renderer doit dégrader proprement (fallback str(v)) sans crash.
    """
    runner.section("P3 — Valeurs anormales (pathologique)")

    t = TraceAudit(regime="STRESS_P3",
                   profil_resume="Stress valeurs anormales")
    t.add(code="P3_NONE", label="Valeur None", valeur=None, unite="")
    t.add(code="P3_LIST", label="Valeur liste",
          valeur=[1, 2, 3], unite="")
    t.add(code="P3_DICT", label="Valeur dict",
          valeur={"a": 1}, unite="")
    t.add(code="P3_NAN", label="Valeur NaN",
          valeur=float('nan'), unite="")
    t.add(code="P3_POSINF", label="Valeur +Inf",
          valeur=float('inf'), unite="")
    t.add(code="P3_NEGINF", label="Valeur -Inf",
          valeur=float('-inf'), unite="")

    pdf, exc = _generer_safe(t)
    _verifier_absence_crash(runner, "P3", pdf, exc)
    if pdf:
        # Bonus : vérifier que chaque code apparaît bien dans le PDF
        # (le rendu de la valeur peut être un fallback `str(v)` mais
        # le code lui-même doit être présent).
        with pdfplumber.open(io.BytesIO(pdf)) as pdf_doc:
            texte = "\n".join((p.extract_text() or "") for p in pdf_doc.pages)
        texte_norm = texte.replace("\n", "").replace(" ", "")
        for code in ("P3_NONE", "P3_LIST", "P3_DICT",
                     "P3_NAN", "P3_POSINF", "P3_NEGINF"):
            runner.check(f"P3.CODE : '{code}' rendu dans le PDF",
                         code in texte_norm)


# ============================================================
# CAS P4 — CODE 200 CHARS
# ============================================================
def cas_p4_code_extreme(runner: StressRunner) -> None:
    """P4 — Code 200 chars : dépasse largement BORNES_CODE_MM[1] = 75.

    Cas pathologique : un namespace de code anormalement long. Le
    calibrage dynamique SP7 plafonne la colonne Code à 75 mm, ce qui
    contraint le wrap. Le renderer doit accepter le wrap sans crash.
    """
    runner.section("P4 — Code 200 chars (pathologique)")

    code_long = "P4_TRES_LONG_" + ("X" * 187)
    assert len(code_long) == 200, f"longueur erronée: {len(code_long)}"

    t = TraceAudit(regime="STRESS_P4",
                   profil_resume="Stress code 200 chars")
    t.add(code=code_long, label="Code de 200 caractères",
          valeur=42.0, unite="EUR")
    t.add(code="P4_NORMAL", label="Code normal pour calibrage",
          valeur=100.0, unite="EUR")

    pdf, exc = _generer_safe(t)
    _verifier_absence_crash(runner, "P4", pdf, exc)
    if pdf:
        # Bonus : vérifier que le calibrage atteint bien la borne max
        col_widths = _calibrer_col_widths(list(t.etapes))
        code_mm = col_widths[0] / mm
        runner.check(f"P4.CALIBRAGE : Col Code = borne max "
                     f"BORNES_CODE_MM[1] = {BORNES_CODE_MM[1]} mm",
                     abs(code_mm - BORNES_CODE_MM[1]) < 0.5,
                     detail=f"observé: {code_mm:.1f} mm")
        # Le code normal (P4_NORMAL) doit rester intact dans le rendu
        with pdfplumber.open(io.BytesIO(pdf)) as pdf_doc:
            texte = "\n".join((p.extract_text() or "") for p in pdf_doc.pages)
        runner.check("P4.CODE_NORMAL : Code 'P4_NORMAL' rendu intact",
                     "P4_NORMAL" in texte)


# ============================================================
# MAIN
# ============================================================
def main() -> int:
    print()
    print("=" * 95)
    print("  TEST MATRICE DE STRESS — SP12 Hardening v1.0.1")
    print("=" * 95)
    print()
    print("  8 cas : 4 réalistes (R1-R4) + 4 pathologiques (P1-P4)")
    print("  Critère : PDF valide pour R*, absence de crash pour P*")
    print()

    runner = StressRunner()

    # Cas réalistes
    cas_r1_volumetrie_extreme(runner)
    cas_r2_profondeur_extreme(runner)
    cas_r3_hypothese_longue(runner)
    cas_r4_quarante_doctrine_refs(runner)

    # Cas pathologiques
    cas_p1_sous_trace_vide(runner)
    cas_p2_unicode_exotique(runner)
    cas_p3_valeurs_anormales(runner)
    cas_p4_code_extreme(runner)

    return runner.synthese()


if __name__ == "__main__":
    sys.exit(main())
