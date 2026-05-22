# Limites assumées de la version au freeze B.2

**Date :** 19 mai 2026 — Doctrine v1.0.1 — Dernière revue v1.1.1 (20 mai 2026)

Ce document liste les **limites connues et acceptées** de l'outil dans son état figé en sortie de Phase B.2. Aucune de ces limites n'est un bug : ce sont des choix de périmètre explicites. Elles sont listées ici pour que tout futur contributeur sache où s'arrête le mandat actuel.

---

## 0. Table de bord des dettes (vue v1.1.1)

> **Lecture rapide.** Cette table regroupe l'ensemble des dettes
> connues (techniques, fonctionnelles, doctrinales) et frontières
> assumées de l'outil. Le journal historique des sous-passes
> (sections 6+) reste accessible pour la traçabilité ; cette section 0
> sert de tableau de bord à jour.
>
> **Légende des statuts :**
> - **Active** : dette à traiter ; un correctif ou une décision est
>   attendu(e) à l'horizon cible.
> - **Clôturée** : dette résolue, soit par correctif effectif, soit
>   par décision doctrinale explicite. Conservée ici pour traçabilité.
> - **Frontière** : refus doctrinal assumé. Ne sera jamais traitée
>   en tant que dette ; relève d'un choix de positionnement produit.
>
> **Légende des catégories :**
> - **Fonctionnelle** : porte sur ce que fait (ou ne fait pas) l'outil
>   métier (calculs, scénarios, périmètres réglementaires).
> - **Technique** : porte sur l'infrastructure logicielle (rendu,
>   performance, dépendances, architecture).
> - **Doctrinale** : porte sur le positionnement produit ou les
>   garanties offertes au cabinet.

### 0.1 Dettes clôturées (traçabilité — cumulé v1.1.1 + v1.2)

| ID | Catégorie | Description | Statut | Introduite | Décision | Horizon |
|---|---|---|---|---|---|---|
| **G4-filles** | Technique | Étapes `parent_id != None` non rendues dans le PDF (27-40 % des étapes selon régime) | **Clôturée** v1.1.1 | SP10 | **Décision doctrinale** : les étapes filles sont considérées comme artefacts internes de calcul et non comme unités d'audit cabinet. Engagement de stabilité v1.x. Cf. `ARCHITECTURE_RENDERER.md` §2.1. | Stable v1.x |
| **Unicode-glyphes** | Technique | Glyphes non-latins (émojis, RTL, CJK) rendus comme rectangles noirs (fontes PDF standard) | **Clôturée** v1.1.1 | SP12 | **Décision doctrinale** : le renderer garantit la stabilité du PDF en présence de glyphes non supportés, mais pas leur restitution visuelle. Comportement testé en P2 (`test_renderer_stress.py`). | Stable v1.x |
| **REC-D7** | Fonctionnelle | Couche UI Streamlit du module réceptacles (3 phases : lecture cabinet, auditabilité visible, navigation audit) | **Clôturée** v1.2 | post-SP19 | **Livrée intégralement** : SP20 (Lecture cabinet) + SP21 (Auditabilité visible) + SP22 (Navigation audit). 10 anti-patterns + 2 bis gravés en doctrine, 6 invariants UI testés (UI-I1 à UI-I6), 43 contrôles automatisés. | Stable v1.x |

### 0.2 Dettes actives (planifiées)

| ID | Catégorie | Description | Statut | Introduite | Décision | Horizon |
|---|---|---|---|---|---|---|
| **REC-D1** | Fonctionnelle | Rattrapages PERIN N-1/N-2/N-3 non modélisés (versement année courante seulement) | Active | SP13 §10.3 | Report v1.2 si validé | v1.2 |
| **REC-D2** | Fonctionnelle | Sortie en rente PERIN/PERECO non modélisée (sortie capital seule en v1.1) | Active | SP15 Q1 | Report v1.2 si validé | v1.2 |
| **REC-D3** | Fonctionnelle | Plafond spécifique PERECO 16 % PASS non modélisé (8 % PASS aligné PEE retenu en v1.1) | Active | SP17 Q1 | Report v1.2 si validé | v1.2 |
| **REC-D4** | Fonctionnelle | Déblocages anticipés PEE/PERECO non modélisés (mariage, naissance 3e enfant, achat RP, etc.) | Active | SP13 §4 | Report v1.2 si validé | v1.2 |
| **REC-D5** | Fonctionnelle | Transferts inter-PER non modélisés | Active | SP13 §4 | Report v1.2 si validé | v1.2 |
| **REC-D6** | Fonctionnelle | Autres enveloppes (assurance-vie, CTO, immobilier locatif) hors périmètre v1.1 | Active | SP13 §4 | Report v1.2+ après priorisation cabinet | v1.2+ |
| **DOC-D1** | Doctrinale | Pas d'historique des hypothèses réglementaires (PASS, plafonds, barèmes IR à un instant donné, pas de comparaison inter-exercices) | Active | Pré-B.2.5 | Report v1.2+ | v1.2+ |
| **DOC-D2** | Technique | Pas d'audit UX couleurs (rendu PDF et UI Streamlit non testés pour lisibilité N&B ni daltonisme) | Active | Pré-B.2.5 | Report v1.2+ | v1.2+ |
| **DOC-D3** | Fonctionnelle | Pas de couche explicative « Pourquoi ce résultat ? » (l'outil restitue, ne raisonne pas) | Active | Pré-B.2.5 | Report v1.2+ | v1.2+ |

### 0.3 Frontières doctrinales assumées (jamais à traiter en tant que dette)

| ID | Catégorie | Description | Statut | Introduite | Décision | Horizon |
|---|---|---|---|---|---|---|
| **FRONT-1** | Doctrinale | **Absence de moteur de recommandation/prescription.** L'outil aligne et restitue de manière descriptive ; il ne classe pas, ne recommande pas, ne préconise pas, ne calcule pas de score, indice, ranking, efficacité ni performance. La décision reste cabinet. | **Frontière** | SP13 D-R12 + SP18 garde-fous | **Refus doctrinal explicite.** Cette frontière sera maintenue pour toute la branche v1.x et v2.x. Toute remise en question relève d'un repositionnement produit majeur (changement de mandat). | Indéfini |

**Justification de FRONT-1 :** le produit est volontairement descriptif. Introduire un moteur prescriptif transformerait l'outil en système d'aide à la décision, avec un régime juridique et déontologique différent (conseil financier). Cette frontière est gardée par :
- D-R12 (`ARCHITECTURE_RECEPTACLES.md`) : « pas de dimensionneur, pas de prescription »
- D-R6 (idem) : « orchestrateur passif »
- 14 patterns proscrits (`doctrine.py` §6.2) testés à chaque commit
- Test SP18 16.5 : « aucun mot interdit dans le contenu visible »
- Test SP19 Récep-6.1 : idem au niveau PDF rendu réceptacles

Toute évolution future qui érode cette frontière (même implicitement, par exemple via un « score global » ou un « indicateur de performance ») doit être traitée comme une **rupture doctrinale** et faire l'objet d'une délibération produit explicite.

### 0.5 Chantiers documentés (activés via C6 ou non activés)

Cette catégorie matérialise les chantiers ayant fait l'objet d'une
**doctrine préparatoire** produite avant tout développement. Deux
statuts possibles :

- **Documenté non activé** : doctrine produite, chantier non
  déclenché (statut SP23 initial pour PERO-D0)
- **Activé via C6** : doctrine produite, puis chantier activé via
  critère C6 « Maturité systémique du framework »
  (§13.2b d'`ARCHITECTURE_PERO.md`), avec journal d'activation
  formel point-par-point

L'objectif est de capitaliser sur la mémoire méthodologique
(patterns, frontières, invariants) **avant** tout cycle de
construction, puis d'activer formellement quand les conditions
sont vérifiées (signaux terrain C1-C5 ou maturité système C6).

| ID | Catégorie | Description | Statut | Introduite | Décision | Horizon |
|---|---|---|---|---|---|---|
| **PERO-D0** | Fonctionnelle | Chantier de modélisation du PERO (Plan d'Épargne Retraite Obligatoire) comme 4e enveloppe du module Réceptacles. Doctrine complète (statut, nature économique, tableau différentiel PERIN/PERECO/PERO, frontières négatives, conventions France 2026, sémantique économique, anti-patterns P1-P5, cohabitation historique, pré-cadrages SP24/SP25/SP26 indicatifs, 5 dangers transversaux, conditions de réactivation §13.2a/§13.2b avec C6 + clause anti-abus + journal d'activation §13bis). | **SP26 livrée — chantier clôturé (POC cabinet-ready)** | post-SP22 | **SP23** doctrine préparatoire (~1091 lignes). **SP23-bis** activation via C6 (§13bis). **SP24** module métier livré (`strategy/receptacles_pero.py`, 73 contrôles, 1 mini-golden). **SP25** orchestration intégrée (`ResultatAllocationReceptacles.pero`, `ENVELOPPES_V1_3`, RECAP étendus à 4, étape `REC_PERO_INPUTS_LUS_PROFIL`). **SP26 (mai 2026)** UI + PDF audit cabinet-ready : `ui/adapter_receptacles.py::ORDRE_DOCTRINAL_ENVELOPPES` étendu à 4 (désynchronisation SP25 refermée), mappings `resultats_par_enveloppe` étendus, `sous_traces_attendues` étendu, `enveloppes_dans_ordre_doctrinal()` retourne 4 enveloppes. `ui/composants_receptacles.py::saisir_inputs_orchestrateur` ajoute le widget `taux_cotisation_pero` (number_input, max 10%, step 0.25%, défaut 0%). `ui/page_receptacles.py` injecte `taux_cotisation_pero` dans le profil avant appel orchestrateur. `test_ui_receptacles_neutralite.py` étendu : section SP26 (7 contrôles cardinalité + absence wording PERO-spécifique + absence composant spécifique). PDF audit Réceptacles inchangé (la trace orchestrateur contenait déjà PERO depuis SP25, golden Réceptacles PDF régénéré en SP25). **Chantier PERO complet : moteur + orchestration + UI + audit.** | v1.3 |

**Lecture du statut « SP26 livrée — chantier clôturé (POC cabinet-ready) » :**

- Distinct de **Documenté non activé** (statut initial PERO-D0
  en SP23) : la doctrine n'est plus seulement de référence.
- Distinct de **Activé via C6 (SP23-bis)** : le développement
  a été conduit jusqu'à son terme.
- Distinct de **SP24 livrée** / **SP25 livrée** : intégration UI
  + PDF audit cabinet-ready livrée. Désynchronisation volontaire
  SP25 levée (`ORDRE_DOCTRINAL_ENVELOPPES` adapter UI aligné à
  4 enveloppes comme l'orchestrateur).
- Distinct de **Active** (au sens §0.2) : PERO-D0 reste en §0.5
  parce que sa **trajectoire doctrinale** est sa caractéristique
  principale (doctrine antérieure au code, gouvernance C6).
- Distinct de **Clôturée** (au sens §0.3) : le chantier est
  fonctionnellement complet et démontrable cabinet, mais reste
  en §0.5 par cohérence avec la trajectoire doctrinale. Une
  bascule éventuelle vers §0.3 (clôturée) sera décidée par le
  décisionnaire produit selon usages cabinet observés.
- Distinct de **Frontière** : la modélisation a été réalisée
  intégralement (4 sous-passes SP24 → SP26).

**Documents de référence (post-clôture SP26) :**
- `ARCHITECTURE_PERO.md` à la racine (~1312 lignes, doctrine
  v0.2, SP23+SP23-bis figées)
- `strategy/receptacles_pero.py` (SP24, ~700 lignes)
- `test_strategy_receptacles_pero.py` (SP24, 73 contrôles)
- `golden_metiers/pero_standard_80k_3pct.json` (SP24)
- `golden_metiers/orchestrateur_composition_pero_actif.json` (SP25)
- `core/profil.py` : champ `taux_cotisation_pero=0.0` (SP25, b1)
- `strategy/receptacles_orchestrateur.py` : ENVELOPPES_V1_3,
  ResultatAllocationReceptacles.pero, RECAP étendus (SP25)
- `ui/adapter_receptacles.py` : ORDRE_DOCTRINAL_ENVELOPPES à
  4 enveloppes, mappings étendus (SP26)
- `ui/composants_receptacles.py` : widget taux_cotisation_pero
  dans saisir_inputs_orchestrateur (SP26)
- `ui/page_receptacles.py` : injection taux dans profil (SP26)
- `test_ui_receptacles_neutralite.py` : section SP26 (SP26-1 à
  SP26-7, +7 contrôles)
- Wordings PERO dans `strategy/receptacles_wordings.py` (6 wordings)

**Référence croisée :** ce document est cité par
`ARCHITECTURE_PERO.md` §14 (références croisées) qui le relie à
`ARCHITECTURE_RECEPTACLES.md`, `ARCHITECTURE_RENDERER.md`,
`ARCHITECTURE_UI_RECEPTACLES.md`.

**Garde-fou technique §13.6 (status post-SP26) :** PERO-D0 est
marquée « SP26 livrée — chantier clôturé (POC cabinet-ready) ».
Le chantier est **complet de bout en bout** : moteur (SP24) +
orchestration (SP25) + UI/PDF audit (SP26). La discipline SP1-SP23
a été préservée tout au long (cadrage Q1-Qn formel par sous-passe,
batterie complète à chaque étape, hash baseline `8863991f27f67847`
strictement inchangé, 0 régression sur le périmètre figé v1.0.1).

### 0.4 Indicateurs de gouvernance (v1.2 — fin, mis à jour SP23-bis)

| Indicateur | Valeur |
|---|---|
| Dettes clôturées en v1.1.1 | 2 (G4-filles, Unicode-glyphes) |
| Dettes clôturées en v1.2 | 1 (REC-D7 UI Réceptacles, livrée par SP20+SP21+SP22) |
| Total dettes clôturées | 3 |
| Dettes actives | 9 (REC-D1 à REC-D6 + DOC-D1 à DOC-D3) |
| Frontières doctrinales | 1 (FRONT-1) |
| **Chantiers documentés activés via C6** | **1 (PERO-D0, activé SP23-bis, développement SP24-SP26 à venir)** |
| Chantiers documentés non activés | 0 |
| Total entrées table de bord | 14 |
| Tests cumulés au vert (post-v1.2 + SP23 + SP23-bis + SP24 + SP25 + SP26) | 846 contrôles + 6 goldens PDF + 7 mini-goldens métier |
| Régressions sur baseline v1.0.1 | 0 |

---

## 1. Périmètre fonctionnel

### Régimes couverts

✓ Assimilé salarié (SAS/SASU)
✓ TNS classique (SARL gérant majoritaire, EURL, EI)
✓ Libéral (BNC, SELARL gérant TNS, SELAS président Assimilé) — niveaux L1 à L4
✓ Salarié (référence comparative, parité Excel v19)

✗ **Holding / SPFPL** : non couvert. Demande un mandat séparé.
✗ **Régime micro-entreprise** : non couvert.
✗ **Pluriactivité** (TNS + salarié simultané, indépendant + dividendes étrangers, etc.) : non couvert.

### Stratégies couvertes

✓ Assimilé : A (salaire seul), B (mix salaire + dividendes), C (dividendes seuls), D (mix avec PERIN)
✓ TNS : 4 stratégies équivalentes + garde-fou T4 (non-agrégation)
✓ Libéral : L1 à L4 avec alerte BNC/SEL et garde-fous spécifiques

✗ **Stratégies avec démembrement, OBO, apport-cession** : non couvertes.
✗ **Optimisation par holding** : non couverte.

---

## 2. Limites méthodologiques

### Garde-fou T4 (TNS)

**Limite assumée :** Le résultat TNS est restitué en **deux indicateurs séparés** (`net_dirigeant_immediat` et `benefice_retenu_societe`), **jamais en somme**. Cela protège contre la fausse comparabilité entre un revenu disponible immédiatement et un bénéfice qui resterait dans la société.

Conséquence : un utilisateur pressé peut être tenté d'additionner mentalement les deux. C'est documenté dans le PDF mais reste une charge cognitive pour le lecteur. **Aucune simplification ne sera apportée tant que cela contredit la doctrine.**

### Alerte BNC/SEL (Libéral L3/L4)

**Limite assumée :** En L3 (SELARL) et L4 (SELAS), l'outil émet systématiquement une alerte de comparabilité BNC/SEL. **Aucun « régime recommandé » n'est jamais affiché** pour ces niveaux, même si les chiffres sont nettement favorables à l'un ou l'autre.

Conséquence : l'utilisateur libéral en exercice mixte BNC/SEL doit lire les chiffres comme un cadrage, pas comme une recommandation. C'est intentionnel.

### Comparateur Option 2

- 15 lignes max, 1 alerte par défaut sur le cas Assimilé défaut
- Pas de simulation pluriannuelle au-delà de la projection 5 ans existante
- Pas de Monte-Carlo, pas de stochastique

### Niveaux de précision (4 niveaux v1.0.1)

- `Conformité renforcée` — niveau cabinet, traçabilité maximale
- `Avancé` — niveau intermédiaire (sémantique précisée dans `TERMINOLOGY.md`)
- `Cadrage` — niveau indicatif structuré
- `Indicatif` — niveau dégrossissage

**Limite assumée :** le niveau « Avancé » a un sens technique précis qui n'était pas évident à la première lecture du code. Le choix retenu en B.2.5 est de **documenter sans migrer**. Pas de renommage, pas de fusion de niveaux.

### Disclaimers

**Limite assumée :** approche hybride :
- `ui/disclaimers.py` (créé en B.2.5) centralise uniquement les disclaimers de **présentation** (Primauté cabinet, AMF Comparateur patrimonial, Avertissement final).
- Les **alertes métier** (`ALERTE_BNC_VS_SEL`, `DISCLAIMER_CHANGEMENT_REGIME`, `DISCLAIMER_COMPARABILITE`, `NOTE_RADAR_INTRA_REGIME`) **restent dans `strategy/`** parce qu'elles sont nécessaires aux calculs et au filtrage des résultats.

Cela impose à tout nouveau disclaimer de décider explicitement de quelle catégorie il relève.

---

## 3. Limites techniques

### `app.py` migré en B.3 (limite levée)

`app.py` (Streamlit, ~1500 lignes) **a été migré** vers les couches canoniques en Phase B.3 (terminée 19/05/2026). Les 11 modules-ponts racine ont été supprimés en G7d. `app.py` n'importe désormais que `core.*`, `regime.*`, `strategy.*`, `ui.*` et `doctrine`. Le test `test_backward_compat_imports.py` (réécrit en G7c) vérifie que les ponts restent absents.

### Tests `test_parite_salarie.py` et `test_scenarios.py`

Ces deux tests **dépendent de la présence physique de `/home/claude/outil_v19.xlsx`** (Excel de référence v19 dont les cellules servent de cibles). Ils régénèrent leurs cibles via LibreOffice headless à chaque exécution.

**Conséquence :** sans le fichier Excel v19 et sans LibreOffice installé, 172 validations (84 Salarié + 88 Scénarios) ne peuvent pas être reproduites. Les autres 680 validations restent reproductibles sans cette dépendance.

Un futur travail pourrait gérer ces tests en mode dégradé (comparaison contre `cibles_salarie.json` / `cibles_scenarios.json` figées), mais cela n'a pas été fait en B.2 pour garder l'Excel comme source de vérité unique.

### MODE_AUDIT v1.6 — 4 régimes + 3 stratégies + 2 comparateurs + 2 post-arbitrage + 2 transverses épargne

**État actuel (19/05/2026) :** MODE_AUDIT v1.6 instrumente **les 4 régimes, 3 modules stratégie, 2 modules comparateur, 2 modules post-arbitrage et 2 modules transverses épargne**. La spec 1.1.0 (sous-traces composables) couvre jusqu'à 6 niveaux d'imbrication.

**Finalisation G3g (19/05/2026) :** doctrine G3 figée dans
`MODE_AUDIT_G3_FINAL.md` (référence stable pour PDF audit-ready et
usages cabinet). Ce document `KNOWN_LIMITATIONS.md` reste vivant et
trace les évolutions ultérieures.

Couvert :
- API stable spec 1.1.0 `core/audit.py` (`TraceAudit`, `EtapeAudit`, `resoudre_doctrine_ref`, `attacher_sous_trace`)
- Instrumentation `regime/tns.py` (24 étapes, codes `TNS_*`)
- Instrumentation `regime/liberal.py` :
  - `calcul_module_bnc()` (16 étapes, codes `LIB_BNC_*`)
  - `calcul_module_sel()` (8 étapes, codes `LIB_SEL_*`)
- Instrumentation `regime/salarie.py::calcul_module_salarie()` (17 étapes, codes `SAL_*`)
- Instrumentation `regime/assimile.py` (2 helpers, codes `ASSIM_*`)
- Instrumentation `strategy/assimile.py` (G3a, codes `STRAT_ASSIM_*`)
- Instrumentation `strategy/tns.py` (G3b, codes `STRAT_TNS_*`, imbrication 2 niveaux)
- Instrumentation `strategy/liberal.py` (G3c, codes `STRAT_LIB_*`, imbrication 3 niveaux sur L4, branches dynamiques SELARL/SELAS)
- Instrumentation `strategy/comparateur.py` (G3d, codes `COMP_*`, 36 étapes plates, module autonome)
- Instrumentation `strategy/comparateur_regimes.py` (G3d-bis, codes `COMP_REG_*`, 412 étapes structurées, **imbrication 6 niveaux**)
- Instrumentation `strategy/synthese.py` (G3e-synthese, codes `SYNTH_*`, ~155 étapes structurées, **composition asymétrique**)
- Instrumentation `strategy/scenarios.py` (G3e-scenarios, codes `SCEN_*`, 37 étapes, module autonome avec composition interne 3 niveaux)
- Instrumentation `strategy/perin.py` (G3f-perin, codes `PERIN_*`, 7 plates + 12 méta + 2 sous-traces conditionnelles)
- Instrumentation `strategy/receptacles.py` (G3f-receptacles, codes `RECEPT_*`, ~16 codes uniques, composition interne 3 niveaux)
- Renderer console récursif (`ui/audit_render.py`)
- **13 suites de tests dédiées** (120+ catégories cumulées) incluant **test 9 non-prescriptif renforcé** (14 patterns à partir de G3e)
- Spec et guide d'usage (`AUDIT_MODE.md`)
- Grammaire formelle du graphe d'audit (table §10.4 stabilisée, 4 grandes familles + 2 transverses)
- 4 constantes promues dans `core/profil.py` (`TX_CSG_DEDUCTIBLE`, `TX_CSG_NON_DEDUCTIBLE`, `PLAFOND_ABAT_10PCT_SAL`, `TX_ABAT_10PCT_SAL`)

**Limites assumées en v1.6 :**
- `_synthese_tns/_synthese_liberal` : **implémentation allégée v1** dans le code source. Ces fonctions ne réutilisent pas les 6 calculs auxiliaires de l'Assimilé (`couts_mise_en_oeuvre`, `radar_6d`, `projection_5_ans`, `decomposition_gain`, `enveloppes_patrimoniales`, `checklist_conformite`). La trace MODE_AUDIT documente cette asymétrie (0 sous-trace côté TNS/Libéral vs 6 côté Assimilé). Extension pleine reportée post-G3.
- **Dette d'instrumentation rétroactive G3d-ter** : `strategy/comparateur.py` (G3d) consomme silencieusement `est_accessible` et `motif_inaccessibilite` depuis `strategy/receptacles.py` (lignes 232-234 du source comparateur). Les appels ne propagent pas l'audit, donc la composition n'apparaît pas en sous-trace `receptacles` au niveau du comparateur. Module receptacles instrumenté indépendamment et entièrement utilisable en appel isolé. Rétro-instrumentation reportée à un jalon dédié (G3d-ter) si besoin réel — valeur ajoutée immédiate faible (3-4 appels max selon config).
- ~~Pas de rendu PDF audit-ready~~ → **limite levée en sortie SP5** (cf. § PDF audit-ready v1.0.0 ci-dessous). Pilote TNS livré ; SP7-SP8 étendront aux autres régimes.
- Pas d'export JSON / sérialisation externe
- Détection des cycles indirects (A → B → A) dans le graphe de sous-traces **non assurée** en spec 1.1.0 — éviter par convention (structure arborescente)

Roadmap d'extension dans `AUDIT_MODE.md` §6.2.

### MODE_AUDIT v1.6 → PDF audit-ready v1.0.0 (SP1-SP5)

**État actuel (20/05/2026) :** Renderer PDF audit-ready livré pour le
**pilote TNS** (`arbitrage_complet_tns`). Constantes :

- `AUDIT_PDF_SPEC_VERSION = "1.0.0"` (spec du renderer, dans
  `ui/pdf_audit_export.py`)
- Indépendante de `AUDIT_SPEC_VERSION = "1.1.0"` (spec du graphe
  d'audit, dans `core/audit.py`)
- Hash baseline `8863991f27f67847` conservé bout-en-bout

**Architecture livrée (SP1 → SP5)** :

| Élément | Choix | Motif |
|---|---|---|
| Renderer | **ReportLab natif** (Platypus) | Continuité avec `ui/pdf_export.py` (Phase A/B.2 Étape 6), même charte. Pas de dépendance lourde nouvelle. |
| Pas WeasyPrint | Volontairement écarté | Aucune valeur ajoutée sur traces hiérarchiques. PDF n'a pas de « responsive ». Évite Pango + Cairo. |
| Pagination (schéma S2) | **Page par sous-trace N1**, N2 enchaîné | « Une stratégie = une section ». Lisibilité cabinet sans pagination excessive. |
| Sommaire | `TableOfContents` natif ReportLab, **2 niveaux**, `multiBuild()` double passe | Numéros de page corrects. Lignes pointillées. Hiérarchie N0 bold / N1 indenté. |
| Signets PDF | Hiérarchisés N0/N1 via `canvas.bookmarkPage` + `addOutlineEntry` | Navigation lecteur PDF (Acrobat/Foxit) dépliable. 1 signet par sous-trace, **pas par étape** (sinon 1187 signets, illisible). |
| Seuil hypothèses longues | **80 caractères** | Calibré sur trace TNS pilote (3 hypothèses dépassent : `tous_nets`, `note_perin`, `texte_alerte_v19`). Toutes des wordings métier figés §6.4 doctrine. |
| Doctrine_refs | Ligne `colspan 4` sous l'étape, **gris 7pt italique** | Densité maximale + différenciation visuelle nette vs étape. |
| Hypothèses < 80 chars | Ligne `colspan 4` sous l'étape, 8pt italique | Lecture directe sous la valeur calculée. |
| Hypothèses ≥ 80 chars | **Encadré dédié** sous le tableau, bordé fond gris clair, 9pt justifié | Reproduction verbatim des wordings métier (alertes, mentions). |
| Notes | Ligne `colspan 4` italique gris 8pt | Idem hypothèses courtes. |
| Override doctrine vs hypothèse | Mention texte **« override local : valeur appliquée X vs doctrine Y »**, sans icône | Q2 = β arbitré : pas d'icône `⚠` (risque de glyph manquant). L'icône reste à la console pour debug. |
| Largeurs de colonnes | **Calibrage dynamique** (SP7) : `pdfmetrics.stringWidth` + bornes min/max neutres | SP1-SP6 utilisait `[60, 51, 50, 13]` mm figés. SP7 calcule dynamiquement les largeurs en fonction des contenus réels de la trace, avec bornes (Code [45-75], Libellé [35-80], Valeur [30-60], Unité [12-18] mm). Évite tout wrap sur codes ≥ 35 chars. Neutre vis-à-vis du régime — itère sur les longueurs littérales sans connaître le namespace. |
| Panel KPI couverture | **Table 2×2** sobre cabinet-style EY/KPMG | 4 indicateurs : étapes / sous-traces / doctrine_refs distinctes / hypothèses. Pas d'icône, pas de gros chiffres colorés, pas d'effet SaaS. |
| Bandeau intro sommaire | Paragraphe `callout` pédagogique | Distinct des disclaimers v1.0.1 (qui restent juridiques en clôture). |

**Couverture v1.0.0 (pilote TNS)** :

- ✓ Régime TNS via `arbitrage_complet_tns(Profil())` — 156 étapes
  tracées, 8 sous-traces, 11 doctrine_refs distinctes, 114 hypothèses,
  ~13 pages PDF, ~40 ko
- ✓ Garde-fou T4 visuellement préservé (`STRAT_TNS_INDICATEURS_SEPARES`
  rendu en étape distincte avec libellé explicite — convention
  non-agrégation §7.10 doctrine)
- ✓ 14 patterns non-prescriptifs §6.2 scannés sur le texte généré
  par le renderer (hors disclaimer figé « recommandée » whitelisté)
- ✓ Branches mockées testées : override doctrine, référence
  doctrinale introuvable
- ✓ Test dédié `test_pdf_audit_render_tns.py` : **93/93 contrôles**

**Périmètre NON couvert en v1.0.0 (extensions ouvertes)** :

- ~~Régime Assimilé (`arbitrage_complet`)~~ → **limite levée SP7** (cf. § ci-dessous)
- ~~Régime Libéral (`arbitrage_complet_liberal`) — BNC + SEL~~ → **limite levée SP7** (cf. § ci-dessous)
- ~~Comparateur multi-régimes (`comparateur_regimes`)~~ → **limite levée SP8** (cf. § ci-dessous). Schéma S2 maintenu (bascule S3 non requise).

La signature publique `generer_pdf_audit(trace, ...)` est **stable**
depuis SP1. SP7-SP8 ont branché les nouvelles traces racines sans
modification du renderer ni de la signature.

**Limites assumées en v1.0.0** :

- **Extraction pdfplumber sur cellules wrappées** : ReportLab fait du
  word-wrap automatique au sein des cellules `Paragraph` si le contenu
  dépasse la colonne. **Depuis SP7**, le calibrage dynamique des
  col_widths élimine quasi totalement les wraps sur les codes (vérifié
  sur les 5 codes ≥ 35 chars du Libéral). Les libellés courants (≤ 80
  chars) peuvent encore wrapper sur 2-3 lignes, ce qui est attendu et
  visuellement acceptable. Helper `_normaliser_texte_pdf` dans les
  tests pour comparaisons robustes en cas de wrap résiduel.
- **Pas de génération d'images / charts dans le PDF audit** : le
  renderer audit-ready se borne à la restitution tabulaire du graphe.
  Les visualisations métier (radar, projection 5 ans) restent
  exclusivement dans le PDF synthèse (`ui/pdf_export.py`), inchangé.
- **Pas d'export JSON parallèle** : le PDF audit est le seul livrable
  documentaire de cette v1.0.0. Export JSON sérialisé pour exploitation
  programmatique reporté (cf. spec MODE_AUDIT §8.4 backlog).
- **Décisions de pagination figées** : le saut de page par sous-trace
  N1 peut produire des pages courtes si une stratégie n'a que peu
  d'étapes (ex. SP3 a généré des pages avec une seule étape racine
  visible avant le break suivant). Acceptable pour le pilote ; sera
  réévalué en SP8 quand la profondeur 5 du comparateur_regimes
  imposera probablement de basculer vers le schéma S3 (annexes
  paginées).
- **Modification d'un audit de référence** : `WHITELIST_FICHIERS` de
  `test_no_declaratif_residual.py` étendue avec `"ui/pdf_audit_export.py"`
  (avec feu vert explicite en SP1). Précédent : la même whitelist
  contenait déjà `"ui/pdf_export.py"` pour la même raison technique
  (résolution de l'alias legacy via `_normaliser_niveau()`).

**Tests SP6 (clôture pilote) :**

- `test_pdf_audit_render_tns.py` : 93/93 contrôles, 18 sections.
- `test_pdf_render_all_regimes.py` (PDF synthèse historique) :
  **64/64 inchangé** — option B (deux renderers indépendants) tenue.
- `compare_baseline.py` : 16/16 OK, hash `8863991f27f67847` inchangé.
- 13 suites MODE_AUDIT, 4 audits sémantiques, baseline_tests 7/7 :
  tous verts.

### MODE_AUDIT v1.6 → PDF audit-ready v1.0.0 (SP7 : extension Assimilé + Libéral)

**État actuel (20/05/2026) :** Le renderer `generer_pdf_audit()` (signature
inchangée depuis SP1) couvre désormais **3 régimes** :

- ✓ **TNS** (pilote de référence, figé SP6 — 93/93)
- ✓ **Assimilé** (`arbitrage_complet`) — 70 étapes, 5 sous-traces,
  graphe plat (profondeur 1) — 71/71 contrôles
- ✓ **Libéral** (`arbitrage_complet_liberal`), 2 branches :
  - **SELARL** → 136 étapes, 9 sous-traces, profondeur 3
  - **SELAS**  → 122 étapes, 9 sous-traces, profondeur 3
  - 148/148 contrôles cumulés

**Méthodologie SP7 (à conserver pour SP8) :**

1. **Phase 1 — Diagnostic sans modification** : générer les 3 PDF avec le
   renderer figé, observer les écarts, classer en (i) cosmétique tolérable,
   (ii) défaut de rendu, (iii) défaut de robustesse.
2. **Phase 2 — Corrections neutres uniquement** : ne traiter que (ii) et
   (iii), toujours par paramétrage neutre (jamais `if regime == ...`).
3. **Tests factorisés** : helper commun `test_pdf_audit_render_common.py`
   pour les assertions transverses ; tests dédiés par régime pour les
   propriétés spécifiques.

**Modifications techniques SP7 (1 seule correction) :**

| Modification | Motif | Impact |
|---|---|---|
| Calibrage dynamique des col_widths (`_calibrer_col_widths`) | Défaut D1 du diagnostic : code Libéral `STRAT_LIB_L4_ALERTE_STRUCTURATION_V2_NB` (39 chars) wrappait sur 2 lignes avec les largeurs figées | Neutre. Mesure stringWidth réelle + bornes min/max. TNS conserve 93/93. Aucune régression. |

**Écarts tolérés (cosmétique non corrigée) :**

- Wording « Détail » uniforme pour toutes les sous-traces de profondeur
  ≥ 1 (alors que profondeur 2-3 mériterait conceptuellement « Sous-détail »
  ou similaire). Cas Libéral L4 → strategie_l3_deleguee → module_tns
  affiche deux entrées « Détail » alors qu'elles sont à des profondeurs
  différentes dans le graphe. **Lisible cabinet, tolérance assumée.**
- Sommaire plafonné à 2 niveaux d'indentation (`min(niveau_toc + 1, 1)`).
  Sur Libéral L4 (profondeur 3), `module_tns` apparaît au même niveau
  visuel que `strategie_l3_deleguee` dans le sommaire alors qu'il en
  est l'enfant. **Décision SP3 préservée — anticipe SP8 où profondeur 5
  rendrait un sommaire à 5 niveaux illisible.**
- Sous-traces utilitaires (ex. `tx_ir_moy` côté Assimilé) traitées
  visuellement comme des stratégies. **Neutre par design.**

**Helper commun `test_pdf_audit_render_common.py` (contrat de neutralité) :**

10 sections d'assertions transverses appelées identiquement par les
3 tests régimes :
1. `section_pdf_valide` — magic, taille, EOF
2. `section_couverture` — titre, régime, client, hash
3. `section_kpis_couverture` — 4 KPIs + valeurs
4. `section_bandeau_intro_sommaire` — texte cabinet, position
5. `section_sommaire_pagine` — itération sur `noms_sous_traces()`, numéros de page
6. `section_signets_hierarchises` — outline PDF + hiérarchie selon profondeur
7. `section_no_declaratif` — garde-fou critique
8. `section_14_patterns_non_prescriptifs` — doctrine §6.2
9. `section_neutralite_structurelle` — méta-assertion (titre = `trace.regime`,
   chaque sous-trace N1 a sa section, KPIs cohérents avec comptage récursif)
10. `section_calibrage_dynamique` — vérifie 0 wrap sur codes ≥ 35 chars

### MODE_AUDIT v1.6 → PDF audit-ready v1.0.0 (SP8 : extension comparateur multi-régimes)

**État actuel (20/05/2026) :** Le renderer `generer_pdf_audit()` (signature
inchangée depuis SP1) couvre désormais **l'ensemble du périmètre
stratégies du dépôt MODE_AUDIT v1.6** :

- ✓ **TNS** (pilote de référence, figé SP6 — 93/93)
- ✓ **Assimilé** — 70 étapes, profondeur 1 — 71/71
- ✓ **Libéral** SELARL + SELAS — 122-136 étapes, profondeur 3 — 148/148
- ✓ **Comparateur multi-régimes** (`comparateur_regimes`) — **412 étapes,
  30 sous-traces, profondeur effective 5** — **83/83**

**Total tests PDF audit-ready cumulés : 395/395 contrôles, 0 régression.**

**Méthodologie SP8 (identique à SP7) :**

1. **Phase 1 — Diagnostic sans modification** : génération du PDF avec
   le renderer SP7, observation des écarts, classification.
2. **Phase 2 — Corrections neutres uniquement** : 1 seule modification
   ciblée (`spaceBefore N0` du style TOC : 4 → 2 pt) ; statu quo sur
   tous les autres aspects (wording, plafond TOC, pagination S2).
3. **Test factorisé** : `test_pdf_audit_render_comparateur_regimes.py`
   utilise le helper commun + 13 sections spécifiques (structure
   4 régimes, profondeur 5, volumétrie, codes namespace tous régimes,
   code 41 chars, pagination sommaire, hypothèses longues).

**Modifications techniques SP8 (2 modifications de portée minimale) :**

| Modification | Motif | Impact |
|---|---|---|
| `_styles_toc()` : `spaceBefore` N0 réduit de 4 → 2 pt | Défaut D8.1 du diagnostic : sommaire comparateur_regimes (33 entrées) débordait sur une page 3 quasi vide avec 1 ligne orpheline (« Détail module_salarie ») | Le sommaire tient désormais sur 1 page pour tous les régimes. TNS conserve 93/93, gain de 1 page sur Assimilé/Libéral, gain de 1 page sur comparateur (34 → 33 pages total). |
| `PATTERNS_EXCEPTION_DISCLAIMER` dans helper test commun : ajout de 3 chaînes anti-prescriptives portées par `comparateur_regimes` (`"meilleur net dirigeant"`, `"recommandation automatique de changement de statut"`, `"(non recommandée)"`) | Ces wordings sont issus des hypothèses `note_source` et `NOTE_RECOMMANDATION` du comparateur — ce sont des mentions **anti-prescriptives explicites** (« non recommandée », « pas de recommandation automatique ») qui mettent en œuvre la doctrine non-prescriptive. Whitelistées au niveau dépôt par `semantic_guardrails.py` mais pas par la whitelist plus restrictive du helper PDF. | Aucun impact sur le renderer. Étend la whitelist du helper de test pour reconnaître les mêmes contextes que `semantic_guardrails.py`. Chaînes précises (pas de regex large). |

**Décisions architecturales SP8 (validées) :**

- **Schéma S2 maintenu** : avec 33 pages et un sommaire qui tient sur
  1 page, S2 reste lisible cabinet. Bascule éventuelle vers S3
  (annexes paginées) reportée en v1.1+ uniquement si retours cabinet
  l'exigent.
- **Plafond TOC à 2 niveaux maintenu** : sur graphe profondeur 5,
  toutes les sous-traces ≥ N1 sont aplaties à N1 dans le sommaire et
  les signets. Acceptable pour une lecture cabinet (la navigation
  reste fonctionnelle) ; un sommaire à 5 niveaux serait illisible.
- **Wording « Détail » uniforme maintenu** : pas de distinction
  visuelle entre N1, N2, N3 effectif. Lisible, tolérance assumée.

**Écarts tolérés (cosmétique non corrigée) :**

- **Titres de section longs qui wrappent sur 2 lignes** : ex.
  `« Sous-trace « ligne_liberal » — Régime Comparateur régimes —
  ligne_liberal »`. Vient du wording générique avec redondance du
  nom d'attachement et du regime de la sous-trace. **Lisible, statu
  quo cosmétique (C8.2).**
- **Parenthèses imbriquées dans certains titres** : ex. `(régime
  Salarié (appel depuis comparateur_regimes, référence))`. Visuellement
  lourd mais lisible. **Statu quo (C8.3).**
- **Sommaire dense (33 entrées) sur 1 page** : l'œil doit reconstituer
  mentalement les couples stratégie+module qui apparaissent en lignes
  successives au même niveau visuel. **Acceptable (C8.4).**

**Validation forte de neutralité (SP8) :**

Le test `test_pdf_audit_render_comparateur_regimes.py` valide explicitement
que **le renderer rend identiquement** :

- `STRAT_TNS_*` quand appelé depuis `ligne_tns/arbitrage_tns/strategie_TX`
  (profondeur 4) qu'en mode TNS isolé (profondeur 2).
- `STRAT_LIB_*` quand appelé depuis `ligne_liberal/arbitrage_liberal/...`
  (profondeur 4) qu'en mode Libéral isolé (profondeur 3).
- `STRAT_ASSIM_*` et `SAL_*` également vérifiés.

C'est la preuve que **le contexte d'appel n'influence pas le rendu** :
le renderer ne « sait pas » s'il est en train de rendre du TNS isolé
ou du TNS imbriqué dans un comparateur. Garde-fou de neutralité
structurelle tenu.

**Périmètre v1.0.0 PDF audit-ready (clôturé SP8) :**

Le périmètre fonctionnel PDF audit-ready v1.0.0 est désormais **complet**
sur les stratégies principales du dépôt MODE_AUDIT v1.6 : TNS,
Assimilé, Libéral (SELARL + SELAS), Comparateur multi-régimes. Les
modules transverses (PERIN, receptacles, scenarios, synthese) restent
appelables via la même signature `generer_pdf_audit(trace)` sans
modification — leur instrumentation MODE_AUDIT existe déjà, seul un
test PDF dédié manquerait pour les valider formellement (extension
v1.1+ si besoin).

### PDF audit-ready v1.0.1 (SP9-SP10 : phase Hardening — doctrine + invariants)

**État actuel (20/05/2026) :** Phase de durcissement post-livraison
v1.0.0. Aucune modification fonctionnelle du renderer. Deux livrables
documentaires/invariants ajoutés.

**Livrables SP9 (doctrine) :**

- `ARCHITECTURE_RENDERER.md` (711 lignes) — doctrine technique du
  renderer, formalise la philosophie, le contrat de neutralité
  (garanties G1-G5, non-garanties N1-N5), les patterns autorisés et
  interdits (§3 et §4), les 15 décisions architecturales D1-D15, les
  procédures d'extension future et les critères de bascule v2.

**Livrables SP10 (invariants) :**

- `test_renderer_invariants.py` — 51 invariants exécutables qui
  transcrivent la doctrine SP9 en assertions automatiques :
  - 10 invariants critiques serrés sur G1-G5 (1 par garantie + variantes)
  - 12 invariants critiques serrés sur §4 (antipatterns interdits :
    pas de `if regime`, pas de hardcoding profondeur, pas de
    couplage namespace, pas d'import strategy/regime, pas de fusion
    renderers)
  - 17 invariants groupés sur D1-D15 (décisions architecturales)
  - 3 invariants sur la stabilité de la surface publique (`__all__`,
    signature `generer_pdf_audit`)
- Scan par regex sur le code pur (commentaires et docstrings
  filtrés) — Q6=a validée.

**Découverte SP10 — dette G4 (étapes filles non rendues) :**

Le test invariant a révélé un écart entre la doctrine et le
comportement réel du renderer. La doctrine initiale G4 promettait
*« toutes les étapes plates, toutes les sous-traces [...] sont
restituées dans le PDF, aucune élision silencieuse »*. La réalité du
code SP1-SP8 :

| Régime | Étapes totales | Étapes racines (rendues) | Étapes filles (non rendues) | Ratio masqué |
|---|---|---|---|---|
| TNS | 156 | 93 | 63 | **40 %** |
| Assimilé | 70 | 51 | 19 | 27 % |
| Libéral SELARL | 136 | 87 | 49 | 36 % |
| Libéral SELAS | 122 | 89 | 33 | 27 % |
| Comparateur | 412 | 274 | 138 | 34 % |

Le renderer `_table_etapes_plates` itère sur `trace.racines()` pour
chaque trace + sous-traces récursives, mais ne descend pas dans
`trace.enfants(code)` (les étapes filles `parent_id != None`).

**Information masquée** : finesses intra-étape, ex. décomposition
`TNS_IR_FOYER_AGGREGE` (rendu) → `TNS_IR_FOYER_BRUT` + `TNS_CEHR` +
`TNS_CDHR` + `TNS_TAUX_MOYEN_IR` + `TNS_IMPOTS_IMPUTABLES_REM` (non
rendus). Le PDF reste **structurellement valide** et **doctrinalement
cohérent** (l'agrégat parent est présent), mais l'auditeur n'a pas la
décomposition détaillée.

**Décision Q5 = γ validée :**

- Pas de correction du renderer maintenant (la discipline Hardening
  impose de **révéler et qualifier, pas refondre à chaud**).
- Doctrine G4 reformulée dans `ARCHITECTURE_RENDERER.md` §2.1 :
  « Préservation du graphe racine » + note explicite de la limite
  étapes filles.
- Invariant `INV-G4.a` reformulé pour vérifier la présence des
  étapes racines (uniquement).
- Invariant `INV-G4.b` ajouté pour valider que les étapes filles
  sont effectivement absentes (cohérence avec la doctrine reformulée).
  Cet invariant tombera quand la dette sera traitée — ce sera le
  moment de mettre à jour G4 et de retirer l'invariant.
- Cette dette est **classée v1.1+** (refonte mineure du renderer pour
  rendre les étapes filles avec indentation visuelle).

**Test invariant 51/51 OK** après reformulation. Aucun autre KO.

**Tests cumulés PDF audit-ready v1.0.1 :**

| Test | Contrôles | Statut |
|---|---|---|
| `test_pdf_audit_render_tns.py` (pilote figé) | 93/93 | ✓ |
| `test_pdf_audit_render_assimile.py` (SP7) | 71/71 | ✓ |
| `test_pdf_audit_render_liberal.py` (SP7) | 148/148 | ✓ |
| `test_pdf_audit_render_comparateur_regimes.py` (SP8) | 83/83 | ✓ |
| `test_renderer_invariants.py` (SP10) | **51/51** | ✓ |
| **Total PDF audit-ready** | **446/446** | **✓** |

**Sous-passes restantes Phase Hardening v1.0.1 :**

- ~~SP11 — Golden PDFs~~ → **livrée** (cf. § ci-dessous)
- SP12 — Matrice de stress (cas extrêmes réalistes : 1000 étapes,
  profondeur 8, hypothèses 300 chars, Unicode, etc.)

### PDF audit-ready v1.0.1 (SP11 : Golden PDFs structurels)

**État actuel (20/05/2026) :** Mécanisme de détection des
micro-régressions visuelles ou structurelles, complétant les tests
de structure SP1-SP8 et les invariants d'architecture SP10. Aucune
modification fonctionnelle du renderer.

**Livrables SP11 :**

- `test_pdf_audit_render_goldens.py` (510 lignes) — script avec modes
  `verify` (défaut) et `--update` (avec confirmation interactive ou
  variable `GOLDEN_UPDATE_FORCE=1` pour CI).
- `golden_pdfs/` : 5 snapshots JSON (1 par cas, Q1=a) :
  - `golden_tns.json` (27 ko, 139 lignes) — 13 pages, 156 étapes, 66 racines, 9 signets
  - `golden_assimile.json` (20 ko, 112 lignes) — 13 pages, 70 étapes, 51 racines, 6 signets
  - `golden_liberal_selarl.json` (29 ko, 133 lignes) — 13 pages, 136 étapes, 56 racines, 10 signets
  - `golden_liberal_selas.json` (30 ko, 135 lignes) — 14 pages, 122 étapes, 57 racines, 10 signets
  - `golden_comparateur_regimes.json` (86 ko, 388 lignes) — 33 pages, 412 étapes, 207 racines, 31 signets

**Invariants snapshotés (5 familles, Q2=b) :**

1. **KPIs** (4 indicateurs panel couverture)
2. **Codes d'étapes racines** présents (triés set, déterministe)
3. **Signets PDF** aplatis (niveau + titre, casté `str`)
4. **Texte normalisé page par page** (dates `dd/mm/yyyy` remplacées par
   `<DATE>`, whitespace réduit, lignes vides retirées)
5. **Largeurs de colonnes calibrées** (mm arrondi 1 décimale)

**Stratégie de stabilité :**

- **Date d'édition** : forcée à `20/05/2026` via paramètre `doctrine_date`
  + remplacement regex `\d{2}/\d{2}/\d{4}` → `<DATE>` dans le texte
  extrait (couvre les dates dynamiques du footer/couverture).
- **Cast `str()` explicite** sur les titres de signets (pypdf retourne
  `TextStringObject`, sous-classe de `str`) pour idempotence
  JSON sérialisation/désérialisation.
- **Comparaison `_comparer_invariants`** : vérification structurelle
  (dict vs list) mais comparaison `==` souple sur valeurs scalaires
  (autorise `TextStringObject == str` qui retourne `True`).

**Modes d'usage :**

- **Mode `verify`** (défaut, exit 0/1/2) : compare PDF généré vs golden
  enregistré, retourne 0 si conforme, 1 si divergence détectée,
  2 si goldens manquants.
- **Mode `--update`** : regénère les goldens après confirmation
  interactive (`y/N`), ou via `GOLDEN_UPDATE_FORCE=1` en CI non-TTY.

**Validation idempotence :** re-update + re-verify retourne 5/5
conformes. Mécanisme déterministe.

**Validation détection :** simulation d'une régression (modification
manuelle d'un KPI dans le golden) → divergence correctement détectée,
exit code 1 remonté.

**Tests cumulés PDF audit-ready v1.0.1 (SP9-SP11) :**

| Test | Contrôles | Statut |
|---|---|---|
| `test_pdf_audit_render_tns.py` (pilote figé) | 93/93 | ✓ |
| `test_pdf_audit_render_assimile.py` (SP7) | 71/71 | ✓ |
| `test_pdf_audit_render_liberal.py` (SP7) | 148/148 | ✓ |
| `test_pdf_audit_render_comparateur_regimes.py` (SP8) | 83/83 | ✓ |
| `test_renderer_invariants.py` (SP10) | 51/51 | ✓ |
| `test_pdf_audit_render_goldens.py` (SP11) | **5/5 goldens** | ✓ |
| **Total PDF audit-ready** | **446 contrôles + 5 goldens** | **✓** |

**Sous-passe restante Phase Hardening v1.0.1 :**

- ~~SP12 — Matrice de stress~~ → **livrée** (cf. § ci-dessous)

### PDF audit-ready v1.0.1 (SP12 : Matrice de stress)

**État actuel (20/05/2026) :** Dernière sous-passe Hardening livrée.
Le renderer a été poussé volontairement dans des cas que les tests de
parcours normal n'exerçaient pas, afin de **qualifier ses limites**.
Aucune modification fonctionnelle du renderer requise.

**Livrable SP12 :**

- `test_renderer_stress.py` (590 lignes) — 8 cas formels :
  4 réalistes (R1-R4) avec exigence PDF valide ; 4 pathologiques
  (P1-P4) avec exigence absence de crash.

**Cas réalistes (R*) — PDF valide exigé (Q2=b) :**

| Cas | Description | Volumétrie observée |
|---|---|---|
| R1 — 1000 étapes | 100 racines + 5 sous-traces × 180 étapes | 36 pages, ~90 ko |
| R2 — Profondeur 8 | Chaîne récursive N0 → N1 → ... → N7 (8 niveaux) | 15 ko, signets plafonnés à N1 |
| R3 — Hypothèse 300 chars | Étape avec 1 hypothèse de 309 chars | 9 ko, encadré séparé |
| R4 — 40 doctrine_refs | Étape consolidation paramétrique | 9 ko, toutes refs rendues |

**Cas pathologiques (P*) — Absence de crash exigée (Q2=b) :**

| Cas | Description | Comportement observé |
|---|---|---|
| P1 — Sous-trace vide | Sous-trace attachée sans étape | Message dédié « *Aucune étape plate à ce niveau (sous-trace purement composite)* » |
| P2 — Unicode exotique | Émoji 🎯, RTL arabe `العربية`, combining `é̃` | PDF valide, glyphes manquants → rectangles noirs (dégradé acceptable) |
| P3 — Valeurs anormales | `None`, `[1,2,3]`, `{"a":1}`, NaN, ±Inf | Fallback `str(v)`, tous codes rendus |
| P4 — Code 200 chars | Code de 200 caractères | Wrap sur 5 lignes, calibrage atteint borne max 75 mm |

**Diagnostic SP12 Phase 1 (avant écriture du test formel) :**

8/8 cas génèrent un PDF sans crash. Aucun défaut bloquant cabinet
détecté (conforme Q3=γ : pas de correction immédiate requise).

**Comportements remarquables découverts :**

- **P1 — Fallback élégant** : le renderer affichait déjà un message
  dédié pour les sous-traces composites vides (« *Aucune étape plate
  à ce niveau* »). Cas anticipé dans le code SP1-SP8 sans qu'il ait
  été explicitement testé jusqu'ici.
- **P3 — Robustesse défensive** : `_formater_valeur_pdf` retourne
  `str(v)` pour tout type non prévu (None, list, dict, NaN, ±Inf).
  Pas de crash sur conversions impossibles.
- **P4 — Bornes max effectives** : le calibrage dynamique SP7 plafonne
  bien la colonne Code à 75 mm même face à un code 200 chars, avec
  wrap accepté. Comportement défensif conforme.

**Dette identifiée v1.1+ (cosmétique, non bloquante) :**

- **Glyphes Unicode manquants** : les fontes Helvetica/Courier de
  ReportLab ne couvrent pas les émojis ni les scripts non-latins
  (arabe, hébreu, CJK). Les caractères inconnus sont rendus comme
  rectangles noirs. **Pour un rendu propre** : embedder une fonte
  Unicode complète (DejaVuSans ou similaire) ou normaliser le texte
  en amont (par exemple `unicodedata.normalize('NFKD', ...)` +
  filtrage des caractères non-ASCII pour les codes). À traiter v1.1+
  si retours cabinet l'exigent.

**Décisions architecturales SP12 (validées) :**

- **Aucune modification du renderer** — la matrice de stress a
  confirmé que les choix architecturaux D1-D15 absorbent les cas
  extrêmes du périmètre v1.0.0+ sans intervention.
- **Bornes min/max du calibrage SP7 jugées correctement dimensionnées**
  pour le périmètre v1.0.0 (R1, R3, R4 OK ; P4 en stress mais comportement
  défensif acceptable).
- **Critères de bascule v2 confirmés** dans
  `ARCHITECTURE_RENDERER.md` §6.4 : à partir de quelle volumétrie ou
  profondeur la doctrine actuelle ne tiendrait plus.

**Tests cumulés PDF audit-ready v1.0.1 (clôture Hardening) :**

| Test | Contrôles | Statut |
|---|---|---|
| `test_pdf_audit_render_tns.py` (pilote figé) | 93/93 | ✓ |
| `test_pdf_audit_render_assimile.py` (SP7) | 71/71 | ✓ |
| `test_pdf_audit_render_liberal.py` (SP7) | 148/148 | ✓ |
| `test_pdf_audit_render_comparateur_regimes.py` (SP8) | 83/83 | ✓ |
| `test_renderer_invariants.py` (SP10) | 51/51 | ✓ |
| `test_pdf_audit_render_goldens.py` (SP11) | 5/5 goldens | ✓ |
| `test_renderer_stress.py` (SP12) | **43/43** | ✓ |
| **TOTAL PDF audit-ready v1.0.1** | **489 contrôles + 5 goldens** | **✓** |

**Phase Hardening v1.0.1 — clôturée** (SP9 à SP12 livrées).

### v1.1.0 — Module Réceptacles (SP13-SP14 : doctrine + scaffolding)

**État actuel (20/05/2026) :** Première phase v1.1.0 démarrée selon
le contrat d'évolution validé : extension métier du framework v1.0.1,
**sans modification du framework**. Tous les invariants SP9-SP12
restent verts après SP13-SP14 (preuve forte du contrat tenu).

**Livrables SP13 (doctrine métier) :**

- `ARCHITECTURE_RECEPTACLES.md` (798 lignes) — doctrine métier +
  technique + frontières négatives. 11 sections : philosophie,
  périmètre, **unités économiques verrouillées**, **frontières
  négatives**, wordings centralisés, architecture technique, couche
  temporelle, contrats framework, 14 décisions D-R1 à D-R14,
  extension future, synthèse.

**Livrables SP14 (scaffolding code) :**

- `strategy/receptacles_wordings.py` (créé) — module centralisé des
  wordings d'hypothèses longues (D-R3). 3 wordings transverses figés
  en SP14 :
  - `WORDING_REC_CONVENTION_RENDEMENT`
  - `WORDING_REC_DISCLAIMER_COMPARABILITE`
  - `WORDING_REC_DISCLAIMER_PERIMETRE`
- `strategy/receptacles_orchestrateur.py` (créé, mock fonctionnel) —
  signature publique définitive `allocation_receptacles(profil, *,
  flux_disponible, horizons, audit)`, dataclass hiérarchique
  (`ResultatAllocationReceptacles` → `ResultatAllocationPerin/Pee/Pereco`
  → `LigneHorizonReceptacle`), instrumentation MODE_AUDIT (5 étapes
  méta + 3 sous-traces mock). Pipeline complet rendable par
  `generer_pdf_audit` validé.
- `test_strategy_receptacles.py` (créé) — 50 assertions structurelles
  sur 11 sections : imports, wordings, dataclass hiérarchique,
  signature publique, constantes, orchestrateur, instrumentation,
  préservation G4, framework-compatibilité, orchestrateur passif,
  horizons paramétrables.

**Décisions architecturales D-R1 à D-R14 figées en SP13 :**

| # | En bref |
|---|---|
| D-R1 | 2 moteurs indépendants (rémunération + réceptacles) |
| D-R2 | Namespace `REC_<ENVELOPPE>_<CONCEPT>[_<HORIZON>]` |
| D-R3 | Wordings ≥ 80 chars centralisés, zéro inline |
| D-R4 | 5 modules distincts (3 enveloppes + orchestrateur + wordings) |
| D-R5 | Signature standardisée `(profil, *, flux_disponible, horizons, audit)` |
| D-R6 | Orchestrateur passif : composition seulement |
| D-R7 | Multi-période par étapes distinctes par horizon, grammaire `TraceAudit` inchangée |
| D-R8 | Rendement conventionnel 2 % nominal, pas prédictif |
| D-R9 | Horizons défaut (5, 10, 20) ans, paramétrables |
| D-R10 | Aucune étape `parent_id != None` en v1.1 (préservation G4) |
| D-R11 | Périmètre strict PERIN + PEE + PERECO |
| D-R12 | Comparateur, pas dimensionneur |
| D-R13 | Capitalisation déterministe, pas stochastique |
| D-R14 | Euros nominaux, pas constants |

**Validations clés SP14 :**

- Pipeline mock fonctionne : génération `TraceAudit` (8 étapes + 3 sous-traces +
  16 hypothèses) → `generer_pdf_audit` produit un PDF valide de 17.4 ko.
- Contrat d'évolution tenu : aucune modification du framework
  v1.0.1, aucune régression sur les 489 contrôles existants +
  5 goldens.
- Préservation G4 (D-R10) : 0/8 étapes filles produites — la trace
  v1.1 SP14 a 100 % de ses étapes rendues dans le PDF.
- Module legacy `strategy/receptacles.py` (matrice d'accessibilité)
  intact et toujours fonctionnel : SP14 le **consomme**, ne le modifie pas.

**Tests cumulés post-SP14 :**

| Test | Contrôles | Statut |
|---|---|---|
| `test_pdf_audit_render_tns.py` (pilote figé) | 93/93 | ✓ |
| `test_pdf_audit_render_assimile.py` (SP7) | 71/71 | ✓ |
| `test_pdf_audit_render_liberal.py` (SP7) | 148/148 | ✓ |
| `test_pdf_audit_render_comparateur_regimes.py` (SP8) | 83/83 | ✓ |
| `test_renderer_invariants.py` (SP10) | 51/51 | ✓ |
| `test_pdf_audit_render_goldens.py` (SP11) | 5/5 goldens | ✓ |
| `test_renderer_stress.py` (SP12) | 43/43 | ✓ |
| `test_strategy_receptacles.py` (SP14) | 50/50 | ✓ |
| **TOTAL post-SP14** | **539 contrôles + 5 goldens** | **✓** |

### v1.1.0 — Module Réceptacles (SP15 : PERIN réel)

**État actuel (20/05/2026) :** Premier module métier réel livré.
PERIN passe de mock à implémentation fonctionnelle, posant le pattern
qui sera réutilisé par SP16 (PEE) et SP17 (PERECO).

**Livrables SP15 :**

- `strategy/receptacles_perin.py` (~340 lignes) — module métier
  PERIN complet :
  - Périmètre Q1=b : plafond annuel complet (consommé via legacy
    `strategy.perin.calcul_plafond_perin`), économie fiscale entrée,
    capitalisation conventionnelle 2 %, fiscalité sortie capital
    (IR sur versements + PFU 30 % sur gains).
  - **Hors SP15** : rattrapages N-1/N-2/N-3, sortie en rente,
    abondement employeur (cf. doctrine SP13 §10.3, périmètre figé).
  - 3 providers doctrinaux (Q8=a, G-2) : `obtenir_plafond_perin`,
    `obtenir_tmi_dirigeant`, `est_eligible_perin`. Aucun branchement
    `if profil.regime ==` dans le module.
  - Volumétrie effective : 5 étapes racines + 3 sous-traces horizons
    × 6 étapes = **23 étapes** par appel (cohérent avec Q3=b estimé
    25-30).
- `strategy/receptacles_wordings.py` (étendu) — 4 wordings PERIN
  spécifiques figés :
  - `WORDING_PERIN_REGLE_PLAFOND`
  - `WORDING_PERIN_DEDUCTIBILITE_IR_ENTREE`
  - `WORDING_PERIN_FISCALITE_SORTIE_CAPITAL`
  - `WORDING_PERIN_DISPONIBILITE_RETRAITE`
- `strategy/receptacles_orchestrateur.py` (étendu) :
  - **Type-aliases documentaires** (Q7=b) : `Euros`, `TauxAnnuel`,
    `Annees`. Verrouillage sémantique du vocabulaire économique.
  - **`__post_init__`** sur `LigneHorizonReceptacle` (Q7=c partiel) :
    valide les 2 invariants algébriques (effort réel, valeur nette)
    avec tolérance 0,01 € pour absorber les arrondis flottants.
  - **Branchement PERIN réel** : `_mock_allocation_perin` reste défini
    pour rétrocompatibilité mais marqué obsolète ; `allocation_receptacles`
    appelle directement `allocation_perin` via import paresseux (évite
    cycle import).
- `test_strategy_receptacles.py` (étendu) :
  - Section 10 reformulée pour SP15 (le test « valeurs identiques quel
    que soit le flux » n'est plus pertinent dès qu'un module métier
    réel est branché ; remplacé par 5 tests d'orchestrateur passif
    plus précis).
  - **Section 12 nouvelle** : 18 contrôles dédiés PERIN (imports,
    providers, signature, constantes fiscalité, calcul économique,
    invariants algébriques, capitalisation croissante, coût entreprise
    nul, préservation D-R10, volumétrie cible).
  - Total : 71/71 contrôles (vs 50/50 SP14).
- `test_strategy_receptacles_goldens.py` (nouveau, Q6=c) — **mini-goldens
  métier** :
  - Mécanisme distinct des goldens PDF SP11 : snapshot du résultat
    économique sérialisé en JSON, indépendant du rendu PDF. Détecte
    les régressions de calcul.
  - Pattern verify/update similaire à SP11 (modes interactif + var
    env `GOLDEN_METIER_UPDATE_FORCE=1` pour CI).
  - 2 cas figés en SP15 (extension progressive prévue SP16-SP17) :
    - `borne_par_plafond` : flux 10 000 € borné à plafond min 4 806 €
    - `sous_plafond` : flux 2 000 € en-dessous du plafond
  - Snapshots JSON dans `golden_metiers/perin_*.json`.

**Décisions architecturales validées SP15 :**

- **Q5 = (a) Un seul taux conventionnel 2 %** : pas de scénarios
  multiples (2/4/6 %) qui auraient changé la nature du livrable. D-R8
  inchangée.
- **Q6 = (c) Mini-goldens métier dès SP15** : démarrage avec 2 cas
  PERIN, extension progressive.
- **Q7 = (b)+(c) partiel** : type-aliases + invariants algébriques
  seulement (effort réel, valeur nette). Pas de validations
  interprétatives.
- **Q8 = (a) Providers doctrinaux centralisés** : `obtenir_plafond_perin`
  délègue au legacy `strategy.perin.calcul_plafond_perin`. Zéro
  redéclaration de paramètre réglementaire.

**Points de vigilance SP15 résolus :**

1. **Conflit de noms évité** : le legacy `strategy/perin.py` (calcul
   plafond avec mutualisation conjoint) coexiste avec le nouveau
   `strategy/receptacles_perin.py` (allocation v1.1) sans conflit
   d'import. Le nouveau **consomme** le legacy.
2. **Cycle import résolu** : `receptacles_perin.py` importe depuis
   `receptacles_orchestrateur.py` (Euros, dataclass), et
   `receptacles_orchestrateur.py` doit importer `allocation_perin`.
   Solution : **import paresseux** dans la fonction `allocation_receptacles`.
3. **Cohérence des arrondis** : la première version naïve faisait
   `round(valeur_nette)` après chaque calcul, ce qui pouvait diverger
   d'un cent vs `round(capital) - round(fisc)`. Solution : arrondir
   **avant** composition, puis recomposer `valeur_nette` à partir
   des champs déjà arrondis. L'invariant `__post_init__` passe
   alors strictement.
4. **Profil par défaut a `remuneration_brute = absent`** : le proxy
   `getattr(profil, "remuneration_brute", 0.0)` retourne 0, donc le
   plafond se rabat au minimum 10 % PASS = 4 806 €. Comportement
   correct mais doit être documenté pour les futurs utilisateurs.

**Tests cumulés post-SP15 :**

| Test | Contrôles | Statut |
|---|---|---|
| `test_pdf_audit_render_tns.py` (pilote figé) | 93/93 | ✓ |
| `test_pdf_audit_render_assimile.py` (SP7) | 71/71 | ✓ |
| `test_pdf_audit_render_liberal.py` (SP7) | 148/148 | ✓ |
| `test_pdf_audit_render_comparateur_regimes.py` (SP8) | 83/83 | ✓ |
| `test_renderer_invariants.py` (SP10) | 51/51 | ✓ |
| `test_pdf_audit_render_goldens.py` (SP11) | 5/5 goldens | ✓ |
| `test_renderer_stress.py` (SP12) | 43/43 | ✓ |
| `test_strategy_receptacles.py` (SP14+SP15) | 71/71 | ✓ |
| `test_strategy_receptacles_goldens.py` (SP15) | 2/2 goldens métier | ✓ |
| **TOTAL post-SP15** | **560 contrôles + 5 goldens PDF + 2 goldens métier** | **✓** |

### v1.1.0 — Module Réceptacles (SP16 : PEE réel)

**État actuel (20/05/2026) :** Deuxième module métier réel livré.
PEE passe de mock à implémentation fonctionnelle, suivant le pattern
posé par SP15 et adaptant la sémantique économique aux spécificités
du Plan d'Épargne Entreprise.

**Tension sémantique résolue en SP16 :**

PEE introduit une dualité que PERIN ne connaît pas : **flux mixte
salarié + employeur**. La question structurante : comment représenter
cette dualité dans `LigneHorizonReceptacle` sans déformer le
vocabulaire verrouillé SP13 §3 ?

Choix retenu (cohérent avec votre apport « modèles comparables sans
homogénéisation artificielle ») :

- `flux_entrant_brut` reste défini comme **ce que le salarié verse
  depuis son patrimoine** (= flux salarié seul). Cohérent avec PERIN
  où c'est le versement du dirigeant.
- `economie_fiscale_immediate = 0` pour PEE (Q5=ii : pas de
  déductibilité IR à l'entrée, contrairement au PERIN).
- `effort_reel = flux_salarié` (l'abondement employeur n'est pas un
  effort du salarié).
- `capital_projete` = (flux_salarié + abondement_net) capitalisé.
  L'abondement gonfle le capital sans gonfler l'effort.
- `cout_entreprise > 0` pour PEE (abondement brut versé), vs 0 pour
  PERIN (produit individuel).
- L'abondement, sa CSG-CRDS, et le flux total versé sont
  **instrumentés dans les étapes audit** (codes dédiés
  `REC_PEE_ABONDEMENT_EMPLOYEUR_BRUT`, `REC_PEE_CSG_CRDS_ABONDEMENT`,
  `REC_PEE_ABONDEMENT_EMPLOYEUR_NET`, `REC_PEE_FLUX_TOTAL_VERSE`).

Cette résolution **préserve** :
- L'invariant algébrique `effort_reel == flux_entrant_brut - economie_fiscale_immediate`
  (=> PEE : `5000 == 5000 - 0` ✓)
- L'invariant algébrique `valeur_nette == capital_projete - fiscalite_sortie`
- La comparabilité dataclass entre PERIN et PEE (mêmes 8 dimensions)
- La spécificité économique de chaque enveloppe (l'effet abondement
  apparaît dans la trace, pas dans des champs spécifiques)

**Livrables SP16 :**

- `strategy/receptacles_pee.py` (~430 lignes) — module métier PEE
  complet :
  - Périmètre Q1=b : versement volontaire + abondement employeur
    (lecture profil + fallback doctrinal 100 %) + frottement CSG-CRDS
    (9,7 % à l'entrée sur abondement) + capitalisation conventionnelle
    + fiscalité sortie au-delà de 5 ans (PFU 17,2 % sur gains seuls).
  - 3 providers doctrinaux (G-2) : `obtenir_taux_abondement_pee`,
    `obtenir_plafond_abondement_pee`, `est_eligible_pee`.
  - Constantes nommées : `PLAFOND_ABONDEMENT_PEE` (8 % PASS),
    `TX_CSG_CRDS_ABONDEMENT_PEE` (9,7 %), `TX_PS_GAINS_PEE` (17,2 %).
  - Volumétrie effective : 6 étapes racines + 3 sous-traces × 9 étapes
    = **33 étapes** par appel (légèrement au-dessus de PERIN 23
    étapes du fait de la décomposition abondement brut → CSG → net →
    total).
- `strategy/receptacles_wordings.py` (étendu) — 4 wordings PEE
  spécifiques figés :
  - `WORDING_PEE_ABONDEMENT_EMPLOYEUR`
  - `WORDING_PEE_CSG_CRDS_ABONDEMENT`
  - `WORDING_PEE_DISPONIBILITE_5ANS`
  - `WORDING_PEE_EXONERATION_PV_SORTIE`
- `strategy/receptacles_orchestrateur.py` (étendu) — branchement
  PEE réel via `allocation_pee` (import paresseux, pattern identique
  à SP15). Le mock `_mock_allocation_pee` reste défini mais marqué
  obsolète. Seul `_mock_allocation_pereco` reste actif en attendant
  SP17.
- `test_strategy_receptacles.py` (étendu) :
  - Section 10 adaptée : PEE n'est plus mocké à zéro, contrôle de
    dépendance au flux ajouté.
  - **Section 13 nouvelle** : 25 contrôles dédiés PEE (imports,
    providers, signature, constantes, sémantique flux_entrant_brut
    salarié, économie fiscale = 0, effort réel = flux salarié,
    coût entreprise > 0, plafonnement, effet abondement,
    invariants algébriques, capitalisation, disponibilité 5 ans,
    préservation D-R10, volumétrie cible, **comparabilité dataclass
    avec PERIN**).
  - Total : 96/96 contrôles (vs 71/71 SP15).
- `test_strategy_receptacles_goldens.py` (étendu) :
  - Champ `enveloppe` ajouté à chaque cas pour router le calcul.
  - Nommage fichier golden : `<enveloppe_lowercase>_<nom>.json`
    (préfixe par enveloppe, vs `perin_` fixe en SP15).
  - **1 nouveau cas PEE figé** (Q3=a) : `abondement_plafonne`
    (flux salarié 5 000 €, abondement plafonné, CSG-CRDS prélevée).
  - Total : 3/3 conformes (2 PERIN + 1 PEE).

**Décisions architecturales validées SP16 :**

- **Q4 = (III)** Flux entrant brut = flux salarié (pas le total).
  Décomposition flux mixte via codes étapes audit, pas via le
  dataclass. Préserve l'invariant `__post_init__`.
- **Q5 = (ii)** `economie_fiscale_immediate = 0` pour PEE. Pas de
  réinterprétation du vocabulaire SP13 §3.
- **Q6 = (b)** CSG-CRSD instrumentée explicitement dans la trace
  (étape dédiée). Pas masquée à la source.
- **Q7 = (a)** Hypothèse simplificatrice horizons ≥ 5 ans. Une étape
  audit `REC_PEE_HORIZONS_AVANT_DISPONIBILITE` signale les cas non
  conformes (mais ne bloque pas).
- **Q8 = (a)** Fallback doctrinal 100 % du versement, plafonné à
  8 % PASS. Tracé dans les hypothèses audit.

**Validation empirique de la doctrine (cas 5 000 € flux salarié) :**

| Dimension | PERIN | PEE |
|---|---|---|
| `flux_entrant_brut` | 4 806 € (borné par plafond) | 5 000 € (flux salarié) |
| `economie_fiscale_immediate` | 1 442 € (déduction IR TMI 30 %) | 0 € (pas de déductibilité) |
| `effort_reel` | 3 364 € | 5 000 € |
| `capital_projete` (H5) | 5 306 € | 9 354 € |
| `valeur_nette` (H5) | 3 714 € | 9 202 € |
| `cout_entreprise` | 0 € (individuel) | 3 845 € (abondement) |

La comparaison cabinet devient parlante : pour 5 000 € versés, le PEE
produit ~2,5× plus de valeur nette à H5 que PERIN — au prix d'un
**coût employeur** non nul. Comparabilité préservée, spécificités
visibles.

**Tests cumulés post-SP16 :**

| Test | Contrôles | Statut |
|---|---|---|
| `test_pdf_audit_render_tns.py` (pilote figé) | 93/93 | ✓ |
| `test_pdf_audit_render_assimile.py` (SP7) | 71/71 | ✓ |
| `test_pdf_audit_render_liberal.py` (SP7) | 148/148 | ✓ |
| `test_pdf_audit_render_comparateur_regimes.py` (SP8) | 83/83 | ✓ |
| `test_renderer_invariants.py` (SP10) | 51/51 | ✓ |
| `test_pdf_audit_render_goldens.py` (SP11) | 5/5 goldens | ✓ |
| `test_renderer_stress.py` (SP12) | 43/43 | ✓ |
| `test_strategy_receptacles.py` (SP14+SP15+SP16) | 96/96 | ✓ |
| `test_strategy_receptacles_goldens.py` (SP15+SP16) | 3/3 goldens métier | ✓ |
| **TOTAL post-SP16** | **585 contrôles + 5 goldens PDF + 3 goldens métier** | **✓** |

### v1.1.0 — Module Réceptacles (SP17 : PERECO hybride)

**État actuel (20/05/2026) :** Troisième et dernier module métier livré.
Le PERECO combine la logique fiscale PERIN (déductibilité IR à
l'entrée, PFU sur gains à la sortie) avec la logique abondement PEE
(coût entreprise, CSG-CRDS, exonération IR sur abondement). C'est
l'enveloppe sémantiquement la plus complexe du périmètre v1.1, et
celle qui valide le principe d'**orthogonalité doctrinale** des
3 enveloppes.

**Apport méthodologique structurant (votre garde-fou SP17) :**

Vous avez recommandé l'ajout d'un **tableau doctrinal transverse**
des dimensions économiques. C'est précisément l'instrument qui empêche
la dérive sémantique au moment de la composition SP18. Ce tableau
figure désormais en **§3.6 de `ARCHITECTURE_RECEPTACLES.md`** et est
**testé empiriquement** par les contrôles 15.3 à 15.7 de
`test_strategy_receptacles.py`.

Matrice doctrinale figée v1.1 :

| Dimension                         | PERIN | PEE | PERECO |
|---|---|---|---|
| Déduction IR entrée               | Oui   | Non | Oui    |
| Abondement employeur              | Non   | Oui | Oui    |
| CSG-CRDS sur abondement           | —     | Oui | Oui    |
| Disponibilité                     | Retraite | 5 ans | Retraite |
| Sortie capital (v1.1)             | Oui   | Oui | Oui    |
| Fiscalité versement salarié sortie| IR TMI | Exonéré | IR TMI |
| Fiscalité abondement sortie       | —     | Exonéré IR | Exonéré IR |
| Fiscalité gains sortie            | PFU 30 % | PS 17,2 % | PFU 30 % |
| Coût entreprise (dataclass)       | 0     | > 0 | > 0    |
| economie_fiscale_immediate        | > 0   | 0   | > 0    |

**Livrables SP17 :**

- `strategy/receptacles_pereco.py` (~485 lignes) — module métier
  PERECO hybride complet :
  - Périmètre Q1=b : versement volontaire + abondement employeur
    + CSG-CRDS + capitalisation + sortie capital
  - 4 providers doctrinaux dont 2 délègués à PERIN
    (`obtenir_plafond_pereco` = `obtenir_plafond_perin`,
    `obtenir_tmi_dirigeant` partagée) et 2 spécifiques PERECO
    (`obtenir_taux_abondement_pereco`, `obtenir_plafond_abondement_pereco`)
  - 3 constantes : `PLAFOND_ABONDEMENT_PERECO` (= 8 % PASS, aligné PEE
    en v1.1), `TX_CSG_CRDS_ABONDEMENT_PERECO` (= 9,7 %, aligné PEE),
    `TX_PFU_GAINS_PERECO` (= 30 %, aligné PERIN)
  - Volumétrie effective : 9 étapes racines + 3 sous-traces × 10 étapes
    = **39 étapes** par appel (la plus volumineuse des 3 modules,
    logique : hybride PERIN+PEE)
  - **Distinction fiscalité de sortie** : versement salarié déduit à
    l'entrée → reprise IR TMI à la sortie ; abondement non déduit
    (mais déjà CSG-CRDS entrée) → **exonéré IR à la sortie** ; gains
    PFU 30 %. C'est une subtilité doctrinale critique.

- `strategy/receptacles_wordings.py` (étendu) — 5 wordings PERECO
  spécifiques figés (DEDUCTIBILITE_IR_ENTREE, ABONDEMENT_EMPLOYEUR,
  CSG_CRDS_ABONDEMENT, FISCALITE_SORTIE_CAPITAL, DISPONIBILITE_RETRAITE).

- `strategy/receptacles_orchestrateur.py` (étendu) — branchement
  PERECO réel via import paresseux. **Plus aucun mock actif** dans
  le pipeline `allocation_receptacles`. Les 3 mocks scaffolding SP14
  restent définis mais marqués obsolètes (rétrocompatibilité).

- `test_strategy_receptacles.py` (étendu) :
  - Section 10 finalisée : tous les modules sont réels, plus de mock
    à pointer.
  - **Section 14 nouvelle** : 20 contrôles dédiés PERECO (imports,
    providers délégués, constantes hybrides, sémantique Q2=γ,
    invariants algébriques, disponibilité retraite, préservation D-R10,
    volumétrie cible).
  - **Section 15 nouvelle** : 7 contrôles dédiés à la **comparabilité
    cross-enveloppes**. Le tableau doctrinal transverse est validé
    empiriquement par les contrôles 15.3-15.7. Toute régression
    future qui homogénéiserait par erreur les enveloppes serait
    détectée par ces 7 contrôles.
  - Total : 123/123 contrôles (vs 96/96 SP16).

- `test_strategy_receptacles_goldens.py` (étendu) — 1 nouveau cas
  PERECO figé : `hybride_perin_pee` (flux salarié 5 000 €,
  déductibilité TMI 30 %, abondement plafonné, CSG-CRDS). Démontre
  la combinaison doctrinale Q2=γ. Total : 4/4 goldens conformes.

- `ARCHITECTURE_RECEPTACLES.md` (étendu) — **§3.6 ajoutée** :
  Tableau doctrinal transverse des dimensions économiques. Section
  doctrinale qui matérialise l'orthogonalité PERIN/PEE/PERECO et
  référence les contrôles de test correspondants.

**Décisions architecturales validées SP17 :**

- **Q1 = (b)** Standard : versement volontaire + abondement +
  déduction IR + CSG-CRDS + capitalisation + sortie capital. Plafond
  spécifique 16 % PASS PERECO **différé v1.2**, plafond 8 % PASS
  retenu par cohérence avec PEE.
- **Q2 = (γ)** Hybride : PERECO hérite de PERIN sa logique fiscale
  entrée+sortie ET de PEE sa logique d'abondement. Aucune
  redéfinition du vocabulaire SP13 §3 :
  - `economie_fiscale_immediate` reste « réduction d'IR » (cohérent
    PERIN, 0 pour PEE).
  - `cout_entreprise` reflète l'abondement brut (cohérent PEE, 0
    pour PERIN).
  - Les deux champs sont > 0 pour PERECO simultanément. C'est la
    signature économique distinctive du PERECO.
- **Q3 = (a)** 1 mini-golden ciblé PERECO.

**Comparaison empirique cross-enveloppes (flux 5 000 €, profil par défaut, H5) :**

| Dimension | PERIN | PEE | PERECO |
|---|---|---|---|
| flux_entrant_brut | 4 806 | 5 000 | 4 806 |
| economie_fiscale_immediate | 1 442 | 0 | 1 442 |
| effort_reel | 3 364 | 5 000 | 3 364 |
| capital_projete | 5 306 | 9 354 | 9 139 |
| fiscalite_sortie | 1 592 | 152 | 1 700 |
| valeur_nette | 3 714 | 9 202 | 7 439 |
| cout_entreprise | 0 | 3 845 | 3 845 |

La comparaison cabinet devient parlante :
- **PERIN** : effort 3 364 €, net 3 714 € → efficacité fiscale
  entrée+sortie élevée mais sans levier employeur.
- **PEE** : effort 5 000 €, net 9 202 € → fort effet abondement,
  faible fiscalité sortie, mais effort double.
- **PERECO** : effort 3 364 €, net 7 439 € → **combine les deux
  avantages** : effort équivalent PERIN ET capital boosté par
  abondement. Fiscalité sortie plus lourde que PEE car versements
  salariés repris à l'IR.

**Tests cumulés post-SP17 :**

| Test | Contrôles | Statut |
|---|---|---|
| `test_pdf_audit_render_tns.py` (pilote figé) | 93/93 | ✓ |
| `test_pdf_audit_render_assimile.py` (SP7) | 71/71 | ✓ |
| `test_pdf_audit_render_liberal.py` (SP7) | 148/148 | ✓ |
| `test_pdf_audit_render_comparateur_regimes.py` (SP8) | 83/83 | ✓ |
| `test_renderer_invariants.py` (SP10) | 51/51 | ✓ |
| `test_pdf_audit_render_goldens.py` (SP11) | 5/5 goldens | ✓ |
| `test_renderer_stress.py` (SP12) | 43/43 | ✓ |
| `test_strategy_receptacles.py` (SP14→SP17) | 123/123 | ✓ |
| `test_strategy_receptacles_goldens.py` (SP15→SP17) | 4/4 goldens métier | ✓ |
| **TOTAL post-SP17** | **612 contrôles + 5 goldens PDF + 4 goldens métier** | **✓** |

### v1.1.0 — Module Réceptacles (SP18 : orchestrateur opérationnel)

**État actuel (20/05/2026) :** L'orchestrateur réceptacles est
opérationnel. Il compose les 3 modules métier livrés en SP15-SP17
et produit des étapes méta récapitulatives cross-enveloppes
**purement descriptives** par horizon — sans aucune logique
prescriptive (D-R6 préservé strictement).

**Apport méthodologique SP18 (votre garde-fou explicite) :**

Vous avez identifié le risque structurant à ce stade :

> *Le plus gros risque maintenant serait que l'orchestrateur commence
> à interpréter, puis à optimiser, puis à recommander. Et là D-R6
> tomberait immédiatement.*

SP18 grave dans le code et dans les tests les contraintes qui rendent
cette dérive **impossible silencieusement** :

1. **Stabilité d'ordre stricte PERIN → PEE → PERECO** dans toutes les
   traces, hypothèses, codes étapes et goldens.
2. **Aucun score / indice / ranking / efficacité / performance** dans
   le contenu visible (testé par contrôle 16.5).
3. **Valeur scalaire neutre** (`= 3`, nombre d'enveloppes alignées)
   pour les étapes RECAP — aucune métrique économique au niveau
   scalaire.
4. **Tout dans la trace, dataclass minimal** (Q2=a) — aucun champ
   `tableau_recapitulatif` au niveau `ResultatAllocationReceptacles`.
5. **Mini-golden orchestrateur** capturant explicitement l'ordre des
   enveloppes via listes ordonnées (insensibles au `sort_keys` du
   dump JSON).

**Livrables SP18 :**

- `strategy/receptacles_orchestrateur.py` (étendu) :
  - **Fonction `_instrumenter_etapes_recapitulatives` nouvelle**
    (~120 lignes) : produit 3 étapes méta × N horizons (9 étapes en
    configuration par défaut). 3 dimensions instrumentées :
    `REC_RECAP_VALEUR_NETTE_{h}ANS`, `REC_RECAP_EFFORT_REEL_{h}ANS`,
    `REC_RECAP_COUT_ENTREPRISE_{h}ANS`. Toutes au niveau racine
    (D-R10 préservé).
  - Appel de cette fonction depuis `allocation_receptacles` après
    les 3 sous-traces enveloppes (composition pure, aucune logique
    métier ajoutée).
  - Harmonisation des commentaires (1/3 PERIN, 2/3 PEE, 3/3 PERECO)
    pour matérialiser visuellement l'ordre stable.

- `test_strategy_receptacles.py` (étendu) :
  - **Section 16 nouvelle** : 7 contrôles dédiés étapes
    récapitulatives :
    - 16.1 Présence des 9 codes RECAP attendus
    - 16.2 Préservation D-R10 (toutes étapes racine)
    - 16.3 Stabilité d'ordre PERIN → PEE → PERECO dans hypothèses
    - 16.4 Cohérence agrégation valeur nette (anti-désynchronisation
      trace/dataclass)
    - 16.5 **Aucun mot interdit** (score / indice / ranking /
      optimal / meilleur / préconis / recommand / efficacité /
      performance) dans contenu visible — testé exhaustivement sur
      labels et hypothèses
    - 16.6 Valeur scalaire neutre (= 3) pour toutes les étapes RECAP
    - 16.7 Mention `ordre_stable` présente dans toutes hypothèses RECAP
  - Total : **130/130 contrôles** (vs 123/123 SP17).

- `test_strategy_receptacles_goldens.py` (étendu) :
  - **Fonction `_extraire_invariants_orchestrateur` nouvelle**
    (~80 lignes) : snapshot ciblé de composition cross-enveloppes.
  - Format snapshot orchestrateur :
    - `composition_dataclass` : 3 enveloppes × 3 horizons × 3 valeurs
      (valeur_nette, effort_reel, cout_entreprise)
    - `etapes_recap_snapshot` : 9 entrées avec
      `hypotheses_enveloppes_ordonnees` sous forme de **listes
      ordonnées de tuples** (insensibles au `sort_keys=True` du
      dump JSON) — preuve explicite de l'ordre
    - `sous_traces_attachees_ordonnees` : liste `[ligne_perin,
      ligne_pee, ligne_pereco]`
    - `nb_etapes_racine_total`
  - 1 nouveau cas figé `ORCHESTRATEUR/composition_5000`.
  - Total : **5/5 goldens métier** (4 enveloppes + 1 orchestrateur).

**Décisions architecturales validées SP18 :**

- **Q1 = (c)** Tableau récapitulatif par horizon (alignement factuel,
  pas de classement).
- **Q2 = (a)** Tout dans la trace, dataclass minimal (orchestrateur
  passif strict).
- **Q3 = (b)** Mini-golden orchestrateur ciblé sur la composition.

**Validation empirique des garde-fous SP18 :**

| Garde-fou utilisateur | Contrôle test | Statut |
|---|---|---|
| Stabilité d'ordre stricte PERIN → PEE → PERECO | 16.3 | ✓ |
| Aucun mot interdit (score, ranking, optimal, etc.) | 16.5 | ✓ |
| Pas de duplication trace/dataclass | 16.4 (cohérence agrégation) | ✓ |
| Étapes RECAP au niveau racine (D-R10) | 16.2 | ✓ |
| 9 codes attendus présents | 16.1 | ✓ |
| Valeur scalaire neutre (= 3, pas une métrique) | 16.6 | ✓ |
| Mention `ordre_stable` auditable | 16.7 | ✓ |

**Pipeline complet post-SP18 (flux 5 000 €) :**

- 3 modules métier réels (PERIN/PEE/PERECO) produisent chacun
  6-9 étapes racine + 3 sous-traces × 6-10 étapes
- 5 étapes méta racine de l'orchestrateur
- 9 étapes RECAP cross-enveloppes
- **Total : 109 étapes au niveau racine + 12 sous-traces de
  168 hypothèses, PDF 75 ko**

**Découverte SP18 (à documenter) :**

L'utilisation de `sort_keys=True` dans `json.dump` réorganise les
clés de dict mais **préserve l'ordre des listes**. La conception du
snapshot orchestrateur via **listes ordonnées de tuples** pour
`hypotheses_enveloppes_ordonnees` est donc immune au tri JSON et
garde l'ordre PERIN→PEE→PERECO explicite dans le golden. C'est un
pattern réutilisable pour tout snapshot où l'ordre est sémantiquement
porteur.

**Tests cumulés post-SP18 :**

| Test | Contrôles | Statut |
|---|---|---|
| `test_pdf_audit_render_tns.py` (pilote figé) | 93/93 | ✓ |
| `test_pdf_audit_render_assimile.py` (SP7) | 71/71 | ✓ |
| `test_pdf_audit_render_liberal.py` (SP7) | 148/148 | ✓ |
| `test_pdf_audit_render_comparateur_regimes.py` (SP8) | 83/83 | ✓ |
| `test_renderer_invariants.py` (SP10) | 51/51 | ✓ |
| `test_pdf_audit_render_goldens.py` (SP11) | 5/5 goldens | ✓ |
| `test_renderer_stress.py` (SP12) | 43/43 | ✓ |
| `test_strategy_receptacles.py` (SP14→SP18) | **130/130** | ✓ |
| `test_strategy_receptacles_goldens.py` (SP15→SP18) | **5/5 goldens métier** | ✓ |
| **TOTAL post-SP18** | **619 contrôles + 5 goldens PDF + 5 goldens métier** | **✓** |

**Sous-passes v1.1.0 restantes :**

- SP19 — Test PDF audit dédié réceptacles + golden réceptacles
  (restitution PDF, pas de stabilisation métier — votre intuition
  SP17 confirmée à nouveau en SP18)

**Note méthodologique SP18 (votre intuition confirmée à nouveau) :**

Vous aviez écrit en SP17 :

> *Si SP17 tient proprement, alors SP18 (orchestrateur cross-enveloppes)
> sera surtout un travail de composition, pas de stabilisation
> doctrinale.*

Validé empiriquement par SP18 :
- **0 nouvelle décision doctrinale** prise pendant SP18
  (les 17 décisions D-R + tableau §3.6 ont suffi)
- **0 modification des modules métier** SP15-SP17
- **0 modification du dataclass partagé** `LigneHorizonReceptacle`
- **0 nouveau wording** ajouté
- **+1 fonction d'instrumentation** (composition pure)
- **+7 contrôles** structurels au test
- **+1 cas mini-golden** orchestrateur

SP18 a été un travail **purement de composition**, conforme à votre
intuition. Cette même intuition s'étend à SP19 : la doctrine étant
intégralement stabilisée, le test PDF audit réceptacles devrait être
un travail de restitution.

### v1.1.0 — Module Réceptacles (SP19 : test PDF audit + golden PDF)

**État final (20/05/2026) : v1.1.0 complète.** Dernière sous-passe
livrée. Le module Réceptacles est désormais couvert par le même
niveau d'assertions PDF que les 4 régimes v1.0.1 (TNS, Assimilé,
Libéral SELARL/SELAS, Comparateur).

**Intuition utilisateur validée pour la 3ème fois :**

> *SP19 (audit PDF réceptacles) devrait être essentiellement un
> travail de restitution, pas de stabilisation métier.*

Confirmé empiriquement :
- **0 nouvelle décision doctrinale** prise pendant SP19
- **0 modification des modules métier** SP15-SP17
- **0 modification de l'orchestrateur** SP18
- **0 modification du framework** `ui/pdf_audit_export.py`
- **0 modification du helper SP7** `test_pdf_audit_render_common.py`
- **+1 nouveau fichier de test** réutilisant 100 % du helper SP7
- **+1 fonction `construire_trace_receptacles`** dans le test SP11
- **+1 cas dans `CAS_GOLDEN`** (golden PDF réceptacles)
- **+86 contrôles** PDF audit-ready
- **+1 golden PDF** stable

**Livrables SP19 :**

- `test_pdf_audit_render_receptacles.py` (nouveau, ~430 lignes)
  - Construction trace orchestrateur cas standard (Q1=a : 1 cas)
  - **10 sections d'assertions communes** (helper SP7) couvrant :
    PDF valide, couverture, KPIs, bandeau intro sommaire, sommaire
    paginé, signets hiérarchisés, no_declaratif, 14 patterns non
    prescriptifs, neutralité structurelle, calibrage dynamique
  - **7 sections spécifiques Réceptacles** :
    - Récep-1 (5 contrôles) : structure de la trace (3 enveloppes
      N1 + 9 horizons N2, ordre stable PERIN → PEE → PERECO)
    - Récep-2 (3 contrôles) : étapes méta SP14 + RECAP SP18
      (présence 5 codes méta + 9 codes RECAP, valeur scalaire = 3)
    - Récep-3 (5 contrôles) : codes namespace REC_<ENV>_*, REC_meta_*,
      REC_RECAP_* rendus dans le PDF
    - Récep-4 (2 contrôles) : ordre stable PERIN → PEE → PERECO
      vérifié dans le PDF (position des signets) ET dans la trace
      (clés d'hypothèses RECAP)
    - Récep-5 (5 contrôles) : wordings doctrinaux rendus (disclaimer
      comparabilité, convention rendement, déductibilité IR PERIN,
      abondement PEE, disponibilité retraite PERECO)
    - Récep-6 (1 contrôle) : aucun mot interdit (garde-fou SP18)
      dans le contexte réceptacles du PDF (score, ranking, optimal,
      recommandation, préconisation, efficacité)
    - Récep-7 (1 contrôle) : profondeur du graphe = 2
  - Total : **86 contrôles**

- `test_pdf_audit_render_goldens.py` (étendu) :
  - Import `allocation_receptacles` ajouté
  - Fonction `construire_trace_receptacles` nouvelle (~25 lignes,
    cas standard cohérent avec mini-golden orchestrateur SP18)
  - Cas `receptacles` ajouté à `CAS_GOLDEN`
  - **6ème golden PDF** : `golden_pdfs/golden_receptacles.json`
    - 21 pages
    - 109 étapes racine
    - 109 codes racines (tous uniques)
    - 13 signets

**Décisions architecturales validées SP19 :**

- **Q1 = (a)** Périmètre minimal : 1 cas standard. Les calculs étant
  déjà protégés par les 5 mini-goldens métier (anti-régression
  économique) et 130 contrôles structurels (anti-régression
  structure), SP19 se concentre sur la **restitution PDF**.
- **Q2 = (a)** Réutilisation du helper SP7 sans enrichissement.
  Le framework helper reste intact.
- **Q3 = (a)** Ajout du 6ème golden PDF aligné sur `composition_5000`.
  Cohérence SP11 (chaque famille de PDF a son golden structurel).

**Métriques v1.1.0 finales (cumulées) :**

| Test | Contrôles | Statut |
|---|---|---|
| `test_pdf_audit_render_tns.py` (pilote figé) | 93/93 | ✓ |
| `test_pdf_audit_render_assimile.py` (SP7) | 71/71 | ✓ |
| `test_pdf_audit_render_liberal.py` (SP7) | 148/148 | ✓ |
| `test_pdf_audit_render_comparateur_regimes.py` (SP8) | 83/83 | ✓ |
| `test_pdf_audit_render_receptacles.py` (SP19) | **86/86** | ✓ |
| `test_renderer_invariants.py` (SP10) | 51/51 | ✓ |
| `test_pdf_audit_render_goldens.py` (SP11+SP19) | **6/6 goldens PDF** | ✓ |
| `test_renderer_stress.py` (SP12) | 43/43 | ✓ |
| `test_strategy_receptacles.py` (SP14→SP18) | 130/130 | ✓ |
| `test_strategy_receptacles_goldens.py` (SP15→SP18) | 5/5 goldens métier | ✓ |
| **TOTAL post-SP19 (v1.1.0 finale)** | **705 contrôles + 6 goldens PDF + 5 goldens métier** | **✓** |

**Aucune sous-passe v1.1.0 restante. v1.1.0 complète.**

### v1.1.0 — Synthèse globale (clôture)

**État final livré :**

| Périmètre | Livré |
|---|---|
| **Doctrine** | `ARCHITECTURE_RECEPTACLES.md` (860 lignes, 17 décisions D-R + tableau §3.6 cross-enveloppes) |
| **Modules métier** | 3 modules réels (PERIN/PEE/PERECO, ~1 250 lignes Python) |
| **Wordings centralisés** | 16 wordings figés (3 transverses + 4 PERIN + 4 PEE + 5 PERECO) |
| **Orchestrateur opérationnel** | Composition passive + 9 étapes RECAP cross-enveloppes |
| **Test PDF audit dédié** | 86 contrôles structurels + 7 sections spécifiques |
| **Golden PDF** | 6 goldens (5 v1.0.1 + 1 réceptacles v1.1.0) |
| **Mini-goldens métier** | 5 goldens JSON (2 PERIN + 1 PEE + 1 PERECO + 1 ORCH) |
| **Tests cumulés** | 705 contrôles |

**Préservation absolue de v1.0.1 (vérifiée à chaque sous-passe) :**

- 0 modification de `ui/pdf_audit_export.py` (framework renderer)
- 0 modification de `core/audit.py` (grammaire TraceAudit)
- 0 modification de `core/profil.py`
- 0 modification de `doctrine.py`
- 0 modification du legacy `strategy/perin.py` (consommé via provider)
- 0 modification des 4 tests PDF v1.0.1 (TNS pilote, Assimilé, Libéral, Comparateur)
- 0 modification des 3 tests Hardening SP10/SP11/SP12 du périmètre v1.0.0
- 0 modification du helper SP7 `test_pdf_audit_render_common.py`
- 0 modification d'`ARCHITECTURE_RENDERER.md`
- 0 modification des 5 goldens PDF v1.0.0 (preuve forte : strictement
  conformes après 7 sous-passes v1.1.0)
- 0 modification de `compare_baseline.py`, hash `8863991f27f67847` inchangé
- 0 régression sur 504 outputs `baseline_tests`

**Garanties principielles tenues :**

| Garantie | Source | État |
|---|---|---|
| α stricte (calculs métier intouchés) | SP9 doctrine | ✓ |
| γ bump conditionnel (extension structurée) | SP13 doctrine | ✓ |
| D-R6 orchestrateur passif | SP13 D-R6 | ✓ (testé en 10.3) |
| D-R10 aucune étape parent_id != None | SP13 D-R10 | ✓ (testé partout) |
| D-R12 pas de dimensionneur, pas de prescription | SP13 D-R12 | ✓ (testé en 16.5) |
| Stabilité d'ordre PERIN → PEE → PERECO | SP18 garde-fou | ✓ (testé en 16.3, Récep-4) |
| Aucun mot interdit (score, optimal, etc.) | SP18 garde-fou | ✓ (testé en 16.5, Récep-6) |
| Invariants algébriques | SP15 Q7 | ✓ (testé silencieusement partout) |
| Wordings centralisés | SP13 D-R3 | ✓ (16 wordings centralisés) |
| Orthogonalité PERIN/PEE/PERECO | SP17 §3.6 | ✓ (testé en 15.3-15.7) |
| Comparabilité dataclass cross-enveloppes | SP16 garde-fou | ✓ (testé en 13.24-25, 15.1-2) |

**Méthodologie tenue de bout en bout :**

| Discipline | État |
|---|---|
| Cadrage Q1-Qn avant chaque sous-passe | ✓ 7 sous-passes, 27 questions arbitrées |
| Validation utilisateur explicite avant code | ✓ Aucun code écrit sans feu vert |
| Auto-scan 14 patterns avant chaque commit | ✓ Toutes occurrences justifiées |
| Surgical edits (str_replace) plutôt que rewrites | ✓ |
| Test régression à chaque étape | ✓ 0 régression cumulée v1.0.1 |
| Documentation au fil de l'eau (KNOWN_LIMITATIONS) | ✓ ~600 lignes ajoutées v1.1.0 |

**Note méthodologique finale (intuition utilisateur trois fois validée) :**

Vous aviez prédit :
- En SP15 : *« le moment où tu introduis 2 % / 4 % / 6 % est le moment
  où l'utilisateur commence à optimiser un scénario financier »*
  → validé : aucune dérive vers la simulation patrimoniale
- En SP17 : *« si SP17 tient proprement, alors SP18 (orchestrateur
  cross-enveloppes) sera surtout un travail de composition »*
  → validé en SP18 (composition pure, 0 doctrine nouvelle)
- En SP18 : *« si SP18 reste purement descriptif, alors SP19 (audit
  PDF réceptacles) devrait être essentiellement un travail de
  restitution »*
  → validé en SP19 (restitution pure, 0 doctrine nouvelle)

Ces trois prédictions successives valident l'architecture
méthodologique :
1. Stabiliser la doctrine (SP13)
2. Construire les modules métier indépendamment (SP15-SP17)
3. Composer après stabilisation (SP18)
4. Restituer après composition (SP19)

Chaque étape hérite d'une plateforme stable et n'a pas à arbitrer
de questions tranchées en amont. C'est précisément le bénéfice du
découpage SP13 → SP19.

### v1.1.1 — Stabilisation de gouvernance (debt cleanup doctrinal)

**État final (20/05/2026) :** v1.1.1 clôturée. Les deux dettes
techniques résiduelles (G4-filles et Unicode-glyphes) sont
**transformées en positions doctrinales stables** pour toute la
branche v1.x.

**Apport méthodologique structurant (votre formulation) :**

> *v1.1.1 doit être vu comme une « stabilisation de gouvernance ».
> Pas seulement un nettoyage. Vous êtes en train de transformer des
> découvertes, des arbitrages, des limites, en positions doctrinales
> stables.*

Cette formulation a guidé les 4 étapes de v1.1.1. Le livrable n'est
pas un patch de bug, c'est un **engagement de stabilité** sur des
choix d'architecture.

**Livrables v1.1.1 :**

- `ARCHITECTURE_RENDERER.md` (modifié, §2.1 G4 reformulée)
  - Garantie G4 reformulée : « **Préservation du graphe racine +
    exclusion doctrinale des étapes filles** »
  - Position doctrinale explicite : *« Les étapes `parent_id != None`
    sont considérées comme des artefacts internes de calcul et non
    comme des unités d'audit cabinet »*
  - 3 justifications convergentes documentées (D-R10 du dépôt
    réceptacles, cohérence d'audit, coût/bénéfice)
  - **Engagement de stabilité v1.x** : refonte hiérarchique reportée
    à une éventuelle bascule v2.x

- `test_renderer_invariants.py` (modifié, INV-G4.b retiré)
  - Suppression de l'invariant temporaire INV-G4.b (était un
    placeholder destiné à tomber au moment du traitement de la dette)
  - Note explicative de 25 lignes documentant le retrait et la
    décision doctrinale sous-jacente
  - INV-G4.a maintenu (valide la présence des étapes racines)
  - Total invariants : 51 → **50** (retrait propre)

- `test_renderer_stress.py` (étendu, cas P2 formalisé)
  - Cas P2 (Unicode exotique) transformé de « pathologique
    observation » en « comportement assumé v1.x »
  - Position doctrinale figée : *« Le renderer garantit la stabilité
    du PDF en présence de glyphes non supportés, mais pas leur
    restitution visuelle »*
  - 3 garanties contractuelles testées explicitement :
    - Pas de crash (`_verifier_absence_crash`)
    - PDF structurellement valide (magic %PDF-, %%EOF, taille ≥ 1 ko)
    - Codes ASCII préservés extractibles malgré présence de glyphes
      non-latins dans les labels
  - 6 nouveaux sous-contrôles : P2.struct.1/2/3 + P2.contrat.1/2/3
  - Total stress : 43 → **49** (+6 contrôles)

- `KNOWN_LIMITATIONS.md` (refondé en tête)
  - **Section 0 nouvelle** : Table de bord des dettes (vue v1.1.1)
  - Structure standardisée par dette : ID, Catégorie, Description,
    Statut, Introduite, Décision, Horizon cible
  - 3 statuts définis : **Active** (à traiter), **Clôturée**
    (résolue par décision doctrinale), **Frontière** (refus
    doctrinal assumé)
  - 3 catégories : Fonctionnelle, Technique, Doctrinale
  - 13 entrées totales :
    - **2 dettes clôturées en v1.1.1** : G4-filles, Unicode-glyphes
    - **10 dettes actives** : 7 fonctionnelles réceptacles
      (REC-D1 à REC-D7) + 3 doctrinales/techniques (DOC-D1, DOC-D2,
      DOC-D3)
    - **1 frontière doctrinale** : FRONT-1 absence de moteur
      prescriptif (votre apport SP19)
  - Indicateurs de gouvernance : compteurs par statut, métriques
    tests
  - Journal historique des sous-passes **conservé** en queue (pas de
    suppression, traçabilité préservée)

**Décisions architecturales v1.1.1 validées :**

| Bloc | Décision | Source |
|---|---|---|
| A — G4 | **(β)** Formalisation doctrinale, retrait INV-G4.b | A-Q1 |
| B — Unicode | **(γ+)** Documentation + test défensif P2 enrichi | B-Q1 |
| C-Q1 — KNOWN_LIMITATIONS | **(β)** Reclassement en place avec table de bord | C-Q1 |
| C-Q2 — Classification | Validée + ajout FRONT-1 frontière prescriptive | C-Q2 |
| D — Discipline | **(a)** Batterie complète à chaque étape | D-Q1 |

**Apport doctrinal utilisateur (FRONT-1) :**

Votre ajout explicite de la frontière *« Absence de moteur de
recommandation/prescription »* est précieux à 3 titres :

1. **Doctrinal** : matérialise un refus assumé là où d'autres
   produits glissent silencieusement vers le conseil.
2. **Juridique/déontologique** : préserve le mandat actuel (outil
   descriptif) face à un éventuel glissement vers un statut de
   conseil financier (régime juridique distinct).
3. **Commercial** : positionne clairement l'outil comme aide à la
   décision cabinet, pas comme automatisation de décision.

Cette frontière est gardée techniquement par :
- D-R12 + D-R6 (`ARCHITECTURE_RECEPTACLES.md`)
- 14 patterns proscrits (`doctrine.py` §6.2)
- 86 contrôles SP19 dont Récep-6.1 (aucun mot interdit dans PDF)
- 130 contrôles SP14-SP18 dont 16.5 (aucun mot interdit dans hypothèses)

**Préservation absolue v1.0.1 + v1.1.0 :**

- 0 modification du framework `ui/pdf_audit_export.py`
- 0 modification de `core/audit.py`, `core/profil.py`, `doctrine.py`
- 0 modification des modules métier `strategy/receptacles_*.py`
- 0 modification de l'orchestrateur `strategy/receptacles_orchestrateur.py`
- 0 modification du dataclass `LigneHorizonReceptacle`
- 0 modification des 6 goldens PDF (5 v1.0.1 + 1 v1.1.0)
- 0 modification des 5 mini-goldens métier
- 0 modification des fichiers de test figés v1.0.1 (SP6-SP8 pilotes)
- 0 modification du helper SP7
- hash baseline `8863991f27f67847` strictement préservé

**Modifications v1.1.1 (3 fichiers seulement) :**

| Fichier | Type modification |
|---|---|
| `ARCHITECTURE_RENDERER.md` | Reformulation G4 §2.1 (~40 lignes) |
| `test_renderer_invariants.py` | Retrait INV-G4.b, note explicative (~25 lignes) |
| `test_renderer_stress.py` | Cas P2 formalisé avec 3 garanties contractuelles (+50 lignes) |
| `KNOWN_LIMITATIONS.md` | Table de bord en tête + section clôture v1.1.1 (~280 lignes) |

**Métriques de clôture v1.1.1 :**

| Suite | Avant v1.1.1 (post-SP19) | Après v1.1.1 | Δ |
|---|---|---|---|
| compare_baseline | hash `8863991f27f67847` ✓ | hash inchangé ✓ | — |
| check_imports | 22 fichiers | 22 fichiers | — |
| baseline_tests outputs | 504/504 | 504/504 | — |
| backward_compat | 23/23 | 23/23 | — |
| pdf_render_all_regimes | 64/64 | 64/64 | — |
| 4 audits sémantiques | 4/4 | 4/4 | — |
| 13 MODE_AUDIT | 13/13 | 13/13 | — |
| 5 PDF audit tests | 93+71+148+83+86 = 481 | 481 | — |
| `test_renderer_invariants` | 51 | **50** | **−1** (INV-G4.b retiré) |
| `test_renderer_stress` | 43 | **49** | **+6** (P2 enrichi) |
| Goldens PDF SP11 | 6/6 conformes | 6/6 conformes | — |
| `test_strategy_receptacles` | 130/130 | 130/130 | — |
| `test_strategy_receptacles_goldens` | 5/5 conformes | 5/5 conformes | — |
| **TOTAL contrôles fonctionnels** | 705 | **710** | **+5 nets** |

**Bilan méthodologique v1.1.1 :**

| Discipline | État |
|---|---|
| Cadrage Q1-Qn avant écriture | ✓ 5 questions arbitrées (A-Q1, B-Q1, C-Q1, C-Q2, D-Q1) |
| Validation utilisateur explicite avant code | ✓ Aucune ligne écrite sans feu vert |
| Auto-scan 14 patterns à chaque commit | ✓ Toutes occurrences justifiées (citations négatives) |
| Surgical edits (str_replace) | ✓ 0 réécriture massive |
| Batterie complète à chaque étape | ✓ (D-Q1 = a) 3 batteries complètes + 1 finale |
| 0 régression sur v1.0.1 + v1.1.0 | ✓ |
| Documentation au fil de l'eau | ✓ Cette section |

**Note méthodologique finale v1.1.1 :**

L'enchaînement v1.0.0 → v1.0.1 → v1.1.0 → v1.1.1 illustre une
maturité progressive du dépôt :

1. **v1.0.0** : livrable fonctionnel initial (modules métier + PDF)
2. **v1.0.1** : phase Hardening (doctrine + invariants + goldens +
   stress)
3. **v1.1.0** : extension métier (module Réceptacles complet)
4. **v1.1.1** : stabilisation de gouvernance (dettes → positions
   doctrinales)

À ce stade, l'outil dispose à la fois d'un **moteur fonctionnel**,
d'un **framework testé**, d'une **doctrine explicite**, et d'une
**gouvernance des dettes**. C'est l'état recommandé avant
d'entamer la prochaine extension fonctionnelle.

**Prochain chantier prévu : v1.2 UI Streamlit Réceptacles** (REC-D7
dans la table de bord). C'est la suite la plus utile commercialement :
valorisation immédiate du travail v1.1 sans ouvrir trop tôt la
complexité réglementaire (REC-D1 à REC-D6 reportées).

### v1.2 — UI Streamlit Réceptacles, Phase 1 (SP20 : Lecture cabinet)

**État partiel (20/05/2026) :** v1.2 démarrée. La phase 1 (Lecture
cabinet) est livrée. Les phases 2 (Auditabilité visible) et 3
(Navigation audit) restent à venir en SP21 et SP22.

**Principe directeur (votre formulation) :**

> *SP20 va être beaucoup plus un chantier de gouvernance UX que de
> Streamlit. Le vrai enjeu maintenant n'est plus technique. C'est :
> préserver la neutralité doctrinale jusque dans l'expérience
> utilisateur.*

Cette formulation a guidé toute la sous-passe SP20. La doctrine UI
a été écrite en premier, les anti-patterns ont été nommés avant
toute ligne de Streamlit, les invariants UI ont été gravés en tests
automatisés.

**Livrables SP20 :**

- `ARCHITECTURE_UI_RECEPTACLES.md` (nouveau, 431 lignes)
  - Squelette doctrinal SP20 (option I), à étendre en SP21/SP22
  - 7 sections : Principes / Responsabilités UI vs Moteur /
    Architecture 3 couches / **Anti-patterns interdits (section
    centrale, 8 anti-patterns détaillés)** / Composants autorisés
    (court, illustratif) / Invariants UI testables / Tests applicables
  - 2 décisions D-UI-1 (adapter pur) + D-UI-2 (Streamlit muet en calcul)
  - 5 invariants UI-I1 à UI-I5

- `ui/adapter_receptacles.py` (nouveau, ~340 lignes)
  - **Couche 2 / frontière doctrinale** entre moteur et Streamlit
  - Conforme D-UI-1 : pur, déterministe, sans Streamlit, sans
    enrichissement métier
  - 5 fonctions de transformation pure :
    - `enveloppes_dans_ordre_doctrinal()` — provider UI-I1
    - `extraire_tableau_multi_horizon()` — DataFrame 9 lignes
      (3 enveloppes × 3 horizons) dans l'ordre fixe
    - `extraire_tableau_par_horizon()` — DataFrame pivoté
      (1 enveloppe par ligne pour 1 horizon)
    - `extraire_etapes_recapitulatives()` — extraction des 9 étapes
      RECAP SP18 avec ordre stable explicite (listes ordonnées de
      tuples)
    - `extraire_hypotheses_doctrinales()` — extraction des
      hypothèses moteur (rendement, TMI, plafonds) pour SP21
    - `compter_etapes_pour_pdf()` — comptage informatif pour SP22

- `ui/composants_receptacles.py` (nouveau, ~310 lignes)
  - **Couche 3a / composants Streamlit réutilisables**
  - Conforme §5.1 (composants autorisés uniquement)
  - 2 composants principaux :
    - `tableau_multi_horizon(df)` — affichage du DataFrame multi-horizon
    - `tableau_par_horizon(df, h)` — affichage pivoté
  - 3 disclaimers neutres : périmètre, comparabilité, convention rendement
  - 1 widget de saisie : `saisir_inputs_orchestrateur()`
  - 2 utilitaires : `formater_euro`, `formater_pourcentage` (format
    français : « 4 806,00 € », « 30,0 % »)

- `ui/page_receptacles.py` (nouveau, ~145 lignes)
  - **Couche 3b / page entry-point**
  - Orchestre l'UX : saisie → délégation orchestrateur → adapter →
    composants
  - Aucun calcul. Aucune dérivation. Aucun import direct des modules
    enveloppe.
  - Titre figé : **« 🧰 Réceptacles auditables »** (votre apport A-Q1)
  - 2 vues : tableau multi-horizon + onglets par horizon (5/10/20 ans)

- `app.py` (modifié, intégration minimaliste)
  - 1 import : `from ui.page_receptacles import page_receptacles as _page_receptacles_v11`
  - 1 entrée dans `PAGES` : `"🧰 Réceptacles auditables": "receptacles_v11"`
  - 1 fonction wrapper : `page_receptacles_auditables()` qui appelle
    `build_profil()` puis délègue
  - 1 entrée dans `ROUTES` : `"receptacles_v11": page_receptacles_auditables`
  - Aucune modification des 9 pages existantes (préservation v1.0)

- `test_ui_receptacles_neutralite.py` (nouveau, ~330 lignes)
  - Couvre les 5 invariants UI-I1 à UI-I5
  - **Auto-scan textuel avec whitelist explicite** (§7.2) : distingue
    les chaînes en argument de `Call` AST (= visibles utilisateur,
    scannées strictement) des docstrings (exemptées)
  - 24 contrôles structurés en 7 sections :
    - Préliminaire : existence des 3 fichiers UI (3 contrôles)
    - UI-I1 : ordre fixe doctrinal (6 contrôles, vérifié à la fois sur
      les constantes et empiriquement sur le résultat adapter)
    - UI-I2 : mots interdits dans chaînes visibles (3 contrôles)
    - UI-I3 : imports métier interdits depuis Streamlit (2 contrôles)
    - UI-I4 : adapter sans Streamlit (2 contrôles)
    - UI-I5 : composants à connotation valeur interdits (3 contrôles)
    - UI-I5 bis : emojis valorisants interdits (3 contrôles)
    - Bonus : déterminisme + pureté adapter (2 contrôles)

**Décisions architecturales SP20 validées :**

| Bloc | Décision | Source |
|---|---|---|
| A-Q1 — Cohabitation | **(α)** Nouvelle page dédiée, l'ancien comparateur intact | A-Q1 |
| B-Q1 — Architecture | **(γ)** 3 couches (page + composants + adapter pur) | B-Q1 |
| C-Q1 — Granularité | **(a)** SP20/SP21/SP22 distincts | C-Q1 |
| D-Q1 — Doctrine | **(I)** Squelette minimal avec anti-patterns détaillés | D-Q1 |
| E-Q1 — Test neutralité | **(a)** Auto-scan textuel avec whitelist | E-Q1 |
| F-Q1 — Discipline relance | **(a)** Batterie complète à chaque étape | F-Q1 |

**Apports doctrinaux utilisateur intégrés en SP20 :**

| Apport | Implémentation |
|---|---|
| Nom UI clair « 🧰 Réceptacles auditables » | Constante `TITRE_PAGE` + entrée `PAGES` dans `app.py` |
| Adapter pur sans Streamlit ni enrichissement métier | D-UI-1, UI-I4 testé, 0 import streamlit dans adapter |
| Composants interdits : liste illustrative non limitative | §4.2 / §4.3 / §4.4 doctrine + 6 contrôles UI-I5 + UI-I5 bis |
| UI descriptive, pas émotionnelle | Principe directeur §1.1, gravé en doctrine |
| Invariant ordre fixe doctrinal | UI-I1 §6.1, 6 contrôles dédiés |
| Whitelist explicite citations doctrinales | §7.2, distinction AST chaînes visibles vs docstrings |

**Préservation absolue v1.0 + v1.1.x :**

- 0 modification du framework `ui/pdf_audit_export.py`
- 0 modification de `core/audit.py`, `core/profil.py`, `doctrine.py`
- 0 modification des modules métier `strategy/receptacles_*.py`
- 0 modification du dataclass `LigneHorizonReceptacle`
- 0 modification des 6 goldens PDF
- 0 modification des 5 mini-goldens métier
- 0 modification des 9 pages Streamlit existantes
- 0 modification des tests v1.0.1 / v1.1.0 / v1.1.1
- hash baseline `8863991f27f67847` strictement préservé

**Modifications SP20 (5 fichiers + 1 test) :**

| Fichier | Type | Volume |
|---|---|---|
| `ARCHITECTURE_UI_RECEPTACLES.md` | Création | 431 lignes |
| `ui/adapter_receptacles.py` | Création | ~340 lignes |
| `ui/composants_receptacles.py` | Création | ~310 lignes |
| `ui/page_receptacles.py` | Création | ~145 lignes |
| `app.py` | Intégration | +20 lignes (imports + PAGES + ROUTES + wrapper) |
| `test_ui_receptacles_neutralite.py` | Création | ~330 lignes |
| `KNOWN_LIMITATIONS.md` | Mise à jour REC-D7 + section clôture | +200 lignes |

**Métriques de clôture SP20 (v1.2 phase 1) :**

| Suite | Avant SP20 (post-v1.1.1) | Après SP20 | Δ |
|---|---|---|---|
| compare_baseline | hash `8863991f27f67847` ✓ | hash inchangé ✓ | — |
| check_imports | 22 fichiers | 22 fichiers (couche UI hors scope) | — |
| baseline_tests outputs | 504/504 | 504/504 | — |
| 4 audits sémantiques | 4/4 | 4/4 | — |
| 13 MODE_AUDIT | 13/13 | 13/13 | — |
| 5 PDF audit tests | 481/481 | 481/481 | — |
| `test_renderer_invariants` | 50/50 | 50/50 | — |
| `test_renderer_stress` | 49/49 | 49/49 | — |
| Goldens PDF | 6/6 conformes | 6/6 conformes | — |
| `test_strategy_receptacles` | 130/130 | 130/130 | — |
| Mini-goldens métier | 5/5 conformes | 5/5 conformes | — |
| **`test_ui_receptacles_neutralite`** (nouveau) | — | **24/24** | **+24** |
| **TOTAL contrôles fonctionnels** | **710** | **734** | **+24** |
| Régressions sur baseline v1.0.1 + v1.1.x | 0 | **0** | — |

**Sous-passes v1.2 restantes :**

- **SP21** — Phase 2 : Auditabilité visible (panneau hypothèses
  doctrinales : rendement, TMI, plafonds, taux abondement, par
  enveloppe). Réutilisation de `extraire_hypotheses_doctrinales`
  déjà livré en SP20.
- **SP22** — Phase 3 : Navigation audit (lien direct vers le PDF
  cabinet, affichage des étapes structurantes, navigation par
  signets). Réutilisation de `compter_etapes_pour_pdf` déjà livré
  en SP20.

**Bilan méthodologique SP20 :**

| Discipline | État |
|---|---|
| Cadrage Q1-Qn avant écriture | ✓ 6 questions arbitrées (A-Q1 à F-Q1) |
| Validation utilisateur explicite avant code | ✓ Aucune ligne écrite sans feu vert |
| Auto-scan 14 patterns à chaque commit | ✓ Toutes occurrences justifiées (citations négatives + reformulation L222 disclaimer) |
| Surgical edits sur `app.py` | ✓ 4 modifications ciblées, 0 refonte des 9 pages existantes |
| Batterie complète à chaque étape (F-Q1=a) | ✓ 6 batteries complètes successives |
| 0 régression sur v1.0 + v1.1.x | ✓ |
| Frontière doctrinale matérialisée techniquement | ✓ adapter pur sans Streamlit (D-UI-1) |
| Anti-patterns nommés AVANT le code | ✓ doctrine écrite en étape 1 |

**Note méthodologique SP20 (votre intuition confirmée) :**

> *Le vrai enjeu maintenant n'est plus technique. C'est : préserver
> la neutralité doctrinale jusque dans l'expérience utilisateur.*

À la sortie de SP20 :
- **8 anti-patterns nommés et documentés** dans la doctrine UI
- **5 invariants UI testables** gravés en tests automatisés (24/24)
- **0 emoji valorisant** dans les chaînes affichées
- **0 composant à connotation valeur** (st.success, st.balloons,
  st.toast, st.snow) utilisé
- **Ordre fixe doctrinal PERIN → PEE → PERECO** vérifié à 6 endroits
- **Adapter pur sans Streamlit** matérialise la frontière
- **Reformulation immédiate d'une dérive** détectée par l'auto-scan
  (L222 composants : « sans recommandation » → « strictement
  descriptive »)

L'enjeu de gouvernance UX est traité **par construction**, pas par
discipline ponctuelle. La doctrine + les tests rendront les futures
contributions UI **incapables** de glisser vers le prescriptif sans
faire échouer les tests automatisés.

### v1.2 — UI Streamlit Réceptacles, Phase 2 (SP21 : Auditabilité visible)

**État partiel (20/05/2026) :** SP21 livrée. v1.2 progresse — les
phases 1 (SP20) et 2 (SP21) sont livrées. Phase 3 (SP22, Navigation
audit) reste à venir.

**Principe directeur (votre formulation SP21) :**

> *SP21 est maintenant essentiellement un exercice de précision
> sémantique. La qualité de SP21 dépendra surtout du langage utilisé.
> Plus encore que des composants Streamlit ou du code lui-même.
> C'est maintenant un problème de doctrine UX appliquée.*

Cette formulation a guidé toute la sous-passe SP21. Le travail n'a
pas porté sur du nouveau code Streamlit (l'`expander` était trivial),
mais sur **15 mots à interdire**, **2 anti-patterns à graver en
doctrine**, et **1 invariant à tester sur tous les fichiers UI**.

**Apports doctrinaux utilisateur intégrés en SP21 :**

| Apport | Implémentation |
|---|---|
| Hypothèses visibles mais non dominantes (caption + dépliable) | `st.expander("Hypothèses doctrinales utilisées", expanded=False)` |
| Variante hybride (a) : conventions transverses + hypothèses par enveloppe | 2 composants `tableau_conventions_transverses` + `tableau_hypotheses_par_enveloppe` |
| Liste 15 mots interdits (dont +2 user : « efficace » et « idéal ») | `PATTERNS_INTERDITS_SP21` + doctrine §4.6 bis |
| Scan global UI-I6 sur tous les fichiers UI | `test_ui_receptacles_neutralite.py` section UI-I6 (3 contrôles) |
| Aucune phrase interprétative autour des tableaux | Phrase introductive figée : « Hypothèses doctrinales utilisées pour les calculs. » + anti-pattern collatéral documenté §4.6 bis |
| Neutralité chromatique stricte (documentation) | §4.4 bis ajoutée à la doctrine, périmètre testé via UI-I5 existant |

**Anti-pattern type SP21 (votre apport critique) :**

| Interdit | Bonne formulation |
|---|---|
| « Le rendement 2 % est prudent. » | « Convention de capitalisation utilisée : 2 %. » |
| « Ces hypothèses permettent de contextualiser les résultats. » | « Hypothèses doctrinales utilisées pour les calculs. » |

Ces deux exemples sont **gravés en doctrine** dans `ARCHITECTURE_UI_RECEPTACLES.md` §4.6 bis comme anti-patterns explicites.

**Livrables SP21 :**

- `ARCHITECTURE_UI_RECEPTACLES.md` (modifié, +136 lignes, 431 → 567 lignes)
  - §4.4 bis nouvelle : Sémantique chromatique implicite — neutralité chromatique stricte (gris, bleu neutre, pas de vert/rouge/orange)
  - §4.6 bis nouvelle : Qualification subjective des hypothèses — 15 mots interdits + anti-pattern « audit → justification » + anti-pattern « phrase d'introduction interprétative »
  - §6.6 nouveau : Invariant UI-I6 — scan global du vocabulaire de qualification subjective sur tous les fichiers UI

- `ui/adapter_receptacles.py` (correction mineure, +6 lignes)
  - Correction du bug SP20 : clé `horizons_annees` (alignée avec l'orchestrateur) au lieu de `horizons` qui retournait `None` silencieusement
  - Test bonus SP21 valide la correction

- `ui/composants_receptacles.py` (extension, +145 lignes, 319 → 464 lignes)
  - 1 constante `LABELS_HYPOTHESES_ENVELOPPES` (5 hypothèses paramétriques par enveloppe)
  - 1 helper `_formater_valeur_hypothese` (format adapté selon nature : Oui/Non, %, €)
  - 3 nouveaux composants :
    - `tableau_conventions_transverses(hypotheses)` : 5 lignes max (rendement, capitalisation, horizons, flux, nb enveloppes)
    - `tableau_hypotheses_par_enveloppe(hypotheses)` : tableau long 3 colonnes (Enveloppe / Hypothèse / Valeur), ordre fixe PERIN → PEE → PERECO
    - `panneau_hypotheses_doctrinales(hypotheses)` : panneau complet avec phrase d'introduction strictement descriptive
  - Aucun usage de mot interdit SP18 ni SP21 (0 occurrence sur 29 patterns)

- `ui/page_receptacles.py` (extension, +9 lignes, 161 → 170 lignes)
  - Import de `panneau_hypotheses_doctrinales`
  - Bloc « Vue 3 : Auditabilité visible » avec `st.expander("Hypothèses doctrinales utilisées", expanded=False)`
  - Conforme A-Q1=β : panneau replié par défaut (visible mais non dominant)

- `test_ui_receptacles_neutralite.py` (extension, +85 lignes, ~330 → ~415 lignes)
  - Constante `PATTERNS_INTERDITS_SP21` : 14 patterns SP21 (les 15 mots dédupliqués avec ceux de SP18 : « optimisé », « avantageux », « idéal » déjà couverts)
  - Section UI-I6 : scan global sur les 3 fichiers UI (3 contrôles)
  - Section Bonus SP21 : 9 contrôles (6 hypothèses extraites correctement + 3 composants exposés)
  - Total : 24 → **36 contrôles** (+12)

- `KNOWN_LIMITATIONS.md` (modifié)
  - REC-D7 mis à jour : Phase 2 livrée
  - Section clôture SP21 ajoutée

**Décisions architecturales SP21 validées :**

| Bloc | Décision | Source |
|---|---|---|
| A-Q1 — Granularité | **(β)** Indicateurs minimaux visibles (caption) + détails dépliables | A-Q1 |
| B-Q1 — Format tableau | **(α)** Tableau long (Enveloppe / Hypothèse / Valeur) | B-Q1 |
| B-Q2 — Conventions | **(a)** Variante hybride : conventions transverses + hypothèses par enveloppe | B-Q2 (votre apport explicite) |
| C-Q1 — Vocabulaire | **(γ)** Doctrine UI locale + test UI, pas SP18 | C-Q1 |
| C-Q2 — Expressions | **(b)** Mots seuls suffisent | C-Q2 |
| D-Q1 — Couleurs | **(α)** Documentation + réutilisation UI-I5 | D-Q1 |
| E-Q1 — Discipline relance | **(a)** Batterie complète à chaque étape | E-Q1 |
| UI-I6 portée | Scan global tous fichiers UI | Question subsidiaire (votre apport) |

**Préservation absolue v1.0 + v1.1.x + SP20 :**

- 0 modification du framework `ui/pdf_audit_export.py`
- 0 modification de `core/audit.py`, `core/profil.py`, `doctrine.py`
- 0 modification des modules métier `strategy/receptacles_*.py`
- 0 modification de `app.py` (l'intégration SP20 reste suffisante)
- 0 modification des 6 goldens PDF
- 0 modification des 5 mini-goldens métier
- 0 modification des 9 pages Streamlit existantes
- 0 modification des tests v1.0.1 / v1.1.0 / v1.1.1
- 0 modification de `tableau_multi_horizon`, `tableau_par_horizon` (SP20)
- hash baseline `8863991f27f67847` strictement préservé

**Métriques de clôture SP21 (v1.2 phase 2) :**

| Suite | Avant SP21 (post-SP20) | Après SP21 | Δ |
|---|---|---|---|
| compare_baseline | hash `8863991f27f67847` ✓ | hash inchangé ✓ | — |
| check_imports | 22 fichiers | 22 fichiers | — |
| baseline_tests outputs | 504/504 | 504/504 | — |
| 4 audits sémantiques | 4/4 | 4/4 | — |
| 13 MODE_AUDIT | 13/13 | 13/13 | — |
| 5 PDF audit tests | 481/481 | 481/481 | — |
| Renderer invariants | 50/50 | 50/50 | — |
| Renderer stress | 49/49 | 49/49 | — |
| Goldens PDF | 6/6 conformes | 6/6 conformes | — |
| Strategy réceptacles | 130/130 | 130/130 | — |
| Mini-goldens métier | 5/5 conformes | 5/5 conformes | — |
| **`test_ui_receptacles_neutralite`** | 24/24 | **36/36** | **+12** |
| **TOTAL contrôles fonctionnels** | **734** | **746** | **+12** |
| Régressions sur baseline | 0 | **0** | — |

**Bilan méthodologique SP21 :**

| Discipline | État |
|---|---|
| Cadrage Q1-Qn avant écriture | ✓ 7 questions arbitrées (A-Q1 à E-Q1 + UI-I6 portée + 2 ajouts vocabulaire) |
| Validation utilisateur explicite avant code | ✓ Aucune ligne écrite sans feu vert |
| Auto-scan SP18 + SP21 (29 patterns combinés) | ✓ 0 occurrence sur les composants + page |
| Surgical edits | ✓ Tous les ajouts sont en `str_replace` ciblés |
| Batterie complète à chaque étape (E-Q1=a) | ✓ 5 batteries complètes successives + 1 finale |
| 0 régression sur v1.0 + v1.1.x + SP20 | ✓ |
| Frontière doctrinale préservée (adapter pur sans Streamlit) | ✓ Aucun import streamlit ajouté dans l'adapter |
| Réutilisation pure de la frontière SP20 | ✓ Les 3 nouveaux composants consomment uniquement la sortie d'`extraire_hypotheses_doctrinales` |
| 1 bug SP20 détecté et corrigé en passant | ✓ horizons_annees clé mal nommée |

**Note méthodologique SP21 (validation empirique de votre observation SP20) :**

> *Le fait que SP21, SP22, puissent maintenant consommer l'adapter
> sans l'étendre doctrinalement est un excellent signal. Cela veut
> dire que la frontière a été correctement dessinée dès SP20.*

SP21 a validé empiriquement votre observation :

- **0 nouvelle fonction ajoutée à l'adapter** — `extraire_hypotheses_doctrinales` (livré SP20) couvrait déjà les besoins SP21
- **1 seule correction mineure** sur l'adapter (clé `horizons_annees`) qui était un bug pré-existant, pas une nouvelle frontière
- **Les 3 nouveaux composants** consomment uniquement la sortie pure de l'adapter, sans recalcul, sans dérivation
- **L'invariant UI-I4** (adapter sans Streamlit) reste vert sans intervention

La frontière dessinée en SP20 a tenu. SP22 (navigation audit) devrait procéder de la même manière en consommant `compter_etapes_pour_pdf` + `extraire_etapes_recapitulatives` déjà livrés.

**Démonstration empirique du garde-fou SP21 — élargi :**

À l'étape 1 (extension doctrine), j'ai naturellement écrit dans la doctrine :

```
"Convention efficace : capitalisation annuelle."
```

en tant qu'**exemple type interdit**. Le mot « efficace » fait partie de votre liste SP21. Cela m'a forcé à structurer l'anti-pattern avec une paire « interdit / reformulation correcte » plutôt qu'une liste plate :

```
# NON
st.write("Convention efficace : capitalisation annuelle.")
# OUI
st.write("Convention : capitalisation annuelle simple et déterministe.")
```

Cette structure paire « interdit / autorisé » est plus pédagogique que la liste plate et reflète exactement la **précision sémantique** que vous demandiez.

**Sous-passes v1.2 restantes :**

- **SP22** — Phase 3 : Navigation audit (lien direct vers PDF cabinet via `generer_pdf_audit`, affichage des étapes structurantes via `extraire_etapes_recapitulatives`, comptage via `compter_etapes_pour_pdf` — tous déjà livrés dans l'adapter SP20).

À la sortie de SP21, l'outil dispose de :
- Une UI Streamlit Réceptacles avec **lecture cabinet** (SP20) + **auditabilité visible** (SP21)
- **6 invariants UI** gravés en tests (UI-I1 à UI-I6)
- **29 patterns lexicaux** interdits (14 SP18 + 15 SP21 dont 3 redondants)
- **3 fichiers UI** sous scan global pour le vocabulaire d'hypothèses
- **746 contrôles fonctionnels** au vert, 0 régression sur la baseline

### v1.2 — UI Streamlit Réceptacles, Phase 3 (SP22 : Navigation audit)

**État final (20/05/2026) :** SP22 livrée. **v1.2 complète** :
SP20 + SP21 + SP22 forment maintenant la couche UI Réceptacles
intégrale. REC-D7 passe au statut **Clôturée v1.2** dans la table
de bord §0.1.

**Principes directeurs (vos formulations SP22) :**

> *Vous êtes maintenant dans la dernière vraie couche UX structurante.
> SP22 devrait essentiellement exposer proprement les capacités déjà
> présentes dans le système.*

> *Le vrai danger maintenant : transformer la navigation audit en
> « expérience d'assistance ». Navigation audit ≠ storytelling.
> L'UI doit permettre l'inspection, la lecture, la traçabilité. Mais
> jamais guider la décision.*

> *SP22 ressemble maintenant à une clôture propre de plateforme, pas
> à une feature supplémentaire.*

Ces formulations ont guidé toute la sous-passe. SP22 n'a pas livré
de nouvelles capacités : il a **exposé proprement** les capacités
déjà présentes (PDF cabinet, étapes structurantes, compteurs audit)
sans glisser vers le storytelling.

**Apports doctrinaux utilisateur intégrés en SP22 :**

| Apport | Implémentation |
|---|---|
| Navigation passive uniquement | §4.9 (A9) avec liste de verbes interdits (Explorer, Approfondir, Analyser, Comparer en détail, Découvrir) |
| Boutons fonctionnels uniquement | Constante `LABEL_TELECHARGER_PDF = "Télécharger le PDF audit"` figée |
| Ordre stable étendu aux signets + boutons | UI-I1 §6.1 enrichi (signets PDF, boutons navigation enveloppes) |
| Aucun bouton conditionné par valeur économique | §4.10 (A10) nouveau anti-pattern + test bonus SP22 (heuristique regex) |
| Bouton PDF unique et neutre | `st.download_button` unique dans `panneau_navigation_audit`, label figé en constante |
| Aucun aperçu RECAP en zone navigation | D-Q1=α confirmé : compteurs structurels uniquement |
| Version doctrine + timestamp + version audit | `afficher_metadonnees_doctrinales` : « Doctrine v1.0.1 (2026-05-01) · Spec audit v1.1.0 · Renderer v1.0.0 · Baseline 8863991f27f67847 · Généré le YYYY-MM-DD HH:MM:SS » |
| Cabinet/client = valeurs par défaut | « Cabinet exemple », « Dirigeant exemple » (personnalisation reportée v1.3+) |

**Anti-pattern type SP22 (votre apport critique) :**

```python
# Interdit (A10) — bouton conditionné par valeur économique
if valeur_nette_perin > valeur_nette_pee:
    st.button("Télécharger audit PERIN")
```

**Autorisé** :

```python
# Bouton unique, neutre, présent sans condition
st.download_button("Télécharger le PDF audit", data=pdf_bytes, ...)
```

Cet anti-pattern est gravé en doctrine `ARCHITECTURE_UI_RECEPTACLES.md` §4.10 + testé par heuristique regex dans `test_ui_receptacles_neutralite.py` (Bonus-SP22-symetrie).

**Livrables SP22 :**

- `ARCHITECTURE_UI_RECEPTACLES.md` (modifié, +118 lignes, 567 → 685 lignes)
  - §4.9 nouvelle : Anti-pattern A9 « Storytelling de navigation audit ». Liste 5 verbes interprétatifs interdits. Distinction « compteurs structurels neutres (autorisés) » vs « valeurs économiques détaillées (interdites) » en zone navigation.
  - §4.10 nouvelle : Anti-pattern A10 « Bouton conditionné par valeur économique ». 3 exemples interdits + règle pratique « si on supprime tous les résultats, les boutons doivent rester identiques ».
  - §5.4 nouvelle : Composants panneau navigation audit autorisés (`st.download_button`, `st.dataframe` pour compteurs, `st.caption` pour versions).
  - §6.1 (UI-I1) étendu : ordre fixe doctrinal s'applique aussi aux signets PDF et aux boutons de navigation enveloppes.

- `ui/composants_receptacles.py` (extension, +152 lignes, 497 → 649 lignes)
  - 1 constante `LABEL_TELECHARGER_PDF = "Télécharger le PDF audit"` (label figé)
  - 1 constante `LABELS_COMPTEURS_AUDIT` (mapping 5 compteurs structurels)
  - 3 nouveaux composants :
    - `tableau_structure_audit(counts, taille_pdf_bytes)` : tableau 2 colonnes des compteurs
    - `afficher_metadonnees_doctrinales(...)` : caption des 4 versions + timestamp
    - `panneau_navigation_audit(...)` : orchestre bouton + tableau + métadonnées
  - Aucun usage de mot interdit SP18 ni SP21 (0 occurrence sur 28 patterns combinés)

- `ui/page_receptacles.py` (extension, +33 lignes, 178 → 211 lignes)
  - Imports : `DOCTRINE_VERSION`, `DOCTRINE_DATE`, `AUDIT_SPEC_VERSION`, `AUDIT_PDF_SPEC_VERSION`, `BASELINE_HASH_DEFAUT`, `compter_etapes_pour_pdf`, `panneau_navigation_audit`, `generer_pdf_audit`
  - Bloc « Vue 4 : Navigation audit » avec `st.expander("Navigation audit et téléchargement", expanded=False)`
  - Conforme A-Q1=β (replié par défaut)
  - Conforme B-Q1=α (régénération à chaque rerun, ~100 ms négligeable)

- `test_ui_receptacles_neutralite.py` (extension, +90 lignes, ~415 → ~505 lignes)
  - Section Bonus SP22 : 7 contrôles
    - 3 composants exposés (présence par grep textuel)
    - 1 constante `LABEL_TELECHARGER_PDF` figée à « Télécharger le PDF audit »
    - 1 absence de verbes interprétatifs (« Explorer », « Approfondir », « Analyser », « Comparer en détail », « Découvrir »)
    - 1 absence de bouton conditionné par `valeur_nette` (heuristique regex multi-lignes)
    - 1 présence de la chaîne d'appel `st.download_button` via `panneau_navigation_audit`
  - Total : 36 → **43 contrôles** (+7)

- `KNOWN_LIMITATIONS.md` (modifié)
  - REC-D7 déplacée de §0.2 (Active) vers §0.1 (Clôturée v1.2)
  - §0.4 indicateurs mis à jour : 3 dettes clôturées, 9 actives, 753 contrôles
  - Section clôture SP22 ajoutée

**Décisions architecturales SP22 validées :**

| Bloc | Décision | Source |
|---|---|---|
| A-Q1 — Périmètre panneau | **(β)** Téléchargement + compteurs structurels (pas d'aperçu RECAP) | A-Q1 |
| B-Q1 — Génération PDF | **(α)** Régénération à chaque rerun (~100 ms) | B-Q1 |
| C-Q1 — Format compteurs | **(α)** Tableau 2 colonnes | C-Q1 |
| D-Q1 — Aperçu RECAP | **(α)** Exclure (navigation ≠ storytelling) | D-Q1 |
| E-Q1 — Tests | Pas de nouvel invariant UI-I7, bonus SP22 uniquement | E-Q1 |
| F-Q1 — Discipline relance | **(a)** Batterie complète à chaque étape | F-Q1 |
| Version doctrine en UI | OUI (descriptif, traçable, non interprétatif) | Question subsidiaire 1 |
| Cabinet/client UI | Valeurs par défaut SP22, personnalisation v1.3+ | Question subsidiaire 2 |

**Préservation absolue v1.0 + v1.1.x + SP20 + SP21 :**

- 0 modification du framework `ui/pdf_audit_export.py`
- 0 modification de `core/audit.py`, `core/profil.py`, `doctrine.py`
- 0 modification des modules métier `strategy/receptacles_*.py`
- 0 modification de `app.py` (l'intégration SP20 reste suffisante)
- 0 modification des 6 goldens PDF
- 0 modification des 5 mini-goldens métier
- 0 modification des 9 pages Streamlit existantes
- 0 modification de l'adapter SP20 (la frontière a tenu intacte sur les 3 phases)
- 0 modification des composants SP20/SP21 livrés (extension uniquement)
- hash baseline `8863991f27f67847` strictement préservé

**Métriques de clôture SP22 (v1.2 phase 3) :**

| Suite | Avant SP22 (post-SP21) | Après SP22 | Δ |
|---|---|---|---|
| compare_baseline | hash `8863991f27f67847` ✓ | hash inchangé ✓ | — |
| check_imports | 22 fichiers | 22 fichiers | — |
| baseline_tests outputs | 504/504 | 504/504 | — |
| 4 audits sémantiques | 4/4 | 4/4 | — |
| 13 MODE_AUDIT | 13/13 | 13/13 | — |
| 5 PDF audit tests | 481/481 | 481/481 | — |
| Renderer invariants | 50/50 | 50/50 | — |
| Renderer stress | 49/49 | 49/49 | — |
| Goldens PDF | 6/6 conformes | 6/6 conformes | — |
| Strategy réceptacles | 130/130 | 130/130 | — |
| Mini-goldens métier | 5/5 conformes | 5/5 conformes | — |
| **`test_ui_receptacles_neutralite`** | 36/36 | **43/43** | **+7** |
| **TOTAL contrôles fonctionnels** | **746** | **753** | **+7** |
| Régressions sur baseline | 0 | **0** | — |

**Bilan méthodologique SP22 :**

| Discipline | État |
|---|---|
| Cadrage Q1-Qn avant écriture | ✓ 7 questions arbitrées (A-Q1 à F-Q1 + 2 questions subsidiaires) |
| Validation utilisateur explicite avant code | ✓ Aucune ligne écrite sans feu vert |
| Auto-scan SP18 + SP21 (28 patterns combinés) | ✓ 0 occurrence sur tous les fichiers UI |
| Surgical edits | ✓ Tous les ajouts en `str_replace` ciblés |
| Batterie complète à chaque étape (F-Q1=a) | ✓ 4 batteries successives + 1 finale |
| 0 régression sur v1.0 + v1.1.x + SP20 + SP21 | ✓ |
| Frontière doctrinale préservée | ✓ 0 modification adapter, réutilisation pure |

---

## v1.2 — Bilan global (cumulé SP20 + SP21 + SP22)

**État final v1.2 :** **complète et stable**. REC-D7 clôturée.
Les 3 phases UI Réceptacles forment maintenant un ensemble
cohérent, doctrinalement gardé et automatiquement testé.

**Cumul des livrables v1.2 (SP20 + SP21 + SP22) :**

| Fichier | Nature | Lignes finales |
|---|---|---|
| `ARCHITECTURE_UI_RECEPTACLES.md` | Doctrine | 685 lignes (12 anti-patterns + 6 invariants) |
| `ui/adapter_receptacles.py` | Adapter pur (frontière doctrinale) | ~340 lignes |
| `ui/composants_receptacles.py` | Composants Streamlit | ~650 lignes |
| `ui/page_receptacles.py` | Page entry-point | ~211 lignes |
| `test_ui_receptacles_neutralite.py` | Test neutralité | ~505 lignes, 43 contrôles |
| `app.py` | Intégration (SP20 uniquement) | +20 lignes |

**Doctrine UI gravée en v1.2 :**

| Élément | Compte |
|---|---|
| Anti-patterns nommés (A1 à A10 + 2 bis) | **12** |
| Invariants UI testables (UI-I1 à UI-I6) | **6** |
| Patterns lexicaux interdits (SP18 + SP21) | **29** |
| Composants Streamlit interdits (§4.2, §5.3) | **6** (`success`, `balloons`, `toast`, `snow`, `metric+delta`, styling conditionnel) |
| Emojis valorisants interdits (§4.3) | **9** |
| Verbes interprétatifs interdits (§4.9) | **5** |
| Décisions architecturales (D-UI-1, D-UI-2) | **2** |

**Garde-fou doctrinal v1.2 — vérification empirique cumulée :**

Au cours des 3 sous-passes, le garde-fou doctrinal a détecté
**plusieurs dérives** au moment même de l'écriture, forçant des
reformulations immédiates :

| Sous-passe | Dérive détectée | Reformulation |
|---|---|---|
| SP20 | `"sans recommandation"` dans disclaimer | `"strictement descriptive"` |
| SP21 | `"Convention efficace : capitalisation annuelle"` dans doctrine | Restructuration paire interdit/autorisé |
| SP22 | (Aucune dérive lexicale détectée) | Sous-passe sans correction lexicale, signe de maturité |

**SP22 sans dérive détectée** est un signe que la discipline
incorporée au cours de SP20-SP21 a porté ses fruits.

**Validation cumulée de votre intuition SP20 :**

> *La frontière a été correctement dessinée dès SP20. SP21 et SP22
> peuvent consommer l'adapter sans l'étendre doctrinalement.*

Mesure objective sur les 3 sous-passes :

| Métrique | SP20 | SP21 | SP22 |
|---|---|---|---|
| Nouvelles fonctions adapter | 5 (initial) | 0 | 0 |
| Corrections adapter | — | 1 (clé `horizons_annees`) | 0 |
| Frontière adapter étendue | — | Non | Non |
| Composants SP21/SP22 consomment via adapter uniquement | — | Oui | Oui |
| UI-I4 (adapter sans Streamlit) | Vert | Vert | Vert |

**Cumul tests v1.2 :**

| Suite | Pre-v1.2 | Post-v1.2 | Δ |
|---|---|---|---|
| `test_ui_receptacles_neutralite` (nouveau) | — | 43/43 | +43 |
| **TOTAL contrôles fonctionnels** | 710 | **753** | **+43** |

**Bilan stratégique v1.2 :**

L'enchaînement v1.0.0 → v1.0.1 → v1.1.0 → v1.1.1 → v1.2 forme
maintenant une trajectoire mature :

1. **v1.0.0** — Livrable fonctionnel (modules métier + PDF)
2. **v1.0.1** — Phase Hardening (doctrine + invariants + goldens + stress)
3. **v1.1.0** — Extension métier (module Réceptacles)
4. **v1.1.1** — Stabilisation de gouvernance (dettes → positions doctrinales)
5. **v1.2** — Couche UI Streamlit Réceptacles (3 phases : lecture, auditabilité, navigation)

À la sortie de v1.2, l'outil dispose de :
- **Moteur fonctionnel** : 4 régimes + module réceptacles cabinet-ready
- **Framework testé** : 50 invariants renderer + 49 stress tests + 6 goldens PDF + 5 goldens métier
- **Doctrine moteur** : `ARCHITECTURE_RENDERER.md` (727 lignes) + `ARCHITECTURE_RECEPTACLES.md` (860 lignes)
- **Doctrine UI** : `ARCHITECTURE_UI_RECEPTACLES.md` (685 lignes, 12 anti-patterns, 6 invariants)
- **Couche UI Streamlit** : page Réceptacles auditables intégrée dans `app.py`, 3 phases livrées
- **Gouvernance des dettes** : 13 entrées table de bord (3 clôturées, 9 actives, 1 frontière)
- **753 contrôles automatisés + 6 goldens PDF + 5 goldens métier** au vert
- **0 régression** sur le périmètre figé v1.0.1

**Validation cumulée de votre observation finale (SP22) :**

> *Après SP22, vous serez probablement à un niveau où le produit peut
> être montré, testé, utilisé, challengé par des cabinets réels. La
> prochaine phase ne sera probablement plus « construire ». Mais :
> observer les usages réels et éviter la sur-complexification.*

Cette observation cadre la **frontière naturelle de v1.x** :

- v1.2 ferme la construction technique de la couche cabinet
- La prochaine phase logique n'est plus une nouvelle sous-passe SP
- C'est un **changement de mode** : passage de construction à observation

Les dettes restantes (REC-D1 à REC-D6, DOC-D1 à DOC-D3) sont
identifiées, classées, priorisées. Elles ne devront être traitées
que si l'usage cabinet réel le justifie — pas par anticipation.

### Pas d'historique des hypothèses réglementaires

Les paramètres réglementaires (PASS, plafonds, barèmes IR) sont dans `doctrine.py` à un instant donné. Il n'y a pas de structure `HypotheseReglementaire` permettant de remonter dans le temps ou de comparer entre exercices. **Reporté après B.2.5.**

### Pas d'audit UX couleurs

Les rendus PDF et l'UI Streamlit utilisent une palette qui n'a **pas été testée pour la lisibilité en noir et blanc ni pour le daltonisme**. À tester avant déploiement client. **Reporté après B.2.5.**

### Pas de couche explicative « Pourquoi ce résultat ? »

L'outil restitue des chiffres et un cadrage mais ne génère pas d'explication narrative automatique « voici pourquoi B est meilleur que A dans ce profil ». La justification reste à la charge du cabinet utilisateur. **Reporté après B.2.5.**

---

## 4. Limites doctrinales

### Pas de recommandation automatique

L'outil est explicitement un **outil d'aide à la décision**. Il n'émet **jamais** :
- « régime recommandé »
- « stratégie optimale »
- « meilleur scénario »
- « choix garanti »

Le vocabulaire de promesse de performance est interdit. Cf. `TERMINOLOGY.md` et `SEMANTIC_GUARDRAILS.md` pour la liste exhaustive des patterns surveillés.

### Primauté cabinet

Chaque PDF affiche un disclaimer de primauté cabinet : la décision finale appartient au conseil, pas à l'outil. Cela ne sera **jamais retiré**.

### Pas de scoring prédictif, pas d'IA

Aucune capacité de prédiction, aucun modèle ML, aucune recommandation dérivée d'un dataset historique. **Bloqué jusqu'à nouvel ordre.**

---

## 5. Limites de mise à jour réglementaire

La doctrine v1.0.1 est calée sur les paramètres **France 2026** (PASS, barèmes IR, taux de CSG/CRDS, plafonds CEHR/CDHR, etc.). Tout changement réglementaire (PLF 2027, réforme retraite, etc.) demande :
1. Une mise à jour de `doctrine.py`
2. Une régénération de la baseline numérique
3. Un re-run complet des 11 suites
4. Une bascule de version doctrine (v1.0.2, v1.1.0, etc.)

**Aucun mécanisme de mise à jour automatique n'est en place.**
