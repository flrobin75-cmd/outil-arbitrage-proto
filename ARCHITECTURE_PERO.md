# Doctrine PERO — chantier activé via C6 (SP23-bis)

**Version :** v0.2 (SP23 doctrine préparatoire + SP23-bis activation via C6)
**Date :** 20 mai 2026
**Statut :** **Chantier activé** via critère C6 (maturité plateforme), cf. §13.2b et §13bis (journal d'activation)

---

## §0 — Statut du document

> **Historique du statut.**
> - SP23 (20/05/2026) : doctrine préparatoire produite. Statut
>   initial : **chantier documenté non activé**. PERO-D0 inscrite
>   en table de bord §0.5 de `KNOWN_LIMITATIONS.md`.
> - SP23-bis (20/05/2026) : §13.2 partitionnée en §13.2a (critères
>   terrain C1-C5, inchangés) et §13.2b (critère de maturité
>   plateforme C6, ajouté). Activation du chantier PERO invoquée
>   via C6. Journal d'activation §13bis. **Chantier activé.**
> - PERO-D0 dans `KNOWN_LIMITATIONS.md` §0.5 mis à jour : statut
>   « Activé via C6 (SP23-bis) ».

Ce document constitue désormais la **doctrine activée** de la
modélisation PERO (Plan d'Épargne Retraite Obligatoire) dans
l'outil. Il fixe les positions doctrinales, conventions,
frontières et anti-patterns qui encadreront le chantier de
développement à venir (SP24 module métier, SP25 orchestration et
goldens, SP26 UI et audit PDF).

**Conditions d'activation §13.2b satisfaites :** voir le journal
d'activation §13bis qui documente point par point les 6 conditions
C6 vérifiées pour PERO.

**Limite explicite de cette activation.** L'activation porte sur
**le chantier PERO et lui seul**. C6 ne dispense pas de la
discipline de cadrage Q1-Qn par sous-passe, ni de la batterie
complète à chaque étape, ni des invariants gravés. SP24 devra
être cadrée formellement comme SP15-SP17 l'ont été.

**Pourquoi un document de capitalisation initialement sans
activation ?** La discipline SP1→SP22 a produit un projet
techniquement mûr (753 contrôles, 6 invariants UI, 12 anti-patterns,
frontière doctrinale matérialisée par un adapter pur). SP23 a
choisi de capitaliser la doctrine PERO **avant** toute reprise
de développement, dans une logique d'observation cabinet.

SP23-bis (immédiatement consécutive) a reconnu que la situation
de maturité système elle-même constitue un critère légitime
d'activation, à condition d'être encadrée. C6 a été créé pour
formaliser explicitement cette évolution doctrinale, plutôt que
de contourner silencieusement §13.

Néanmoins, la mémoire méthodologique, les patterns, les frontières
et les invariants sont encore frais. Capitaliser ces éléments
maintenant — sous forme de doctrine activée et stable — protège
contre :

- la perte d'arbitrages au cours d'une pause longue
- la reconstitution partielle au moment d'une éventuelle reprise
- la dérive « on continue parce qu'on peut »

**Statut formel post-SP23 + SP23-bis :**

- SP23 a produit la doctrine seule (~1091 lignes initiales). Aucun
  code, test, UI, orchestrateur ni golden n'a été produit dans le
  cadre de SP23.
- SP23-bis a amendé §13.2 (partition §13.2a + §13.2b avec C6) et
  ajouté §13bis (journal d'activation). Aucun code, test, UI,
  orchestrateur ni golden n'a été produit dans le cadre de SP23-bis
  non plus.
- Le chantier est **activé** mais le développement (SP24 module
  métier, SP25 orchestration, SP26 UI/PDF) **n'a pas commencé**.
  Chaque sous-passe à venir devra être cadrée formellement Q1-Qn
  selon discipline standard.

Le document constitue désormais le **point de référence vivant**
du chantier PERO. Toute évolution doctrinale ultérieure (relecture
des conventions France 2026, ajustement des anti-patterns, etc.)
devra y être documentée.

---

## §1 — Nature économique du PERO

Le PERO (Plan d'Épargne Retraite Obligatoire) est une enveloppe
retraite supplémentaire d'entreprise mise en place pour une
catégorie objective de salariés. Sa nature économique le distingue
fondamentalement du PERIN (individuel) et du PERECO (collectif
volontaire).

### 1.1 — Caractéristiques structurantes

**Enveloppe collective obligatoire.** Le PERO ne relève pas du
choix individuel du salarié. Il est mis en place par l'entreprise
au bénéfice d'une **catégorie objective** (cadres, non-cadres,
métiers définis par accord, etc.) et l'adhésion est obligatoire
pour les salariés relevant de cette catégorie. C'est une
**enveloppe d'entreprise**, pas une enveloppe d'épargne salariée
volontaire.

**Cotisation employeur structurante.** Contrairement au PERECO où
l'abondement employeur s'ajoute à un versement volontaire du
salarié, le PERO est principalement financé par une **cotisation
employeur** exprimée en pourcentage du salaire brut. Cette
cotisation est une **charge de personnel** pour l'entreprise et
non un avantage en nature pour le salarié au moment du versement.

**Catégorie objective requise.** L'éligibilité PERO s'apprécie au
niveau d'une catégorie de salariés définie objectivement
(convention collective, accord d'entreprise, décision unilatérale
de l'employeur dans le respect des règles d'objectivité). Le
dirigeant TNS n'est typiquement pas éligible (il n'est pas salarié) ;
le dirigeant assimilé salarié peut l'être si la catégorie objective
le couvre.

**Dépendance au salaire.** L'assiette de cotisation PERO est
fonction du salaire brut. Le PERO est donc indissociable d'une
**logique salaire** : pas de salaire, pas de PERO.

**Logique entreprise plus forte.** Le PERO modifie le coût
employeur global de manière plus structurante que le PERECO :
là où le PERECO est conditionné à un versement volontaire du
salarié, le PERO est un engagement employeur récurrent. Sa mise en
place modifie le PnL de la société et engage durablement.

### 1.2 — Inscription dans le périmètre arbitrage rémunération dirigeant

Dans le cadre de l'outil (arbitrage rémunération dirigeant France
2026), le PERO intéresse principalement :

- le dirigeant **assimilé salarié** (SAS/SASU) éligible à sa
  propre catégorie objective
- les dirigeants TNS qui se versent une rémunération salariée
  partielle (cas atypiques, hors périmètre v1.x)

Pour le dirigeant assimilé salarié, le PERO constitue une
**enveloppe complémentaire** distincte de PERIN, PEE, PERECO, avec
un mécanisme économique propre : la cotisation employeur PERO
**diminue** le revenu net immédiat du dirigeant (en augmentant le
coût employeur consacré à la retraite) en échange d'une
**capitalisation différée** à l'horizon retraite.

---

## §2 — Différences PERIN / PERECO / PERO

### 2.1 — Tableau doctrinal de référence

Ce tableau positionne le PERO **au sein de la famille retraite**
(PERIN, PERECO, PERO). Il ne couvre **volontairement pas** le PEE,
qui relève d'une logique d'épargne salariale à 5 ans hors retraite
(le PEE reste néanmoins présent dans la doctrine globale v1.2 du
framework, cf. `ARCHITECTURE_RECEPTACLES.md` §3.6).

| Dimension | PERIN | PERECO | PERO |
|---|---|---|---|
| Caractère du versement | Volontaire individuel | Volontaire collectif (PEE/PERECO) | **Obligatoire collectif** |
| Initiative | Salarié / dirigeant | Salarié dans un cadre entreprise | **Employeur (cotisation)** |
| Catégorie objective requise | Non | Non | **Oui** |
| Déduction IR du versement | Oui (sous plafond) | Oui (versement volontaire, sous plafond) | **Oui (cotisation employeur exonérée à l'entrée pour le salarié, dans la limite des plafonds)** |
| Abondement employeur | Non | Oui (PERECO abondé) | **Non — la cotisation employeur EST le financement principal** |
| Cotisation employeur structurante | Non | Optionnelle (abondement) | **Oui (taux %, base salaire)** |
| Base de calcul | Versement libre du salarié | Versement libre + abondement éventuel | **% du salaire brut** |
| Forfait social employeur | N/A | Oui (sur abondement) | **Oui (sur cotisation employeur)** |
| CSG/CRDS au moment du versement | Non sur versement personnel | Oui sur abondement | **Oui sur cotisation employeur** |
| Disponibilité | Retraite (sauf cas légaux) | Retraite (sauf cas légaux) | **Retraite (sauf cas légaux)** |
| Modalité de sortie principale | Capital ou rente | Capital ou rente | **Rente (capital marginal selon contrat)** |
| Fiscalité à la sortie en capital | IR sur versements déductibles + PFU sur PV | IR sur versements + PFU sur PV | **IR sur rente (régime spécifique)** |
| Logique sociale dominante | Individuelle | Salariale collective | **Entreprise (engagement employeur)** |

**Lecture du tableau :** chaque ligne identifie une **dimension
descriptive**. Aucune ligne n'identifie une « meilleure » enveloppe.
Les colonnes restent dans l'ordre strict PERIN → PERECO → PERO
(la cohérence d'ordre avec UI-I1 du framework UI s'écrira
PERIN → PEE → PERECO → PERO à l'échelle globale ; ici on omet PEE
qui n'appartient pas à la famille retraite).

### 2.2 — Trois familles, trois cas d'usage

- **PERIN** : épargne retraite individuelle, à l'initiative du
  dirigeant pour son propre patrimoine. Pas de catégorie, pas de
  dépendance au statut salarié.
- **PERECO** : épargne retraite collective, intégrée à un dispositif
  PEE/PERECO d'entreprise, financée principalement par versement
  volontaire du salarié + abondement employeur optionnel.
- **PERO** : régime retraite supplémentaire d'entreprise, financé
  principalement par cotisation employeur sur le salaire d'une
  catégorie objective. Engagement employeur récurrent.

---

## §3 — Frontières négatives

Cette section liste explicitement ce que la modélisation PERO
**ne fera pas**, en cohérence stricte avec FRONT-1 de
`KNOWN_LIMITATIONS.md` §0.3 (absence de moteur prescriptif).

### 3.1 — Pas d'optimisation de taux

Le moteur ne calcule **pas** un « taux de cotisation PERO optimal »
pour un profil dirigeant. Il restitue les conséquences économiques
d'un taux donné, fourni en entrée. La recherche d'un taux
particulier (par solveur, par maximisation d'une métrique, par
heuristique) **n'entre pas dans le périmètre**.

### 3.2 — Pas de recommandation de catégorie objective

Le moteur ne suggère **pas** quelle catégorie objective définir,
ni quel périmètre de salariés y inclure. La structuration des
catégories objectives relève du conseil RH/social, hors mandat de
l'outil.

### 3.3 — Pas de dimensionnement automatique

Le moteur ne propose **pas** de « niveau de cotisation idéal pour
ce profil ». Il prend une cotisation en entrée et restitue ses
conséquences. Aucune méthode de dimensionnement (objectif de rente,
objectif de TRI, objectif d'effort) n'est implémentée.

### 3.4 — Pas de comparaison prescriptive

Le moteur peut afficher PERIN, PERECO, PERO côte à côte (même
horizon, même flux disponible quand cela a un sens) mais ne
**classe pas**, ne **range pas**, ne **recommande pas** d'enveloppe.
La comparaison est descriptive, conformément à la doctrine
v1.2 et FRONT-1.

### 3.5 — Pas de logique RH

Le moteur ne modélise **pas** :
- la gestion multi-collèges (cadres / non-cadres en parallèle)
- les rattrapages PERO N-1/N-2/N-3
- les transferts inter-régimes
- les sorties anticipées au-delà des cas légaux génériques

Le périmètre SP24 (si activé un jour) est délibérément réduit
à un cas usuel mono-catégorie, sans architecture RH avancée.

---

## §4 — Conventions PERO (France 2026, à confirmer)

> **Note rédactionnelle (convention §0 / D-Q1=β).** Toutes les
> valeurs numériques de cette section sont des **valeurs doctrinales
> de référence (France 2026 — à confirmer lors d'une éventuelle
> réactivation du chantier)**. La réglementation française évolue
> (PLF annuels, réformes retraite, accords de branche) ; une
> reprise du chantier devra valider chaque valeur avant
> implémentation.

### 4.1 — Forfait social employeur sur cotisation PERO

**Valeur doctrinale de référence (France 2026 — à confirmer lors
d'une éventuelle réactivation du chantier) :** taux forfait social
applicable à la cotisation employeur PERO = **16 %** (régime
général ; taux réduit applicable aux entreprises mettant en place
un PERO d'entreprise sous conditions, en remplacement du taux
standard de 20 %).

**Provider doctrinal cible (SP24) :** `obtenir_taux_forfait_social_pero(profil)`.

### 4.2 — Traitement CSG/CRDS sur cotisation employeur PERO

**Valeur doctrinale de référence (France 2026 — à confirmer lors
d'une éventuelle réactivation du chantier) :** la cotisation
employeur PERO est soumise à CSG/CRDS pour le salarié
(**9,7 %** au total, avec part déductible et part non déductible).

**Provider doctrinal cible (SP24) :** `obtenir_taux_ps_pero(profil)`.

### 4.3 — Plafonds PERO

**Valeur doctrinale de référence (France 2026 — à confirmer lors
d'une éventuelle réactivation du chantier) :**

- Plafond annuel d'exonération sociale de la cotisation PERO
  pour le salarié : **5 % de la rémunération brute** dans la
  limite de **5 PASS** (à reconfirmer selon évolutions
  réglementaires)
- Plafond annuel d'exonération IR pour le salarié : limite globale
  PEE/PERECO/PERO de **8 % de la rémunération brute** dans la
  limite de **8 PASS** (à reconfirmer)

**Provider doctrinal cible (SP24) :** `obtenir_plafond_pero(profil)`.

### 4.4 — Base salaire de référence

**Valeur doctrinale de référence (France 2026 — à confirmer lors
d'une éventuelle réactivation du chantier) :** assiette = salaire
brut annuel du dirigeant assimilé salarié, plafonné le cas échéant
à un multiple du PASS selon les règles du PERO mis en place.

### 4.5 — Disponibilité et déblocage

**Valeur doctrinale de référence (France 2026 — à confirmer lors
d'une éventuelle réactivation du chantier) :** disponibilité à la
retraite (article L. 224-2 du code monétaire et financier).
Déblocages anticipés possibles selon les cas légaux génériques
PER (invalidité, décès du conjoint, surendettement, expiration
des droits ASS, cessation d'activité non salariée suite à
liquidation judiciaire, acquisition de la résidence principale —
ce dernier cas exclut typiquement la fraction issue de
cotisations obligatoires en PERO).

### 4.6 — Modalités de sortie

**Valeur doctrinale de référence (France 2026 — à confirmer lors
d'une éventuelle réactivation du chantier) :** sortie principale
en **rente viagère**. Sortie en capital possible selon contrat
pour la fraction issue de versements volontaires éventuels, mais
**la fraction issue des cotisations obligatoires est typiquement
versée en rente**.

### 4.7 — Hypothèses de rendement

**Convention v1.2 reprise sans changement :** rendement nominal
annuel de **2 %**, capitalisation annuelle simple et déterministe
(cf. `ARCHITECTURE_RECEPTACLES.md` D-R8 et `WORDING_REC_CONVENTION_RENDEMENT`).
La même convention transverse s'applique aux 4 enveloppes
PERIN / PEE / PERECO / PERO pour préserver la comparabilité
directionnelle.

---

## §5 — Sémantique économique

Chaque grandeur économique manipulée par le module PERO doit être
**définie explicitement**, sans ambiguïté. Cette section fixe le
vocabulaire ; SP24 (si activé) devra produire un dataclass
`LigneHorizonPero` reprenant ces grandeurs avec validations
algébriques.

### 5.1 — `flux_employeur_pero`

**Définition :** montant nominal de la cotisation employeur PERO
versée annuellement au régime, en euros. Calculé comme
**taux_cotisation_pero × salaire_brut_annuel**, sous réserve des
plafonds. Avant forfait social et avant CSG/CRDS prélevés sur le
salarié.

**Unité :** EUR.

### 5.2 — `flux_salarie_pero` (cas dégénéré v1.x)

**Définition :** montant du versement volontaire individuel du
salarié au PERO, **typiquement nul** en v1.x où on modélise un
PERO purement obligatoire à cotisation employeur. Conservé pour
extension future, valeur par défaut **0 EUR**.

**Unité :** EUR.

### 5.3 — `economie_fiscale_immediate`

**Définition :** réduction d'impôt sur le revenu du salarié-dirigeant
au titre de la cotisation employeur PERO **non imposable à l'IR**
(dans la limite du plafond §4.3). Calculée comme
**partie_exoneree × TMI**.

**Unité :** EUR.

**Note :** ce gain fiscal est différent économiquement de celui du
PERIN (où le versement individuel est déduit du revenu imposable).
Pour le PERO, l'exonération porte sur la cotisation patronale qui
**n'entre pas dans le revenu imposable** du salarié.

### 5.4 — `cout_entreprise`

**Définition :** charge totale supportée par l'entreprise au titre
de la cotisation PERO. Calculée comme
**flux_employeur_pero + forfait_social × flux_employeur_pero +
charges_patronales_residuelles_sur_la_fraction_assujettie**.

**Unité :** EUR.

### 5.5 — `effort_reel`

**Définition :** coût net économique réel pour le dirigeant
assimilé salarié, en tenant compte de :

- la cotisation employeur qui réduit potentiellement son salaire
  net immédiat
- la CSG/CRDS prélevée sur la cotisation employeur PERO
- l'économie d'IR §5.3

Doit être **défini précisément en SP24** via une identité
algébrique testable. La définition retenue devra rester homogène
avec celle utilisée pour PERIN, PEE, PERECO (cohérence cross-enveloppes).

**Unité :** EUR.

### 5.6 — `capital_projete`

**Définition :** valeur nominale du capital constitué dans le PERO
à un horizon donné, par capitalisation des flux annuels au taux
de rendement conventionnel.

**Unité :** EUR.

**Convention :** capitalisation annuelle simple et déterministe
au taux §4.7 (2 %).

### 5.7 — `valeur_nette` à l'horizon

**Définition :** valeur économique nette à terme **après fiscalité
de sortie** retenue par convention (cf. §4.6 — sortie en rente
viagère par défaut). La valeur_nette PERO doit donc être calculée
sur une logique de **flux de rente actualisés** ou de **capital
équivalent à la rente**, selon la convention retenue en SP24.

**Unité :** EUR.

**Note critique pour SP24 :** la `valeur_nette` PERO sera
structurellement différente des `valeur_nette` PERIN/PEE/PERECO,
car le PERO est typiquement liquidé en rente et non en capital.
La comparaison directionnelle reste pertinente à condition de
**convertir explicitement la rente en capital équivalent** sous
hypothèses claires (durée de versement, taux technique). Cette
convention de conversion **devra être documentée et testée en SP24**.

### 5.8 — `disponibilite`

**Définition :** chaîne descriptive de la disponibilité du capital,
analogue aux 3 enveloppes existantes. Wording doctrinal cible :

> « Bloqué jusqu'à la retraite, versement en rente viagère
> principalement (sortie en capital marginale selon contrat).
> Cas légaux de déblocage anticipé : invalidité, décès du conjoint,
> surendettement, expiration ASS, cessation d'activité non salariée
> sur liquidation judiciaire. Cas RP exclu pour la fraction issue
> de cotisations obligatoires. »

**Unité :** chaîne.

---

## §6 — Anti-patterns PERO

Cette section nomme les dérives spécifiques au PERO, en plus des
12 anti-patterns A1-A10 + bis déjà gravés dans
`ARCHITECTURE_UI_RECEPTACLES.md`. Ces anti-patterns devront être
testés au moment d'une éventuelle activation SP24-SP26.

### 6.1 — Anti-pattern P1 : Calcul de « taux optimal »

**Interdit :**

```python
# NON : solveur ou heuristique de taux
taux_optimal = solveur_maximisant(profil, fonction=valeur_nette_a_horizon)
st.write(f"Taux PERO recommandé : {taux_optimal:.1%}")
```

**Pourquoi :** transformer le moteur en outil de dimensionnement
viole FRONT-1. Le moteur restitue les conséquences d'un taux
donné en entrée, il ne le détermine pas.

**À la place :** l'utilisateur fournit un taux de cotisation
PERO en entrée (saisi par l'UI ou par défaut documenté). Le
moteur calcule et restitue.

### 6.2 — Anti-pattern P2 : Suggestion de catégorie objective

**Interdit :**

```python
# NON : recommandation RH
if profil.statut == "Cadre dirigeant":
    st.write("Catégorie objective recommandée : Cadres + Mandataires sociaux")
```

**Pourquoi :** la définition d'une catégorie objective est un
acte de conseil RH, hors mandat de l'outil. Risque déontologique.

**À la place :** l'utilisateur indique l'éligibilité du dirigeant
à une catégorie PERO (oui/non), le moteur en tire les conséquences
économiques. Aucun conseil sur la structuration.

### 6.3 — Anti-pattern P3 : Qualification de la structuration PERO

**Interdits dans les chaînes affichées :**

- « meilleure structuration »
- « architecture PERO optimale »
- « configuration recommandée »
- « régime mieux adapté »

**Pourquoi :** ces qualifications sont des justifications
déguisées (cf. §4.6 bis de `ARCHITECTURE_UI_RECEPTACLES.md` —
qualification subjective des hypothèses).

**À la place :** description paramétrique. Exemple :
« Taux de cotisation employeur appliqué : X %. Catégorie
objective renseignée : Y. »

### 6.4 — Anti-pattern P4 : Comparaison prescriptive entre enveloppes retraite

**Interdit :**

```python
# NON : classement implicite
if valeur_nette_pero > valeur_nette_perin:
    st.success("Le PERO est plus avantageux que le PERIN")
```

**Pourquoi :** viole simultanément A1 (signal prescriptif explicite),
A2 (composant à connotation valeur), A4 (couleur sémantique),
A6 (wording prescriptif libre), A10 (bouton/affichage conditionné
par valeur économique), FRONT-1.

**À la place :** affichage descriptif des 3 grandeurs
indépendamment, ordre fixe doctrinal.

### 6.5 — Anti-pattern P5 : Présentation du PERO comme « complément naturel »

**Interdits dans les chaînes affichées :**

- « PERO complète idéalement le dispositif PERECO »
- « PERO naturellement intégré dans la stratégie retraite »
- « solution complète PERO + PERECO »

**Pourquoi :** suggère une combinatoire prescriptive, alors que
chaque enveloppe doit pouvoir être lue isolément.

**À la place :** descriptions séparées par enveloppe. Le cabinet
construit la combinatoire, pas l'outil.

---

## §7 — Cohabitation historique

### 7.1 — Existence d'un PERO dans l'ancien comparateur

Une logique PERO **préexiste** dans le dépôt, intégrée à la page
« 🧮 Comparateur de dispositifs » (`app.py::page_comparateur`),
livrée en Phase A bien avant SP13. On y trouve dans `st.session_state` :

- `pero_actif` : checkbox d'activation
- `dirigeant_eligible_pero` : éligibilité à la catégorie objective
- `pero_mode_saisie` : mode pourcentage ou euros
- `pero_taux` : taux de cotisation
- `pero_montant` : montant fixe alternatif

Cette logique appartient à une autre époque du dépôt et à une
autre doctrine : antérieure à SP13 (doctrine réceptacles), antérieure
à SP20-SP22 (doctrine UI). Elle **n'a pas été construite sous les
contraintes doctrinales SP13-SP22**.

### 7.2 — Principe de cohabitation stricte (M-Q2=L1)

L'arbitrage M-Q2=L1 validé au cadrage SP23 fixe le principe
suivant : **ne pas toucher à l'ancien comparateur PERO**. Les
deux PERO coexisteront, distincts.

**Périmètres respectifs :**

| Aspect | Ancien PERO (page comparateur) | Nouveau PERO v1.3+ (si activé) |
|---|---|---|
| Localisation UI | `app.py::page_comparateur` | Page dédiée nouvelle, à intégrer comme SP20 a intégré la page « 🧰 Réceptacles auditables » |
| Doctrine appliquée | Phase A pré-SP13 | SP13-SP22 + présente doctrine PERO |
| Périmètre métier | Multi-flux (PERO + participation + intéressement + PEE + PERECO) | PERO seul, intégré à l'orchestrateur réceptacles |
| Audit PDF | Non disponible | À produire en SP26 (si activé) |
| Tests de neutralité UI | Non couverts par SP20-SP22 | Couverts dès SP26 |

### 7.3 — Absence de migration automatique

**Aucune migration automatique des paramètres** entre l'ancien
PERO et le nouveau PERO v1.3+ ne sera implémentée. L'utilisateur
cabinet qui souhaite utiliser le nouveau PERO devra resaisir ses
inputs dans la page dédiée. Cette absence est délibérée :

- Évite une dette de synchronisation entre deux états
- Évite la confusion sur quelle saisie sera prise en compte
- Cohérent avec SP20 qui n'a pas migré les saisies de l'ancien
  comparateur

### 7.4 — Conditions d'unification (différée)

Une unification éventuelle (suppression de l'ancien PERO,
migration des utilisateurs vers le nouveau) **ne relèvera pas du
chantier PERO v1.3**. Elle nécessiterait :

- Validation cabinet d'usage exclusif du nouveau PERO
- Régression complète sur l'ancienne page comparateur
- Plan de migration des utilisateurs

Ces conditions ne sont **pas** dans le périmètre SP24-SP26.
Elles relèvent d'une éventuelle phase de **rationalisation
ultérieure** (v1.4+) à cadrer séparément, et seulement après
preuve d'usage réel du nouveau module.

---

## §8 — Pré-cadrage SP24 (indicatif — module métier PERO)

> ⚠️ **Cette section constitue un pré-cadrage doctrinal indicatif.
> Les arbitrages opérationnels devront être réouverts via un cadrage
> Q1-Qn lors d'une éventuelle activation du chantier.**

### 8.1 — Fichier cible

`strategy/receptacles_pero.py`, à créer dans le pattern strict de
`strategy/receptacles_perin.py`, `strategy/receptacles_pee.py`,
`strategy/receptacles_pereco.py` (SP15-SP17). **Ne pas inventer un
nouveau pattern.**

### 8.2 — Dataclasses pré-cadrées

Indicatif, à confirmer au moment de l'activation :

- `LigneHorizonPero` : dataclass d'horizon analogue à
  `LigneHorizonReceptacle` du framework SP18. Champs minimaux pré-cadrés :
  `horizon_annees`, `flux_employeur_pero`, `flux_salarie_pero`,
  `economie_fiscale_immediate`, `effort_reel`, `cout_entreprise`,
  `capital_projete`, `fiscalite_sortie`, `valeur_nette`,
  `disponibilite`.
- `ResultatAllocationPero` : conteneur de résultats analogue
  `ResultatAllocationReceptacle*` SP15-SP17, avec champ
  `lignes_par_horizon: list[LigneHorizonPero]`.

**Validations algébriques `__post_init__` (à définir précisément
SP24) :**
- tolérance 0,01 € sur identités cross-champs
- cohérence `effort_reel` ↔ `flux_employeur_pero` ↔ `economie_fiscale_immediate`
- cohérence `cout_entreprise` ↔ `flux_employeur_pero` + forfait social

### 8.3 — Inputs pré-cadrés

**Obligatoires :**
- `salaire_brut_annuel: float` (assiette de cotisation)
- `tmi: float` (taux marginal d'imposition pour économie fiscale)
- `taux_cotisation_pero: float` (taux annuel exprimé en fraction)
- `horizons: tuple[int, ...]` (typiquement 5, 10, 20 ans pour
  comparabilité avec PERIN/PEE/PERECO)
- `rendement_annuel: float` (cohérent §4.7 convention transverse 2 %)

**Optionnels :**
- `categorie_objective_eligible: bool` (par défaut `True`)
- `forfait_social_taux: Optional[float]` (par défaut provider §4.1)
- `plafond_versement: Optional[float]` (par défaut provider §4.3)

**Interdits en SP24 (cf. §3 frontières négatives) :**
- rattrapages N-1/N-2/N-3
- architecture multi-collèges
- gestion RH avancée (catégories multiples, ancienneté pondérée)
- transferts inter-régimes
- rente complexe (table de mortalité, taux technique variable)
- solveur de taux

### 8.4 — Providers doctrinaux pré-cadrés

**Zéro magic number.** Trois providers à créer dans le module
métier (ou dans `doctrine.py` selon convention dépôt) :

- `obtenir_taux_forfait_social_pero(profil) -> float`
- `obtenir_plafond_pero(profil) -> dict` (plafond exonération
  sociale + plafond exonération IR)
- `obtenir_taux_ps_pero(profil) -> float`

Chaque provider devra logger une étape `REC_PERO_*` dans la
sous-trace audit, conformément au pattern SP15-SP17.

### 8.5 — TraceAudit attendue

**Cohérence stricte D-R10 :**
- Aucune étape `parent_id != None` produite
- Étapes plates dans la sous-trace `ligne_pero`
- Sous-traces nichées uniquement pour les horizons

**Codes étapes pré-cadrés (indicatifs) :**
- `REC_PERO_ELIGIBILITE` (racine sous-trace)
- `REC_PERO_TAUX_COTISATION_APPLIQUE`
- `REC_PERO_FLUX_EMPLOYEUR_BRUT`
- `REC_PERO_FORFAIT_SOCIAL`
- `REC_PERO_CSG_CRDS`
- `REC_PERO_TMI_APPLIQUEE`
- `REC_PERO_PLAFOND_VERSEMENT`
- `REC_PERO_ECONOMIE_FISCALE`
- `REC_PERO_COUT_ENTREPRISE`
- `REC_PERO_EFFORT_REEL`
- `REC_PERO_CAPITAL_PROJETE_<H>ANS` (par horizon)
- `REC_PERO_VALEUR_NETTE_<H>ANS` (par horizon)

### 8.6 — Wordings doctrinaux pré-cadrés

À ajouter dans `strategy/receptacles_wordings.py` (extension
SP18 sans modification des 16 wordings existants) :

- `WORDING_PERO_REGLE_COTISATION`
- `WORDING_PERO_CSG_CRDS_COTISATION`
- `WORDING_PERO_FISCALITE_SORTIE_RENTE`
- `WORDING_PERO_DISPONIBILITE_RETRAITE`

Wordings strictement descriptifs (cf. anti-pattern P3), formulation
analogue aux 4 wordings PEE/PERECO existants.

---

## §9 — Pré-cadrage SP25 (indicatif — orchestration et goldens)

> ⚠️ **Cette section constitue un pré-cadrage doctrinal indicatif.
> Les arbitrages opérationnels devront être réouverts via un cadrage
> Q1-Qn lors d'une éventuelle activation du chantier.**

### 9.1 — Extension de l'orchestrateur

L'orchestrateur `strategy/receptacles_orchestrateur.py::allocation_receptacles`
devra accueillir le PERO **sans modifier sa philosophie**. Le PERO
sera une **enveloppe supplémentaire**, pas une nouvelle architecture.

Le dataclass `ResultatAllocationReceptacles` (sortie de
l'orchestrateur) devra gagner un champ `pero: ResultatAllocationPero`
en parallèle des champs `perin`, `pee`, `pereco` existants.

### 9.2 — Ordre doctrinal fixe étendu

L'ordre doctrinal `ORDRE_DOCTRINAL_ENVELOPPES` de
`ui/adapter_receptacles.py` devra passer de :

```python
ORDRE_DOCTRINAL_ENVELOPPES = ("PERIN", "PEE", "PERECO")
```

à :

```python
ORDRE_DOCTRINAL_ENVELOPPES = ("PERIN", "PEE", "PERECO", "PERO")
```

**PERO en 4e position.** Cet ordre s'applique à :
- les tableaux multi-enveloppes (multi-horizon, par horizon)
- les onglets et sections de pages
- les étapes RECAP
- les signets PDF
- les boutons de navigation enveloppes

### 9.3 — Étapes RECAP cross-enveloppes

L'orchestrateur produira des étapes `REC_RECAP_<DIM>_<H>ANS`
incluant le PERO dans `valeurs_par_enveloppe`. **Strictement
descriptif :** aucune notion de « max », « min », « meilleur » dans
les codes ni dans les hypothèses.

### 9.4 — Goldens à produire

**Indicatif, à arbitrer SP25 le moment venu :**

- 1 nouveau mini-golden métier PERO (sur le modèle des 5 mini-goldens
  SP15-SP17 existants)
- 1 mise à jour du mini-golden orchestrateur (pour intégrer PERO)
- 1 nouveau golden PDF PERO (sur le modèle de
  `golden_receptacles.json` SP19)

**Préservation absolue :** les 6 goldens PDF existants + les 5
mini-goldens métier doivent rester **strictement conformes** sans
modification. Tout changement de leur empreinte serait une
régression.

### 9.5 — Stress tests pré-cadrés

À ajouter dans `test_renderer_stress.py` ou un test dédié :

- Salaire élevé (1 PASS, 5 PASS, 10 PASS)
- Taux de cotisation faible (1 %) et fort (8 %)
- Catégorie objective absente (éligibilité = False, doit dégrader
  proprement sans crash)
- Horizon retraite long (30, 40 ans)

---

## §10 — Pré-cadrage SP26 (indicatif — UI et audit PDF)

> ⚠️ **Cette section constitue un pré-cadrage doctrinal indicatif.
> Les arbitrages opérationnels devront être réouverts via un cadrage
> Q1-Qn lors d'une éventuelle activation du chantier.**

### 10.1 — Page UI cible

**Option par défaut, à arbitrer le moment venu :** intégrer le PERO
**dans la page existante « 🧰 Réceptacles auditables »** (SP20),
qui deviendrait « Réceptacles auditables incluant PERO ». Pas de
nouvelle page dédiée. Le tableau multi-horizon affiche 4 lignes
par horizon (PERIN, PEE, PERECO, PERO) au lieu de 3.

**Justification :** cohérence v1.2, UI-I1 garantit l'ordre fixe,
les utilisateurs cabinet retrouvent un point d'entrée unique.

**Alternative à arbitrer :** page séparée « 🧰 PERO auditable »
distincte. Plus modulable mais introduit un point d'entrée
supplémentaire.

### 10.2 — Saisie input PERO

**Sur le modèle de `saisir_inputs_orchestrateur` SP20 :**

- saisie du salaire brut annuel
- saisie du taux de cotisation PERO (avec aide tooltip neutre)
- case éligibilité catégorie objective (par défaut cochée)

**Sans :**
- assistant de dimensionnement
- préréglages valorisants (« situation typique cadre », « situation
  type dirigeant »)
- mise en évidence de plages « usuelles » par couleur

### 10.3 — Doctrine UI Réceptacles inchangée

**Aucune modification de `ARCHITECTURE_UI_RECEPTACLES.md`** au-delà
de l'extension naturelle de UI-I1 (déjà documentée § 6.1 pour
inclure les signets et boutons de navigation).

Les 12 anti-patterns A1-A10 + bis restent **strictement applicables**
au PERO. Les 15 patterns de qualification subjective SP21 + les
5 verbes interprétatifs SP22 restent **strictement applicables**.

**Le scan global UI-I6 devra couvrir le PERO** dès qu'il sera
livré (chaînes visibles `st.write`, labels boutons, captions).

### 10.4 — Hypothèses visibles PERO

À afficher dans le panneau hypothèses (extension du
`tableau_hypotheses_par_enveloppe` SP21) :

- taux de cotisation employeur PERO appliqué
- base salaire de référence
- taux forfait social appliqué (provider §4.1)
- TMI utilisée
- rendement (commun aux 4 enveloppes)

**Vocabulaire strict :** « Taux de cotisation employeur PERO »
(pas « Taux optimal »), « Forfait social appliqué » (pas « Charge
employeur favorable »).

### 10.5 — Audit PDF

À produire :

- `test_pdf_audit_render_pero.py` sur le modèle de
  `test_pdf_audit_render_receptacles.py` SP19
- Golden PDF PERO (extension de `golden_receptacles.json`)

**Préservation :** le golden PDF SP19 ne doit pas être modifié.
Soit on crée un nouveau golden « réceptacles + PERO » distinct,
soit on règle l'orchestrateur pour produire deux PDF (un sans
PERO compatible v1.2, un avec PERO v1.3+). Arbitrage SP25.

---

## §11 — Invariants critiques pré-cadrés (indicatif)

> ⚠️ **Cette section constitue un pré-cadrage doctrinal indicatif.
> Les arbitrages opérationnels devront être réouverts via un cadrage
> Q1-Qn lors d'une éventuelle activation du chantier.**

### 11.1 — Invariants doctrinaux à ajouter

À tester via `test_pdf_audit_render_pero.py` et
`test_strategy_receptacles.py` étendu :

- Aucun wording prescriptif PERO dans les chaînes visibles
  (cf. anti-patterns P1-P5)
- Ordre stable PERO maintenu partout (4e position après PERECO)
- Aucune logique UI économique spécifique au PERO

### 11.2 — Invariants métier à ajouter

À tester via `test_strategy_receptacles.py` (extension SP24) :

- Identités algébriques PERO (`__post_init__` sur `LigneHorizonPero`)
- Cohérence `flux_employeur_pero` ↔ `salaire_brut × taux_cotisation`
- Cohérence `effort_reel` ↔ identité économique retenue
- Cohérence `cout_entreprise` ↔ flux employeur + forfait social
- Plafonds respectés (versement, abondement, exonération sociale)

### 11.3 — Invariants UI à ajouter

À tester via `test_ui_receptacles_neutralite.py` étendu :

- Scan lexical PERO : aucun mot interdit dans les chaînes visibles
  liées au PERO (UI-I2 + UI-I6 étendus)
- Scan boutons : aucun bouton conditionné par valeur économique
  PERO (A10 étendu)
- Scan labels : aucun verbe interprétatif autour du PERO
  (A9 étendu)

**Aucun nouvel invariant UI-I7+ n'est pré-cadré.** L'extension
SP26 reposera sur les 6 invariants UI existants (UI-I1 à UI-I6)
appliqués au périmètre étendu PERO.

---

## §12 — Ce qu'il ne faut surtout pas faire (5 dangers transversaux)

Cette section reprend explicitement les 5 dangers transversaux
identifiés au cadrage SP23. Chaque danger est nommé pour pouvoir
être refusé sans ambiguïté à toute étape du chantier (si activé).

### 12.1 — Danger 1 : Transformer le PERO en moteur RH

L'outil **n'est pas un configurateur RH**. Il ne :

- gère pas les catégories objectives multiples
- ne définit pas les périmètres salariés
- ne propose pas d'architecture sociale
- ne modélise pas les conventions collectives

Le PERO entre dans l'outil **uniquement comme enveloppe économique
pour un dirigeant assimilé salarié donné, avec un taux de cotisation
donné**. Tout ce qui dépasse cela relève du conseil RH/social, hors
mandat.

### 12.2 — Danger 2 : Ajouter des simulations d'optimisation

**Interdit :**

- recherche de « taux PERO optimal »
- simulateur « quel taux pour quel objectif »
- assistant de dimensionnement

**Pourquoi :** transformer le moteur en outil prescriptif viole
FRONT-1 (`KNOWN_LIMITATIONS.md` §0.3).

### 12.3 — Danger 3 : Introduire du scoring (même implicite)

**Interdit :**

- score d'efficacité PERO
- score de pertinence PERO
- indice composite cross-enveloppes
- « note » ou « rang » d'une configuration

**Y compris** : tri par valeur économique, mise en évidence visuelle
conditionnelle, ordre des onglets selon performance. Tous ces
mécanismes sont du scoring implicite.

### 12.4 — Danger 4 : Créer une logique UI spécifique au PERO

Le PERO **doit consommer le framework UI existant** (composants,
adapter, page Réceptacles auditables). Pas de nouveaux composants
Streamlit hors framework SP20-SP22. Pas de nouvelle frontière
adapter spécifique PERO. Pas de nouvelles couleurs ni typographies.

Si le besoin d'un nouveau composant émergeait, il devrait
**d'abord** être intégré au framework existant (avec doctrine
mise à jour si nécessaire), **pas** créé en parallèle.

### 12.5 — Danger 5 : Refondre l'orchestrateur

L'orchestrateur `allocation_receptacles` accueille PERO en **4e
enveloppe**, sans changement de signature publique notable (le
champ `pero` du résultat est ajouté ; les champs `perin`, `pee`,
`pereco` restent identiques).

**Interdit :**

- changer la philosophie composition séquentielle SP18
- introduire un mécanisme de classement
- introduire un mécanisme de pondération inter-enveloppes
- introduire une dépendance de calcul entre PERO et les autres
  enveloppes

Le PERO est une **nouvelle enveloppe**, pas une **nouvelle
architecture**.

---

## §13 — Conditions de réactivation du chantier PERO

> **Section critique du document SP23.** Cette section porte la
> gouvernance d'activation du chantier PERO. Sans franchissement
> explicite des conditions ci-dessous, le chantier PERO **reste
> non activé**, indépendamment de la complétude doctrinale du
> présent document.

### 13.1 — Principe directeur

Le présent document constitue une **doctrine préparatoire**.
Son existence ne crée **aucune obligation de mise en œuvre** ni
**aucun engagement de calendrier**. La discipline SP1→SP22 a
démontré que la capacité à **suspendre la construction** est aussi
importante que la capacité à construire.

Le chantier PERO ne sera activé que si une **demande terrain
réelle** le justifie — pas par anticipation, pas par cohérence
architecturale interne, pas par « complétion produit ».

### 13.2 — Critères concrets de réactivation

Le chantier PERO peut être réactivé si **au moins l'un** des
critères suivants est observé.

> **Évolution doctrinale SP23-bis (mai 2026).** Cette section a
> été partitionnée en **§13.2a** (critères terrain C1-C5) et
> **§13.2b** (critère de maturité systémique C6, avec clause
> anti-abus). La partition formalise une distinction de nature :
> C1-C5 sont des signaux d'usage cabinet, C6 est un signal système.
> Les mélanger affaiblirait la hiérarchie conceptuelle.

#### 13.2a — Critères terrain (signaux d'usage cabinet)

**Critère C1 — Demande cabinet explicite.** Un cabinet utilisateur
exprime explicitement le besoin de modéliser le PERO dans le
cadre d'un arbitrage rémunération dirigeant, après avoir utilisé
les modules PERIN, PEE, PERECO existants. La demande doit être :
- documentée (verbatim, message, brief)
- récurrente (au moins 2 cabinets distincts ou 3 occurrences chez
  un même cabinet sur des dossiers différents)
- concrète (associée à un cas dirigeant identifié, pas une
  question abstraite « est-ce que vous gérez le PERO »)

**Critère C2 — Insuffisance identifiée du PERIN/PERECO.** L'usage
réel des modules PERIN et PERECO révèle une **insuffisance
structurelle** pour traiter des cas dirigeant assimilé salarié
fréquemment rencontrés. Cette insuffisance doit être :
- décrite précisément (quel type de profil, quel arbitrage)
- non substituable par une combinaison PERIN+PERECO
- documentée sur au moins 3 dossiers réels

**Critère C3 — Usage ancien PERO insuffisant.** L'ancien PERO de
la page comparateur (cf. §7) est utilisé en pratique par des
cabinets, **mais** son périmètre, sa neutralité doctrinale ou
son auditabilité PDF se révèlent insuffisants pour ces usages.
La preuve d'usage doit être documentée (sessions observées,
verbatims, demandes de fonctionnalités sur la page comparateur).

**Critère C4 — Besoin audit cabinet réel.** Un cabinet demande
explicitement un PDF audit cabinet incluant le PERO (ce que
l'ancienne page comparateur ne produit pas). La demande doit
être associée à un dossier client réel et un usage déontologique
identifié (justification d'arbitrage cabinet face à un dirigeant).

**Critère C5 — Verbatims récurrents.** Au moins **5 verbatims
distincts** d'utilisateurs cabinet mentionnent le PERO comme
limite ou comme besoin, sur une période d'observation d'au moins
**3 mois** d'utilisation effective des modules v1.2 existants.

#### Transition §13.2a → §13.2b

Les critères C1-C5 correspondent à des **signaux d'usage terrain**.
Le critère C6 ci-dessous relève d'une **logique distincte** :
maturité systémique du framework et capacité démontrée d'extension
incrémentale sans refonte.

Cette distinction est structurante. C1-C5 et C6 ne sont **pas
interchangeables** :
- C1-C5 sont auto-limitants (nécessitent verbatims, dossiers,
  demandes documentées — difficiles à fabriquer)
- C6 est plus facilement invocable (la maturité système est
  observable depuis l'intérieur du projet) et donc plus sujet à
  abus si non encadré

C'est pourquoi C6 est accompagné d'une **clause anti-abus** et de
**restrictions d'usage explicites** dans §13.2b, restrictions qui
n'ont pas de pendant pour C1-C5.

#### 13.2b — Critère de maturité plateforme (signal système)

**Critère C6 — Maturité systémique du framework.** L'activation
d'un chantier peut être autorisée lorsque l'ensemble des conditions
suivantes est démontrablement vérifié :

- **Framework stabilisé** : le moteur de calcul (`strategy/*`,
  `core/*`) et le renderer PDF (`ui/pdf_audit_export.py`) ne
  nécessitent aucune modification pour absorber le chantier
- **Doctrine verrouillée** : la doctrine pertinente
  (`ARCHITECTURE_RECEPTACLES.md`, `ARCHITECTURE_RENDERER.md`,
  `ARCHITECTURE_UI_RECEPTACLES.md`) est figée et l'extension
  visée s'inscrit dans son cadre sans amendement
- **Dette gouvernée** : la table de bord `KNOWN_LIMITATIONS.md`
  §0 reflète l'état réel du dépôt, avec dettes actives et
  frontières assumées correctement classifiées
- **Chantier sans refonte structurelle** : l'extension visée
  ne requiert aucune modification des invariants fondamentaux
  (UI-I1 à UI-I6 inchangés, D-R\* inchangés, garde-fous SP18
  inchangés), même au prix d'un périmètre fonctionnel réduit
- **Coût marginal incrémental** : l'effort estimé est de
  l'ordre d'une extension du framework existant (réutilisation
  des patterns SP15-SP22), pas d'une nouvelle architecture
- **Doctrine préparatoire existante** : le chantier dispose
  déjà d'un document de capitalisation doctrinale (à la manière
  de `ARCHITECTURE_PERO.md` SP23) couvrant nature économique,
  frontières négatives, conventions, sémantique, anti-patterns,
  cohabitation historique éventuelle

##### Clause anti-abus C6

Cette clause est **non négociable** :

Le critère C6 ne peut être invoqué que pour :

- une **extension incrémentale** au framework existant (et non
  une refonte, même partielle)
- un chantier déjà **pré-documenté** par une doctrine préparatoire
  produite **antérieurement** à l'invocation de C6 (pas de
  doctrine écrite ad hoc pour justifier l'activation)
- une extension **compatible avec les invariants existants** sans
  modification de leur formulation actuelle
- une extension **sans modification des fondations** du dépôt
  (renderer, core, doctrine UI, framework SP18)

L'invocation de C6 doit être **documentée explicitement** : un
journal d'activation listant point par point en quoi chacune des
conditions C6 ci-dessus est vérifiée pour le chantier considéré
(cf. §13bis pour la justification PERO).

##### Distinction entre C6 et les conditions exclues §13.3

C6 doit être soigneusement distingué des motifs explicitement
**exclus** par §13.3 :

| Motif | Statut | Différence |
|---|---|---|
| **« Complétion produit »** (§13.3) | Exclu | C6 ne dit pas « il manque PERO pour compléter ». C6 dit « si on devait l'ajouter, l'effort serait incrémental ». La capacité d'absorption n'est pas un besoin produit. |
| **« Cohérence architecturale »** (§13.3) | Exclu | C6 ne dit pas « le framework accueillerait facilement ». C6 dit « le framework est stabilisé ET la doctrine préparatoire existe ET les invariants ne bougent pas ». La facilité technique seule n'est pas C6. |
| **« Veille concurrentielle »** (§13.3) | Exclu | C6 ne s'appuie sur aucun argument externe au projet. |
| **« Continuité de l'élan »** (§13.3) | Exclu | C6 ne dit pas « la discipline est rodée, enchaînons ». C6 dit « la maturité système permet d'activer **un chantier précis pré-documenté** ». Sans doctrine préparatoire antérieure, C6 ne s'applique pas. |

**Règle pratique :** si un chantier ne dispose pas d'une doctrine
préparatoire produite **antérieurement** à l'invocation de C6,
alors l'invocation est un **abus de C6** au sens §13.3 « cohérence
architecturale » ou « continuité de l'élan », et doit être refusée.

##### Restrictions d'usage de C6

- C6 ne peut **pas** justifier l'activation d'un chantier modifiant
  le framework, le renderer, le core, ou les invariants gravés
- C6 ne peut **pas** justifier l'activation d'un chantier pour
  lequel aucune doctrine préparatoire n'a été produite à l'avance
- C6 ne peut **pas** justifier l'activation simultanée de plusieurs
  chantiers : un seul chantier activable à la fois (sauf signal
  terrain C1-C5 surajouté)
- C6 ne dispense **pas** de la procédure §13.4 (mise à jour
  PERO-D0, cadrage SP24 explicite, batterie complète à chaque
  étape, etc.)

### 13.3 — Conditions exclues de réactivation

Les motifs suivants **n'autorisent pas** la réactivation du
chantier :

- **« complétion produit »** : argument selon lequel « il faut
  ajouter PERO parce que les 3 autres enveloppes sont livrées ».
  Non, la complétude n'est pas un objectif en soi.
- **« cohérence architecturale »** : argument selon lequel le
  framework SP18 « accueillerait facilement » une 4e enveloppe.
  La facilité technique ne justifie pas l'engagement métier.
- **« veille concurrentielle »** : argument selon lequel un outil
  concurrent traite le PERO. Le mandat de l'outil est défini par
  les besoins cabinet identifiés, pas par parité fonctionnelle.
- **« continuité de l'élan »** : argument selon lequel « la
  discipline méthodologique est rodée, on peut enchaîner ». C'est
  précisément le piège que ce document est conçu pour éviter.

### 13.4 — Procédure de réactivation

Si l'un des critères §13.2 est satisfait :

1. **Documenter formellement** le critère satisfait dans le journal
   `KNOWN_LIMITATIONS.md` (entrée PERO-D0 mise à jour).
2. **Réviser le présent document** : §4 (conventions France 2026 à
   reconfirmer selon réglementation en vigueur), §7 (cohabitation
   à réexaminer selon l'évolution de l'ancien PERO), §8-§11
   (pré-cadrages à réouvrir via questions Q1-Qn).
3. **Cadrage SP24 spécifique** : poser les questions Q1-Qn de
   SP24 selon le pattern SP15-SP17, valider explicitement chaque
   arbitrage avec l'utilisateur cabinet ou décisionnaire.
4. **Engager SP24 → SP25 → SP26** dans l'ordre, avec batterie
   complète à chaque étape (discipline F-Q1=a SP21/SP22).
5. **Mettre à jour PERO-D0 en clôture** : passage de « Documenté
   non activé » à « Active » puis « Clôturée vN » selon livraison.

### 13.5 — Procédure de non-réactivation prolongée

Si **aucun** critère §13.2 n'est satisfait sur une période d'au
moins **12 mois** d'usage cabinet réel des modules v1.2, le
chantier PERO peut être :

- **maintenu en l'état** (doctrine préparatoire conservée comme
  référence)
- **déclassé en « Frontière doctrinale »** dans la table de bord
  (le statut passe alors de « Chantier documenté non activé » à
  « Frontière assumée — pas de modélisation PERO », par cohérence
  avec FRONT-1)

Le déclassement en frontière ne signifie pas l'absence d'intérêt
pour le PERO, mais **acte que l'outil ne le modélisera pas**, par
choix de positionnement produit. Toute reprise ultérieure
nécessiterait un repositionnement explicite (changement de mandat).

### 13.6 — Responsabilité de l'arbitrage de réactivation

L'arbitrage de réactivation appartient au **décisionnaire produit**
(utilisateur principal du présent dépôt). Aucune équipe technique,
aucune contribution externe ne peut activer le chantier de sa
propre initiative. Le présent document est conçu pour rendre cette
gouvernance **non négociable techniquement** : tant que PERO-D0
n'est pas marqué « Activé » dans `KNOWN_LIMITATIONS.md` et tant
qu'une SP24 n'a pas été formellement cadrée, aucun fichier
`strategy/receptacles_pero.py` ne doit exister dans le dépôt.

### 13bis — Journal d'activation : invocation de C6 pour PERO (SP23-bis)

> **Décision de gouvernance (mai 2026, SP23-bis).** Le chantier
> PERO est **activé via le critère C6** (§13.2b). La présente
> sous-section documente point par point comment chacune des
> 6 conditions C6 est satisfaite pour le chantier PERO. Conforme
> à la clause anti-abus C6 et à la règle pratique §13.2b.

**Conditions C6 satisfaites pour PERO :**

| Condition C6 | Vérification PERO |
|---|---|
| Framework stabilisé | Renderer PDF (`ui/pdf_audit_export.py`) et core (`core/audit.py`, `core/profil.py`) figés depuis v1.0.1. 50 invariants renderer + 49 stress tests verts. 6 goldens PDF strictement conformes. Hash baseline `8863991f27f67847` inchangé sur SP13→SP23. **Aucune modification du framework ne sera requise pour PERO.** |
| Doctrine verrouillée | `ARCHITECTURE_RENDERER.md` (727 lignes) figée v1.1.1. `ARCHITECTURE_RECEPTACLES.md` (~860 lignes) figée v1.1.0+. `ARCHITECTURE_UI_RECEPTACLES.md` (685 lignes, 12 anti-patterns + 6 invariants) figée v1.2. **Aucun amendement requis** pour absorber PERO ; seule la constante `ORDRE_DOCTRINAL_ENVELOPPES` de l'adapter SP20 passera de 3 à 4 éléments (pas un changement de doctrine). |
| Dette gouvernée | `KNOWN_LIMITATIONS.md` §0 reflète l'état réel : 3 dettes clôturées, 9 actives, 1 frontière, 1 chantier documenté non activé (PERO-D0 actuel). 14 entrées table de bord visibles. Indicateurs de gouvernance v1.2 à jour. |
| Sans refonte structurelle | Le pré-cadrage SP24 (§8) confirme : pattern strict SP15-SP17 copié, aucun nouvel invariant fondamental, D-R10 respecté, étapes plates. Le pré-cadrage SP25 (§9) confirme : extension orchestrateur sans changement de philosophie. Le pré-cadrage SP26 (§10) confirme : aucun nouveau composant UI hors framework SP20-SP22, 6 invariants UI-I1 à UI-I6 inchangés. |
| Coût marginal incrémental | Estimation cumulée SP24+SP25+SP26 (votre lecture SP23) : équivalent à SP15-SP17 (module) + SP18-SP19 (orchestration + goldens) + SP20-SP22 (UI + audit PDF). C'est un chantier substantiel mais **strictement incrémental** : aucune fondation nouvelle, réutilisation des 5 patterns existants. |
| Doctrine préparatoire existante | `ARCHITECTURE_PERO.md` (~1091 lignes avant SP23-bis, 15 sections §0-§14) produite **antérieurement** à l'invocation de C6, lors de SP23. Couvre : statut, nature économique, tableau différentiel, frontières négatives, conventions France 2026, sémantique économique, anti-patterns P1-P5, cohabitation historique, pré-cadrages SP24/SP25/SP26 indicatifs, 5 dangers transversaux. **Cette pré-existence est ce qui distingue C6 de l'abus « continuité de l'élan » (§13.3).** |

**Conformité à la clause anti-abus §13.2b :**

- Extension **incrémentale** : oui (pas de refonte)
- Chantier **pré-documenté** : oui (`ARCHITECTURE_PERO.md` SP23
  antérieure à SP23-bis)
- **Compatible avec les invariants** existants : oui (UI-I1 à
  UI-I6, D-R10, garde-fous SP18 inchangés)
- **Sans modification des fondations** : oui (renderer, core,
  doctrine UI, framework SP18 intacts)

**Conformité aux restrictions d'usage §13.2b :**

- Pas de modification framework/renderer/core/invariants : oui
- Doctrine préparatoire produite à l'avance : oui (SP23 antérieure)
- Activation d'un seul chantier à la fois : oui (PERO uniquement)
- Procédure §13.4 respectée : oui (mise à jour PERO-D0 dans
  `KNOWN_LIMITATIONS.md`, cadrage SP24 à conduire formellement,
  batterie complète à chaque étape de SP24 → SP26)

**Distinction explicite des motifs exclus §13.3 :**

- Cette activation **n'est pas** un argument de « complétion
  produit » : PERO n'est pas activé parce qu'il manquerait. Il
  est activé parce qu'il est *prêt à être activé sans coût
  structural*.
- Cette activation **n'est pas** un argument de « cohérence
  architecturale » seul : C6 exige **également** la doctrine
  préparatoire antérieure, qui est ce qui rend l'extension
  contrôlable.
- Cette activation **n'est pas** une « continuité de l'élan » :
  une pause méthodologique a été marquée (SP23 a explicitement
  positionné le chantier comme non activé ; SP23-bis amende
  formellement §13.2 avant d'activer ; le garde-fou §13.6 a été
  respecté).

**Conséquences immédiates de l'activation :**

- PERO-D0 passe du statut « Documenté non activé » à
  « **Activé via C6 (SP23-bis)** » dans `KNOWN_LIMITATIONS.md` §0.5
- §0 du présent document mis à jour pour refléter le statut
  « chantier activé »
- SP24 (module métier PERO) peut être cadrée formellement Q1-Qn
  selon procédure standard, dans la continuité de la discipline
  SP15-SP17

**Conséquences durables (pour audit historique) :**

- §13bis reste dans le document comme **journal d'activation
  permanent** : trace écrite de quand, comment et pourquoi C6 a
  été invoqué pour la première fois
- Toute invocation future de C6 (pour un autre chantier que PERO)
  devra produire un journal analogue en §13ter, §13quater, etc.
- Le format point-par-point du tableau ci-dessus est la **forme
  de référence** pour toute invocation C6

---

## §14 — Références croisées

Le présent document s'articule avec les autres doctrines du dépôt :

- **`ARCHITECTURE_RECEPTACLES.md`** (SP13, ~860 lignes) — doctrine
  du module Réceptacles v1.1.0. Le PERO étendra cette doctrine
  (4e enveloppe). La §3.6 tableau doctrinal transverse devra
  intégrer le PERO lors d'une activation SP25.
- **`ARCHITECTURE_RENDERER.md`** (SP1-SP11, ~727 lignes) — doctrine
  du renderer PDF. Aucun changement requis : le PERO consomme le
  framework existant (D-R10, étapes plates, sous-traces horizons).
- **`ARCHITECTURE_UI_RECEPTACLES.md`** (SP20-SP22, ~685 lignes,
  12 anti-patterns + 6 invariants) — doctrine UI. Aucun nouveau
  invariant pré-cadré : les 6 invariants UI-I1 à UI-I6 couvrent
  le périmètre PERO étendu (sous réserve de mise à jour de la
  constante `ORDRE_DOCTRINAL_ENVELOPPES`).
- **`KNOWN_LIMITATIONS.md`** §0.5 — entrée **PERO-D0** dans la
  catégorie « Chantiers documentés non activés ». Référence vers
  le présent document.

**Lecture transverse recommandée pour reprise éventuelle :**

1. Relire d'abord `KNOWN_LIMITATIONS.md` §0.1 à §0.5 pour situer
   l'état du dépôt et confirmer le statut PERO-D0.
2. Relire ensuite le présent document §0, §13 pour confirmer la
   gouvernance d'activation.
3. Relire ensuite `ARCHITECTURE_RECEPTACLES.md` SP13/D-R\* pour
   le pattern à reproduire.
4. Engager SP24 seulement après cadrage Q1-Qn validé.

---

**Fin de la doctrine PERO v0.2 (SP23 + SP23-bis).**

**Statut :** chantier **activé via C6** (cf. §13.2b + §13bis journal
d'activation). Développement SP24 → SP26 à conduire selon discipline
standard (cadrage Q1-Qn par sous-passe, batterie complète à chaque
étape, préservation absolue du framework et des invariants).
