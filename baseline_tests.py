"""
Test runner baseline — Étape 0 du chantier B.2.

Exécute tous les tests existants, capture leurs résultats dans un JSON de
référence, et calcule un hash global. Ce JSON sert de baseline pour vérifier
qu'aucun test ne casse pendant la refactorisation et les ajouts B.2.

Usage :
  python3 baseline_tests.py freeze    # Capture la baseline initiale
  python3 baseline_tests.py compare   # Compare l'état actuel à la baseline
"""

import subprocess, sys, json, hashlib, os
from datetime import datetime
from pathlib import Path

BASELINE_FILE = "baseline_tests.json"

# Tests existants à exécuter (Phase A + B.1)
TESTS = [
    {
        "module": "TNS",
        "script": "test_parite_tns_complet.py",
        "expected_total": 114,
        "tolerance": "0,01 €",
    },
    {
        "module": "Libéral",
        "script": "test_parite_liberal.py",
        "expected_total": 96,
        "tolerance": "0,01 €",
    },
    {
        "module": "Salarié",
        "script": "test_parite_salarie.py",
        "expected_total": 84,
        "tolerance": "0,01 €",
    },
    {
        "module": "Comparateur Option 2",
        "script": "test_coherence_comparateur.py",
        "expected_total": 64,
        "tolerance": "Cohérence interne",
    },
    {
        "module": "Synthèse",
        "script": "test_synthese.py",
        "expected_total": 30,
        "tolerance": "Cohérence interne",
    },
    {
        "module": "Scénarios A vs B",
        "script": "test_scenarios.py",
        "expected_total": 88,
        "tolerance": "0,01 €",
    },
    {
        "module": "PERIN mutualisé",
        "script": "test_perin.py",
        "expected_total": 28,
        "tolerance": "0,01 €",
    },
]


def hash_content(s: str) -> str:
    """Hash SHA256 du contenu, tronqué à 16 caractères."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def extraire_total(stdout: str) -> dict:
    """Parse la sortie d'un test pour extraire le nombre de validations OK/total."""
    lignes = stdout.split("\n")
    # Chercher la ligne TOTAL
    for ligne in reversed(lignes):
        if "TOTAL" in ligne and "/" in ligne:
            # Patterns possibles :
            # "TOTAL : 28/28"
            # "TOTAL : 28/28 cellules en parité"
            # "TOTAL                              : 64/64"
            import re
            match = re.search(r"(\d+)\s*/\s*(\d+)", ligne)
            if match:
                ok = int(match.group(1))
                total = int(match.group(2))
                return {"ok": ok, "total": total, "ligne_source": ligne.strip()}
    return {"ok": None, "total": None, "ligne_source": "Non trouvé"}


def executer_test(script: str) -> dict:
    """Exécute un script de test et retourne les résultats."""
    result = subprocess.run(
        ["python3", script],
        capture_output=True, text=True, cwd=".",
        timeout=300,
    )
    stdout = result.stdout
    stderr = result.stderr
    return {
        "returncode": result.returncode,
        "stdout_hash": hash_content(stdout),
        "stderr_hash": hash_content(stderr),
        "stdout_len": len(stdout),
        **extraire_total(stdout),
    }


def freeze_baseline():
    """Capture l'état actuel des tests dans baseline_tests.json."""
    print("=" * 80)
    print("  ÉTAPE 0 — FREEZE TESTS + SAUVEGARDE BASELINE")
    print("=" * 80)
    print()

    baseline = {
        "timestamp": datetime.now().isoformat(),
        "version_doctrine": None,  # rempli ci-dessous
        "tests": {},
        "summary": {},
    }

    # Récupérer version doctrine
    try:
        from doctrine import DOCTRINE_VERSION
        baseline["version_doctrine"] = DOCTRINE_VERSION
        print(f"Version doctrine : v{DOCTRINE_VERSION}")
    except ImportError:
        print("⚠ doctrine.py non importable, version inconnue")

    print()
    total_ok = 0
    total_total = 0
    nb_failures = 0

    for t in TESTS:
        print(f"  Exécution : {t['module']:30s}", end=" ", flush=True)
        result = executer_test(t["script"])
        baseline["tests"][t["module"]] = {
            **t,
            **result,
        }
        if result["returncode"] == 0 and result["ok"] is not None:
            print(f"→ {result['ok']}/{result['total']}", end=" ")
            if result["ok"] == result["total"] == t["expected_total"]:
                print("✓")
                total_ok += result["ok"]
                total_total += result["total"]
            else:
                print(f"⚠ ATTENDU {t['expected_total']}")
                nb_failures += 1
        else:
            print(f"✗ ERREUR (code {result['returncode']})")
            nb_failures += 1

    baseline["summary"] = {
        "total_ok": total_ok,
        "total_total": total_total,
        "nb_modules": len(TESTS),
        "nb_failures": nb_failures,
        "global_hash": hash_content(json.dumps(
            {m: r["stdout_hash"] for m, r in baseline["tests"].items()},
            sort_keys=True
        )),
    }

    print()
    print(f"━━━ SYNTHÈSE BASELINE ━━━")
    print(f"  Modules testés         : {len(TESTS)}")
    print(f"  Total validations OK   : {total_ok}/{total_total}")
    print(f"  Failures               : {nb_failures}")
    print(f"  Hash global baseline   : {baseline['summary']['global_hash']}")

    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=2)
    print(f"\n✓ Baseline sauvegardée dans : {BASELINE_FILE}")

    return baseline


def compare_baseline():
    """Compare l'état actuel à la baseline figée."""
    print("=" * 80)
    print("  COMPARAISON ÉTAT ACTUEL vs BASELINE")
    print("=" * 80)
    print()

    if not os.path.exists(BASELINE_FILE):
        print(f"✗ Baseline introuvable : {BASELINE_FILE}")
        print(f"  Lancez d'abord : python3 baseline_tests.py freeze")
        return False

    with open(BASELINE_FILE) as f:
        baseline = json.load(f)

    print(f"Baseline figée le : {baseline['timestamp']}")
    print(f"Version doctrine baseline : v{baseline['version_doctrine']}")
    print(f"Hash global baseline : {baseline['summary']['global_hash']}")
    print()

    nb_ok = 0
    nb_diff = 0
    nb_failures = 0

    for t in TESTS:
        module = t["module"]
        print(f"  {module:30s}", end=" ", flush=True)
        if module not in baseline["tests"]:
            print("⚠ NOUVEAU MODULE (absent de baseline)")
            continue

        base = baseline["tests"][module]
        actuel = executer_test(t["script"])

        if actuel["returncode"] != 0:
            print(f"✗ ERREUR EXÉCUTION (code {actuel['returncode']})")
            nb_failures += 1
            continue

        if actuel["ok"] != base["ok"] or actuel["total"] != base["total"]:
            print(f"⚠ RÉGRESSION : baseline {base['ok']}/{base['total']} → "
                  f"actuel {actuel['ok']}/{actuel['total']}")
            nb_diff += 1
            continue

        # Tout est OK
        print(f"✓ {actuel['ok']}/{actuel['total']}")
        nb_ok += 1

    print()
    print(f"━━━ RÉSULTAT COMPARAISON ━━━")
    print(f"  Modules conformes    : {nb_ok}/{len(TESTS)}")
    print(f"  Régressions          : {nb_diff}")
    print(f"  Erreurs exécution    : {nb_failures}")

    if nb_diff == 0 and nb_failures == 0:
        print(f"\n  ✓ AUCUNE RÉGRESSION — refactoring sécurisé")
        return True
    else:
        print(f"\n  ✗ RÉGRESSIONS DÉTECTÉES — corriger avant de continuer")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python3 baseline_tests.py [freeze|compare]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "freeze":
        freeze_baseline()
    elif cmd == "compare":
        success = compare_baseline()
        sys.exit(0 if success else 1)
    else:
        print(f"Commande inconnue : {cmd}")
        sys.exit(1)
