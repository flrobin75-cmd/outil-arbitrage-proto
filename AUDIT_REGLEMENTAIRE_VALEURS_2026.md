# Audit réglementaire des valeurs France 2026

> **À destination d'un fiscaliste, expert-comptable senior, spécialiste
> protection sociale ou courtier épargne salariale.**
> Document de validation point par point des valeurs réglementaires
> utilisées dans le moteur de simulation. Date de référentiel cible :
> 01/01/2026.

**Avertissement préliminaire au relecteur**

Ce document liste toutes les valeurs réglementaires (taux, plafonds,
formules) hardcodées dans le moteur de simulation. Pour chaque
valeur, la colonne **statut** indique :

- **Confirmé** : valeur considérée stable par l'équipe technique,
  à valider tout de même
- **À confirmer** : valeur incertaine, marquée comme telle dans le
  code source — relecture **prioritaire**
- **Simplification doctrinale** : valeur correcte techniquement mais
  qui repose sur une **simplification** explicite à valider quant à
  son acceptabilité cabinet (vous décidez si la simplification est
  acceptable ou trompeuse)

Pour chaque ligne, indiquez `OK`, `KO` (avec valeur corrigée) ou
`AVIS` (commentaire libre). Toute correction signalée déclenchera
une sous-passe de mise à jour du moteur avec batterie complète et
préservation du framework.

---

## 1. Plafond annuel de la Sécurité sociale (PASS)

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `PASS_2026 = 48 060 €` | `core/profil.py:15` | **À confirmer** | Valeur officielle attendue 2026. ☐ OK / ☐ KO : ____ |

**Note relecteur** : valeur publiée annuellement par décret en
décembre/janvier. Source à confirmer : Décret n° 202?-???.

---

## 2. Cotisations sociales (taux génériques)

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `TX_PATRONAL = 42 %` | `core/profil.py:18` | À confirmer | Cotisations patronales globales assimilé salarié. ☐ OK / ☐ KO : ____ |
| `TX_SALARIAL = 12 %` | `core/profil.py:19` | À confirmer | Cotisations salariales globales. ☐ OK / ☐ KO : ____ |
| `TX_TNS = 45 %` | `core/profil.py:20` | À confirmer | Cotisations TNS globales. ☐ OK / ☐ KO : ____ |
| `TX_LIB = 45 %` | `core/profil.py:21` | À confirmer | Cotisations libéral globales. ☐ OK / ☐ KO : ____ |

**Note relecteur** : ces taux sont des **moyennes pondérées
globales** utilisées dans le module legacy, pas des taux décomposés
par branche (maladie, retraite, AT/MP, etc.). Le moteur ne prétend
pas modéliser la décomposition. Validation : ces taux globaux
sont-ils dans une fourchette acceptable pour une simulation
d'arbitrage rémunération dirigeant ? ☐ Acceptable / ☐ Trop simpliste

---

## 3. CSG/CRDS

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `TX_CSG_CRDS_ACT = 9,7 %` | `core/profil.py:22` | Confirmé | CSG (9,2 %) + CRDS (0,5 %) sur revenus d'activité. ☐ OK / ☐ KO : ____ |
| `TX_CSG_DEDUCTIBLE = 6,8 %` | `core/profil.py:23` | Confirmé | CSG déductible IR. ☐ OK / ☐ KO : ____ |
| `TX_CSG_NON_DEDUCTIBLE = 2,9 %` | `core/profil.py:24` | Confirmé | CSG non déductible IR (2,4 %) + CRDS (0,5 %). ☐ OK / ☐ KO : ____ |
| `ASSIETTE_CSG_SAL = 98,25 %` | `core/profil.py:25` | Confirmé | Abattement 1,75 % pour frais professionnels (plafonné 4 PASS). ☐ OK / ☐ KO : ____ |

---

## 4. Impôt sur le revenu (barème 2026)

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| Plafond T1 (0%) | `IR_PLAFOND_T1 = 11 600 €` | **À confirmer** | Plafond tranche à 0 %. ☐ OK / ☐ KO : ____ |
| Plafond T2 (11%) | `IR_PLAFOND_T2 = 29 579 €` | **À confirmer** | ☐ OK / ☐ KO : ____ |
| Plafond T3 (30%) | `IR_PLAFOND_T3 = 84 577 €` | **À confirmer** | ☐ OK / ☐ KO : ____ |
| Plafond T4 (41%) | `IR_PLAFOND_T4 = 181 917 €` | **À confirmer** | ☐ OK / ☐ KO : ____ |
| Taux T2 = 11 % | `core/profil.py:32` | Confirmé | ☐ OK / ☐ KO : ____ |
| Taux T3 = 30 % | `core/profil.py:33` | Confirmé | ☐ OK / ☐ KO : ____ |
| Taux T4 = 41 % | `core/profil.py:34` | Confirmé | ☐ OK / ☐ KO : ____ |
| Taux T5 = 45 % | `core/profil.py:35` | Confirmé | ☐ OK / ☐ KO : ____ |

**Note relecteur** : barème publié dans la loi de finances annuelle.
Confirmer le périmètre exact des seuils (revenus 2025 imposés en
2026, ou revenus 2026 imposés en 2027 ?). La doctrine du dépôt
indique « référentiel applicable au 01/01/2026 ».

---

## 5. Plafonds du quotient familial

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `PLAF_QF_DEMI_PART = 1 807 €` | `core/profil.py:42` | À confirmer | ☐ OK / ☐ KO : ____ |
| `PLAF_QF_PARENT_ISOLE = 4 262 €` | `core/profil.py:43` | À confirmer | Case T, 1ère personne à charge. ☐ OK / ☐ KO : ____ |
| `PLAF_QF_PERS_SEULE_L = 1 079 €` | `core/profil.py:44` | À confirmer | Case L. ☐ OK / ☐ KO : ____ |
| `PLAF_QF_VEUF = 5 625 €` | `core/profil.py:45` | À confirmer | Veuf avec enfants à charge. ☐ OK / ☐ KO : ____ |
| `PLAF_QF_INVALIDE = 3 608 €` | `core/profil.py:46` | À confirmer | Ancien combattant > 74 ans ou invalide. ☐ OK / ☐ KO : ____ |

---

## 6. Contribution exceptionnelle sur les hauts revenus (CDHR)

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `CDHR_TAUX_PLANCHER = 20 %` | `core/profil.py:54` | À confirmer | Taux plancher CDHR. ☐ OK / ☐ KO : ____ |

---

## 7. Prélèvement forfaitaire unique (PFU)

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `TX_PFU = 31,4 %` | `core/profil.py:59` | À confirmer | PFU global (12,8 % IR + 17,2 % PS... mais 31,4 % ≠ 30 %). **Anomalie potentielle** à clarifier avec le relecteur. ☐ OK / ☐ KO : ____ |
| `TX_PFU_IR = 12,8 %` | `core/profil.py:60` | Confirmé | Part IR du PFU. ☐ OK / ☐ KO : ____ |
| `TX_PFU_GAINS_PERIN = 30 %` | `strategy/receptacles_perin.py:81` | Confirmé | PFU sur gains PERIN (12,8 % + 17,2 %). ☐ OK / ☐ KO : ____ |
| `TX_PFU_GAINS_PERECO = 30 %` | `strategy/receptacles_pereco.py:131` | Confirmé | PFU sur gains PERECO. ☐ OK / ☐ KO : ____ |
| `TX_PFU_GAINS_PERO = 30 %` | `strategy/receptacles_pero.py:141` | Confirmé | PFU sur gains PERO (en sortie capital simulée — cf. §13 simplification). ☐ OK / ☐ KO : ____ |

**Point d'attention** : `TX_PFU = 31,4 %` dans `core/profil.py` vs
`TX_PFU_GAINS_PER* = 30 %`. La valeur 31,4 % pourrait correspondre
à PFU 30 % + CEHR additionnelle, ou être une erreur. À clarifier.

---

## 8. Prélèvements sociaux sur gains (PS 17,2 %)

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `TX_PS_GAINS_PERIN = 17,2 %` | `strategy/receptacles_perin.py:80` | Confirmé | PS sur gains à la sortie PERIN. ☐ OK / ☐ KO : ____ |
| `TX_PS_GAINS_PEE = 17,2 %` | `strategy/receptacles_pee.py:97` | Confirmé | PS sur gains à la sortie PEE (>5 ans). ☐ OK / ☐ KO : ____ |

---

## 9. Impôt sur les sociétés (IS)

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `TX_IS_REDUIT = 15 %` | `core/profil.py:64` | Confirmé | IS taux réduit. ☐ OK / ☐ KO : ____ |
| `TX_IS_NORMAL = 25 %` | `core/profil.py:65` | Confirmé | IS taux normal. ☐ OK / ☐ KO : ____ |
| `IS_PLAF_REDUIT = 42 500 €` | `core/profil.py:66` | Confirmé | Plafond bénéfice IS taux réduit. ☐ OK / ☐ KO : ____ |

---

## 10. Distribution TNS / dividendes

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `SEUIL_DIV_TNS = 10 %` | `core/profil.py:61` | Confirmé | Seuil dividendes TNS assujettis cotisations sociales (10 % capital + primes + CCA). ☐ OK / ☐ KO : ____ |

---

## 11. Forfait social

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `FS_PART, FS_INT, FS_ABO` | `core/profil.py:69-73` | À confirmer | Forfait social participation/intéressement/abondement par taille entreprise (0% pour <50 sal., 20% standard, etc.). **Lire le détail dans le code.** ☐ OK / ☐ KO : ____ |
| `TX_FORFAIT_SOCIAL_PERO = 16 %` | `strategy/receptacles_pero.py:122` | **À CONFIRMER ⚠ PRIORITAIRE** | Forfait social PERO obligatoire. Valeur de 16 % retenue conventionnellement. **Le relecteur doit confirmer ce taux pour PERO** : selon la nature exacte du régime, le taux peut être différent (8 %, 16 %, 20 %, voire 0 % dans certains cas). ☐ OK / ☐ KO : ____ |

**Point d'attention critique** : le forfait social PERO est une
valeur structurante du calcul. Une erreur de 16 % → 8 % ou 20 %
modifie sensiblement le coût entreprise affiché et change
l'attractivité relative du dispositif.

---

## 12. PERIN — plafonds individuels

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `PERIN_PLAFOND_MIN = 10 % × PASS = 4 806 €` | `strategy/perin.py:39` | Confirmé | Plancher du plafond PERIN (CGI art. 163 quatervicies). ☐ OK / ☐ KO : ____ |
| `PERIN_PLAFOND_MAX = 8 × PASS = 384 480 €` | `strategy/perin.py:40` | Confirmé | Plafond absolu PERIN (8 PASS). ☐ OK / ☐ KO : ____ |
| Formule plafond individuel | `strategy/perin.py` | À confirmer | `max(10 % rev. pro. N-1 ; 10 % PASS)` plafonné à `8 PASS`. ☐ OK / ☐ KO : ____ |
| Mutualisation conjoint | `strategy/perin.py` | À confirmer | Mutualisation conjoint via case `7QR`. ☐ OK / ☐ KO : ____ |

---

## 13. PEE / PERECO — abondement

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `PLAFOND_ABONDEMENT_PEE = 8 % × PASS = 3 845 €` | `strategy/receptacles_pee.py:84` | À confirmer | Plafond légal abondement PEE (Code travail art. L3332-11). ☐ OK / ☐ KO : ____ |
| `PLAFOND_ABONDEMENT_PERECO = idem PEE` | `strategy/receptacles_pereco.py:124` | **Simplification doctrinale** | Le plafond légal PERECO est **16 % PASS** (≈ 7 690 €), pas 8 % PASS. Le moteur retient le plafond PEE par cohérence v1.1 (cf. wording). **Acceptabilité cabinet à valider** : faut-il étendre PERECO à son plafond réel ? ☐ Acceptable simplification / ☐ Doit être corrigé |
| `TX_CSG_CRDS_ABONDEMENT_PEE = 9,7 %` | `strategy/receptacles_pee.py:92` | Confirmé | CSG/CRDS sur abondement PEE. ☐ OK / ☐ KO : ____ |
| `TX_CSG_CRDS_ABONDEMENT_PERECO = 9,7 %` | `strategy/receptacles_pereco.py:127` | Confirmé | CSG/CRDS sur abondement PERECO. ☐ OK / ☐ KO : ____ |

---

## 14. PERO — valeurs spécifiques (SP24)

| Valeur | Code source | Statut | Validation |
|---|---|---|---|
| `TX_FORFAIT_SOCIAL_PERO = 16 %` | `strategy/receptacles_pero.py:122` | **À CONFIRMER ⚠** | (Doublon §11 ci-dessus, point critique.) |
| `TX_CSG_CRDS_PERO = 9,7 %` | `strategy/receptacles_pero.py:127` | Confirmé | CSG/CRDS sur cotisation employeur PERO, prélevée sur le salarié. ☐ OK / ☐ KO : ____ |
| `TX_PLAFOND_EXONERATION_REM = 8 %` | `strategy/receptacles_pero.py:134` | **À confirmer** | Plafond d'exonération IR : 8 % de la rémunération brute annuelle (CGI art. 83 2°). Limite globale partagée avec PEE/PERECO. ☐ OK / ☐ KO : ____ |
| `PLAFOND_EXONERATION_PASS = 8 × PASS` | `strategy/receptacles_pero.py:135` | **À confirmer** | Cap absolu d'exonération PERO. ☐ OK / ☐ KO : ____ |
| `TX_PFU_GAINS_PERO = 30 %` | `strategy/receptacles_pero.py:141` | Voir §15 simplification | PFU sur gains à la sortie en capital simulée. ☐ OK / ☐ KO : ____ |

---

## 15. Simplifications doctrinales PERO — validation acceptabilité

> **Ces simplifications sont volontaires et tracées dans le code.**
> Le relecteur doit valider qu'elles **ne sont pas trompeuses** pour
> un cabinet, sachant qu'un wording explicatif est joint au PDF audit.

### 15.1 Sortie capital simulée (le PERO réel est servi en rente)

**Simplification** : le moteur calcule la valeur PERO en sortie
capital, par cohérence comparative avec PERIN/PEE/PERECO. Le PERO
est en réalité servi **principalement en rente viagère**, dont
l'imposition (barème IR sur arrérages) n'est pas modélisée v1.3.

**Wording joint au PDF audit** :
> *« Note de simulation : la valeur nette projetée du PERO est
> calculée en sortie capital, par cohérence et comparabilité avec
> les autres enveloppes du périmètre. Le PERO est en réalité servi
> principalement en rente viagère. La fiscalité de rente n'est pas
> modélisée v1.3. La projection capital présentée doit donc être
> lue comme une simulation comparative, non comme une restitution
> du flux de rente réel. »*

**Validation cabinet** :
- ☐ Le wording est suffisamment clair pour un EC
- ☐ Le wording doit être plus explicite : ___________
- ☐ Cette simplification n'est pas acceptable ; il faut modéliser
  la rente avant POC

### 15.2 Effort réel PERO = CSG/CRDS − économie fiscale (peut être négatif)

**Simplification** : pour un salarié dirigeant assimilé, le seul
flux sortant immédiat au titre du PERO est la CSG/CRDS prélevée
sur la cotisation employeur. L'« effort réel » est défini comme :
`CSG/CRDS − économie fiscale immédiate`. Cette valeur peut être
**négative** (gain net immédiat) quand TMI > CSG/CRDS, ce qui est
fréquent pour un dirigeant.

**Validation cabinet** :
- ☐ Cette définition est cohérente avec la pratique cabinet
- ☐ Risque de mécompréhension EC : un effort négatif peut être lu
  comme « PERO gratuit » ou pire « PERO rémunérateur immédiat »
- ☐ Suggestion d'ajustement : ___________

### 15.3 Capitalisation conventionnelle 2 % annuel déterministe

| Valeur | Code source | Validation |
|---|---|---|
| `RENDEMENT_NOMINAL_ANNUEL = 2 %` | `strategy/receptacles_orchestrateur.py:91` | ☐ Acceptable pour démo cabinet / ☐ Trop conservateur / ☐ Trop optimiste |

**Simplification** : taux fixe 2 % annuel, capitalisation annuelle
simple, déterministe. Pas de stochastique, pas de différenciation
par enveloppe.

**Wording joint** :
> *« Capitalisation conventionnelle annuelle à 2 %, déterministe.
> Cette hypothèse est volontairement simplificatrice : elle ne
> représente pas une projection de rendement réel et ne constitue
> ni une recommandation, ni une promesse de performance. »*

### 15.4 Reprise IR à la sortie PERO non modélisée

**Simplification** : la cotisation employeur PERO, exonérée à
l'entrée, est en théorie reprise au barème IR lors de la sortie
capital. Le moteur applique uniquement le PFU sur les gains (comme
PERIN/PERECO en sortie capital), **sans reprise IR sur la
cotisation employeur initiale**.

**Validation cabinet — point sensible** :
- ☐ Cette simplification est acceptable car PERO réel = rente (et
  donc la sortie capital n'est pas le cas standard)
- ☐ Cette simplification fausse l'arbitrage capital simulé : il
  faudrait appliquer IR au TMI sur la cotisation reprise
- ☐ Avis : ___________

### 15.5 Plafond d'exonération IR mutualisé non implémenté

**Simplification** : le plafond global d'exonération IR
(8 % rémunération, 8 PASS) est en réalité **partagé** entre PERO,
PEE/PERECO obligatoires, et autres versements. Le moteur applique
ce plafond à PERO **sans déduire ce qui aurait déjà été consommé**
par les autres dispositifs.

**Validation cabinet** :
- ☐ Acceptable pour simulation simple
- ☐ Risque de surestimation de l'économie fiscale dans certains cas
- ☐ Avis : ___________

---

## 16. Wordings réglementaires PERO (6 wordings — lisibilité cabinet)

Les 6 wordings doctrinaux PERO sont listés ci-dessous pour
relecture. Ils apparaissent dans le PDF audit Réceptacles attachés
aux étapes économiques correspondantes.

### 16.1 WORDING_PERO_REGLE_COTISATION

> Le PERO est financé par une cotisation employeur exprimée en
> pourcentage du salaire brut du salarié-dirigeant assimilé. Cette
> cotisation est due au titre d'une catégorie objective de salariés
> définie par accord d'entreprise, décision unilatérale de
> l'employeur ou convention collective. L'éligibilité du dirigeant
> assimilé salarié dépend de son appartenance à cette catégorie
> objective.
> *Référence : Code monétaire et financier art. L224-23.*

**Validation** : ☐ Réglementairement correct / ☐ KO : ____________

### 16.2 WORDING_PERO_CSG_CRDS_COTISATION

> La cotisation employeur PERO est assujettie à la CSG et à la
> CRDS au taux global de 9,7 %, prélevées sur le salarié (et non
> sur l'employeur). Cette retenue constitue le seul flux sortant
> immédiat du salarié au titre du PERO : le salarié ne réalise pas
> de versement volontaire dans le périmètre v1.3 retenu.
> *Référence : Code de la sécurité sociale art. L136-1 et L136-2.*

**Validation** : ☐ Réglementairement correct / ☐ KO : ____________

### 16.3 WORDING_PERO_FORFAIT_SOCIAL_EMPLOYEUR

> Côté employeur, la cotisation PERO est soumise au forfait social
> au taux applicable aux régimes de retraite supplémentaire
> obligatoires d'entreprise. v1.3 retient le taux conventionnel de
> 16 % (valeur doctrinale France 2026, à confirmer selon
> réglementation en vigueur). Le coût entreprise total est donc la
> cotisation majorée du forfait social.
> *Référence : Code de la sécurité sociale art. L137-15.*

**Validation** : ☐ Réglementairement correct / ☐ KO : ____________
**Point critique** : confirmer le taux 16 % ou indiquer le taux applicable.

### 16.4 WORDING_PERO_ECONOMIE_FISCALE_ENTREE

> La cotisation employeur PERO n'entre pas dans le revenu imposable
> du salarié (exonération à l'entrée dans la limite globale
> PEE/PERECO/PERO de 8 % de la rémunération brute annuelle,
> plafonnée à 8 PASS). L'économie fiscale immédiate du salarié est
> calculée comme partie exonérée × TMI. Cette économie est
> conceptuellement distincte de celle du PERIN (qui repose sur une
> déduction du revenu imposable du versement individuel).
> *Référence : CGI art. 83 2°.*

**Validation** : ☐ Réglementairement correct / ☐ KO : ____________

### 16.5 WORDING_PERO_DISPONIBILITE_RETRAITE

> Le PERO est un produit retraite : les sommes capitalisées sont
> bloquées jusqu'à la liquidation effective de la retraite, hors
> cas légaux de déblocage anticipé. Cas légaux génériques PER :
> invalidité 2e/3e catégorie, décès du conjoint, surendettement,
> expiration droits chômage, cessation activité non salariée suite
> à liquidation judiciaire. Le cas « acquisition résidence
> principale » est typiquement exclu pour la fraction issue de
> cotisations obligatoires.
> *Référence : Code monétaire et financier art. L224-4 et L224-23.*

**Validation** : ☐ Réglementairement correct / ☐ KO : ____________

### 16.6 WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL

> Note de simulation : la valeur nette projetée du PERO est
> calculée en sortie capital, par cohérence et comparabilité avec
> les autres enveloppes du périmètre (PERIN, PEE, PERECO). Le PERO
> est en réalité servi principalement en rente viagère. La
> fiscalité de rente (imposition au barème progressif sur les
> arrérages) n'est pas modélisée v1.3. La projection capital
> présentée doit donc être lue comme une simulation comparative,
> non comme une restitution du flux de rente réel.

**Validation** : ☐ Wording clair pour EC / ☐ KO : ____________

---

## 17. Récapitulatif des points critiques

| Priorité | Point | Risque si non validé |
|---|---|---|
| **🔴 Très haut** | TX_FORFAIT_SOCIAL_PERO = 16 % (§11, §14) | Coût entreprise affiché faux ; arbitrage cabinet fondé sur une donnée fausse |
| **🔴 Très haut** | PASS_2026 = 48 060 € (§1) | Affecte tous les plafonds dérivés (PERIN, PEE, PERECO, PERO) |
| **🔴 Très haut** | Barème IR 2026 (§4) | Affecte toutes les simulations TMI et économies fiscales |
| **🟠 Haut** | Acceptabilité simplification sortie capital PERO (§15.1) | Risque de mécompréhension EC sur la nature économique réelle du PERO |
| **🟠 Haut** | Effort réel PERO négatif possible (§15.2) | Risque de lecture « PERO gratuit » par un cabinet |
| **🟠 Haut** | Plafond PERECO 8 % vs 16 % PASS (§13) | Sous-estimation potentielle de l'abondement PERECO |
| **🟡 Moyen** | TX_PFU = 31,4 % vs 30 % autres (§7) | Anomalie à clarifier |
| **🟡 Moyen** | Reprise IR sortie PERO non modélisée (§15.4) | Surestimation valeur nette PERO en sortie capital |
| **🟡 Moyen** | Plafond exonération non mutualisé (§15.5) | Surestimation économie fiscale dans cas combinés |

---

## 18. Mode d'emploi pour le relecteur

1. **Parcours rapide §1 à §14** : pour chaque valeur numérique,
   indiquer OK / KO. Une seule passe suffit, le code est strictement
   verrouillé sur ces constantes.

2. **Lecture attentive §15** : les simplifications doctrinales sont
   le **point d'attention majeur**. Vous décidez si elles sont
   acceptables pour un POC cabinet ou si elles doivent être corrigées
   avant.

3. **Relecture §16** : les 6 wordings sont ce que le cabinet **verra
   réellement** dans le PDF audit. Indiquer toute formulation qui
   pourrait induire un cabinet en erreur ou être imprécise
   réglementairement.

4. **Synthèse §17** : si une seule case « 🔴 Très haut » est KO,
   il faut corriger le moteur **avant** tout POC.

5. **Renvoyer le document annoté** au décisionnaire produit. Les
   corrections déclencheront une sous-passe de mise à jour
   (typiquement SP27 si besoin) avec batterie complète et
   préservation du framework SP1-SP26.

---

**Date du document** : 2026-05-21
**Version** : 1.0 (initial, post-SP26 livraison)
**Auteur** : généré automatiquement depuis l'inventaire du code source
**Périmètre** : moteur Réceptacles v1.3 (4 enveloppes PERIN/PEE/PERECO/PERO)
**Total contrôles techniques au vert** : 846
**Hash baseline** : `8863991f27f67847`
