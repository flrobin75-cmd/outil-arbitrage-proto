# Architecture UI Réceptacles — Doctrine v1.2 (SP20)

**Version :** v1.2.0 (squelette SP20)
**Date :** 20 mai 2026
**Statut :** doctrine vivante — à étendre lors de SP21/SP22

---

## §1 — Principes fondamentaux

Ce document encadre la couche UI Streamlit du module Réceptacles
(`strategy/receptacles_*.py`, v1.1.0). Sa raison d'être est de
**rendre exploitable au quotidien** un moteur métier déjà stabilisé,
sans déformer la doctrine établie en SP13-SP19.

### 1.1 — Position produit (principe directeur)

> **L'UI doit rester descriptive, pas émotionnelle.**

L'outil aligne, structure, restitue. Il ne classe pas, ne recommande
pas, ne valorise pas une option vis-à-vis d'une autre. Cette neutralité
est **gardée par construction** dans le moteur (D-R6, D-R12,
`ARCHITECTURE_RECEPTACLES.md` §3.6, FRONT-1 de `KNOWN_LIMITATIONS.md`)
et doit l'être tout autant dans l'UI.

### 1.2 — Architecture consumer-side stricte

L'UI Streamlit consomme exclusivement le résultat de
`allocation_receptacles()` (orchestrateur SP18). Elle ne :

- ne **recalcule** rien (aucune formule, aucune dérivation économique)
- ne **filtre** rien à des fins métier (filtrer ≠ trier ≠ classer)
- ne **réinterprète** rien (un nombre est un nombre, pas une « valeur favorable »)
- ne **génère** aucun wording prescriptif (les wordings doctrinaux
  sont déjà figés dans `strategy/receptacles_wordings.py`)

### 1.3 — Principe de neutralité UX

L'UI ne doit produire **aucun signal émotionnel ou prescriptif** vers
l'utilisateur cabinet. Voir §4 (anti-patterns).

---

## §2 — Responsabilités UI vs Moteur

### 2.1 — Ce qui appartient au moteur (rappel)

Tout ce qui produit une valeur économique, un wording doctrinal, ou
une trace d'audit :
- Calculs économiques (`strategy/receptacles_*.py`)
- Wordings doctrinaux (`strategy/receptacles_wordings.py`)
- Composition cross-enveloppes (`strategy/receptacles_orchestrateur.py`)
- Trace audit (`core/audit.py::TraceAudit`)
- Rendu PDF cabinet (`ui/pdf_audit_export.py`)

### 2.2 — Ce qui appartient à l'UI (périmètre SP20)

- Affichage de structures de données déjà calculées par le moteur
- Mise en forme visuelle (Streamlit widgets : `st.table`, `st.metric`,
  `st.dataframe`, `st.expander`, `st.tabs`)
- Saisie utilisateur des **inputs** du moteur
  (flux disponible, horizons demandés, profil)
- Délégation au moteur (appel à `allocation_receptacles()`)
- Navigation entre vues (à partir de SP21/SP22)

### 2.3 — Ce qui n'appartient à personne (interdit)

- Calculer en doublon ce que le moteur a déjà calculé (anti-pattern fort)
- Recomposer ou réagréger les résultats moteur (anti-pattern fort)
- Surcharger les wordings doctrinaux par des wordings UI ad hoc

---

## §3 — Architecture 3 couches

```
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 3 — STREAMLIT                                       │
│  ui/page_receptacles.py      (entry-point, ~150 lignes)     │
│  ui/composants_receptacles.py (widgets, ~250 lignes)        │
│  Affiche, saisit, navigue. AUCUN CALCUL.                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ consomme structures UI-ready
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 2 — ADAPTATEUR (FRONTIÈRE DOCTRINALE)               │
│  ui/adapter_receptacles.py   (~200 lignes)                  │
│  Pure fonction. Pas de Streamlit. Pas de calcul.            │
│  Transforme ResultatAllocationReceptacles → DataFrames      │
│  / listes ordonnées / dicts UI-ready.                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ consomme ResultatAllocationReceptacles
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  COUCHE 1 — MOTEUR (FIGÉ V1.1.0)                            │
│  strategy/receptacles_*.py                                  │
│  Calculs, wordings, trace audit, orchestration.             │
└─────────────────────────────────────────────────────────────┘
```

### 3.1 — Décision D-UI-1 : adapter pur fonction

`ui/adapter_receptacles.py` doit être :

- **pur** : pas d'effet de bord, pas de state Streamlit
- **déterministe** : entrée identique → sortie identique
- **sans Streamlit** : `import streamlit` interdit dans ce fichier
- **sans pandas magique implicite** : si pandas est utilisé, c'est
  pour produire un DataFrame de sortie, pas pour appliquer une
  transformation métier
- **sans enrichissement métier** : pas de calcul nouveau, pas
  d'agrégation nouvelle, pas de wording nouveau

L'adapter est l'**unique** point d'entrée du moteur dans la couche UI.

### 3.2 — Décision D-UI-2 : couche Streamlit muette en calcul

`ui/page_receptacles.py` et `ui/composants_receptacles.py` :

- consomment uniquement les structures produites par l'adapter
- n'importent aucun module `strategy/receptacles_*.py` directement
  pour leurs calculs (l'orchestrateur n'est appelé qu'une fois,
  dans la page, et son résultat passe par l'adapter)
- peuvent importer les **wordings doctrinaux** (lecture seule) pour
  les afficher tels quels (mais ne les modifient ni ne les composent)

---

## §4 — Anti-patterns interdits (section centrale)

Cette section est volontairement détaillée. Les dérives UI sont
beaucoup plus dangereuses que les oublis UI : un oubli sera demandé
par un utilisateur, une dérive sera **silencieusement intégrée** et
deviendra difficile à corriger.

### 4.1 — Anti-pattern A1 : Signal prescriptif explicite

**Interdit :**
```python
if valeur_nette_perin > valeur_nette_pee:
    st.success("PERIN recommandé")
```

**Pourquoi :** introduit une recommandation. Viole FRONT-1
(`KNOWN_LIMITATIONS.md` §0.3).

**À la place :** afficher les valeurs côte à côte sans assertion.

### 4.2 — Anti-pattern A2 : Composants Streamlit à connotation valeur

**Interdits sans justification explicite :**

- `st.success(...)` : suggère que c'est « bien »
- `st.error(...)` (hors message d'erreur technique) : suggère que c'est « mal »
- `st.warning(...)` à propos d'une valeur économique
- `st.balloons()` : célébration
- `st.toast(...)` à propos d'une valeur économique
- `st.snow()` : décoration émotionnelle

**Liste illustrative non limitative.** Toute API Streamlit à
connotation émotionnelle est suspecte par défaut.

**Autorisés :**

- `st.info(...)` pour rappel doctrinal neutre
- `st.error(...)` pour erreur **technique** (ex. « profil invalide,
  veuillez le compléter »)
- `st.warning(...)` pour avertissement **technique** (ex. « calcul
  basé sur des hypothèses conventionnelles »)

### 4.3 — Anti-pattern A3 : Emojis valorisants

**Interdits dans le contenu :**

- ✅ : suggère validation/approbation
- 🏆 : suggère gagnant
- 🚀 : suggère performance
- 💰 : suggère gain d'argent
- 🥇🥈🥉 : suggère classement
- 🔥 : suggère « hot pick »
- ⭐ : suggère qualité valorisée

**Autorisés** (descriptifs neutres) :

- 🧰 : outil
- 📘 : document
- 📊 : tableau
- 📋 : liste
- ⏱️ : horizon temporel
- ℹ️ : information

**Liste illustrative non limitative.** Tout emoji à connotation
valorisante ou compétitive est suspect par défaut.

### 4.4 — Anti-pattern A4 : Couleurs sémantiques valorisantes

**Interdits :**

- Texte vert pour la « meilleure » valeur
- Texte rouge pour la « pire » valeur
- Surlignage doré, bordures or, badges « top »
- Highlight conditionnel d'une cellule de tableau selon sa valeur
  économique (ex. `df.style.highlight_max`)
- Heatmap colorée sur valeurs économiques (ex. `df.style.background_gradient`)
- Gradients de couleur indexés sur la valeur (ex. « plus c'est élevé,
  plus c'est vert »)

**Autorisés :**

- Palette monochrome cabinet (gris/anthracite/blanc)
- Couleur d'accent **unique** pour la structure (ex. titres, séparateurs)
- Distinction visuelle par **forme** (gras, encadré) à condition
  qu'elle ne soit pas conditionnelle à la valeur

### 4.4 bis — Anti-pattern A4 bis : Sémantique chromatique implicite (SP21)

Cette section est l'extension SP21 de A4.

**Position doctrinale (votre formulation SP21) :**

> *Le vrai risque n'est pas la palette ; c'est la sémantique
> visuelle.*

**Neutralité chromatique stricte appliquée à la restitution des
hypothèses :**

- Pas de **vert** (suggère « bon », « validé »)
- Pas de **rouge** (suggère « mauvais », « bloqué »)
- Pas d'**orange / jaune saturé** (suggère « attention », « risque »)
- Pas de **badges colorés** sur des valeurs économiques ni sur des
  hypothèses
- Pas de **delta colorée** (`st.metric(..., delta=...)` qui colore
  positif/négatif)

**Privilégier :**

- **Gris / anthracite** (texte, séparateurs)
- **Bleu neutre** (titres, accents structurels)
- **Séparateurs sobres** (`st.divider`, lignes fines)

**Justification du périmètre :** un scan automatisé de la palette
(valeurs hex) serait disproportionné et générerait des faux positifs.
La protection effective est portée par les invariants UI-I5
(composants à connotation valeur interdits, déjà testés) et par la
discipline de ne jamais introduire de styling conditionnel sur les
valeurs économiques.

Concrètement, le périmètre SP21 utilise uniquement les widgets
Streamlit standards (`st.dataframe`, `st.table`, `st.markdown`,
`st.expander`, `st.caption`) avec leur thème par défaut, sans
override de couleurs.

### 4.5 — Anti-pattern A5 : Tri/classement implicite

**Interdit :**

```python
df_sorted = df.sort_values("valeur_nette", ascending=False)
st.dataframe(df_sorted)
```

**Pourquoi :** un tri sur une dimension économique introduit une
hiérarchie. Même sans annonce, l'utilisateur lit la première ligne
comme « la meilleure ».

**À la place :** ordre fixe doctrinal **PERIN → PEE → PERECO**,
toujours, dans tous les tableaux. Voir §6 (invariant UI-I1).

### 4.6 — Anti-pattern A6 : Wording prescriptif libre

**Interdits dans les chaînes affichées :**

- « recommandé », « optimal », « idéal », « parfait »
- « meilleur », « gagnant », « préférable », « avantageux »
- « priorité », « privilégier », « conseiller »
- « score », « ranking », « indice de performance »
- « rendement supérieur », « efficacité fiscale », « performance »
- « gain », « perte » (sauf au sens technique chiffré non comparatif)

**À la place :** wordings doctrinaux figés de
`strategy/receptacles_wordings.py` (16 wordings centralisés v1.1.0).

### 4.6 bis — Anti-pattern A6 bis : Qualification subjective des hypothèses (SP21)

Cette section est l'extension SP21 de A6, spécifique à la
restitution des hypothèses doctrinales.

**Position doctrinale (votre formulation SP21) :**

> *Le danger maintenant : transformer l'auditabilité en justification.
> « Le rendement 2 % est prudent. » Pourquoi ? Parce que c'est déjà
> une interprétation. La bonne formulation : « Convention de
> capitalisation utilisée : 2 %. »*

Quand l'UI restitue une hypothèse, elle doit la **décrire**, pas la
**qualifier**. Toute qualification (« prudent », « raisonnable »,
« conservateur », « efficace »...) est une interprétation déguisée,
même si elle paraît défensive ou modeste.

**Interdits dans les chaînes affichées (étendus SP21) :**

- « sécurisé », « optimisé », « performant », « avantageux »,
  « intéressant »
- « prudent », « raisonnable », « équilibré », « conservateur »
- « favorable », « défavorable », « attractif », « pertinent »
- « efficace », « idéal »

**Liste illustrative non limitative.** Tout adjectif qui qualifie
une hypothèse plutôt que la décrire est suspect par défaut.

**Exemple type interdit :**

```python
# NON : qualifie l'hypothèse
st.write("Le rendement 2 % est prudent.")
st.write("Convention efficace : capitalisation annuelle.")
st.write("TMI 30 % : situation conservatrice.")
st.write("Plafond idéal pour ce profil.")
```

**Reformulations descriptives correctes :**

```python
# OUI : décrit l'hypothèse
st.write("Convention de capitalisation utilisée : 2 % par an.")
st.write("Convention : capitalisation annuelle simple et déterministe.")
st.write("TMI appliquée : 30 %.")
st.write("Plafond légal de versement : 4 806 €.")
```

**Règle pratique :** si la phrase pouvait être supprimée sans perdre
d'information factuelle, c'est probablement une interprétation. Une
description énonce des valeurs et des paramètres ; une justification
porte un jugement.

**Anti-pattern collatéral — phrase d'introduction interprétative :**

Même les phrases d'introduction autour des tableaux doivent rester
strictement descriptives.

```python
# NON : interprète l'intention de l'affichage
st.write("Ces hypothèses permettent de contextualiser les résultats.")
st.write("Ces paramètres garantissent la fiabilité du calcul.")
```

```python
# OUI : décrit le contenu
st.write("Hypothèses doctrinales utilisées pour les calculs.")
st.write("Conventions de simulation appliquées aux 3 enveloppes.")
```

### 4.7 — Anti-pattern A7 : Recalcul caché

**Interdit :**

```python
# Dans un composant UI
valeur_nette = capital - fiscalite_sortie  # NON : doublon moteur
gain_relatif = (val_pereco - val_perin) / val_perin  # NON : dérivation nouvelle
```

**Pourquoi :** chaque ligne de calcul dans l'UI est une **régression
silencieuse en attente**. Si le moteur change sa formule
(`fiscalite_sortie` par exemple), l'UI continuera à calculer avec
l'ancienne logique sans crash visible.

**À la place :** ne lire que ce que le moteur a déjà calculé. Si une
grandeur n'est pas exposée par le dataclass `LigneHorizonReceptacle`,
c'est qu'elle n'est pas censée être affichée — pas qu'il faut la
recalculer.

### 4.8 — Anti-pattern A8 : Métriques agrégées cross-enveloppes

**Interdit :**

```python
total = val_perin + val_pee + val_pereco
st.metric("Total cumulé", total)
```

**Pourquoi :** suggère qu'on peut additionner 3 enveloppes alternatives
(elles répondent à la même question avec des moyens différents,
elles ne se cumulent pas dans la vraie vie sauf cas spécifique).

**À la place :** afficher les 3 valeurs séparément, dans l'ordre fixe.

### 4.9 — Anti-pattern A9 : Storytelling de navigation audit (SP22)

**Position doctrinale (votre formulation SP22) :**

> *Navigation audit ≠ storytelling. L'UI doit permettre l'inspection,
> la lecture, la traçabilité. Mais jamais guider la décision.*

Cette section est l'extension SP22 de la philosophie A1-A8 spécifique
à la couche « navigation » : panneau de téléchargement PDF, accès
audit, étapes structurantes.

Le danger n'est plus la prescription explicite (couverte par A1, A6,
A6 bis) mais la **mise en scène narrative** : présenter le panneau
navigation comme une « exploration », une « découverte » de
résultats. Même sans qualificatif valoratif, le simple choix de
**re-montrer des valeurs économiques** dans un panneau navigation
crée une nouvelle surface narrative.

**Interdits dans le panneau navigation audit :**

- Aperçu détaillé des étapes RECAP **avant** téléchargement du PDF
  (sélectionne et met en avant des dimensions économiques)
- Mise en évidence d'une enveloppe par rapport à une autre (couleur,
  position, taille)
- Verbes interprétatifs : « Explorer », « Approfondir », « Analyser »,
  « Comparer en détail », « Découvrir »
- Métadonnées qualitatives sur le contenu du PDF (« audit détaillé »,
  « analyse complète » : adjectifs valoratifs)
- Affichage de toute valeur économique calculée (les valeurs sont
  dans le PDF et dans les tableaux multi-horizon SP20)

**Autorisés dans le panneau navigation audit :**

- Téléchargement direct du PDF (composant `st.download_button`)
- Compteurs structurels neutres : nombre d'étapes racine, nombre de
  sous-traces, nombre d'hypothèses tracées, nombre d'étapes RECAP,
  taille PDF en bytes
- Métadonnées de traçabilité : version doctrine, version spec audit,
  version renderer, hash baseline, timestamp génération
- Verbes strictement fonctionnels : « Télécharger », « Voir »,
  « Afficher », « Ouvrir »

**Règle pratique :** un panneau navigation correct est ennuyeux à
lire. S'il « donne envie » d'aller voir quelque chose, c'est
probablement déjà du storytelling déguisé.

### 4.10 — Anti-pattern A10 : Bouton conditionné par valeur économique (SP22)

**Position doctrinale (votre formulation SP22) :**

> *Aucun bouton ne doit dépendre d'une valeur économique. Tous les
> accès doivent rester symétriques, indépendants des résultats.*

**Interdits :**

```python
# NON : le bouton n'apparaît que si PERIN « gagne »
if valeur_nette_perin > valeur_nette_pee:
    st.button("Télécharger audit PERIN")

# NON : le label dépend du résultat
label = f"Télécharger audit {meilleure_enveloppe}"
st.download_button(label, ...)

# NON : ordre des boutons selon performance
ordre = sorted(enveloppes, key=lambda e: e.valeur_nette, reverse=True)
for env in ordre:
    st.button(f"Voir {env}")
```

**Pourquoi :** un bouton dont l'existence, le label ou la position
dépend d'une valeur économique introduit **une recommandation
implicite par voie d'interface**, même si aucun mot prescriptif
n'est employé. La personne qui clique reçoit le signal « ceci a été
mis en avant pour moi », ce qui contredit FRONT-1
(`KNOWN_LIMITATIONS.md` §0.3).

**Autorisés :**

```python
# OUI : un bouton unique, neutre, présent sans condition
st.download_button("Télécharger le PDF audit", data=pdf_bytes, ...)

# OUI : 3 boutons symétriques dans l'ordre fixe doctrinal
for env in enveloppes_dans_ordre_doctrinal():  # PERIN, PEE, PERECO
    st.button(f"Voir {env}", disabled=False)  # tous accessibles
```

**Règle pratique :** si on supprime tous les résultats du calcul, les
boutons doivent rester identiques (présents, labellisés pareil, dans
le même ordre). Sinon, ils encodent un signal économique implicite.

---

## §5 — Composants autorisés (court, illustratif)

Cette section est volontairement courte. Le périmètre des composants
sera enrichi au fil de SP20-SP22 selon les besoins réels.

### 5.1 — Composants Streamlit autorisés en SP20

- `st.title`, `st.header`, `st.subheader`, `st.caption` : structure
- `st.markdown`, `st.write`, `st.text` : contenu textuel neutre
- `st.table`, `st.dataframe` : tableaux (sans styling conditionnel
  sur valeurs)
- `st.metric` (sans `delta` qui ferait apparaître une variation
  positive/négative colorée)
- `st.columns`, `st.tabs`, `st.expander` : layout
- `st.info` : rappel doctrinal neutre
- `st.number_input`, `st.selectbox` : saisie inputs
- `st.divider`, `st.empty` : structure

### 5.2 — Composants tolérés sous condition

- `st.button` : pour lancer le calcul, jamais pour valoriser un choix
- `st.download_button` : pour télécharger le PDF cabinet
- `st.code` : pour afficher des chaînes brutes (codes étapes, etc.)

### 5.3 — Composants interdits par défaut (§4)

- `st.success`, `st.balloons`, `st.toast`, `st.snow`
- `st.metric` **avec** paramètre `delta` (colore selon signe)
- `dataframe.style.highlight_*`, `dataframe.style.background_gradient`

### 5.4 — Composants panneau navigation audit autorisés (SP22)

Le panneau navigation audit (§4.9) utilise un sous-ensemble strict :

- `st.download_button(label, data=pdf_bytes, file_name, mime)` :
  bouton unique de téléchargement, label strictement fonctionnel
  (« Télécharger le PDF audit »).
- `st.dataframe(df, ...)` : tableau de compteurs structurels neutres.
- `st.caption` : mention de version doctrine + timestamp génération,
  strictement descriptive.

**Composants interdits dans le panneau navigation** (en plus des
interdits §5.3 généraux) :

- Tout bouton conditionné par une valeur économique (A10)
- Tout label de bouton à verbe interprétatif (A9) : « Explorer »,
  « Approfondir », « Analyser », « Comparer en détail », « Découvrir »
- Tout aperçu détaillé des étapes RECAP en zone navigation
  (A9 : les valeurs économiques sont dans le PDF téléchargé et dans
  les vues SP20/SP21, pas dans la navigation)

---

## §6 — Invariants UI testables

### 6.1 — Invariant UI-I1 : ordre fixe doctrinal

**L'ordre d'affichage ne doit jamais être déterminé par la performance
économique.** L'ordre fixe doctrinal est **PERIN → PEE → PERECO**,
dans :

- les colonnes ou lignes de tableaux multi-enveloppes
- les onglets (`st.tabs`)
- les sections de pages
- les exports CSV
- les structures intermédiaires de l'adapter
- les **signets PDF** (SP22) — ordre des entrées dans la table des
  matières du PDF audit, ordre des sections enveloppes
- les **boutons de navigation** (SP22) — si plusieurs boutons portent
  sur des enveloppes (ex. liens directs PERIN/PEE/PERECO), ils
  apparaissent dans l'ordre doctrinal

Toute fonction qui retourne une liste d'enveloppes doit retourner
l'ordre `["PERIN", "PEE", "PERECO"]` strict.

Testé par : `test_ui_receptacles_neutralite.py` (section ordre stable).

### 6.2 — Invariant UI-I2 : aucun mot interdit dans le code UI

Auto-scan textuel des 14 patterns proscrits + mots interdits SP18 sur
les fichiers `ui/page_receptacles.py`, `ui/composants_receptacles.py`,
`ui/adapter_receptacles.py`.

Citations négatives autorisées via **whitelist explicite** (cf. §7.2).

Testé par : `test_ui_receptacles_neutralite.py` (section auto-scan).

### 6.3 — Invariant UI-I3 : pas d'import direct de modules métier
depuis la couche Streamlit

Les fichiers `ui/page_receptacles.py` et `ui/composants_receptacles.py`
**peuvent** importer :

- `streamlit`, `pandas`
- `ui.adapter_receptacles` (la frontière)
- `strategy.receptacles_orchestrateur` (uniquement pour appeler
  `allocation_receptacles`, jamais pour autre chose)
- `strategy.receptacles_wordings` (lecture seule de wordings figés)
- `core.profil`, `core.audit` (types et structures)
- `ui.pdf_audit_export` (pour le bouton télécharger PDF, SP22+)

Mais ne **doivent pas** importer :

- `strategy.receptacles_perin`, `strategy.receptacles_pee`,
  `strategy.receptacles_pereco` directement (l'orchestrateur les
  appelle, l'UI ne les appelle pas)

Testé par : `test_ui_receptacles_neutralite.py` (section imports).

### 6.4 — Invariant UI-I4 : adapter sans Streamlit

`ui/adapter_receptacles.py` ne **doit pas** importer streamlit.

Testé par : `test_ui_receptacles_neutralite.py` (section adapter pur).

### 6.5 — Invariant UI-I5 : interdiction de composants à connotation valeur

Auto-scan du code UI pour détecter `st.success`, `st.balloons`,
`st.toast`, `st.snow`, et `st.metric(..., delta=...)`.

Testé par : `test_ui_receptacles_neutralite.py` (section composants
interdits).

### 6.6 — Invariant UI-I6 : vocabulaire de qualification subjective interdit (SP21)

Auto-scan textuel **global** sur **tous les fichiers UI Réceptacles**
(`ui/adapter_receptacles.py`, `ui/composants_receptacles.py`,
`ui/page_receptacles.py`) pour détecter les 15 mots de qualification
subjective des hypothèses interdits par A6 bis (§4.6 bis) :

  sécurisé, optimisé, performant, avantageux, intéressant,
  prudent, raisonnable, équilibré, conservateur, favorable,
  défavorable, attractif, pertinent, efficace, idéal

**Portée du scan : tous les fichiers UI** (votre apport SP21).

Justification (votre formulation) :

> *Si on ne scanne pas globalement, la dérive se déplacera
> naturellement vers helper, composant secondaire, caption, tooltip,
> page future.*

Le principe UI-I2 doit rester **global**.

**Whitelist :** comme UI-I2, l'auto-scan s'applique uniquement aux
chaînes en argument de `Call` AST (chaînes visibles utilisateur).
Les commentaires, docstrings et noms de constantes restent exemptés.

Testé par : `test_ui_receptacles_neutralite.py` (section UI-I6
vocabulaire hypothèses, scan global).

---

## §7 — Tests applicables et whitelist

### 7.1 — Test principal v1.2

`test_ui_receptacles_neutralite.py` couvre les 6 invariants UI-I1 à
UI-I6 ci-dessus.

### 7.2 — Whitelist explicite des citations doctrinales

Le présent fichier (`ARCHITECTURE_UI_RECEPTACLES.md`) cite **par
nature** les anti-patterns à interdire. L'auto-scan ne s'applique
pas à ce fichier ; il s'applique uniquement aux fichiers Python
de l'UI.

Pour les fichiers `ui/page_receptacles.py`,
`ui/composants_receptacles.py`, `ui/adapter_receptacles.py`, les
citations négatives sont **autorisées** dans :

- les **commentaires de code** (lignes commençant par `#`)
- les **docstrings** de fonctions/modules
- les **noms d'anti-patterns** (constantes, ex. `ANTI_PATTERN_A1`)

Mais **interdites** dans :

- les **chaînes affichées** à l'utilisateur (`st.markdown(...)`,
  `st.write(...)`, `st.title(...)`, etc.)
- les **labels** de widgets (`st.button("...")`, etc.)
- les **noms de colonnes** de DataFrames affichés

L'auto-scan distingue les deux contextes (commentaire/docstring vs
chaîne affichée).

### 7.3 — Critères de bascule v2

Si l'un des éléments suivants survient, ré-examiner la doctrine UI :

- Demande cabinet explicite pour un signal prescriptif (« quelle
  enveloppe choisir ? »)
- Refonte du moteur (changement de structure
  `LigneHorizonReceptacle`)
- Migration hors Streamlit (ex. SaaS web full)
- Évolution de la frontière FRONT-1 (`KNOWN_LIMITATIONS.md` §0.3)

---

**Fin de la doctrine v1.2.0 — squelette SP20.**

Sera enrichie en SP21 (panneau hypothèses doctrinales) et SP22
(navigation audit, lien PDF, trace).
