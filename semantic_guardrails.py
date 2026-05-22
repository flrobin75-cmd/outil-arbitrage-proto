"""
semantic_guardrails.py — Audit sémantique unifié (Phase B.2.5)

Ce script unifie les trois audits historiques :
- audit_final_b2_controle3.py (4 patterns historiques)
- test_no_declaratif_residual.py (Déclaratif visible PDF)
- test_terminologie_freeze.py (3 patterns terminologiques)

Et étend la couverture aux 5 nouveaux patterns décidés en B.2.5 :
- déclaratif (adjectif minuscule, suite Option 1 de la décision propriétaire)
- garanti / garantie
- sans risque
- optimal (extension du pattern optimisation)
- meilleur régime
- recommandé automatiquement

Sortie : 0 si aucune violation, 1 sinon.

Voir SEMANTIC_GUARDRAILS.md pour la doctrine, TERMINOLOGY.md pour le vocabulaire.
"""

import os, re, subprocess, sys
from pathlib import Path


# ============================================================
# SCOPE — Fichiers et répertoires scannés
# ============================================================
ROOTS_SCANNED = ["core/", "regime/", "strategy/", "ui/", "doctrine.py", "app.py"]


# ============================================================
# PATTERNS — 9 patterns surveillés
# ============================================================

# Patterns autorisés universels : tout pattern parmi cette liste est
# autorisé QUEL QUE SOIT le pattern surveillé. Évite la duplication.
WHITELIST_UNIVERSELLE = [
    # Commentaire de code
    r"^\s*#",
    # Mention dans une docstring (ligne contenant """ ou suivant un """)
    # (test imparfait sur une seule ligne, mais suffisant en pratique)
    r'"""',
    # Mention dans un test ou un fichier d'audit (le scope les exclut déjà,
    # mais on laisse la ceinture en plus des bretelles)
    r"test_.*\.py",
    r"audit_.*\.py",
    r"semantic_guardrails",
]


PATTERNS = {
    # ─────────────────────────────────────────────────────────────────
    # 1. Déclaratif (nom de niveau, capitalisé) — historique B.2 Étape 6
    "Déclaratif (nom de niveau)": {
        "description": "Vocabulaire legacy v1.0.0 (renommé en « Conformité renforcée »)",
        "regex": r"Déclaratif",
        "patterns_autorises": [
            r'"Déclaratif":\s*"Conformité renforcée"',
            r'"Déclaratif".*"Conformité renforcée"',
            r'"Conformité renforcée".*"Déclaratif"',
            r'legacy\s*\(\s*"Déclaratif"\s*\)',
            r'#.*Déclaratif',
            r'«\s*Déclaratif\s*».*«\s*Conformité renforcée\s*»',
            r'renommage.*Déclaratif',
        ],
        "severite": "bloquant",
    },
    # ─────────────────────────────────────────────────────────────────
    # 2. déclaratif (adjectif courant, minuscule) — NOUVEAU B.2.5
    "déclaratif (adjectif visible)": {
        "description": (
            "Adjectif « déclaratif » en contenu utilisateur "
            "(B.2.5 — Option 1 : audit strict)"
        ),
        # \B...\B pour matcher l'adjectif sans confondre avec le nom de niveau
        # capitalisé déjà couvert par #1
        "regex": r"déclaratif[sve]?\b",
        "patterns_autorises": [
            # Commentaire / docstring (acceptable code-side, pas affiché utilisateur)
            r"^\s*#.*déclaratif",
            r'""".*déclaratif',
            r"#.*déclaratif",
            # ─── Exception technique whitelistée (B.2.5, décision propriétaire) ───
            # doctrine.py — docstring de la classe NiveauConfiance qui décrit
            # l'usage du niveau CONFORMITE_RENFORCEE. Le mot apparaît dans le
            # texte explicatif destiné aux développeurs (Help() Python sur
            # l'Enum). Cette docstring n'est jamais affichée à l'utilisateur
            # ni rendue dans un PDF.
            # Pattern matché : ligne située à l'intérieur du bloc docstring
            # commençant ligne 53 et finissant ligne 65 de doctrine.py.
            r"préparation d'éléments déclaratifs.*SOUS VALIDATION CABINET",
        ],
        "severite": "bloquant",
    },
    # ─────────────────────────────────────────────────────────────────
    # 3. recommandée / recommandation — historique B.2 Étape 6
    "recommandée / recommandation": {
        "description": "Formulations prescriptives (interdites hors disclaimers/docstrings/code)",
        "regex": r"\brecommand[aéeé]+\b",
        "patterns_autorises": [
            # Disclaimers négatifs
            r"\bpas\s+(de\s+|une\s+)?recommand",
            r"\bne\s+constitue\s+pas\s+(une\s+)?recommand",
            r"\bne\s+formule\s+pas\s+(de\s+)?recommand",
            r"\bnon\s+d'une\s+recommand",
            r"\bjamais\s+.*recommand",
            r"\bnon\s+recommand",
            r"\bsans\s+recommand",
            r"ni\s+une\s+recommand",
            # Garde-fous explicites
            r"INTERDICTION.*recommand",
            r"PAS\s+(de|une)\s+\"?recommand",
            r'PAS\s+"recommand',
            r'PAS\s+de\s+(marqueur|formulation)\s+"',
            r'PAS\s+de\s+".+recommandé',
            r'NE\s+PAS\s+interpréter\s+comme\s+(une\s+)?recommand',
            # Mentions techniques / passive neutre
            r"analyse\s+complémentaire\s+recommand",
            r"provision\s+URSSAF.*recommand",
            r"il\s+ne\s+constitue\s+pas\s+une\s+recommand",
            # Citations legacy entre guillemets
            r'"recommandée"\.',
            r'"recommandée"\)',
            r'"recommandée"\s*—',
            r'"recommandée"\s+mécanique',
            r'recommandée\s+du\s+cabinet',
            # Patterns de docstrings descriptives
            r'pour\s+rétrocompat',
            r'clé\s+technique',
            r'historique\s*\(Phase\s+A\)',
            r'Note\s+terminologique',
            r'stratégie\s+recommandée\s+sur\s+la\s+base',
            r'dict\s+des\s+4\s+stratégies\s+\+\s+code\s+recommandée',
            r"référence le code",
            r"identifie la stratégie",
            # Tournures interprétatives en mode négatif
            r'(comme\s+)?(une\s+)?recommandation\s+automatique',
            r'recommandation\s+(au\s+sens\s+conseil|se\s+fait|se\s+fonde)',
            r'reste\s+éligible\s+à\s+la\s+recommandation',
            # Documentation / spécifications utilisateur
            r'point\s+\d+\s+de\s+la\s+recommandation\s+utilisateur',
            # Variables Python nommées 'recommandation' / 'recommandee' (sans accent : identifiant Python)
            r'^\s*recommandation\s*=',
            r'^\s*recommandee\s*[,=]',             # affectation ou passage en argument positionnel
            r'^\s*recommandee\s*:',                # annotation type dataclass
            r'Paragraph\(recommandation,',
            r'recommandee\s*=\s*max\(',            # affectation pattern courant
            r'recommandee\s*=\s*recommandee\b',    # passage de paramètre nommé
            r'"recommandee":\s*recommandee\b',     # construction de dict
            r'\["recommandee"\]',                   # accès dict par clé chaîne
            r'\[recommandee\]',                     # accès dict par variable identifiant
            r'\.recommandee\b',                     # accès attribut dataclass
            r"['\"]recommandee['\"]",               # mention de la clé dans une chaîne
            # Docstring décrivant ce que fait le champ 'recommandee' (sans accent)
            r"#\s*Code\s+de\s+la\s+stratégie\s+au\s+(meilleur|plus\s+haut)",
            r"-\s+recommandee:\s+code",            # bullet de docstring
            r"\bPAS\s+(de\s+champ\s+)?[\"']recommandee[\"']",  # garde-fou explicite
            r"champ\s+s'appelle.*PAS\s+['\"]recommandee['\"]",
            # Chaîne emboîtée : le mot « recommandé » apparaît dans une mention de garde-fou
            # comme f"recommandé » n'est jamais affiché"
            r"recommandé\s+»\s+n['e]est\s+jamais\s+affiché",
            # Disclaimers AMF
            r'ni\s+un\s+conseil.*ni\s+une\s+recommand',
            r'(ni\s+)?(une\s+)?recommandation\s+de\s+souscription',
            # Lecture Libéral SEL
            r'non\s+d\'une\s+recommand',
            r"recommandation\s+de\s+structuration",
            # B.2.5 → MODE_AUDIT (M1) — Citation pédagogique d'un terme interdit
            # avec marqueur « : INTERDIT » sur la même ligne. Permet aux modules
            # qui documentent eux-mêmes le vocabulaire proscrit de citer les
            # termes en clair, à condition d'afficher le verdict.
            # Ex : `« recommandée », « stratégie optimale » : INTERDIT`
            r"(valeur\s+correcte|stratégie\s+optimale|recommandée)[^:]*:\s*INTERDIT",
        ],
        "severite": "bloquant",
    },
    # ─────────────────────────────────────────────────────────────────
    # 4. optimisation / optimal — historique B.2 + extension B.2.5
    "optimisation / optimal": {
        "description": "Terminologie commerciale 'optimisation' / 'optimal' (interdite hors rationale)",
        "regex": r"\b(optimis[a-zé]+|optimal[a-zé]*)\b",
        "patterns_autorises": [
            r"calcul fictif d'optimisation",   # rationale L2 strategy/liberal.py
            r"#.*optim",
            r'""".*optim',
            r"rationale.*optim",
            # Mention négative : "jamais une optimisation"
            r"\bjamais\s+.*optim",
            r"\bni\s+(une\s+)?optim",
            r"\bpas\s+(d['ec]\s+|une\s+)?optim",
            # B.2.5 → MODE_AUDIT (M1) — Citation pédagogique d'un terme interdit
            # avec marqueur « : INTERDIT » sur la même ligne.
            # Ex : `« stratégie optimale » : INTERDIT`
            r"(valeur\s+correcte|stratégie\s+optimale|recommandée)[^:]*:\s*INTERDIT",
        ],
        "severite": "bloquant",
    },
    # ─────────────────────────────────────────────────────────────────
    # 5. garanti / garantie — NOUVEAU B.2.5
    "garanti / garantie": {
        "description": "Promesse de performance (interdite hors mentions négatives)",
        "regex": r"\bgaranti[ese]?\b",
        "patterns_autorises": [
            # Mention négative (« jamais ... une garantie »)
            r"\bjamais\s+.*garanti",
            r"\bni\s+(une\s+)?garanti",
            r"\bpas\s+(d['ec]\s+|une\s+)?garanti",
            r"\baucune?\s+garanti",
            r"\bne\s+constitue\s+pas\s+.*garanti",
            # Docstring / commentaire
            r"#.*garanti",
            r'""".*garanti',
            # Mention technique de la parité de tests (« parité 504/504 garantie »)
            # = mention interne validant la non-régression, pas une promesse client
            r"parité\s+\d+/\d+\s+garantie",
            r"garantie\s+par\s+(le\s+)?test",
        ],
        "severite": "bloquant",
    },
    # ─────────────────────────────────────────────────────────────────
    # 6. sans risque — NOUVEAU B.2.5
    "sans risque": {
        "description": "Qualification AMF inappropriée (aucun arbitrage n'est sans risque)",
        "regex": r"sans\s+risque",
        "patterns_autorises": [
            r"#.*sans\s+risque",
            r'""".*sans\s+risque',
            # Mention négative explicite : « pas sans risque », « n'est jamais sans risque »
            r"n['e]est\s+(jamais\s+)?sans\s+risque",
            r"\bpas\s+sans\s+risque",
        ],
        "severite": "bloquant",
    },
    # ─────────────────────────────────────────────────────────────────
    # 7. meilleur régime — NOUVEAU B.2.5
    "meilleur régime": {
        "description": "Comparatif absolu (interdit)",
        "regex": r"meilleur(e?s?)\s+régime",
        "patterns_autorises": [
            r"#.*meilleur",
            r'""".*meilleur',
            # Mention négative
            r"\bpas\s+(de\s+)?meilleur",
            r"\bjamais\s+(de\s+)?meilleur",
            r"\baucun\s+meilleur",
        ],
        "severite": "bloquant",
    },
    # ─────────────────────────────────────────────────────────────────
    # 8. recommandé automatiquement — NOUVEAU B.2.5
    "recommandé automatiquement": {
        "description": "Recommandation automatique (l'outil ne recommande jamais)",
        "regex": r"recommand[éeéà]+s?\s+automatiquement",
        "patterns_autorises": [
            r"#.*recommand.*automatiquement",
            r'""".*recommand.*automatiquement',
            # Mention négative
            r"\bpas\s+recommand[éeéà]+s?\s+automatiquement",
            r"\bjamais\s+recommand[éeéà]+s?\s+automatiquement",
            r"\bn['e]est\s+(pas\s+|jamais\s+)?recommand[éeéà]+s?\s+automatiquement",
        ],
        "severite": "bloquant",
    },
    # ─────────────────────────────────────────────────────────────────
    # 9. Agrégation T4 — historique B.2 Étape 6
    "agregation_T4": {
        "description": "Agrégation net_dirigeant_immediat + benefice_retenu_societe (interdite)",
        "regex": (
            r"(net_dirigeant_immediat\s*\+\s*benefice_retenu|"
            r"benefice_retenu.*\+\s*net_dirigeant_immediat|"
            r"total_brut|valeur_totale|patrimoine_total|somme_indicateurs|"
            r"net_dirigeant_total_t4|net_global_t4)"
        ),
        "patterns_autorises": [
            r"INTERDICTION\s+d'agréger.*net_dirigeant_immediat\s*\+\s*benefice_retenu",
        ],
        "severite": "bloquant",
    },
}


# ============================================================
# OUTILS
# ============================================================
def grep(pattern: str) -> list:
    """Renvoie les occurrences sous forme [(fichier, ligne, contenu)]."""
    res = subprocess.run(
        ["grep", "-rEn", pattern] + ROOTS_SCANNED,
        capture_output=True, text=True, cwd=".",
    )
    out = []
    for line in res.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        out.append((parts[0], int(parts[1]), parts[2].rstrip()))
    return out


def matche_autorise(contenu: str, patterns_autorises: list) -> bool:
    """Vrai si la ligne matche l'un des patterns autorisés."""
    # Whitelist universelle d'abord
    for p in WHITELIST_UNIVERSELLE:
        if re.search(p, contenu, re.IGNORECASE):
            return True
    # Patterns spécifiques au pattern surveillé
    for p in patterns_autorises:
        if re.search(p, contenu, re.IGNORECASE):
            return True
    return False


def filtrer(occ: list, patterns_autorises: list) -> tuple:
    """Sépare les occurrences en (autorisées, violations)."""
    autorisees, violations = [], []
    for f, n, c in occ:
        if matche_autorise(c, patterns_autorises):
            autorisees.append((f, n, c))
        else:
            violations.append((f, n, c))
    return autorisees, violations


# ============================================================
# EXÉCUTION
# ============================================================
def main():
    print("=" * 95)
    print("  SEMANTIC GUARDRAILS — Audit unifié v1.0.1 (Phase B.2.5)")
    print("=" * 95)
    print()

    resultats = []
    for nom, config in PATTERNS.items():
        print(f"  ▸ {nom}")
        print(f"     {config['description']}")
        occ = grep(config["regex"])
        autorisees, violations = filtrer(occ, config["patterns_autorises"])
        statut = "✓ OK" if not violations else f"✗ {len(violations)} violation(s)"
        print(
            f"     Total : {len(occ):3d} | "
            f"Autorisées : {len(autorisees):3d} | "
            f"Violations : {len(violations):3d}   {statut}"
        )

        if violations:
            print(f"     Détail :")
            for f, n, c in violations[:15]:
                snippet = c.strip()
                if len(snippet) > 90:
                    snippet = snippet[:87] + "..."
                print(f"       ✗ {f}:{n}  {snippet}")
            if len(violations) > 15:
                print(f"       ... ({len(violations) - 15} autres)")
        print()

        resultats.append((nom, len(occ), len(autorisees), len(violations)))

    # Synthèse tabulaire
    print("  " + "─" * 90)
    print(
        f"  {'Pattern':<32} {'Total':>6}  {'Autorisées':>11}  "
        f"{'Violations':>11}  Statut"
    )
    print("  " + "─" * 90)
    nb_violations_total = 0
    for nom, tot, ok, viol in resultats:
        marker = "✓ OK" if viol == 0 else f"✗ {viol} viol."
        print(
            f"  {nom:<32} {tot:>6}  {ok:>11}  {viol:>11}  {marker}"
        )
        nb_violations_total += viol
    print("  " + "─" * 90)

    print()
    if nb_violations_total == 0:
        print(f"  ✓ AUCUNE VIOLATION sur les {len(PATTERNS)} patterns scannés")
        return 0
    else:
        print(f"  ✗ {nb_violations_total} violation(s) à examiner")
        return 1


if __name__ == "__main__":
    sys.exit(main())
