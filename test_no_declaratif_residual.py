"""
Test garde-fou sémantique — Phase B.2 Étape 6.

Vérifie qu'aucune occurrence visible de "Déclaratif" ne subsiste dans le
code, à l'exception des emplacements strictement autorisés (alias de
migration, documentation explicative, tests).

Couvre 3 niveaux de vérification :

1. GREP STRUCTUREL — aucune occurrence de "Déclaratif" hors whitelist :
   - core/, regime/, strategy/, ui/
   - racine (sauf modules-ponts générés)

2. NIVEAU_COULEURS_PDF ne contient PLUS "Déclaratif"
   - Vérifié via inspection directe de la constante

3. RENDU PDF — aucun PDF généré ne contient "Déclaratif"
   - Génère 6 PDF (5 régimes + cas legacy "Déclaratif")
   - Vérifie via pdfplumber qu'aucun ne contient la chaîne

Garde-fou utilisateur :
> "aucun vocabulaire Déclaratif résiduel doit devenir vrai
>   fonctionnellement, vrai visuellement, vrai sémantiquement."

Sortie : 0 si OK, 1 si violation détectée.
"""

import sys, os, re, subprocess, io
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path


# ============================================================
# Whitelist d'emplacements autorisés à contenir "Déclaratif"
# ============================================================
WHITELIST_FICHIERS = {
    # Alias historique strictement interne (résolution silencieuse)
    "ui/pdf_export.py",
    # Renderer PDF audit : mentionne uniquement l'alias legacy normalisé par _normaliser_niveau().
    "ui/pdf_audit_export.py",
    # Trace historique de migration dans la doctrine (jamais affichée à l'UI v1)
    "doctrine.py",
}

# Patterns autorisés dans les fichiers whitelistés. Toute occurrence de
# "Déclaratif" dans un fichier whitelisté doit matcher l'un de ces patterns.
PATTERNS_AUTORISES = [
    # Définition de l'alias dans pdf_export.py
    r'"Déclaratif":\s*"Conformité renforcée"',
    # Docstring / commentaire explicatif "Déclaratif" → "Conformité renforcée"
    r'"Déclaratif".*"Conformité renforcée"',
    r'"Conformité renforcée".*"Déclaratif"',
    # Docstring décrivant le legacy
    r'legacy\s*\(\s*"Déclaratif"\s*\)',
    # Commentaire de migration générique (ligne commençant par # mentionne Déclaratif)
    r'#.*Déclaratif',
    # Historique de version dans la doctrine : renommage explicite
    r'«\s*Déclaratif\s*».*«\s*Conformité renforcée\s*»',
    r'renommage.*Déclaratif',
]


def grep_declaratif(racine: Path) -> list:
    """
    Liste toutes les occurrences de 'Déclaratif' dans la racine.

    Returns:
        Liste de tuples (fichier, ligne, contenu).
    """
    result = subprocess.run(
        ["grep", "-rn", "Déclaratif",
         "core/", "regime/", "strategy/", "ui/",
         "doctrine.py", "app.py"],
        capture_output=True, text=True, cwd=str(racine)
    )
    occurrences = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        # Format : "fichier:ligne:contenu"
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        fichier, ligne, contenu = parts
        occurrences.append((fichier, int(ligne), contenu.rstrip()))
    return occurrences


def filtrer_violations(occurrences: list) -> list:
    """Retourne les occurrences qui ne sont PAS dans la whitelist."""
    violations = []
    for fichier, ligne, contenu in occurrences:
        # Fichier whitelisté → autorisé si pattern autorisé
        if fichier in WHITELIST_FICHIERS:
            # Vérifier que le contenu correspond à un pattern autorisé
            if any(re.search(p, contenu) for p in PATTERNS_AUTORISES):
                continue
            # Sinon : violation même dans un fichier whitelisté
            violations.append((fichier, ligne, contenu, "occurrence non autorisée"))
        else:
            # Fichier hors whitelist → violation absolue
            violations.append((fichier, ligne, contenu, "fichier hors whitelist"))
    return violations


def test_grep_structurel():
    """Test 1 — grep structurel sur l'arborescence."""
    print("=" * 95)
    print("  TEST 1 — GREP STRUCTUREL : Aucune occurrence 'Déclaratif' hors whitelist")
    print("=" * 95)

    racine = Path(os.path.dirname(__file__))
    occurrences = grep_declaratif(racine)
    violations = filtrer_violations(occurrences)

    print(f"\n  Occurrences totales : {len(occurrences)}")
    print(f"  Violations détectées : {len(violations)}")
    print()

    if occurrences:
        print("  Détail des occurrences :")
        for fichier, ligne, contenu in occurrences:
            is_violation = any(v[:3] == (fichier, ligne, contenu) for v in violations)
            marker = "✗ VIOLATION" if is_violation else "✓ autorisée  "
            print(f"    {marker} {fichier}:{ligne}")
            print(f"               {contenu[:100]}")
        print()

    if violations:
        print(f"  ✗ {len(violations)} violation(s) — corrigez avant de continuer")
        return False, 0, 1
    else:
        print(f"  ✓ Aucune violation : 'Déclaratif' n'apparaît qu'aux emplacements autorisés")
        return True, 1, 1


def test_niveau_couleurs_pdf():
    """Test 2 — la constante NIVEAU_COULEURS_PDF est purgée."""
    print("\n" + "=" * 95)
    print("  TEST 2 — NIVEAU_COULEURS_PDF ne contient PLUS 'Déclaratif'")
    print("=" * 95)

    from ui.pdf_export import NIVEAU_COULEURS_PDF, _ALIASES_NIVEAUX

    has_declaratif = "Déclaratif" in NIVEAU_COULEURS_PDF
    print(f"\n  NIVEAU_COULEURS_PDF.keys() : {sorted(NIVEAU_COULEURS_PDF.keys())}")
    print(f"  'Déclaratif' présent ? {'OUI' if has_declaratif else 'NON'}")

    has_alias = _ALIASES_NIVEAUX.get("Déclaratif") == "Conformité renforcée"
    print(f"  _ALIASES_NIVEAUX['Déclaratif'] = 'Conformité renforcée' ? {'OUI' if has_alias else 'NON'}")

    ok = (not has_declaratif) and has_alias
    print()
    if ok:
        print("  ✓ Migration propre : dict public purgé, alias interne en place")
    else:
        print("  ✗ Migration incomplète")
    return ok, 1 if ok else 0, 1


def test_rendu_pdf_sans_declaratif():
    """Test 3 — aucun PDF généré ne contient 'Déclaratif'."""
    print("\n" + "=" * 95)
    print("  TEST 3 — Aucun PDF généré ne contient 'Déclaratif'")
    print("=" * 95)

    from ui.pdf_export import generer_pdf_synthese, _build_pdf_salarie
    from strategy.synthese import calcul_synthese, _synthese_salarie
    from strategy.comparateur import ConfigComparateur
    from strategy.tns import arbitrage_complet_tns
    from strategy.liberal import arbitrage_complet_liberal
    from strategy.assimile import arbitrage_complet
    from core.profil import Profil

    # 6 cas couvrant tous les régimes + cas legacy
    config = ConfigComparateur()
    cas = []

    # Assimilé
    p = Profil(forme_juridique="SAS / SASU")
    arb = arbitrage_complet(p)
    s = calcul_synthese(p, arb["strategies"], config)
    cas.append(("assimile", lambda: generer_pdf_synthese(s, arb, p,
                niveau_confiance="Avancé")))

    # TNS
    p = Profil(forme_juridique="SARL (gérance majoritaire) / EURL",
               benefice_is=200_000)
    arb = arbitrage_complet_tns(p)
    s = calcul_synthese(p, arb.strategies, config)
    cas.append(("tns", lambda: generer_pdf_synthese(s, arb, p,
                niveau_confiance="Conformité renforcée")))

    # Libéral BNC
    p = Profil(forme_juridique="Profession libérale (BNC)",
               recettes_bnc=150_000)
    arb = arbitrage_complet_liberal(p)
    s = calcul_synthese(p, arb.strategies, config)
    cas.append(("liberal_bnc", lambda: generer_pdf_synthese(s, arb, p,
                niveau_confiance="Avancé")))

    # Libéral SEL
    p = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELAS",
               recettes_bnc=300_000, frais_pro_bnc=50_000)
    arb = arbitrage_complet_liberal(p)
    s = calcul_synthese(p, arb.strategies, config)
    cas.append(("liberal_sel", lambda: generer_pdf_synthese(s, arb, p,
                niveau_confiance="Cadrage")))

    # Salarié
    p_sal = Profil(forme_juridique="SAS / SASU", salaire_brut_assimile=80_000)
    s_sal = _synthese_salarie(p_sal, None, config)
    cas.append(("salarie", lambda: _build_pdf_salarie(s_sal, None, p_sal,
        cabinet_nom="Test", client_nom="Test", expert_comptable="",
        niveau_confiance="Avancé", doctrine_version="1.0.1",
        doctrine_date="01/01/2026")))

    # CAS LEGACY : passage explicite de "Déclaratif"
    p = Profil(forme_juridique="SAS / SASU")
    arb = arbitrage_complet(p)
    s = calcul_synthese(p, arb["strategies"], config)
    cas.append(("LEGACY_declaratif", lambda: generer_pdf_synthese(s, arb, p,
                niveau_confiance="Déclaratif")))

    import pdfplumber

    nb_ok = 0
    nb_total = len(cas)
    print()
    for nom, generator in cas:
        try:
            pdf_bytes = generator()
        except Exception as e:
            print(f"  ✗ {nom}: exception {e}")
            continue

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        except Exception as e:
            print(f"  ✗ {nom}: extraction text échouée {e}")
            continue

        has_declaratif = "Déclaratif" in text or "déclaratif" in text.lower()
        if has_declaratif:
            # Localiser
            for line in text.split("\n"):
                if "Déclaratif" in line or "déclaratif" in line.lower():
                    print(f"  ✗ {nom}: 'Déclaratif' trouvé dans le PDF !")
                    print(f"       Ligne : {line[:100]}")
                    break
        else:
            print(f"  ✓ {nom}: aucun 'Déclaratif' dans le PDF ({len(pdf_bytes):,} bytes)")
            nb_ok += 1

    print(f"\n  Résultat : {nb_ok}/{nb_total}")
    return nb_ok == nb_total, nb_ok, nb_total


# ============================================================
# EXÉCUTION
# ============================================================
if __name__ == "__main__":
    ok1, p1, t1 = test_grep_structurel()
    ok2, p2, t2 = test_niveau_couleurs_pdf()
    ok3, p3, t3 = test_rendu_pdf_sans_declaratif()

    print("\n" + "=" * 95)
    print("  SYNTHÈSE — GARDE-FOU SÉMANTIQUE 'Déclaratif'")
    print("=" * 95)
    print(f"  Test 1 — Grep structurel             : {'✓' if ok1 else '✗'}  ({p1}/{t1})")
    print(f"  Test 2 — NIVEAU_COULEURS_PDF purgé   : {'✓' if ok2 else '✗'}  ({p2}/{t2})")
    print(f"  Test 3 — Aucun PDF contient le terme : {'✓' if ok3 else '✗'}  ({p3}/{t3})")

    total_ok = p1 + p2 + p3
    total = t1 + t2 + t3
    print(f"\n  TOTAL : {total_ok}/{total}")

    if ok1 and ok2 and ok3:
        print("\n  ✓ Dette sémantique 'Déclaratif' totalement purgée du livrable.")
    else:
        print("\n  ✗ Dette sémantique résiduelle — corriger avant clôture")

    sys.exit(0 if (ok1 and ok2 and ok3) else 1)
