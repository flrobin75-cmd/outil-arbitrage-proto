# Terminology — Outil arbitrage rémunération dirigeant

**Version :** alignée sur doctrine v1.0.1
**Date :** 19 mai 2026
**Statut :** Référence Phase B.2.5

Ce document fixe le **vocabulaire prudent** retenu pour l'outil dans son ensemble (UI Streamlit + PDF cabinet + messages d'alerte). Il sert de référence à `SEMANTIC_GUARDRAILS.md` et à l'audit automatique `semantic_guardrails.py`.

---

## 1. Posture éditoriale

L'outil est un **cadrage indicatif** et un **outil d'aide à la décision**. Il **ne formule jamais** :

- de recommandation positive d'arbitrage,
- de promesse de performance,
- de jugement « optimal » / « meilleur »,
- de qualification « sans risque » / « garanti ».

Toute décision relève du **cabinet en charge du dossier**. Cette ligne éditoriale n'est pas un confort : elle conditionne la responsabilité civile/professionnelle de l'éditeur et la non-qualification de l'outil au sens conseil en investissement (AMF / MIF II).

---

## 2. Tableau « À éviter / Préférer »

| ❌ À éviter | ✅ Préférer | Pourquoi |
|---|---|---|
| « stratégie recommandée » | « stratégie retenue », « scénario présenté » | « recommandée » est prescriptif (risque conseil opposable) |
| « régime recommandé » | « régime à arbitrer en cabinet » | jamais en libéral L3/L4 (cf. ALERTE_BNC_VS_SEL) |
| « optimisation fiscale » | « cadrage fiscal », « scénario fiscal » | « optimisation » est commercial / promet un résultat |
| « optimiser le net dirigeant » | « comparer les équilibres possibles » | idem |
| « stratégie optimale » | « stratégie la plus efficace fiscalement sur ce cas » | « optimal » suppose une mesure unidimensionnelle |
| « meilleur régime » | « régime à arbitrer », « équilibre à examiner » | jamais de comparatif absolu |
| « garanti », « garantie de performance » | « cadrage prudent », « hypothèse retenue » | promesse de résultat (risque AMF) |
| « sans risque » | « sécurisé sous réserve de validation cabinet » | aucun arbitrage n'est sans risque |
| « recommandé automatiquement » | « marqué comme retenu par l'outil sur la base du critère X » | aucune recommandation n'est automatique |
| « calcul déclaratif » | « calcul destiné aux obligations fiscales » | « déclaratif » comme adjectif est levé pour audit strict |
| « usage déclaratif » | « usage de production fiscale » | idem |
| « modules déclaratifs » | « modules de conformité renforcée » | idem |
| « pré-remplissage déclaratif » | « préparation des obligations fiscales » | idem |
| « Déclaratif » (nom de niveau) | « Conformité renforcée » | renommé en v1.0.1 |

Note sur la dernière ligne : le **nom de niveau** « Déclaratif » a été renommé en « Conformité renforcée » en doctrine v1.0.1. Un alias interne `_ALIASES_NIVEAUX = {"Déclaratif": "Conformité renforcée"}` subsiste **uniquement dans le code**, pour absorber d'éventuels appelants historiques. Il n'est **jamais** affiché à l'utilisateur.

---

## 3. Les quatre niveaux de précision v1.0.1

L'outil expose à l'utilisateur (en couverture de PDF, dans le footer, et dans l'annexe « Trace doctrinale ») un **niveau de précision** par module. Ce niveau qualifie la profondeur de modélisation et le degré de précision technique du calcul, pas la qualité ou la fiabilité de la recommandation (l'outil ne recommande pas).

### 3.1. Conformité renforcée

> *Modules calibrés sur les règles fiscales et sociales applicables au 01/01/2026 (CEHR, CDHR, plafonnement QF). Précision suffisante pour la préparation des obligations fiscales, sous validation cabinet.*

**Modules concernés :** TNS, Libéral, Salarié, Assimilé salarié.

**Caractéristiques :**
- Application complète du barème IR 2026
- CEHR (3 % / 4 %), CDHR (plancher 20 %)
- Plafonnement du quotient familial
- 4 cas particuliers (parent isolé, personne seule case L, veuf avec enfants, invalide ou ancien combattant)
- Cotisations TNS calibrées sur la rémunération nette (méthodologie URSSAF prudente)
- Parité vérifiée contre l'Excel v19 de référence

**Bon usage cabinet :** ce niveau peut sourcer la préparation des liasses fiscales et des bulletins de paie du dirigeant, **sous validation cabinet** et avec contrôle des hypothèses d'entrée. Il ne se substitue pas au moteur fiscal du cabinet.

### 3.2. Avancé

> *Modèle complet consolidant les modules de conformité renforcée. Lecture consolidée prudente des plafonds sociaux. Adapté à l'arbitrage stratégique et à la formalisation de la mission cabinet.*

**Modules concernés :** Comparateur dispositifs (Option 2), Synthèse dirigeant.

**Caractéristiques :**
- Consolide plusieurs modules « Conformité renforcée » pour produire une vue d'ensemble
- Lecture **prudente** des plafonds d'épargne salariale (PEE/PERECO/PERO) selon la doctrine URSSAF 2024 (plafond cumulé 16 % PASS = 7 689,60 €)
- Hypothèse uniforme de TMI moyen calculé sur le module Assimilé pour la projection inter-régimes (méthodologie v19)
- Permet de comparer 4 stratégies A/B/C/D ou T1-T4 ou L1-L4 sur un même profil

**Le piège du nom :** « Avancé » ne signifie pas *plus précis* que « Conformité renforcée ». Il signifie **niveau d'analyse plus large** (consolidation), au prix de simplifications consolidantes. Sur un cas mono-régime, un module « Conformité renforcée » est plus pointu qu'une Synthèse « Avancée ». Sur un arbitrage multi-régimes, la Synthèse « Avancée » est seule pertinente — mais ses chiffres reposent sur des conventions qu'il faut comprendre (TMI moyen unique, plafond consolidé prudent).

**Bon usage cabinet :** ce niveau formalise une **mission d'arbitrage**. Il n'est **pas** destiné à la production des bulletins de paie ou de la liasse fiscale.

### 3.3. Cadrage

> *Modèle simplifié sans CEHR/CDHR ni plafonnement QF, destiné à comparer rapidement plusieurs équilibres. Pour les calculs destinés aux obligations fiscales, utiliser les modules de conformité renforcée.*

**Modules concernés :** Scénarios A vs B (avant/après dividendes, inter-régimes).

**Caractéristiques :**
- Modèle simplifié : **pas** de CEHR, **pas** de CDHR, **pas** de plafonnement QF
- Permet de tester rapidement la sensibilité d'un arbitrage à un paramètre (salaire, dividendes, enveloppe)
- Comparer 2 scénarios complets en une page

**Bon usage cabinet :** dégrossissage en réunion client, exploration d'options. Toute conclusion doit être reprise au niveau « Conformité renforcée » ou « Avancé » avant validation.

### 3.4. Indicatif

> *Projection reposant sur des hypothèses externes (rendements, fiscalité future, durée de placement), à ajuster selon le dossier. Ne constitue pas un engagement de performance.*

**Modules concernés :** Projection 5 ans, Comparateur patrimonial.

**Caractéristiques :**
- Hypothèses paramétrables : rendement cash défensif (2 %), rendement épargne capitalisable (4 %), rendement comparateur (5 %)
- Capitalisation annuelle composée, versement en début d'année
- **Aucune** garantie de performance, aucune projection ne vaut prédiction
- Disclaimer AMF systématiquement affiché

**Bon usage cabinet :** appui visuel pour illustrer un raisonnement patrimonial à 5 ans. À ne **jamais** présenter sans le disclaimer AMF.

---

## 4. Lexique des objets métier

### 4.1. Net dirigeant immédiat vs Bénéfice retenu (TNS T4)

| Terme | Définition |
|---|---|
| **Net dirigeant immédiat** | Revenu disponible immédiatement pour le dirigeant après cotisations et IR (rémunération + dividendes nets après PFU ou TNS-imposition) |
| **Bénéfice retenu en société** | Bénéfice après IS conservé dans la société (réserve, trésorerie) — n'entre pas dans la poche du dirigeant à court terme |

**Garde-fou structurel :** ces deux indicateurs sont **toujours présentés séparément**, jamais additionnés. La stratégie T4 (rétention de bénéfice) est volontairement non-comparable « toutes choses égales » à T1/T2/T3 ; le PDF explicite cette non-additivité. Cf. test `test_strategy_tns.py` (11 tests structurels) et `SEMANTIC_GUARDRAILS.md` §3.

### 4.2. BNC vs SEL (Libéral L3/L4)

| Sigle | Définition |
|---|---|
| **BNC** | Bénéfice non commercial — libéral en exercice individuel ou en société non-IS (déclaration 2035) |
| **SEL** | Société d'exercice libéral (SELARL = gérant TNS, SELAS = président Assimilé) |

**Garde-fou structurel :** dès qu'un cadrage compare un niveau BNC à un niveau SEL (typiquement L3 ou L4), l'outil émet l'**ALERTE_BNC_VS_SEL** et **ne désigne jamais de « régime recommandé »**. La comparaison BNC/SEL met en jeu la couche IS qui n'est qu'une partie du choix réel : trésorerie professionnelle, transmission, distribution de bénéfices à terme, statut du conjoint, etc.

### 4.3. Stratégies par régime

| Régime | Stratégies | Sens |
|---|---|---|
| Assimilé salarié | A, B, C, D | A = salaire seul, B = mix salaire + dividendes, C = dividendes seuls, D = mix avec PERIN |
| TNS | T1, T2, T3, T4 | équivalents A/B/C/D + T4 = rétention de bénéfice en société |
| Libéral | L1, L2, L3, L4 | L1 = BNC pur, L2 = BNC avec optimisation de structure, L3 = SELARL, L4 = SELAS |

Note : « optimisation de structure » apparaît dans L2 comme **descriptif** d'un choix de personne morale. Ce n'est **pas** une recommandation d'optimisation fiscale. Audit `semantic_guardrails.py` lève toute ambiguïté.

---

## 5. Tournures de phrase systématiquement vérifiées

Les patterns ci-dessous sont scannés en CI par `semantic_guardrails.py` :

1. `Déclaratif` (capitalisé, comme nom de niveau) — interdit hors alias interne
2. `déclaratif` (minuscule, en adjectif) — interdit dans tout contenu utilisateur (PDF, UI)
3. `recommandée` / `recommandé` / `recommandation` — interdit hors disclaimers négatifs et docstrings de garde-fou
4. `optimisation` / `optimiser` / `optimal` — interdit hors rationale documenté
5. `garanti` / `garantie` — interdit (sauf docstring expliquant le garde-fou)
6. `sans risque` — interdit
7. `meilleur régime` — interdit
8. `recommandé automatiquement` — interdit
9. Agrégation `net_dirigeant_immediat + benefice_retenu_societe` — interdite

Liste exhaustive et patterns regex dans `SEMANTIC_GUARDRAILS.md` et `semantic_guardrails.py`.

---

## 6. Évolution du vocabulaire

Toute proposition d'ajout de terme à éviter ou à préférer doit faire l'objet :

1. d'une modification de ce document,
2. d'une mise à jour de `SEMANTIC_GUARDRAILS.md` et `semantic_guardrails.py`,
3. d'un audit complet (11 suites + audit final 6 contrôles) confirmant 0 régression,
4. d'une validation du propriétaire du projet.

Pour mémoire, le passage de v1.0.0 à v1.0.1 a notamment introduit :
- renommage « Déclaratif » → « Conformité renforcée »,
- harmonisation « cadre méthodologique » / « efficience »,
- disclaimer AMF Comparateur patrimonial,
- principe de primauté cabinet.

Voir `doctrine.DOCTRINE_HISTORIQUE` pour la liste à jour.
