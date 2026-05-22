# CHANGELOG B.2 — Refactorisation multi-régimes

**Période :** Phase A/B.1 terminée 18/05/2026 → Phase B.2 freezée 19/05/2026
**Version doctrine au freeze :** v1.0.1
**Hash baseline numérique :** `8863991f27f67847`

---

## Vue d'ensemble

La Phase B.2 a réorganisé l'arborescence du moteur en quatre couches canoniques
strictement orientées (`core ← regime ← strategy ← ui ← app`), sans aucune
régression sur les 504 validations baseline Phase A/B.1.

À la sortie de B.2 :

- **852 validations cumulées vertes** (504 baseline + 348 nouvelles B.2)
- **0 régression numérique** (16/16 valeurs clés inchangées vs gel initial)
- **0 violation d'architecture** (16 fichiers scannés conformes)
- **0 dette terminologique résiduelle** (« Déclaratif » purgé du livrable, vocabulaire prudent verrouillé)

---

## Étape 1 — Extraction `core/`

**Objectif :** isoler le socle métier neutre (profil, foyer fiscal, projection).

- Création de `core/profil.py`, `core/ir_foyer.py`, `core/projection.py`
- `core/` n'importe **rien** de `regime/`, `strategy/`, `ui/`
- Vérifié par `check_imports.py`

**Validations :** baseline 504/504 conservée.

---

## Étape 2 — Extraction `regime/`

**Objectif :** un module dédié par régime social (assimilé, TNS, libéral, salarié).

- `regime/assimile.py`, `regime/tns.py`, `regime/liberal.py`, `regime/salarie.py`
- Chaque `regime/X.py` n'importe que `core/` et `doctrine.py`
- Aucune dépendance croisée entre régimes

**Validations :** baseline 504/504 conservée + parité numérique par régime (TNS 114, Libéral 96, Salarié 84).

---

## Étape 3 — Extraction `strategy/`

**Objectif :** isoler les moteurs stratégiques par régime + comparateur + scénarios.

- `strategy/assimile.py` — 4 stratégies A/B/C/D Assimilé
- `strategy/tns.py` — stratégies TNS avec garde-fou T4 (non-agrégation)
- `strategy/liberal.py` — stratégies L1 à L4 avec alerte BNC/SEL
- `strategy/comparateur.py` — Comparateur Option 2 (15 lignes, 1 alerte)
- `strategy/comparateur_regimes.py` — Comparateur inter-régimes
- `strategy/synthese.py` — Synthèse multi-régimes
- `strategy/scenarios.py` — Scénarios A vs B (avant/après dividendes)
- `strategy/perin.py` — PERIN mutualisé conjoint
- `strategy/receptacles.py` — Matrice §5 (filtrage Comparateur)

**Validations :**
- `test_strategy_tns.py` : 34/34 (dont 11 tests structurels non-agrégation T4)
- `test_strategy_liberal.py` : 43/43 (dont 12 garde-fous méthodologiques)
- `test_etape4.py` : 38/38 (12 synthèse + 17 comparateur régimes + 9 garde-fous)
- `test_etape5.py` : 61/61 (28 matrice §5 + 12 filtre Comparateur + 11 Madelin + 3 unicité règle)
- Baseline 504/504 conservée

---

## Étape 4 — Extraction `ui/`

**Objectif :** isoler la couche présentation (utils Streamlit, export PDF, admin).

- `ui/utils.py` — `format_eur`, `NIVEAU_COULEURS`, helpers Streamlit
- `ui/pdf_export.py` — `generer_pdf_synthese` + générateurs par régime
- `ui/admin.py` — interface admin paramètres

**Validations :**
- `test_pdf_render_all_regimes.py` : 64/64 (39 structure + 18 disclaimers v1.0.1 + 7 garde-fous critiques)
- 6 PDF générés et archivés (`pdf_assimile`, `pdf_tns`, `pdf_tns_t4`, `pdf_liberal_bnc`, `pdf_liberal_sel`, `pdf_salarie`)

---

## Étape 5 — Modules-ponts rétrocompatibilité

**Objectif :** ne PAS casser `app.py` avant la migration de Phase B.3.

11 modules-ponts racine conservés exposant les anciens noms publics :
- `moteur.py`, `moteur_tns.py`, `moteur_liberal.py`, `moteur_salarie.py`
- `moteur_comparateur.py`, `moteur_synthese.py`, `moteur_perin.py`, `moteur_scenarios.py`
- `utils_ui.py`, `export_pdf.py`, `admin_parametres.py`

**Validations :**
- `test_backward_compat_imports.py` : 34/34 imports rétrocompatibles fonctionnels
- Chaque pont est un simple `from <nouveau_module> import *` (ou alias explicite)

⚠ **Suppression interdite avant migration B.3** (cf. `MIGRATION_PLAN_B3.md`).

---

## Étape 6 — Purge terminologique + audit final 6 contrôles

**Objectif :** lever toute dette sémantique avant freeze.

- Purge du terme « Déclaratif » du rendu visible
  - 4 niveaux v1.0.1 conservés : `Conformité renforcée`, `Avancé`, `Cadrage`, `Indicatif`
  - Alias interne `_ALIASES_NIVEAUX` autorisé pour rétrocompat code, jamais affiché
- Verrouillage du vocabulaire prudent :
  - « optimisation » → uniquement dans disclaimers négatifs
  - « recommandée » → 33 occurrences, toutes en contexte négatif/garde-fou
  - Jamais de « régime recommandé » côté libéral L3/L4

**Validations :**
- `test_no_declaratif_residual.py` : 8/8 (1 NIVEAU_COULEURS_PDF + 6 PDF + 1 grep racine)
- `test_terminologie_freeze.py` : audit clean, 0 violation
- Audit final 6 contrôles (script `audit_final_b2_controle3.py`) : passé

---

## Architecture canonique au freeze B.2

```
┌─────────────┐
│    app.py   │  ← Streamlit, non migré en B.2 (Phase B.3)
└──────┬──────┘
       │ peut importer tout
       ▼
┌─────────────┐
│     ui/     │  utils.py, pdf_export.py, admin.py
└──────┬──────┘
       │ peut importer strategy/, regime/, core/, doctrine
       ▼
┌─────────────┐
│  strategy/  │  assimile, tns, liberal, comparateur, comparateur_regimes,
│             │  synthese, scenarios, perin, receptacles
└──────┬──────┘
       │ peut importer regime/, core/, doctrine
       ▼
┌─────────────┐
│   regime/   │  assimile, tns, liberal, salarie
└──────┬──────┘
       │ peut importer core/, doctrine
       ▼
┌─────────────┐
│    core/    │  profil, ir_foyer, projection
└─────────────┘
```

**Règles d'import** vérifiées en CI par `check_imports.py` (16 fichiers OK).

---

## Garde-fous validés au freeze

| # | Garde-fou | Test gardien |
|---|---|---|
| 1 | T4 (TNS) : pas d'agrégation `net_dirigeant_immediat` + `benefice_retenu_societe` | `test_strategy_tns.py` (11 tests) |
| 2 | Libéral L3/L4 : alerte BNC/SEL systématique, jamais « régime recommandé » | `test_strategy_liberal.py` (12 tests) |
| 3 | Vocabulaire prudent : « cadrage indicatif », jamais « recommandée » positif | `test_terminologie_freeze.py` |
| 4 | Disclaimers v1.0.1 : Primauté cabinet + AMF Comparateur dans chaque PDF | `test_pdf_render_all_regimes.py` (18 tests) |
| 5 | Aucun « Déclaratif » dans le rendu visible | `test_no_declaratif_residual.py` (8 tests) |
| 6 | Architecture canonique `core ← regime ← strategy ← ui ← app` | `check_imports.py` (16 fichiers) |
| 7 | Modules-ponts : `app.py` reste fonctionnel via la couche rétrocompat | `test_backward_compat_imports.py` (34 tests) |

---

## Note sur le décompte 852

- **504 validations baseline Phase A/B.1** (TNS 114 + Libéral 96 + Salarié 84 + Comparateur 64 + Synthèse 30 + Scénarios 88 + PERIN 28)
- **348 validations B.2** : 282 tests chiffrés explicites (34+34+43+38+61+64+8) + audits non-numériques (`test_terminologie_freeze.py` = audit grep multi-patterns, `check_imports.py` = audit 16 fichiers, `compare_baseline.py` = 16 valeurs, audit final 6 contrôles)

Le chiffre 348 inclut donc des validations atomiques au sein des audits d'architecture/terminologie/numériques, pas seulement les `assert` des tests métier.

---

## Sujets explicitement reportés (hors B.2)

- Migration complète de `app.py` vers la nouvelle arborescence → **terminée en B.3 (19/05/2026)**
- Suppression des 11 modules-ponts → **terminée en B.3 G7d (19/05/2026)**
- Mode audit (`MODE_AUDIT`) → après B.2.5
- Historique hypothèses détaillé (`HypotheseReglementaire`) → après B.2.5
- Audit UX couleurs (N&B, daltonisme) → après B.2.5
- Couche explicative « Pourquoi ce résultat ? » → après B.2.5
- Nouvelles stratégies / régimes, holding/SPFPL, IA, scoring → **bloqués jusqu'à nouvel ordre**

---

## Phase B.3 — Migration applicative (terminée 19/05/2026)

Cette section documente l'achèvement de la migration prévue dans `MIGRATION_PLAN_B3.md`.

### G1 → G6 — Migration des imports d'`app.py`

42 imports d'`app.py` (en début de fichier) migrés des 11 modules-ponts racine vers les couches canoniques :

| Groupe | Périmètre |
|---|---|
| G1 | `moteur_synthese`, `moteur_scenarios`, `moteur_perin` → `strategy.*` (12 symboles) |
| G2 | `moteur_comparateur` → `strategy.comparateur` (3 symboles) |
| G3 | `moteur_tns`, `moteur_liberal`, `moteur_salarie` → `core.profil` + `regime.*` (6 symboles) |
| G4 | `moteur` → `strategy.assimile` + `core.projection` (3 symboles) |
| G5 | `utils_ui` → `ui.utils` (11 symboles) |
| G6 | `export_pdf` → `ui.pdf_export`, `admin_parametres` → `ui.admin` (7 symboles) |

Snapshots intermédiaires conservés : `baseline_B3_groupe_<N>_pre/` pour chaque groupe.

### G7 — Suppression des modules-ponts

| Sous-étape | Périmètre | Résultat |
|---|---|---|
| G7a | Migration des outils baseline (`compare_baseline.py`, `baseline_outputs.py`) — 13 imports | ✓ |
| G7b | Migration de 9 tests métier — 14 imports | ✓ |
| G7c | Réécriture de `test_backward_compat_imports.py` en test d'absence de ponts (23 validations) | ✓ |
| G7d | `rm` des 11 modules-ponts | ✓ |
| G7e | Re-validation complète : 11 suites + 9 patterns + 4 patterns historiques + 6 PDF delta 0 octet | ✓ |
| G7f | Mise à jour de `ARCHITECTURE.md`, `CHANGELOG_B2_GLOBAL.md`, `README_FREEZE_B2.md`, `KNOWN_LIMITATIONS.md`, `MIGRATION_PLAN_B3.md` | ✓ |

### Imports déférés découverts en cours de G7

L'inventaire initial des imports d'`app.py` ne capturait que les imports en début de fichier. Quatre imports déférés (à l'intérieur de fonctions) ont été révélés par la régression du test `test_no_declaratif_residual.py` post-G7d :

- `app.py:496` — `from moteur_tns import TX_SALARIAL, ASSIETTE_CSG_SAL, TX_CSG_CRDS_ACT, calcul_ir_foyer` → `core.profil` + `core.ir_foyer`
- `app.py:843` — `from moteur_comparateur import estimer_tmi, estimer_revenu_imposable_par_part` → `strategy.comparateur`
- `app.py:1169` — `from moteur_synthese import calcul_enveloppes_patrimoniales` → `strategy.synthese`
- `test_no_declaratif_residual.py:171` — `from moteur import arbitrage_complet` → `strategy.assimile`

Tous migrés vers leurs cibles canoniques. Garde-fou ajouté au nouveau `test_backward_compat_imports.py` : un grep statique sur tout le dépôt vérifie qu'aucun fichier ne référence plus les ponts (ancrage déféré compris).

### État final post-B.3

| Métrique | Valeur |
|---|---|
| Modules-ponts restants | **0** |
| Imports historiques fonctionnels | **0** (chaque `import moteur_*` lève maintenant `ImportError`) |
| Fichiers Python racine | ~25 (au lieu de 36 avant G7d) |
| Validations vertes | 11 suites + 4 audits + 23 vérifications absence ponts |
| Hash baseline numérique | `8863991f27f67847` conservé bout en bout |
| Smoke test Streamlit | ✓ Uvicorn démarre, app charge sans exception |
| 6 PDF de référence | Delta 0 octet vs freeze B.2 + B.2.5 |

L'architecture canonique `core ← regime ← strategy ← ui ← app` est désormais respectée à la lettre dans tout le dépôt, sans couche transitoire.
