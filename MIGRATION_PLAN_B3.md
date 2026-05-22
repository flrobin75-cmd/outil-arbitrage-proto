# Plan de migration — Phase B.3 (migration de `app.py`)

> ✅ **PLAN EXÉCUTÉ LE 19/05/2026** — toutes les étapes G1 à G7f sont terminées. Ce document est conservé comme **trace historique** de la séquence appliquée. Les éventuelles différences entre le plan initial et l'exécution réelle sont consignées en fin de document (« Écarts entre plan et exécution »).

**Pré-requis :** Freeze B.2 + B.2.5 Hardening terminés et validés. ✅
**Objectif final :** `app.py` n'importe plus aucun module-pont racine ; les 11 modules-ponts peuvent être supprimés. ✅
**Garde-fou de méthode :** audit complet (11 suites + audit final 6 contrôles) après **chaque** groupe. ✅

---

## État de départ

`app.py` (~1500 lignes, Streamlit) importait ~30 symboles depuis les 11 modules-ponts racine. La nouvelle arborescence existait et était validée, mais `app.py` continuait à utiliser les anciens noms publics par rétrocompatibilité.

L'inventaire effectué au début de B.3 a révélé **42 symboles importés** depuis les ponts (et non 30 comme estimé), via 9 lignes `from`. Trois imports déférés supplémentaires ont été découverts en cours de G7 (cf. « Écarts entre plan et exécution »).

Les modules-ponts étaient des shims minimes (généralement `from <nouveau> import *`).

---

## Inventaire des imports actuels (à confirmer en début de B.3)

À faire en premier en B.3 :

```bash
cd tns_dev/
grep -nE "^(from|import) (moteur|utils_ui|export_pdf|admin_parametres)" app.py
```

Cela donnera la liste exhaustive. Le plan ci-dessous suit la **structure attendue**, à ajuster si l'inventaire diffère.

---

## Stratégie : migration par groupes de 5–10 imports

Chaque groupe :
1. Modifie 5–10 imports de `app.py` (et seulement ceux-là)
2. Garde **inchangé** tout le reste du fichier
3. Régénère la baseline numérique si nécessaire (en principe inutile car pas de changement métier)
4. Lance les 11 suites de tests + l'audit 6 contrôles
5. Si vert → commit, sinon → rollback et diagnostique avant retry

**Snapshot obligatoire avant chaque groupe** (dans `baseline_B3_groupe_<N>/`).

---

## Groupe 1 — `moteur_synthese` → `strategy.synthese`

**Imports concernés (estimés)**

```python
from moteur_synthese import calcul_synthese, FORFAITS_DEFAUT
```

**Cible**

```python
from strategy.synthese import calcul_synthese, FORFAITS_DEFAUT
```

**Risque :** faible. Symboles identiques.

**Audit après :** baseline 504/504, 8 suites B.2 vertes, ARCHITECTURE.md inchangé.

---

## Groupe 2 — `moteur_comparateur` → `strategy.comparateur`

**Imports concernés (estimés)**

```python
from moteur_comparateur import (
    calcul_comparateur, ConfigComparateur, FluxEpargne,
    # éventuellement helpers
)
```

**Cible**

```python
from strategy.comparateur import (
    calcul_comparateur, ConfigComparateur, FluxEpargne,
)
```

**Risque :** faible. Les helpers exposés par le pont doivent tous exister sur le module cible. À vérifier en lisant `moteur_comparateur.py` (typiquement 5–10 lignes).

---

## Groupe 3 — `moteur_tns`, `moteur_liberal`, `moteur_salarie` → couches métier

**Imports concernés**

```python
from moteur_tns import Profil, arbitrage_tns
from moteur_liberal import calcul_module_liberal
from moteur_salarie import calcul_module_salarie
```

**Cible**

```python
from core.profil import Profil
from strategy.tns import arbitrage_tns
from regime.liberal import calcul_module_liberal
from regime.salarie import calcul_module_salarie
```

⚠ **Subtilité :** `Profil` est dans `core/`, pas dans `regime/tns/`. C'est l'occasion de clarifier dans `app.py` que le profil est un objet **transversal** (foyer fiscal, régime, parts), pas une propriété TNS.

**Risque :** moyen. Imports multiples, dérive sémantique possible si `app.py` traitait `Profil` comme un objet TNS.

**Audit après :** strict — vérifier qu'aucun appel à `Profil(...)` n'a changé de signature implicitement.

---

## Groupe 4 — `moteur` → `regime.assimile` + `strategy.assimile`

**Imports concernés**

```python
from moteur import arbitrage_complet, calcul_module_assimile
```

**Cible**

```python
from regime.assimile import calcul_module_assimile
from strategy.assimile import arbitrage_complet
```

**Risque :** moyen. `arbitrage_complet` est l'entrée historique principale — vérifier qu'`app.py` n'utilise pas de constantes secondaires (FS_*, alias) exposées par `moteur.py` mais pas par les modules cibles.

**Audit après :** `test_strategy_tns.py`, `test_pdf_render_all_regimes.py` particulièrement attentifs.

---

## Groupe 5 — `utils_ui` → `ui.utils`

**Imports concernés**

```python
from utils_ui import format_eur, NIVEAU_COULEURS, # autres helpers Streamlit
```

**Cible**

```python
from ui.utils import format_eur, NIVEAU_COULEURS,
```

**Risque :** faible mais visuel — toute couleur, format ou helper Streamlit ratée se voit immédiatement à l'écran. Tester en lançant `streamlit run app.py` manuellement après migration.

---

## Groupe 6 — `export_pdf` → `ui.pdf_export`

**Imports concernés**

```python
from export_pdf import generer_pdf_synthese, # autres générateurs par régime
```

**Cible**

```python
from ui.pdf_export import generer_pdf_synthese,
```

**Risque :** moyen. Les générateurs PDF par régime (TNS, libéral BNC, libéral SEL, salarié, assimilé, TNS T4) doivent tous être accessibles depuis `ui.pdf_export`. Vérifier que les 6 PDF de référence se génèrent à l'identique (hash binaire ou taille à ±5%).

---

## Groupe 7 — Suppression des 11 modules-ponts

**Pré-requis :** plus aucun `from moteur*` / `from utils_ui` / `from export_pdf` / `from admin_parametres` ne subsiste dans `app.py`. Vérifier par grep :

```bash
grep -nE "^(from|import) (moteur|utils_ui|export_pdf|admin_parametres)" app.py
# attendu : 0 résultat
```

Puis supprimer :

```bash
rm moteur.py moteur_tns.py moteur_liberal.py moteur_salarie.py
rm moteur_comparateur.py moteur_synthese.py moteur_perin.py moteur_scenarios.py
rm utils_ui.py export_pdf.py admin_parametres.py
```

⚠ Adapter `test_backward_compat_imports.py` : les imports rétrocompat n'ont plus de sens. **Soit supprimer le test, soit le convertir en test de non-existence** (« vérifier qu'aucun module-pont ne subsiste »).

**Audit final B.3 :** 11 suites - 1 (backward_compat) + 1 (vérif non-existence) = toujours 11. Hash baseline `8863991f27f67847` toujours conservé.

---

## Garde-fous de migration

Ces règles **doivent rester valables** à chaque étape de B.3 :

1. **Aucun changement métier** dans `app.py` ne doit être fait pendant B.3. Si un bug est repéré, on le note et on le traite **après** la migration. La migration est purement un renommage d'imports.
2. **Aucune modification de signature** dans les modules cibles. Si une signature divergeait, c'est le pont qui doit être ajusté pour correspondre, pas le module cible.
3. **Baseline `8863991f27f67847`** intacte tout au long de B.3. Si elle dévie d'un seul chiffre, **stop** et diagnostique.
4. **Test manuel Streamlit** au moins une fois par groupe (lancer l'app, parcourir les écrans clés, vérifier l'export PDF d'au moins un cas).

---

## Critères de fin de B.3

✓ `app.py` n'importe plus aucun module-pont racine
✓ Les 11 modules-ponts sont supprimés du dépôt
✓ 11 suites toujours vertes (852 validations, dont l'éventuel test de non-existence)
✓ Hash baseline `8863991f27f67847` conservé
✓ Lancement manuel Streamlit OK, 6 PDF générés à l'identique
✓ `ARCHITECTURE.md` mis à jour pour refléter la disparition de la couche-pont
✓ `CHANGELOG_B3.md` créé avec récap par groupe

---

## Estimation

| Groupe | Effort estimé | Risque |
|---|---|---|
| 1 — moteur_synthese | 15 min | Faible |
| 2 — moteur_comparateur | 20 min | Faible |
| 3 — moteur_tns + liberal + salarie | 45 min | Moyen |
| 4 — moteur | 30 min | Moyen |
| 5 — utils_ui | 20 min | Faible (visuel) |
| 6 — export_pdf | 30 min | Moyen |
| 7 — Suppression ponts | 20 min | Faible |
| Audit final | 30 min | — |
| **Total estimé** | **~3h30** | |

Tient en une session avec marge pour rollback éventuel.

---

## Écarts entre plan et exécution (consigné après G7f)

### 1. Inventaire initial sous-estimé

- Plan : « ~30 imports actuels de `app.py` »
- Réel : **42 imports** (en début de fichier) + **3 imports déférés** dans des fonctions (lignes 496, 843, 1169)

Les imports déférés n'ont été révélés que par la régression du test `test_no_declaratif_residual.py` post-G7d, qui contenait lui aussi un import déféré raté (ligne 171). Quatre imports déférés au total ont dû être migrés en G7e.

**Garde-fou ajouté en conséquence :** le nouveau `test_backward_compat_imports.py` (G7c) fait un grep statique sans ancrage de début de ligne, qui capture également les imports indentés dans des fonctions. Toute réintroduction d'un import historique (même déféré) bloque la validation.

### 2. Périmètre G7 élargi à 6 sous-étapes

- Plan initial : G7 = « Suppression des 11 modules-ponts » en 20 min
- Réel : G7 a dû être découpé en **6 sous-étapes** (G7a→G7f) parce que l'inventaire post-G6 a révélé que **3 outils baseline + 9 tests métier** consommaient encore les ponts. Tout supprimer sans migrer ces consommateurs aurait cassé tout le filet de validation.

| Sous-étape | Périmètre | Effort réel |
|---|---|---|
| G7a | Migration `compare_baseline.py` + `baseline_outputs.py` (13 imports) | ~15 min |
| G7b | Migration des 9 tests métier (14 imports) | ~30 min |
| G7c | Réécriture de `test_backward_compat_imports.py` en test d'absence | ~15 min |
| G7d | `rm` des 11 ponts | 1 commande |
| G7e | Re-validation complète + correction des 4 imports déférés ratés | ~20 min |
| G7f | Mise à jour de la documentation (5 fichiers) | ~20 min |

### 3. Aucun rollback nécessaire

Tous les snapshots intermédiaires (`baseline_B3_groupe_<N>_pre/`) ont été conservés, mais aucun n'a été utilisé. Hash baseline numérique `8863991f27f67847` conservé sans interruption de G1 à G7f. Six PDF de référence : delta 0 octet vs freeze B.2 + B.2.5.

### 4. Smoke test Streamlit substitué au test manuel

Le plan prévoyait « tester en lançant `streamlit run app.py` manuellement » après G5 et G6. Un smoke test automatisé (démarrage headless 6 s, vérification que Uvicorn démarre et que l'app charge sans exception) a été exécuté en remplacement, parce que l'environnement de la session ne permet pas un test visuel interactif. Le rendu visuel complet reste à valider côté propriétaire lors d'une session locale.
