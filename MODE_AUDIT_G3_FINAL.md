# MODE_AUDIT — Référentiel figé G3 (G3a → G3f)

**Statut :** Document de référence **figé** au 19 mai 2026
**Version :** 1.0 (premier figement, finalisation G3g)
**Périmètre :** Consolidation finale des jalons G3a à G3f du chantier MODE_AUDIT
**Spec sous-jacente :** `core/audit.py` AUDIT_SPEC_VERSION = 1.1.0 (figée)
**Document vivant complémentaire :** `AUDIT_MODE.md`

> **Convention de figement.** Ce document est figé à G3g. Toute évolution
> ultérieure du framework MODE_AUDIT (jalons G3d-ter, G4+, extensions
> `_synthese_tns/liberal`, helpers de requête, renderer PDF, export JSON)
> sera tracée dans `AUDIT_MODE.md` (vivant) et éventuellement dans un
> nouveau document figé du même format (`MODE_AUDIT_G4_FINAL.md`, etc.).
> Le contenu de ce document n'est plus modifié.

---

## §1. Synthèse exécutive

Le chantier MODE_AUDIT G3 (G3a → G3f, 19 mai 2026) instrumente le Strategy
Engine du projet `tns_dev` avec un mécanisme de traces d'audit
composables, opt-in, et sans impact sur la logique métier.

**Périmètre couvert à la finalisation G3g :**

- **12 modules** instrumentés : 4 régimes (TNS, Libéral BNC/SEL, Salarié, Assimilé), 3 stratégies (Assimilé, TNS, Libéral), 2 comparateurs (dispositifs + régimes), 2 post-arbitrage (synthèse + scénarios), 2 transverses épargne (PERIN + receptacles).
- **13 suites de tests** dédiées MODE_AUDIT (120+ catégories cumulées), toutes vertes.
- **9 namespaces** de codes isolés (`TNS_*`, `LIB_BNC_*`, `LIB_SEL_*`, `SAL_*`, `ASSIM_*`, `STRAT_*`, `COMP_*`/`COMP_REG_*`, `SYNTH_*`/`SCEN_*`, `PERIN_*`/`RECEPT_*`).
- **~1187 étapes** d'audit structurées au cumul.
- **Profondeur maximale** du graphe : 6 niveaux d'imbrication (atteinte en G3d-bis `comparateur_regimes`).
- **Spec 1.1.0** (sous-traces composables) figée, n'a pas eu besoin d'évoluer sur les 6 jalons.
- **Hash baseline** `8863991f27f67847` conservé bout-en-bout (zéro régression métier).
- **Discipline non-prescriptive renforcée** : 14 patterns regex scannés récursivement, zéro violation tolérée. Le wording métier vit en hypotheses.

**Doctrine en une phrase :** *La trace d'audit n'est pas une copie des
calculs, c'est un graphe nommé qui les explique, sans jamais les
recalculer.*

---

## §2. Catalogue des 12 modules instrumentés

| # | Module | Jalon | Namespace | Étapes typiques | Profondeur interne | Sous-traces typiques |
|---|---|---|---|---|---|---|
| 1 | `regime/tns.py` | G1 (historique) | `TNS_*` | 24 plates | 0 (feuille) | — |
| 2 | `regime/liberal.py::calcul_module_bnc()` | G1a | `LIB_BNC_*` | 16 plates | 0 (feuille) | — |
| 3 | `regime/liberal.py::calcul_module_sel()` | G1b | `LIB_SEL_*` | 8 plates | 0 (feuille) | — |
| 4 | `regime/salarie.py::calcul_module_salarie()` | G2a | `SAL_*` | 17 plates | 0 (feuille) | — |
| 5 | `regime/assimile.py::calcul_tx_ir_moyen()` + `fs_moyen_epargne()` | G2b | `ASSIM_*` | 11 + 1 plates | 0 (feuille) | — |
| 6 | `strategy/assimile.py` | G3a | `STRAT_ASSIM_*` | 7 méta + 4×13 régime | 2 | `arbitrage_assimile`, `module_assimile` |
| 7 | `strategy/tns.py` (4 stratégies + 1 arbitrage) | G3b | `STRAT_TNS_*` | 7 méta + 53 stratégies + 4×24 régime | 2 | `strategie_<CODE>`, `module_tns` |
| 8 | `strategy/liberal.py` (4 stratégies + 1 arbitrage, branches dynamiques SELARL/SELAS) | G3c | `STRAT_LIB_*` | 7 méta + ~35 stratégies + sous-traces variables | 3 (L4) | `strategie_<CODE>`, `module_bnc`, `module_sel` |
| 9 | `strategy/comparateur.py` (autonome, trace plate) | G3d | `COMP_*` | 36 plates | 0 (trace plate volontaire) | — |
| 10 | `strategy/comparateur_regimes.py` (composition 3 stratégies + module Salarié) | G3d-bis | `COMP_REG_*` | 5 méta + 4×7 lignes + sous-traces composées (~412 total) | **6 (record graphe)** | `ligne_<regime>`, `arbitrage_<regime>`, `strategie_<CODE>`, `module_<X>` |
| 11 | `strategy/synthese.py` (7 fonctions calculs + 1 routeur + 4 sous-fonctions régime, composition asymétrique) | G3e-synthese | `SYNTH_*` | ~155 étapes structurées | 2 | `couts`, `radar`, `projection`, `decomposition`, `enveloppes`, `checklist`, `module_salarie`, `synthese_<regime>` |
| 12 | `strategy/scenarios.py` (3 fonctions, autonome avec composition interne) | G3e-scenarios | `SCEN_*` | 37 étapes | 3 (interne) | `scenario_a`, `scenario_b`, `ir_barème` |
| 13 | `strategy/perin.py` (2 fonctions, composition conditionnelle) | G3f-perin | `PERIN_*` | 7 plates + 12 méta + 2 sous-traces conditionnelles | 2 | `plafond_dirigeant`, `plafond_conjoint` |
| 14 | `strategy/receptacles.py` (5 fonctions, composition interne 3 niveaux) | G3f-receptacles | `RECEPT_*` | ~16 codes uniques | 3 (interne) | `regime_effectif`, `accessibilite` |

> **Note de lecture.** Le tableau liste 14 lignes pour 12 modules : les modules 5 et 7-8 couvrent plusieurs fonctions instrumentées dans le même fichier source.

**Total cumulé instrumenté :** ~1187 étapes structurées, 9 namespaces
isolés, profondeur maximale 6 niveaux.

**Modules NON instrumentés en G3 (par choix) :**
- `core/profil.py` : pas de logique métier instrumentable (data layer).
- `core/projection.py`, `core/ir_foyer.py` : utilitaires purs, instrumentés indirectement via les régimes/stratégies qui les consomment.
- `ui/*.py` : couche de présentation, pas de calcul.
- `app.py` : couche d'orchestration Streamlit, pas de calcul.

---

## §3. Catalogue des 13 suites de tests MODE_AUDIT

| # | Suite | Jalon | Catégories | Étapes scannées | Spécificités |
|---|---|---|---|---|---|
| 1 | `test_mode_audit_tns.py` | G1 | 7 | ~24 | Trace plate régime, premier jalon historique |
| 2 | `test_mode_audit_liberal.py` | G1a + G1b | 14 | ~24 (BNC + SEL) | 2 modules dans 1 suite |
| 3 | `test_mode_audit_salarie.py` | G2a | 8 | ~17 | Promotion constantes G2a vérifiée |
| 4 | `test_mode_audit_assimile.py` | G2b | 11 | ~12 | 2 helpers dans 1 suite, suppression duplication `PLAFOND_ABAT_10PCT_REF` |
| 5 | `test_mode_audit_strategy_assimile.py` | G3a | 12 | ~60 | **Premier test 9 non-prescriptif** (12 patterns) |
| 6 | `test_mode_audit_strategy_tns.py` | G3b | 11 | ~150 | Première imbrication 2 niveaux validée |
| 7 | `test_mode_audit_strategy_liberal.py` | G3c | 12 | ~120 | Imbrication 3 niveaux, branches dynamiques SELARL/SELAS |
| 8 | `test_mode_audit_strategy_comparateur.py` | G3d | 14 | ~36 | Module autonome, trace plate top 3 mécanique |
| 9 | `test_mode_audit_strategy_comparateur_regimes.py` | G3d-bis | 14 | ~412 | **Imbrication 6 niveaux** (record), convention non-agrégation T4 |
| 10 | `test_mode_audit_strategy_synthese.py` | G3e-synthese | 14 | ~155 | **Test 9 renforcé à 14 patterns**, asymétrie d'implémentation tracée |
| 11 | `test_mode_audit_strategy_scenarios.py` | G3e-scenarios | 12 | ~37 | Module autonome avec composition interne, cas égalité testé |
| 12 | `test_mode_audit_strategy_perin.py` | G3f-perin | 13 | 194 | Composition conditionnelle (4 scénarios distincts), cas limites plancher/plafond/excédent |
| 13 | `test_mode_audit_strategy_receptacles.py` | G3f-receptacles | 12 | 46 | Composition 3 niveaux internes, trace plate volontaire, branche short-circuit |

**Discipline cumulée :** 120+ catégories, exécution séquentielle ~30 s,
intégrées à la séquence opératoire (`README_FREEZE_B2.md` §7).

**Couverture transversale assurée par chaque suite :**

1. Rétrocompat parfaite (résultats strictement identiques avec/sans audit).
2. Structure (codes attendus, profondeur, sous-traces).
3. Cohérence valeurs trace ↔ valeurs retournées par le calcul.
4. Test non-prescriptif (12 patterns G3a → 14 patterns à partir de G3e).
5. Isolation namespace (vérification absence d'intrusion préfixes étrangers).
6. Résolution doctrine_refs (constantes citées existent dans `core/profil.py`).

---

## §4. Conventions de namespaces

### §4.1. Inventaire des 9 familles isolées

| Famille | Préfixes | Modules sources |
|---|---|---|
| Régimes | `TNS_*`, `LIB_BNC_*`, `LIB_SEL_*`, `SAL_*`, `ASSIM_*` | `regime/*.py` |
| Stratégies | `STRAT_ASSIM_*`, `STRAT_TNS_*`, `STRAT_LIB_*` | `strategy/assimile.py`, `strategy/tns.py`, `strategy/liberal.py` |
| Comparateurs | `COMP_*`, `COMP_REG_*` | `strategy/comparateur.py`, `strategy/comparateur_regimes.py` |
| Post-arbitrage | `SYNTH_*`, `SCEN_*` | `strategy/synthese.py`, `strategy/scenarios.py` |
| Transverses épargne | `PERIN_*`, `RECEPT_*` | `strategy/perin.py`, `strategy/receptacles.py` |

### §4.2. Règle d'isolation

**Aucune famille ne se croise avec une autre.** Chaque suite de tests
vérifie explicitement l'absence de préfixe étranger dans son périmètre
(test 12 type). Cette règle est vérifiée structurellement par scan
récursif sur l'ensemble du graphe.

### §4.3. Anti-collision avec les noms de stratégies

Les préfixes stratégie (`STRAT_TNS_*`) ne se confondent pas avec les
préfixes régime (`TNS_*`) : la prefix-match « `TNS_` » ne match jamais
`STRAT_TNS_`. Les suites de tests vérifient cette isolation
explicitement.

### §4.4. Sous-traces et namespaces

Dans une trace stratégie, comparateur, post-arbitrage ou transverse,
**aucun code de préfixe régime n'apparaît à plat**. Les codes régime
vivent uniquement dans les sous-traces nommées (cf. §5). Cette
discipline garantit que la lecture top-down d'une trace reste
contextuellement cohérente.

### §4.5. Convention de nommage des codes

```
<NAMESPACE>_<DOMAINE>[_<ETAPE>]
```

Exemples :
- `TNS_REM_ASSIETTE_RSI` (régime TNS, domaine rémunération, étape assiette RSI)
- `STRAT_TNS_STRAT_RESULTAT_CAS_3` (stratégie TNS, stratégie 3, domaine résultat)
- `COMP_REG_NET_TOTAL_RETENU` (comparateur régimes, domaine arbitrage)
- `SYNTH_COUTS_TOTAL_5_ANS` (synthèse, sous-domaine coûts)
- `PERIN_PLAFOND_INDIVIDUEL` (PERIN, domaine plafond)
- `RECEPT_RECEPTACLE_PEE` (receptacles, ligne réceptacle PEE)

Conventions stables et descriptives. Une fois publié dans une suite de
tests, un code ne change plus de nom (continuité contractuelle).

---

## §5. Modèle de graphe d'audit et conventions de composition

### §5.1. Modèle mental

Une trace d'audit MODE_AUDIT est un **graphe arborescent nommé**, pas
une liste plate. Chaque nœud du graphe est une `TraceAudit` qui contient :

1. Des **étapes plates** (`EtapeAudit`) propres au niveau, avec codes
   préfixés du namespace de ce niveau.
2. Des **sous-traces nommées** attachées par `attacher_sous_trace(nom, sous_trace)`.

Le nom de la sous-trace est **stable et descriptif**, indépendant de
l'ordre de calcul, et permet la **navigation par chemin symbolique**
(`trace.get_sous_trace("arbitrage_tns").get_sous_trace("strategie_3")`).

### §5.2. Grammaire formelle des noms de sous-traces (figée G3g)

| Nom d'attachement | Sémantique | Modules utilisateurs |
|---|---|---|
| `module_<X>` | Appel à un module de calcul de bas niveau (`module_tns`, `module_bnc`, `module_sel`, `module_salarie`, `module_assimile`) | Stratégies, post-arbitrage, comparateurs |
| `strategie_<CODE>` | Appel à une stratégie individuelle dans un arbitrage (`strategie_1`, `strategie_2`, ..., `strategie_5`) | `strategy/{assimile,tns,liberal}.py` |
| `arbitrage_<regime>` | Appel à un arbitrage complet (`arbitrage_assimile`, `arbitrage_tns`, `arbitrage_liberal`) | `strategy/comparateur_regimes.py` |
| `ligne_<regime>` | Une ligne du tableau de comparaison régimes (`ligne_assimile`, `ligne_tns`, `ligne_liberal`, `ligne_salarie`) | `strategy/comparateur_regimes.py` |
| `synthese_<regime>` | Routeur vers la sous-fonction de synthèse régime (`synthese_assimile`, `synthese_tns`, `synthese_liberal`, `synthese_salarie`) | `strategy/synthese.py::calcul_synthese` |
| `couts`, `radar`, `projection`, `decomposition`, `enveloppes`, `checklist` | 6 calculs auxiliaires de la synthèse Assimilé | `strategy/synthese.py::_synthese_assimile` |
| `scenario_a`, `scenario_b` | Les 2 scénarios comparés | `strategy/scenarios.py::calcul_comparaison` |
| `ir_barème` | Calcul IR par barème pur (composition interne) | `strategy/scenarios.py::_calcul_scenario` |
| `tx_ir_moy` | Appel à `calcul_tx_ir_moyen` (composition interne) | `strategy/synthese.py` |
| `plafond_dirigeant` | Calcul plafond PERIN dirigeant (toujours attaché) | `strategy/perin.py::calcul_perin_mutualise` |
| `plafond_conjoint` | Calcul plafond PERIN conjoint (attaché si mutualisation effective) | `strategy/perin.py::calcul_perin_mutualise` |
| `regime_effectif` | Résolution du régime effectif (règle SELARL/SELAS) | `strategy/receptacles.py::est_accessible` |
| `accessibilite` | Évaluation d'accessibilité d'un réceptacle | `strategy/receptacles.py::motif_inaccessibilite` |

### §5.3. Patterns de composition validés (4 patterns reconnus)

**Pattern A — Composition simple stratégie → régime (G3a, G3b)**

```
arbitrage_tns                                — niveau 1 (top)
├── strategie_1                               — niveau 2 (sous-trace)
│   └── module_tns                            — niveau 3 (feuille régime)
├── strategie_2
│   └── module_tns
├── ...
```

**Pattern B — Composition dynamique par branche (G3c)**

`strategy/liberal.py::strategie_4_distribution_dividendes_sel` attache
soit `module_bnc` soit `module_sel` selon la forme juridique du profil,
mais pas les deux. La sous-trace est dynamique (branche unique tracée).

**Pattern C — Composition asymétrique (G3e-synthese)**

`strategy/synthese.py::_synthese_assimile` attache 6 sous-traces
(`couts`, `radar`, `projection`, `decomposition`, `enveloppes`,
`checklist`). `_synthese_salarie` en attache 1 (`module_salarie`).
`_synthese_tns` et `_synthese_liberal` en attachent 0 (implémentation
allégée v1). **L'asymétrie est rendue visible par la trace elle-même.**

**Pattern D — Composition conditionnelle (G3f-perin)**

`strategy/perin.py::calcul_perin_mutualise` attache `plafond_dirigeant`
toujours, et `plafond_conjoint` **si et seulement si** la mutualisation
est effective (situation == "Marié / pacsé" AND conjoint_declare AND
revenu_pro_conjoint > 0). La condition logique est explicitement tracée
dans `hypotheses["condition"]`.

### §5.4. Pattern « trace plate volontaire »

Quand la composition par sous-traces ajouterait du bruit structurel
sans valeur d'audit ajoutée, on choisit consciemment une **trace plate**.

Exemples :
- `strategy/comparateur.py` (G3d) : 36 étapes plates pour le top 3 des
  dispositifs. Composer aurait noyé le lecteur dans des sous-traces
  quasi-identiques.
- `strategy/receptacles.py::liste_receptacles_par_regime` (G3f-receptacles) :
  6 réceptacles itérés en codes plats (`RECEPT_RECEPTACLE_<NOM>`)
  plutôt que 12 sous-traces (`est_accessible` + `motif_inaccessibilite`
  × 6).

**Critère de décision :**

| Situation | Choix |
|---|---|
| Les sous-traces apportent une valeur d'audit (calculs distincts, navigation utile) | Sous-traces |
| Les sous-traces seraient quasi-identiques en structure (itération sur N éléments) | Trace plate |
| Composition naturelle (un calcul appelle un autre calcul) | Sous-traces |
| Sortie aplatie (top N, liste, énumération) | Trace plate |

La décision est **documentée dans le code** en hypotheses
(`"convention_trace": "Trace plate volontaire — ..."`) et **vérifiée
dans les tests** (assertion explicite sur l'absence de sous-traces).

### §5.5. Profondeurs typiques par couche

| Couche | Profondeur typique | Profondeur maximale atteinte |
|---|---|---|
| Régimes | 1 (feuille) | 1 |
| Stratégies | 2-3 | 3 (G3c, branche L4) |
| Comparateur dispositifs (G3d) | 1 (plate) | 1 |
| Comparateur régimes (G3d-bis) | 4-5 | **6** (record graphe) |
| Synthèse (G3e-synthese) | 2 | 2 |
| Scénarios (G3e-scenarios) | 2-3 (interne) | 3 |
| PERIN (G3f-perin) | 2 | 2 |
| Receptacles (G3f-receptacles) | 2-3 (interne) | 3 |

### §5.6. Garde-fous structurels (4 vérifications)

Toute opération `attacher_sous_trace(nom, sous_trace)` lève une
exception en cas de :

1. **Doublon de nom** : un même nom ne peut pas être attaché deux fois
   au même niveau.
2. **Réattachement** : une sous-trace déjà attachée ailleurs ne peut
   pas être réattachée (pas de partage de référence).
3. **Cycle direct** : on ne peut pas attacher `t` à `t` lui-même.
4. **Type incorrect** : `sous_trace` doit être une instance `TraceAudit`.

> **Limite assumée :** les cycles indirects (A → B → A) ne sont pas
> détectés en spec 1.1.0. Ils sont évités par convention (graphe
> strictement arborescent, jamais réutilisé).

---

## §6. Doctrine non-prescriptive

### §6.1. Principe

**La trace d'audit décrit ce qui a été calculé, jamais ce qu'il faudrait
faire.** Aucun jugement de valeur dans les labels et les notes. Le
wording métier qui pourrait être interprété comme prescriptif vit
exclusivement en `hypotheses` (champ dict non scanné par les tests
non-prescriptifs).

### §6.2. 14 patterns scannés (renforcés G3e)

| # | Pattern regex | Famille |
|---|---|---|
| 1 | `\boptim\w*\b` | optimal/optimisation |
| 2 | `\bmeilleur(?:e\|s\|es)?\b` | meilleur/meilleurs |
| 3 | `\bgagnant(?:e\|s\|es)?\b` | gagnant |
| 4 | `\bperdant(?:e\|s\|es)?\b` | perdant |
| 5 | `\bavantageu(?:x\|se\|ses)\b` | avantageux |
| 6 | `\brecommand(?:é\|ée\|és\|ées\|er\|ation\|ations)\b` | recommandation |
| 7 | `\bpréconis(?:é\|ée\|er\|ation)\b` | préconisation |
| 8 | `\bconseill(?:é\|ée\|er)\b` | conseil |
| 9 | `\bidéal(?:e\|s\|es)?\b` | idéal |
| 10 | `\bparfait(?:e\|s\|es)?\b` | parfait |
| 11 | `\bsupérieur(?:e\|s\|es)?\b` | supérieur |
| 12 | `\binférieur(?:e\|s\|es)?\b` | inférieur |
| 13 | `\bprioritaire(?:s)?\b` | prioritaire (ajouté G3e) |
| 14 | `\bprivilégi\w*\b` | privilégier (ajouté G3e) |

**Champ scannés :** `label` et `notes` de chaque `EtapeAudit`,
récursivement sur tout le graphe de sous-traces. **Champ exclu :**
`hypotheses` (dict, contient le wording métier).

### §6.3. Terminologie factuelle

Quand un code nécessitait à l'origine un terme comme « meilleur » ou
« gagnant », il a été renommé en formulation factuelle :

| Code original (proscrit) | Code factuel (adopté) |
|---|---|
| `SYNTH_ENV_MEILLEURE_ENVELOPPE` | `SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE` |
| `SCEN_GAGNANT` (envisagé) | `SCEN_SCENARIO_NET_LE_PLUS_ELEVE` |
| `COMP_REG_MEILLEUR_REGIME` (envisagé) | `COMP_REG_NET_TOTAL_RETENU` |

Le champ Python sous-jacent (`meilleure`, `gagnant`) est préservé pour
la rétrocompat des consommateurs métier ; il est exposé dans
`hypotheses["champ_source"]` ou similaire.

### §6.4. Wording métier en hypotheses

Les textes structurants destinés au cabinet (alertes, mentions
réglementaires, disclaimers) sont préservés **intégralement** dans le
champ `hypotheses` de l'étape concernée, jamais dans `label` ou
`notes`. Vérification systématique dans les tests : fragments-clés
explicitement testés absents de `label`/`notes`.

Exemples :
- `RECEPT_MENTION_LONGUEUR.hypotheses["MADELIN_PER_TNS_MENTION"]` (184 chars, mention Madelin/PER TNS intégrale)
- `SCEN_*.hypotheses["AVERTISSEMENT_SCENARIOS"]`
- `SCEN_*.hypotheses["MENTION_REGIMES"]`

### §6.5. Citation pédagogique « : INTERDIT »

Les garde-fous sémantiques (`semantic_guardrails.py`,
`test_terminologie_freeze.py`) acceptent les occurrences de termes
proscrits **uniquement** dans les contextes suivants :

1. **Docstrings de garde-fou** (citation pédagogique : `# Le terme "meilleur" : INTERDIT`).
2. **Disclaimers négatifs** (UI : `« nous ne désignons pas de meilleure stratégie »`).
3. **Contextes techniques neutres** (champs Python internes, noms de variables historiques préservés pour rétrocompat).

Les tests ont une whitelist de ces contextes ; toute occurrence hors
whitelist déclenche une violation.

---

## §7. Patterns architecturaux validés

### §7.1. Composition spec 1.1.0 (graphe, pas copies)

**Une stratégie n'agrège jamais** les calculs d'un module qu'elle
appelle : elle les **compose** via `attacher_sous_trace`. Les valeurs
restent dans la sous-trace, accessibles par navigation symbolique
(`trace.get_sous_trace(...)`). **Aucune réémission, aucune
duplication.** Vérifié structurellement par les tests d'isolation
namespace.

### §7.2. Sous-traces immutables après attachement (invariant conceptuel)

Une fois une sous-trace attachée par `attacher_sous_trace(nom,
sous_trace)`, son contenu n'est plus modifié par le code consommateur.
Cet invariant n'est pas (encore) une règle technique dure du framework,
mais il est respecté par tous les patterns G3a → G3f et constitue une
base nécessaire pour :

- Les **futurs renderers** (rendu déterministe à partir d'un graphe figé).
- Le **renderer PDF audit-ready** (génération séquentielle sans risque
  d'altération en cours de rendu).
- Les **exports JSON** ou autres sérialisations (snapshot stable).
- Une éventuelle **API externe** (cabinet, intégration tierce).

En pratique : on construit une sous-trace localement, on la peuple
entièrement, puis on l'attache une seule fois. On ne ré-accède pas à
une sous-trace attachée pour y ajouter des étapes ou attacher une
sous-sous-trace après coup.

> **Note de figement.** Cet invariant devient probablement une règle
> technique dure dans une future spec 1.2.0 (à instruire séparément).
> En 1.1.0, la convention est documentée mais pas vérifiée par le
> framework lui-même.

### §7.3. Composition conditionnelle

Une sous-trace est attachée **si et seulement si** le calcul correspondant
est effectivement exécuté. Inventé en G3c (branches L3/L4 dynamiques),
généralisé en G3e-synthese (asymétrie d'implémentation), confirmé en
G3f-perin (`plafond_conjoint` selon condition logique).

**Implémentation type :**

```python
if mutualisation_possible:
    if audit is not None:
        st_conj = TraceAudit(regime="Plafond conjoint")
        plaf_conj = calcul_plafond_perin("Conjoint", revenu, audit=st_conj)
        audit.attacher_sous_trace("plafond_conjoint", st_conj)
    else:
        plaf_conj = calcul_plafond_perin("Conjoint", revenu)
```

La condition d'attachement est **tracée explicitement** dans une étape
plate dédiée (`PERIN_MUTUALISATION_POSSIBLE` avec
`hypotheses["condition"]` documentant la formule logique).

### §7.4. Trace plate volontaire

Cf. §5.4. Arbitrage conscient documenté dans le code et vérifié par les
tests.

### §7.5. Branche short-circuit

Une fonction qui peut court-circuiter une partie de son calcul
(typiquement pour un cas de sécurité ou un fallback) **ne compose pas**
les sous-traces qui auraient été produites par la branche normale.

Exemple : `strategy/receptacles.py::est_accessible` retourne True sans
composer `regime_effectif` si le réceptacle n'est pas dans la matrice
(sécurité — ne pas bloquer un futur réceptacle non documenté).

La branche est tracée en `hypotheses["branche"]` (par exemple
`"receptacle_inconnu_fallback"`), et les tests vérifient explicitement
l'absence de la sous-trace dans ce cas.

### §7.6. Asymétrie d'implémentation rendue visible

Quand le code source contient une asymétrie (un régime traité plus
finement qu'un autre, une implémentation allégée v1), la trace
**reflète fidèlement cette asymétrie**. Elle ne masque pas, elle ne
compense pas, elle documente.

Exemple G3e-synthese :
- `_synthese_assimile` attache 6 sous-traces (couts, radar, projection,
  decomposition, enveloppes, checklist).
- `_synthese_salarie` attache 1 sous-trace (module_salarie).
- `_synthese_tns` et `_synthese_liberal` attachent 0 sous-trace
  (implémentation allégée v1).

L'asymétrie d'implémentation, qui n'était pas documentée auparavant, est
maintenant visible dans le graphe et signalée dans
`KNOWN_LIMITATIONS.md`.

### §7.7. Branche tracée en hypotheses

Quand une fonction présente plusieurs branches de calcul, **chaque
branche emprunte une formule différente** mais retourne un résultat
homogène. La branche empruntée est tracée explicitement dans
`hypotheses["branche"]` (ou `["branche_appliquee"]` selon le module).

Exemples :
- `PERIN_PLAFOND_TOTAL_RETENU.hypotheses["branche"]` = `"sans_mutualisation"` ou `"avec_mutualisation"`
- `RECEPT_REGIME_EFFECTIF.hypotheses["branche_appliquee"]` = `"selarl_vers_tns"`, `"selas_vers_assimile"`, `"liberal_bnc_pur"`, etc.
- `STRAT_LIB_S4_DIV_SEL.hypotheses["forme_sel_appliquee"]` = `"SELARL"` ou `"SELAS"`

Permet la lecture déterministe : à valeurs d'entrée identiques, la
trace est identique.

### §7.8. Condition explicite en hypotheses

Toute condition logique non-triviale est documentée en hypotheses avec
la formule complète **et** chaque sous-condition évaluée séparément :

```python
audit.add("PERIN_MUTUALISATION_POSSIBLE",
    "Condition de mutualisation conjoint évaluée",
    1.0 if mutualisation_possible else 0.0,
    hypotheses={
        "valeur_bool": mutualisation_possible,
        "condition": "situation == 'Marié / pacsé' AND "
                     "conjoint_declare AND revenu_pro_conjoint > 0",
        "situation_evaluee": situation == "Marié / pacsé",
        "conjoint_declare_evalue": conjoint_declare,
        "revenu_conjoint_evalue": revenu_pro_conjoint > 0,
    })
```

Le lecteur peut reconstituer **pourquoi** la condition a été satisfaite
ou non, sans avoir à relire le code source.

### §7.9. Doctrine_refs résolus

Toute constante doctrinale citée dans `EtapeAudit.doctrine_refs` est
**résolue** par `core/audit.py::resoudre_doctrine_ref` vers sa valeur
réelle dans `core/profil.py`. Vérification systématique dans les tests
(test 13 type). Aucune référence orpheline tolérée.

Constantes citées : `PASS_2026`, `TX_CSG_DEDUCTIBLE`,
`TX_CSG_NON_DEDUCTIBLE`, `PLAFOND_ABAT_10PCT_SAL`, `TX_ABAT_10PCT_SAL`,
plus les constantes locales aux régimes (citées sans résolution).

### §7.10. Non-agrégation transversale T4 (convention G3b → G3d-bis → G3e-synthese)

Quand un consommateur affiche les indicateurs d'un calcul composé, il
les **présente séparément**, sans en faire la somme algébrique. Cette
convention a été retenue en G3b (consommateurs de stratégies TNS), en
G3d-bis (consommateurs de comparateur_regimes) et en G3e-synthese
(consommateurs de synthese). Marqueur dans le code :
`INDICATEURS_SEPARES_T4`.

---

## §8. Dettes connues et reportées

### §8.1. Dette G3d-ter — Rétro-instrumentation `comparateur.py` → `receptacles.py`

**Constat.** `strategy/comparateur.py` (G3d, figé) consomme silencieusement
`est_accessible` et `motif_inaccessibilite` depuis `strategy/receptacles.py`
(lignes 232-234 du source comparateur). Ces appels **ne propagent pas
l'audit**, donc la composition n'apparaît pas en sous-trace
`receptacles` au niveau du comparateur.

**Conséquence.** Une trace de comparateur (G3d) ne contient pas la
décomposition des décisions d'accessibilité prises sur les 3-4
réceptacles concernés. La traçabilité est partielle sur ce maillon.

**Mitigation.**
- Le module `receptacles.py` est **entièrement instrumenté en standalone**
  (G3f-receptacles) et utilisable en appel isolé avec son propre `audit`.
- L'impact sur la lisibilité d'une trace de comparateur est faible
  (3-4 appels max selon configuration).
- Le module `comparateur.py` reste un livrable G3d **figé** ; toute
  modification est une intervention rétroactive sur un graphe stabilisé.

**Décision.** Reporté à un jalon dédié **G3d-ter** si besoin réel se
manifeste (retours cabinet, intégration PDF avancée). Faible priorité.

### §8.2. `_synthese_tns` et `_synthese_liberal` allégés (v1)

**Constat.** `strategy/synthese.py::_synthese_tns` et `_synthese_liberal`
sont des **implémentations allégées v1** : elles ne réutilisent pas les
6 calculs auxiliaires de la synthèse Assimilé (`couts`, `radar`,
`projection`, `decomposition`, `enveloppes`, `checklist`). La trace
MODE_AUDIT documente cette asymétrie (0 sous-trace côté TNS/Libéral vs
6 côté Assimilé).

**Décision.** Extension pleine reportée **post-G3**. Le sujet est
documenté dans `KNOWN_LIMITATIONS.md` et dans la table de §7.6
(asymétrie d'implémentation rendue visible).

### §8.3. Détection des cycles indirects (spec 1.1.0)

**Constat.** Les garde-fous spec 1.1.0 détectent les cycles directs
(`t.attacher_sous_trace("x", t)` → exception), mais pas les cycles
indirects (`A → B → A`).

**Mitigation.** En pratique, la convention de **graphe strictement
arborescent** (cf. §7.2 invariant d'immutabilité) rend les cycles
indirects impossibles : chaque sous-trace est créée localement,
peuplée, puis attachée une seule fois. Aucun cas observé sur 12
modules instrumentés.

**Décision.** Détection des cycles indirects à instruire en spec 1.2.0
(future) si besoin.

### §8.4. Sérialisation et exports

**Reporté :**
- Export JSON / sérialisation externe (pour intégration cabinet).
- Helpers de requête (`find_by_regime`, `total_par_code`).
- Renderer alternatifs au renderer console actuel (HTML, PDF
  audit-ready, etc.).

Le renderer console (`ui/audit_render.py`) couvre l'usage debug et
revue technique en interne. Le **renderer PDF audit-ready** est le
prochain chantier produit (cf. §9 pour le cadrage de lecture).

---

## §9. Guide de lecture synthétique pour cabinet

### §9.1. Modèle mental en 3 phrases

1. Une trace MODE_AUDIT est **un arbre nommé** dont chaque nœud est un
   calcul, et chaque feuille est une étape élémentaire.
2. La **racine** correspond au calcul de plus haut niveau invoqué
   (typiquement un arbitrage, une synthèse ou une comparaison).
3. Les **sous-arbres** correspondent aux calculs internes composés, et
   se naviguent par leur nom symbolique.

### §9.2. Comment naviguer une trace

Trois modes de navigation, du plus simple au plus structuré :

**Mode 1 — Lecture séquentielle (renderer console actuel).** Affiche
toutes les étapes dans l'ordre, avec indentation reflétant la
profondeur. Convient au debug et à la revue technique. C'est le mode
fourni par défaut par `ui/audit_render.py`.

**Mode 2 — Lecture par chemin symbolique.** Le consommateur navigue
explicitement vers la sous-trace qui l'intéresse :

```python
arbitrage = trace.get_sous_trace("arbitrage_tns")
strategie_3 = arbitrage.get_sous_trace("strategie_3")
module_tns = strategie_3.get_sous_trace("module_tns")
# module_tns contient les étapes plates TNS_*
```

Convient aux usages programmatiques (extraction de valeurs spécifiques,
diff entre traces, etc.).

**Mode 3 — Lecture par filtre.** Récupération de toutes les étapes d'un
namespace, ou de toutes les sous-traces d'un nom donné. **Pas encore
disponible en spec 1.1.0** (helpers `find_by_regime`, `total_par_code`
en backlog §8.4).

### §9.3. Comment interpréter une sous-trace

**Règle de lecture :** une sous-trace attachée correspond à un **appel
effectif** au calcul correspondant. Son absence signifie que le calcul
n'a pas été exécuté (typiquement composition conditionnelle, branche
short-circuit, ou implémentation allégée).

**Exemples d'interprétation :**

- Sur une trace `calcul_perin_mutualise`, l'absence de `plafond_conjoint`
  signifie que la mutualisation n'était **pas applicable** au moment du
  calcul (vérifier l'étape `PERIN_MUTUALISATION_POSSIBLE` pour le
  motif).
- Sur une trace `_synthese_tns`, l'absence des 6 sous-traces auxiliaires
  signifie que l'**implémentation est allégée v1** (cf. §8.2).
- Sur une trace `est_accessible`, l'absence de `regime_effectif`
  signifie que le **réceptacle est inconnu** (branche short-circuit,
  cf. §7.5).

### §9.4. Mini-exemple visuel — Graphe réel de comparateur régimes (3 niveaux)

Trace top-niveau pour un profil SARL gérance majoritaire, comparaison
des 4 régimes :

```
comparateur_regimes  (TraceAudit racine, namespace COMP_REG_*)
│
├─ étapes plates (5 étapes méta)
│   ├─ COMP_REG_PROFIL_RESUME
│   ├─ COMP_REG_NB_REGIMES_COMPARES
│   ├─ COMP_REG_DOCTRINE_VERSION
│   ├─ COMP_REG_NET_TOTAL_RETENU
│   └─ COMP_REG_REGIME_NET_LE_PLUS_ELEVE
│
├─ ligne_assimile  (sous-trace régime Assimilé)
│   ├─ étapes plates (7 étapes ligne)
│   │   ├─ COMP_REG_LIGNE_ASSIM_RUNNING_GAIN
│   │   ├─ COMP_REG_LIGNE_ASSIM_NET_DIRIGEANT
│   │   └─ ...
│   └─ arbitrage_assimile  (composition stratégies Assimilé)
│       ├─ étapes méta arbitrage (7 étapes)
│       └─ module_assimile  (sous-trace régime)
│           └─ étapes plates ASSIM_* (12 étapes)
│
├─ ligne_tns  (sous-trace régime TNS)
│   ├─ étapes plates (7 étapes ligne)
│   └─ arbitrage_tns  (composition 5 stratégies TNS)
│       ├─ étapes méta arbitrage
│       ├─ strategie_1
│       │   └─ module_tns  (étapes plates TNS_* — 24 étapes)
│       ├─ strategie_2
│       │   └─ module_tns
│       ├─ strategie_3  (stratégie retenue)
│       │   └─ module_tns
│       ├─ strategie_4
│       │   └─ module_tns
│       └─ strategie_5
│           └─ module_tns
│
├─ ligne_liberal  (sous-trace régime Libéral, branche dynamique BNC/SEL)
│   └─ arbitrage_liberal
│       └─ strategie_4 (branche SELARL)
│           └─ module_sel  (étapes plates LIB_SEL_*)
│
└─ ligne_salarie  (sous-trace régime Salarié, feuille directe)
    └─ module_salarie  (étapes plates SAL_*)
```

**Lecture suggérée pour le cabinet :**

1. Lire les **5 étapes méta** au niveau racine pour comprendre la
   décision globale (régime retenu, profil résumé, doctrine appliquée).
2. Ouvrir la **ligne du régime retenu** (`ligne_tns` dans cet exemple)
   pour voir comment le net dirigeant a été calculé.
3. Ouvrir l'**arbitrage** correspondant pour voir quelles stratégies
   ont été comparées et laquelle a été retenue (cf. champ Python
   `strategie_retenue`).
4. Ouvrir la **stratégie retenue** (`strategie_3`) pour voir les
   paramètres exacts (taux de marge, plafonds appliqués, dispositifs
   activés).
5. Ouvrir le **module régime** (`module_tns`) pour voir le détail des
   24 étapes de calcul TNS (CSG, RSI, IR, etc.).

### §9.5. Conventions de présentation envisageables (pour PDF audit-ready)

À titre indicatif, en préparation du jalon « renderer PDF
audit-ready » :

| Élément | Présentation suggérée |
|---|---|
| Racine | Bloc titre + 5-10 étapes méta en tableau |
| Sous-traces | Sections ou sous-sections, navigables par signets/liens |
| Étapes plates | Tableau code / label / valeur / unité (4 colonnes minimum) |
| Hypotheses | Bloc dépliable (« voir les hypothèses ») ou note de bas de page |
| Doctrine_refs | Lien hypertexte vers une annexe de constantes doctrinales |
| Profondeur > 3 | Pagination dédiée par sous-trace, sommaire en tête |
| Wording métier intégral (mention Madelin, avertissements scénarios) | Encadré dédié reproduit verbatim |

> **À cadrer en jalon dédié.** Le format final dépend des retours
> cabinet et n'est pas figé ici. Cette section est indicative.

### §9.6. Garanties données au cabinet

À doctrine et hypothèses identiques, **deux exécutions produisent la
même trace** (déterminisme structurel). Cette propriété est vérifiée
par les tests de rétrocompat de chaque suite MODE_AUDIT (assertion
`r_sans == r_avec`).

À donnée d'entrée modifiée, **la trace reflète immédiatement le
changement** : aucune mémorisation, aucun cache, aucun état latent. La
trace est régénérée à chaque appel à partir des paramètres d'entrée.

Toute valeur affichée dans la trace **peut être recroisée** avec la
valeur retournée par le calcul Python sous-jacent (assertion type des
tests 10 « cohérence valeurs trace vs résultat »).

---

## §10. Bibliographie interne

### §10.1. Documents vivants

- **`AUDIT_MODE.md`** : spec vivante du framework MODE_AUDIT (spec
  1.1.0, conventions, exemples, tests gardiens). Évolue avec les
  jalons futurs.
- **`ARCHITECTURE.md` §7.5** : intégration du framework dans
  l'architecture canonique du projet (`core ← regime ← strategy ← ui ←
  app`).
- **`KNOWN_LIMITATIONS.md`** : dettes assumées, limites connues,
  périmètre v1.6 explicite.
- **`README_FREEZE_B2.md` §7** : séquence opératoire de validation
  (504 baseline + 6 suites B.2 + 13 suites MODE_AUDIT + 3 audits
  sémantiques).
- **`TERMINOLOGY.md`** : glossaire des termes proscrits et termes
  factuels (référence pour la doctrine non-prescriptive §6).
- **`SEMANTIC_GUARDRAILS.md`** : description des garde-fous sémantiques
  (`semantic_guardrails.py`, `audit_final_b2_controle3.py`,
  `test_terminologie_freeze.py`).

### §10.2. Récaps figés (jamais modifiés)

- `RECAP_SESSION_20260519.md` (refactoring B.2 historique)
- `RECAP_SESSION_B3.md` (architecture canonique B.3)
- `CHANGELOG_B2_GLOBAL.md` (changelog cumulé B.2)
- `RECAP_SESSION_MODE_AUDIT_v1_1.md` (G1a — Libéral BNC)
- `RECAP_SESSION_MODE_AUDIT_v1_2.md` (G1b — Libéral SEL)
- `RECAP_SESSION_MODE_AUDIT_v1_3.md` (G2a — Salarié, G2b — Assimilé helpers)
- `RECAP_SESSION_MODE_AUDIT_v1_4.md` (G3a — Stratégie Assimilé, G3b — Stratégie TNS, G3c — Stratégie Libéral, G3d — Comparateur dispositifs, G3d-bis — Comparateur régimes)
- `RECAP_SESSION_MODE_AUDIT_v1_5.md` (G3e-synthese, G3e-scenarios)
- `RECAP_SESSION_MODE_AUDIT_v1_6.md` (G3f-perin, G3f-receptacles)

### §10.3. Snapshots techniques figés

Tous les snapshots intermédiaires `baseline_audit_*_pre/` sont
conservés dans le dépôt et inclus dans l'archive
`snapshot_tns_dev_mode_audit_v1_6.tar.gz` :

`baseline_audit_M0_pre/`, `G1a_pre/`, `G1b_pre/`, `G2a_pre/`,
`G2b_pre/`, `G3a_pre/`, `G3b_pre/`, `G3c_pre/`, `G3d_pre/`, `G3e_pre/`,
`G3f_pre/`.

Chaque snapshot conserve l'état des modules avant le jalon
correspondant et permet la diff exacte de l'instrumentation ajoutée.

### §10.4. Suites de tests de référence

Cf. §3 pour la liste complète. Les 13 fichiers sont à la racine du
dépôt :

```
test_mode_audit_tns.py
test_mode_audit_liberal.py
test_mode_audit_salarie.py
test_mode_audit_assimile.py
test_mode_audit_strategy_assimile.py
test_mode_audit_strategy_tns.py
test_mode_audit_strategy_liberal.py
test_mode_audit_strategy_comparateur.py
test_mode_audit_strategy_comparateur_regimes.py
test_mode_audit_strategy_synthese.py
test_mode_audit_strategy_scenarios.py
test_mode_audit_strategy_perin.py
test_mode_audit_strategy_receptacles.py
```

### §10.5. API de référence

- `core/audit.py` (AUDIT_SPEC_VERSION = 1.1.0) — figée.
  - `class TraceAudit` : nœud du graphe, expose `add()`,
    `attacher_sous_trace()`, `get()`, `get_sous_trace()`, `codes()`,
    `noms_sous_traces()`.
  - `class EtapeAudit` : feuille du graphe, expose `code`, `label`,
    `valeur`, `unite`, `hypotheses`, `notes`, `doctrine_refs`.
  - `resoudre_doctrine_ref(ref)` : résolution d'une référence
    doctrinale vers sa valeur dans `core/profil.py`.

---

## §11. Note de figement (annexe)

Ce document est figé le **19 mai 2026** à la finalisation du jalon
G3g.

**Conditions atteintes au figement :**

- ✓ 12 modules instrumentés, couverture complète du Strategy Engine identifié au cadrage initial.
- ✓ 13 suites de tests MODE_AUDIT vertes, 120+ catégories cumulées.
- ✓ Hash baseline `8863991f27f67847` conservé bout-en-bout.
- ✓ 8 patterns architecturaux validés (composition simple, dynamique, asymétrique, conditionnelle, trace plate, short-circuit, asymétrie rendue visible, branche tracée).
- ✓ 14 patterns non-prescriptifs scannés sur l'ensemble du graphe, zéro violation.
- ✓ 9 namespaces isolés, vérifiés structurellement.
- ✓ Grammaire §5.2 des noms de sous-traces stabilisée (14 entrées).
- ✓ Spec 1.1.0 inchangée sur 6 jalons consécutifs (preuve de stabilité).
- ✓ Documents vivants (AUDIT_MODE, ARCHITECTURE, KNOWN_LIMITATIONS, README) alignés v1.6.
- ✓ Récaps figés v1.1 à v1.6 livrés, jamais modifiés.

**Évolutions à venir (hors périmètre de ce document figé) :**

- Renderer PDF audit-ready (prochain chantier produit).
- G3d-ter (rétro-instrumentation comparateur → receptacles, faible priorité).
- Spec 1.2.0 (détection cycles indirects, immutabilité dure des sous-traces).
- Export JSON / sérialisation externe.
- Helpers de requête.
- Extension `_synthese_tns/liberal` pleine.

Toute évolution future sera tracée dans `AUDIT_MODE.md` (vivant) et
éventuellement dans un nouveau document figé du même format.

---

*Fin du document `MODE_AUDIT_G3_FINAL.md` (figé G3g, 19 mai 2026).*
