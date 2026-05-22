# ARCHITECTURE_RENDERER.md

**Doctrine technique du renderer PDF audit-ready (`ui/pdf_audit_export.py`).**

Document de référence pour comprendre, étendre et préserver
l'architecture du renderer. Statut : **vivant** — toute modification
structurelle du renderer doit s'accompagner d'une mise à jour
correspondante de ce document.

| Métadonnée | Valeur |
|---|---|
| Version renderer | `AUDIT_PDF_SPEC_VERSION = "1.0.0"` |
| Périmètre couvert | TNS, Assimilé, Libéral (SELARL/SELAS), Comparateur multi-régimes |
| Sous-passes de construction | SP1 → SP8 (cf. KNOWN_LIMITATIONS.md) |
| Tests cumulés | 395 contrôles (`test_pdf_audit_render_{tns,assimile,liberal,comparateur_regimes}.py`) |
| Hash baseline préservé | `8863991f27f67847` |

---

## §1 — Philosophie

### 1.1 Le renderer comme produit documentaire séparé

Le dépôt possède **deux produits PDF distincts**, et leur séparation
est volontaire :

| Produit | Module | Destinataire | Rôle |
|---|---|---|---|
| **PDF synthèse** | `ui/pdf_export.py` | Client final | Restitution lisible des résultats économiques (radar, projection 5 ans, comparaisons stratégies, mentions cabinet finales). |
| **PDF audit** | `ui/pdf_audit_export.py` | Auditeur / EC / contrôle qualité | Restitution structurée du **graphe de calcul exécuté** par le moteur, étape par étape, avec doctrine_refs et hypothèses. |

Ces deux produits partagent la **même charte graphique** (couleurs,
en-tête bandeau bleu, footer 3 lignes, polices Helvetica/Courier)
mais leur **contenu et leur logique de génération sont strictement
indépendants**.

**Choix architectural fondateur (SP1-Q1, option B validée)** : deux
renderers indépendants, pas de hiérarchie ni de réutilisation
mutuelle. Le PDF synthèse peut évoluer sans risque de casser le PDF
audit, et réciproquement. Le seul couplage assumé est la charte
graphique partagée (constantes de couleur et de police importées
depuis `ui/pdf_export.py`).

### 1.2 Pourquoi la neutralité structurelle est l'invariant central

Le renderer audit a un seul vrai contrat : **rendre n'importe quelle
`TraceAudit` valide de manière homogène et prédictible.**

C'est plus fort qu'un contrat de validité (« ne pas planter ») : c'est
un contrat de **prédictibilité**. Une trace produite par
`arbitrage_complet_tns()` doit être rendue selon les mêmes principes
qu'une trace produite par `calcul_comparateur_regimes()`, même si la
seconde est 6× plus grosse et 4× plus profonde. La forme du PDF
généré ne doit dépendre que de la **structure** de la trace (étapes,
sous-traces, doctrine_refs, hypotheses, notes, profondeur), pas de
son **contenu sémantique** (régime, namespace de codes, libellés).

Cette propriété a deux conséquences pratiques :

1. **Le renderer ne contient aucun branchement par régime.** Pas de
   `if trace.regime == "TNS":`. Pas de `if "STRAT_LIB" in code:`.
   Pas de logique de classification des sous-traces selon leur nom.
   Vérifié empiriquement : `grep -n 'if.*regime' ui/pdf_audit_export.py`
   ne retourne aucun branchement métier.
2. **Le contexte d'appel n'influence pas le rendu d'un module.** Un
   `module_tns` rendu en profondeur 2 (mode TNS isolé) produit les
   mêmes lignes de tableau qu'un `module_tns` rendu en profondeur 5
   (sous `comparateur_regimes → ligne_tns → arbitrage_tns →
   strategie_T1 → module_tns`). Vérifié par
   `test_pdf_audit_render_comparateur_regimes.py` section « Codes
   namespace tous régimes ».

**Pourquoi c'est stratégique.** Tant que cette propriété tient :
- Tout nouveau module métier instrumenté MODE_AUDIT devient
  automatiquement « audit-renderable » sans modification du renderer.
- Toute évolution de la grammaire `TraceAudit` est absorbée
  uniformément (pas de cas particuliers à propager dans le renderer).
- Les tests de non-régression sont **structurels**, pas régime-par-régime.
- Le renderer reste maintenable par une personne qui ne connaît pas
  le métier sous-jacent (fiscalité, doctrine FR 2026).

Si cette propriété se brise, le renderer redevient un produit
spécialisé — chaque nouveau régime exige sa branche dédiée, le code
gonfle, la testabilité s'effondre. **La neutralité structurelle est
donc la propriété la plus précieuse à défendre dans toute évolution
future.**

### 1.3 Pourquoi le schéma S2 a été préféré à S3

Le **schéma S2** est la convention de pagination retenue : *une page
par sous-trace de niveau 1, sous-traces de niveau ≥ 2 enchaînées en
continu sans saut de page*. Concrètement, pour la trace TNS pilote
qui a 4 sous-traces de niveau 1 (`strategie_T1` à `strategie_T4`),
chacune contenant 1 sous-trace `module_tns` :

```
Page 1     → Couverture
Page 2     → Sommaire
Page 3     → Étapes racine
Page 4-5   → strategie_T1 + module_tns enchaîné
Page 6-7   → strategie_T2 + module_tns enchaîné
Page 8-10  → strategie_T3 + module_tns enchaîné
Page 11-12 → strategie_T4 + module_tns enchaîné
Page 13    → Disclaimers
```

Le **schéma S3 alternatif** aurait été : annexes paginées dédiées,
avec contenu principal compact en début et détails séparés. Schéma
plus complexe à mettre en œuvre, et son intérêt apparaît surtout
quand le PDF dépasse plusieurs dizaines de pages.

**Pourquoi S2 a été retenu :**

- **Lisibilité cabinet** : « une stratégie = une section navigable »
  est un mental model immédiat. L'auditeur sait que pour comprendre
  `strategie_T1`, il regarde une seule section continue.
- **Volumétrie acceptable** : 13 pages pour TNS, 14 pour Assimilé,
  14-15 pour Libéral, 33 pour comparateur_regimes. Tous dans la
  fourchette cible cabinet (25-40 pages haute densité), donc S2 tient.
- **Conformité multiBuild** : reportlab gère naturellement les
  PageBreak entre sections de niveau 1. S3 aurait demandé un mécanisme
  de re-pagination plus complexe.
- **Simplicité d'extension** : SP7 et SP8 ont confirmé que S2 absorbe
  profondeur 3 (Libéral L4) et profondeur 5 (comparateur_regimes)
  sans modification.

**Conditions de bascule vers S3 (futures)** : si une trace dépasse
~60 pages, ou si une sous-trace seule génère plus de 15 pages
internes, S2 perd sa lisibilité. Dans ce cas, S3 redeviendrait à
considérer. Sur le périmètre v1.0.0, ce seuil n'est jamais approché.

### 1.4 Conséquence : le pilote n'est pas le produit

SP1-SP6 ont construit et validé le pilote TNS comme **référence**.
Mais ce pilote n'est pas le produit final — il est la **preuve par
l'exemple** qu'une grammaire `TraceAudit` est rendable. Le vrai
produit livré v1.0.0 est :

> Un renderer `generer_pdf_audit(trace, ...)` qui transforme toute
> `TraceAudit` conforme à la spec `core/audit.py` v1.1.0+ en un PDF
> audit-ready cabinet, indépendamment du domaine métier sous-jacent.

C'est cette propriété — *renderer générique validé* — qui constitue
la base de plateforme. Tout ce qui suit (PERIN, réceptacles,
synthèse décisionnelle) bénéficie automatiquement de cette base, tant
que les modules métier respectent la grammaire `TraceAudit`.

---

## §2 — Le contrat de neutralité

### 2.1 Ce que le renderer garantit

**G1 — Rendabilité universelle.** Toute `TraceAudit` valide au sens
de `core/audit.py` spec ≥ 1.1.0 produit un PDF (`bytes` commençant
par `%PDF-`, ≥ 3 ko, terminé par `%%EOF`), sans exception ni crash.

> *Validé par* : `section_pdf_valide` du helper commun. 4 cas
> empiriquement couverts (TNS 156 étapes, Assimilé 70, Libéral 122-136,
> comparateur 412).

**G2 — Indépendance du régime.** Aucune modification du renderer
n'est requise pour ajouter un nouveau régime à la condition que la
trace soit conforme à la grammaire. La signature publique
`generer_pdf_audit(trace, ...)` est stable depuis SP1 et **ne contient
aucun paramètre régime-spécifique**.

> *Validé par* : SP7 et SP8 ont ajouté 3 régimes (Assimilé, Libéral,
> Comparateur) sans modifier la signature publique. Seul ajout en SP7 :
> calibrage dynamique des col_widths (paramétrage neutre).

**G3 — Indépendance du contexte d'appel.** Un module rendu
isolément et le même module rendu imbriqué profondément produisent
des lignes de tableau **identiques**. Le rendu d'une étape est une
fonction pure de l'`EtapeAudit` et des styles, pas du chemin
d'attachement.

> *Validé par* : `test_pdf_audit_render_comparateur_regimes.py`
> section « Codes namespace tous régimes » vérifie explicitement la
> présence des préfixes `STRAT_TNS_*`, `STRAT_LIB_*`, `STRAT_ASSIM_*`,
> `SAL_*`, `TNS_*`, `LIB_BNC_*` dans le PDF comparateur (où ces codes
> sont à profondeur 4-5), preuve que le rendu n'est pas dégradé par
> l'imbrication.

**G4 — Préservation du graphe racine + exclusion doctrinale des étapes filles.**

Toutes les **étapes racines** (au sens `EtapeAudit.parent_id is None`)
de chaque trace et sous-trace sont restituées dans le PDF, avec leurs
doctrine_refs, hypothèses et notes. Aucune élision silencieuse à ce
niveau. Toutes les sous-traces attachées sont rendues récursivement.

> *Validé par* : `_compter_kpis_trace` opère par récursion totale sur
> les étapes (KPIs panel couverture) ; `INV-G4.a` du test
> `test_renderer_invariants.py` vérifie que chaque code d'étape racine
> est présent dans le texte du PDF.

**Position doctrinale v1.1.1 sur les étapes filles (clôture définitive
de la dette G4-filles découverte en SP10) :**

Les étapes `parent_id != None` sont **considérées comme des artefacts
internes de calcul et non comme des unités d'audit cabinet**. Cette
position s'appuie sur trois constats convergents :

1. **Convergence du dépôt** : SP13 / D-R10 a explicitement décidé que
   les modules métier réceptacles ne produiraient **aucune étape
   `parent_id != None`**. Le dépôt converge naturellement vers
   « pas d'étapes filles ».
2. **Cohérence d'audit** : l'agrégat parent est toujours rendu, et il
   suffit à un auditeur cabinet pour valider le calcul. La
   décomposition fiscale fine (ex. `TNS_IR_FOYER_AGGREGE` →
   `TNS_IR_FOYER_BRUT` + `TNS_CEHR` + `TNS_CDHR`...) reste accessible
   dans le code Python et reproductible.
3. **Risque framework** : implémenter le rendu hiérarchique nécessiterait
   de toucher `_table_etapes_plates` et invaliderait les 6 goldens PDF
   v1.0.1 + v1.1.0. Le coût excède largement le bénéfice cabinet.

**Conséquences techniques :**

- Le renderer **ne descend pas** dans `trace.enfants(code)` — ce n'est
  pas un bug mais un **choix d'architecture** assumé.
- Pour les modules v1.0.0 (`strategy/tns.py`, `strategy/assimile.py`,
  `strategy/liberal.py`, `strategy/comparateur*.py`) : 27 à 40 % des
  étapes sont des étapes filles non rendues. Ce comportement est
  **stable** et **n'est pas à corriger**.
- Pour les modules v1.1.0 (`strategy/receptacles_*.py`) : aucune
  étape fille n'est produite (D-R10), donc la question ne se pose
  même pas.
- L'invariant `INV-G4.a` valide la présence des étapes racines.
  L'invariant temporaire `INV-G4.b` (qui vérifiait que les étapes
  filles étaient effectivement absentes) **est retiré en v1.1.1** :
  c'était un placeholder destiné à tomber au moment du traitement
  de la dette ; la dette étant désormais close par décision
  doctrinale, l'invariant n'a plus de raison d'être.

**Engagement de stabilité v1.x :** cette position est **définitive
pour toute la branche v1.x**. Si dans un avenir lointain un cabinet
réclame la décomposition fiscale fine dans le PDF, ce sera l'objet
d'une **bascule majeure** (v2.x) — pas d'un patch.

**G5 — Versionnement séparé.** Le renderer évolue indépendamment
de la grammaire trace. La constante `AUDIT_PDF_SPEC_VERSION = "1.0.0"`
(version du renderer) est **distincte** de la constante
`AUDIT_SPEC_VERSION = "1.1.0"` (version du graphe d'audit dans
`core/audit.py`). Une montée mineure de l'un n'impose pas la montée
de l'autre.

### 2.2 Ce que le renderer ne garantit pas

**N1 — Lisibilité au-delà des seuils empiriques.** Le pilotage des
choix de mise en page (densité, plafond TOC à 2 niveaux, schéma S2)
a été calibré pour des traces de :
- **≤ 500 étapes** environ (412 testé)
- **≤ 5 niveaux de profondeur** (5 testé)
- **≤ 40 pages PDF** (33 testé)
- **≤ ~30 entrées de sommaire** (33 testé, tient sur 1 page après SP8)

Au-delà, le rendu reste **valide** (cf. G1) mais la **lisibilité
cabinet** n'est plus garantie. Voir §3.5 sur le seuil de bascule S3.

**N2 — Performance non bornée.** Aucune contrainte de temps de
génération n'est garantie. Le temps observé sur le périmètre v1.0.0
est de l'ordre de quelques secondes pour la trace la plus volumineuse
(comparateur_regimes, 412 étapes). Pour des traces beaucoup plus
grosses, la complexité reste linéaire en nombre d'étapes (`O(n)` pour
le calibrage dynamique et la construction du flow reportlab) plus
sub-linéaire pour le `multiBuild` (deux passes).

**N3 — Wording cosmétique sans garantie.** Le wording produit par le
renderer (titres de section, étiquettes de panel KPI, bandeau intro)
est **utilitaire et factuel**, pas adapté finement à chaque contexte.
Exemples assumés (cf. SP7-Q2 et SP8-Q2 = statu quo cosmétique) :

- Titres de section longs qui wrappent sur 2 lignes en cas de régime
  composite (`« Sous-trace « ligne_liberal » — Régime Comparateur
  régimes — ligne_liberal »`).
- Wording « Détail » uniforme pour toutes les sous-traces ≥ N1,
  indépendamment de leur profondeur réelle dans le graphe.
- Parenthèses imbriquées dans certains titres
  (`(régime Salarié (appel depuis comparateur_regimes, référence))`).

Ces imperfections sont **tolérables tant qu'elles ne nuisent pas à
la lisibilité audit**. Tout raffinement cosmétique régime-spécifique
serait une violation de G2 (indépendance du régime).

**N4 — Stabilité octet-par-octet du PDF.** Le PDF généré n'est
**pas reproductible bit-à-bit** entre deux exécutions (ReportLab
inclut un timestamp interne, la date d'édition s'affiche
dynamiquement). La stabilité est garantie au niveau **structurel**
(mêmes pages, mêmes contenus, mêmes signets), pas au niveau **binaire**.

> *Implication SP11 Golden PDFs* : les snapshots de référence ne
> pourront pas hasher le PDF brut. Ils devront figer des **invariants
> extraits** (texte normalisé, structure de signets, KPIs, comptes
> d'éléments). Cf. SP11 pour la mécanique.

**N5 — Pas de configuration métier.** Le renderer ne propose aucun
paramètre permettant de masquer des sous-traces, de filtrer des
étapes par doctrine_ref, de réordonner les sections, ou de produire
un sous-ensemble du graphe. La trace fournie est rendue intégralement
ou pas du tout. C'est un choix volontaire — toute logique de filtrage
appartient au module métier (qui peut construire une trace partielle
si besoin), pas au renderer.

---

## §3 — Patterns autorisés

### 3.1 Itération sur la structure (pas sur les noms)

Le renderer itère sur des **collections génériques** exposées par
`TraceAudit` :

```python
# ✓ Pattern autorisé : itération sur structure
for etape in trace.etapes:
    ...
for nom in trace.noms_sous_traces():
    sub = trace.get_sous_trace(nom)
    ...
for ref in etape.doctrine_refs:
    ...
for cle, val in etape.hypotheses.items():
    ...
```

Le renderer **ne fait jamais** de filtrage par nom symbolique :

```python
# ✗ Pattern interdit : sélection par nom
if nom == "strategie_T1":
    ...
if etape.code.startswith("STRAT_TNS_"):
    ...
```

Cas exemplaire : `_section_sous_traces()` itère uniformément sur
`trace.noms_sous_traces()`, peu importe que les noms soient
`strategie_T1..T4` (TNS), `strategie_A..D + tx_ir_moy` (Assimilé),
`strategie_L1..L4` (Libéral) ou `ligne_assimile / ligne_tns /
ligne_liberal / ligne_salarie` (Comparateur).

### 3.2 Paramétrage neutre (cas exemplaire : `_calibrer_col_widths`)

Quand une caractéristique de rendu doit s'adapter au contenu, la
solution est un **paramétrage neutre** : mesurer le contenu effectif
et adapter selon des bornes min/max indépendantes du domaine.

Cas modèle, le calibrage dynamique introduit en SP7 pour absorber le
code 41 chars du comparateur :

```python
# ✓ Pattern autorisé : mesure stringWidth + bornes neutres
def _calibrer_col_widths(etapes: list) -> list:
    largeur_code = max(
        _mesurer_largeur_chaine_mm(e.code, "Courier", 7)
        for e in etapes
    )
    # ... idem valeur, unité
    code_mm = _borner(
        largeur_code + PADDING_CELLULAIRE_MM + MARGE_SECURITE_MM,
        BORNES_CODE_MM,  # (45, 75) — bornes neutres globales
    )
    # ...
```

Les bornes `BORNES_CODE_MM = (45, 75)`, `BORNES_VALEUR_MM = (30, 60)`,
etc. sont des **constantes au niveau du module**, partagées par toutes
les traces. Elles ne sont jamais ajustées par régime.

Antipattern correspondant :

```python
# ✗ Pattern interdit : seuils régime-spécifiques
if trace.regime == "Comparateur Régimes":
    BORNES_CODE_MM = (50, 80)  # plus large pour les codes COMP_REG_*
```

### 3.3 Récursion uniforme (`_rendre_sous_trace_recursif`)

Toute traversée de sous-trace utilise une **récursion à profondeur
arbitraire**, jamais une boucle dépliée par niveau. Le helper
`_rendre_sous_trace_recursif` accepte un paramètre `chemin: list`
qui cumule les noms d'attachement traversés, et un paramètre
`niveau_toc: int` qui plafonne l'inscription au sommaire à 2 niveaux
(décision SP3 préservée, cf. §5).

```python
# ✓ Pattern autorisé : récursion uniforme
def _rendre_sous_trace_recursif(flow, styles, trace, nom_attachement,
                                 *, chemin: list, niveau_toc: int) -> None:
    # ... rendu de cette sous-trace
    for nom_enfant in trace.noms_sous_traces():
        sous_sous = trace.get_sous_trace(nom_enfant)
        _rendre_sous_trace_recursif(
            flow, styles, sous_sous, nom_enfant,
            chemin=chemin + [nom_enfant],
            niveau_toc=min(niveau_toc + 1, 1),  # plafond TOC à 2 niveaux
        )
```

La profondeur effective traversée n'est pas codée en dur. Validation
SP8 : la même récursion absorbe les profondeurs 1 (Assimilé), 3
(Libéral L4) et 5 (comparateur_regimes).

### 3.4 Helper commun de test (`test_pdf_audit_render_common.py`)

Le helper de test est **le contrat de neutralité formalisé en
assertions exécutables**. Ses 10 sections d'assertions sont
appelables identiquement par les 4 tests régimes
(`test_pdf_audit_render_tns.py`, `_assimile.py`, `_liberal.py`,
`_comparateur_regimes.py`) sans la moindre adaptation par régime.

```python
# ✓ Pattern autorisé : assertions structurelles dans le helper
def section_signets_hierarchises(runner, cas):
    # itère sur trace.noms_sous_traces() — neutre
    for nom in cas.trace.noms_sous_traces():
        runner.check(
            f"Signet présent pour sous-trace '{nom}'",
            any(nom in t for t in titres),
        )

# ✓ Pattern autorisé : assertions spécifiques DANS le test régime,
# pas dans le helper
# (test_pdf_audit_render_assimile.py)
runner.check(
    "Sous-trace 'tx_ir_moy' présente (helper de calcul intercalé)",
    "tx_ir_moy" in noms_n1,
)
```

Règle : **toute assertion qui mentionne un nom symbolique de
sous-trace, un code namespace ou une propriété régime-spécifique
appartient au test du régime concerné, pas au helper commun.**

### 3.5 Disclaimers et invariants documentaires

Les disclaimers v1.0.1 (`DISCLAIMER_AVERTISSEMENT_FINAL`,
`DISCLAIMER_PRIMAUTE_CABINET`) sont importés depuis `ui/pdf_export.py`
(source unique de vérité). Le renderer audit les inclut en fin de
PDF sans modification.

Le bandeau d'introduction du sommaire (`BANDEAU_INTRO_SOMMAIRE`) est
une constante du module renderer audit (texte pédagogique distinct
des disclaimers juridiques). Modifiable seulement par décision
explicite (changement SP5-Q3 validé).

---

## §4 — Patterns interdits

### 4.1 Aucun `if regime == "..."`

L'interdiction est **absolue** dans `ui/pdf_audit_export.py`. Aucun
branchement de logique de rendu basé sur la valeur de `trace.regime`,
de `etape.code` ou d'un nom d'attachement.

```python
# ✗ INTERDIT — viole G2 (indépendance du régime)
if trace.regime == "TNS":
    largeur_code = 60*mm
elif trace.regime == "Libéral":
    largeur_code = 65*mm

# ✗ INTERDIT — viole G3 (indépendance du contexte d'appel)
if "comparateur" in nom_attachement:
    titre = "Comparaison"  # wording dédié
else:
    titre = "Sous-trace"
```

Justification : tout branchement par régime serait une **dette
structurelle** qui transformerait le renderer en collection de cas
particuliers et casserait la garantie « tout nouveau module métier
devient automatiquement audit-renderable ».

### 4.2 Aucun hardcoding de profondeur

La récursion sur les sous-traces ne doit **jamais** dépendre de la
profondeur courante pour décider de son comportement, à l'exception
unique du **plafond du sommaire** (`niveau_toc = min(niveau_toc + 1, 1)`)
qui est une décision de présentation, pas une logique métier.

```python
# ✗ INTERDIT — hardcoding de profondeur
if niveau == 0:
    titre = "Sous-trace"
elif niveau == 1:
    titre = "Détail"
elif niveau == 2:
    titre = "Sous-détail"  # NON

# ✓ AUTORISÉ — plafond cosmétique uniforme
titre = "Sous-trace" if niveau == 0 else "Détail"
```

Justification : la profondeur effective d'une trace est une propriété
émergente du métier (TNS = 2, Libéral = 3, comparateur = 5). Ajouter
des wording dédiés par niveau revient à présumer le métier, ce qui
casse G3.

### 4.3 Aucun couplage à un namespace de code

Les codes d'étapes (`STRAT_TNS_*`, `TNS_*`, `LIB_BNC_*`, `COMP_REG_*`,
etc.) sont des **identifiants symboliques opaques** pour le renderer.
Le renderer les affiche tels quels et calibre les colonnes en
fonction de leur longueur littérale, mais n'extrait jamais de sens
de leur préfixe.

```python
# ✗ INTERDIT — extraction sémantique de namespace
if etape.code.startswith("COMP_REG_"):
    # rendu particulier pour les étapes du comparateur
    ...

# ✗ INTERDIT — classification par regex sur les codes
if re.match(r"STRAT_\w+_T\d+", etape.code):
    # rendu particulier pour les étapes de stratégie numérotée
    ...
```

Cas exemplaire de respect : `_table_etapes_plates()` rend tous les
codes dans la même police (Courier 7pt), même cellule, peu importe
leur préfixe.

### 4.4 Aucune logique métier dans le renderer

Le renderer ne contient **aucune** des éléments suivants :
- Calcul fiscal, simulation, projection
- Connaissance des règles doctrinales (à part la résolution générique
  `resoudre_doctrine_ref(ref)` qui est une lookup neutre)
- Distinction conceptuelle entre « stratégie », « module utilitaire »,
  « ligne régime » — pour le renderer, tout est une `TraceAudit`
- Tri, filtrage ou réorganisation des étapes selon des critères
  métier

Si une logique métier semble nécessaire pour rendre correctement un
nouveau cas, c'est qu'elle doit être **ajoutée à la trace par le
module métier**, pas introduite dans le renderer. Le renderer
restitue ; il n'interprète pas.

### 4.5 Aucune fusion entre PDF synthèse et PDF audit

Les deux renderers `generer_pdf_synthese()` et `generer_pdf_audit()`
restent indépendants. Pas de classe parente partagée, pas de
factorisation prématurée, pas de paramètre `mode="synthese|audit"`
dans une fonction commune.

Le seul couplage assumé est le **partage de la charte graphique**
(constantes de couleur, polices, disclaimers) importées depuis
`ui/pdf_export.py`. Toute extension de ce couplage doit être
explicitement décidée et tracée (cas typique : si une nouvelle
constante de couleur est introduite dans le renderer audit qui
devrait aussi servir au renderer synthèse, elle est définie dans
`ui/pdf_export.py` puis importée).

---

## §5 — Décisions architecturales numérotées

Récapitulatif des décisions structurelles prises lors de la
construction SP1→SP8. Chaque décision a son ancrage dans une
sous-passe identifiée, son motif et son statut.

| # | Décision | Sous-passe | Motif | Statut |
|---|---|---|---|---|
| **D1** | Deux renderers indépendants (option B), pas de hiérarchie ni de fusion | SP1-Q1 | Découplage : le PDF synthèse peut évoluer sans risque pour le PDF audit. Pas de classe parente prématurée. | Figé. |
| **D2** | ReportLab natif, pas de WeasyPrint | SP1-Q2 | Continuité avec `ui/pdf_export.py`, pas de dépendance Pango+Cairo. Aucun bénéfice attendu de WeasyPrint sur traces hiérarchiques. | Figé. |
| **D3** | Pilote v1 = `arbitrage_complet_tns` (trace racine + 4 stratégies + 4 module_tns) | SP1-Q3 | Trace réelle, instrumentée, taille moyenne (156 étapes), profondeur 2. Bon laboratoire avant extension. | Réalisé SP6. |
| **D4** | Schéma S2 (page par sous-trace N1, N2+ enchaîné) | SP1-Q4 | Cf. §1.3. Lisibilité cabinet, conformité reportlab, simplicité d'extension. | Figé. Validation SP7 (profondeur 3) et SP8 (profondeur 5). |
| **D5** | Hypothèses ≥ 80 chars en encadré séparé, < 80 chars inline | SP4-Q1 | Calibré sur trace TNS pilote (3 hypothèses dépassaient, toutes des wordings métier figés §6.4 doctrine). Universel sur tous régimes (Assimilé 0, Libéral 11, Comparateur 21). | Figé. `SEUIL_HYPOTHESE_LONGUE = 80`. |
| **D6** | Override doctrine : mention texte explicite « override local : appliquée X vs doctrine Y », sans icône | SP4-Q2 | Lisibilité cabinet, évite risque glyph manquant (`⚠`). L'icône reste à la console pour debug. | Figé. |
| **D7** | Plafond TOC à 2 niveaux (`min(niveau_toc + 1, 1)`) | SP3-Q3, SP7-Q3 | Au-delà, sommaire illisible (cas comparateur profondeur 5 : sommaire à 5 niveaux serait inutilisable). Signets PDF également plafonnés à N1. | Figé. |
| **D8** | Calibrage dynamique des col_widths (stringWidth + bornes neutres) | SP7-Q1 | Code 39 chars (Libéral L4) wrappait avec largeurs figées. Calibrage neutre absorbe désormais jusqu'à 41 chars (comparateur). | Figé. Cf. §3.2. |
| **D9** | Statu quo wording « Détail » uniforme | SP7-Q2, SP8-Q2 | Tolérance cosmétique assumée. Toute distinction par profondeur violerait §4.2. | Figé. |
| **D10** | Panel KPI couverture 2×2 sobre, 4 indicateurs (étapes, sous-traces, doctrine_refs distinctes, hypothèses) | SP5-Q2 | Style cabinet EY/KPMG-like. Pas d'icône, pas d'effet SaaS. Indicateurs **structurels** (pas métier comme « net dirigeant »). | Figé. |
| **D11** | Bandeau d'introduction sommaire (`BANDEAU_INTRO_SOMMAIRE`) distinct des disclaimers juridiques | SP5-Q3 | Texte pédagogique/méthodologique, non juridique. Position : page sommaire, avant TOC. Distinct des disclaimers v1.0.1 qui restent en clôture. | Figé. |
| **D12** | `spaceBefore N0` du TOC réduit de 4 → 2 pt | SP8-Q1 | Sommaire comparateur (33 entrées) débordait sur page 3 quasi vide. Modification neutre, aucune dégradation visible sur TNS/Assimilé/Libéral. | Figé. |
| **D13** | Schéma S2 maintenu, pas de bascule S3 en v1.0.0 | SP8-Q3 | Comparateur tient en 33 pages avec sommaire 1 page. S3 reste option v1.1+. Cf. seuils §2.2 N1. | Figé pour v1.0.0. |
| **D14** | Tests : 1 pilote figé (TNS) + 3 tests dédiés (Assimilé, Libéral, Comparateur) + 1 helper commun | SP7-Q4, SP8-Q4 | Helper formalise la neutralité. Tests dédiés portent les propriétés régime-spécifiques. Pilote TNS reste référence non modifiable. | Figé. |
| **D15** | Versionnement séparé `AUDIT_PDF_SPEC_VERSION` (renderer) et `AUDIT_SPEC_VERSION` (graphe) | SP1 | Évolution indépendante. Une montée mineure de l'un n'impose pas la montée de l'autre. | Figé. |

---

## §6 — Extension future

### 6.1 Comment ajouter un nouveau régime

Procédure complète, validée empiriquement par SP7 (Assimilé, Libéral)
et SP8 (Comparateur).

**Côté module métier** :
1. Le module doit produire une `TraceAudit` conforme à
   `core/audit.py` spec ≥ 1.1.0 : étapes avec `code` /
   `label` / `valeur` / `unite` / `doctrine_refs` / `hypotheses` /
   `notes`, sous-traces attachées via `attacher_sous_trace()`.
2. Aucune contrainte sur le namespace des codes, ni sur la
   profondeur des sous-traces (≤ 5 testé, robuste au-delà sous
   réserve N1 §2.2).
3. Hypothèses ≥ 80 chars sont automatiquement rendues en encadré
   séparé. Pas d'action requise côté module.

**Côté tests** :
1. Créer `test_pdf_audit_render_<regime>.py` sur le modèle de
   `test_pdf_audit_render_assimile.py`.
2. Importer le helper commun :
   ```python
   from test_pdf_audit_render_common import (
       AssertionRunner, faire_cas_test,
       section_pdf_valide, section_couverture,
       section_kpis_couverture, section_bandeau_intro_sommaire,
       section_sommaire_pagine, section_signets_hierarchises,
       section_no_declaratif, section_14_patterns_non_prescriptifs,
       section_neutralite_structurelle, section_calibrage_dynamique,
   )
   ```
3. Appeler les 10 sections communes (contrat de neutralité).
4. Ajouter une section « Spécifique <Régime> » avec les propriétés
   structurelles attendues (noms de sous-traces, profondeur, codes
   namespace présents).

**Côté renderer** :
- **Aucune modification attendue.** Si une modification du renderer
  semble nécessaire, c'est probablement une violation de §4 — vérifier
  d'abord.
- Cas légitime de modification : un nouveau wording métier figé
  introduit un terme qui matche les 14 patterns non-prescriptifs
  (cf. §6.2 doctrine). Whitelister la chaîne précise dans
  `PATTERNS_EXCEPTION_DISCLAIMER` du helper commun (précédent SP8 :
  ajout de 3 chaînes anti-prescriptives portées par
  `comparateur_regimes`).

### 6.2 Comment ajouter un nouveau type d'enrichissement

L'`EtapeAudit` actuelle expose 5 enrichissements : `doctrine_refs`,
`hypotheses`, `notes`, plus implicitement `valeur` et `unite`. Si la
grammaire évolue pour ajouter un nouveau type (hypothèse :
`alertes: list[str]` ou `references_externes: dict`), la procédure est :

1. **Étendre `core/audit.py`** (incrément `AUDIT_SPEC_VERSION` : 1.1.0
   → 1.2.0). Le champ doit avoir un défaut neutre (`[]`, `{}`) pour
   ne pas casser les traces existantes.
2. **Étendre `_render_enrichissements_etape()`** dans le renderer.
   Ajouter une boucle d'itération sur le nouveau champ qui produit
   des lignes `Paragraph` colspan 4 dans le style approprié
   (probablement réutiliser un style existant ou en créer un dans
   `_build_audit_styles()` si nuance visuelle souhaitée).
3. **Décider le placement** :
   - Inline (ligne colspan dans le tableau) → comme `notes`,
     `hypotheses` courtes, `doctrine_refs`.
   - Encadré séparé sous le tableau → comme `hypotheses` longues
     (rare, justifié uniquement si contenu typiquement long).
4. **Tests** : étendre le helper commun avec une section
   `section_enrichissement_<type>` qui vérifie la présence du
   nouveau type dans le rendu. Toujours **neutre** : itère sur le
   champ, ne présume rien du contenu.
5. **Incrémenter `AUDIT_PDF_SPEC_VERSION`** : 1.0.0 → 1.1.0 si la
   capacité est nouvelle (et non rétrocompatible silencieusement
   avec les traces anciennes).

### 6.3 Où ne **pas** toucher

Liste **explicite** des éléments à ne **jamais** modifier sans une
revue architecturale formelle équivalente à une nouvelle sous-passe :

**Signature publique** :
- `generer_pdf_audit(trace, *, cabinet_nom, client_nom, expert_comptable, niveau_confiance, doctrine_version, audit_pdf_spec_version, doctrine_date, baseline_hash) -> bytes`
- Toute modification est un changement breaking → bump majeur `AUDIT_PDF_SPEC_VERSION`.

**Constantes versionnées exposées** :
- `AUDIT_PDF_SPEC_VERSION` (modification = bump version)
- `AUDIT_PDF_DATE`
- `BASELINE_HASH_DEFAUT` (cohérence avec `compare_baseline.py`)
- `SEUIL_HYPOTHESE_LONGUE = 80` (cf. D5)
- `BANDEAU_INTRO_SOMMAIRE` (cf. D11)
- `LARGEUR_UTILE_MM`, `BORNES_*_MM` (cf. D8)

**Décisions architecturales D1-D15** :
Listées en §5. Toute remise en cause exige une sous-passe formelle
avec cadrage, questions, arbitrage, validation, mise à jour du
présent document.

**Tests de référence** :
- `test_pdf_audit_render_tns.py` est le **pilote figé**. Aucune
  modification autorisée. Si une évolution du renderer le casse, c'est
  que l'évolution est non-rétrocompatible et doit être traitée comme
  telle.
- Les tests Assimilé / Libéral / Comparateur sont **étendables**
  (ajout de sections spécifiques OK) mais leurs sections communes
  doivent rester en phase avec le helper.

**Audits de référence** :
- `compare_baseline.py`, `baseline_outputs.py`, `semantic_guardrails.py`,
  `test_no_declaratif_residual.py`, `test_terminologie_freeze.py`,
  `audit_final_b2_controle3.py`, `test_backward_compat_imports.py` :
  fichiers figés du périmètre B.2/B.3, modification interdite sauf
  feu vert explicite ad hoc (cas observé SP1 : ajout de
  `"ui/pdf_audit_export.py"` dans `WHITELIST_FICHIERS` de
  `test_no_declaratif_residual.py` après feu vert explicite, motif
  technique identique à `"ui/pdf_export.py"`).

### 6.4 Critères de bascule vers une refonte

Si l'une des conditions suivantes est rencontrée, une refonte du
renderer (et donc un bump majeur `AUDIT_PDF_SPEC_VERSION` 1.x.x →
2.0.0) doit être envisagée :

- Une trace réelle dépasse **60 pages** PDF en S2 → bascule S3
  (annexes paginées) devient nécessaire.
- Une trace réelle a une sous-trace seule qui génère plus de
  **15 pages internes** → idem.
- Le sommaire dépasse **2 pages** même après ajustements
  cosmétiques → repenser le mécanisme (TOC interactif, sommaire par
  niveau séparé, etc.).
- Le calibrage dynamique des col_widths atteint régulièrement les
  bornes max (`BORNES_CODE_MM[1] = 75`) → besoin d'élargir les
  bornes ou de réduire la police Courier (actuellement 7pt).
- Plus de 5 régimes coexistent avec des besoins de présentation
  divergents documentés → réévaluation possible du contrat de
  neutralité (mais à très haut niveau d'argumentation : la
  neutralité est plus précieuse que les raffinements cosmétiques).

Tant que ces conditions ne sont pas approchées, la doctrine actuelle
tient et toute modification doit s'inscrire dans le respect des
patterns autorisés (§3) et des interdictions (§4).

---

## §7 — Synthèse exécutive

Le renderer PDF audit-ready v1.0.0 (`ui/pdf_audit_export.py`,
~1542 lignes) est un **framework de présentation neutre** qui
transforme toute `TraceAudit` valide en PDF cabinet-ready, sans
connaissance du domaine métier sous-jacent.

Sa propriété la plus précieuse n'est pas son rendu visuel — c'est
sa **neutralité structurelle démontrée** : 4 régimes, 5 niveaux de
profondeur, 70 à 412 étapes ont été absorbés par la même fonction
sans branchement métier (cf. G1-G5 §2.1).

Cette neutralité est l'actif stratégique du système : tant qu'elle
est préservée (§4 interdictions), tout nouveau module métier
instrumenté MODE_AUDIT devient **automatiquement** audit-renderable.
C'est la base de plateforme qui permettra les extensions v1.1+
(PERIN, réceptacles, synthèse décisionnelle) sans réinventer le
renderer à chaque fois.

Toute modification structurelle du renderer doit s'inscrire dans le
cadre des patterns autorisés (§3), respecter les décisions
architecturales D1-D15 (§5) et mettre à jour le présent document si
elle introduit un nouveau pattern ou modifie une décision existante.

---

*Document SP9, livré dans le cadre de la phase Hardening v1.0.1
(SP9 → SP12). Cf. KNOWN_LIMITATIONS.md pour le récap des sous-passes
SP1-SP8 de construction.*
