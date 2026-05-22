"""
Test d'absence des modules-ponts — Phase B.3 finalisée.

Historique :
- Phase B.2 : ce fichier vérifiait que 34 imports historiques continuaient de
  fonctionner depuis les modules-ponts racine, après le refactoring vers
  core/ + regime/ + strategy/ + ui/.
- Phase B.3 : `app.py`, les outils baseline et les tests métier ont été migrés
  vers les couches canoniques. Les 11 modules-ponts ont été supprimés.
- À partir de B.3 finalisée : ce fichier vérifie l'INVERSE — qu'aucun module-pont
  ne subsiste à la racine, et qu'aucun import historique ne fonctionne plus.

Logique du test :
1. Aucun fichier-pont ne doit exister à la racine (11 fichiers vérifiés)
2. Aucun import des noms historiques ne doit fonctionner (doit lever ImportError)
3. Aucun fichier consommateur ne doit faire `from moteur_*` / `from utils_ui` etc.
   (vérification statique par grep sur tout le dépôt hors archives baseline_*)

Tout autre comportement = régression à diagnostiquer.

Usage :
    python3 test_backward_compat_imports.py

Sortie :
    Code 0 si tous les ponts sont effectivement absents.
    Code 1 si un pont subsiste ou si un import historique fonctionne encore.
"""

import sys
import os
import subprocess
from pathlib import Path


# Les 11 modules-ponts qui DOIVENT être absents en Phase B.3 finalisée
MODULES_PONTS = [
    "moteur.py",
    "moteur_tns.py",
    "moteur_liberal.py",
    "moteur_salarie.py",
    "moteur_comparateur.py",
    "moteur_synthese.py",
    "moteur_scenarios.py",
    "moteur_perin.py",
    "utils_ui.py",
    "export_pdf.py",
    "admin_parametres.py",
]

# Les noms d'import qui ne doivent plus fonctionner
NOMS_PONTS_IMPORT = [
    "moteur",
    "moteur_tns",
    "moteur_liberal",
    "moteur_salarie",
    "moteur_comparateur",
    "moteur_synthese",
    "moteur_scenarios",
    "moteur_perin",
    "utils_ui",
    "export_pdf",
    "admin_parametres",
]


def check(label: str, ok: bool, detail: str = "") -> tuple:
    marker = "✓" if ok else "✗"
    suffix = f"  ({detail})" if detail else ""
    line = f"  {marker} {label}{suffix}"
    return ok, line


print("=" * 95)
print("  TEST B.3 finalisée — Absence des 11 modules-ponts")
print("=" * 95)
print()

results = []
racine = Path(os.path.dirname(__file__))


# ============================================================
# Test 1 — Aucun fichier-pont ne subsiste à la racine
# ============================================================
print("  ▸ Test 1 — Absence physique des 11 fichiers-ponts")
for pont in MODULES_PONTS:
    chemin = racine / pont
    ok, line = check(f"{pont} absent du dépôt", not chemin.exists())
    print(line)
    results.append(("absence_fichier", pont, ok))
print()


# ============================================================
# Test 2 — Aucun import historique ne doit fonctionner
# ============================================================
print("  ▸ Test 2 — Absence d'imports historiques fonctionnels")
for nom in NOMS_PONTS_IMPORT:
    # Forcer le rejet du cache d'import potentiel
    for cle in list(sys.modules.keys()):
        if cle == nom or cle.startswith(f"{nom}."):
            del sys.modules[cle]
    try:
        __import__(nom)
        # Si on arrive ici, l'import a fonctionné — c'est un échec attendu inversé
        ok, line = check(f"import {nom} doit lever ImportError",
                         False, "l'import a fonctionné !")
    except ImportError:
        ok, line = check(f"import {nom} doit lever ImportError", True)
    except Exception as e:
        ok, line = check(f"import {nom} doit lever ImportError",
                         False, f"a levé {type(e).__name__}")
    print(line)
    results.append(("import_absent", nom, ok))
print()


# ============================================================
# Test 3 — Aucun fichier consommateur ne référence les ponts
# ============================================================
print("  ▸ Test 3 — Aucun consommateur ne fait `from <pont>` dans le dépôt")
pattern = r"^(from|import) (moteur|utils_ui|export_pdf|admin_parametres)"
# Scan toutes les sources sauf le test lui-même et les archives baseline_*
res = subprocess.run(
    ["grep", "-rlE", pattern, "--include=*.py",
     "--exclude=test_backward_compat_imports.py",
     "--exclude-dir=baseline_freeze_b2", "--exclude-dir=baseline_outputs",
     "--exclude-dir=baseline_outputs_b2",
     "--exclude-dir=baseline_B3_pre_g7",
     "--exclude-dir=baseline_B3_groupe_0_pre_migration",
     "--exclude-dir=baseline_B3_groupe_1_pre",
     "--exclude-dir=baseline_B3_groupe_2_pre",
     "--exclude-dir=baseline_B3_groupe_3_pre",
     "--exclude-dir=baseline_B3_groupe_4_pre",
     "--exclude-dir=baseline_B3_groupe_5_pre",
     "--exclude-dir=baseline_B3_groupe_6_pre",
     "--exclude-dir=baseline_B3_post_g6",
     "."],
    capture_output=True, text=True, cwd=str(racine),
)
fichiers_consommateurs = [f.strip() for f in res.stdout.strip().split("\n") if f.strip()]
ok_grep = len(fichiers_consommateurs) == 0
if ok_grep:
    _, line = check("aucun fichier ne consomme un module-pont", True)
    print(line)
else:
    _, line = check("aucun fichier ne consomme un module-pont",
                    False, f"{len(fichiers_consommateurs)} fichier(s)")
    print(line)
    for f in fichiers_consommateurs[:10]:
        print(f"       ⚠ {f}")
results.append(("grep_absence_consommateurs", "tous fichiers", ok_grep))
print()


# ============================================================
# Synthèse
# ============================================================
nb_ok = sum(1 for _, _, ok in results if ok)
nb_total = len(results)
print("━━━ RÉSULTAT ━━━")
print(f"  OK    : {nb_ok}/{nb_total}")
print(f"  KO    : {nb_total - nb_ok}")
print()

if nb_ok == nb_total:
    print(f"  ✓ Aucun module-pont ne subsiste — B.3 finalisée propre")
    sys.exit(0)
else:
    print(f"  ✗ Des ponts subsistent — supprimer les ponts ou les consommateurs")
    sys.exit(1)
