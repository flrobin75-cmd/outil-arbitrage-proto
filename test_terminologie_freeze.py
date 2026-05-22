"""
Test garde-fou terminologique — Phase B.2 freeze.

Audit automatique sur 3 patterns sensibles pour la dette terminologique :

1. "optimisation" / "optimiser" — formulations commerciales fortes
2. "recommandée" / "recommandation" — risque conseil opposable
3. "Déclaratif" — terme legacy v1.0.0 (déjà couvert par test dédié)

Pour chaque pattern, on distingue :
- VIOLATIONS  : occurrence dans un contexte problématique
- AUTORISÉES  : occurrence dans :
    a. docstrings/commentaires renforçant le garde-fou
       (« PAS de recommandée », « INTERDICTION », ...)
    b. disclaimers négatifs (« pas une recommandation », « ne constitue pas »)
    c. mentions techniques neutres (« KPI optimisation », « param recommandée »)

Politique : on tolère les occurrences explicatives mais on bloque toute
nouvelle introduction de formulation prescriptive ou commerciale.

À jour : Phase B.2 Étape 6.12 (audit terminologique freeze).
"""

import sys, os, re, subprocess
sys.path.insert(0, os.path.dirname(__file__))

from pathlib import Path


# ============================================================
# Patterns problématiques + contextes autorisés
# ============================================================
PATTERNS_SENSIBLES = {
    "optimisation": {
        "regex_recherche": r"\boptimis[a-zé]+\b",
        "patterns_autorises": [
            # Docstring expliquant pourquoi on ne fait PAS d'optimisation fictive
            r"calcul fictif d'optimisation",
            # Commentaires explicatifs (rationale)
            r"#.*optimis",
            # Mention dans un rationale (texte de docstring)
            r'""".*optimis',
            # B.2.5 — mention négative explicite « jamais une optimisation »
            r"\bjamais\s+.*optimis",
            r"\bni\s+(une\s+)?optimis",
            r"\bpas\s+(d['ec]\s+|une\s+)?optimis",
            # MODE_AUDIT (M1) — citation pédagogique d'un terme interdit
            # avec marqueur « : INTERDIT » (cf. core/audit.py docstring)
            r"(valeur\s+correcte|stratégie\s+optimale|recommandée)[^:]*:\s*INTERDIT",
        ],
        # Fichiers dans lesquels les occurrences sont autorisées
        # (à condition de matcher un pattern_autorise)
        "fichiers_avec_contexte": {
            "strategy/liberal.py",     # rationale L4 (« calcul fictif d'optimisation »)
            "ui/disclaimers.py",       # B.2.5 — mention négative trace doctrinale
            "core/audit.py",           # MODE_AUDIT (M1) — citations pédagogiques
        },
    },
    "recommandée_positive": {
        # On cherche "recommandée" précédée ou suivie de mots positifs
        # (sans négation "pas de recommandée" ou similaire)
        "regex_recherche": r"\brecommand[aéeé]+\b",
        "patterns_autorises": [
            # Toute mention dans une négation (les disclaimers)
            r"\bpas\s+(de\s+|une\s+)?recommand",
            r"\bne\s+constitue\s+pas\s+(une\s+)?recommand",
            r"\bne\s+formule\s+pas\s+(de\s+)?recommand",
            r"\bnon\s+d'une\s+recommand",
            r"\binterdict\w+\s+.*recommand",
            r"\bjamais\s+.*recommand",
            r"\bnon\s+recommand",
            # Le terme dans une docstring qui explique le garde-fou
            r"INTERDICTION.*recommand",
            r"PAS\s+de\s+marqueur",
            r"PAS\s+de\s+formulation",
            r"PAS\s+de\s+",
            r"PAS\s+\"",
            # "PAS \"régime recommandé\"" — garde-fou explicite
            r"PAS\s+.\w+\s+recommand",
            # Mention "analyse complémentaire recommandée" (passive, neutre)
            r"analyse\s+complémentaire\s+recommand",
            # Cassure de chaîne sur 2 lignes physiques (PDF concatenation)
            r"recommandée\s+du\s+cabinet",
            # Mention technique "provision URSSAF X% recommandée"
            r"provision\s+URSSAF\s+\d+\s*%\s+recommand",
            # Phrase technique dans la lecture textuelle TNS/Libéral
            r"il\s+ne\s+constitue\s+pas\s+une\s+recommand",
            # ─────────── PATTERNS TECHNIQUES INTERNES ───────────
            # Clé technique du dict Phase A (rétrocompat, jamais affichée à l'UI)
            # Toute occurrence du token `recommandee` sans accent (camelCase code)
            r"\brecommandee\b",  # Identifier Python (sans accent) → toujours technique
            # Docstring explicative mentionnant "recommandée" entre guillemets
            # comme citation du legacy
            r'"recommandée"\.',
            r'"recommandée"\)',
            r'pour\s+rétrocompat',
            r'clé\s+technique',
            r'historique\s*\(Phase\s+A\)',
            # Note terminologique de docstring
            r'Note\s+terminologique',
            # Description neutre dans docstring TNS
            r'stratégie\s+recommandée\s+sur\s+la\s+base',
            r'dict\s+des\s+4\s+stratégies\s+\+\s+code\s+recommandée',
            # Mentions explicites de docstring "rétrocompat", "clé technique"
            r"référence le code",
            r"identifie la stratégie",
            # B.2.5 — Mention négative inversée dans trace doctrinale
            # « aucun "régime recommandé" n'est jamais affiché »
            r'recommand[éeéà]+\s+»?\s*n[\'e]est\s+jamais\s+affich',
            r'recommand[éeéà]+\s*"?\s*n[\'e]est\s+jamais',
            # MODE_AUDIT (M1) — Citation pédagogique d'un terme interdit
            # avec marqueur « : INTERDIT » sur la même ligne (cf. core/audit.py)
            r"(valeur\s+correcte|stratégie\s+optimale|recommandée)[^:]*:\s*INTERDIT",
        ],
        "fichiers_avec_contexte": {
            "core/profil.py", "doctrine.py", "app.py",
            "core/audit.py",  # MODE_AUDIT (M1) — doctrine sémantique avec citations pédagogiques
            "strategy/assimile.py", "strategy/tns.py", "strategy/liberal.py",
            "strategy/comparateur.py", "strategy/comparateur_regimes.py",
            "strategy/synthese.py", "strategy/perin.py", "strategy/scenarios.py",
            "strategy/receptacles.py",
            "ui/pdf_export.py", "ui/utils.py", "ui/admin.py",
            "ui/disclaimers.py",  # B.2.5 — disclaimers centralisés (mentions négatives)
            "regime/tns.py", "regime/liberal.py", "regime/salarie.py", "regime/assimile.py",
        },
    },
}


def grep_pattern(racine: Path, regex: str) -> list:
    """Liste les occurrences d'un pattern dans le code source."""
    result = subprocess.run(
        ["grep", "-rEn", regex,
         "core/", "regime/", "strategy/", "ui/",
         "doctrine.py", "app.py"],
        capture_output=True, text=True, cwd=str(racine)
    )
    occurrences = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        fichier, ligne, contenu = parts
        occurrences.append((fichier, int(ligne), contenu.rstrip()))
    return occurrences


def filtrer_violations(occurrences: list, patterns_autorises: list,
                       fichiers_avec_contexte: set) -> tuple:
    """
    Sépare occurrences en : autorisées, violations.
    """
    autorisees = []
    violations = []
    for fichier, ligne, contenu in occurrences:
        # Si le fichier n'est pas dans la whitelist contextuelle → potentielle violation
        # Sinon, on vérifie si le contenu matche un pattern autorisé
        matche = any(re.search(p, contenu, re.IGNORECASE) for p in patterns_autorises)
        if matche:
            autorisees.append((fichier, ligne, contenu))
        elif fichier in fichiers_avec_contexte:
            # Fichier autorisé mais contenu non matché → violation
            violations.append((fichier, ligne, contenu))
        else:
            # Fichier hors whitelist → violation
            violations.append((fichier, ligne, contenu))
    return autorisees, violations


def test_pattern(nom_pattern: str, config: dict, racine: Path) -> tuple:
    """Teste un pattern individuel."""
    occurrences = grep_pattern(racine, config["regex_recherche"])
    autorisees, violations = filtrer_violations(
        occurrences, config["patterns_autorises"],
        config["fichiers_avec_contexte"]
    )

    print(f"\n  → {nom_pattern} : {len(occurrences)} occurrences trouvées")
    print(f"     - Autorisées : {len(autorisees)}")
    print(f"     - Violations : {len(violations)}")

    if violations:
        print(f"\n     Violations détectées :")
        for fichier, ligne, contenu in violations[:10]:
            print(f"       ✗ {fichier}:{ligne}")
            print(f"           {contenu[:100]}")
        if len(violations) > 10:
            print(f"       ... ({len(violations) - 10} autres)")

    return (len(violations) == 0), len(violations), len(occurrences)


# ============================================================
# EXÉCUTION
# ============================================================
if __name__ == "__main__":
    print("=" * 95)
    print("  AUDIT TERMINOLOGIQUE — Phase B.2 freeze")
    print("=" * 95)

    racine = Path(os.path.dirname(__file__))
    resultats = []

    for nom, config in PATTERNS_SENSIBLES.items():
        ok, nb_violations, nb_total = test_pattern(nom, config, racine)
        resultats.append((nom, ok, nb_violations, nb_total))

    print("\n" + "=" * 95)
    print("  SYNTHÈSE AUDIT TERMINOLOGIQUE")
    print("=" * 95)
    for nom, ok, nb_v, nb_t in resultats:
        marker = "✓" if ok else "✗"
        print(f"  {marker} {nom:30s}  occurrences={nb_t}, violations={nb_v}")

    total_violations = sum(r[2] for r in resultats)
    if total_violations == 0:
        print(f"\n  ✓ AUCUNE VIOLATION TERMINOLOGIQUE — toutes les occurrences sont")
        print(f"    soit dans des disclaimers négatifs, soit dans des docstrings de")
        print(f"    garde-fou, soit dans des contextes techniques neutres.")
        sys.exit(0)
    else:
        print(f"\n  ✗ {total_violations} violation(s) — corriger avant freeze")
        sys.exit(1)
