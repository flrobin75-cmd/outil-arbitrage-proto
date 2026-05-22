"""
Audit final Phase B.2 — Contrôle 3 raffiné.

Scanne 4 patterns sensibles dans l'arborescence avec whitelists correctement
calibrées pour distinguer vrais positifs et faux positifs.

Patterns surveillés :
- Déclaratif       : vocabulaire legacy (doit avoir disparu)
- recommandée      : formulations prescriptives (interdites hors disclaimers/docstrings)
- optimisation     : terminologie commerciale (interdite hors rationale documenté)
- agregation_T4    : addition net_dirigeant_immediat + benefice_retenu_societe (interdite)

Pour le pattern T4, on vérifie spécifiquement qu'aucune fonction n'opère
sur des objets ResultatStrategieTNS pour produire un total agrégé.
"""

import os, re, subprocess
from pathlib import Path


# ============================================================
# CONFIG DES 4 PATTERNS
# ============================================================
PATTERNS = {
    # ─────────────────────────────────────────────────────────────────
    "Déclaratif": {
        "description": "Vocabulaire legacy v1.0.0 (renommé en 'Conformité renforcée')",
        "regex": r"Déclaratif",
        "patterns_autorises": [
            r'"Déclaratif":\s*"Conformité renforcée"',  # alias dans pdf_export
            r'"Déclaratif".*"Conformité renforcée"',     # docstring explicative
            r'legacy\s*\(\s*"Déclaratif"\s*\)',          # docstring _normaliser_niveau
            r'#.*Déclaratif',                             # commentaire de migration
            r'«\s*Déclaratif\s*».*«\s*Conformité renforcée\s*»',  # historique doctrine
            r'renommage.*Déclaratif',                     # idem
        ],
    },
    # ─────────────────────────────────────────────────────────────────
    "recommandée_visible": {
        "description": "Formulations prescriptives (interdites hors disclaimers/docstrings/code)",
        "regex": r"recommandée|recommandation|recommandé[^e]",
        "patterns_autorises": [
            # ═══ Disclaimers négatifs ═══
            r"\bpas\s+(de\s+|une\s+)?recommand",
            r"\bne\s+constitue\s+pas\s+(une\s+)?recommand",
            r"\bne\s+formule\s+pas\s+(de\s+)?recommand",
            r"\bnon\s+d'une\s+recommand",
            r"\bjamais\s+.*recommand",
            r"\bnon\s+recommand",
            r"\bsans\s+recommand",
            r"ni\s+une\s+recommand",
            # ═══ Garde-fous explicites ═══
            r"INTERDICTION.*recommand",
            r"PAS\s+(de|une)\s+\"?recommand",
            r'PAS\s+"recommand',
            r'PAS\s+de\s+(marqueur|formulation)\s+"',
            r'PAS\s+de\s+".+recommandé',           # garde-fou « PAS de "régime recommandé" »
            r'NE\s+PAS\s+interpréter\s+comme\s+(une\s+)?recommand',
            # ═══ Mentions techniques / passive neutre ═══
            r"analyse\s+complémentaire\s+recommand",
            r"provision\s+URSSAF.*recommand",
            r"il\s+ne\s+constitue\s+pas\s+une\s+recommand",
            # ═══ Citations legacy entre guillemets ═══
            r'"recommandée"\.',
            r'"recommandée"\)',
            r'"recommandée"\s*—',
            r'"recommandée"\s+mécanique',
            r'recommandée\s+du\s+cabinet',
            # ═══ Patterns de docstrings descriptives ═══
            r'pour\s+rétrocompat',
            r'clé\s+technique',
            r'historique\s*\(Phase\s+A\)',
            r'Note\s+terminologique',
            r'stratégie\s+recommandée\s+sur\s+la\s+base',
            r'dict\s+des\s+4\s+stratégies\s+\+\s+code\s+recommandée',
            r"référence le code",
            r"identifie la stratégie",
            # ═══ Tournures interprétatives en mode négatif ═══
            r'(comme\s+)?(une\s+)?recommandation\s+automatique',
            r'recommandation\s+(au\s+sens\s+conseil|se\s+fait|se\s+fonde)',
            r'reste\s+éligible\s+à\s+la\s+recommandation',
            # ═══ Documentation / spécifications utilisateur ═══
            r'point\s+\d+\s+de\s+la\s+recommandation\s+utilisateur',
            # ═══ Variables Python nommées 'recommandation' ═══
            r'^\s*recommandation\s*=',
            r'Paragraph\(recommandation,',
            # ═══ Disclaimers AMF ═══
            r'ni\s+un\s+conseil.*ni\s+une\s+recommand',
            r'(ni\s+)?(une\s+)?recommandation\s+de\s+souscription',
            # ═══ Lecture Libéral SEL ═══
            r'non\s+d\'une\s+recommand',
            r"recommandation\s+de\s+structuration",
            # ═══ B.2.5 — Mention négative inversée dans trace doctrinale ═══
            # « aucun "régime recommandé" n'est jamais affiché »
            r'recommand[éeéà]+\s+»?\s*n[\'e]est\s+jamais\s+affich',
            r'recommand[éeéà]+\s*"?\s*n[\'e]est\s+jamais',
            # ═══ MODE_AUDIT (M1) — Citation pédagogique d'un terme interdit ═══
            # avec marqueur « : INTERDIT » sur la même ligne (cf. core/audit.py).
            r"(valeur\s+correcte|stratégie\s+optimale|recommandée)[^:]*:\s*INTERDIT",
        ],
    },
    # ─────────────────────────────────────────────────────────────────
    "optimisation_visible": {
        "description": "Terminologie commerciale 'optimisation' (interdite hors rationale documenté)",
        "regex": r"\boptimis[a-zé]+\b",
        "patterns_autorises": [
            r"calcul fictif d'optimisation",
            r"#.*optimis",
            r"rationale.*optimis",
            # B.2.5 — mention négative explicite « jamais une optimisation »
            r"\bjamais\s+.*optimis",
            r"\bni\s+(une\s+)?optimis",
            r"\bpas\s+(d['ec]\s+|une\s+)?optimis",
            # MODE_AUDIT (M1) — citation pédagogique d'un terme interdit
            r"(valeur\s+correcte|stratégie\s+optimale|recommandée)[^:]*:\s*INTERDIT",
        ],
    },
    # ─────────────────────────────────────────────────────────────────
    "agregation_T4": {
        "description": "Agrégation net_dirigeant_immediat + benefice_retenu_societe (interdite)",
        "regex": r"(net_dirigeant_immediat\s*\+\s*benefice_retenu|benefice_retenu.*\+\s*net_dirigeant_immediat|total_brut|valeur_totale|patrimoine_total|somme_indicateurs|net_dirigeant_total_t4|net_global_t4)",
        "patterns_autorises": [
            # Définition du garde-fou lui-même (docstring strategy/tns.py)
            r"INTERDICTION\s+d'agréger.*net_dirigeant_immediat\s*\+\s*benefice_retenu",
        ],
    },
}


# ============================================================
# Outils
# ============================================================
def grep(pattern: str) -> list:
    """Renvoie les occurrences sous forme (fichier, ligne, contenu)."""
    res = subprocess.run(
        ["grep", "-rEn", pattern,
         "core/", "regime/", "strategy/", "ui/", "doctrine.py", "app.py"],
        capture_output=True, text=True, cwd="."
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


def filtrer(occ: list, patterns_autorises: list) -> tuple:
    """Sépare occurrences en autorisées vs violations."""
    autorisees, violations = [], []
    for f, n, c in occ:
        if any(re.search(p, c, re.IGNORECASE) for p in patterns_autorises):
            autorisees.append((f, n, c))
        else:
            violations.append((f, n, c))
    return autorisees, violations


# ============================================================
# Exécution
# ============================================================
def main():
    print("=" * 95)
    print("  AUDIT FINAL PHASE B.2 — Contrôle 3 raffiné")
    print("=" * 95)

    resultats = []
    for nom, config in PATTERNS.items():
        print(f"\n  ▸ {nom}")
        print(f"     {config['description']}")
        occ = grep(config["regex"])
        autorisees, violations = filtrer(occ, config["patterns_autorises"])
        print(f"     Total : {len(occ)} | Autorisées : {len(autorisees)} | Violations : {len(violations)}")

        if violations:
            print(f"     Détail :")
            for f, n, c in violations[:10]:
                print(f"       ✗ {f}:{n}  {c[:90]}")
            if len(violations) > 10:
                print(f"       ... ({len(violations) - 10} autres)")

        resultats.append((nom, len(occ), len(autorisees), len(violations)))

    # Synthèse
    print()
    print("  " + "─" * 90)
    print(f"  {'Pattern':<25} {'Total':<8} {'Autorisées':<12} {'Violations':<12} {'Statut'}")
    print("  " + "─" * 90)
    nb_violations_total = 0
    for nom, tot, ok, viol in resultats:
        statut = "✓ OK" if viol == 0 else f"✗ {viol} viol."
        print(f"  {nom:<25} {tot:<8} {ok:<12} {viol:<12} {statut}")
        nb_violations_total += viol

    print()
    if nb_violations_total == 0:
        print(f"  ✓ AUCUNE VIOLATION sur les 4 patterns scannés")
        return 0
    else:
        print(f"  ✗ {nb_violations_total} violation(s) à examiner")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
