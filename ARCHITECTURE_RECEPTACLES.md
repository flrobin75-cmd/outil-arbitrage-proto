# ARCHITECTURE_RECEPTACLES.md

**Doctrine métier et technique du module d'allocation de flux vers
enveloppes sociales/retraite (v1.1.0).**

Document de référence pour le périmètre v1.1 « réceptacles » :
PERIN + PEE + PERECO. Statut **vivant** — toute modification
structurelle du module doit s'accompagner d'une mise à jour
correspondante de ce document. Pendant Hardening, c'est ce document
qui est consulté en premier sur toute question de périmètre métier
ou de frontière.

| Métadonnée | Valeur |
|---|---|
| Version cible | v1.1.0 (extension métier du framework v1.0.1) |
| Périmètre v1.1 | PERIN + PEE + PERECO |
| Statut Hardening framework | v1.0.1 clôturée (SP9-SP12), 489 contrôles + 5 goldens |
| Sous-passes v1.1 prévues | SP13 (ce doc) → SP14 (scaffolding) → SP15-17 (3 modules) → SP18 (orchestrateur) → SP19 (PDF audit) |
| Référence framework | `ARCHITECTURE_RENDERER.md` |

---

## §1 — Philosophie

### 1.1 Contrat d'évolution v1.1

La v1.1 est une **extension métier** du framework v1.0.1, pas une
modification du framework. Cette distinction est non négociable et
définit l'ensemble du périmètre d'action autorisé.

**Ce que v1.1 PEUT faire :**

- Ajouter de nouveaux modules métier dans `strategy/`
- Produire de nouvelles `TraceAudit` racines, conformes à la
  grammaire `core/audit.py` v1.1.0 actuelle
- Consommer la signature publique `generer_pdf_audit(trace, ...)`
  sans modification
- Ajouter de nouveaux namespaces de codes (`PERIN_*`, `PEE_*`,
  `PERECO_*`, `REC_*`)
- Ajouter de nouveaux tests dédiés (`test_strategy_receptacles.py`,
  `test_pdf_audit_render_receptacles.py`) et de nouveaux goldens
- Ajouter de nouvelles constantes réglementaires dans `doctrine.py`

**Ce que v1.1 NE PEUT PAS faire :**

- Modifier `ui/pdf_audit_export.py` (renderer audit cœur)
- Modifier `core/audit.py` (grammaire `TraceAudit`)
- Casser les invariants `test_renderer_invariants.py` (G1-G5, §4,
  D1-D15, surface publique)
- Casser les goldens existants (5 cas v1.0.0)
- Modifier les fichiers de test figés (pilote TNS, Assimilé, Libéral,
  Comparateur, helper commun)
- Introduire une logique métier dans le renderer (toute exception par
  régime est interdite par §4 d'`ARCHITECTURE_RENDERER.md`)
- Bumper `AUDIT_PDF_SPEC_VERSION` ou `AUDIT_SPEC_VERSION` sans
  sous-passe Hardening formelle dédiée

### 1.2 Pourquoi un module séparé

Les arbitrages de rémunération existants (`arbitrage_complet_tns`,
`arbitrage_complet`, `arbitrage_complet_liberal`,
`calcul_comparateur_regimes`) calculent un **net dirigeant** à
horizon zéro. Ils répondent à la question : « combien me reste-t-il
en poche après rémunération + IS + IR + cotisations ? ».

Le module réceptacles répond à une **question complémentaire** :
« étant donné un flux disponible à placer, comment ce flux se
comporte-t-il dans les différentes enveloppes sociales et retraite ? ».

Ces deux questions ont des **logiques différentes** :

| Aspect | Rémunération (v1.0) | Réceptacles (v1.1) |
|---|---|---|
| Horizon | Statique (snapshot) | Multi-période (5/10/20 ans) |
| Question | « Combien net ? » | « Combien à terme dans chaque enveloppe ? » |
| Levier principal | Choix du régime / stratégie | Choix de l'enveloppe pour un flux donné |
| Sortie principale | Net dirigeant immédiat | Capital projeté + effort réel + disponibilité |
| Granularité fiscale | À l'année courante | Plafonds annuels + déductibilité + sortie |

Fusionner les deux logiques dans une seule fonction serait une
erreur d'architecture : on perdrait l'autonomie de chacune, on
augmenterait la surface de couplage, et les modifications de l'une
risqueraient de casser l'autre.

**Décision D-R1** : deux moteurs indépendants (rémunération existant
+ réceptacles nouveau), chacun avec sa propre `TraceAudit` racine,
chacun audit-renderable séparément.

### 1.3 Comment v1.1 s'inscrit dans le pattern SP1-SP12

La phase Hardening v1.0.1 a démontré empiriquement que le framework
absorbe sans modification :

- 4 régimes différents (TNS, Assimilé, Libéral, Comparateur)
- Profondeurs 1 à 5 (et jusqu'à 7-8 en stress)
- Volumétries 70 à 412 étapes (et jusqu'à 1000 en stress)

Le module réceptacles s'inscrit comme un **5ème régime** au sens du
framework : `arbitrage_receptacles(profil, *, flux_disponible, audit)`
produit une `TraceAudit(regime="Réceptacles", ...)` qui sera rendue
**par le même renderer** sans aucune modification.

C'est précisément la propriété que la Phase Hardening a protégée :
la neutralité structurelle.

---

## §2 — Périmètre fonctionnel

### 2.1 Les 3 enveloppes couvertes en v1.1

| Enveloppe | Nature | Logique fiscale principale |
|---|---|---|
| **PERIN** | Plan d'Épargne Retraite Individuel (titre 1) | Déduction du revenu imposable IR à l'entrée, fiscalité à la sortie |
| **PEE** | Plan d'Épargne Entreprise (épargne salariale) | Abondement employeur défiscalisé, exonération PV à la sortie après 5 ans |
| **PERECO** | Plan d'Épargne Retraite Collectif (épargne salariale retraite) | Abondement employeur + déduction IR à l'entrée (titre 3 PERIN-d'entreprise) |

### 2.2 Question principale traitée

> Étant donné un flux disponible (typiquement issu de la rémunération
> du dirigeant), **comparer le comportement de ce flux** dans chacune
> des 3 enveloppes selon plusieurs dimensions économiques et selon
> 3 horizons (5/10/20 ans).

L'output est une **comparaison multi-dimensionnelle** entre les
3 enveloppes pour un flux donné, **pas une recommandation
d'allocation**. Le cabinet conserve la décision finale.

### 2.3 Dimensions de comparaison

Pour chaque enveloppe × chaque horizon, le module calcule :

| Dimension | Définition | Unité |
|---|---|---|
| Flux entrant brut | Montant versé dans l'enveloppe avant tout traitement | EUR |
| Économie fiscale immédiate | Réduction IR/IS résultant du versement | EUR |
| Effort réel | Flux entrant brut − économie fiscale immédiate | EUR |
| Capital projeté à l'horizon | Valeur de l'enveloppe à l'horizon (capitalisation simplifiée) | EUR |
| Fiscalité de sortie | IR + prélèvements sociaux à la sortie | EUR |
| Valeur nette à l'horizon | Capital projeté − fiscalité de sortie | EUR |
| Disponibilité | Conditions de retrait (déblocage anticipé, fin de carrière, etc.) | qualitatif |
| Coût entreprise | Coût employeur (cotisations patronales, abondement) | EUR |

Ces 8 dimensions définissent le **vocabulaire économique commun**
verrouillé en §3.

### 2.4 Inputs requis

| Input | Source | Exemple |
|---|---|---|
| Flux disponible | Paramètre explicite | 20 000 € |
| Profil dirigeant | Existant (`core.profil.Profil`) | TMI 30 %, dirigeant TNS |
| Horizon(s) | Liste validée [5, 10, 20] | [5, 10, 20] ans |
| Hypothèses rendement | Doctrine | 2 % net/an conservateur, capitalisation simple |
| Plafonds réglementaires | `doctrine.py` | PERIN : 10 % BNC + 15 % au-delà PASS, etc. |

### 2.5 Sorties produites

| Sortie | Forme |
|---|---|
| `TraceAudit` racine | Avec 3 sous-traces (une par enveloppe), 3 horizons par enveloppe |
| Résultat structuré | dataclass `ResultatAllocationReceptacles` (4 lignes × 3 horizons) |
| Disclaimers permanents | Mentions doctrine (comparabilité, primauté cabinet, etc.) |

---

## §3 — Unités économiques (vocabulaire verrouillé)

Cette section **verrouille le vocabulaire** utilisé par tous les
modules métier `strategy/receptacles_*.py`. Toute ambiguïté
sémantique introduite ailleurs viole cette doctrine.

### 3.1 Distinction flux vs stock

| Terme | Définition | Exemple |
|---|---|---|
| **Flux** | Mouvement monétaire à une date donnée (versement, sortie) | « Verser 20 000 € sur PERIN en année 0 » |
| **Stock** | Valeur d'une enveloppe à une date donnée | « Capital PERIN à 10 ans » |

**Règle stricte** : les codes d'étapes doivent refléter cette
distinction. Pas de `PERIN_VALEUR` ambigu — soit `PERIN_FLUX_VERSE`
(flux), soit `PERIN_CAPITAL_PROJETE_10ANS` (stock).

### 3.2 Distinction nominal vs net

| Terme | Définition | Exemple |
|---|---|---|
| **Brut / nominal** | Avant tout prélèvement | Versement brut 20 000 € |
| **Net** | Après prélèvement explicite | Versement net après IR évité |

**Règle stricte** : tout code contenant `NET` doit préciser **net de
quoi**. Pas de `PERIN_NET` ambigu — soit `PERIN_NET_APRES_IR_SORTIE`,
soit `PERIN_NET_APRES_PS_SORTIE`.

### 3.3 Vocabulaire économique verrouillé

| Terme officiel | Définition opérationnelle | Synonymes interdits |
|---|---|---|
| **Flux entrant brut** | Montant nominal versé sur l'enveloppe en année 0 | « versement », « apport », « cotisation » seuls (trop génériques) |
| **Économie fiscale immédiate** | Réduction d'impôt (IR ou IS) directement attribuable au versement, en année 0 | « gain fiscal », « avantage fiscal », « réduction IR » |
| **Effort réel** | Flux entrant brut − économie fiscale immédiate = ce que le dirigeant débourse réellement net | « coût net », « effort net », « décaissement effectif » |
| **Capital projeté à H ans** | Stock dans l'enveloppe à l'horizon H, après capitalisation simplifiée | « valeur projetée », « épargne à terme » |
| **Fiscalité de sortie** | Total IR + prélèvements sociaux dus à la sortie de l'enveloppe à H ans | « impôts sortie » |
| **Valeur nette à H ans** | Capital projeté − fiscalité de sortie | « net final », « net retraite » |
| **Disponibilité** | Conditions et délais de retrait possibles avant l'horizon | « liquidité » (interdit, car connoté marché financier) |
| **Coût entreprise** | Coût employeur direct (cotisations patronales sur versement, abondement payé) | « charge employeur », « coût patronal » |

### 3.4 Notation des horizons

Les horizons sont toujours notés en **années pleines** sur les codes :
`5ANS`, `10ANS`, `20ANS`. Jamais en mois, jamais en variantes
(`5A`, `5_ANS`, `5_YEAR`).

**Exemple de codes conformes** :
```
REC_PERIN_FLUX_VERSE              (flux à l'entrée)
REC_PERIN_ECO_FISCALE_IMMEDIATE   (économie en année 0)
REC_PERIN_EFFORT_REEL             (flux − économie)
REC_PERIN_CAPITAL_PROJETE_5ANS    (stock à 5 ans)
REC_PERIN_CAPITAL_PROJETE_10ANS   (stock à 10 ans)
REC_PERIN_CAPITAL_PROJETE_20ANS   (stock à 20 ans)
REC_PERIN_FISC_SORTIE_10ANS       (fiscalité de sortie à 10 ans)
REC_PERIN_VALEUR_NETTE_10ANS      (capital − fiscalité à 10 ans)
```

### 3.5 Notation de l'enveloppe

Tous les codes du module commencent par `REC_` (Receptacles), suivi
de l'enveloppe (`PERIN`, `PEE`, `PERECO`), puis du concept. Pas de
codes nus `PERIN_*` ou `PEE_*` qui pourraient être confondus avec
d'autres modules.

**Décision D-R2** : namespace de codes `REC_<ENVELOPPE>_<CONCEPT>[_<HORIZON>]`.

### 3.6 Tableau doctrinal transverse des dimensions économiques (SP17)

Cette matrice **verrouille** la logique économique de chaque enveloppe
v1.1. Elle est testée explicitement dans `test_strategy_receptacles.py`
section 15 (contrôles 15.3 à 15.7). Toute évolution future qui
modifierait une cellule doit faire l'objet d'une sous-passe formelle.

| Dimension                          | PERIN     | PEE       | PERECO    |
|------------------------------------|-----------|-----------|-----------|
| **Déduction IR à l'entrée**        | Oui       | Non       | Oui       |
| **Abondement employeur**           | Non       | Oui       | Oui       |
| **CSG-CRDS sur abondement**        | —         | Oui (9,7 %) | Oui (9,7 %) |
| **Disponibilité**                  | Retraite  | 5 ans     | Retraite  |
| **Sortie capital (v1.1)**          | Oui       | Oui       | Oui       |
| **Fiscalité versement salarié sortie** | IR au TMI | Exonéré | IR au TMI |
| **Fiscalité abondement sortie**    | —         | Exonéré IR | Exonéré IR |
| **Fiscalité gains sortie**         | PFU 30 %  | PS 17,2 % | PFU 30 %  |
| **Coût entreprise (champ dataclass)** | 0      | > 0       | > 0       |
| **economie_fiscale_immediate (champ)** | > 0 (flux × TMI) | 0 | > 0 (flux × TMI) |
| **flux_entrant_brut (champ)**      | flux salarié (borné par plafond) | flux salarié | flux salarié (borné par plafond) |

**Lecture** : PERECO = hybride PERIN + PEE.

- PERECO **hérite de PERIN** sa logique fiscale entrée+sortie
  (déductibilité IR, PFU sur gains, disponibilité retraite).
- PERECO **hérite de PEE** sa logique d'abondement employeur
  (coût entreprise, CSG-CRDS, exonération IR sur abondement à la
  sortie).

**Orthogonalité préservée** : aucune enveloppe ne « contamine » les
autres. Si SP16 (PEE) avait remis en cause l'invariant
« déductibilité IR uniquement pour PERIN », SP17 (PERECO) n'aurait
pas pu prétendre hériter de PERIN sa logique fiscale entrée.

**Implication invariants algébriques** : ces 3 dimensions sont
combinables sans conflit avec le `__post_init__` de
`LigneHorizonReceptacle` (cohérence `effort_reel == flux_entrant_brut
- economie_fiscale_immediate`, `valeur_nette == capital_projete -
fiscalite_sortie`).

---

## §4 — Frontières négatives (hors périmètre v1.1)

Cette section est **aussi importante que les sections positives**.
Elle dit explicitement ce que v1.1 **ne fait pas**.

### 4.1 Enveloppes hors périmètre

Les enveloppes suivantes sont **hors périmètre v1.1** :

- ✗ **Assurance-vie** (AV) — fiscalité successorale, abattement par
  bénéficiaire, mécanique de rachat complexe. Périmètre v1.2+ si
  validé.
- ✗ **Compte-titres ordinaire** (CTO) — fiscalité PFU/option barème,
  PV mobilières. Pas d'horizon défini, pas de capitalisation
  fiscalement encapsulée. Périmètre v1.2+ si validé.
- ✗ **Immobilier locatif** — fiscalité revenus fonciers, dispositifs
  Pinel/Denormandie, crédit immobilier. Trop éloigné du périmètre
  rémunération-dirigeant. Périmètre v2+ si validé.
- ✗ **PEA / PEA-PME** — cohérent v1.2+ mais hors v1.1 pour limiter
  l'extension initiale.
- ✗ **SCPI, sociétés holdings, démembrement, structuration
  patrimoniale** — wealth management, sortie complète du périmètre.

### 4.2 Méthodes de calcul hors périmètre

- ✗ **Optimisation / solveur** — pas de `dimensionner_versement_optimal()`
  qui résoudrait « combien verser pour maximiser X sous contrainte Y ».
  Le module **compare** des enveloppes pour un flux donné, il ne
  **dimensionne pas** le flux lui-même.
- ✗ **Rendement stochastique** — la capitalisation est strictement
  déterministe (taux nominal fixe par hypothèse). Pas de
  Monte-Carlo, pas de distribution de rendements.
- ✗ **Prédiction marché** — aucune référence à un quelconque
  rendement futur réaliste basé sur l'historique. Les rendements
  sont des **hypothèses conventionnelles** documentées.
- ✗ **Calcul actuariel retraite** — pas de calcul de pension, pas
  de carrière de cotisation, pas de modélisation de durée de vie ou
  de table de mortalité.
- ✗ **Modélisation inflation** — les valeurs sont en euros nominaux,
  pas en euros constants. La doctrine documente ce choix
  explicitement.
- ✗ **Modélisation crédit / endettement** — pas de prise en compte
  d'un éventuel financement par crédit.

### 4.3 Outputs hors périmètre

- ✗ **Recommandation d'allocation** — le module ne dit jamais « il
  faut verser X sur Y ». Il restitue des comparaisons factuelles ;
  le cabinet décide.
- ✗ **Score / classement automatique** — pas de notation des
  enveloppes (« PERIN > PEE pour ce profil »). Présentation
  symétrique des comparaisons.
- ✗ **Mention « idéal » / « meilleur » / « optimal »** — vocabulaire
  prescriptif interdit par §6.2 doctrine globale.
- ✗ **Pédagogie marché financier** — pas d'explication sur les
  classes d'actifs, les frais de gestion, le timing d'investissement.

### 4.4 Tentations à refuser

Les sollicitations suivantes sont **prévisibles** et doivent être
**refusées** au profit d'une sous-passe v1.2+ formelle si elles
réémergent :

> « Et si on ajoutait juste l'assurance-vie, c'est presque pareil que
> le PERIN ? »

Refus : l'AV a une logique successorale spécifique (clause
bénéficiaire, abattement 152 500 €) et une fiscalité de rachat
multi-paramètres (durée détention, montant) qui justifient une
modélisation dédiée. Hors périmètre v1.1.

> « Pourquoi pas calculer le versement optimal automatiquement ? »

Refus : v1.1 est un **comparateur**, pas un **dimensionneur**. La
décision de versement appartient au cabinet/client. Un solveur
introduirait des hypothèses d'objectif et de contrainte qui sortent
du périmètre.

> « Le rendement 2 % est conservateur, on pourrait mettre 4 % en
> scénario favorable ? »

Refus partiel : les hypothèses de rendement sont **conventionnelles**
et documentées. On peut proposer une variante (basse/centrale/haute)
si validé par sous-passe formelle, mais on n'introduit pas de
distributions ni de scénarios stochastiques. Toute modification doit
préserver la propriété « directionnel pas prédictif ».

> « Et pour gérer une transmission successorale ? »

Refus : hors périmètre. Wealth management.

---

## §5 — Wordings centralisés

### 5.1 Principe : zéro wording inline

Les wordings d'hypothèses longues (≥ 80 chars, SEUIL_HYPOTHESE_LONGUE)
sont des **composants structurels** du système. Ils apparaissent
dans le PDF audit en encadré séparé et conditionnent directement les
goldens (cf. SP11).

**Règle stricte** : aucun wording d'hypothèse longue n'est écrit
inline dans les modules métier (`strategy/receptacles_*.py`). Tous
sont définis comme constantes nommées dans `strategy/receptacles_wordings.py`.

**Exemple interdit (inline)** :

```python
# strategy/receptacles_perin.py
audit.add(
    code="REC_PERIN_PLAFOND",
    label="Plafond annuel PERIN",
    valeur=plafond,
    unite="EUR",
    hypotheses={
        "regle_plafond": (
            "Le plafond annuel PERIN est égal au plus élevé "  # ← INTERDIT
            "des deux montants suivants : 10% des revenus..."
        )
    }
)
```

**Exemple autorisé (référence centralisée)** :

```python
# strategy/receptacles_wordings.py
WORDING_PERIN_REGLE_PLAFOND = (
    "Le plafond annuel PERIN est égal au plus élevé des deux "
    "montants suivants : 10% des revenus professionnels nets de "
    "l'année N-1 dans la limite de 8 PASS, ou 10% du PASS de "
    "l'année N-1. Référence : art. 154 bis du CGI."
)

# strategy/receptacles_perin.py
from strategy.receptacles_wordings import WORDING_PERIN_REGLE_PLAFOND

audit.add(
    code="REC_PERIN_PLAFOND",
    label="Plafond annuel PERIN",
    valeur=plafond, unite="EUR",
    hypotheses={"regle_plafond": WORDING_PERIN_REGLE_PLAFOND},
)
```

### 5.2 Convention de nommage

Tous les wordings centralisés suivent la convention :

```
WORDING_<ENVELOPPE>_<CONCEPT>
```

Exemples :

```
WORDING_PERIN_REGLE_PLAFOND
WORDING_PERIN_DEDUCTIBILITE_IR_ENTREE
WORDING_PERIN_FISCALITE_SORTIE_RENTE
WORDING_PERIN_FISCALITE_SORTIE_CAPITAL
WORDING_PEE_ABONDEMENT_EMPLOYEUR
WORDING_PEE_DISPONIBILITE_5ANS
WORDING_PEE_EXONERATION_PV_SORTIE
WORDING_PERECO_DEDUCTIBILITE_IR_ENTREE
WORDING_PERECO_SORTIE_CAPITAL_VS_RENTE
WORDING_REC_CONVENTION_RENDEMENT
WORDING_REC_DISCLAIMER_COMPARABILITE
```

Préfixe `WORDING_REC_*` pour les mentions transverses (non
spécifiques à une enveloppe).

### 5.3 Versionnement des wordings

Chaque wording est implicitement versionné par la version v1.1.0 du
module. Modifier un wording **change le golden** du PDF audit
correspondant. Cela doit être un acte conscient :

1. Modification du wording dans `receptacles_wordings.py`
2. Exécution de `python3 test_pdf_audit_render_goldens.py` →
   divergence attendue
3. Mise à jour explicite du golden : `--update` avec confirmation

Pas de modification silencieuse en CI.

### 5.4 Décision D-R3

**D-R3** : tous les wordings d'hypothèses ≥ 80 chars sont définis
exclusivement dans `strategy/receptacles_wordings.py` avec
convention `WORDING_<ENVELOPPE>_<CONCEPT>`. Toute occurrence de
wording inline dans `strategy/receptacles_*.py` est une violation
de doctrine, détectable par scan textuel (cf. SP14).

---

## §6 — Architecture technique

### 6.1 Modules à créer

```
strategy/
├── receptacles_perin.py      ← Module PERIN (SP15)
├── receptacles_pee.py        ← Module PEE (SP16)
├── receptacles_pereco.py     ← Module PERECO (SP17)
├── receptacles_orchestrateur.py  ← Composition (SP18)
└── receptacles_wordings.py   ← Wordings centralisés (SP14+)
```

**Décision D-R4** : 5 modules distincts, un par enveloppe + un pour
l'orchestration + un pour les wordings. Pas de fichier unique
`receptacles.py` qui regrouperait tout (anti-pattern).

### 6.2 Signature publique de chaque module enveloppe

Pattern uniforme, calqué sur les arbitrages existants
(`arbitrage_complet_tns`, etc.) :

```python
def allocation_perin(
    profil: Profil,
    *,
    flux_disponible: float,
    horizons: tuple = (5, 10, 20),
    audit: TraceAudit | None = None,
) -> ResultatAllocationPerin:
    """..."""
```

Signature similaire pour `allocation_pee` et `allocation_pereco`.

**Décision D-R5** : signature standardisée
`(profil, *, flux_disponible, horizons, audit)`. Permet à
l'orchestrateur d'itérer uniformément sur les 3 enveloppes.

### 6.3 Orchestrateur passif

```python
def allocation_receptacles(
    profil: Profil,
    *,
    flux_disponible: float,
    horizons: tuple = (5, 10, 20),
    audit: TraceAudit | None = None,
) -> ResultatAllocationReceptacles:
    """Orchestrateur passif : appelle les 3 modules, compose les traces.

    Aucune logique métier ici. L'orchestrateur :
      1. appelle allocation_perin, allocation_pee, allocation_pereco
      2. attache les 3 sous-traces à audit
      3. construit le ResultatAllocationReceptacles (4 lignes × 3 horizons)
      4. ajoute les disclaimers permanents

    Cf. ARCHITECTURE_RECEPTACLES.md §6.3.
    """
```

**Décision D-R6** : l'orchestrateur ne contient **aucune** des
opérations suivantes :

- Calcul fiscal
- Décision de classement / tri / sélection
- Modification des résultats produits par les modules enveloppe
- Logique conditionnelle métier (« si profil = X alors PERIN
  prioritaire »)

Il **compose** seulement. Toute logique métier dans l'orchestrateur
est une violation de doctrine, à traiter par déplacement vers le
module enveloppe approprié.

### 6.4 Structure de la trace racine produite

```
TraceAudit(regime="Réceptacles")
├── 5 étapes racines (méta : nb enveloppes, disclaimers, horizons)
├── sous-trace "ligne_perin"
│   ├── arbitrage_perin (étapes méta)
│   └── 3 sous-traces (horizon_5ans, horizon_10ans, horizon_20ans)
├── sous-trace "ligne_pee"
│   ├── arbitrage_pee
│   └── 3 sous-traces (horizon_5ans, horizon_10ans, horizon_20ans)
└── sous-trace "ligne_pereco"
    ├── arbitrage_pereco
    └── 3 sous-traces (horizon_5ans, horizon_10ans, horizon_20ans)
```

Profondeur effective : 3 niveaux (sous-trace enveloppe → arbitrage
+ horizons → étapes plates).

Cohérent avec D-R1 (deux moteurs indépendants) : chaque ligne
enveloppe a son propre arbitrage interne, l'orchestrateur ne fait
qu'attacher.

### 6.5 Volumétrie estimée

Estimation préliminaire (à valider en SP14) :

| Élément | Estimation |
|---|---|
| Étapes par enveloppe × horizon | ~25-30 |
| Étapes par enveloppe (3 horizons) | ~80-90 |
| Étapes 3 enveloppes | ~250-300 |
| Étapes méta orchestrateur | ~10-15 |
| **Total estimé** | **~300-350** |

En-dessous des 412 étapes du Comparateur (validé en SP8) et
largement en-dessous des 1000 stressées en SP12. **Conforme N1 §2.2
d'`ARCHITECTURE_RENDERER.md`** (≤ 500 étapes, ≤ 5 profondeur).

---

## §7 — Couche temporelle

### 7.1 Choix de modélisation : étapes par horizon (D-R7)

Suite à l'arbitrage SP13-Q2 = (α) :

**Décision D-R7** : la dimension temporelle est instrumentée par
des **étapes distinctes par horizon**, pas par une évolution de la
grammaire `TraceAudit`. La grammaire `core/audit.py` v1.1.0 reste
strictement inchangée.

**Pattern uniforme** :

```python
audit.add(code="REC_PERIN_CAPITAL_PROJETE_5ANS", ...)
audit.add(code="REC_PERIN_CAPITAL_PROJETE_10ANS", ...)
audit.add(code="REC_PERIN_CAPITAL_PROJETE_20ANS", ...)
```

L'horizon est suffixe du code (`_5ANS`, `_10ANS`, `_20ANS`) — pas un
champ de la grammaire. Le `TraceAudit` reste **mono-période** au
sens technique ; la multi-période émerge de la **composition de
codes**.

### 7.2 Hypothèses de capitalisation

**Hypothèse de référence v1.1** (à figer en SP14) :

- Rendement nominal annuel : **2 %** (conservateur, conventionnel)
- Capitalisation : **annuelle, simple** (pas continue, pas mensuelle)
- Pas d'inflation
- Pas de frais explicites (déjà inclus dans le 2 % conservateur)

**Décision D-R8** : ces hypothèses sont **conventionnelles**, pas
prédictives. Elles permettent une comparaison **directionnelle**
entre enveloppes. Elles ne valent pas projection patrimoniale
sérieuse.

**Wording associé** (`WORDING_REC_CONVENTION_RENDEMENT`) :

> *Les projections présentées reposent sur une hypothèse
> conventionnelle de rendement nominal annuel de 2 %, capitalisé
> annuellement et identique pour toutes les enveloppes comparées.
> Cette convention permet une comparaison directionnelle entre
> enveloppes sur des bases homogènes. Elle n'a pas vocation à
> représenter un rendement attendu ni à constituer une projection
> patrimoniale. La performance réelle dépendra des supports
> sélectionnés, des frais effectifs et du contexte de marché. Le
> cabinet apprécie la pertinence des hypothèses au cas par cas.*

### 7.3 Horizons par défaut

**Décision D-R9** : horizons standards (5, 10, 20) ans.

- 5 ans : proximité (cohérent avec disponibilité PEE)
- 10 ans : moyen terme
- 20 ans : horizon retraite (PERIN/PERECO)

Possibilité de paramétrer d'autres horizons via le paramètre
`horizons` de la signature publique, mais le défaut est ces 3 valeurs.

### 7.4 Ce que le temporel n'est PAS

- **Pas une projection actuarielle** : pas de table de mortalité,
  pas de probabilité de vie, pas de rente viagère calculée
  rigoureusement
- **Pas une simulation dynamique** : les versements sont en année 0,
  pas étalés dans le temps (un seul flux entrant)
- **Pas multi-scénarios** : un seul jeu d'hypothèses par exécution.
  Pas de « scénario bas / central / haut » en parallèle.

---

## §8 — Contrats avec le framework v1.0.1

### 8.1 Contrats à respecter (non négociables)

| Contrat | Origine | Implication v1.1 |
|---|---|---|
| **G1** Rendabilité universelle | ARCHITECTURE_RENDERER.md §2.1 | Toute `TraceAudit` produite par v1.1 doit être rendable sans erreur par `generer_pdf_audit` |
| **G2** Indépendance régime | idem | Aucun paramètre régime-spécifique dans la signature publique. v1.1 ajoute un régime (« Réceptacles »), pas un branchement |
| **G3** Indépendance contexte d'appel | idem | Un module enveloppe rendu seul doit produire un rendu identique à un module enveloppe imbriqué dans l'orchestrateur |
| **G4** Préservation graphe racine | idem (reformulée SP10) | Toutes les étapes racines du graphe v1.1 sont rendues. La dette étapes filles `parent_id != None` reste tracée v1.1+ ; **v1.1 N'IMPLÉMENTE PAS** d'étapes filles dans les modules réceptacles tant que la dette G4 n'est pas traitée |
| **G5** Versionnement séparé | idem | v1.1 ne bumpe ni `AUDIT_PDF_SPEC_VERSION` ni `AUDIT_SPEC_VERSION` |
| **§4.1-4.5** Antipatterns interdits | idem | v1.1 n'introduit aucun `if regime`, aucun hardcoding profondeur, aucun couplage namespace, aucun import strategy/regime dans le renderer, aucune fusion renderers |
| **D1-D15** Décisions architecturales | idem | v1.1 respecte les 15 décisions. Notamment D4 (schéma S2), D5 (SEUIL_HYPOTHESE_LONGUE=80), D7 (plafond TOC 2 niveaux), D8 (calibrage dynamique col_widths) |

### 8.2 Décision spécifique sur G4

**Décision D-R10** : v1.1 ne crée **aucune étape avec `parent_id`
non-null**. Toutes les étapes produites par les modules réceptacles
sont des étapes racines. Cela évite d'aggraver la dette G4 identifiée
en SP10 et garantit que **100 %** des étapes v1.1 seront rendues
dans le PDF audit (vs 60-73 % pour les modules existants).

Cette décision est **strictement défensive** : elle préserve
l'invariant `INV-G4.a` actuel (toutes les racines sont rendues) sans
toucher au mécanisme racines/filles.

Conséquence pratique : les décompositions fines qui auraient été
naturelles avec `parent_id` (ex. décomposition d'un capital projeté
en quote-part versement + quote-part rendement + quote-part
abondement) devront être exprimées comme étapes racines explicites
avec des codes distincts.

### 8.3 Tests à produire (consommation framework)

| Test | Périmètre | Statut v1.1 |
|---|---|---|
| `test_strategy_receptacles.py` | Tests métier des 3 modules + orchestrateur | À créer SP14-SP18 |
| `test_pdf_audit_render_receptacles.py` | Validation framework-compatibilité (les 10 sections du helper commun) | À créer SP19 |
| `golden_pdfs/golden_receptacles.json` | Nouveau golden (6e cas) | À créer SP19 |
| `test_renderer_invariants.py` | **PAS modifié** (les 51 invariants doivent rester verts sur le code v1.0.1) | — |
| `test_renderer_stress.py` | **PAS modifié** (sauf si SP19 ajoute un cas R5 ciblé v1.1) | — |
| Goldens existants (TNS/Assim/Lib/Comp) | **PAS modifiés** (preuve forte que v1.1 ne touche pas au framework) | — |

### 8.4 Critère de validation v1.1.0

v1.1 sera considérée comme livrée quand **les 7 conditions
suivantes sont réunies simultanément** :

1. Les 3 modules enveloppe + orchestrateur sont fonctionnels
2. Le test métier dédié passe (compte d'assertions à définir SP14)
3. Le test PDF audit dédié passe (sur le modèle SP7/SP8, ~80-100 contrôles)
4. Un nouveau golden réceptacles est figé
5. Les 51 invariants `test_renderer_invariants.py` restent verts
6. Les 5 goldens existants (v1.0.0) restent conformes
7. La batterie globale (compare_baseline, MODE_AUDIT, audits
   sémantiques, backward_compat) reste verte

Toute violation d'une des 7 conditions = arrêt et investigation.
Pattern Hardening.

---

## §9 — Décisions architecturales numérotées

Récapitulatif des décisions doctrinales prises en SP13. Chaque
décision a son motif. Toute remise en cause exige une sous-passe
formelle (cadrage, questions, arbitrage, validation, mise à jour du
présent document).

| # | Décision | Motif | Statut |
|---|---|---|---|
| **D-R1** | Deux moteurs indépendants (rémunération + réceptacles), pas de fusion | Découplage, autonomie de chaque logique métier | Figé SP13 |
| **D-R2** | Namespace de codes `REC_<ENVELOPPE>_<CONCEPT>[_<HORIZON>]` | Évite collision avec autres modules, traçabilité visuelle | Figé SP13 |
| **D-R3** | Wordings hypothèses ≥ 80 chars centralisés dans `receptacles_wordings.py`, zéro inline | Stabilité goldens, versionnement, mutualisation | Figé SP13 |
| **D-R4** | 5 modules distincts dans `strategy/` (3 enveloppes + orchestrateur + wordings) | Découplage, testabilité, extension future | Figé SP13 |
| **D-R5** | Signature standardisée `(profil, *, flux_disponible, horizons, audit)` | Itération uniforme dans l'orchestrateur | Figé SP13 |
| **D-R6** | Orchestrateur passif : composition seulement, zéro logique métier | Préservation autonomie modules enveloppe | Figé SP13 |
| **D-R7** | Multi-période par étapes distinctes par horizon, grammaire `TraceAudit` inchangée | Respect du framework, évite bump grammaire | Figé SP13 |
| **D-R8** | Hypothèses de rendement conventionnelles (2 % nominal), pas prédictives | Directionnel pas prédictif, doctrine v1.1 | Figé SP13 |
| **D-R9** | Horizons par défaut (5, 10, 20) ans, paramétrables | Cohérence avec disponibilité PEE et horizon retraite | Figé SP13 |
| **D-R10** | Aucune étape `parent_id != None` en v1.1 (préservation G4) | Évite aggraver dette G4 identifiée SP10 | Figé SP13 |
| **D-R11** | Périmètre v1.1 strict : PERIN + PEE + PERECO, **pas** AV/CTO/immobilier | Évite dérive wealth management, focalisation produit | Figé SP13 |
| **D-R12** | Comparateur, pas dimensionneur. Pas de solveur d'optimisation | Le cabinet décide, le module compare | Figé SP13 |
| **D-R13** | Capitalisation déterministe, pas stochastique | Évite faux semblant prédictif, simplicité | Figé SP13 |
| **D-R14** | Euros nominaux, pas constants. Pas d'inflation | Simplicité, comparabilité | Figé SP13 |

---

## §10 — Extension future

### 10.1 Critères de bascule v1.2

v1.2 (extension réceptacles) serait justifiée si :

- Retours cabinet structurés (≥ 3 cabinets différents) demandent
  explicitement l'ajout d'une enveloppe précise (AV, PEA, CTO)
- Le périmètre v1.1 est stable depuis ≥ 6 mois en production
- Aucune dette technique majeure n'est en cours sur réceptacles v1.1
- La grammaire `TraceAudit` n'a pas besoin d'évoluer (sinon → v1.x
  framework)

v1.2 ajoute des enveloppes ; elle ne modifie pas la doctrine v1.1.

### 10.2 Critères de bascule v2 (refonte)

v2 serait justifiée si :

- Une refonte de la grammaire `TraceAudit` est nécessaire (ex.
  séries temporelles natives)
- Le passage à un moteur stochastique devient incontournable
- L'intégration de wealth management complet (AV+CTO+immobilier+
  démembrement) est validée stratégiquement

v2 est un **bump majeur du framework**, pas une extension métier. Il
suit la discipline Hardening (équivalent SP9-SP12 reproductible).

### 10.3 Tentations à refuser jusqu'à v1.2 minimum

Les sollicitations suivantes doivent être refusées :

- Ajouter une 4ème enveloppe en v1.1 (même PEA-PME jugée « simple »)
- Introduire un mécanisme de scénarios optimiste/central/pessimiste
- Permettre des horizons non-standards (ex. 7 ans, 15 ans) hors
  paramètre explicite
- Ajouter une recommandation cabinet automatique (« basé sur votre
  profil, PERIN est le plus efficace »)

---

## §11 — Synthèse exécutive

La v1.1.0 est une **extension métier** du framework v1.0.1, focalisée
sur la **comparaison d'enveloppes sociales et retraite** liées à la
rémunération du dirigeant : PERIN, PEE, PERECO.

Trois principes structurants :

1. **Le framework reste figé.** Aucun touchier au renderer, à la
   grammaire `TraceAudit`, aux invariants, aux goldens existants. Les
   tests SP1-SP12 doivent rester verts à 100 % à la fin de v1.1.
2. **La doctrine est positive ET négative.** Le périmètre couvert
   (3 enveloppes, comparaison multi-horizon) est aussi important que
   ce qui est exclu (AV/CTO/immobilier, solveur, stochastique,
   prédiction, actuariat). Les frontières négatives sont **explicites**
   dans §4.
3. **L'extension consomme le framework.** Chaque module produit une
   `TraceAudit` valide, qui passe par `generer_pdf_audit` sans
   adaptation. Le module réceptacles est conceptuellement un 5ème
   régime au sens du framework.

Les 14 décisions D-R1 à D-R14 verrouillent les choix structurants.
Toute remise en cause exige une sous-passe formelle.

La phase v1.1.0 se déroulera en 7 sous-passes (SP13 → SP19), même
discipline que SP1-SP12 : cadrage → questions → arbitrage →
exécution → validation, sans saut.

À l'arrivée :

- 4 nouveaux modules `strategy/receptacles_*.py`
- 1 nouveau régime audit-renderable (5ème, après TNS/Assim/Lib/Comp)
- ~300-350 étapes produites en routine
- 1 nouveau golden JSON
- 1 nouveau test PDF audit dédié
- 1 nouveau test métier
- **0 modification du framework v1.0.1**

Le succès se mesurera à l'absence totale de régression sur le
périmètre figé (446 contrôles framework + 5 goldens + 51 invariants),
et à l'apport métier nouveau (~80-100 nouveaux contrôles
réceptacles).

---

*Document SP13, premier livrable v1.1.0. Doctrine métier + technique
+ frontières négatives. Conformité ARCHITECTURE_RENDERER.md §6
(extension future). Cf. KNOWN_LIMITATIONS.md pour le récap des
sous-passes SP1-SP12 (framework v1.0.0/v1.0.1).*
