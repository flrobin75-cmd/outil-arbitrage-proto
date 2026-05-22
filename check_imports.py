"""
Validation des règles d'import canoniques.

Règle : core ← regime ← strategy ← ui ← app
       Jamais l'inverse.

À exécuter avant chaque commit. Doit retourner 0 (aucune violation).

Usage :
    python3 check_imports.py
"""

import os, re, sys
from pathlib import Path


# Règles d'import : quels niveaux ne peut-on PAS importer ?
INTERDICTIONS = {
    "core/":     ["regime", "strategy", "ui"],
    "regime/":   ["strategy", "ui"],
    "strategy/": ["ui"],
    # ui/ peut tout importer (core, regime, strategy)
    # app.py peut tout importer
}


def scan_imports(filepath: str) -> list:
    """Retourne la liste des modules importés dans le fichier."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # Patterns : "from XXX import ..." et "import XXX"
    imports = []
    for match in re.finditer(r"^(?:from|import)\s+(\S+)", content, re.MULTILINE):
        imports.append((match.group(1), match.start()))
    return imports


def line_of(content: str, pos: int) -> int:
    """Retourne le numéro de ligne pour une position dans le fichier."""
    return content[:pos].count("\n") + 1


def check_file(filepath: str, scope: str, interdits: list) -> list:
    """Retourne la liste des violations détectées."""
    violations = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    for module, pos in scan_imports(filepath):
        # Vérifier si l'import commence par un niveau interdit
        for interdit in interdits:
            if module == interdit or module.startswith(interdit + "."):
                ligne = line_of(content, pos)
                violations.append({
                    "file": filepath,
                    "scope": scope,
                    "line": ligne,
                    "import": module,
                    "interdit": interdit,
                })
    return violations


def main():
    print("=" * 80)
    print("  CHECK IMPORTS — Règles d'architecture canoniques")
    print("=" * 80)
    print()
    print("Règle : core ← regime ← strategy ← ui ← app")
    print()

    total_violations = []
    nb_fichiers = 0

    for scope, interdits in INTERDICTIONS.items():
        scope_path = Path(scope)
        if not scope_path.exists():
            continue
        print(f"▸ Scope : {scope}  (ne peut pas importer : {', '.join(interdits)})")
        for py_file in scope_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            nb_fichiers += 1
            violations = check_file(str(py_file), scope, interdits)
            if violations:
                for v in violations:
                    print(f"  ✗ {v['file']} ligne {v['line']} : "
                          f"import interdit '{v['import']}' "
                          f"(scope {v['scope']} ne peut pas dépendre de {v['interdit']}/)")
                total_violations.extend(violations)
            else:
                print(f"  ✓ {py_file.name}")
        print()

    print("━" * 80)
    if total_violations:
        print(f"  ✗ {len(total_violations)} VIOLATION(S) détectée(s) sur {nb_fichiers} fichier(s)")
        print(f"  → Corriger ces imports AVANT commit")
        sys.exit(1)
    else:
        print(f"  ✓ {nb_fichiers} fichiers scannés — règles d'import respectées")
        print(f"  Architecture canonique : core ← regime ← strategy ← ui ← app")
        sys.exit(0)


if __name__ == "__main__":
    main()
