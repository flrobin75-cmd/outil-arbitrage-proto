# Semantic Guardrails

**Version :** alignée sur doctrine v1.0.1
**Date :** 19 mai 2026
**Statut :** Référence Phase B.2.5

Ce document décrit les **garde-fous sémantiques** appliqués à l'outil et la manière dont ils sont automatiquement audités. Il sert de cahier des charges au script `semantic_guardrails.py`.

---

## 1. Pourquoi ces garde-fous

L'outil produit des PDF qui circulent entre cabinets, dirigeants, et parfois conseils tiers (banquier, notaire, gestionnaire de patrimoine). Un mot mal choisi peut :

- requalifier l'outil en conseil en investissement (AMF / MIF II),
- créer une obligation d'information opposable au cabinet,
- pousser à une décision que la modélisation ne supporte pas (TNS T4, BNC vs SEL),
- véhiculer une promesse de performance.

Les garde-fous ne sont pas négociables. Ils sont vérifiés en CI à chaque modification du code, et avant tout freeze de phase.

---

## 2. Patterns surveillés — vue d'ensemble

| # | Pattern | Sévérité | Test gardien |
|---|---|---|---|
| 1 | `Déclaratif` (nom de niveau capitalisé) | **bloquant** | `semantic_guardrails.py` + `test_no_declaratif_residual.py` |
| 2 | `déclaratif` / `déclaratifs` / `déclaratives` (adjectif) | **bloquant dans contenu utilisateur** | `semantic_guardrails.py` (patterns_autorises : docstrings/commentaires uniquement) |
| 3 | `recommandée` / `recommandé` / `recommandation` | bloquant hors whitelist | `semantic_guardrails.py` + `test_terminologie_freeze.py` |
| 4 | `optimisation` / `optimiser` / `optimal` | bloquant hors whitelist | `semantic_guardrails.py` |
| 5 | `garanti` / `garantie` (B.2.5 nouveau) | **bloquant** | `semantic_guardrails.py` |
| 6 | `sans risque` (B.2.5 nouveau) | **bloquant** | `semantic_guardrails.py` |
| 7 | `meilleur régime` (B.2.5 nouveau) | **bloquant** | `semantic_guardrails.py` |
| 8 | `recommandé automatiquement` (B.2.5 nouveau) | **bloquant** | `semantic_guardrails.py` |
| 9 | Agrégation `net_dirigeant_immediat + benefice_retenu_societe` | **bloquant** | `semantic_guardrails.py` + `test_strategy_tns.py` |

Les patterns 1, 3, 4, 9 héritent des audits existants (Phase B.2 Étape 6 — `audit_final_b2_controle3.py`, `test_no_declaratif_residual.py`, `test_terminologie_freeze.py`). Les patterns 2, 5, 6, 7, 8 sont **nouveaux** en B.2.5.

---

## 3. Détail des patterns

### 3.1. Pattern « Déclaratif » (nom de niveau)

**Regex :** `Déclaratif` (sensible à la casse)

**Origine :** terme legacy v1.0.0 renommé en « Conformité renforcée » en v1.0.1.

**Politique :** zéro occurrence visible utilisateur. Tolérance code uniquement pour l'**alias interne** `_ALIASES_NIVEAUX = {"Déclaratif": "Conformité renforcée"}` (résolution silencieuse au cas où un appelant historique passerait l'ancien nom).

**Whitelist :**
- `ui/pdf_export.py` : ligne définissant l'alias
- `doctrine.py` : historique de version (`renommage « Déclaratif » → « Conformité renforcée »`)
- Commentaires de migration (`# ... Déclaratif ...`)
- Docstrings explicatives mentionnant l'alias

**Test gardien :** `test_no_declaratif_residual.py` (8 validations dont 6 PDF + 1 NIVEAU_COULEURS_PDF + 1 grep structurel).

### 3.2. Pattern « déclaratif » (adjectif courant)

**Regex :** `\bdéclaratif[sve]?\b` (insensible à la casse pour ne pas double-matcher avec 3.1)

**Origine :** l'adjectif « déclaratif » (au sens « relatif à la déclaration fiscale ») a été supprimé du livrable utilisateur en B.2.5 pour conserver un garde-fou simple et lisible : zéro occurrence du mot, sous toute forme, dans les contenus présentés.

**Politique :** zéro occurrence visible utilisateur. Tolérance code uniquement dans :
- les docstrings de modules métier (qui parlent à des développeurs)
- les commentaires (`#`)
- les chaînes de tests d'audit (qui doivent contenir le mot pour le chercher)

**Whitelist :**
- `# ... déclaratif ...` (commentaires)
- Docstrings (`"""..."""`)
- Fichiers de tests (`test_*.py`)
- Fichiers d'audit (`semantic_guardrails.py`, `audit_*.py`)
- Documentation (`*.md`)

**Reformulations adoptées en B.2.5** (cf. `TERMINOLOGY.md` §2) :
- « calcul déclaratif » → « calcul destiné aux obligations fiscales »
- « usage déclaratif » → « usage de production fiscale »
- « modules déclaratifs » → « modules de conformité renforcée »
- « pré-remplissage déclaratif » → « préparation des obligations fiscales »

### 3.3. Pattern « recommandée » / « recommandation »

**Regex :** `\brecommand[aéeé]+\b`

**Politique :** seules les **mentions négatives** ou les **désignations techniques internes** sont autorisées.

**Whitelist (extraits non exhaustifs, liste complète dans `semantic_guardrails.py`) :**
- Disclaimers négatifs : `pas (de|une) recommand`, `ne constitue pas`, `ni une recommand`, `non recommand`, etc.
- Garde-fous explicites : `INTERDICTION`, `PAS de "recommandée"`, `jamais ... recommand`
- Mentions passives/neutres : `analyse complémentaire recommandée du cabinet`, `provision URSSAF X % recommandée`
- Désignations techniques internes (clé de dict, variable Python) : `dict des 4 stratégies + code recommandée`, `recommandation = ...`
- Disclaimers AMF : `ni un conseil ... ni une recommand`

**Garde-fou métier :** en libéral L3/L4, **aucune** désignation « régime recommandé » n'est jamais affichée (cf. `ALERTE_BNC_VS_SEL`).

**Test gardien :** `test_terminologie_freeze.py`.

### 3.4. Pattern « optimisation »

**Regex :** `\boptimis[a-zé]+\b` + extension `\boptimal[a-zé]*\b` en B.2.5

**Politique :** zéro occurrence dans le rendu utilisateur. Tolérance code pour :
- `# ... optimis ...` (commentaire)
- `"""... optimis ..."""` (docstring, dont rationale explicite)
- Le **seul** cas où le mot apparaît dans une chaîne affichée est dans `strategy/liberal.py` : la stratégie L2 décrit un « calcul fictif d'**optimisation** de structure » (mot juridiquement consacré pour le choix de personne morale). Le contexte est explicitement défensif et le mot est encadré par un rationale documenté.

### 3.5. Pattern « garanti » / « garantie » (NOUVEAU B.2.5)

**Regex :** `\bgaranti[ese]?\b`

**Politique :** zéro occurrence dans le rendu utilisateur. Aucune **promesse de performance** ou **garantie de résultat** ne doit être véhiculée.

**Whitelist :**
- Docstrings de garde-fou (`"""... aucune garantie de performance ..."""`)
- Commentaires
- Tests et fichiers d'audit
- Disclaimer AMF (le mot apparaît dans la formulation « ne constitue ni une garantie ... »)

**Cas légitime** : la phrase d'avertissement final « ne constitue pas un engagement de performance » est volontairement formulée sans le mot « garantie » pour éviter de l'introduire dans le PDF. Si une formulation alternative était souhaitée, elle doit passer par disclaimer négatif explicite.

### 3.6. Pattern « sans risque » (NOUVEAU B.2.5)

**Regex :** `sans\s+risque`

**Politique :** zéro occurrence, partout, sauf docstring/commentaire de garde-fou.

**Pourquoi :** aucune stratégie d'arbitrage n'est sans risque. Le terme suggère une qualification AMF inappropriée pour un outil non régulé.

### 3.7. Pattern « meilleur régime » (NOUVEAU B.2.5)

**Regex :** `meilleur(e?s?)\s+régime` (insensible à la casse)

**Politique :** zéro occurrence, partout, sauf docstring/commentaire de garde-fou.

**Pourquoi :** le « meilleur régime » suppose une mesure objective unique. En particulier en libéral, le choix BNC/SEL met en jeu trésorerie, transmission, statut du conjoint, etc., dont l'outil ne traite que la couche fiscale/sociale immédiate.

### 3.8. Pattern « recommandé automatiquement » (NOUVEAU B.2.5)

**Regex :** `recommand[éeéà]+s?\s+automatiquement`

**Politique :** zéro occurrence, partout. L'outil **n'effectue jamais de recommandation automatique** — il marque une stratégie comme **retenue** sur la base d'un critère explicitement documenté (typiquement « net dirigeant maximal sous les hypothèses retenues »), ce qui n'est pas la même chose.

### 3.9. Pattern agrégation T4

**Regex :** `(net_dirigeant_immediat\s*\+\s*benefice_retenu|benefice_retenu.*\+\s*net_dirigeant_immediat|total_brut|valeur_totale|patrimoine_total|somme_indicateurs|net_dirigeant_total_t4|net_global_t4)`

**Politique :** zéro occurrence en code métier. Tolérance uniquement pour la **docstring du garde-fou lui-même** dans `strategy/tns.py`.

**Pourquoi :** la stratégie T4 (rétention de bénéfice) est intrinsèquement non-comparable « toutes choses égales » à T1/T2/T3. L'addition donne un chiffre faux (le bénéfice retenu n'est pas dans la poche du dirigeant à court terme). Cf. test `test_strategy_tns.py` (11 tests structurels).

---

## 4. Mécanisme d'audit

### 4.1. Outil unifié `semantic_guardrails.py`

À la sortie de Phase B.2.5, **un script unique** `semantic_guardrails.py` couvre les 9 patterns ci-dessus. Il remplace fonctionnellement trois scripts existants :

- `audit_final_b2_controle3.py` (4 patterns historiques)
- `test_no_declaratif_residual.py` (Déclaratif visible PDF)
- `test_terminologie_freeze.py` (3 patterns terminologiques)

Les trois scripts sont **conservés** dans le dépôt pour garder l'historique d'exécution (et parce que la suite de tests `test_no_declaratif_residual.py` produit des assertions atomiques utiles), mais `semantic_guardrails.py` est l'outil de référence pour les audits en CI ou avant freeze.

### 4.2. Sortie attendue

```
==========================================================================================
  SEMANTIC GUARDRAILS — Audit unifié v1.0.1
==========================================================================================

  ▸ Déclaratif (nom de niveau)
     Total : N | Autorisées : N | Violations : 0   ✓ OK
  ▸ déclaratif (adjectif visible)
     Total : N | Autorisées : N | Violations : 0   ✓ OK
  ▸ recommandée / recommandation
     Total : N | Autorisées : N | Violations : 0   ✓ OK
  ▸ optimisation / optimal
     Total : N | Autorisées : N | Violations : 0   ✓ OK
  ▸ garanti / garantie
     Total : N | Autorisées : N | Violations : 0   ✓ OK
  ▸ sans risque
     Total : N | Autorisées : N | Violations : 0   ✓ OK
  ▸ meilleur régime
     Total : N | Autorisées : N | Violations : 0   ✓ OK
  ▸ recommandé automatiquement
     Total : N | Autorisées : N | Violations : 0   ✓ OK
  ▸ agregation_T4
     Total : N | Autorisées : N | Violations : 0   ✓ OK

  ✓ AUCUNE VIOLATION sur les 9 patterns scannés
```

Code de retour : `0` si OK, `1` si violation.

### 4.3. Politique de filtrage (autorisé vs violation)

Pour chaque pattern, deux mécanismes coexistent :

1. **Patterns regex autorisés** (`patterns_autorises`) — appliqués sur le **contenu de la ligne**. Une ligne qui matche un pattern autorisé est classée « Autorisée » même si elle contient le mot scanné.
2. **Fichiers contextuels** (`fichiers_avec_contexte`) — pour certains patterns, seuls quelques fichiers ont le droit de contenir le mot et seulement s'ils matchent en plus un pattern autorisé.

Les fichiers `test_*.py`, `audit_*.py`, `semantic_guardrails.py` et les `*.md` sont **exclus du scan** par défaut : ils servent à parler du vocabulaire interdit, donc ils doivent pouvoir le contenir.

---

## 5. Politique de PR

Toute PR doit faire passer `semantic_guardrails.py` au vert. Une PR qui introduit une violation est bloquée. Une PR qui introduit une **nouvelle occurrence légitime** doit explicitement étendre le tableau `patterns_autorises` du pattern concerné, avec rationale dans la description.

Toute PR qui propose de **lever** un garde-fou doit avoir le mandat explicite du propriétaire du projet (cf. `README_FREEZE_B2.md` §3).
