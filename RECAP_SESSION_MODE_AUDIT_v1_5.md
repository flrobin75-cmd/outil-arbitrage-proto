# Session 19/05/2026 — MODE_AUDIT v1.5 (G3e complet : synthese.py + scenarios.py)

**Statut final :** ✓ Session complète. MODE_AUDIT couvre désormais **les 4 régimes + 3 modules stratégie + 2 modules comparateur + 2 modules post-arbitrage**. La spec 1.1.0 a tenu la charge avec un graphe asymétrique sur 10 modules instrumentés (G3e-synthese.4). Tout au vert sur 8 suites B.2 + 3 audits sémantiques + **11 suites MODE_AUDIT**. Hash baseline `8863991f27f67847` conservé.

---

## 1. Point de départ

État post-MODE_AUDIT v1.4 (4 régimes + 3 stratégies + 2 comparateurs instrumentés) livré en consolidation précédente. La couche comparateur (G3d + G3d-bis) était jugée le « pire endroit du codebase pour introduire de la prescription » — passée proprement.

Bascule conceptuelle prévue pour G3e : `synthese.py` (926 lignes) introduisait pour la première fois :
- une synthèse top-niveau (assemblage de résultats vs calcul de stratégies),
- une checklist conformité (vrai point de vigilance sémantique),
- un radar 6D pédagogique (risque de comparaison qualitative),
- un comparateur 2 scénarios (`scenarios.py`, 204 lignes) avec champ Python `gagnant` explicite.

Cadrage validé en début de session :
1. Namespaces séparés `SYNTH_*` et `SCEN_*` (cohérence avec G3d/G3d-bis)
2. Découpage G3e-synthese en 4 sous-passes par fonction (pas par stratégie comme G3b/c)
3. Découpage G3e-scenarios en 2 sous-passes
4. Sous-trace `module_salarie` uniquement dans `_synthese_salarie` (seul appel à un module instrumenté)
5. Pas de sous-trace externe dans `scenarios.py` (module autonome avec composition interne)
6. Convention radar `SYNTH_RADAR_<AXE>_<STRATEGIE>` (lecture verticale par axe)
7. Scenarios : `SCEN_SCENARIO_NET_LE_PLUS_ELEVE` factuel + `champ_source="gagnant"` en hypotheses

## 2. G3e-synthese.1 — `reset_forfaits` + `calcul_couts_mise_en_oeuvre`

**Périmètre :** 2 fonctions du module synthèse, 14 étapes ajoutées.

### 2.1. Découverte cadrage

`synthese.py` (926 lignes) est en réalité un **module multi-fonctions diversifié** — 7 fonctions de calcul de natures différentes (coûts, scoring, projection, waterfall, enveloppes, checklist) + 1 routeur + 4 sous-fonctions régime. Découpage par fonction adopté (pas par stratégie).

### 2.2. Pattern instrumenté

```
calcul_couts_mise_en_oeuvre (plate)                  — 8 à 12 étapes SYNTH_COUTS_*
├── 5 racines inputs : STRATEGIE_RETENUE, NB_FORFAITS_*, EFFECTIF_PROFIL, CONFIG_*
├── SYNTH_COUTS_NB_POSTES_RETENUS
│     ├── SYNTH_COUTS_POSTE_<NN>_<CLE>  (variable selon stratégie et config)
└── SYNTH_COUTS_TOTAL
```

**Discipline appliquée** : libellés source (« Mission cabinet — cadrage stratégique »…) intégralement en `hypotheses["libelle_integral"]`. Notes source (« Inclut audit du dossier… ») en `hypotheses["note_source"]`. Labels MODE_AUDIT factuels (« Poste NN — cadrage »).

## 3. G3e-synthese.2 — `calcul_radar_6d` + `calcul_projection_5_ans` + `calcul_decomposition_gain`

**Périmètre :** 3 fonctions analytiques, 53 étapes ajoutées.

### 3.1. Innovations

- **Radar 6D** : 4 racines (NB_AXES + NOTE_INTRA_REGIME + NB_STRATEGIES + NET_MAX_REFERENCE) + 6 axes × 4 stratégies = 24 étapes. Convention `SYNTH_RADAR_<AXE>_<STRATEGIE>` validée (lecture verticale).
- **Note doctrinale intra-régime** : `SYNTH_RADAR_NOTE_INTRA_REGIME` racine + texte intégral en `hypotheses`. Rappel doctrinal explicite (cohérent avec G3d-bis qui avait introduit `NOTE_RADAR_INTRA_REGIME` au niveau comparateur régimes).
- **Pondérations `PONDS_PROTECTION`** : dict complet en `hypotheses` de chaque étape `PROTECTION_SOCIALE_*`.
- **Hypothèse approximation 51 %** : justification intégrale en `hypotheses["justification_ratio"]` de chaque `MAITRISE_CHARGES_*` (cf. commentaire source lignes 273-277).
- **Projection 5 ans** : 4 racines + 5 années × 3 valeurs (A/RETENUE/ECART) + GAIN_5_ANS = 20 étapes.
- **Décomposition waterfall** : libellés source (« Stratégie A — Référence salaire », « + Allocation dividendes »…) préservés en `hypotheses["libelles_source"]`, label MODE_AUDIT factuel (« contribution incrémentale »).

## 4. G3e-synthese.3 — `calcul_enveloppes_patrimoniales` + `calcul_checklist_conformite`

**Périmètre :** 2 fonctions, point de vigilance sémantique majeur.

### 4.1. Lecture analytique préalable de la checklist

Avant code, **lecture complète et rapport rigoureux** sur `calcul_checklist_conformite`. Verdict : module **strictement descriptif et procédural**, **aucune** occurrence des 14 patterns prescriptifs scannés. 3 formulations stylistiquement directives identifiées (« encouragée », « à mettre en place », « Vérifier ») mais qualifiées comme wording procédural standard à protéger en `hypotheses`. Pas de bascule vers aide à la décision.

### 4.2. Pattern enveloppes patrimoniales

```
calcul_enveloppes_patrimoniales (plate)               — 14 étapes
├── 4 racines inputs : MONTANT_INITIAL, HORIZON, RENDEMENT, SITUATION
├── 1 racine HYPOTHESES_FISCALES (TX_PFU, PS_TAUX, PFU_AV_REDUIT, ABATTEMENT_AV, tmi_sortie)
├── 2 racines VALEUR_BRUTE_5ANS + PLUS_VALUE
├── SYNTH_ENV_NB_ENVELOPPES (=4)
│     ├── NET_DISPONIBLE_CTO / PEA / ASSURANCE_VIE / PER_INDIVIDUEL
└── SYNTH_ENV_CRITERE_CLASSEMENT (= "max(net_disponible)")
      └── SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE (factuel)
```

Le champ Python `meilleure` du résultat est **préservé tel quel** pour rétrocompat, mais reformulé côté trace en `SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE`. Le nom Python est tracé en `hypotheses["champ_source_python"]`.

### 4.3. Pattern checklist conformité

```
calcul_checklist_conformite (plate)                   — 3 à 12 étapes
├── SYNTH_CHECKLIST_NB_POINTS_TOTAL
│     ├── POINT_NN_ALERTE_COMP_NN     (Phase 1 — alertes Comparateur)
│     └── POINT_NN_<NOM_CHECK_V19>    (Phase 2 — checks v19)
└── SYNTH_CHECKLIST_NB_POINTS_PAR_STATUT (ventilation ✅/⚠/🔴/-)
```

- **Statut catégoriel comme valeur** : `p.statut` (chaîne `'✅'`/`'⚠'`/`'🔴'`/`'-'`) en valeur de l'étape, jamais converti en score
- **Origine de chaque point tracée** : `hypotheses["origine"] = "alerte_comparateur"` ou `"check_v19_specifique"`
- **Condition d'activation tracée** : chaque check v19 expose explicitement la condition logique
- **Discipline maximale** : labels parlent strictement de critère/statut/seuil/point de contrôle/présence, jamais d'action

### 4.4. Test 11 renforcé détecte une auto-violation pendant le dev

En G3e-synthese.3a, j'avais initialement écrit dans les notes : « Le champ Python `'meilleure'` du résultat est préservé tel quel pour rétrocompat ». Le test 11 renforcé (élargi G3e à 14 patterns) a **détecté le mot `meilleure`** et m'a forcé à reclasser cette explication en `hypotheses["note_mapping"]`. Bon réflexe défensif validé : **la discipline « tout libellé source en hypotheses » s'applique même quand le développeur croit faire un commentaire neutre**.

## 5. G3e-synthese.4 — Routeur `calcul_synthese` + 4 sous-fonctions régime

**Périmètre :** 1 routeur + 4 `_synthese_<regime>` + suite de tests. ~29 étapes méta + composition asymétrique.

### 5.1. Découverte structurante : asymétrie d'implémentation

L'instrumentation a **clarifié une asymétrie déjà présente dans le code source** :
- `_synthese_assimile` est l'implémentation pleine (« Phase A, parité v19 stricte ») et appelle les **6 fonctions transversales** instrumentées en G3e-synthese.1-3
- `_synthese_tns/liberal` sont des **implémentations allégées v1** qui ne réutilisent pas ces 6 fonctions (commentaires lignes 1331 et 1392 du source : « Coûts spécifiques TNS à raffiner en B.3 », `couts_mise_en_oeuvre=[]`, `decomposition=[]`)
- `_synthese_salarie` appelle uniquement `calcul_module_salarie` (G2a)

La trace MODE_AUDIT **rend cette asymétrie visible** :
- `_synthese_assimile` attache **6 sous-traces** (couts, radar, projection, decomposition, enveloppes, checklist)
- `_synthese_salarie` attache **1 sous-trace** (`module_salarie`)
- `_synthese_tns/liberal` attachent **0 sous-trace**

C'est **conforme à §9.2** (« on compose ce qui est réellement appelé »). Documenter cette différence est utile pour le cabinet : il sait que la synthèse TNS/Libéral est plus pauvre que l'Assimilé en v1.

### 5.2. Routeur tracé

`SYNTH_REGIME_DISPATCH` au niveau du routeur : valeur = nom de la fonction cible, hypothèses contiennent le mapping complet. Sous-trace `synthese_<regime>` attachée selon dispatch.

### 5.3. Garde-fou T4 transversal généralisé

`SYNTH_TNS_INDICATEURS_SEPARES_T4` au niveau méta de `_synthese_tns` : extension du pattern inventé en G3b (`STRAT_TNS_INDICATEURS_SEPARES`) et propagé en G3d-bis (`COMP_REG_INDICATEURS_SEPARES_T4`). Le pattern « convention transversale aux niveaux » est désormais validé sur **3 couches successives** (stratégie → comparateur régimes → synthèse).

### 5.4. Structure complète Assimilé (le graphe le plus riche)

```
calcul_synthese (Assimilé)                          — 1 étape SYNTH_REGIME_DISPATCH
└── synthese_assimile                                — 8 étapes SYNTH_ASSIM_*
      ├── couts                                      — 12 étapes SYNTH_COUTS_*
      ├── radar                                      — 28 étapes SYNTH_RADAR_*
      ├── projection                                 — 20 étapes SYNTH_PROJECTION_*
      ├── decomposition                              — 5 étapes SYNTH_DECOMPOSITION_*
      ├── enveloppes                                 — 14 étapes SYNTH_ENV_*
      └── checklist                                  — 3 à 12 étapes SYNTH_CHECKLIST_*

Total : ~93 étapes structurées, 3 niveaux de profondeur.
```

## 6. G3e-scenarios.1 + .2 — `_ir_barème_pur` + `_calcul_scenario` + `calcul_comparaison`

**Périmètre :** 3 fonctions + suite de tests. 37 étapes structurées en 3 niveaux internes.

### 6.1. Module 100% autonome avec composition interne

`scenarios.py` n'importe **aucun module instrumenté externe** (seulement les constantes de `core.profil`). Mais il a une **composition interne riche** :
- `_calcul_scenario` attache `ir_barème` (appel à `_ir_barème_pur`)
- `calcul_comparaison` attache `scenario_a` + `scenario_b` (deux appels à `_calcul_scenario`)
- Donc une comparaison complète atteint **3 niveaux d'imbrication** : `calcul_comparaison → scenario_a/b → ir_barème`

### 6.2. Champ Python `gagnant`

Le champ Python `gagnant` ("A" / "B" / "égalité") du `ResultatComparaison` est préservé tel quel pour rétrocompat. Côté trace MODE_AUDIT, il est exposé sous `SCEN_SCENARIO_NET_LE_PLUS_ELEVE` (factuel), avec `hypotheses["champ_source"] = "gagnant"` pour traçabilité du mapping.

### 6.3. 2 textes structurants

`AVERTISSEMENT_SCENARIOS` (274 chars) et `MENTION_REGIMES` (190 chars) intégralement en `hypotheses`. Test 7 dédié vérifie que les fragments-clés (« cadrage stratégique », « Comparateur 2 scénarios », « conformité renforcée », « 4 régimes ») n'apparaissent jamais en label ou notes.

### 6.4. Cas « égalité »

Le seuil 0.01 € est tracé explicitement dans `hypotheses["seuil_egalite"]` de `SCEN_SCENARIO_NET_LE_PLUS_ELEVE`. Test 8 dédié vérifie que les deux scénarios identiques produisent bien `gagnant = "égalité"` côté résultat et `valeur = "égalité"` côté trace.

## 7. Consolidation documentaire post-G3e

Documents vivants mis à jour :

| Fichier | Mise à jour |
|---|---|
| `AUDIT_MODE.md` | v1.4 → v1.5. §6.1 enrichi (10 modules instrumentés, 11 suites). §6.2 roadmap G3f marqué « prochaine étape ». §8 enrichi (11 tests gardiens, 8.10 et 8.11 ajoutés). §10.2 enrichi (familles `SYNTH_*` + `SCEN_*` documentées). §10.3 isolation étendue aux post-arbitrages. §10.4 enrichi (3 blocs sous-traces additionnels : synthèse-régime, synthèse-fonctions, scenarios — **grammaire formelle du graphe d'audit** stabilisée) |
| `ARCHITECTURE.md` §7.5 | v1.4 → v1.5. Tableau enrichi (synthese.py + scenarios.py). Principes structurants enrichis (codes post-arbitrage). Note explicite sur l'asymétrie `_synthese_tns/liberal` documentée. |
| `KNOWN_LIMITATIONS.md` | v1.4 → v1.5. 2 modules post-arbitrage ajoutés au « Couvert ». Asymétrie `_synthese_tns/liberal` explicitement assumée. G3f marqué « prochaine étape ». |
| `README_FREEZE_B2.md` §5 | 2 suites post-arbitrage ajoutées à la séquence opératoire |
| `RECAP_SESSION_MODE_AUDIT_v1_5.md` | **NOUVEAU** — récap consolidé G3e (synthese + scenarios), structurel comme v1.4 |

Récaps figés **non modifiés** (intégrité historique préservée) :
- `RECAP_SESSION_20260519.md`, `RECAP_SESSION_B3.md`
- `RECAP_SESSION_MODE_AUDIT_v1_1.md` à `v1_4.md`
- `CHANGELOG_B2_GLOBAL.md`

Le présent récap (`RECAP_SESSION_MODE_AUDIT_v1_5.md`) est une **création**.

## 8. Validation finale post-G3e complet (`post_audit_g3e_complet_*.log`)

| Validation | Résultat |
|---|---|
| Baseline numérique | ✓ Hash `8863991f27f67847` conservé |
| Architecture canonique | ✓ 17 fichiers conformes |
| Spec MODE_AUDIT | ✓ AUDIT_SPEC_VERSION = 1.1.0 |
| 504 baseline | ✓ 7/7 modules, 0 régression |
| 8 suites B.2 | ✓ Toutes vertes |
| **11 suites MODE_AUDIT** | ✓ Toutes vertes |
| `semantic_guardrails.py` | ✓ 0 violation (9 patterns) |
| `audit_final_b2_controle3.py` | ✓ 0 violation (4 patterns) |
| `test_terminologie_freeze.py` | ✓ 0 violation |
| Test 11 renforcé G3e | ✓ 0 violation sur tout le graphe v1.5 (14 patterns) |

## 9. Découvertes architecturales cumulées G3e

1. **L'instrumentation MODE_AUDIT révèle des asymétries d'implémentation invisibles autrement.** L'asymétrie `_synthese_assimile` (6 sous-traces) vs `_synthese_tns/liberal` (0 sous-trace) vs `_synthese_salarie` (1 sous-trace) est **conforme à la doctrine §9.2** mais **rend visible** au cabinet le périmètre réel d'implémentation v1. C'est un bénéfice secondaire de l'instrumentation qui n'était pas anticipé.

2. **Le test 11 renforcé fonctionne comme un garde-fou actif pendant le développement.** Pas seulement comme test final : il a détecté **une auto-violation** (mot `meilleure` glissé dans une note explicative) pendant G3e-synthese.3a, et m'a forcé à appliquer la discipline « tout libellé source en hypotheses » même aux commentaires méta-techniques.

3. **Le pattern « convention transversale aux niveaux » est désormais validé sur 3 couches successives** (`STRAT_TNS_INDICATEURS_SEPARES` G3b → `COMP_REG_INDICATEURS_SEPARES_T4` G3d-bis → `SYNTH_TNS_INDICATEURS_SEPARES_T4` G3e). Quand une convention sémantique de bas niveau doit être préservée par une couche supérieure, elle est explicitée par une étape méta dédiée. Pattern réutilisable.

4. **Module autonome ≠ pas de sous-trace.** `scenarios.py` montre qu'un module peut être « 100% autonome » externe (aucun import instrumenté) tout en ayant une composition interne riche (`scenario_a/b` qui contiennent eux-mêmes `ir_barème`). La distinction « autonome / composé » est fonctionnelle, pas binaire.

5. **La grammaire formelle des sous-traces (§10.4) se stabilise comme contrat structurant.** Après 5 itérations (G3a → G3e), la table couvre désormais 4 grandes familles : modules régime, stratégies, comparateurs, post-arbitrage. Les noms sont **stables, descriptifs, invariants à l'ordre**. C'est devenu un contrat de navigation explicite : un consommateur de trace peut naviguer par chemin symbolique (`trace.get_sous_trace("synthese_assimile").get_sous_trace("radar")`) sans dépendre de l'implémentation.

6. **La discipline non-prescriptive renforcée G3e (14 patterns) tient sans surcoût.** L'ajout de `prioritaire` et `privilégi` n'a déclenché aucune violation sur les 25 + 37 + 132 étapes scannées en G3e. La discipline d'écriture est désormais réflexe.

## 10. Garanties tenues

- ✓ Hash baseline `8863991f27f67847` conservé bout en bout (M1 → G3e)
- ✓ Aucune logique métier déplacée — instrumentation = pur side channel
- ✓ Couche `core/` neutre (`core/audit.py` ne dépend que de `dataclasses`/`typing`)
- ✓ Rétrocompat parfaite vérifiée sur 10 modules instrumentés (résultats strictement identiques avec/sans audit)
- ✓ Test 9/11 non-prescriptif automatique : aucune violation sur l'ensemble du graphe v1.5
- ✓ Espaces de codes isolés (régimes ⊥ stratégies ⊥ comparateurs ⊥ post-arbitrage)
- ✓ Modèle composable strict : aucune duplication d'étapes, aucune collision de codes
- ✓ Convention de non-agrégation T4 préservée transversalement (G3b → G3d-bis → G3e-synthese)

## 11. État du dépôt après G3e

**Fichiers livrés cette session (G3e-synthese + G3e-scenarios) :**

| Fichier | Action | Lignes ajoutées (env.) |
|---|---|---|
| `strategy/synthese.py` | Instrumenté G3e-synthese | +330 |
| `strategy/scenarios.py` | Instrumenté G3e-scenarios | +200 |
| `test_mode_audit_strategy_synthese.py` | Nouveau (G3e-synthese.4) | +470 |
| `test_mode_audit_strategy_scenarios.py` | Nouveau (G3e-scenarios.2) | +380 |
| `AUDIT_MODE.md` | v1.4 → v1.5 | ±150 |
| `ARCHITECTURE.md` §7.5 | v1.5 | ±40 |
| `KNOWN_LIMITATIONS.md` | v1.5 | ±25 |
| `README_FREEZE_B2.md` §5 | 2 suites ajoutées | +3 |
| `RECAP_SESSION_MODE_AUDIT_v1_5.md` | NOUVEAU | +280 |

**Snapshots intermédiaires conservés** dans `baseline_audit_*_pre/` :
- `baseline_audit_G3e_pre/` — avant G3e (synthese.py + scenarios.py originaux)

## 12. État global MODE_AUDIT après v1.5

| Couche | Modules instrumentés | Étapes typiques |
|---|---|---|
| Régimes (G1 + G2) | TNS, Libéral BNC/SEL, Salarié, Assimilé (tx_ir + fs) | ~75 étapes |
| Stratégies (G3a/b/c) | Assimilé, TNS, Libéral | ~430 étapes structurées |
| Comparateurs (G3d + G3d-bis) | comparateur (dispositifs) + comparateur_regimes | 36 + 412 = 448 étapes |
| **Post-arbitrage (G3e)** | synthese.py (7 calculs + 1 routeur + 4 régimes) + scenarios.py | **~155 + 37 = ~192 étapes structurées** |
| **Total v1.5** | **10 modules + spec 1.1.0 + 11 suites MODE_AUDIT (100+ catégories)** | **~1145 étapes au cumul** |

## 13. Décisions de gouvernance respectées

- Feu vert explicite obtenu avant chaque modification :
  - Cadrage G3e validé en pré-code (7 points)
  - Découpage G3e-synthese en 4 sous-passes (.1 → .4)
  - Lecture analytique de `calcul_checklist_conformite` **avant code**, avec rapport détaillé (verdict : descriptif strictement, pas de bascule aide à la décision)
  - Découpage G3e-scenarios en 2 sous-passes
  - Conventions terminologiques validées (`SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE`, `SCEN_SCENARIO_NET_LE_PLUS_ELEVE`)
- Aucune modification d'`app.py` cette session
- Aucun récap figé modifié — récap consolidé écrit en une seule passe en fin de G3e
- Audits historiques (`semantic_guardrails.py`, `audit_final_b2_controle3.py`, `test_terminologie_freeze.py`) **non modifiés** — parsimonie
- Pas de PDF audit-ready — format à stabiliser après G3 complet

## 14. Roadmap MODE_AUDIT (post-v1.5)

Conformément à la priorité acceptée :

1. **G3f — `strategy/perin.py` + `receptacles.py`** : modules transverses épargne (~400 lignes au total). **Plus simple sur le plan structurel que G3e** — pas de bascule conceptuelle attendue. Cadrage avant code prévu mais sans risque sémantique majeur identifié.
2. **G3g — Consolidation doc finale + récap global G3** : sortie de G3. Conditions d'achèvement à valider :
   - 12 modules instrumentés
   - Spec stabilisée
   - 13+ suites MODE_AUDIT vertes
   - Grammaire §10.4 stabilisée
3. **Rendu PDF audit-ready** : déclenchable après G3 complet, format à stabiliser avec retours cabinet.
4. **Export JSON / sérialisation externe**.
5. **Helpers de requête** (`find_by_regime`, `total_par_code`).
6. **Extension `_synthese_tns/liberal`** (post-G3) : composition pleine des 6 calculs auxiliaires (actuellement allégée v1).

Avant G3f, l'état est **stable** : tous les modules post-arbitrage sont instrumentés, les helpers d'épargne pourront composer leurs traces sans regénération de l'existant.
