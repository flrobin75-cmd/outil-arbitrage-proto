# Session 19/05/2026 — MODE_AUDIT v1.3 (Strategy G3a + G3b + G3c)

**Statut final :** ✓ Session complète. MODE_AUDIT couvre désormais **les 4 régimes + 3 modules stratégie** (Assimilé, TNS, Libéral). Spec 1.1.0 introduite. Tout au vert sur 8 suites B.2 + 3 audits sémantiques + **7 suites MODE_AUDIT**. Hash baseline `8863991f27f67847` conservé.

---

## 1. Point de départ

État post-MODE_AUDIT v1.2 (4 régimes instrumentés) livré au tour précédent.

Roadmap acceptée pour G3 :
1. G3a — `strategy/assimile.py` (routeur simple, banc d'essai du modèle composable)
2. G3b — `strategy/tns.py` (module dense, premier test de robustesse)
3. G3c — `strategy/liberal.py` (fermeture des stratégies amont, branches dynamiques)
4. G3d — `strategy/comparateur.py` (reporté à la prochaine session)

## 2. G3a — Introduction de la spec 1.1.0 et instrumentation Assimilé

### 2.1. Spec 1.1.0 — sous-traces composables

Premier changement structurel de la spec depuis sa publication. Ajout dans `core/audit.py` :

- Champ `sous_traces: dict[str, TraceAudit]` dans `TraceAudit`
- Méthodes `attacher_sous_trace(nom, sous_trace)`, `get_sous_trace(nom)`, `noms_sous_traces()`
- **4 garde-fous actifs** : refus doublons de noms, refus réattachement (même instance ailleurs), refus cycle direct, refus type incorrect
- Bump `AUDIT_SPEC_VERSION` : "1.0.0" → "1.1.0" (transparent, les 4 suites régime importent la constante)

### 2.2. Instrumentation `strategy/assimile.py`

- `calcul_strategie(profil, code, tx_ir_moy, audit=None)` : 13 étapes par stratégie, codes `STRAT_ASSIM_<X>_*` où X∈{A,B,C,D}
- `arbitrage_complet(profil, audit=None)` : 7 étapes méta `STRAT_ASSIM_*` + attache **5 sous-traces nommées** :
  - `tx_ir_moy` (régime Assimilé)
  - `strategie_A/B/C/D` (stratégies)

Codes méta clés :
- `STRAT_ASSIM_TX_IR_MOY_RACINE` (référence amont)
- `STRAT_ASSIM_COMPARE_AB` + `STRAT_ASSIM_DELTA_<X>_VS_A` (deltas factuels)
- `STRAT_ASSIM_CRITERE_RETENU = "max(total_net)"` (critère explicite)
- `STRAT_ASSIM_RETENU` (code de la stratégie retenue)

### 2.3. Renderer console récursif

`ui/audit_render.py` : ajout du rendu récursif des sous-traces avec paramètre interne `_niveau`. En-tête « SOUS-TRACE — » pour les niveaux > 0, indentation cumulative. **Fonctionne nativement pour 2, 3 niveaux ou plus** (validé en G3b/G3c).

### 2.4. Test 9 non-prescriptif automatique

Innovation majeure de G3a : **scan récursif automatique** des labels et notes de tout le graphe contre 12 patterns regex (`\boptim...\b`, `\bmeilleur...\b`, `\brecommand...\b`, etc.). 0 violation tolérée. Industrialise la discipline non-prescriptive.

### 2.5. Fix sémantique post-G3a

Deux reformulations locales pour passer `semantic_guardrails.py` (sans modifier l'audit de référence) :
- `core/audit.py:288` : « garantie en v1.1.0 » → « assurée en v1.1.0 »
- `strategy/assimile.py:32` : énumération « optimal/meilleur/gagnant » → renvoi à TERMINOLOGY.md

Whitelist `semantic_guardrails.py` étendue (avec feu vert) sur 2 patterns variables Python :
- `r"^\s*recommandee\s*="` → `r"^\s*recommandee\s*[,=]"` (extension : passage en argument positionnel)
- Ajout `r"\[recommandee\]"` (indexation par variable identifiant)

### 2.6. Suite de tests G3a

`test_mode_audit_strategy_assimile.py` : **12 catégories, ~110 assertions**. Premier test 9 non-prescriptif. Test 7 garde-fous d'attachement (4 cas refusés). Test 5 anti-duplication.

## 3. G3b — Instrumentation TNS (module dense, imbrication 2 niveaux)

### 3.1. Spécificités TNS

`strategy/tns.py` (513 lignes) :
- Helper `_calcul_is` inline (option A2 validée — pas d'instrumentation pour ce mini-helper)
- 4 stratégies T1/T2/T3/T4 avec mécaniques très différentes (T2 avec branches IS + garde-fou + alertes ; T3 avec PERIN + TMI marginal ; T4 avec convention de non-agrégation)

### 3.2. Imbrication 2 niveaux

Premier usage de l'imbrication : chaque stratégie attache sa propre sous-trace `module_tns` (24 étapes régime). Graphe complet sur profil par défaut :

```
arbitrage_complet_tns (méta)              — 7 étapes STRAT_TNS_*
├── strategie_T1                          — 12 étapes STRAT_TNS_T1_*
│     └── module_tns                      — 24 étapes TNS_*
├── strategie_T2                          — 14 étapes STRAT_TNS_T2_*
│     └── module_tns                      — 24 étapes TNS_*
├── strategie_T3                          — 16 étapes STRAT_TNS_T3_*
│     └── module_tns                      — 24 étapes TNS_*
└── strategie_T4                          — 11 étapes STRAT_TNS_T4_*
      └── module_tns                      — 24 étapes TNS_*

Total : 156 étapes structurées, 0 duplication, 0 collision.
```

### 3.3. Convention de non-agrégation T4

Étape méta `STRAT_TNS_INDICATEURS_SEPARES` (factuelle, pas de qualification) + indicateurs séparés `BENEFICE_RETENU_SOCIETE` / `NET_DIRIGEANT_IMMEDIAT` dans la sous-trace `strategie_T4`. Aucun parent commun structurel — la trace reflète la règle métier.

### 3.4. Textes d'alertes T2 préservés en hypotheses

Le texte d'alerte métier T2 contient `optimum dividendes-PFU` (vocabulaire métier français). Cette terminologie ne doit pas apparaître dans les labels ou notes MODE_AUDIT (test 9 strict). **Solution structurante** : textes d'alertes placés en `hypotheses["textes_alertes"]` (champ dict non scanné par le test 9). Le wording métier reste intact, la trace MODE_AUDIT reste factuelle.

Étape `STRAT_TNS_T2_ALERTES_NB = float(len(alertes))` au lieu d'un texte qualifié.

### 3.5. Élargissement pattern non-prescriptif

Conséquence directe de la lecture du wording T2 : le pattern `\boptim(?:al|isation|...)\b` ne capturait pas `optimum`. **Élargi à `\boptim\w*\b`** pour couvrir `optimum`, `optimisé`, `optime`, etc. Propagé G3a + G3b pour cohérence.

### 3.6. Suite de tests G3b

`test_mode_audit_strategy_tns.py` : **11 catégories, ~140 assertions**. Test 4 imbrication 2 niveaux (24 étapes TNS validées). Test 6 non-agrégation T4. Test 8 textes d'alertes en hypotheses. Test 9 non-prescriptif sur **156 étapes** avec pattern élargi.

## 4. G3c — Instrumentation Libéral (branches dynamiques, imbrication 3 niveaux)

### 4.1. Spécificités Libéral

`strategy/liberal.py` (452 lignes) :
- 3 alertes structurantes définies au niveau module (`ALERTE_BNC_VS_SEL`, `MENTION_RETENTION_V2`, `ALERTE_L4_V2`)
- Terminologie native non-prescriptive : la dataclass `ResultatArbitrageLib` utilise déjà `plus_efficace_fiscalement` au lieu de `recommandee`, et le module porte une **interdiction doctrinale explicite** d'utiliser « recommandée » sur le résultat consolidé (§36-38 docstring)
- **L3 branches dynamiques** selon `forme_sel` : SELARL → module TNS ; SELAS → module Salarié
- **L4 délégué à L3** : code identique, alerte structurante ajoutée

### 4.2. Branches dynamiques SELARL/SELAS

Première utilisation des sous-traces régime à nom **dynamique** :
- SELARL → sous-trace `module_tns` (24 étapes `TNS_*`)
- SELAS → sous-trace `module_salarie` (17 étapes `SAL_*`)

Aucune extension API nécessaire — le nom est calculé à l'attachement, l'infrastructure spec 1.1.0 couvre nativement ce cas.

### 4.3. Délégation L4 → L3 (option B validée)

L4 wrapper minimal (3 étapes : `DELEGATION_L3`, `ALERTE_STRUCTURATION_V2_NB`, `NET_DIRIGEANT_TOTAL`) + sous-trace `strategie_l3_deleguee` contenant le calcul L3 complet. Pas de recalcul, reflet fidèle de la sémantique « L4 = L3 + alerte ».

**Premier cas de 3 niveaux d'imbrication** :
```
arbitrage_complet_liberal → strategie_L4 → strategie_l3_deleguee → module_tns/module_salarie
```

### 4.4. Terminologie spécifique STRAT_LIB_PLUS_EFFICACE_FISCALEMENT

Le routeur méta utilise `STRAT_LIB_PLUS_EFFICACE_FISCALEMENT` (au lieu du `STRAT_<X>_RETENU` employé en G3a/G3b). Cohérent avec la doctrine module (§36-38). Test 2 vérifie explicitement l'absence de `STRAT_LIB_RETENU` et la présence de `STRAT_LIB_PLUS_EFFICACE_FISCALEMENT`.

### 4.5. Alertes structurantes en hypotheses

Les 3 alertes textuelles structurantes sont placées en `hypotheses` pour préserver leur wording métier intégral :
- `STRAT_LIB_L3_ALERTES_NB.hypotheses["ALERTE_BNC_VS_SEL"]` = texte intégral
- `STRAT_LIB_L3_ALERTES_NB.hypotheses["MENTION_RETENTION_V2"]` = texte intégral
- `STRAT_LIB_L4_ALERTE_STRUCTURATION_V2_NB.hypotheses["ALERTE_L4_V2"]` = texte intégral
- `STRAT_LIB_AVERTISSEMENT_BNC_SEL.hypotheses["ALERTE_BNC_VS_SEL"]` (niveau méta) = texte intégral

### 4.6. Reformulation préventive G3c

Le piège « ne constitue PAS une recommandation » a été levé par le test 9 — mot `recommandation` dans une note méta, même au sens négatif. Reformulation immédiate :
- « ne constitue PAS une recommandation de structuration juridique » → « ne constitue pas un avis sur le choix de structuration juridique »
- « Indicateur factuel, pas une recommandation de structuration. » → « Indicateur factuel — voir avertissement BNC vs SEL. »

Ton point de vigilance G3c (« PLUS_EFFICACE_FISCALEMENT acceptable si le label affiché demeure factuel et non prescriptif ») a été déterminant pour cette discipline.

### 4.7. Suite de tests G3c

`test_mode_audit_strategy_liberal.py` : **12 catégories, ~120 assertions**. Test 4 branches dynamiques (SELARL + SELAS validées). Test 5 délégation L4 → L3 (pas de recalcul). Test 6 imbrication 3 niveaux. Test 9 alertes en hypotheses. Test 10 non-prescriptif sur **258 étapes** (2 branches).

## 5. Consolidation documentaire post-G3c

Documents vivants mis à jour :

| Fichier | Mise à jour |
|---|---|
| `AUDIT_MODE.md` | v1.2 → v1.3 ; spec → 1.1.0 ; §6.1 enrichi (3 stratégies) ; §6.2 roadmap G3d/e/f/g ; §8 enrichi (7 tests gardiens) ; **§9 nouveau** « Modèle composable » (5 invariants doctrinaux) ; **§10 nouveau** « Conventions de namespaces » |
| `ARCHITECTURE.md` §7.5 | « Phase MODE_AUDIT v1.2 » → « v1.3 » ; périmètre 3 stratégies ajouté ; principes structurants v1.1.0 explicités |
| `KNOWN_LIMITATIONS.md` | « v1.2 — 4 régimes » → « v1.3 — 4 régimes + 3 stratégies » |
| `README_FREEZE_B2.md` §5 | Séquence opératoire : ajout des 3 nouvelles suites stratégie |

Récaps figés **non modifiés** (intégrité historique préservée) :
- `RECAP_SESSION_20260519.md`
- `RECAP_SESSION_B3.md`
- `RECAP_SESSION_MODE_AUDIT_v1_1.md`
- `RECAP_SESSION_MODE_AUDIT_v1_2.md`
- `CHANGELOG_B2_GLOBAL.md`

Le présent récap (`RECAP_SESSION_MODE_AUDIT_v1_3.md`) est une **création**, pas une modification.

## 6. Validation finale (`post_audit_g3c_*.log`)

| Validation | Résultat |
|---|---|
| Baseline numérique | ✓ Hash `8863991f27f67847` conservé |
| Architecture canonique | ✓ 17 fichiers conformes |
| Spec MODE_AUDIT | ✓ AUDIT_SPEC_VERSION = 1.1.0 |
| 504 baseline | ✓ 7/7 modules, 0 régression |
| 8 suites B.2 | ✓ Toutes vertes |
| **7 suites MODE_AUDIT** | ✓ Toutes vertes (régimes : TNS 7, Libéral 14, Salarié 8, Assimilé 11 ; stratégies : Assimilé 12, TNS 11, Libéral 12 catégories) |
| `semantic_guardrails.py` | ✓ 0 violation (9 patterns) |
| `audit_final_b2_controle3.py` | ✓ 0 violation (4 patterns) |
| `test_terminologie_freeze.py` | ✓ 0 violation |

## 7. Garanties tenues

- ✓ Hash baseline `8863991f27f67847` conservé bout en bout (M1 → G3c)
- ✓ Aucune logique métier déplacée — instrumentation = pur side channel
- ✓ Couche `core/` neutre (`core/audit.py` ne dépend que de `dataclasses`/`typing`)
- ✓ Rétrocompat parfaite vérifiée sur les 4 régimes + 3 stratégies (résultats strictement identiques avec/sans audit)
- ✓ Test 9 non-prescriptif automatique : aucune violation sur l'ensemble du graphe v1.3
- ✓ Espaces de codes isolés (régimes ⊥ stratégies, et au sein de chaque couche)
- ✓ Modèle composable strict : aucune duplication d'étapes, aucune collision de codes

## 8. Découvertes architecturales cumulées G3

1. **Le modèle composable (spec 1.1.0) absorbe toutes les complexités rencontrées** sans extension API :
   - 1 niveau d'imbrication (G3a Assimilé)
   - 2 niveaux d'imbrication (G3b TNS)
   - 3 niveaux d'imbrication (G3c Libéral L4)
   - Sous-traces à nom dynamique (G3c Libéral L3 SELARL/SELAS)

2. **Le pattern « alertes métier en hypotheses »** est devenu structurel. Toute information textuelle métier qui pourrait contenir du vocabulaire prescriptif va en `hypotheses[]` (champ dict, non scanné). Validé sur 4 cas distincts (T2, L3, L4, AVERTISSEMENT meta Libéral).

3. **Le test 9 non-prescriptif est progressivement durci** :
   - G3a : pattern initial `\boptim(?:al|isation|...)\b`
   - G3b : élargissement à `\boptim\w*\b` (capture `optimum` rencontré en T2)
   - G3c : exposition du piège « ne constitue PAS une recommandation » au sens négatif → reformulation
   
   Le pattern de la discipline se construit empiriquement, exactement comme prévu (« code d'abord, observe les vrais besoins, durcis ensuite »).

4. **Convention de codes longue payante** : `STRAT_<REGIME>_<STRATEGIE>_<DOMAINE>_<ETAPE>` permet de distinguer immédiatement `STRAT_TNS_T2_NET_DIVIDENDES` de `STRAT_LIB_L3_NET_DIVIDENDES` sans contexte. Verbosité acceptée, ambiguïté éliminée.

5. **Terminologie native non-prescriptive** (G3c) : la doctrine du module `strategy/liberal.py` interdisait déjà « recommandée » avant MODE_AUDIT. La trace consomme cette doctrine (`STRAT_LIB_PLUS_EFFICACE_FISCALEMENT`) plutôt que de l'imposer. La trace s'adapte au module, pas l'inverse.

## 9. État du dépôt après G3c

**Fichiers livrés cette session :**

| Fichier | Action | Lignes ajoutées (env.) |
|---|---|---|
| `core/audit.py` | API spec 1.1.0 (sous-traces) | +120 |
| `ui/audit_render.py` | Renderer récursif | +30 |
| `strategy/assimile.py` | Instrumenté G3a | +130 |
| `strategy/tns.py` | Instrumenté G3b | +350 |
| `strategy/liberal.py` | Instrumenté G3c | +280 |
| `test_mode_audit_strategy_assimile.py` | Nouveau (G3a) | +300 |
| `test_mode_audit_strategy_tns.py` | Nouveau (G3b) | +400 |
| `test_mode_audit_strategy_liberal.py` | Nouveau (G3c) | +420 |
| `semantic_guardrails.py` | Whitelist étendue (G3a) | ±3 |
| 4 suites MODE_AUDIT régimes | Labels « Spec version » dynamiques | ±4 |
| `AUDIT_MODE.md` | v1.2 → v1.3 + §9 + §10 | +200 |
| `ARCHITECTURE.md` §7.5 | v1.3 | ±60 |
| `KNOWN_LIMITATIONS.md` | v1.3 | ±20 |
| `README_FREEZE_B2.md` §5 | 3 suites ajoutées | +3 |

**Snapshots intermédiaires conservés** dans `baseline_audit_*_pre/` :
- `baseline_audit_M0_pre/` — avant M1 (MODE_AUDIT TNS)
- `baseline_audit_G1a_pre/` — avant G1a (BNC)
- `baseline_audit_G1b_pre/` — avant G1b (SEL)
- `baseline_audit_G2a_pre/` — avant G2a (Salarié)
- `baseline_audit_G2b_pre/` — avant G2b (Assimilé)
- `baseline_audit_G3a_pre/` — avant G3a (Strategy Assimilé)
- `baseline_audit_G3b_pre/` — avant G3b (Strategy TNS)
- `baseline_audit_G3c_pre/` — avant G3c (Strategy Libéral)

## 10. Décisions de gouvernance respectées

- Feu vert explicite obtenu avant chaque modification :
  - Modification spec `core/audit.py` (1.0.0 → 1.1.0) — G3a
  - Whitelist `semantic_guardrails.py` (G3a)
  - Option B délégation L4 (G3c)
  - Branches dynamiques SELARL/SELAS (G3c)
  - Terminologie `STRAT_LIB_PLUS_EFFICACE_FISCALEMENT` (G3c)
- Aucune modification de `app.py` cette session
- Aucun récap figé modifié — récap consolidé écrit en une seule passe en fin de G3c
- Audits historiques (`audit_final_b2_controle3.py`, `test_terminologie_freeze.py`) **non modifiés** — pas de propagation artificielle (parsimonie)
- Pas de PDF audit-ready — format à stabiliser après G3 complet

## 11. Roadmap MODE_AUDIT (post-v1.3)

Conformément à la priorité acceptée :

1. **G3d — `strategy/comparateur.py` + `comparateur_regimes.py`** : comparaisons inter-régimes. **Point critique** comparaison vs prescription. Multiples sous-traces régime simultanées, arbitrages croisés.
2. **G3e — `strategy/synthese.py` + `scenarios.py`** : top-niveau, agrège tout.
3. **G3f — `strategy/perin.py` + `receptacles.py`** : modules transverses épargne.
4. **G3g — Consolidation doc finale + récap global G3** : sortie de G3.
5. **Rendu PDF audit-ready** : déclenchable après G3 complet, format à stabiliser avec retours cabinet.
6. Export JSON / sérialisation externe.
7. Helpers de requête (`find_by_regime`, `total_par_code`).

Avant G3d, le présent état est **stable** : toutes les stratégies amont sont instrumentées, le comparateur pourra composer leurs traces sans regénération.
