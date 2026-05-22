# Session 19/05/2026 — MODE_AUDIT v1.6 (G3f complet : perin.py + receptacles.py)

**Statut final :** ✓ Session complète. MODE_AUDIT couvre désormais **les 4 régimes + 3 modules stratégie + 2 modules comparateur + 2 modules post-arbitrage + 2 modules transverses épargne**. La spec 1.1.0 est inchangée et tient toujours la charge sur 12 modules instrumentés. Tout au vert sur 8 suites B.2 + 3 audits sémantiques + **13 suites MODE_AUDIT**. Hash baseline `8863991f27f67847` conservé.

---

## 1. Point de départ

État post-MODE_AUDIT v1.5 (10 modules instrumentés : 4 régimes + 3 stratégies + 2 comparateurs + 2 post-arbitrage) livré en consolidation précédente. Le jalon v1.5 était considéré comme « le sommet du chantier » — toutes les bascules conceptuelles avaient été franchies (synthèse top-niveau, scénarios autonomes, composition asymétrique).

G3f était positionné comme la dernière étape d'instrumentation pure avant la consolidation finale G3g. Hypothèse de cadrage : « modules transverses, simples structurellement, pas de bascule conceptuelle ».

Cadrage validé en début de session (5 points) :
1. Namespaces `PERIN_*` et `RECEPT_*` orthogonaux à toutes les familles existantes
2. Sous-traces composées : `plafond_dirigeant` (toujours), `plafond_conjoint` (conditionnelle) pour `calcul_perin_mutualise` ; `regime_effectif` pour `est_accessible` ; `accessibilite` pour `motif_inaccessibilite` ; pas de sous-traces pour `liste_receptacles_par_regime`
3. Découpage en 3 sous-passes : G3f-perin.1 + G3f-receptacles.1 + G3f.2
4. **Option A** : ne pas rétro-instrumenter `comparateur.py` → `receptacles.py` (dette documentée, jalon G3d-ter futur)
5. Profondeur 3 niveaux pour `motif_inaccessibilite → accessibilite → regime_effectif` validée

## 2. G3f-perin.1 — `calcul_plafond_perin` + `calcul_perin_mutualise`

**Périmètre :** 2 fonctions, 19 étapes méta + 14 étapes plates dans les 2 sous-traces composables.

### 2.1. `calcul_plafond_perin` (7 étapes plates)

Module trivial structurellement (formule `max(min(...)`), riche en doctrine (CGI art. 163 quatervicies). 7 étapes plates avec :
- `PERIN_TITULAIRE` (string "Dirigeant" ou "Conjoint")
- `PERIN_REVENU_PRO_N_MOINS_1` (input EUR)
- `PERIN_PLAFOND_CALCULE` (10 % rev. pro., doctrine_ref `PASS_2026`)
- `PERIN_PLAFOND_PLANCHER` (= constante module 10 % PASS)
- `PERIN_PLAFOND_PLAFOND` (= constante module 8 PASS)
- `PERIN_PLAFOND_INDIVIDUEL` (= max-then-min appliqué, formule explicitée)
- `PERIN_SOLDE_DISPONIBLE_INITIAL` (= plafond avant versement)

Doctrine `PASS_2026` cité dans 3 étapes (calculé, plancher, plafond) avec formule en hypotheses.

### 2.2. `calcul_perin_mutualise` (12 étapes méta + 2 sous-traces conditionnelles)

Module à branches conditionnelles : avec ou sans mutualisation conjoint. **Composition conditionnelle** :
- `plafond_dirigeant` : toujours attachée
- `plafond_conjoint` : attachée si et seulement si situation == "Marié / pacsé" AND `conjoint_declare` AND `revenu_pro_conjoint > 0`

**Pattern non-prescriptif renforcé** : la condition logique de mutualisation est explicitement tracée en `hypotheses["condition"]` avec chaque sous-condition évaluée séparément. Pas d'inférence implicite.

**Branche tracée** : `PERIN_PLAFOND_TOTAL_RETENU.hypotheses["branche"]` = `"sans_mutualisation"` ou `"avec_mutualisation"`. Le code de la fonction utilise effectivement 2 branches `return` distinctes, l'instrumentation reflète fidèlement cette dualité.

**Excédent factuel** : `PERIN_VERSEMENT_EXCEDENT.hypotheses["depasse_plafond"]` = `bool(excedent > 0)`. Pas d'alerte texte synthétique car absente du code source.

### 2.3. Structure complète du graphe

```
calcul_perin_mutualise                          — 12 étapes PERIN_*
├── plafond_dirigeant                            — 7 étapes PERIN_*
└── plafond_conjoint (si mutualisation)          — 7 étapes PERIN_*

Total avec mutualisation : 26 étapes, 2 niveaux
Total sans mutualisation : 19 étapes, 2 niveaux
```

## 3. G3f-receptacles.1 — 5 fonctions de routage

**Périmètre :** 5 fonctions instrumentées, ~16 codes uniques, profondeur 3 niveaux internes.

### 3.1. `regime_effectif_receptacles` (4 étapes plates) — règle d'or

Fonction centrale qui implémente la « règle d'or » SELARL→TNS / SELAS→Assimilé. 4 étapes :
- `RECEPT_REGIME_SOCIAL_PROFIL` (input)
- `RECEPT_FORME_JURIDIQUE_PROFIL` (input)
- `RECEPT_FORME_SEL_PROFIL` (input, "(non applicable)" si vide)
- `RECEPT_REGIME_EFFECTIF` (sortie + branche tracée)

**6 branches explicites** tracées en `hypotheses["branche_appliquee"]` :
- `assimile_direct`
- `tns_direct`
- `selarl_vers_tns` (règle d'or)
- `selas_vers_assimile` (règle d'or)
- `liberal_bnc_pur`
- `salarie_ou_inconnu_fallback`

### 3.2. `est_accessible` (3-4 étapes + sous-trace conditionnelle)

**Branche short-circuit** : si le réceptacle n'est pas dans la matrice, retourne True sans composer `regime_effectif` (sécurité — ne pas bloquer un futur réceptacle non documenté). Cette branche est tracée en `hypotheses["branche"] = "receptacle_inconnu_fallback"`.

Si réceptacle connu : sous-trace `regime_effectif` attachée.

### 3.3. `motif_inaccessibilite` (1 étape + sous-trace `accessibilite`)

**Profondeur 3 niveaux** : `motif_inaccessibilite → accessibilite → regime_effectif`. C'est la profondeur maximale interne au module (la profondeur maximale globale du chantier reste 6 niveaux atteints en G3d-bis).

Cas accessible : retourne `None`, tracé en `hypotheses["valeur_python_retournee"]: None`.
Cas inaccessible : retourne `f"Non accessible en régime {regime_eff}."`, format explicité en `hypotheses["format_motif"]`.

### 3.4. `liste_receptacles_par_regime` (7 étapes plates volontaires)

**Trace plate volontaire** (cf. cadrage G3f, point 2.4). Pour éviter 12 sous-traces (`est_accessible` + `motif_inaccessibilite` × 6 réceptacles), on itère les 6 réceptacles en codes plats :
- `RECEPT_NB_RECEPTACLES_MODELISES` (= 6, racine)
- `RECEPT_RECEPTACLE_PEE`
- `RECEPT_RECEPTACLE_PERECO`
- `RECEPT_RECEPTACLE_PERO`
- `RECEPT_RECEPTACLE_PERIN`
- `RECEPT_RECEPTACLE_INTERESSEMENT`
- `RECEPT_RECEPTACLE_PARTICIPATION`

Convention « bruit structurel vs valeur d'audit » documentée en hypotheses.

### 3.5. `mention_madelin` (1 étape constante)

Wording métier intégral en `hypotheses["MADELIN_PER_TNS_MENTION"]` (184 chars). Pattern systématique pour textes structurants : label factuel + texte en hypotheses.

## 4. G3f.2 — 2 suites de tests dédiées

### 4.1. `test_mode_audit_strategy_perin.py` (13 catégories, 194 étapes scannées)

- Test 5 dédié à la **composition conditionnelle** : 4 scénarios distincts (Marié déclaré rev>0, Marié non déclaré, Marié déclaré rev=0, Célibataire forcé)
- Tests 6/7/8 cas limites : plancher 10% PASS, plafond 8 PASS, excédent versement
- Test 9 branches tracées : sans/avec mutualisation
- Test 10 cohérence : 6 mappings trace ↔ résultat vérifiés
- Test 11 non-prescriptif renforcé : 0 violation sur 194 étapes × 14 patterns

### 4.2. `test_mode_audit_strategy_receptacles.py` (12 catégories, 46 étapes scannées)

- Test 1 rétrocompat : 5 fonctions × scénarios variés (24 assertions)
- Test 5 profondeur 3 niveaux : `motif → accessibilite → regime_effectif` vérifié structurellement
- Test 6 trace plate volontaire : NB + 6 réceptacles, 0 sous-trace
- Test 7 mention_madelin : fragments-clés absents de label/notes
- Test 8 règle SELARL/SELAS : 2 branches tracées et vérifiées
- Test 9 short-circuit : réceptacle inconnu retourne True sans sous-trace `regime_effectif`
- Test 10 cohérence : 5 mappings trace ↔ retour vérifiés
- Test 11 non-prescriptif renforcé : 0 violation sur 46 étapes × 14 patterns

## 5. Consolidation documentaire post-G3f

Documents vivants mis à jour :

| Fichier | Mise à jour |
|---|---|
| `AUDIT_MODE.md` | v1.5 → v1.6. §6.1 enrichi (12 modules, 13 suites, périmètre transverses). §6.2 roadmap : G3g devient prochaine étape (principalement documentaire), G3d-ter ajouté en faible priorité. §8.12 et §8.13 ajoutés (transverses épargne), §8.14 renuméroté. §10.2 enrichi (tableau dédié transverses). §10.3 isolation étendue. §10.4 enrichi (2 blocs : sous-traces perin + sous-traces receptacles). |
| `ARCHITECTURE.md` §7.5 | v1.5 → v1.6. Tableau enrichi (2 lignes G3f). Codes G3f dans principes structurants. Bénéfice collatéral G3f documenté (dette rétro-instrumentation). |
| `KNOWN_LIMITATIONS.md` | v1.5 → v1.6. 2 modules transverses au « Couvert ». **Dette G3d-ter** explicitement assumée (rétro-instrumentation comparateur → receptacles). |
| `README_FREEZE_B2.md` §7 | 2 suites G3f ajoutées à la séquence opératoire (13 suites au total) |
| `RECAP_SESSION_MODE_AUDIT_v1_6.md` | **NOUVEAU** — récap consolidé G3f (perin + receptacles) |

Récaps figés **non modifiés** (intégrité historique préservée) :
- `RECAP_SESSION_20260519.md`, `RECAP_SESSION_B3.md`
- `RECAP_SESSION_MODE_AUDIT_v1_1.md` à `v1_5.md`
- `CHANGELOG_B2_GLOBAL.md`

## 6. Validation finale post-G3f complet

| Validation | Résultat |
|---|---|
| Baseline numérique | ✓ Hash `8863991f27f67847` conservé |
| Architecture canonique | ✓ 17 fichiers conformes |
| Spec MODE_AUDIT | ✓ AUDIT_SPEC_VERSION = 1.1.0 |
| 504 baseline | ✓ 7/7 modules, 0 régression |
| 6 suites B.2 standalone | ✓ Toutes vertes |
| **13 suites MODE_AUDIT** | ✓ Toutes vertes |
| `semantic_guardrails.py` | ✓ 0 violation (9 patterns) |
| `audit_final_b2_controle3.py` | ✓ 0 violation (4 patterns) |
| `test_terminologie_freeze.py` | ✓ 0 violation |
| Test 11 renforcé G3f | ✓ 0 violation sur 240 étapes (perin 194 + receptacles 46) × 14 patterns |

## 7. Découvertes cumulées G3f

1. **L'hypothèse de cadrage « modules mécaniques » a été validée.** G3f n'a introduit aucune nouvelle bascule conceptuelle. Les patterns inventés en G3a-G3e (composition spec 1.1.0, branches tracées, conditions explicites en hypotheses, terminologie factuelle, namespace isolé, test 11 renforcé) ont été réutilisés tels quels sans adaptation. **C'est le signe d'une discipline mature** : on ajoute des modules sans réinventer la grammaire d'audit.

2. **Une dette d'instrumentation rétroactive a été identifiée mais explicitement reportée** (option A validée). `strategy/comparateur.py` consomme `est_accessible` et `motif_inaccessibilite` depuis G3d sans propager l'audit. La dette est documentée dans `KNOWN_LIMITATIONS.md` avec un jalon dédié `G3d-ter`. Cette décision préserve l'intégrité du livrable G3d figé : la rétro-instrumentation serait une modification structurelle, pas une simple extension, et elle ne touche que 3-4 appels (faible valeur ajoutée immédiate).

3. **La composition conditionnelle est désormais un pattern reconnu**. Inventé en G3c (branches dynamiques L3/L4), généralisé en G3e-synthese.4 (asymétrie `_synthese_*`), confirmé en G3f-perin.1 (`plafond_conjoint` attaché selon condition logique). Pattern réutilisable : **la sous-trace est attachée si et seulement si le calcul correspondant est effectivement exécuté**.

4. **La trace plate volontaire est un arbitrage architectural conscient**, pas un défaut. `liste_receptacles_par_regime` aurait pu attacher 12 sous-traces (6 réceptacles × 2 fonctions), mais cela aurait introduit du « bruit structurel » sans valeur d'audit ajoutée (chaque sous-trace serait quasi-identique en structure). La décision « trace plate, valeur factuelle » est documentée dans le code en hypotheses (`"convention_trace": "Trace plate volontaire — pas de sous-trace par réceptacle pour éviter surcharge structurelle"`) et vérifiée dans les tests (test 6 explicite sur l'absence de sous-traces).

5. **La grammaire §10.4 absorbe naturellement les nouveaux modules.** Aucun nouveau nom de sous-trace exotique n'a été inventé pour G3f : les noms sont descriptifs (`plafond_dirigeant`, `plafond_conjoint`, `regime_effectif`, `accessibilite`) et respectent la règle d'invariance à l'ordre. Le contrat de navigation par chemin symbolique tient.

## 8. Garanties tenues

- ✓ Hash baseline `8863991f27f67847` conservé bout en bout (M1 → G3f)
- ✓ Aucune logique métier déplacée — instrumentation = pur side channel
- ✓ Couche `core/` neutre (`core/audit.py` ne dépend que de `dataclasses`/`typing`)
- ✓ Rétrocompat parfaite vérifiée sur 12 modules instrumentés (résultats strictement identiques avec/sans audit)
- ✓ Test 11 non-prescriptif renforcé : 0 violation sur l'ensemble du graphe v1.6 (14 patterns)
- ✓ Espaces de codes isolés : 9 familles distinctes, aucune intrusion
- ✓ Modèle composable strict : aucune duplication d'étapes, aucune collision de codes
- ✓ Convention de non-agrégation T4 préservée transversalement (G3b → G3d-bis → G3e-synthese)
- ✓ Aucun récap figé modifié

## 9. État du dépôt après G3f

**Fichiers livrés cette session (G3f-perin + G3f-receptacles + G3f.2 + consolidation v1.6) :**

| Fichier | Action | Lignes ajoutées (env.) |
|---|---|---|
| `strategy/perin.py` | Instrumenté G3f-perin | +90 |
| `strategy/receptacles.py` | Instrumenté G3f-receptacles | +120 |
| `test_mode_audit_strategy_perin.py` | Nouveau (G3f.2) | +430 |
| `test_mode_audit_strategy_receptacles.py` | Nouveau (G3f.2) | +400 |
| `AUDIT_MODE.md` | v1.5 → v1.6 | ±100 |
| `ARCHITECTURE.md` §7.5 | v1.6 | ±20 |
| `KNOWN_LIMITATIONS.md` | v1.6 + dette G3d-ter | ±30 |
| `README_FREEZE_B2.md` §7 | 2 suites ajoutées | +3 |
| `RECAP_SESSION_MODE_AUDIT_v1_6.md` | NOUVEAU | +270 |

**Snapshots intermédiaires conservés** dans `baseline_audit_*_pre/` :
- `baseline_audit_G3f_pre/` — avant G3f (perin.py + receptacles.py originaux)

## 10. État global MODE_AUDIT après v1.6

| Couche | Modules instrumentés | Étapes typiques |
|---|---|---|
| Régimes (G1 + G2) | TNS, Libéral BNC/SEL, Salarié, Assimilé (tx_ir + fs) | ~75 étapes |
| Stratégies (G3a/b/c) | Assimilé, TNS, Libéral | ~430 étapes structurées |
| Comparateurs (G3d + G3d-bis) | comparateur (dispositifs) + comparateur_regimes | 36 + 412 = 448 étapes |
| Post-arbitrage (G3e) | synthese.py + scenarios.py | ~155 + 37 = ~192 étapes |
| **Transverses épargne (G3f)** | **perin.py + receptacles.py** | **~26 + ~16 = ~42 étapes** |
| **Total v1.6** | **12 modules + spec 1.1.0 + 13 suites MODE_AUDIT (120+ catégories)** | **~1187 étapes au cumul** |

## 11. Décisions de gouvernance respectées

- Feu vert explicite obtenu avant chaque modification :
  - Cadrage G3f validé en pré-code (5 questions de validation, toutes traitées)
  - Découpage G3f en 3 sous-passes accepté
  - Option A pour `comparateur.py → receptacles.py` (dette documentée) validée
  - Conventions terminologiques validées (namespaces `PERIN_*` et `RECEPT_*`, sous-traces nommées)
- Aucune modification d'`app.py` cette session
- Aucun récap figé modifié — récap consolidé écrit en une seule passe en fin de G3f
- Audits historiques (`semantic_guardrails.py`, `audit_final_b2_controle3.py`, `test_terminologie_freeze.py`) **non modifiés** — parsimonie
- `strategy/comparateur.py` (G3d) **non modifié** — option A respectée

## 12. Roadmap MODE_AUDIT (post-v1.6)

Conformément à la priorité acceptée et aux conditions d'achèvement :

1. **G3g — Consolidation doc finale + récap global G3** : **prochaine étape**. Conditions atteintes :
   - 12 modules instrumentés ✓
   - 13 suites MODE_AUDIT vertes ✓
   - Grammaire §10.4 stabilisée (4 familles + 2 transverses) ✓
   - Spec 1.1.0 inchangée ✓
   - Documents vivants alignés v1.6 ✓
   
   G3g est essentiellement **un travail de consolidation et de récap global G3** (pas d'instrumentation supplémentaire).

2. **Rendu PDF audit-ready** : déclenchable maintenant. Format à stabiliser avec retours cabinet (CSV/PDF/HTML, niveaux d'imbrication à afficher, niveau de détail des hypothèses, etc.).

3. **G3d-ter — Rétro-instrumentation comparateur → receptacles** : faible priorité, dette documentée. À programmer si besoin réel.

4. **Export JSON / sérialisation externe**.

5. **Helpers de requête** (`find_by_regime`, `total_par_code`).

6. **Extension `_synthese_tns/liberal`** (post-G3) : composition pleine des 6 calculs auxiliaires.

L'état post-G3f est **stable** : tous les modules métier identifiés du Strategy Engine sont instrumentés. Aucune dette structurelle ouverte autre que les sujets ci-dessus, tous explicitement reportés.
