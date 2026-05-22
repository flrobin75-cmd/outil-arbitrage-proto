# MODE_AUDIT — Spécification et usage

**Version spec :** 1.1.0
**Date :** 19 mai 2026
**Statut :** v1.6 livrée — 4 régimes + 3 modules stratégie + 2 modules comparateur + 2 modules post-arbitrage + 2 modules transverses épargne instrumentés. Spec 1.1.0 (sous-traces composables) couvre jusqu'à 6 niveaux d'imbrication.

> **Référence figée G3 :** voir `MODE_AUDIT_G3_FINAL.md` (finalisation
> G3g, 19/05/2026). Ce document-ci reste vivant et évolue avec les
> jalons ultérieurs (renderer PDF, G3d-ter, spec 1.2.0, etc.).
> `MODE_AUDIT_G3_FINAL.md` est figé et constitue la doctrine de
> référence pour le futur PDF audit-ready et les usages cabinet.

Ce document décrit le **mode d'audit déterministe** ajouté à l'outil. Il sert de contrat de référence pour les modules instrumentés et de guide d'usage pour les développeurs et les expert-comptables consommateurs.

---

## 1. Intention

Permettre à un expert-comptable de **lire la traçabilité complète d'un arbitrage** : pour chaque ligne d'un calcul (cotisation, prélèvement, plafond, tranche IR), connaître la valeur, l'hypothèse réglementaire qui la fixe, la doctrine qui la justifie, et la position dans la hiérarchie du calcul.

L'audit est volontairement **déterministe et structuré** :

- Pas de génération narrative
- Pas d'IA, pas de scoring, pas de recommandation
- Pas d'explication « humaine » des arbitrages

Ces sujets relèvent d'une couche supérieure « Pourquoi ce résultat ? » non incluse en v1.

---

## 2. Modèle de données

### 2.1. `EtapeAudit` — enregistrement atomique

Défini dans `core/audit.py`. Une étape = une opération de calcul significative.

| Attribut | Type | Rôle |
|---|---|---|
| `code` | `str` | Identifiant **stable et versionné** (cf. §3) |
| `label` | `str` | Libellé humain en français, vocabulaire prudent |
| `valeur` | `Any` | Valeur calculée (généralement float monétaire) |
| `unite` | `str` | `"EUR"`, `"%"`, `"ratio"`, etc. |
| `doctrine_refs` | `tuple[str, ...]` | Identifiants doctrinaux résolus côté renderer |
| `hypotheses` | `dict[str, Any]` | Snapshot des hypothèses chiffrées effectivement utilisées |
| `parent_id` | `str \| None` | Code de l'étape parente, ou `None` pour une racine |
| `notes` | `str` | Annotation libre, vocabulaire prudent |

### 2.2. `TraceAudit` — conteneur

Liste ordonnée d'`EtapeAudit` + métadonnées (régime, profil résumé, version de spec). Helpers exposés :

- `add(code, label, valeur, ...)` — ajoute une étape (lève `ValueError` si code déjà présent)
- `get(code)` — accès par code
- `enfants(code)` — itère les enfants directs
- `racines()` — itère les étapes de premier niveau
- `codes()` — liste ordonnée des codes

### 2.3. Versioning de la spec

`AUDIT_SPEC_VERSION` (actuellement `"1.0.0"`) figure dans chaque `TraceAudit`. Toute modification **rétro-incompatible** de la structure (suppression de champ, changement de sémantique d'un champ existant) doit incrémenter ce numéro.

---

## 3. Convention des `code`

### 3.1. Forme

`<REGIME>_<DOMAINE>_<ETAPE>` en SCREAMING_SNAKE_CASE.

Exemples :

```
TNS_REM_BRUTE                  # racine, input
TNS_COTIS_SOCIALES             # racine, agrégat
TNS_COTIS_TNS_BASE             # enfant de TNS_COTIS_SOCIALES
TNS_CSG_DEDUCTIBLE             # enfant de TNS_COTIS_SOCIALES
TNS_IR_FOYER_AGGREGE           # racine, agrégat IR/CEHR/CDHR
TNS_IR_FOYER_BRUT              # enfant
TNS_DIV_SEUIL_10PCT            # enfant de TNS_DIVIDENDES
```

### 3.2. Politique de versionning

Un code est **stable une fois publié**. Si sa sémantique change :

- ✓ Incrémentation par suffixe : `TNS_IR_FOYER_BRUT_V2`
- ✗ Renommage silencieux : interdit

Le code stable permet aux tests, aux renderers et aux consommateurs futurs (notamment « Pourquoi ce résultat ? ») de référencer sans dépendre du label.

### 3.3. Unicité par trace

Une `TraceAudit` ne peut pas contenir deux étapes avec le même code. `add()` lève `ValueError` en cas de doublon.

---

## 4. Convention des `doctrine_ref`

### 4.1. Forme

Le nom de la **constante ou variable** exposée par `doctrine.py` ou `core/profil.py`.

Exemples :

```
PASS_2026          → 48060          (core/profil.py)
TX_TNS             → 0.45           (core/profil.py)
TX_PFU             → 0.314          (core/profil.py)
SEUIL_DIV_TNS      → 0.10           (core/profil.py)
IR_PLAFOND_T1      → 11600          (core/profil.py)
IR_PLAFOND_T2      → 29579          (core/profil.py)
```

### 4.2. Résolution

Effectuée côté renderer par `core.audit.resoudre_doctrine_ref(ref)`. Cherche d'abord dans `doctrine.py`, puis dans `core.profil`. Lève `AttributeError` si introuvable.

### 4.3. Hypothèses vs doctrine

Le champ `hypotheses` enregistre la **valeur réellement utilisée** par l'étape. Le renderer compare avec la **valeur doctrinale courante** :

- Si égales : affichage standard `doctrine: TX_TNS=0.45`
- Si différentes : marqueur ⚠ `doctrine TX_TNS=0.45 (valeur appliquée: X — override)`

Permet de détecter immédiatement un override local de constante.

---

## 5. Activation et usage

### 5.1. Mécanisme : paramètre par appel

Pas de booléen global. Chaque fonction instrumentée accepte un paramètre :

```python
def calcul_module_tns(profil, rem_nette_souhaitee, ..., *,
                      audit: TraceAudit | None = None) -> ResultatTNS:
    ...
```

- `audit=None` (défaut) : comportement strictement identique au comportement historique. Aucune surcharge, aucune modification du résultat.
- `audit=TraceAudit(...)` : la trace est remplie au fil du calcul.

### 5.2. Exemple minimal

```python
from core.profil import Profil
from core.audit import TraceAudit
from regime.tns import calcul_module_tns
from ui.audit_render import rendre_trace_console

profil = Profil()
trace = TraceAudit(regime="TNS", profil_resume="rem=80k, div=20k")
resultat = calcul_module_tns(
    profil,
    rem_nette_souhaitee=80_000,
    div_bruts=20_000,
    audit=trace,
)

# Le résultat est identique à un appel sans audit
print(resultat.net_apres_ir)  # 68782.82

# La trace contient 24 étapes structurées
print(f"{len(trace.etapes)} étapes")

# Rendu console
print(rendre_trace_console(trace))
```

### 5.3. Accès programmatique à la trace

```python
# Récupération directe d'une étape
e = trace.get("TNS_NET_APRES_IR")
print(e.valeur, e.label)

# Hiérarchie
for racine in trace.racines():
    print(racine.code)
    for enfant in trace.enfants(racine.code):
        print(f"  {enfant.code}")

# Filtrage doctrine
etapes_avec_doctrine = [
    e for e in trace.etapes if e.doctrine_refs
]
```

---

## 6. Périmètre v1.6 et roadmap

### 6.1. Couvert en v1.6 (4 régimes + 3 stratégies + 2 comparateurs + 2 post-arbitrage + 2 transverses épargne)

**Modules transverses épargne** (modules autonomes consommés par d'autres) :
- ✓ Instrumentation `strategy/perin.py` — G3f-perin (1 sous-passe)
  - Namespace `PERIN_*` (Plan d'Épargne Retraite Individuel)
  - 2 fonctions : `calcul_plafond_perin` (trace plate, 7 étapes), `calcul_perin_mutualise` (12 étapes méta + composition conditionnelle)
  - **Composition conditionnelle** : `calcul_perin_mutualise` attache `plafond_dirigeant` toujours et `plafond_conjoint` uniquement si mutualisation effective (situation == "Marié / pacsé" AND conjoint_declare AND revenu_pro_conjoint > 0)
  - Condition explicite tracée : `PERIN_MUTUALISATION_POSSIBLE.hypotheses["condition"]` documente la formule logique + chaque sous-condition évaluée
  - Branche tracée : `PERIN_PLAFOND_TOTAL_RETENU.hypotheses["branche"]` = `"sans_mutualisation"` ou `"avec_mutualisation"`
  - Excédent factuel (pas d'alerte texte synthétique car absente du source)
  - Doctrine_ref : `PASS_2026` cité dans 3 étapes (PLAFOND_CALCULE, PLAFOND_PLANCHER, PLAFOND_PLAFOND)
- ✓ Instrumentation `strategy/receptacles.py` — G3f-receptacles (1 sous-passe)
  - Namespace `RECEPT_*` (matrice §5 d'accessibilité par régime)
  - 5 fonctions : `regime_effectif_receptacles` (4 étapes plates), `est_accessible` (3-4 étapes + sous-trace conditionnelle `regime_effectif`), `motif_inaccessibilite` (1 étape + sous-trace `accessibilite`), `liste_receptacles_par_regime` (trace plate volontaire, 7 étapes), `mention_madelin` (1 étape constante)
  - **Composition interne 3 niveaux** : `motif_inaccessibilite → accessibilite → regime_effectif`
  - **Trace plate volontaire** pour `liste_receptacles_par_regime` : 6 réceptacles itérés en codes plats (`RECEPT_RECEPTACLE_<NOM>`), pas 12 sous-traces (cf. cadrage G3f — convention « bruit structurel vs valeur d'audit »)
  - **Branche short-circuit** : `est_accessible` retourne True sans composer `regime_effectif` si le réceptacle est inconnu (sécurité — ne pas bloquer un futur réceptacle non documenté)
  - **Règle d'or SELARL/SELAS** centralisée : 4 branches explicites tracées (`assimile_direct`, `tns_direct`, `selarl_vers_tns`, `selas_vers_assimile`, `liberal_bnc_pur`, `salarie_ou_inconnu_fallback`)

**Régimes** (sous-trace seule par appel) :
- ✓ Spec et API stable (`core/audit.py`)
- ✓ Instrumentation `regime/tns.py` (24 étapes, codes `TNS_*`) — G1 historique
- ✓ Instrumentation `regime/liberal.py` :
  - `calcul_module_bnc()` (16 étapes, codes `LIB_BNC_*`) — G1a
  - `calcul_module_sel()` (8 étapes, codes `LIB_SEL_*`) — G1b
- ✓ Instrumentation `regime/salarie.py::calcul_module_salarie()` (17 étapes, codes `SAL_*`) — G2a
- ✓ Instrumentation `regime/assimile.py` :
  - `calcul_tx_ir_moyen()` (11 étapes, codes `ASSIM_TX_IR_MOY_*`) — G2b
  - `fs_moyen_epargne()` (1 étape, code `ASSIM_FS_MOYEN`) — G2b

**Stratégies** (consomment les régimes via sous-traces composables, spec 1.1.0) :
- ✓ Instrumentation `strategy/assimile.py` — G3a
  - `calcul_strategie()` (13 étapes par stratégie A/B/C/D, codes `STRAT_ASSIM_<X>_*`)
  - `arbitrage_complet()` (7 étapes méta `STRAT_ASSIM_*` + 5 sous-traces nommées)
- ✓ Instrumentation `strategy/tns.py` — G3b
  - 4 stratégies T1/T2/T3/T4 (12 à 16 étapes selon stratégie, codes `STRAT_TNS_T<X>_*`)
  - `arbitrage_complet_tns()` (7 étapes méta + 4 sous-traces stratégie, chacune avec sous-trace `module_tns`)
  - Convention non-agrégation T4 : étape méta `STRAT_TNS_INDICATEURS_SEPARES` + structure
- ✓ Instrumentation `strategy/liberal.py` — G3c
  - 4 stratégies L1/L2/L3/L4 (3 à 14 étapes selon stratégie, codes `STRAT_LIB_L<X>_*`)
  - `arbitrage_complet_liberal()` (7 étapes méta + 4 sous-traces stratégie)
  - Branches dynamiques L3/L4 : sous-trace `module_tns` ou `module_salarie` selon `forme_sel`
  - Terminologie spécifique : `STRAT_LIB_PLUS_EFFICACE_FISCALEMENT` (au lieu de `RETENU`)
  - Délégation L4 → L3 via sous-trace `strategie_l3_deleguee` (3 niveaux d'imbrication)

**Comparateurs** (couche distincte — comparaison mécanique, namespace dédié) :
- ✓ Instrumentation `strategy/comparateur.py` — G3d (4 sous-passes)
  - Namespace `COMP_*` (comparateur de dispositifs/réceptacles)
  - 36 étapes plates structurées par `parent_id` (pas de sous-trace : module autonome)
  - 6 étapes section A + 1 NB_LIGNES + 15 lignes + 4 top 3 + 5 réceptacles + 4 alertes
  - Top 3 : labels strictement mécaniques (« rang dans le classement par score »)
  - Convention non-prescriptive renforcée : 36 étapes × 12 patterns = 0 violation
- ✓ Instrumentation `strategy/comparateur_regimes.py` — G3d-bis (3 sous-passes)
  - Namespace `COMP_REG_*` (comparateur inter-régimes)
  - 412 étapes au total via composition naturelle (4 sous-traces ligne_<regime>
    qui consomment elles-mêmes arbitrage_assimile / arbitrage_tns / arbitrage_liberal / module_salarie)
  - **Profondeur 6 niveaux** atteinte sur la branche
    `comparateur_regimes → ligne_liberal → arbitrage_liberal → strategie_L4 → strategie_l3_deleguee → module_tns`
  - Garde-fou T4 transversal : `COMP_REG_INDICATEURS_SEPARES_T4` au niveau méta
  - 3 disclaimers permanents en `hypotheses` (DISCLAIMER_CHANGEMENT_REGIME,
    DISCLAIMER_COMPARABILITE, NOTE_RADAR_INTRA_REGIME)
  - Terminologie : `COMP_REG_NET_LE_PLUS_ELEVE` (factuel, pas `RETENU` ni `MEILLEUR`)

**Modules post-arbitrage** (synthèse top-niveau + comparateur 2 scénarios) :
- ✓ Instrumentation `strategy/synthese.py` — G3e-synthese (4 sous-passes)
  - Namespace `SYNTH_*` (synthèse multi-aspects)
  - 7 fonctions de calcul instrumentées : `reset_forfaits`, `calcul_couts_mise_en_oeuvre`, `calcul_radar_6d`, `calcul_projection_5_ans`, `calcul_decomposition_gain`, `calcul_enveloppes_patrimoniales`, `calcul_checklist_conformite`
  - 1 routeur (`calcul_synthese`) + 4 sous-fonctions régime (`_synthese_assimile/tns/liberal/salarie`)
  - **Composition asymétrique** : `_synthese_assimile` attache **6 sous-traces** (couts, radar, projection, decomposition, enveloppes, checklist), `_synthese_salarie` attache 1 sous-trace (`module_salarie`), `_synthese_tns/liberal` n'attachent rien (implémentation allégée v1, non régression de la doctrine §9.2)
  - Garde-fou T4 transversal : `SYNTH_TNS_INDICATEURS_SEPARES_T4` au niveau méta
  - Terminologie : `SYNTH_ENV_ENVELOPPE_NET_LE_PLUS_ELEVE` (factuel, champ Python `meilleure` préservé en `hypotheses["champ_source_python"]`)
  - Checklist conformité strictement descriptive : statuts catégoriels (✅/⚠/🔴/-) en valeur, textes procéduraux source en `hypotheses` (`action_source`, `condition_activation`, `origine`)
  - Discipline non-prescriptive **renforcée** : 14 patterns (12 base + `prioritaire`, `privilégi`)
- ✓ Instrumentation `strategy/scenarios.py` — G3e-scenarios (2 sous-passes)
  - Namespace `SCEN_*` (comparateur 2 scénarios)
  - 3 fonctions instrumentées : `_ir_barème_pur`, `_calcul_scenario`, `calcul_comparaison`
  - **Module 100% autonome** (aucun import instrumenté externe) avec composition interne : `_calcul_scenario` attache `ir_barème`, `calcul_comparaison` attache `scenario_a` + `scenario_b`
  - 3 niveaux d'imbrication internes (`calcul_comparaison → scenario_a/b → ir_barème`)
  - Terminologie : `SCEN_SCENARIO_NET_LE_PLUS_ELEVE` (factuel, champ Python `gagnant` préservé en `hypotheses["champ_source"]`)
  - 2 textes structurants en hypotheses (`AVERTISSEMENT_SCENARIOS`, `MENTION_REGIMES`)

**Infrastructure** :
- ✓ Renderer console (`ui/audit_render.py`) — récursif natif jusqu'à 6 niveaux (G3a → G3d-bis)
- ✓ Suites de tests dédiées (**13 suites**, 120+ catégories cumulées) :
  - `test_mode_audit_tns.py` (7 catégories)
  - `test_mode_audit_liberal.py` (14 catégories, BNC + SEL)
  - `test_mode_audit_salarie.py` (8 catégories)
  - `test_mode_audit_assimile.py` (11 catégories, 2 helpers)
  - `test_mode_audit_strategy_assimile.py` (12 catégories, test 9 non-prescriptif G3a)
  - `test_mode_audit_strategy_tns.py` (11 catégories, imbrication 2 niveaux)
  - `test_mode_audit_strategy_liberal.py` (12 catégories, imbrication 3 niveaux, branches dynamiques)
  - `test_mode_audit_strategy_comparateur.py` (14 catégories, module autonome G3d)
  - `test_mode_audit_strategy_comparateur_regimes.py` (14 catégories, imbrication 6 niveaux G3d-bis)
  - `test_mode_audit_strategy_synthese.py` (14 catégories, **test non-prescriptif renforcé G3e à 14 patterns**)
  - `test_mode_audit_strategy_scenarios.py` (12 catégories, module autonome avec composition interne)
  - `test_mode_audit_strategy_perin.py` (13 catégories, composition conditionnelle G3f)
  - `test_mode_audit_strategy_receptacles.py` (12 catégories, composition 3 niveaux internes G3f)
- ✓ Garde-fous sémantiques étendus (citation pédagogique « : INTERDIT »)
- ✓ Constantes doctrinales centralisées dans `core/profil.py` (4 promotions G2a, suppression duplication G2b)

### 6.2. Reporté

| Étape | Description | Priorité |
|---|---|---|
| G3g — Consolidation doc finale G3 + récap global | Conditions d'achèvement à valider : 12 modules instrumentés, spec stabilisée, 13 suites MODE_AUDIT vertes (atteint en v1.6), grammaire §10.4 stabilisée (atteint en v1.5) | Élevée (prochaine étape, principalement documentaire) |
| Rendu PDF audit-ready | Annexe « Trace d'audit » dans les PDF cabinet — format à stabiliser avec retours cabinet | Élevée (déclenchable maintenant que G3 est conceptuellement complet) |
| G3d-ter — Rétro-instrumentation `comparateur.py` → `receptacles.py` | Propager `audit=` aux appels `est_accessible`/`motif_inaccessibilite` depuis le comparateur G3d. Dette d'instrumentation rétroactive documentée. Modification d'un livrable figé, à cadrer en jalon dédié. | Faible (valeur ajoutée limitée — 3-4 appels max selon config) |
| Export JSON / sérialisation | Pour intégration externe (audit cabinet) | Moyenne |
| Filtrage et requête | Helpers `find_by_regime`, `total_par_code`, etc. | Faible |
| Extension `_synthese_tns/liberal` | Composition pleine des 6 calculs auxiliaires de synthèse (actuellement allégée v1) | Moyenne (post-G3) |

### 6.3. Hors périmètre du mode audit

- Génération narrative automatique (« Le net dirigeant est supérieur de 5 % parce que… »)
- IA / scoring prédictif
- Recommandation automatique de stratégie ou de régime
- Comparaison automatique avec d'autres exercices fiscaux

Ces sujets relèvent de la couche supérieure `Pourquoi ce résultat ?` (cf. `KNOWN_LIMITATIONS.md`).

---

## 7. Garanties non-négociables

Toute évolution du `MODE_AUDIT` doit préserver :

1. **Rétrocompat parfaite** : `audit=None` doit produire un résultat **strictement identique** au comportement historique. Hash baseline `8863991f27f67847` conservé. Vérifié par `compare_baseline.py`.

2. **Aucune logique métier dans la trace** : l'instrumentation est un *side channel*. Une étape d'audit ne modifie jamais le calcul. Si un test métier passe sans audit, il doit passer avec audit, et inversement.

3. **Couche core neutre** : `core/audit.py` ne dépend que de `typing` et `dataclasses`. Le formatage console et PDF reste dans `ui/`. La règle d'architecture `core ← regime ← strategy ← ui ← app` est respectée.

4. **Vocabulaire prudent** : libellés et notes doivent passer les garde-fous sémantiques (`semantic_guardrails.py`, 9 patterns). Le pattern « citation pédagogique » (`: INTERDIT`) permet aux docstrings doctrinales de citer les termes proscrits.

5. **Codes stables** : un `code` publié n'est plus renommé. Toute évolution sémantique incrémente le suffixe (`_V2`).

---

## 8. Tests gardiens

Treize suites de tests sont les **références** du MODE_AUDIT v1.6 :

### 8.1. `test_mode_audit_tns.py` — référence TNS régime (7 catégories)

1. Rétrocompat parfaite (résultat identique avec/sans audit)
2. Structure attendue (codes, hiérarchie, comptage)
3. Cohérence valeurs tracées vs attributs du résultat
4. Résolution doctrinale pour tous les `doctrine_refs` cités
5. Unicité des codes
6. Cas limite : dividendes nuls
7. Rendu console fonctionnel

### 8.2. `test_mode_audit_liberal.py` — référence BNC + SEL régime (14 catégories)

7 pour BNC + 7 pour SEL, dont le test 14 d'isolation des espaces de codes
`LIB_BNC_*` ⊥ `LIB_SEL_*`.

### 8.3. `test_mode_audit_salarie.py` — référence Salarié régime (8 catégories)

7 axes habituels + test 8 d'isolation contre `TNS_*`, `LIB_BNC_*`, `LIB_SEL_*`.

### 8.4. `test_mode_audit_assimile.py` — référence Assimilé régime (11 catégories)

Spécifique parce que `regime/assimile.py` expose deux helpers (un calcul long,
une table) au lieu d'un `calcul_module_X()` unique.

### 8.5. `test_mode_audit_strategy_assimile.py` — référence stratégie Assimilé (12 catégories)

Premier niveau « méta » du MODE_AUDIT (G3a). Vérifie le **modèle composable**
de la spec 1.1.0 : sous-traces nommées (`tx_ir_moy`, `strategie_A/B/C/D`),
4 garde-fous d'attachement, aucune duplication d'étapes entre méta et
sous-traces. Inclut le **premier test 9 non-prescriptif automatique** :
scan récursif sur 12 patterns regex contre labels et notes.

### 8.6. `test_mode_audit_strategy_tns.py` — référence stratégie TNS (11 catégories)

Premier usage de **sous-traces imbriquées sur 2 niveaux** (G3b) :
`arbitrage_complet_tns → strategie_T<X> → module_tns`. Convention de
non-agrégation T4 vérifiée structurellement (indicateurs séparés
`BENEFICE_RETENU_SOCIETE` / `NET_DIRIGEANT_IMMEDIAT`). Textes d'alertes T2
préservés en `hypotheses` (non scannés par le test non-prescriptif).
Pattern non-prescriptif élargi à `\boptim\w*\b` (capture `optimum` aussi).

### 8.7. `test_mode_audit_strategy_liberal.py` — référence stratégie Libéral (12 catégories)

Premier cas de **3 niveaux d'imbrication** (G3c) :
`arbitrage_complet_liberal → strategie_L4 → strategie_l3_deleguee → module_tns/salarie`.
**Branches dynamiques** L3/L4 : sous-trace régime nommée `module_tns`
(SELARL) ou `module_salarie` (SELAS) selon `forme_sel`. Terminologie
spécifique vérifiée : `STRAT_LIB_PLUS_EFFICACE_FISCALEMENT` (pas `RETENU`).
3 alertes structurantes (`ALERTE_BNC_VS_SEL`, `MENTION_RETENTION_V2`,
`ALERTE_L4_V2`) préservées en `hypotheses`.

### 8.8. `test_mode_audit_strategy_comparateur.py` — référence comparateur dispositifs (14 catégories)

Premier module strategy **autonome** (G3d) — aucune sous-trace attachée.
36 étapes plates structurées par `parent_id`. Namespace dédié `COMP_*`
isolé de `STRAT_*` et de tous les préfixes régime (test 10).
Top 3 vérifié structurellement (test 12) : labels mécaniques
(« rang dans le classement par score »), critère explicité, pas de
« meilleur/gagnant/optimal ». Test 13 : alertes (URSSAF, plafonds) en
`hypotheses["textes_alertes_integraux"]`.

### 8.9. `test_mode_audit_strategy_comparateur_regimes.py` — référence comparateur régimes (14 catégories)

Profondeur d'imbrication maximale du chantier (G3d-bis) : **6 niveaux** sur
la branche `comparateur_regimes → ligne_liberal → arbitrage_liberal →
strategie_L4 → strategie_l3_deleguee → module_tns`. Composition naturelle
des 3 stratégies G3a/b/c + module Salarié G2a (4 sous-traces de niveau 1).
Garde-fou T4 transversal (`COMP_REG_INDICATEURS_SEPARES_T4`). Disclaimers
permanents en `hypotheses` (3 textes intégraux). Test 9 non-prescriptif
scanne **412 étapes** en une exécution. Terminologie factuelle
`COMP_REG_NET_LE_PLUS_ELEVE`.

### 8.10. `test_mode_audit_strategy_synthese.py` — référence synthèse top-niveau (14 catégories)

Premier module **multi-fonctions diversifié** (G3e-synthese) : 7 fonctions de
calcul + 1 routeur + 4 sous-fonctions régime, chacune avec une nature
différente (coûts, scoring radar, projection temporelle, waterfall,
enveloppes patrimoniales, checklist, dispatch). **Composition asymétrique**
vérifiée structurellement : `_synthese_assimile` attache 6 sous-traces
(couts, radar, projection, decomposition, enveloppes, checklist),
`_synthese_salarie` attache `module_salarie`, `_synthese_tns/liberal`
ne composent rien (implémentation allégée v1 documentée).
Garde-fou T4 transversal généralisé : `SYNTH_TNS_INDICATEURS_SEPARES_T4`
(héritage G3b → G3d-bis → G3e). Checklist conformité vérifiée comme
**strictement descriptive** : statuts catégoriels (✅/⚠/🔴/-) en valeur,
textes procéduraux source en `hypotheses["action_source"]`.
**Test non-prescriptif renforcé à 14 patterns** : 12 base + `prioritaire`,
`privilégi`.

### 8.11. `test_mode_audit_strategy_scenarios.py` — référence comparateur 2 scénarios (12 catégories)

Module **100% autonome** (G3e-scenarios) — aucun import depuis un module
instrumenté externe — avec **composition interne riche** :
`_calcul_scenario` attache `ir_barème`, `calcul_comparaison` attache
`scenario_a` + `scenario_b` (qui contiennent chacune `ir_barème`).
Profondeur 3 niveaux internes. Champ Python `gagnant` ("A"/"B"/"égalité")
préservé en `hypotheses["champ_source"]` ; côté trace,
`SCEN_SCENARIO_NET_LE_PLUS_ELEVE` factuel. 2 textes structurants
(`AVERTISSEMENT_SCENARIOS`, `MENTION_REGIMES`) vérifiés en
`hypotheses`, fragments testés explicitement absents de label/notes.
Cas « égalité » (seuil 0.01 €) tracé séparément (test 8).

### 8.12. `test_mode_audit_strategy_perin.py` — référence PERIN (13 catégories)

Module **transverse épargne** (G3f-perin) — utilisé en lecture par d'autres
modules (cabinet, calculs ad-hoc). **100% autonome** (import unique
`PASS_2026`). 2 fonctions instrumentées : `calcul_plafond_perin` (trace
plate, 7 étapes) et `calcul_perin_mutualise` (12 étapes méta + composition
conditionnelle).
**Composition conditionnelle** validée structurellement (test 5) : la
sous-trace `plafond_conjoint` est attachée si et seulement si situation
== "Marié / pacsé" AND conjoint_declare AND revenu_pro_conjoint > 0 —
4 scénarios distincts vérifiés (Marié déclaré rev>0 ; Marié non déclaré ;
Marié déclaré rev=0 ; Célibataire avec conjoint forcé).
**Conditions explicites en hypotheses** : `PERIN_MUTUALISATION_POSSIBLE.hypotheses["condition"]`
documente la formule logique avec chaque sous-condition évaluée.
**Branches tracées** : `PERIN_PLAFOND_TOTAL_RETENU.hypotheses["branche"]`
= `"sans_mutualisation"` ou `"avec_mutualisation"`. Cas limites couverts :
plancher 10% PASS (test 6), plafond 8 PASS (test 7), excédent versement
> plafond (test 8). Doctrine_ref unique `PASS_2026` résolu (test 13).

### 8.13. `test_mode_audit_strategy_receptacles.py` — référence RECEPTACLES (12 catégories)

Module **transverse de routage** (G3f-receptacles) — implémente la matrice
§5 d'accessibilité par régime. **100% autonome** (import unique
`Profil`). 5 fonctions instrumentées avec **composition interne sur 3
niveaux** : `motif_inaccessibilite → accessibilite → regime_effectif`
(test 5 vérifie la profondeur structurellement).
**Trace plate volontaire** pour `liste_receptacles_par_regime` (test 6) :
6 réceptacles itérés en codes plats (`RECEPT_RECEPTACLE_<NOM>`), pas
12 sous-traces — convention « bruit structurel vs valeur d'audit ».
**Branche short-circuit** (test 9) : `est_accessible` retourne True sans
composer `regime_effectif` si le réceptacle est inconnu (sécurité). Le
test vérifie l'absence de sous-trace dans ce cas.
**Règle d'or SELARL/SELAS** (test 8) : 4 branches explicites tracées
en `hypotheses["branche_appliquee"]` (`selarl_vers_tns`, `selas_vers_assimile`,
`assimile_direct`, `tns_direct`, `liberal_bnc_pur`, `salarie_ou_inconnu_fallback`).
**Texte structurant `MADELIN_PER_TNS_MENTION`** (test 7) intégral en
hypotheses, fragments-clés testés explicitement absents de label/notes.

### 8.14. Quand mettre à jour les sets `CODES_ATTENDUS_*` ?

Les sets `CODES_ATTENDUS_*` (TNS, BNC, SEL, SAL, TX_IR_MOY, FS, META,
par stratégie, COMP, COMP_REG par régime, SYNTH par section, SCEN méta)
sont des **snapshots du contrat d'instrumentation**. Si une étape est
ajoutée ou supprimée intentionnellement dans le module sous-jacent,
le set doit être mis à jour explicitement — c'est un garde-fou contre
les modifications silencieuses.

---

## 9. Modèle composable (spec 1.1.0)

À partir de la spec 1.1.0 (G3a), `TraceAudit` supporte la **composition
par sous-traces nommées**. Cette section formalise les invariants doctrinaux
du modèle.

### 9.1. Graphe de traces, pas copies de traces

Une stratégie qui appelle un régime (ou une autre stratégie) **ne réémet
jamais** les étapes du régime appelé. Elle :

1. Crée une `TraceAudit` enfant fraîche pour l'appel.
2. Passe cette sous-trace à la fonction appelée (paramètre `audit=`).
3. Attache la sous-trace remplie sous une **clé symbolique** descriptive du
   contexte d'appel.

Le résultat est un **graphe orienté** : la trace parente référence ses
sous-traces, qui peuvent elles-mêmes référencer d'autres sous-traces.
Aucune étape n'est dupliquée.

### 9.2. Interdiction de recalcul

**Règle dure** : une stratégie compose, elle ne recalcule pas.

Si une stratégie a besoin d'une valeur produite par un régime ou par une
autre stratégie, elle l'obtient via :
- Le résultat retourné (`ResultatTNS.net_apres_ir`, etc.)
- L'inspection de la sous-trace (`sub.get(code).valeur`)

Elle ne refait jamais le calcul. Cette règle protège la cohérence du
graphe et évite les divergences silencieuses.

**Conséquence pratique** : si une stratégie appelle deux fois le même
régime (cas du comparateur), elle crée deux sous-traces distinctes sous
deux noms d'attachement différents (`comparaison_a`, `comparaison_b`).
Les codes `TNS_*` apparaissent dans les deux sous-traces sans collision
parce qu'ils vivent dans des `TraceAudit` distinctes.

### 9.3. Une stratégie compose, ne réémet pas

**Une trace stratégie contient uniquement des codes de niveau stratégie**
(`STRAT_<X>_*`). Les codes régime (`TNS_*`, `SAL_*`, etc.) restent dans
les sous-traces régime — jamais à plat dans la trace stratégie parente.

Vérification : tests d'isolation (`Test 5` en G3a, `Test 5` en G3b,
`Test 7` en G3c) refusent toute intrusion d'un préfixe étranger.

### 9.4. Garde-fous d'attachement (refus actifs)

`attacher_sous_trace(nom, sous_trace)` refuse activement :

1. **Doublon de nom** : `nom` déjà utilisé dans cette `TraceAudit` parente.
2. **Réattachement** : même instance `TraceAudit` déjà attachée ailleurs
   dans cette trace parente.
3. **Cycle direct** : `sous_trace is self`.
4. **Type incorrect** : `sous_trace` n'est pas une `TraceAudit`.

Les cycles indirects (A → B → A) ne sont **pas** détectés en v1.1.0 —
éviter par convention. La structure attendue est arborescente.

### 9.5. Doctrine non-prescriptive

Les libellés (`label`) et notes (`notes`) d'une `EtapeAudit` doivent rester
**strictement factuels**. Aucun wording prescriptif n'est toléré, y compris
au sens négatif ou disclaimer (« ne constitue PAS une recommandation » →
reformuler en « ne constitue pas un avis sur le choix de structuration »).

Le **test 9 non-prescriptif** (introduit en G3a, propagé à G3b/G3c) scanne
récursivement labels et notes contre 12 patterns regex :

```
\boptim\w*\b              (optimum, optimal, optimisation, …)
\bmeilleur(e|s|es)?\b     \bgagnant(e|s|es)?\b
\bperdant(e|s|es)?\b      \bavantageu(x|se|ses)\b
\brecommand(é|ée|…)\b     \bpréconis(é|ée|…)\b
\bconseill(é|ée|…)\b      \bidéal(e|s|es)?\b
\bparfait(e|s|es)?\b      \bsupérieur(e|s|es)?\b
\binférieur(e|s|es)?\b
```

**Échappatoire structurelle** : les textes métier qui contiennent du
vocabulaire prescriptif (alertes utilisateur en français) sont placés
dans le champ `hypotheses` (dict non scanné). Le wording métier reste
intact, la trace MODE_AUDIT reste factuelle.

Exemples documentés :
- G3b TNS T2 — alerte `optimum dividendes-PFU est très limité` → `hypotheses["textes_alertes"]`
- G3c Libéral L3/L4 — `ALERTE_BNC_VS_SEL`, `MENTION_RETENTION_V2`, `ALERTE_L4_V2` → toutes en `hypotheses`

---

## 10. Conventions de namespaces

Les codes d'étapes utilisent des **préfixes par couche**, isolés les uns
des autres. Cette section formalise la convention.

### 10.1. Régimes (couche `regime/`)

| Préfixe | Module source | Fonctions |
|---|---|---|
| `TNS_*` | `regime/tns.py` | `calcul_module_tns` (24 étapes) |
| `LIB_BNC_*` | `regime/liberal.py` | `calcul_module_bnc` (16 étapes) |
| `LIB_SEL_*` | `regime/liberal.py` | `calcul_module_sel` (8 étapes) |
| `SAL_*` | `regime/salarie.py` | `calcul_module_salarie` (17 étapes) |
| `ASSIM_TX_IR_MOY_*` | `regime/assimile.py` | `calcul_tx_ir_moyen` (11 étapes) |
| `ASSIM_FS_*` | `regime/assimile.py` | `fs_moyen_epargne` (1 étape) |

### 10.2. Stratégies et comparateurs et post-arbitrage (couche `strategy/`)

**Stratégies mono-régime** — convention longue validée : `STRAT_<REGIME>_<STRATEGIE>_<DOMAINE>_<ETAPE>`

| Préfixe | Module source | Fonctions |
|---|---|---|
| `STRAT_ASSIM_*` | `strategy/assimile.py` (méta) | `arbitrage_complet` |
| `STRAT_ASSIM_<X>_*` (X∈{A,B,C,D}) | `strategy/assimile.py` | `calcul_strategie` |
| `STRAT_TNS_*` | `strategy/tns.py` (méta) | `arbitrage_complet_tns` |
| `STRAT_TNS_T<X>_*` (X∈{1,2,3,4}) | `strategy/tns.py` | `_calcul_strategie_t<X>` |
| `STRAT_LIB_*` | `strategy/liberal.py` (méta) | `arbitrage_complet_liberal` |
| `STRAT_LIB_L<X>_*` (X∈{1,2,3,4}) | `strategy/liberal.py` | `_calcul_strategie_l<X>` |

**Comparateurs** — namespace distinct de `STRAT_*` parce que la nature est
différente (classement mécanique, pas arbitrage mono-régime) :

| Préfixe | Module source | Fonctions | G3 |
|---|---|---|---|
| `COMP_*` | `strategy/comparateur.py` | `calcul_comparateur` (réceptacles, dispositifs) | G3d |
| `COMP_REG_*` | `strategy/comparateur_regimes.py` (méta) | `calcul_comparateur_regimes` | G3d-bis |
| `COMP_REG_ASSIM_*` | `strategy/comparateur_regimes.py` | `_ligne_assimile` | G3d-bis |
| `COMP_REG_TNS_*` | `strategy/comparateur_regimes.py` | `_ligne_tns` | G3d-bis |
| `COMP_REG_LIB_*` | `strategy/comparateur_regimes.py` | `_ligne_liberal` | G3d-bis |
| `COMP_REG_SAL_*` | `strategy/comparateur_regimes.py` | `_ligne_salarie` | G3d-bis |

**Modules post-arbitrage** — synthèse top-niveau et comparateur 2 scénarios.
Distincts de tous les namespaces précédents pour refléter la nature
fonctionnelle différente (assemblage de résultats vs calcul de stratégies) :

| Préfixe | Module source | Fonctions | G3 |
|---|---|---|---|
| `SYNTH_RESET_FORFAITS_*` | `strategy/synthese.py` | `reset_forfaits` | G3e-synthese.1 |
| `SYNTH_COUTS_*` | `strategy/synthese.py` | `calcul_couts_mise_en_oeuvre` | G3e-synthese.1 |
| `SYNTH_RADAR_*` | `strategy/synthese.py` | `calcul_radar_6d` | G3e-synthese.2 |
| `SYNTH_PROJECTION_*` | `strategy/synthese.py` | `calcul_projection_5_ans` | G3e-synthese.2 |
| `SYNTH_DECOMPOSITION_*` | `strategy/synthese.py` | `calcul_decomposition_gain` | G3e-synthese.2 |
| `SYNTH_ENV_*` | `strategy/synthese.py` | `calcul_enveloppes_patrimoniales` | G3e-synthese.3 |
| `SYNTH_CHECKLIST_*` | `strategy/synthese.py` | `calcul_checklist_conformite` | G3e-synthese.3 |
| `SYNTH_REGIME_DISPATCH` | `strategy/synthese.py` | `calcul_synthese` (routeur) | G3e-synthese.4 |
| `SYNTH_ASSIM_*` | `strategy/synthese.py` | `_synthese_assimile` | G3e-synthese.4 |
| `SYNTH_TNS_*` | `strategy/synthese.py` | `_synthese_tns` | G3e-synthese.4 |
| `SYNTH_LIB_*` | `strategy/synthese.py` | `_synthese_liberal` | G3e-synthese.4 |
| `SYNTH_SAL_*` | `strategy/synthese.py` | `_synthese_salarie` | G3e-synthese.4 |
| `SCEN_IR_*` | `strategy/scenarios.py` | `_ir_barème_pur` | G3e-scenarios.1 |
| `SCEN_*` (à plat) | `strategy/scenarios.py` | `_calcul_scenario`, `calcul_comparaison` | G3e-scenarios.1 |

**Modules transverses épargne** — modules autonomes consommés en lecture
par d'autres modules (cabinet, comparateur, etc.) :

| Préfixe | Module source | Fonctions | G3 |
|---|---|---|---|
| `PERIN_*` | `strategy/perin.py` | `calcul_plafond_perin`, `calcul_perin_mutualise` | G3f-perin |
| `RECEPT_*` | `strategy/receptacles.py` | `regime_effectif_receptacles`, `est_accessible`, `motif_inaccessibilite`, `liste_receptacles_par_regime`, `mention_madelin` | G3f-receptacles |

### 10.3. Règles d'isolation (vérifiées par les tests)

- Les préfixes régime ne se croisent pas (`TNS_*` ⊥ `LIB_BNC_*` ⊥ `LIB_SEL_*` ⊥ `SAL_*` ⊥ `ASSIM_*`).
- Les préfixes stratégie ne se croisent pas (`STRAT_ASSIM_*` ⊥ `STRAT_TNS_*` ⊥ `STRAT_LIB_*`).
- Les préfixes comparateur ne se croisent ni entre eux ni avec stratégies (`COMP_*` ⊥ `COMP_REG_*` ⊥ `STRAT_*`).
- Les préfixes post-arbitrage ne se croisent pas (`SYNTH_*` ⊥ `SCEN_*`) ; ne se croisent avec aucune des couches précédentes.
- Les préfixes transverses épargne ne se croisent pas (`PERIN_*` ⊥ `RECEPT_*`) ; ne se croisent avec aucune des couches précédentes.
- Les préfixes stratégie ne se confondent pas avec les préfixes régime (`STRAT_TNS_*` ≠ `TNS_*`).
- Dans une trace stratégie, comparateur, post-arbitrage ou transverse, **aucun code de préfixe régime** n'apparaît à plat — les codes régime vivent dans les sous-traces.

### 10.4. Noms de sous-traces standards

La grammaire formelle du graphe d'audit. Les noms d'attachement sont
**stables** entre modules et **explicitement testés** pour éviter toute
divergence. Toute évolution requiert mise à jour de cette table.

**Sous-traces de modules régime** (appelées depuis les stratégies) :

| Nom d'attachement | Sémantique | Utilisé dans |
|---|---|---|
| `module_bnc` | Appel à `calcul_module_bnc` (LIB_BNC_*) | strategy/liberal L1, L2 |
| `module_tns` | Appel à `calcul_module_tns` (TNS_*) | strategy/tns T1-T4, strategy/liberal L3/L4 SELARL, strategy/scenarios indirect |
| `module_salarie` | Appel à `calcul_module_salarie` (SAL_*) | strategy/liberal L3/L4 SELAS, strategy/comparateur_regimes, strategy/synthese `_synthese_salarie` |
| `module_sel` | Appel à `calcul_module_sel` (LIB_SEL_*) | Réservé G3 ultérieur |
| `tx_ir_moy` | Appel à `calcul_tx_ir_moyen` (ASSIM_TX_IR_MOY_*) | strategy/assimile (arbitrage) |

**Sous-traces de stratégies** (composition au niveau arbitrage) :

| Nom d'attachement | Sémantique | Utilisé dans |
|---|---|---|
| `strategie_<CODE>` | Sous-trace stratégie individuelle | Tous routeurs `arbitrage_complet_*` (codes A, B, C, D ou T1-T4 ou L1-L4) |
| `strategie_l3_deleguee` | Délégation L4 → L3 | strategy/liberal L4 |

**Sous-traces de comparateur régimes** (G3d-bis) :

| Nom d'attachement | Sémantique | Utilisé dans |
|---|---|---|
| `ligne_<regime>` | Sous-trace ligne régime au niveau méta | strategy/comparateur_regimes |
| `arbitrage_assimile` | Appel à `arbitrage_complet` (Assimilé) | `_ligne_assimile` |
| `arbitrage_tns` | Appel à `arbitrage_complet_tns` | `_ligne_tns` |
| `arbitrage_liberal` | Appel à `arbitrage_complet_liberal` | `_ligne_liberal` |

**Sous-traces de synthèse** (G3e-synthese) :

| Nom d'attachement | Sémantique | Utilisé dans |
|---|---|---|
| `synthese_<regime>` | Sous-trace synthèse régime au niveau routeur | `calcul_synthese` (dispatch) |
| `couts` | Appel à `calcul_couts_mise_en_oeuvre` | `_synthese_assimile` |
| `radar` | Appel à `calcul_radar_6d` | `_synthese_assimile` |
| `projection` | Appel à `calcul_projection_5_ans` | `_synthese_assimile` |
| `decomposition` | Appel à `calcul_decomposition_gain` | `_synthese_assimile` |
| `enveloppes` | Appel à `calcul_enveloppes_patrimoniales` | `_synthese_assimile` |
| `checklist` | Appel à `calcul_checklist_conformite` | `_synthese_assimile` |

**Sous-traces de scenarios** (G3e-scenarios, composition interne au module) :

| Nom d'attachement | Sémantique | Utilisé dans |
|---|---|---|
| `ir_barème` | Appel à `_ir_barème_pur` | `_calcul_scenario` |
| `scenario_a` | Appel à `_calcul_scenario` (premier scénario) | `calcul_comparaison` |
| `scenario_b` | Appel à `_calcul_scenario` (second scénario) | `calcul_comparaison` |

**Sous-traces de perin** (G3f-perin, composition conditionnelle) :

| Nom d'attachement | Sémantique | Utilisé dans |
|---|---|---|
| `plafond_dirigeant` | Appel à `calcul_plafond_perin("Dirigeant", ...)` (toujours attaché) | `calcul_perin_mutualise` |
| `plafond_conjoint` | Appel à `calcul_plafond_perin("Conjoint", ...)` (attaché si et seulement si mutualisation effective) | `calcul_perin_mutualise` |

**Sous-traces de receptacles** (G3f-receptacles, composition interne sur 3 niveaux) :

| Nom d'attachement | Sémantique | Utilisé dans |
|---|---|---|
| `regime_effectif` | Appel à `regime_effectif_receptacles` (composition interne) | `est_accessible` (si réceptacle connu) |
| `accessibilite` | Appel à `est_accessible` (composition interne) | `motif_inaccessibilite` |

**Règle de nommage** : les noms sont **descriptifs et invariants** (pas de
suffixe d'ordre, pas d'horodatage). Ils décrivent **ce qui est composé**
(le rôle fonctionnel de la sous-trace), pas **comment** ni **dans quel ordre**.
Cela permet à un consommateur de trace de naviguer le graphe par chemin
symbolique (`trace.get_sous_trace("synthese_assimile").get_sous_trace("radar")`)
sans dépendance à l'ordre d'attachement.

### 10.5. Évolution des préfixes

Comme pour les codes d'étape, les préfixes sont **stables une fois publiés**.
Toute évolution sémantique structurelle (changement de granularité,
fusion/scission d'espaces) doit incrémenter `AUDIT_SPEC_VERSION` et être
documentée dans la section historique.
