# Session 19/05/2026 — Freeze B.2 formel + B.2.5 Hardening

**Statut final :** ✓ Travail terminé, tous audits verts, livrables prêts.

---

## 1. État au démarrage

Snapshot `tns_dev_v2_avec_tests_phase_a.tar.gz` extrait dans `/home/claude/tns_dev/`. 11 suites de tests prévues à 852/852 validations.

Bloquant détecté au setup : 2 tests baseline (`test_parite_salarie.py`, `test_scenarios.py`) dépendaient de `/home/claude/outil_v19.xlsx` absent. Upload du fichier puis :

- 504/504 baseline ✓ (hash `8863991f27f67847`)
- 282 tests B.2 chiffrés ✓
- 0 régression

---

## 2. Étape 2 — Freeze formel B.2

Livrables créés à la racine :

| Fichier / dossier | Contenu |
|---|---|
| `baseline_freeze_b2/` | Snapshot du code source au freeze (core/, regime/, strategy/, ui/, doctrine.py, app.py, modules-ponts, ARCHITECTURE.md, TERMINOLOGY.md, SEMANTIC_GUARDRAILS.md, semantic_guardrails.py) |
| `baseline_outputs_b2/pdf/` | 6 PDF de référence (pdf_assimile, pdf_tns, pdf_tns_t4, pdf_liberal_bnc, pdf_liberal_sel, pdf_salarie) |
| `baseline_outputs_b2/tests/freeze_b2_20260519T101733Z.log` | Log horodaté des 11 suites au freeze initial |
| `baseline_outputs_b2/tests/final_b25_20260519T104419Z.log` | Log horodaté de la re-validation finale post-B.2.5 |
| `CHANGELOG_B2_GLOBAL.md` | Récap des 6 étapes B.2 + garde-fous validés |
| `README_FREEZE_B2.md` | Point d'entrée freeze pour les futurs contributeurs |
| `KNOWN_LIMITATIONS.md` | Limites assumées de la v1 (régimes, méthodologie, technique, doctrinal, mise à jour) |
| `MIGRATION_PLAN_B3.md` | Plan détaillé migration app.py (7 groupes, ~3h30) |

---

## 3. Étape 3 — B.2.5 Hardening

### 3.1. Documents créés

- `TERMINOLOGY.md` — vocabulaire prudent (« À éviter / Préférer ») + sémantique des 4 niveaux v1.0.1
- `SEMANTIC_GUARDRAILS.md` — doctrine des 9 patterns sémantiques surveillés
- `ARCHITECTURE.md` enrichi (v1.0 → v1.1) — sens des dépendances, doctrine métier/UI, B.2.5 ajouté, cycle de vie des ponts détaillé

### 3.2. Code créé

- `ui/disclaimers.py` — centralisation des disclaimers de présentation (Primauté cabinet, AMF, Avertissement final, Trace doctrinale footer + annexe). Alertes métier laissées dans `strategy/` (`ALERTE_BNC_VS_SEL`, `DISCLAIMER_CHANGEMENT_REGIME`, `DISCLAIMER_COMPARABILITE`, `NOTE_RADAR_INTRA_REGIME`).
- `semantic_guardrails.py` — script unifié de 9 patterns (3 audits existants fusionnés + 5 nouveaux patterns B.2.5)

### 3.3. Trace doctrinale PDF (B.2.5)

- **Footer enrichi (Option A)** : remplacement de `Doctrine v{x} ({date})` par `Doctrine v1.0.1 — France 2026` sur toutes les pages des 6 PDF.
- **Annexe enrichie (Option C)** : helper `_section_trace_doctrinale_annexe` ajouté à `ui/pdf_export.py`, appelé dans les 4 zones d'annexe (Synthèse principale, TNS, Libéral, Salarié). Insère le titre H2 « Trace doctrinale » suivi d'une fiche méthodo : version doctrine, niveau du module, grille des 4 niveaux v1.0.1, rappel des garde-fous structurels.

### 3.4. Nettoyage terminologique (Option 1 stricte du propriétaire)

4 occurrences résiduelles de l'adjectif « déclaratif » dans les contenus utilisateur reformulées :

| Fichier | Avant | Après |
|---|---|---|
| `doctrine.py:94` | « préparation d'éléments **déclaratifs** » | « préparation des obligations fiscales » |
| `doctrine.py:105` | « calculs **déclaratifs** détaillés, utiliser les modules complets » | « calculs destinés aux obligations fiscales, utiliser les modules de conformité renforcée » |
| `app.py:470` | « Calculs **déclaratifs** avec CEHR, CDHR ... » | « Calculs destinés aux obligations fiscales — CEHR, CDHR ... » |
| `strategy/scenarios.py:195` | « calculs **déclaratifs** détaillés ... modules complets » | « calculs destinés aux obligations fiscales ... modules de conformité renforcée » |

Une occurrence whitelistée explicitement dans `semantic_guardrails.py` comme exception technique tolérée : `doctrine.py:58` (docstring de la classe `NiveauConfiance`, jamais affichée à l'utilisateur).

### 3.5. Régression intermédiaire diagnostiquée et levée

Pendant l'écriture de l'annexe enrichie, le mot « déclaratifs » avait été repris depuis `DESCRIPTION_NIVEAU` (doctrine.py). Diagnostic immédiat, reformulation dans `ui/disclaimers.py` selon la grille validée. Test PDF 64/64 redevenu vert.

---

## 4. Étape 4 — Re-validation finale

Log complet : `baseline_outputs_b2/tests/final_b25_20260519T104419Z.log`

| Validation | Résultat |
|---|---|
| `compare_baseline.py` (16 valeurs) | ✓ 16/16 |
| `check_imports.py` (16 fichiers) | ✓ 16/16 |
| `baseline_tests.py compare` (504 tests) | ✓ 504/504 — hash `8863991f27f67847` |
| `test_backward_compat_imports.py` (34 imports) | ✓ 34/34 |
| `test_strategy_tns.py` | ✓ 34/34 |
| `test_strategy_liberal.py` | ✓ 43/43 |
| `test_etape4.py` | ✓ 38/38 |
| `test_etape5.py` | ✓ 61/61 |
| `test_pdf_render_all_regimes.py` | ✓ 64/64 |
| `test_no_declaratif_residual.py` | ✓ 8/8 |
| `test_terminologie_freeze.py` | ✓ 0 violation |
| `audit_final_b2_controle3.py` (4 patterns historiques) | ✓ 0 violation |
| `semantic_guardrails.py` (9 patterns unifiés) | ✓ 0 violation |

**Cumul : 852 validations chiffrées vertes + 13 audits structurels au vert.**

Effets de bord détectés et traités pendant la re-validation :
- Les deux audits historiques (`test_terminologie_freeze.py`, `audit_final_b2_controle3.py`) ont initialement signalé 2 violations sur le contenu B.2.5 introduit dans `ui/disclaimers.py` (mentions négatives « jamais une recommandation, une optimisation, ou une garantie »). Whitelists patchées pour reconnaître les patterns négatifs B.2.5. Les deux audits sont maintenant cohérents avec le script unifié.

---

## 5. Garde-fous validés au freeze B.2 + B.2.5

| # | Garde-fou | Test gardien |
|---|---|---|
| 1 | T4 (TNS) : pas d'agrégation `net_dirigeant_immediat` + `benefice_retenu_societe` | `test_strategy_tns.py`, `semantic_guardrails.py` |
| 2 | Libéral L3/L4 : alerte BNC/SEL systématique, jamais « régime recommandé » | `test_strategy_liberal.py` (12 tests garde-fous) |
| 3 | Vocabulaire prudent : « cadrage indicatif », jamais « recommandée » positif, jamais « optimisation » | `test_terminologie_freeze.py`, `semantic_guardrails.py` (9 patterns) |
| 4 | Disclaimers v1.0.1 : Primauté cabinet + AMF Comparateur dans chaque PDF | `test_pdf_render_all_regimes.py` (18 tests) |
| 5 | Aucun « Déclaratif » dans le rendu visible + adjectif « déclaratif » sous audit strict | `test_no_declaratif_residual.py`, `semantic_guardrails.py` |
| 6 | Architecture canonique `core ← regime ← strategy ← ui ← app` | `check_imports.py` (16 fichiers) |
| 7 | Modules-ponts : `app.py` reste fonctionnel via la couche rétrocompat | `test_backward_compat_imports.py` (34 tests) |

---

## 6. Sujets reportés (non touchés en B.2.5)

Conformément à la note de reprise :
- Mode audit (`MODE_AUDIT`)
- Historique hypothèses détaillé (`HypotheseReglementaire`)
- Audit UX couleurs (lisibilité N&B, daltonisme)
- Couche explicative « Pourquoi ce résultat ? »
- Migration `app.py` (Phase B.3 — plan dans `MIGRATION_PLAN_B3.md`)
- Suppression des 11 modules-ponts (fin B.3)
- Nouvelles stratégies / régimes, holding/SPFPL, IA, scoring, benchmark sectoriel

---

## 7. Prochaine session

Tout est prêt pour démarrer **Phase B.3** directement depuis `MIGRATION_PLAN_B3.md`. Le freeze B.2 + B.2.5 constitue le point de rollback ultime.
