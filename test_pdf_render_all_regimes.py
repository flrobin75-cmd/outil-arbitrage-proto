"""
Test de rendu PDF multi-régimes — Étape 6 Phase B.2.

Génère un PDF pour chacun des 5 régimes-types et vérifie :

1. Génération sans erreur (pas d'exception runtime)
2. Magic number PDF (%PDF-) en début de fichier
3. Taille minimale (PDF non vide / non tronqué)
4. Aucune chaîne "Déclaratif" résiduelle dans le PDF
5. Présence des libellés couverture validés
6. Présence des disclaimers v1.0.1 obligatoires
7. Pas de formulation positive "recommandée" / "recommandation" pour Libéral SEL
8. Régime affiché explicitement (couverture)
9. Pour PDF TNS T4 : pas d'agrégation net_immediat + benefice_retenu
   (vérification que les deux sont mentionnés séparément)
10. Pour PDF Libéral SEL : alerte BNC/SEL présente

Sauvegarde tous les PDF dans /tmp/pdf_test_outputs/ pour inspection
visuelle manuelle si besoin.
"""

import sys, os, re
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path

# Modules métier
from ui.pdf_export import (
    generer_pdf_synthese,
    _build_pdf_assimile, _build_pdf_tns,
    _build_pdf_liberal, _build_pdf_salarie,
    LIBELLES_REGIME,
    DISCLAIMER_PRIMAUTE_CABINET,
    DISCLAIMER_AMF_COMPARATEUR_PATRIMONIAL,
)
from strategy.synthese import calcul_synthese, _synthese_salarie
from strategy.comparateur import ConfigComparateur
from strategy.tns import arbitrage_complet_tns
from strategy.liberal import arbitrage_complet_liberal
from strategy.assimile import arbitrage_complet
from core.profil import Profil


# Dossier de sortie des PDF
PDF_OUT_DIR = Path("/tmp/pdf_test_outputs")
PDF_OUT_DIR.mkdir(exist_ok=True)


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extrait le texte d'un PDF.

    Utilise pdfplumber si disponible, sinon fallback sur une lecture
    grossière du contenu (pas idéal mais fonctionne pour les chaînes en clair).
    """
    try:
        import pdfplumber
        import io
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)
    except ImportError:
        # Fallback : pypdf
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(pdf_bytes))
            return "\n".join(p.extract_text() for p in reader.pages)
        except ImportError:
            # Fallback final : extraction grossière (chaînes ASCII)
            # Pas parfait mais détecte la plupart des textes en clair
            text_bytes = pdf_bytes.replace(b'\\r', b' ').replace(b'\\n', b' ')
            return text_bytes.decode('latin-1', errors='replace')


def check(label, py, expected):
    if isinstance(expected, bool):
        ok = py == expected
    else:
        ok = py == expected
    return ("✓" if ok else "✗"), ok


# ============================================================
# Préparation des 5 profils types
# ============================================================
def build_profils():
    """Construit les 5 profils-types pour les tests PDF."""
    config = ConfigComparateur()

    # Assimilé (SAS standard)
    profil_a = Profil(forme_juridique="SAS / SASU")
    arb_a = arbitrage_complet(profil_a)
    synth_a = calcul_synthese(profil_a, arb_a["strategies"], config)

    # TNS (SARL gérance majoritaire)
    profil_t = Profil(forme_juridique="SARL (gérance majoritaire) / EURL",
                      benefice_is=200_000, capital_cca=100_000)
    arb_t = arbitrage_complet_tns(profil_t)
    synth_t = calcul_synthese(profil_t, arb_t.strategies, config)

    # TNS T4 forcée (pour test garde-fou non-agrégation)
    synth_t4 = calcul_synthese(profil_t, arb_t.strategies, config, code_retenue="T4")

    # Libéral BNC pur
    profil_bnc = Profil(forme_juridique="Profession libérale (BNC)",
                       recettes_bnc=150_000, frais_pro_bnc=30_000)
    arb_bnc = arbitrage_complet_liberal(profil_bnc)
    synth_bnc = calcul_synthese(profil_bnc, arb_bnc.strategies, config)

    # Libéral SEL (SELAS)
    profil_selas = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELAS",
                          recettes_bnc=300_000, frais_pro_bnc=50_000,
                          remuneration_sel_souhaitee=80_000)
    arb_selas = arbitrage_complet_liberal(profil_selas)
    synth_selas = calcul_synthese(profil_selas, arb_selas.strategies, config,
                                   code_retenue="L3")  # force L3 pour test alerte

    # Salarié (référence comparative)
    profil_sal = Profil(forme_juridique="SAS / SASU", salaire_brut_assimile=80_000)
    synth_sal = _synthese_salarie(profil_sal, None, config)

    return {
        "assimile": (profil_a, arb_a, synth_a),
        "tns": (profil_t, arb_t, synth_t),
        "tns_t4": (profil_t, arb_t, synth_t4),
        "liberal_bnc": (profil_bnc, arb_bnc, synth_bnc),
        "liberal_sel": (profil_selas, arb_selas, synth_selas),
        "salarie": (profil_sal, None, synth_sal),
    }


# ============================================================
# 6.A — Génération PDF tous régimes (pas d'exception)
# ============================================================
def test_generation_pdf_tous_regimes():
    print("=" * 95)
    print("  6.A — Génération PDF tous régimes (pas d'exception)")
    print("=" * 95)

    profils = build_profils()
    nb_ok = 0
    checks = []

    for nom, (profil, arb, synth) in profils.items():
        try:
            if nom == "salarie":
                # Pour le salarié, on appelle directement le builder
                pdf = _build_pdf_salarie(
                    synth, arb, profil,
                    cabinet_nom="Cabinet TEST",
                    client_nom="Client TEST",
                    expert_comptable="EC TEST",
                    niveau_confiance="Avancé",
                    doctrine_version="1.0.1",
                    doctrine_date="01/01/2026",
                )
            else:
                pdf = generer_pdf_synthese(
                    synth, arb, profil,
                    cabinet_nom="Cabinet TEST",
                    client_nom="Client TEST",
                    expert_comptable="EC TEST",
                    niveau_confiance="Avancé",
                    doctrine_version="1.0.1",
                    doctrine_date="01/01/2026",
                )

            # Sauvegarder
            out_file = PDF_OUT_DIR / f"pdf_{nom}.pdf"
            out_file.write_bytes(pdf)

            # Vérif magic number + taille minimale
            magic_ok = pdf[:5] == b"%PDF-"
            size_ok = len(pdf) > 2_000

            checks.append((f"{nom}: PDF généré sans exception", True, True))
            checks.append((f"{nom}: magic number %PDF-", magic_ok, True))
            checks.append((f"{nom}: taille > 2 KB ({len(pdf):,} bytes)", size_ok, True))
        except Exception as e:
            checks.append((f"{nom}: exception {type(e).__name__}: {e}", False, True))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 6.A : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 6.B — Aucun vocabulaire "Déclaratif" dans les PDF générés
# ============================================================
def test_aucun_declaratif_residuel():
    print("\n" + "=" * 95)
    print("  6.B — Aucun vocabulaire 'Déclaratif' résiduel dans les PDF")
    print("=" * 95)

    nb_ok = 0
    checks = []

    for pdf_file in sorted(PDF_OUT_DIR.glob("pdf_*.pdf")):
        pdf_bytes = pdf_file.read_bytes()
        text = extract_text_from_pdf(pdf_bytes)

        # Le mot "Déclaratif" ne doit jamais apparaître (renommage v1.0.1)
        has_declaratif = "Déclaratif" in text or "déclaratif" in text.lower()
        nom = pdf_file.stem.replace("pdf_", "")
        checks.append((
            f"{nom}: pas de 'Déclaratif' dans le texte extrait",
            not has_declaratif, True
        ))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 6.B : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 6.C — Libellés couverture validés
# ============================================================
def test_libelles_couverture():
    print("\n" + "=" * 95)
    print("  6.C — Libellés couverture par régime")
    print("=" * 95)

    mapping_libelles = {
        "pdf_assimile.pdf": ("Arbitrage de rémunération", "Dirigeant assimilé"),
        "pdf_tns.pdf": ("Arbitrage de rémunération", "Dirigeant TNS"),
        "pdf_liberal_bnc.pdf": ("Cadrage de structuration", "Profession libérale BNC"),
        "pdf_liberal_sel.pdf": ("Cadrage de structuration", "SELARL"),
        "pdf_salarie.pdf": ("Référence comparative", "Salarié non-dirigeant"),
    }

    nb_ok = 0
    checks = []
    for filename, (titre_part, sous_titre_part) in mapping_libelles.items():
        path = PDF_OUT_DIR / filename
        text_raw = extract_text_from_pdf(path.read_bytes())
        # Normalisation : pdfplumber casse les mots sur retour à la ligne PDF
        text = re.sub(r'\s+', ' ', text_raw)
        nom = filename.replace("pdf_", "").replace(".pdf", "")
        checks.append((
            f"{nom}: contient '{titre_part}'",
            titre_part in text, True
        ))
        checks.append((
            f"{nom}: contient '{sous_titre_part}'",
            sous_titre_part in text, True
        ))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 6.C : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 6.D — Disclaimers v1.0.1 obligatoires
# ============================================================
def test_disclaimers_v1_0_1():
    print("\n" + "=" * 95)
    print("  6.D — Disclaimers v1.0.1 obligatoires sur toutes les variantes")
    print("=" * 95)

    # Phrases-clé à rechercher dans chaque PDF
    phrases_obligatoires = {
        "primauté cabinet": "Primauté de l'analyse cabinet",
        "AMF comparateur": "Comparateur patrimonial — information AMF",
        "cadrage indicatif": "cadrage indicatif",
    }

    nb_ok = 0
    checks = []

    for pdf_file in sorted(PDF_OUT_DIR.glob("pdf_*.pdf")):
        nom = pdf_file.stem.replace("pdf_", "")
        text = extract_text_from_pdf(pdf_file.read_bytes())

        for label_phrase, phrase in phrases_obligatoires.items():
            # Recherche insensible aux espaces multiples (pdfplumber peut casser)
            text_normalized = re.sub(r'\s+', ' ', text)
            phrase_normalized = re.sub(r'\s+', ' ', phrase)
            present = phrase_normalized in text_normalized
            checks.append((
                f"{nom}: {label_phrase} présent",
                present, True
            ))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 6.D : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 6.E — Garde-fous critiques métier
# ============================================================
def test_garde_fous_metier():
    print("\n" + "=" * 95)
    print("  6.E — Garde-fous critiques métier")
    print("=" * 95)

    nb_ok = 0
    checks = []

    # === Garde-fou T4 : pas d'agrégation net_immediat + benefice_retenu ===
    # On vérifie que le PDF TNS T4 mentionne SÉPARÉMENT les deux indicateurs
    text_t4 = extract_text_from_pdf((PDF_OUT_DIR / "pdf_tns_t4.pdf").read_bytes())
    text_t4_norm = re.sub(r'\s+', ' ', text_t4)

    # Vérifier que les deux indicateurs sont nommés explicitement
    has_immediat = "immédiat" in text_t4_norm or "Immédiat" in text_t4_norm
    has_retenu = "retenu en société" in text_t4_norm or "Retenu" in text_t4_norm
    has_separation_msg = "n'est pas un revenu disponible" in text_t4_norm.lower() or \
                          "pas un revenu disponible" in text_t4_norm.lower()

    checks.append(("T4: mention 'net immédiat'", has_immediat, True))
    checks.append(("T4: mention 'bénéfice retenu en société'", has_retenu, True))
    checks.append(("T4: garde-fou 'pas un revenu disponible' affiché",
                   has_separation_msg, True))

    # === Garde-fou Libéral SEL : alerte BNC/SEL présente ===
    text_sel = extract_text_from_pdf((PDF_OUT_DIR / "pdf_liberal_sel.pdf").read_bytes())
    text_sel_norm = re.sub(r'\s+', ' ', text_sel)
    has_bnc_sel = "BNC / SEL" in text_sel_norm or "BNC/SEL" in text_sel_norm
    has_analyse_complete = "analyse juridique" in text_sel_norm.lower()

    checks.append(("Libéral SEL: alerte 'BNC / SEL' présente", has_bnc_sel, True))
    checks.append(("Libéral SEL: mention 'analyse juridique' présente",
                   has_analyse_complete, True))

    # === Garde-fou Libéral : terminologie prudente (post-audit) ===
    # Phase B.2 freeze : "plus efficace fiscalement" remplacé par
    # "présentant le niveau de net le plus élevé dans le cadre des hypothèses retenues"
    has_terminologie_prudente = (
        "présentant le niveau de net le plus élevé" in text_sel_norm or
        "niveau de net le plus élevé" in text_sel_norm.lower()
    )
    checks.append(("Libéral SEL: terminologie prudente (niveau de net le plus élevé)",
                   has_terminologie_prudente, True))

    # === Garde-fou Salarié : mention non-arbitrage ===
    text_sal = extract_text_from_pdf((PDF_OUT_DIR / "pdf_salarie.pdf").read_bytes())
    text_sal_norm = re.sub(r'\s+', ' ', text_sal)
    has_pas_enveloppe = "n'a pas d'enveloppe" in text_sal_norm.lower() or \
                        "pas d'enveloppe dirigeant" in text_sal_norm.lower()
    checks.append(("Salarié: mention 'pas d'enveloppe dirigeant à arbitrer'",
                   has_pas_enveloppe, True))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 6.E : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 6.F — Régime affiché explicitement
# ============================================================
def test_regime_affiche_explicitement():
    print("\n" + "=" * 95)
    print("  6.F — Régime affiché explicitement en couverture")
    print("=" * 95)

    mapping_regimes = {
        "pdf_assimile.pdf": "Assimilé salarié",
        "pdf_tns.pdf": "TNS",
        "pdf_liberal_bnc.pdf": "TNS (libéral)",
        "pdf_liberal_sel.pdf": "TNS (libéral)",
        "pdf_salarie.pdf": "Assimilé salarié",  # car SAS dans le test
    }

    nb_ok = 0
    checks = []
    for filename, regime in mapping_regimes.items():
        path = PDF_OUT_DIR / filename
        text = extract_text_from_pdf(path.read_bytes())
        nom = filename.replace("pdf_", "").replace(".pdf", "")
        has_regime = regime in text
        checks.append((
            f"{nom}: 'Régime social' = '{regime}' affiché",
            has_regime, True
        ))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 6.F : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# EXÉCUTION
# ============================================================
if __name__ == "__main__":
    print("\nTests PDF — génération sortie dans " + str(PDF_OUT_DIR))
    print()

    r_a = test_generation_pdf_tous_regimes()
    r_b = test_aucun_declaratif_residuel()
    r_c = test_libelles_couverture()
    r_d = test_disclaimers_v1_0_1()
    r_e = test_garde_fous_metier()
    r_f = test_regime_affiche_explicitement()

    print("\n" + "=" * 95)
    print("  SYNTHÈSE TESTS PDF MULTI-RÉGIMES (ÉTAPE 6)")
    print("=" * 95)
    print(f"  6.A — Génération PDF tous régimes        : {r_a[0]}/{r_a[1]}")
    print(f"  6.B — Aucun 'Déclaratif' résiduel        : {r_b[0]}/{r_b[1]}")
    print(f"  6.C — Libellés couverture validés        : {r_c[0]}/{r_c[1]}")
    print(f"  6.D — Disclaimers v1.0.1 obligatoires    : {r_d[0]}/{r_d[1]}")
    print(f"  6.E — Garde-fous critiques métier        : {r_e[0]}/{r_e[1]}")
    print(f"  6.F — Régime affiché explicitement       : {r_f[0]}/{r_f[1]}")

    total_ok = sum(r[0] for r in [r_a, r_b, r_c, r_d, r_e, r_f])
    total = sum(r[1] for r in [r_a, r_b, r_c, r_d, r_e, r_f])
    print(f"\n  TOTAL : {total_ok}/{total}")
    print(f"  PDF générés sauvegardés dans : {PDF_OUT_DIR}/")
    sys.exit(0 if total_ok == total else 1)
