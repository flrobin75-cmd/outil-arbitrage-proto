# Session 19/05/2026 — B.3 finalisée (ponts supprimés)

**Statut final :** ✓ B.3 entièrement terminée. Hash baseline `8863991f27f67847` conservé bout en bout. 0 module-pont, 0 import historique fonctionnel, 11 suites + 4 audits + 23 vérifications absence ponts au vert.

---

## 1. Point de départ de la session

État post-G6 du tour précédent : `app.py` migré, 11 ponts encore présents mais plus consommés par `app.py`. Reste à faire : G7 (migration des autres consommateurs + suppression des ponts).

Note : suite à un dépassement de quota Claude.ai intermédiaire, la session avait été coupée. Reprise du travail à partir de l'archive `snapshot_tns_dev_post_g6.tar.gz` et de `NOTE_REPRISE_G7.md` qui avaient été livrées avant la coupure.

## 2. G7 — Suppression des modules-ponts (6 sous-étapes)

### G7a — Migration des outils baseline

- `compare_baseline.py` : 6 imports migrés (ponts → couches canoniques)
- `baseline_outputs.py` : 7 imports migrés
- Audit : `compare_baseline.py` → 16/16, hash baseline inchangé

### G7b — Migration des 9 tests métier

| Fichier | Imports migrés |
|---|---|
| `test_coherence_comparateur.py` | 2 |
| `test_etape4.py` | 1 |
| `test_parite_liberal.py` | 2 |
| `test_parite_salarie.py` | 2 |
| `test_parite_tns_complet.py` | 1 |
| `test_pdf_render_all_regimes.py` | 1 |
| `test_perin.py` | 1 |
| `test_scenarios.py` | 1 |
| `test_synthese.py` | 3 |

Audit : 504/504 baseline + 282 tests B.2 chiffrés toujours verts.

### G7c — Réécriture de `test_backward_compat_imports.py`

L'ancien test (34 imports rétrocompat fonctionnels) a été remplacé par un test inversé :

1. **Test 1** — les 11 fichiers-ponts doivent être absents du dépôt
2. **Test 2** — les 11 noms d'import doivent lever `ImportError`
3. **Test 3** — aucun fichier consommateur ne doit faire `from <pont>` (grep statique sur tout le dépôt, sans ancrage début de ligne pour capturer les imports déférés)

Total : 23 vérifications.

### G7d — Suppression effective

```bash
rm moteur.py moteur_tns.py moteur_liberal.py moteur_salarie.py \
   moteur_comparateur.py moteur_synthese.py moteur_perin.py moteur_scenarios.py \
   utils_ui.py export_pdf.py admin_parametres.py
```

Les 4 greps de garde-fou propriétaire (`moteur_`, `utils_ui`, `export_pdf`, `admin_parametres`) reviennent **tous vides**.

### G7e — Re-validation complète

**Imports déférés détectés en cours de re-validation** : 4 occurrences ratées à l'inventaire initial parce que `grep -E "^(from|import)"` ne capturait pas les imports indentés dans des fonctions.

| Fichier | Ligne | Import déféré raté |
|---|---|---|
| `app.py` | 496 | `from moteur_tns import TX_SALARIAL, ASSIETTE_CSG_SAL, TX_CSG_CRDS_ACT, calcul_ir_foyer` |
| `app.py` | 843 | `from moteur_comparateur import estimer_tmi, estimer_revenu_imposable_par_part` |
| `app.py` | 1169 | `from moteur_synthese import calcul_enveloppes_patrimoniales` |
| `test_no_declaratif_residual.py` | 171 | `from moteur import arbitrage_complet` |

Tous migrés vers leurs cibles canoniques :
- `TX_SALARIAL`, `ASSIETTE_CSG_SAL`, `TX_CSG_CRDS_ACT` → `core.profil` (constantes de cotisations salariales)
- `calcul_ir_foyer` → `core.ir_foyer`
- `estimer_tmi`, `estimer_revenu_imposable_par_part` → `strategy.comparateur`
- `calcul_enveloppes_patrimoniales` → `strategy.synthese`
- `arbitrage_complet` (test_no_declaratif) → `strategy.assimile`

### G7f — Mise à jour documentation

5 documents actualisés :
- `ARCHITECTURE.md` (v1.1 → v1.2) — §4 réécrite (ponts supprimés), §3 racine actualisée, §7.3 B.3 finalisée, §8 stats post-B.3
- `CHANGELOG_B2_GLOBAL.md` — section « Phase B.3 — Migration applicative » ajoutée
- `README_FREEZE_B2.md` — arborescence actualisée, garde-fou n°7 réécrit, §4 « État de la migration » remplace l'ancien « Que faire ensuite »
- `KNOWN_LIMITATIONS.md` — limite « app.py non migré » remplacée par « app.py migré en B.3 (limite levée) »
- `MIGRATION_PLAN_B3.md` — bandeau « PLAN EXÉCUTÉ » en tête, section « Écarts entre plan et exécution » en fin

## 3. Tableau final des validations

| Validation | Résultat |
|---|---|
| `compare_baseline.py` (16 valeurs) | ✓ 16/16 — hash `8863991f27f67847` |
| `check_imports.py` (architecture canonique) | ✓ 16 fichiers conformes |
| `baseline_tests.py compare` (504 tests baseline) | ✓ 504/504 |
| `test_backward_compat_imports.py` (nouveau, absence ponts) | ✓ 23/23 |
| `test_strategy_tns.py` | ✓ 34/34 |
| `test_strategy_liberal.py` | ✓ 43/43 |
| `test_etape4.py` | ✓ 38/38 |
| `test_etape5.py` | ✓ 61/61 |
| `test_pdf_render_all_regimes.py` | ✓ 64/64 |
| `test_no_declaratif_residual.py` | ✓ 8/8 |
| `test_terminologie_freeze.py` | ✓ 0 violation |
| `semantic_guardrails.py` (9 patterns) | ✓ 0 violation |
| `audit_final_b2_controle3.py` (4 patterns) | ✓ 0 violation |
| Smoke test Streamlit (démarrage headless) | ✓ Uvicorn OK |
| 6 PDF de référence (delta vs freeze B.2 + B.2.5) | **0 octet** sur les 6 |

Cumul : **852 + 23 = 875 validations vertes**, 0 régression depuis le début de la journée.

## 4. État final du dépôt racine

25 fichiers `.py` à la racine (au lieu de 36 avant G7d, -11 ponts) :

```
app.py
doctrine.py

audit_final_b2_controle3.py
baseline_outputs.py
baseline_tests.py
check_imports.py
compare_baseline.py
semantic_guardrails.py

generer_cibles.py
generer_cibles_liberal.py

test_backward_compat_imports.py       ← nouveau (absence ponts)
test_coherence_comparateur.py
test_etape4.py
test_etape5.py
test_no_declaratif_residual.py
test_parite_liberal.py
test_parite_salarie.py
test_parite_tns_complet.py
test_pdf_render_all_regimes.py
test_perin.py
test_scenarios.py
test_strategy_liberal.py
test_strategy_tns.py
test_synthese.py
test_terminologie_freeze.py
```

Dossiers `core/`, `regime/`, `strategy/`, `ui/` inchangés depuis le freeze B.2 + B.2.5.

## 5. Snapshots conservés

Tous les snapshots intermédiaires de la session sont conservés pour rollback éventuel ou audit historique :

```
baseline_B3_groupe_0_pre_migration/   ← état avant G1 (session précédente)
baseline_B3_groupe_1_pre/             ← état avant G1
baseline_B3_groupe_2_pre/             ← état avant G2
baseline_B3_groupe_3_pre/             ← état avant G3
baseline_B3_groupe_4_pre/             ← état avant G4
baseline_B3_groupe_5_pre/             ← état avant G5
baseline_B3_groupe_6_pre/             ← état avant G6
baseline_B3_post_g6/                  ← état post-G6
baseline_B3_pre_g7/                   ← état avant G7 (cette session)
baseline_freeze_b2/                   ← snapshot freeze B.2 + B.2.5
```

Logs horodatés des re-validations dans `baseline_outputs_b2/tests/` :
- `freeze_b2_20260519T101733Z.log` (freeze B.2)
- `final_b25_20260519T104419Z.log` (post-B.2.5)
- `post_g6_20260519T110449Z.log` (post-G6)
- `post_g7_20260519T112137Z.log` (post-G7)

## 6. Pour la prochaine session

L'architecture est désormais propre, l'écosystème de validation est complet et redondant. Les pistes possibles selon le backlog `KNOWN_LIMITATIONS.md` :

**Priorité moyenne :**
- Mode audit (`MODE_AUDIT`) — booléen activant un mode verbeux avec citations doctrine
- Historique hypothèses détaillé (`HypotheseReglementaire`) — structure de versionning paramétrique
- Audit UX couleurs — lisibilité N&B, daltonisme
- Couche explicative « Pourquoi ce résultat ? »
- Documentation utilisateur (manuel cabinet)

**Bloqués jusqu'à nouvel ordre :**
- Nouvelles stratégies / régimes, holding/SPFPL
- IA, scoring prédictif, recommandations automatiques
- Benchmark sectoriel

## 7. Règle de gouvernance (rappel)

Pour toute modification touchant `app.py`, les **audits de référence** ou la **doctrine** → feu vert explicite avant action. Règle respectée pendant toute la session G7 (G7c, G7f touchent les audits de référence ; G7f touche `ARCHITECTURE.md`, `CHANGELOG`, `MIGRATION_PLAN`).
