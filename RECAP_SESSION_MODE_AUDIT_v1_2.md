# Session 19/05/2026 — MODE_AUDIT v1.2 (Salarié G2a + Assimilé G2b)

**Statut final :** ✓ Session complète. MODE_AUDIT couvre désormais **les 4 régimes** (TNS + Libéral + Salarié + Assimilé). Tout au vert sur 11 suites + 3 audits sémantiques + 4 suites MODE_AUDIT. Hash baseline `8863991f27f67847` conservé.

---

## 1. Point de départ de la session

État post-MODE_AUDIT v1.1 (TNS + Libéral BNC/SEL) livré au tour précédent.

Roadmap d'extension acceptée :
1. Salarié G2a (plus simple — un moteur unique, structure courte)
2. Assimilé G2b (plus subtil — module = helpers, logique métier dans `strategy/assimile.py`)
3. Stratégies G3 (reporté à la prochaine itération)

## 2. G2a — Instrumentation Salarié

### 2.1. Promotion de constantes vers `core/profil.py`

Décision validée (option B sur le cadrage `PLAFOND_ABAT_10PCT_SAL`) : promotion des constantes doctrinales depuis les régimes vers la couche `core/`. Préserve la doctrine comme source canonique unique, évite la dispersion (« certaines hypothèses sont doctrinales mais non référencées »).

| Constante | Valeur | Origine |
|---|---|---|
| `TX_CSG_DEDUCTIBLE` | 0.068 | Codée en dur dans TNS, Libéral BNC, Salarié |
| `TX_CSG_NON_DEDUCTIBLE` | 0.029 | Codée en dur dans TNS, Libéral BNC |
| `PLAFOND_ABAT_10PCT_SAL` | 14 426 | Constante locale `regime/salarie.py` |
| `TX_ABAT_10PCT_SAL` | 0.10 | Codé en dur dans `regime/salarie.py` |

### 2.2. Instrumentation `calcul_module_salarie()`

- Paramètre opt-in `audit: TraceAudit | None = None`
- 17 étapes hiérarchisées, codes `SAL_*` :

```
SAL_SALAIRE_BRUT                  (input racine)
SAL_COTISATIONS                   (agrégat)
  ├── SAL_COTIS_SALARIALES
  ├── SAL_CSG_CRDS_TOTALE
  └── SAL_CSG_DEDUCTIBLE
SAL_NET_AVANT_IMPOT
SAL_REVENU_SALARIAL_IMPOSABLE
SAL_ABATTEMENT_10PCT              (doctrine_refs G2a)
SAL_REVENU_IMPOSABLE_NET
SAL_REVENU_IMPOSABLE_FOYER
SAL_IR_FOYER_AGGREGE              (agrégat)
  ├── SAL_IR_FOYER_BRUT
  ├── SAL_CEHR
  ├── SAL_CDHR
  └── SAL_TAUX_MOYEN_IR
SAL_IMPOTS_IMPUTABLES_REM
SAL_NET_APRES_IMPOTS              (sortie)
```

10 doctrine_refs uniques cités, toutes résolues.

### 2.3. Correction collatérale `strategy/liberal.py:65`

Import historique `from regime.salarie import PLAFOND_ABAT_10PCT_SAL` repointé vers `core.profil` (source canonique). Le re-export accidentel transitif de `regime.salarie` continuait à fonctionner mais était conceptuellement incorrect.

### 2.4. Suite de tests `test_mode_audit_salarie.py`

8 catégories de tests, ~50 assertions chiffrées.

## 3. G2b — Instrumentation Assimilé

### 3.1. Spécificité du module

`regime/assimile.py` n'a pas de `calcul_module_assimile()` global. Il expose deux helpers consommés par le Strategy Engine :
- `calcul_tx_ir_moyen(profil)` — calcul long (~10 étapes) du taux moyen IR de référence
- `fs_moyen_epargne(profil)` — table forfait social par effectif (1 étape)

Décision validée : **les 2 helpers sont instrumentés** (option A), pour cohérence avec les 3 autres régimes et pour préparer G3 stratégies (chaînage de traces sans regénération).

### 3.2. Suppression duplication `PLAFOND_ABAT_10PCT_REF`

`regime/assimile.py` définissait localement une copie de la constante (`PLAFOND_ABAT_10PCT_REF = 14_426`) pour éviter une dépendance régime ↔ régime. Maintenant que la constante est dans `core/profil.py` (G2a), cette duplication n'a plus de raison d'être. Import direct depuis `core.profil`. Idem pour `0.068` → `TX_CSG_DEDUCTIBLE` et `0.10` → `TX_ABAT_10PCT_SAL`.

### 3.3. Instrumentation `calcul_tx_ir_moyen`

11 étapes en ligne (pas de hiérarchie : c'est un calcul séquentiel pur, chaque étape consomme la précédente) :

```
ASSIM_TX_IR_MOY_BRUT_REF
ASSIM_TX_IR_MOY_COTIS_SALARIALES
ASSIM_TX_IR_MOY_CSG_CRDS
ASSIM_TX_IR_MOY_CSG_DEDUCTIBLE
ASSIM_TX_IR_MOY_NET_AVANT_IR
ASSIM_TX_IR_MOY_REV_SAL_IMP
ASSIM_TX_IR_MOY_ABATTEMENT
ASSIM_TX_IR_MOY_REV_IMP_NET
ASSIM_TX_IR_MOY_REV_IMP_FOYER
ASSIM_TX_IR_MOY_TOTAL_IMPOTS
ASSIM_TX_IR_MOY_RESULTAT          (avec hypotheses 'plancher_v19'=0.05 + 'tx_moy_avant_plancher')
```

10 doctrine_refs cités. Le plancher v19 de 5 % est explicité dans les hypothèses de l'étape finale (traçabilité du correctif appliqué).

### 3.4. Instrumentation `fs_moyen_epargne`

1 étape unique `ASSIM_FS_MOYEN`. Hypothèses : `effectif_profil` (valeur appliquée) + table complète des 3 paliers (0 %, 13,3 %, 20 %). Permet au cabinet de comprendre immédiatement quel palier s'applique et pourquoi.

### 3.5. Suite de tests `test_mode_audit_assimile.py`

11 catégories, dont :
- Comportement par effectif (5 cas distincts × valeur attendue × cohérence trace)
- Plancher 5 % v19 tracé via hypotheses
- Isolation `ASSIM_*` ⊥ {`TNS_*`, `LIB_BNC_*`, `LIB_SEL_*`, `SAL_*`}

## 4. G2c — Consolidation documentaire

| Document | Mise à jour |
|---|---|
| `AUDIT_MODE.md` | v1.1 → v1.2 ; §6.1 et §6.2 mis à jour ; §8 enrichi (4 tests gardiens, 40 catégories cumulées) |
| `KNOWN_LIMITATIONS.md` | « MODE_AUDIT v1.1 — TNS + Libéral » → « v1.2 — 4 régimes » |
| `ARCHITECTURE.md` §7.5 | « Phase MODE_AUDIT v1.1 » → « v1.2 (4 régimes) » ; ajout d'une remarque sur le bénéfice architectural collatéral (centralisation doctrinale) |
| `README_FREEZE_B2.md` §5 | Séquence opératoire actualisée — 4 suites MODE_AUDIT |

## 5. Validation finale (`post_audit_g2c_*.log`)

| Validation | Résultat |
|---|---|
| Baseline numérique | ✓ 16/16 — hash `8863991f27f67847` |
| Architecture canonique | ✓ 17 fichiers conformes |
| 504 baseline | ✓ 7/7 modules, 0 régression |
| Parité Excel TNS | ✓ 114/114 |
| Parité Excel Libéral | ✓ 96/96 |
| Parité Excel Salarié | ✓ 84/84 |
| 8 suites B.2 | ✓ Toutes vertes |
| MODE_AUDIT TNS | ✓ 7 catégories |
| MODE_AUDIT Libéral | ✓ 14 catégories |
| MODE_AUDIT Salarié | ✓ 8 catégories |
| MODE_AUDIT Assimilé | ✓ 11 catégories |
| `semantic_guardrails.py` | ✓ 0 violation (9 patterns) |
| `audit_final_b2_controle3.py` | ✓ 0 violation (4 patterns) |
| `test_terminologie_freeze.py` | ✓ 0 violation |

## 6. Garanties tenues

- ✓ Hash baseline `8863991f27f67847` conservé bout en bout (M1 → G2c)
- ✓ Aucune logique métier déplacée — instrumentation = pur side channel
- ✓ Couche `core/` neutre (`core/audit.py` ne dépend que de `dataclasses`/`typing`)
- ✓ Rétrocompat parfaite vérifiée sur les 4 régimes (résultat strictement identique avec/sans audit, attribut par attribut quand dataclass, valeur par valeur quand scalaire)
- ✓ 9/9 patterns sémantiques `semantic_guardrails.py`
- ✓ 4/4 patterns historiques `audit_final_b2_controle3.py`
- ✓ Espaces de codes isolés : `TNS_*` ⊥ `LIB_BNC_*` ⊥ `LIB_SEL_*` ⊥ `SAL_*` ⊥ `ASSIM_*`

## 7. Bénéfice architectural cumulé

L'extension MODE_AUDIT a poussé la **centralisation doctrinale** dans `core/profil.py` :

| Constante | Avant G2 | Après G2 |
|---|---|---|
| `TX_CSG_DEDUCTIBLE` (0.068) | Codée en dur ×3 modules | Constante doctrinale référençable |
| `TX_CSG_NON_DEDUCTIBLE` (0.029) | Codée en dur ×2 modules | Constante doctrinale référençable |
| `PLAFOND_ABAT_10PCT_SAL` (14 426) | Constante locale `regime/salarie.py` + duplication `regime/assimile.py` | Centrale, sans duplication |
| `TX_ABAT_10PCT_SAL` (0.10) | Codée en dur ×2 modules | Constante doctrinale référençable |

L'audit améliore l'architecture métier, exactement comme prédit.

## 8. État du dépôt après G2

**Fichiers livrés cette session :**

| Fichier | Action | Lignes |
|---|---|---|
| `core/profil.py` | + 4 constantes promues | +5 |
| `regime/salarie.py` | Instrumenté + import core | +120 |
| `regime/assimile.py` | Instrumenté + suppression duplication locale | +90, -15 |
| `strategy/liberal.py` | Correction import (re-export → source canonique) | ±2 |
| `test_mode_audit_salarie.py` | Nouveau | +290 |
| `test_mode_audit_assimile.py` | Nouveau | +330 |
| `AUDIT_MODE.md` | v1.1 → v1.2 | ±50 |
| `KNOWN_LIMITATIONS.md` | Section MODE_AUDIT à jour | ±15 |
| `ARCHITECTURE.md` | §7.5 à jour | ±30 |
| `README_FREEZE_B2.md` | §5 séquence opératoire | +3 |

**Snapshots intermédiaires conservés** dans `baseline_audit_*_pre/` :
- `baseline_audit_M0_pre/` — avant M1 (MODE_AUDIT TNS)
- `baseline_audit_G1a_pre/` — avant G1a (BNC)
- `baseline_audit_G1b_pre/` — avant G1b (SEL)
- `baseline_audit_G2a_pre/` — avant G2a (Salarié)
- `baseline_audit_G2b_pre/` — avant G2b (Assimilé)

## 9. Décisions de gouvernance respectées

- Feu vert explicite obtenu avant chaque modification doctrinale :
  - Promotion 4 constantes vers `core/profil.py` (G2a)
  - Suppression duplication `PLAFOND_ABAT_10PCT_REF` (G2b)
  - Mise à jour `AUDIT_MODE.md`, `KNOWN_LIMITATIONS.md`, `ARCHITECTURE.md` §7.5 (G2c)
- Aucune modification de `app.py` cette session
- Aucun récap figé modifié — récap consolidé écrit en une seule passe en G2c
- Audits de référence (`semantic_guardrails.py`, `audit_final_b2_controle3.py`, `test_terminologie_freeze.py`) **non modifiés** — leur structure actuelle suffit

## 10. Roadmap MODE_AUDIT (post-v1.2)

Conformément à la priorité acceptée :

1. **G3 — Instrumentation des stratégies** (`strategy/*.py`). Désormais possible avec les 4 régimes instrumentés en amont : chaque appel à un `calcul_module_*` ou helper Assimilé peut chaîner sa trace dans la trace globale de la stratégie. La logique A/B/C/D Assimilé pourra être pleinement explicitée.
2. **Rendu PDF audit-ready** — déclenchable après G3, format à stabiliser avec retours cabinet sur la couverture stratégie + régimes.
3. Export JSON / sérialisation externe
4. Helpers de requête (`find_by_regime`, `total_par_code`, etc.)
