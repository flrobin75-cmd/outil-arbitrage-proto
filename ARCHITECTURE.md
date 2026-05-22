# ARCHITECTURE — Outil d'arbitrage rémunération dirigeant

**Version document :** 1.2 (B.3 finalisée — ponts supprimés)
**Date :** 19 mai 2026
**Statut :** Référence post-B.3 — architecture canonique sans couche-pont

> Document de référence architectural. Les **règles d'import** et la **doctrine de séparation métier/UI** sont opposables — toute PR qui les enfreint est bloquée. Pour le vocabulaire prudent, voir `TERMINOLOGY.md`. Pour les garde-fous sémantiques automatisés, voir `SEMANTIC_GUARDRAILS.md`.

---

## 1. Vue d'ensemble

L'application est structurée selon **quatre niveaux d'abstraction** alignés avec le Cadre méthodologique v1.0.1 §2. Chaque niveau a une responsabilité unique et ne peut consommer que les niveaux inférieurs.

```
        ┌─────────────┐
        │   app.py    │   Routing Streamlit, états UI, pages
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │     ui/     │   Présentation (formatage, PDF, admin)
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │  strategy/  │   Stratégies d'arbitrage par régime
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │   regime/   │   Calcul net dirigeant par régime
        └──────┬──────┘
               ↓
        ┌─────────────┐
        │    core/    │   Maths fiscales/sociales communes
        └─────────────┘
```

---

## 2. Règle d'import canonique

> **`core ← regime ← strategy ← ui ← app`**
>
> **Jamais l'inverse.**

### 2.1. Conséquences pratiques

| Niveau émetteur | Peut importer depuis | NE PEUT PAS importer depuis |
|---|---|---|
| `core/*`     | (aucun module métier)        | `regime/*`, `strategy/*`, `ui/*`, `app.py` |
| `regime/*`   | `core/*`                     | `strategy/*`, `ui/*`, `app.py`             |
| `strategy/*` | `core/*`, `regime/*`         | `ui/*`, `app.py`                           |
| `ui/*`       | `core/*`, `regime/*`, `strategy/*` | `app.py`                             |
| `app.py`     | tout                         | —                                          |

### 2.2. Sens des dépendances : pourquoi cet ordre

Le sens choisi reflète la **stabilité décroissante des couches** :

- `core/` change rarement (paramètres fiscaux annuels, structure de profil). Toute modification y casse potentiellement tout le reste — donc on ne lui inflige aucune dépendance entrante.
- `regime/` change quand un régime social évolue (réforme TNS, plafond Madelin, etc.). Indépendant entre régimes : aucun fichier `regime/X.py` n'importe `regime/Y.py`.
- `strategy/` change quand on revoit une stratégie d'arbitrage ou un comparateur. C'est l'endroit où les choix éditoriaux se concrétisent (vocabulaire prudent, alertes métier).
- `ui/` change quand on revoit la présentation (Streamlit, PDF). Aucune logique métier ici.
- `app.py` orchestre, mais **n'a pas le droit d'inventer du métier** : si une page Streamlit fait un calcul, c'est qu'il manque un appel à un module `strategy/` ou `regime/`.

### 2.3. Doctrine de séparation métier / UI

Au-delà du sens d'import, deux règles éditoriales :

1. **Aucune logique métier dans `ui/` ni dans `app.py`.** Un calcul, une règle d'arbitrage, une alerte conditionnelle (« si L3/L4 alors alerte BNC/SEL ») relèvent toujours de `strategy/` ou `regime/`. La couche UI consomme et formate.
2. **Aucune dépendance à Streamlit dans `core/`, `regime/`, `strategy/`.** Ces couches doivent rester importables et testables sans Streamlit installé. Toute fonction qui appelle `st.*` est dans `ui/` ou dans `app.py`.

Conséquence pratique pour les disclaimers (cf. `ui/disclaimers.py`, B.2.5) :

| Type de disclaimer | Localisation | Exemple |
|---|---|---|
| **Présentation** (n'affecte pas le calcul) | `ui/disclaimers.py` | Primauté cabinet, AMF Comparateur, avertissement final |
| **Alerte métier** (conditionne ou qualifie un résultat) | `strategy/*.py` | `ALERTE_BNC_VS_SEL` (Libéral), `DISCLAIMER_CHANGEMENT_REGIME` (Comparateur de régimes) |

Pour ajouter un nouveau message : trancher d'abord s'il sert à un calcul / filtrage / qualification de résultat (→ `strategy/`) ou s'il est purement informatif côté lecteur (→ `ui/disclaimers.py`).

### 2.4. Détection automatique

Un script de validation peut grep les imports interdits :

```bash
# Aucun strategy/* ne doit importer ui/*
grep -r "^from ui" strategy/

# Aucun regime/* ne doit importer strategy/*
grep -r "^from strategy" regime/

# Aucun core/* ne doit importer regime/* ou strategy/*
grep -rE "^from (regime|strategy|ui)" core/
```

Verrouillé en CI par `check_imports.py` (17 fichiers scannés). Toute violation est un **blocage de merge**.

---

## 3. Structure des dossiers

### `core/` — Core Engine

Mathématiques fiscales et sociales **communes à tous les régimes**. Invariant.

| Fichier | Contenu | Symboles principaux |
|---|---|---|
| `core/profil.py` | Constantes 2026 + dataclass `Profil` + situations QF | `Profil`, `PASS_2026`, `TX_PFU`, `SITUATIONS_PARTICULIERES` |
| `core/ir_foyer.py` | Chaîne IR + CEHR + CDHR + plafonnement QF | `calcul_ir_foyer`, `ir_par_tranche`, `tmi_de` |
| `core/projection.py` | Math pure de capitalisation 5 ans | `projection_5_ans` |
| `core/audit.py` | API MODE_AUDIT — trace déterministe opt-in (side channel) | `TraceAudit`, `EtapeAudit`, `resoudre_doctrine_ref`, `AUDIT_SPEC_VERSION` |

### `regime/` — Regime Engine

Calcul du **net dirigeant par régime**, à partir d'un revenu cotisable donné. Chaque moteur de régime est strictement isolé : pas d'import croisé entre fichiers regime.

| Fichier | Régime | Symboles principaux |
|---|---|---|
| `regime/assimile.py` | Assimilé salarié (helpers) | `calcul_tx_ir_moyen`, `fs_moyen_epargne` |
| `regime/tns.py` | TNS (gérant majoritaire / EURL) | `calcul_module_tns`, `ResultatTNS` |
| `regime/liberal.py` | Libéral (BNC + SEL) | `calcul_module_bnc`, `calcul_module_sel` |
| `regime/salarie.py` | Salarié | `calcul_module_salarie`, `ResultatSalarie` |

### `strategy/` — Strategy Engine

**Stratégies d'arbitrage** propres à chaque régime. Consomme les Regime Engine pour produire des comparaisons et synthèses. C'est ici que vivent les **alertes métier** (qui conditionnent un résultat ou un libellé).

| Fichier | Rôle | Symboles principaux |
|---|---|---|
| `strategy/assimile.py` | Stratégies A/B/C/D Assimilé | `arbitrage_complet`, `STRATEGIES` |
| `strategy/tns.py` | Stratégies T1–T4 + garde-fou T4 | `arbitrage_complet_tns`, `ResultatStrategieTNS` |
| `strategy/liberal.py` | Stratégies L1–L4 + `ALERTE_BNC_VS_SEL` | `arbitrage_complet_liberal`, `ALERTE_BNC_VS_SEL`, `ALERTE_L4_V2` |
| `strategy/comparateur.py` | Comparateur dispositifs Option 2 | `calcul_comparateur`, `ConfigComparateur` |
| `strategy/comparateur_regimes.py` | Comparateur inter-régimes + alertes | `DISCLAIMER_CHANGEMENT_REGIME`, `DISCLAIMER_COMPARABILITE`, `NOTE_RADAR_INTRA_REGIME` |
| `strategy/synthese.py` | Synthèse + Radar 6D + ROI | `calcul_synthese`, `FORFAITS_DEFAUT` |
| `strategy/scenarios.py` | Scénarios A vs B multi-régimes | `calcul_comparaison`, `ScenarioInputs`, `AVERTISSEMENT_SCENARIOS` |
| `strategy/perin.py` | PERIN mutualisé conjoints | `calcul_perin_mutualise` |
| `strategy/receptacles.py` | Matrice §5 (filtrage Comparateur) | `MATRICE_RECEPTACLES` |

**Alertes métier qui restent ici (et non dans `ui/`)** :
- `ALERTE_BNC_VS_SEL` — conditionne le libellé Libéral L3/L4
- `ALERTE_L4_V2` — calcul fictif d'optimisation de structure
- `DISCLAIMER_CHANGEMENT_REGIME` — affichée si le profil change de régime entre scénarios
- `DISCLAIMER_COMPARABILITE` — affichée si le comparateur croise des modèles à granularité différente
- `NOTE_RADAR_INTRA_REGIME` — affichée pour la lecture radar intra-régime

### `ui/` — UI Layer

**Présentation et formatage**. Aucune logique métier. Streamlit, génération PDF, page admin, disclaimers de présentation.

| Fichier | Rôle | Symboles principaux |
|---|---|---|
| `ui/utils.py` | Formatage € / % / badges niveau | `format_eur`, `NIVEAU_COULEURS` |
| `ui/pdf_export.py` | Génération PDF cabinet | `generer_pdf_synthese`, `_build_pdf_assimile`, `_build_pdf_tns`, `_build_pdf_liberal`, `_build_pdf_salarie` |
| `ui/admin.py` | Page admin paramètres | `construire_catalogue`, `restaurer_doctrine_officielle` |
| `ui/disclaimers.py` | Disclaimers de présentation (B.2.5) | `DISCLAIMER_PRIMAUTE_CABINET`, `DISCLAIMER_AMF_COMPARATEUR_PATRIMONIAL`, `DISCLAIMER_AVERTISSEMENT_FINAL`, `TRACE_DOCTRINALE_FOOTER`, `trace_doctrinale_annexe_complete()` |
| `ui/audit_render.py` | Renderer console pour `TraceAudit` (MODE_AUDIT v1) | `rendre_trace_console` |

### Racine

| Fichier | Rôle | Statut |
|---|---|---|
| `doctrine.py` | Cadre méthodologique v1.0.1 (constantes, enum NiveauConfiance, historique versions) | Permanent |
| `app.py` | Application Streamlit (routing, pages, états UI) | Permanent — imports canoniques uniquement (post-B.3) |
| `compare_baseline.py`, `baseline_outputs.py`, `baseline_tests.py`, `check_imports.py` | Outils de validation numérique et architecturale | Permanents |
| `semantic_guardrails.py`, `audit_final_b2_controle3.py` | Audits sémantiques (9 patterns + 4 patterns historiques) | Permanents |
| `test_*.py` | 11 suites de tests (504 baseline + B.2) | Permanents — y compris `test_backward_compat_imports.py` qui vérifie l'absence des ponts |

---

## 4. Modules-ponts rétrocompatibilité — SUPPRIMÉS en B.3

> ⚠ **Cette couche a été supprimée le 19/05/2026 à la fin de la Phase B.3.**
> La section ci-dessous est conservée comme **historique de référence** pour comprendre pourquoi le dépôt a contenu cette couche transitoire de mars à mai 2026, et pourquoi elle a disparu.

### 4.1. Pourquoi les ponts ont existé pendant B.2

Pendant la **Phase B.2** (refactorisation multi-régimes), les anciens noms de fichiers (`moteur_tns.py`, `moteur_liberal.py`, etc.) ont été conservés à la racine sous forme de **modules-ponts**, pour ne pas casser `app.py` (~1500 lignes Streamlit) qui importait ~42 symboles via leurs noms historiques. Les ponts étaient des re-exports minimaux vers les couches canoniques `core/`, `regime/`, `strategy/`, `ui/`.

Ce dispositif permettait :
- de ne **pas** ré-écrire `app.py` pendant B.2 (charge cognitive et risque de régression),
- de valider la **non-régression métier** isolément avant de toucher la couche applicative,
- d'avoir un point de rollback simple si la nouvelle arborescence posait problème.

### 4.2. Suppression en B.3 (terminée 19/05/2026)

La Phase B.3 a migré tous les consommateurs vers les imports canoniques :
- `app.py` (G1→G6, 42 imports + 3 imports déférés)
- `compare_baseline.py`, `baseline_outputs.py` (G7a)
- 9 fichiers de tests métier (G7b)
- `test_backward_compat_imports.py` réécrit en test d'absence (G7c)

Puis les 11 ponts ont été supprimés (G7d) :

```
moteur.py             admin_parametres.py    moteur_perin.py
moteur_tns.py         export_pdf.py          moteur_salarie.py
moteur_liberal.py     moteur_comparateur.py  moteur_scenarios.py
                      moteur_synthese.py     utils_ui.py
```

### 4.3. Garde-fou d'absence (B.3 finalisée)

Le fichier `test_backward_compat_imports.py` a été réécrit. Il vérifie maintenant l'INVERSE :
1. Aucun fichier-pont ne subsiste à la racine (11 vérifications)
2. Aucun nom historique n'est importable (11 vérifications — chaque import doit lever `ImportError`)
3. Aucun consommateur ne fait `from moteur_*` / `from utils_ui` / `from export_pdf` / `from admin_parametres` (vérification statique par grep)

Sortie : `OK : 23/23` quand le dépôt est propre, exit code 1 sinon. Tout passage à `KO` signale qu'un pont a été ré-introduit.

---

## 5. Tests et baseline

### 5.1. Validation à 4 étages

| Étage | Fichier | Couverture |
|---|---|---|
| Valeurs numériques | `compare_baseline.py` | 16 valeurs clés (Arbitrage, Comparateur, Synthèse, PERIN, Scénarios) |
| Tests métier baseline | `baseline_tests.py compare` | 504 validations sur 7 modules (TNS, Libéral, Salarié, Comparateur, Synthèse, Scénarios, PERIN) |
| Tests métier B.2 | 8 suites dédiées | 348 validations B.2 (rétrocompat imports, strategy TNS/Libéral, étapes 4–5, PDF render, garde-fous Déclaratif + terminologie) |
| Audit sémantique unifié | `semantic_guardrails.py` (B.2.5) | 9 patterns surveillés en CI (Déclaratif nom + adjectif, recommandée, optimisation/optimal, garanti/garantie, sans risque, meilleur régime, recommandé automatiquement, agrégation T4) |

### 5.2. Workflow validation après chaque modification

```bash
python3 compare_baseline.py             # 16 valeurs
python3 check_imports.py                # 17 fichiers conformes
python3 baseline_tests.py compare       # 504 tests baseline
# Suites B.2
python3 test_backward_compat_imports.py
python3 test_strategy_tns.py
python3 test_strategy_liberal.py
python3 test_etape4.py
python3 test_etape5.py
python3 test_pdf_render_all_regimes.py
python3 test_no_declaratif_residual.py
python3 test_terminologie_freeze.py
# Audit sémantique unifié B.2.5
python3 semantic_guardrails.py
```

**Aucune modification ne peut être committée si l'une de ces commandes échoue.**

### 5.3. Historique baseline

| Baseline | Localisation | Doctrine | Statut |
|---|---|---|---|
| `baseline_outputs/` | Régénérable par `baseline_outputs.py` | v1.0.1 | Active (référence numérique courante, hash `8863991f27f67847`) |
| `baseline_freeze_b2/` | Snapshot code au freeze B.2 | v1.0.1 | Archive figée 19/05/2026 |
| `baseline_outputs_b2/` | 6 PDF de référence + log horodaté des 11 suites | v1.0.1 | Archive figée 19/05/2026 |

---

## 6. Doctrine et versionning

Le moteur applique le **Cadre méthodologique v1.0.1** (document Word `Cadre_Methodologique_Arbitrage_v1.0.1.docx`).

Chaque calcul embarque trois éléments de traçabilité :

- `DOCTRINE_VERSION` (actuellement `"1.0.1"`)
- `DOCTRINE_DATE` (actuellement `"2026-05-01"`)
- `DOCTRINE_HISTORIQUE` (liste des versions et changements)

Définis dans `doctrine.py`. Affichés dans le footer de l'app + chaque PDF généré.

---

## 7. Évolution

### 7.1. Phase B.2 — Refactorisation multi-régimes (figée 19/05/2026)

Sur la base de cette architecture, B.2 a livré :

- `core/`, `regime/`, `strategy/`, `ui/` (15 nouveaux fichiers métier)
- Stratégies TNS (T1–T4 avec garde-fou T4), Libéral (L1–L4 avec ALERTE_BNC_VS_SEL)
- Comparateur de régimes (vue inter-régimes)
- Synthèse multi-régimes adaptée
- Réceptacles différenciés par régime dans le Comparateur
- 6 PDF adaptés par régime (Assimilé, TNS, TNS T4, Libéral BNC, Libéral SEL, Salarié)
- Disclaimers v1.0.1 (Primauté cabinet, AMF, avertissement final) intégrés aux 6 PDF
- Renommage « Déclaratif » → « Conformité renforcée » (alias interne conservé)
- 11 modules-ponts pour rétrocompatibilité de `app.py`

Cf. `CHANGELOG_B2_GLOBAL.md` pour le récap des 6 étapes B.2.

### 7.2. Phase B.2.5 — Hardening documentaire (19/05/2026)

Documente l'état figé en B.2 sans modifier la logique métier :

- `TERMINOLOGY.md` — vocabulaire prudent + sémantique des 4 niveaux v1.0.1
- `SEMANTIC_GUARDRAILS.md` — doctrine des garde-fous sémantiques
- `semantic_guardrails.py` — script unifié (3 audits existants + 5 nouveaux patterns)
- `ui/disclaimers.py` — centralisation des disclaimers de présentation (alertes métier restent dans `strategy/`)
- Trace doctrinale enrichie dans les PDF (footer « Doctrine v1.0.1 — France 2026 » + annexe « Trace doctrinale » consultable)
- Nettoyage des 4 occurrences résiduelles de l'adjectif « déclaratif » dans les contenus utilisateur (doctrine.py × 2, app.py × 1, strategy/scenarios.py × 1)

Aucune modification de l'architecture canonique. Hash baseline numérique inchangé.

### 7.3. Phase B.3 — Migration applicative (terminée 19/05/2026)

Migration des imports d'`app.py`, des outils baseline et des tests métier vers les couches canoniques `core.*`, `regime.*`, `strategy.*`, `ui.*`, puis suppression des 11 modules-ponts racine.

**Séquence exécutée en 7 groupes (G1 → G7) :**

| Groupe | Périmètre | Résultat |
|---|---|---|
| G1 | `app.py` : imports `moteur_synthese`, `moteur_scenarios`, `moteur_perin` → `strategy.*` | ✓ |
| G2 | `app.py` : imports `moteur_comparateur` → `strategy.comparateur` | ✓ |
| G3 | `app.py` : imports `moteur_tns`, `moteur_liberal`, `moteur_salarie` → `core.profil` + `regime.*` | ✓ |
| G4 | `app.py` : imports `moteur` → `strategy.assimile` + `core.projection` | ✓ |
| G5 | `app.py` : imports `utils_ui` → `ui.utils` | ✓ |
| G6 | `app.py` : imports `export_pdf` → `ui.pdf_export`, `admin_parametres` → `ui.admin` | ✓ |
| G7a | `baseline_outputs.py`, `compare_baseline.py` migrés vers les couches canoniques | ✓ |
| G7b | 9 tests métier migrés vers les couches canoniques | ✓ |
| G7c | `test_backward_compat_imports.py` réécrit en test d'absence de ponts | ✓ |
| G7d | Suppression effective des 11 modules-ponts (`rm`) | ✓ |
| G7e | Re-validation complète : 11 suites + 9 patterns + 4 patterns + 6 PDF delta 0 octet | ✓ |
| G7f | Mise à jour de `ARCHITECTURE.md`, `CHANGELOG_B2_GLOBAL.md`, `README_FREEZE_B2.md`, `KNOWN_LIMITATIONS.md`, `MIGRATION_PLAN_B3.md` | ✓ |

Snapshots intermédiaires conservés : `baseline_B3_groupe_<N>_pre/` (0–6) + `baseline_B3_pre_g7/` + `baseline_B3_post_g6/`.

**Imports déférés** : trois imports dans des fonctions internes d'`app.py` (lignes 496, 843, 1169) avaient été ratés par l'inventaire initial (qui ne scrutait que les imports en début de fichier). Détectés et migrés au moment du G7e via `test_no_declaratif_residual.py` qui en avait un quatrième. Tous corrigés vers leurs cibles canoniques (`core.profil`, `core.ir_foyer`, `strategy.comparateur`, `strategy.synthese`, `strategy.assimile`).

**Hash baseline numérique** : `8863991f27f67847` conservé sans interruption de G1 à G7f.

### 7.4. Hors périmètre v1 (renvoyé v2)

Conformément au Cadre v1.0.1 §10.3 et à `KNOWN_LIMITATIONS.md` :
- Holding patrimoniale et démembrement (L4 étendu)
- SPFPL
- Article 83 historique
- IFI et transmission successorale
- Régimes étrangers / expatriés / frontaliers
- Personnalisation par niveau de maturité utilisateur
- Historique hypothèses détaillé, couche explicative « Pourquoi ce résultat ? »
- IA / recommandations automatiques, scoring prédictif

### 7.5. Phase MODE_AUDIT v1.6 (19/05/2026, 4 régimes + 3 modules stratégie + 2 modules comparateur + 2 modules post-arbitrage + 2 modules transverses épargne)

Première brique d'infrastructure d'explicabilité du moteur. Permet à un cabinet de **lire la traçabilité complète** d'un arbitrage : pour chaque étape de calcul, valeur, hypothèse réglementaire appliquée, doctrine citée, position dans la hiérarchie.

À partir de la spec 1.1.0 (G3a), `TraceAudit` supporte la **composition par sous-traces nommées**. Les stratégies ne réémettent plus les étapes des régimes appelés : elles composent un graphe de traces. La spec a tenu la charge jusqu'à 6 niveaux d'imbrication (G3d-bis) et couvre désormais 10 modules instrumentés avec asymétrie de composition (G3e).

**Principes structurants :**

- **Trace déterministe** : pas de génération narrative, pas d'IA, pas de scoring. La trace est un dump structuré du calcul, lisible programmatiquement (`TraceAudit.get(code)`, `TraceAudit.enfants(code)`, `TraceAudit.get_sous_trace(nom)`) ou via un renderer récursif.
- **Opt-in par appel** : chaque fonction instrumentée accepte un paramètre `audit: TraceAudit | None = None`. Pas de booléen global, pas d'état partagé.
- **Side channel pur** : aucune logique métier déplacée, aucune modification du résultat numérique quand `audit=None`. Rétrocompat parfaite — hash baseline `8863991f27f67847` conservé bout en bout.
- **Codes stables versionnés** : chaque étape porte un identifiant stable. Pour les régimes : `<REGIME>_<DOMAINE>_<ETAPE>`. Pour les stratégies : `STRAT_<REGIME>_<STRATEGIE>_<DOMAINE>_<ETAPE>`. Pour les comparateurs : `COMP_*` (dispositifs) et `COMP_REG_*` (régimes). Pour le post-arbitrage : `SYNTH_*` (synthèse top-niveau) et `SCEN_*` (comparateur 2 scénarios). Pour les transverses épargne : `PERIN_*` (PER individuel) et `RECEPT_*` (matrice §5 d'accessibilité).
- **Espaces de codes isolés** : `TNS_*`, `LIB_BNC_*`, `LIB_SEL_*`, `SAL_*`, `ASSIM_*` (régimes) ⊥ `STRAT_ASSIM_*`, `STRAT_TNS_*`, `STRAT_LIB_*` (stratégies) ⊥ `COMP_*`, `COMP_REG_*` (comparateurs) ⊥ `SYNTH_*`, `SCEN_*` (post-arbitrage) ⊥ `PERIN_*`, `RECEPT_*` (transverses). Détails : `AUDIT_MODE.md` §10.
- **Références doctrinales structurées** : les hypothèses citent des `doctrine_ref` symboliques résolues à la demande côté renderer.
- **Hiérarchie native** : chaque étape porte un `parent_id` optionnel ; le renderer reconstruit l'arbre du calcul.
- **Sous-traces composables (spec 1.1.0)** : les traces sont attachées par référence sous une clé symbolique (`attacher_sous_trace`). Immutabilité après attachement : 4 garde-fous actifs (refus doublons, réattachement, cycle direct, type incorrect). Détails : `AUDIT_MODE.md` §9.
- **Grammaire formelle du graphe** : noms de sous-traces stables et descriptifs (`module_<X>`, `strategie_<CODE>`, `arbitrage_<regime>`, `ligne_<regime>`, `synthese_<regime>`, `couts`/`radar`/`projection`/`decomposition`/`enveloppes`/`checklist`, `scenario_a`/`scenario_b`, `ir_barème`, `tx_ir_moy`, `plafond_dirigeant`/`plafond_conjoint`, `regime_effectif`/`accessibilite`). Vérifiés par les suites de tests. Détails : `AUDIT_MODE.md` §10.4.
- **Non-prescriptif structurellement** : 12 patterns regex (renforcés à 14 en G3e) scannés récursivement sur tous les labels et notes du graphe (test 9 automatique). Wording métier en français préservé en `hypotheses` (champ dict non scanné).

**Bénéfice collatéral observé** : l'instrumentation MODE_AUDIT pousse mécaniquement vers une **centralisation doctrinale** dans `core/profil.py`. En G2a/G2b, 4 constantes ont été promues depuis les régimes vers la couche `core/` (`TX_CSG_DEDUCTIBLE`, `TX_CSG_NON_DEDUCTIBLE`, `PLAFOND_ABAT_10PCT_SAL`, `TX_ABAT_10PCT_SAL`). Une duplication locale (`PLAFOND_ABAT_10PCT_REF` dans `regime/assimile.py`) a été supprimée. L'audit améliore l'architecture métier elle-même. G3e-synthese.4 a en outre **rendu visible une asymétrie d'implémentation** (`_synthese_tns/liberal` allégés vs `_synthese_assimile` pleinement composé) qui n'était pas documentée auparavant. G3f a **révélé une dette d'instrumentation rétroactive** : `strategy/comparateur.py` consomme silencieusement `est_accessible`/`motif_inaccessibilite` sans propager l'audit (documenté dans KNOWN_LIMITATIONS, jalon G3d-ter à programmer si besoin).

**Périmètre v1.6 :**

| Module | Statut | Étapes |
|---|---|---|
| `core/audit.py` (API spec 1.1.0) | ✓ Livré | — |
| Instrumentation `regime/tns.py` | ✓ Livré (G1 historique) | 24 |
| Instrumentation `regime/liberal.py::calcul_module_bnc()` | ✓ Livré (G1a) | 16 |
| Instrumentation `regime/liberal.py::calcul_module_sel()` | ✓ Livré (G1b) | 8 |
| Instrumentation `regime/salarie.py::calcul_module_salarie()` | ✓ Livré (G2a) | 17 |
| Instrumentation `regime/assimile.py::calcul_tx_ir_moyen()` | ✓ Livré (G2b) | 11 |
| Instrumentation `regime/assimile.py::fs_moyen_epargne()` | ✓ Livré (G2b) | 1 |
| Instrumentation `strategy/assimile.py` (1 calcul + 1 arbitrage) | ✓ Livré (G3a) | 7 méta + 4×13 |
| Instrumentation `strategy/tns.py` (4 stratégies + 1 arbitrage, imbrication 2 niveaux) | ✓ Livré (G3b) | 7 méta + 53 stratégies + 4×24 régime |
| Instrumentation `strategy/liberal.py` (4 stratégies + 1 arbitrage, imbrication 3 niveaux L4, branches dynamiques SELARL/SELAS) | ✓ Livré (G3c) | 7 méta + ~35 stratégies + sous-traces variables |
| Instrumentation `strategy/comparateur.py` (autonome, trace plate, namespace `COMP_*`) | ✓ Livré (G3d, 4 sous-passes) | 36 étapes plates |
| Instrumentation `strategy/comparateur_regimes.py` (composition 3 stratégies + module Salarié, **imbrication 6 niveaux**, namespace `COMP_REG_*`) | ✓ Livré (G3d-bis, 3 sous-passes) | 5 méta + 4×7 lignes + sous-traces composées (~412 total) |
| Instrumentation `strategy/synthese.py` (7 fonctions calculs + 1 routeur + 4 sous-fonctions régime, composition asymétrique, namespace `SYNTH_*`) | ✓ Livré (G3e-synthese, 4 sous-passes) | ~155 étapes structurées |
| Instrumentation `strategy/scenarios.py` (3 fonctions, autonome avec composition interne, namespace `SCEN_*`) | ✓ Livré (G3e-scenarios, 2 sous-passes) | 37 étapes (3 niveaux internes) |
| Instrumentation `strategy/perin.py` (2 fonctions, autonome avec composition conditionnelle, namespace `PERIN_*`) | ✓ Livré (G3f-perin, 1 sous-passe) | 7 plates + 12 méta + 2 sous-traces conditionnelles |
| Instrumentation `strategy/receptacles.py` (5 fonctions, autonome avec composition interne 3 niveaux, namespace `RECEPT_*`) | ✓ Livré (G3f-receptacles, 1 sous-passe) | ~16 codes uniques, 3 niveaux internes |
| Renderer console récursif (`ui/audit_render.py`) | ✓ Livré (G3a) | — |
| Suites de tests : **13 fichiers**, 120+ catégories cumulées | ✓ Livré | — |
| Documentation spec + usage (`AUDIT_MODE.md`) | ✓ Livré | — |
| Promotion constantes doctrinales dans `core/profil.py` | ✓ Livré (G2a/G2b) | — |

**Reporté à G3g et au-delà :**

- G3g — Consolidation doc finale + récap global G3. Conditions atteintes : 12 modules instrumentés, 13 suites MODE_AUDIT, grammaire §10.4 stabilisée, spec 1.1.0 inchangée.
- Rendu PDF audit-ready (déclenchable maintenant que G3 est conceptuellement complet)
- G3d-ter — rétro-instrumentation `comparateur.py` → `receptacles.py` (dette documentée, faible priorité)
- Export JSON / sérialisation externe
- Helpers de requête (`find_by_regime`, `total_par_code`)
- Extension `_synthese_tns/liberal` : composition pleine des 6 calculs auxiliaires (post-G3)

Détails complets dans `AUDIT_MODE.md`.

---

## 8. Annexe — Statistiques freeze B.2 + B.2.5 + B.3 finalisée

| Métrique | Valeur |
|---|---|
| Fichiers Python racine avant refactoring (Phase A/B.1) | 11 (logique métier mélangée) |
| Fichiers Python racine après B.2 freeze | 11 modules-ponts + `app.py` + `doctrine.py` + outillage |
| **Fichiers Python racine après B.3 finalisée** | `app.py` + `doctrine.py` + outils baseline + tests + audits (≈25 fichiers, **0 module-pont**) |
| Nouveaux dossiers | `core/`, `regime/`, `strategy/`, `ui/` |
| Nouveaux fichiers métier B.2 | 15 |
| Nouveau fichier B.2.5 | `ui/disclaimers.py` |
| Lignes refactorées | ~3 500 (transposition fidèle, 0 logique modifiée) |
| Validations parité v19 préservées | 504/504 |
| Validations B.2 | 348 (dont 282 tests chiffrés + audits) |
| Validations cumulées au freeze B.2+B.2.5 | 852 |
| Validations cumulées au freeze B.3 finalisée | 852 + 23 (test absence ponts) |
| Patterns sémantiques audités | 9 (`semantic_guardrails.py`) |
| **Modules-ponts restants** | **0** (supprimés en G7d le 19/05/2026) |
| Imports déférés migrés en G7 | 4 (3 dans `app.py`, 1 dans `test_no_declaratif_residual.py`) |
| Régressions détectées tout au long de B.2/B.2.5/B.3 | 0 |
| Hash baseline numérique conservé bout en bout | `8863991f27f67847` |
