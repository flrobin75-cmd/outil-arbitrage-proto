# Session 19/05/2026 — MODE_AUDIT v1.4 (G3d + G3d-bis : couche comparateur complète)

**Statut final :** ✓ Session complète. MODE_AUDIT couvre désormais **les 4 régimes + 3 modules stratégie + 2 modules comparateur**. La spec 1.1.0 a tenu la charge jusqu'à **6 niveaux d'imbrication** (G3d-bis). Tout au vert sur 8 suites B.2 + 3 audits sémantiques + **9 suites MODE_AUDIT**. Hash baseline `8863991f27f67847` conservé.

---

## 1. Point de départ

État post-MODE_AUDIT v1.3 (4 régimes + 3 stratégies instrumentés) livré en consolidation précédente.

Roadmap acceptée pour G3d + G3d-bis :
1. G3d — `strategy/comparateur.py` (723 lignes, comparateur de dispositifs)
2. G3d-bis — `strategy/comparateur_regimes.py` (267 lignes, comparateur inter-régimes)

Point de vigilance ouvert : « le comparateur introduit comparaisons croisées, multiples sous-traces simultanées, arbitrages inter-régimes, risques de duplication, risques sémantiques, risques de prescription implicite ». Cadrage requis avant code.

## 2. G3d — Instrumentation `strategy/comparateur.py` (module autonome)

### 2.1. Découverte clé du cadrage

**Le module est totalement autonome** : aucun import depuis `regime/*` ni `strategy/{tns,liberal,assimile}.py`. Le seul import strategy est `from strategy.receptacles import est_accessible, motif_inaccessibilite` (helpers G3f reportés, pas les stratégies G3a/b/c). Donc **pas de composition** à faire — la trace est plate, structurée uniquement par `parent_id`. **Premier module G3 sans imbrication.**

Décisions doctrinales validées en cadrage :
- Namespace `COMP_*` dédié (pas `STRAT_*`) — un comparateur n'est pas une stratégie mono-régime
- Aucune sous-trace attachée
- Discipline label « rang dans le classement par score » (pas « meilleur/top »)
- Label épuré + nom intégral préservé en `hypotheses` (emoji 💸 cashback conservé)

### 2.2. Découpage 4 sous-passes

| Sous-passe | Périmètre | Étapes |
|---|---|---|
| G3d.1 | Section A (paramètres dérivés) + signature `audit` opt-in | 6 racines `COMP_*` |
| G3d.2 | 15 lignes via `_ligne_*` + podium top 3 | 1 NB_LIGNES + 15 LIGNE_<NN>_* + 2 TOP3 base + 3 RANG |
| G3d.3 | Réceptacles (4 vues) + alertes (3 counts par sévérité) | 1 NB_RECEPTACLES + 4 RECEPTACLE_* + 4 alertes |
| G3d.4 | Suite `test_mode_audit_strategy_comparateur.py` | 14 catégories, ~150 assertions |

### 2.3. Trace G3d finale (profil par défaut)

```
Strategy/Comparateur (plate, pas de sous-trace)             — 36 étapes COMP_*
├── Section A : COMP_REVENU_IMPOSABLE_PAR_PART, COMP_TMI_ESTIMEE, …
├── COMP_NB_LIGNES (=15)
│     ├── COMP_LIGNE_00_SALAIRE … COMP_LIGNE_14_PERO (15 enfants)
├── COMP_TOP3_CRITERE (= "tri décroissant sur score_ajuste = ratio_net_cout × coef_risque")
│     ├── COMP_TOP3_RANG_1 (parent_id=CRITERE)
│     ├── COMP_TOP3_RANG_2
│     └── COMP_TOP3_RANG_3
├── COMP_TOP3_NB
├── COMP_NB_RECEPTACLES (=4)
│     ├── COMP_RECEPTACLE_PEE / PERECO / PERO / PERIN
├── COMP_ALERTES_NB
      ├── COMP_ALERTES_ERROR_NB / WARNING_NB / INFO_NB
```

### 2.4. Innovation : pattern Top 3 audité comme classement mécanique

Le risque sémantique « top 3 prescriptif » a été levé par discipline de label :
- `COMP_TOP3_CRITERE.valeur = "tri décroissant sur score_ajuste = ratio_net_cout × coef_risque"` (formule factuelle)
- `COMP_TOP3_RANG_<R>.label = "Rang R dans le classement par score"`
- `COMP_TOP3_CRITERE.notes = "Classement mécanique sur scores. Ne reflète pas un avis sur le choix de dispositif."`

Le mot « top » reste dans le code Python (`top3_rang`, `appliquer_top3`) mais n'apparaît jamais comme superlatif dans les labels rendus. Application directe de la consigne « `top3` peut rester un terme de code si le rendu utilisateur ne devient jamais prescriptif ».

### 2.5. Pattern alertes intégrales en hypotheses (systématisé G3b/G3c)

6 textes d'alertes métier (lectures URSSAF, plafonds dépassés) sont sérialisés dans `COMP_ALERTES_NB.hypotheses["textes_alertes_integraux"]`. Counts factuels par sévérité dans la trace. Aucun mot prescriptif n'apparaît dans labels ou notes.

## 3. G3d-bis — Instrumentation `strategy/comparateur_regimes.py` (composition naturelle)

### 3.1. Découverte clé du cadrage

**Le module compose réellement les 3 stratégies G3a/b/c + le module Salarié G2a** (lignes 46-48 du source). Application directe de §9.2 du MODE_AUDIT (« une stratégie compose, ne réémet pas »). Premier cas où une trace MODE_AUDIT atteindra **6 niveaux d'imbrication**.

Décisions doctrinales validées en cadrage :
- Namespace `COMP_REG_*` distinct de `COMP_*` (couche conceptuelle différente : inter-régimes vs intra-régime)
- Sous-traces composées : `arbitrage_assimile`, `arbitrage_tns`, `arbitrage_liberal`, `module_salarie`
- Terminologie `COMP_REG_NET_LE_PLUS_ELEVE` (factuel, pas `RETENU` ni `MEILLEUR`)
- 7 étapes par ligne régime, granularité « suffisante pour tracer l'arbitrage sans noyer la lecture »

### 3.2. Découpage 3 sous-passes

| Sous-passe | Périmètre | Étapes |
|---|---|---|
| G3d-bis.1 | 4 helpers `_ligne_*` instrumentés | 4 × 7 étapes + 4 sous-traces composées |
| G3d-bis.2 | Routeur `calcul_comparateur_regimes` méta | 5 étapes méta + 4 sous-traces `ligne_<X>` |
| G3d-bis.3 | Suite `test_mode_audit_strategy_comparateur_regimes.py` | 14 catégories, ~140 assertions |

### 3.3. Graphe G3d-bis (profil SELARL par défaut)

```
calcul_comparateur_regimes (méta)                           — 5 étapes COMP_REG_*
├── ligne_assimile                                           — 7 étapes COMP_REG_ASSIM_*
│     └── arbitrage_assimile                                 — 7 étapes STRAT_ASSIM_*
│           ├── tx_ir_moy                                    — 11 étapes ASSIM_TX_IR_MOY_*
│           └── strategie_A/B/C/D                            — 4 × 13 étapes STRAT_ASSIM_<X>_*
├── ligne_tns                                                — 7 étapes COMP_REG_TNS_*
│     └── arbitrage_tns                                      — 7 étapes STRAT_TNS_*
│           ├── strategie_T1                                 — 12 étapes
│           │     └── module_tns                             — 24 étapes TNS_*
│           └── strategie_T2/T3/T4 + module_tns × 3
├── ligne_liberal                                            — 7 étapes COMP_REG_LIB_*
│     └── arbitrage_liberal                                  — 7 étapes STRAT_LIB_*
│           ├── strategie_L1                                 — 7 étapes
│           │     └── module_bnc                             — 16 étapes LIB_BNC_*
│           ├── strategie_L2 → module_bnc
│           ├── strategie_L3 → module_tns (24 étapes)
│           └── strategie_L4                                 — 3 étapes
│                 └── strategie_l3_deleguee                  — 14 étapes
│                       └── module_tns                       — 24 étapes TNS_*   ← NIVEAU 6
└── ligne_salarie                                            — 7 étapes COMP_REG_SAL_*
      └── module_salarie                                     — 17 étapes SAL_*

Total : 412 étapes structurées, 6 niveaux de profondeur maximum.
```

### 3.4. Innovation : garde-fou T4 transversal

Le bénéfice retenu T4 (convention de non-agrégation héritée du module TNS — G3b) est explicité au niveau méta du comparateur régimes par `COMP_REG_INDICATEURS_SEPARES_T4`. C'est la première fois qu'une convention sémantique de stratégie est **propagée explicitement à une couche supérieure** :
- Valeur = `ligne.benefice_retenu_societe` de la ligne TNS
- `hypotheses["convention"] = "non-agrégation T4 (transversale aux niveaux)"`
- `hypotheses["regle"] = "Ne PAS sommer avec net_dirigeant pour le classement"`
- `notes = "Convention de non-agrégation T4 transversale au comparateur régimes (héritée du module TNS)"`

### 3.5. Innovation : 3 disclaimers permanents en hypotheses

`COMP_REG_DISCLAIMERS_NB = 3.0` au niveau méta, avec :
- `hypotheses["DISCLAIMER_CHANGEMENT_REGIME"]` = texte intégral (cadrage indicatif)
- `hypotheses["DISCLAIMER_COMPARABILITE"]` = texte intégral (ordres de grandeur)
- `hypotheses["NOTE_RADAR_INTRA_REGIME"]` = texte intégral

Pattern G3b/G3c/G3d systématisé : aucun mot prescriptif dans labels/notes, wording métier intégral préservé en `hypotheses`. **412 étapes scannées par le test non-prescriptif × 12 patterns = 0 violation.**

### 3.6. Innovation : terminologie `NET_LE_PLUS_ELEVE`

La méta utilise `COMP_REG_NET_LE_PLUS_ELEVE` (factuel et mesurable) au lieu de `COMP_REG_RETENU` (réservé aux régimes mono-couche) ou `COMP_REG_MEILLEUR_*` (prescriptif). Test 2 vérifie explicitement l'absence de ces deux alternatives.

Cohérent avec la doctrine du module source (lignes 30-34) : « PAS de "régime recommandé" automatique ».

## 4. Consolidation documentaire post-G3d-bis

Documents vivants mis à jour :

| Fichier | Mise à jour |
|---|---|
| `AUDIT_MODE.md` | v1.3 → v1.4 ; §6.1 enrichi (8 modules instrumentés, 9 suites) ; §6.2 roadmap G3e/f/g ; §8 enrichi (9 tests gardiens, 8.8 + 8.9 ajoutés) ; §10.2 enrichi (familles `COMP_*` et `COMP_REG_*`) ; §10.3 + §10.4 enrichis (isolation comparateurs + noms de sous-traces) |
| `ARCHITECTURE.md` §7.5 | v1.3 → v1.4 ; 2 lignes comparateur ajoutées au tableau ; principes structurants enrichis (codes comparateur) |
| `KNOWN_LIMITATIONS.md` | v1.3 → v1.4 ; 2 modules comparateur ajoutés au « Couvert » ; G3e marqué « bascule conceptuelle, cadrage requis avant code » |
| `README_FREEZE_B2.md` §5 | 2 suites comparateur ajoutées à la séquence opératoire |

Récaps figés **non modifiés** (intégrité historique préservée) :
- `RECAP_SESSION_20260519.md`, `RECAP_SESSION_B3.md`
- `RECAP_SESSION_MODE_AUDIT_v1_1.md`, `v1_2.md`, `v1_3.md`
- `CHANGELOG_B2_GLOBAL.md`

Le présent récap (`RECAP_SESSION_MODE_AUDIT_v1_4.md`) est une **création**.

## 5. Validation finale post-G3d-bis (`post_audit_g3dbis_*.log`)

| Validation | Résultat |
|---|---|
| Baseline numérique | ✓ Hash `8863991f27f67847` conservé |
| Architecture canonique | ✓ 17 fichiers conformes |
| Spec MODE_AUDIT | ✓ AUDIT_SPEC_VERSION = 1.1.0 |
| 504 baseline | ✓ 7/7 modules, 0 régression |
| 8 suites B.2 | ✓ Toutes vertes |
| **9 suites MODE_AUDIT** | ✓ Toutes vertes |
| `semantic_guardrails.py` | ✓ 0 violation (9 patterns) |
| `audit_final_b2_controle3.py` | ✓ 0 violation (4 patterns) |
| `test_terminologie_freeze.py` | ✓ 0 violation |

## 6. Découvertes architecturales cumulées G3d/G3d-bis

1. **Le modèle composable (spec 1.1.0) absorbe nativement le cas « trace plate »** (G3d) et **le cas « imbrication 6 niveaux »** (G3d-bis) sans extension API. `attacher_sous_trace()` n'est appelé nulle part en G3d (parce que rien à composer) et 4 fois en G3d-bis (4 stratégies amont). Le renderer récursif gère `sous_traces == {}` comme cas de base et descend autant que nécessaire.

2. **Le namespace `COMP_*`/`COMP_REG_*` parallèle valide la décision de séparation**. Les deux modules partagent une philosophie (classement mécanique, anti-prescription) mais des structures distinctes (lignes/réceptacles/top3 vs lignes/régimes/disclaimers). Mélanger les namespaces aurait compliqué les tests d'isolation. Test 8 vérifie `COMP_REG_*` ⊥ `COMP_<autre>_` (sans REG).

3. **Le pattern « alertes/disclaimers en hypotheses »** est désormais structurel. Validé sur 4 cas distincts (G3b alertes T2, G3c alertes BNC/SEL, G3d alertes URSSAF, G3d-bis disclaimers permanents). Le wording métier intégral est préservé, la trace MODE_AUDIT reste factuelle.

4. **Le test 9/11 non-prescriptif scanne désormais jusqu'à 412 étapes en une exécution** (G3d-bis). 0 violation. La discipline tient sur toute la chaîne de composition.

5. **Le pattern « convention transversale aux niveaux »** émerge en G3d-bis (`COMP_REG_INDICATEURS_SEPARES_T4`). Quand une convention sémantique de stratégie (ici la non-agrégation T4 héritée de G3b) doit être préservée par une couche supérieure, la trace l'explicite par une étape méta dédiée. Pattern à appliquer en G3e si la synthèse touche aux mêmes invariants.

6. **L'instrumentation par sous-passes avec validations intermédiaires** est devenue le pattern de travail G3 standard. G3d (4 sous-passes), G3d-bis (3 sous-passes). Chaque sous-passe ferme la rétrocompat avant la suivante. Aucune régression sur tout le chantier.

## 7. Garanties tenues

- ✓ Hash baseline `8863991f27f67847` conservé bout en bout (M1 → G3d-bis)
- ✓ Aucune logique métier déplacée — instrumentation = pur side channel
- ✓ Couche `core/` neutre (`core/audit.py` ne dépend que de `dataclasses`/`typing`)
- ✓ Rétrocompat parfaite vérifiée sur 8 modules instrumentés (résultats strictement identiques avec/sans audit)
- ✓ Test 9/11 non-prescriptif automatique : aucune violation sur l'ensemble du graphe v1.4
- ✓ Espaces de codes isolés (régimes ⊥ stratégies ⊥ comparateurs)
- ✓ Modèle composable strict : aucune duplication d'étapes, aucune collision de codes
- ✓ Convention de non-agrégation T4 préservée transversalement (G3b → G3c → G3d-bis)

## 8. État du dépôt après G3d-bis

**Fichiers livrés cette session (G3d + G3d-bis) :**

| Fichier | Action | Lignes ajoutées (env.) |
|---|---|---|
| `strategy/comparateur.py` | Instrumenté G3d | +185 |
| `strategy/comparateur_regimes.py` | Instrumenté G3d-bis | +230 |
| `test_mode_audit_strategy_comparateur.py` | Nouveau (G3d) | +380 |
| `test_mode_audit_strategy_comparateur_regimes.py` | Nouveau (G3d-bis) | +470 |
| `AUDIT_MODE.md` | v1.3 → v1.4 | ±100 |
| `ARCHITECTURE.md` §7.5 | v1.4 | ±35 |
| `KNOWN_LIMITATIONS.md` | v1.4 | ±20 |
| `README_FREEZE_B2.md` §5 | 2 suites ajoutées | +2 |

**Snapshots intermédiaires conservés** dans `baseline_audit_*_pre/` :
- `baseline_audit_G3d_pre/` — avant G3d (et G3d-bis, proche temporellement)

## 9. État global MODE_AUDIT après v1.4

| Couche | Modules instrumentés | Étapes typiques |
|---|---|---|
| Régimes (G1 + G2) | TNS, Libéral BNC/SEL, Salarié, Assimilé (tx_ir + fs) | ~75 étapes |
| Stratégies (G3a/b/c) | Assimilé, TNS, Libéral | ~430 étapes structurées |
| **Comparateurs (G3d + G3d-bis)** | comparateur (dispositifs) + comparateur_regimes | **36 + 412 = 448 étapes** |
| **Total v1.4** | 8 modules + spec 1.1.0 + 9 suites MODE_AUDIT (80+ catégories) | **~950 étapes au cumul** |

## 10. Décisions de gouvernance respectées

- Feu vert explicite obtenu avant chaque modification :
  - Découpage G3d en 4 sous-passes (G3d.1 → G3d.4)
  - Namespace `COMP_*` autonome (G3d)
  - Top 3 audité comme classement mécanique (G3d)
  - Découpage G3d-bis en 3 sous-passes
  - Namespace `COMP_REG_*` distinct (G3d-bis)
  - Composition naturelle 3 stratégies + module Salarié (G3d-bis)
  - Terminologie `COMP_REG_NET_LE_PLUS_ELEVE` (G3d-bis)
- Aucune modification de `app.py` cette session
- Aucun récap figé modifié — récap consolidé écrit en une seule passe en fin de G3d-bis
- Audits historiques (`semantic_guardrails.py`, `audit_final_b2_controle3.py`, `test_terminologie_freeze.py`) **non modifiés** — parsimonie
- Pas de PDF audit-ready — format à stabiliser après G3 complet

## 11. Roadmap MODE_AUDIT (post-v1.4)

Conformément à la priorité acceptée :

1. **G3e — `strategy/synthese.py` (926 lignes) + `scenarios.py` (204 lignes)** : **bascule conceptuelle** vers l'agrégation et l'orchestration top-niveau. Risques nouveaux à anticiper :
   - Synthèse top-niveau : potentiel de narration implicite plus élevé
   - Agrégation : tentation d'écraser les indicateurs séparés (T4, BNC/SEL)
   - Orchestration : multiplication des chemins → graphe plus complexe
   - Cadrage avant code requis (séquencement validé : G3d-doc → cadrage G3e → G3e.1 synthese → G3e.2 scenarios → G3e.3 tests + doc)
2. **G3f — `strategy/perin.py` (163 lignes) + `receptacles.py` (236 lignes)** : modules transverses épargne. Plus simple sur le plan structurel.
3. **G3g — Consolidation doc finale + récap global G3** : sortie de G3.
4. **Rendu PDF audit-ready** : déclenchable après G3 complet, format à stabiliser avec retours cabinet.
5. Export JSON / sérialisation externe.
6. Helpers de requête (`find_by_regime`, `total_par_code`).

Avant G3e, l'état est **stable** : toute la couche comparateur est instrumentée, la synthèse pourra composer leurs traces sans regénération.
