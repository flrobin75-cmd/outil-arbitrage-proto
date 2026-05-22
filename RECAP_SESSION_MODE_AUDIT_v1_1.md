# Session 19/05/2026 — MODE_AUDIT v1.1 (Libéral BNC + SEL)

**Statut final :** ✓ Session complète. MODE_AUDIT couvre désormais TNS + Libéral. Tout au vert sur 11 suites + 3 audits sémantiques + 2 suites MODE_AUDIT. Hash baseline `8863991f27f67847` conservé.

---

## 1. Point de départ de la session

État post-MODE_AUDIT v1 (TNS uniquement) livré au tour précédent. Avant d'enchaîner Libéral, 4 incohérences de référence avaient été détectées :
- `KNOWN_LIMITATIONS.md` : « Pas de mode audit » obsolète
- `ARCHITECTURE.md` : `check_imports.py` mentionnait 16 fichiers (réalité = 17)
- `core/audit.py` : exemples docstring (`TNS_REMUNERATION_BRUTE`, `BAREME_IR_TRANCHES`) divergeaient du contrat réel
- `README_FREEZE_B2.md` : commentaire instructionnel `# 16 fichiers OK` et `# 34/34` faux

## 2. Corrections de cohérence

| Document | Correction | Catégorie |
|---|---|---|
| `KNOWN_LIMITATIONS.md` | « Pas de mode audit » remplacé par « MODE_AUDIT v1.1 — TNS + Libéral » | Document vivant |
| `ARCHITECTURE.md` §2.4 et §5.2 | 16 → 17 fichiers scannés | Document vivant |
| `core/audit.py` docstring | 24 codes alignés sur le contrat réel ; `BAREME_IR_TRANCHES` → `IR_PLAFOND_T1..T4` | Doctrine |
| `README_FREEZE_B2.md:87` | `# attendu : 16 fichiers OK` → `# attendu : 17 fichiers OK` | Procédure |
| `README_FREEZE_B2.md:93` | `# 34/34` → `# 23/23 (test d'absence des ponts post-B.3)` | Procédure |

Récaps figés intacts (`CHANGELOG_B2_GLOBAL.md`, `RECAP_SESSION_20260519.md`, `RECAP_SESSION_B3.md`) — décision explicite de conserver l'historicité.

## 3. G1a — Instrumentation `calcul_module_bnc()`

- `regime/liberal.py::calcul_module_bnc()` instrumenté
- Paramètre opt-in `audit: TraceAudit | None = None` (signature 100 % rétrocompatible)
- 16 étapes hiérarchisées, codes `LIB_BNC_*` :

```
LIB_BNC_RECETTES                       (input racine)
LIB_BNC_BENEFICE                       (agrégat)
  ├── LIB_BNC_FRAIS_PRO
  └── LIB_BNC_BENEFICE_NET
LIB_BNC_COTISATIONS                    (agrégat)
  ├── LIB_BNC_COTIS_BASE
  └── LIB_BNC_CSG_NON_DEDUCTIBLE
LIB_BNC_REVENU_IMPOSABLE_LIB
LIB_BNC_REVENU_IMPOSABLE_FOYER
LIB_BNC_IR_FOYER_AGGREGE               (agrégat)
  ├── LIB_BNC_IR_FOYER_BRUT
  ├── LIB_BNC_CEHR
  ├── LIB_BNC_CDHR
  └── LIB_BNC_TAUX_MOYEN_IR
LIB_BNC_IMPOTS_IMPUTABLES
LIB_BNC_NET_APRES_IMPOTS               (sortie)
```

doctrine_refs cités : `TX_LIB`, `IR_PLAFOND_T1..T4` (5 références, toutes résolues).

## 4. G1b — Instrumentation `calcul_module_sel()`

- `regime/liberal.py::calcul_module_sel()` instrumenté
- Paramètre opt-in `audit: TraceAudit | None = None`
- 8 étapes hiérarchisées, codes `LIB_SEL_*` :

```
LIB_SEL_BENEFICE_AVANT_REM             (input racine)
LIB_SEL_REMUNERATION_DIRIGEANT         (input racine)
LIB_SEL_BENEFICE_IMPOSABLE_IS          (agrégat)
  ├── LIB_SEL_FRACTION_REDUITE
  ├── LIB_SEL_FRACTION_NORMALE
  └── LIB_SEL_IS_DU
LIB_SEL_RESULTAT_NET_DISTRIBUABLE
LIB_SEL_DIVIDENDES_ENVISAGES
```

doctrine_refs cités : `IS_PLAF_REDUIT`, `TX_IS_REDUIT`, `TX_IS_NORMAL` (3 références, toutes résolues).

## 5. Suite de tests dédiée

Le fichier `test_mode_audit_liberal_bnc.py` a été renommé en `test_mode_audit_liberal.py` et étendu pour couvrir les deux modules. **14 catégories de tests, ~85 assertions** :

| # | Catégorie | Module |
|---|---|---|
| 1 | Rétrocompat parfaite | BNC |
| 2 | Structure attendue (codes, hiérarchie) | BNC |
| 3 | Cohérence valeurs ↔ résultat | BNC |
| 4 | Résolution doctrinale | BNC |
| 5 | Unicité des codes | BNC |
| 6 | Cas limite : `frais_pro = 0` | BNC |
| 7 | Rendu console | BNC |
| 8 | Rétrocompat parfaite | SEL |
| 9 | Structure attendue | SEL |
| 10 | Cohérence valeurs ↔ résultat | SEL |
| 11 | Résolution doctrinale | SEL |
| 12 | Cas limite : `imposable IS = 0` (rém > bénéfice) | SEL |
| 13 | Rendu console | SEL |
| 14 | Isolation des espaces de codes (`LIB_BNC_*` ⊥ `LIB_SEL_*`) | Cross |

## 6. G1c — Consolidation documentation

| Fichier | Mise à jour |
|---|---|
| `README_FREEZE_B2.md` §5 | Ajout `semantic_guardrails.py`, `audit_final_b2_controle3.py`, `test_mode_audit_tns.py`, `test_mode_audit_liberal.py` à la séquence de vérification opérationnelle |
| `AUDIT_MODE.md` | Version v1 → v1.1 ; §6.1 et §6.2 mis à jour (Libéral livré, Salarié/Assimilé reportés) ; §8 enrichi (deux tests gardiens, isolation des codes) |
| `KNOWN_LIMITATIONS.md` | « MODE_AUDIT v1 — TNS uniquement » → « MODE_AUDIT v1.1 — TNS + Libéral » |
| `ARCHITECTURE.md` §7.5 | « Phase MODE_AUDIT v1 (TNS) » → « Phase MODE_AUDIT v1.1 (TNS + Libéral BNC/SEL) » avec tableau du périmètre |

## 7. Garanties tenues

- ✓ Hash baseline `8863991f27f67847` conservé bout en bout
- ✓ Baseline 16/16, 504 tests baseline, parité Excel Libéral 96/96
- ✓ 8 suites B.2 (TNS 34, Libéral 43, etc.) toutes vertes
- ✓ Rétrocompat parfaite vérifiée attribut par attribut sur BNC et SEL
- ✓ 9/9 patterns sémantiques `semantic_guardrails.py`
- ✓ 4/4 patterns historiques `audit_final_b2_controle3.py`
- ✓ Architecture canonique respectée (17 fichiers conformes)
- ✓ Espaces de codes isolés : `TNS_*` ⊥ `LIB_BNC_*` ⊥ `LIB_SEL_*` (vérifié par test 14)

## 8. État après G1c

**Fichiers livrés :**

| Fichier | Nature | Lignes |
|---|---|---|
| `core/audit.py` | API audit | ~260 (héritage M1) |
| `ui/audit_render.py` | Renderer console | ~170 (héritage M3) |
| `regime/tns.py` | Instrumentation TNS | ~290 (héritage M2) |
| `regime/liberal.py` | Instrumentation BNC + SEL | ~230 |
| `test_mode_audit_tns.py` | Tests TNS | ~280 (héritage M5) |
| `test_mode_audit_liberal.py` | Tests BNC + SEL | ~390 |
| `AUDIT_MODE.md` | Spec et usage | ~260 |

**Snapshots intermédiaires conservés** dans `baseline_audit_*_pre/` :
- `baseline_audit_M0_pre/` — avant M1 (MODE_AUDIT TNS)
- `baseline_audit_G1a_pre/` — avant G1a (BNC)
- `baseline_audit_G1b_pre/` — avant G1b (SEL)

**Logs horodatés** dans `baseline_outputs_b2/tests/` :
- `post_audit_m5_*.log` — fin de MODE_AUDIT v1 (TNS)
- `post_audit_g1a_*.log` — fin de G1a (BNC instrumenté)
- `post_audit_g1c_*.log` — fin de G1c (Libéral complet + docs)

## 9. Roadmap MODE_AUDIT (post-v1.1)

Dans l'ordre de priorité (cf. `AUDIT_MODE.md` §6.2) :

1. Instrumentation `regime/salarie.py` (pattern identique à BNC)
2. Instrumentation `regime/assimile.py` (pattern proche TNS)
3. Instrumentation des stratégies (`strategy/*.py`) — agrégation de plusieurs traces régime
4. Rendu PDF audit-ready — déclenchable après stabilisation du format avec retours cabinet
5. Export JSON / sérialisation externe
6. Helpers de requête (`find_by_regime`, `total_par_code`)

## 10. Décisions de gouvernance respectées

- Feu vert explicite demandé avant chaque modification d'audit de référence (`semantic_guardrails.py`, `test_terminologie_freeze.py`, `audit_final_b2_controle3.py`, récaps figés)
- Aucune modification de `app.py` cette session
- Modifications de doctrine (`core/audit.py` docstring exemples, `KNOWN_LIMITATIONS.md`, `AUDIT_MODE.md`, `ARCHITECTURE.md` §7.5) effectuées avec accord explicite
- Récaps figés (`RECAP_SESSION_20260519.md`, `RECAP_SESSION_B3.md`, `CHANGELOG_B2_GLOBAL.md`) **non modifiés** — intégrité historique préservée
