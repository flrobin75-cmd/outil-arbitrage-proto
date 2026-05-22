# README — Freeze B.2

**Date du freeze :** 19 mai 2026
**Version doctrine :** v1.0.1
**Hash baseline numérique :** `8863991f27f67847`

Ce fichier est le **point d'entrée** pour quiconque reprend le projet après la Phase B.2.

---

## 1. Ce que vous avez sous les yeux

L'arborescence est dans un état stable, validé par **11 suites de tests vertes**, **0 régression** vs gel initial Phase A/B.1. La Phase B.2 (refactorisation multi-régimes en quatre couches) est terminée.

```
tns_dev/
├── core/                      ← socle métier neutre
│   ├── profil.py
│   ├── ir_foyer.py
│   └── projection.py
├── regime/                    ← un module par régime social
│   ├── assimile.py
│   ├── tns.py
│   ├── liberal.py
│   └── salarie.py
├── strategy/                  ← moteurs stratégiques + comparateur + scénarios
│   ├── assimile.py
│   ├── tns.py
│   ├── liberal.py
│   ├── comparateur.py
│   ├── comparateur_regimes.py
│   ├── synthese.py
│   ├── scenarios.py
│   ├── perin.py
│   └── receptacles.py
├── ui/                        ← présentation (Streamlit + PDF + disclaimers)
│   ├── utils.py
│   ├── pdf_export.py
│   ├── admin.py
│   └── disclaimers.py        ← B.2.5 (disclaimers de présentation)
├── doctrine.py                ← doctrine v1.0.1
├── app.py                     ← Streamlit, imports canoniques (B.3 finalisée)
│
├── baseline_freeze_b2/        ← snapshot du code au freeze B.2 + B.2.5
├── baseline_outputs_b2/       ← 6 PDF + log horodaté des 11 suites (freeze + post-G6 + post-G7)
├── baseline_outputs/          ← baseline numérique de référence (JSON + PDF)
├── baseline_B3_groupe_<N>_pre/ ← snapshots intermédiaires B.3 (G1 à G6)
├── baseline_B3_pre_g7/        ← snapshot pré-G7
├── baseline_B3_post_g6/       ← snapshot post-G6
│
├── CHANGELOG_B2_GLOBAL.md     ← récap B.2 + B.2.5 + B.3 finalisée
├── README_FREEZE_B2.md        ← (ce fichier)
├── KNOWN_LIMITATIONS.md       ← limites assumées de la v1
├── MIGRATION_PLAN_B3.md       ← plan historique de migration (exécuté)
├── ARCHITECTURE.md            ← doctrine architecturale (v1.2 post-B.3)
├── TERMINOLOGY.md             ← vocabulaire prudent + 4 niveaux v1.0.1
└── SEMANTIC_GUARDRAILS.md     ← doctrine des 9 patterns sémantiques
```

> Note : les 11 modules-ponts (`moteur*.py`, `utils_ui.py`, `export_pdf.py`, `admin_parametres.py`) qui existaient pendant les Phases B.2 et B.2.5 ont été **supprimés** à l'issue de la Phase B.3 (G7d, 19/05/2026). Le test `test_backward_compat_imports.py` vérifie maintenant qu'ils restent absents.

---

## 2. Comment vérifier en 5 minutes que tout va bien

### Pré-requis environnement

```bash
pip install streamlit reportlab matplotlib openpyxl
```

Et **`/home/claude/outil_v19.xlsx` doit être présent** (cible Excel utilisée par
`test_parite_salarie.py` et `test_scenarios.py`).

### Séquence de vérification

```bash
cd tns_dev/

# 1. Régénérer la baseline numérique (si baseline_outputs/ vide)
python3 baseline_outputs.py

# 2. Vérifier les 16 valeurs numériques clés
python3 compare_baseline.py            # attendu : 16/16, AUCUNE RÉGRESSION

# 3. Vérifier l'architecture canonique
python3 check_imports.py               # attendu : 17 fichiers OK

# 4. Vérifier les 504 validations baseline Phase A/B.1
python3 baseline_tests.py compare      # attendu : 7/7 modules conformes, hash 8863991f27f67847

# 5. Vérifier les 8 suites B.2
python3 test_backward_compat_imports.py     # 23/23 (test d'absence des ponts post-B.3)
python3 test_strategy_tns.py                # 34/34
python3 test_strategy_liberal.py            # 43/43
python3 test_etape4.py                      # 38/38
python3 test_etape5.py                      # 61/61
python3 test_pdf_render_all_regimes.py      # 64/64
python3 test_no_declaratif_residual.py      # 8/8
python3 test_terminologie_freeze.py         # 0 violation

# 6. Vérifier les audits sémantiques unifiés
python3 semantic_guardrails.py              # 9/9 patterns, 0 violation
python3 audit_final_b2_controle3.py         # 4/4 patterns, 0 violation (historique)

# 7. Vérifier les suites MODE_AUDIT (4 régimes + 3 stratégies + 2 comparateurs + 2 post-arbitrage + 2 transverses)
python3 test_mode_audit_tns.py                              # 7 catégories
python3 test_mode_audit_liberal.py                          # 14 catégories (BNC + SEL)
python3 test_mode_audit_salarie.py                          # 8 catégories
python3 test_mode_audit_assimile.py                         # 11 catégories (2 helpers)
python3 test_mode_audit_strategy_assimile.py                # 12 catégories (G3a, test 9 non-prescriptif)
python3 test_mode_audit_strategy_tns.py                     # 11 catégories (G3b, imbrication 2 niveaux)
python3 test_mode_audit_strategy_liberal.py                 # 12 catégories (G3c, imbrication 3 niveaux, branches dynamiques)
python3 test_mode_audit_strategy_comparateur.py             # 14 catégories (G3d, module autonome, top 3 mécanique)
python3 test_mode_audit_strategy_comparateur_regimes.py     # 14 catégories (G3d-bis, imbrication 6 niveaux)
python3 test_mode_audit_strategy_synthese.py                # 14 catégories (G3e-synthese, composition asymétrique, test renforcé 14 patterns)
python3 test_mode_audit_strategy_scenarios.py               # 12 catégories (G3e-scenarios, module autonome avec composition interne)
python3 test_mode_audit_strategy_perin.py                   # 13 catégories (G3f-perin, composition conditionnelle)
python3 test_mode_audit_strategy_receptacles.py             # 12 catégories (G3f-receptacles, composition interne 3 niveaux)
```

Si l'une des suites échoue, **stoppez** et consultez le log archivé dans
`baseline_outputs_b2/tests/freeze_b2_*.log` pour comparer avec l'état au freeze.

---

## 3. Garde-fous non-négociables (rappel)

Ces 7 règles **doivent rester valides** à tout moment :

1. **T4 (TNS)** : pas d'agrégation `net_dirigeant_immediat` + `benefice_retenu_societe` — toujours 2 indicateurs séparés
2. **Libéral L3/L4** : alerte BNC/SEL systématique, jamais « régime recommandé »
3. **Vocabulaire** : « cadrage indicatif », « outil d'aide à la décision », jamais « recommandée » positif, jamais « optimisation » non négative
4. **Disclaimers v1.0.1** : Primauté cabinet + AMF Comparateur dans chaque PDF
5. **Aucun « Déclaratif »** dans le rendu visible (alias interne `_ALIASES_NIVEAUX` autorisé en code)
6. **Architecture canonique** : `core ← regime ← strategy ← ui ← app` (vérifiée par `check_imports.py`)
7. **Modules-ponts** : **supprimés en B.3 G7d (19/05/2026)**. Le test `test_backward_compat_imports.py` vérifie maintenant qu'ils restent absents — toute réintroduction d'un fichier `moteur*.py`, `utils_ui.py`, `export_pdf.py` ou `admin_parametres.py` à la racine bloque la validation.

Si une PR enfreint l'une de ces règles, elle doit être bloquée tant que les
tests gardiens correspondants ne repassent pas.

---

## 4. État de la migration (post-B.3 finalisée)

✓ **B.2 Refactorisation multi-régimes** — terminée 19/05/2026
✓ **B.2.5 Hardening documentaire** — terminée 19/05/2026
✓ **B.3 Migration applicative + suppression ponts** — terminée 19/05/2026

L'architecture canonique `core ← regime ← strategy ← ui ← app` est désormais respectée à la lettre dans tout le dépôt. Aucun module-pont ne subsiste. Le hash baseline numérique `8863991f27f67847` a été conservé bout en bout.

### Backlog reporté pour les sessions à venir

Conformément à `KNOWN_LIMITATIONS.md` :
- Mode audit (`MODE_AUDIT`)
- Historique hypothèses détaillé (`HypotheseReglementaire`)
- Audit UX couleurs (lisibilité N&B, daltonisme)
- Couche explicative « Pourquoi ce résultat ? »
- Documentation utilisateur (manuel cabinet)

Bloqués jusqu'à nouvel ordre :
- Nouvelles stratégies / régimes, holding/SPFPL
- IA, scoring prédictif, recommandations automatiques
- Benchmark sectoriel

---

## 5. Décisions structurantes verrouillées

| Sujet | Décision |
|---|---|
| Niveau « Avancé » | Option A : documenter les 4 niveaux v1.0.1 existants, **pas de migration de code** |
| Centralisation disclaimers | Hybride : `ui/disclaimers.py` pour présentation, alertes métier restent `strategy/` |
| Trace doctrinale PDF | Option A + C : footer enrichi + annexe enrichie, **pas de bloc lourd en couverture** |
| `semantic_guardrails.py` | Option A : script unifié des 3 audits existants + 5 nouveaux patterns |

Ces décisions ne se re-débattent pas. Toute remise en cause demande un mandat explicite du propriétaire du projet.

---

## 6. Contact / propriétaire

Propriétaire du projet : Florent Robin.
Toute modification structurante (suppression de modules-ponts, changement d'architecture, levée d'un garde-fou) doit faire l'objet d'une validation explicite.
