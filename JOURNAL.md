# JOURNAL — Outil d'arbitrage rémunération dirigeant

> Trace des sessions de développement et des décisions structurantes.
> Format : par session, du plus récent au plus ancien.
> Tenu manuellement à chaque clôture de session significative.

---

## Méta-projet

**Nom** : Outil d'arbitrage rémunération dirigeant
**Stack** : Python 3.14 + Streamlit 1.57 (Streamlit Cloud)
**URL prod** : https://outil-arbitrage-proto.streamlit.app
**Repo** : `flrobin75-cmd/outil-arbitrage-proto` (branche `main`)
**Owner** : Florent Robin (Cydenti)
**Hash baseline doctrine** : `8863991f27f67847`
**Périmètre v1.3** : 4 réceptacles (PERIN, PEE, PERECO, PERO), 4 régimes (Assimilé salarié, TNS, BNC, Salarié), 4 stratégies (A/B/C/D), audit MODE_AUDIT.

---

## Constantes réglementaires 2026 figées

| Paramètre | Valeur | Source |
|---|---|---|
| PASS 2026 | 48 060 € | LFSS 2026 |
| PFU PER gains sortie capital | 30% (12,8% IR + 17,2% PS) | CGI 158, posture Hagnéré-Altis |
| PFU dividendes (CEHR exclue) | 30% | CGI 117 quater |
| Forfait social PERO | 16% | CSS L. 137-16 al. 3 (PACTE 2019, condition gestion pilotée par défaut) |
| Forfait social PERECO/PEE | 0% | PACTE 2019 |
| Abondement PEE max | 3 845 € (8% PASS) | Code travail L. 3332-11 |
| Abondement PERECO max v1.3 (bridé) | 3 845 € (8% PASS) | CMF L. 224-13 (réel : 7 690 €) |
| Plafond PERIN | 4 806 € (10% PASS) à 38 448 € (8 PASS) | CGI 163 quatervicies, art. 154 bis |
| Plafond Participation | 30 855 € (75% PASS) | Code travail L. 3324-1 |
| Plafond Intéressement | 30 855 € (75% PASS) | Code travail L. 3314-8 |
| CSG/CRDS abondement | 9,7% (CSG 9,2% + CRDS 0,5%) | CSS L. 136-1 et L. 136-2 |
| Plafond exonération PERO | 8% rém brute, max 8 PASS | CGI 83 2° |

---

## Architecture technique

### Pages (10 totales)

**8 pages métier visibles tous utilisateurs** :
1. 🎯 Arbitrage stratégique
2. 🔬 Modules détaillés
3. 🧮 Comparateur de dispositifs
4. 🧰 Réceptacles auditables
5. 📋 Synthèse dirigeant
6. 🔀 Scénarios A vs B
7. 💼 Comparateur patrimonial
8. ✅ Tests de cohérence

**2 pages admin masquées (visibles uniquement avec mot de passe)** :
9. ⚙ Paramètres réglementaires (lecture/contrôle catalogue admin)
10. 🔧 Administration (expert) (édition catalogue admin avec mode expert)

### Auth actuelle
- `ADMIN_PASSWORD` dans Streamlit Secrets (TOML), clé en MAJUSCULES
- Expander discret "🔐 Acces admin" en bas de sidebar
- Mode admin activé via `st.session_state["is_admin"]`
- Pas encore de logs centralisés (chantier auth+logs en cours)

### Sécurité côté UI
- CSS de masquage appliqué juste après `st.set_page_config(...)` :
  - `[data-testid="stToolbar"]` : masque lien GitHub, Share, Edit
  - `#MainMenu` : masque le menu hamburger
  - `.viewerBadge_*` (3 classes) : masque le badge "Made with Streamlit"
  - `footer`, `div[data-testid="stDecoration"]` : masque footer et décoration
- "Manage app" reste visible **uniquement pour le propriétaire du repo** (toi), invisible pour les EC anonymes

---

## Sessions chronologiques (du plus récent au plus ancien)

### Session du 1er juin 2026 — Masquage admin finalisé + cadrage auth+logs

**Durée** : ~2h30
**État final** : ✅ Masquage admin complet et fonctionnel en production

#### Livré

1. **Masquage des 2 pages admin** (Paramètres + Administration) pour utilisateur standard
2. **Expander discret "🔐 Acces admin"** en bas de sidebar avec authentification mot de passe
3. **FS_PERO aligné à 16%** dans le catalogue admin (`ui/admin.py`) avec note PACTE explicite ("sous condition gestion pilotée par défaut")
4. **Sources légales corrigées** dans le catalogue admin :
   - FS_PERO : `CSS L. 137-16 al. 3 (PACTE 2019)` (anciennement `CSS L137-15-1` inexistant)
   - PLAF_ABO_PERECO : `CMF L. 224-13` (anciennement `CSS L3334-8` erroné)
5. **Masquage CSS de la toolbar Streamlit** (lien GitHub, Share, Edit, menu hamburger, badge Streamlit)

#### Méthode validée
- Scripts PowerShell avec marqueurs exacts (find/replace string-based)
- Backups systématiques (`app.py.backup`, `ui/admin.py.backup`)
- Vérification syntaxique `py_compile` avant validation
- Restauration auto en cas d'erreur

#### Bug critique résolu (méthode mémorable)
Mot de passe rejeté malgré config correcte → ligne de debug temporaire `st.write(...secrets_keys...)` ajoutée + push → révélé que le secret était nommé `app_password` (minuscules) dans Streamlit Cloud Secrets au lieu de `ADMIN_PASSWORD` (majuscules). Renommage clé → fix immédiat. Ligne debug retirée et commitée.

**Leçon** : Python `st.secrets.get("X", "")` est case-sensitive et retourne `""` silencieusement si clé absente. À tester avec ligne debug temporaire si suspicion.

#### Cadrage auth+logs (mis en pause)

**Sujet** : remplacer `ADMIN_PASSWORD` unique par `streamlit-authenticator` + logs Google Sheets (chantier ~4h)

**Décisions prises** :
1. **Granularité comptes** = MIX (1 compte cabinet générique + comptes EC individuels à la demande)

**Décisions à prendre (5 restantes)** :
2. Rôles : Option 1 (admin+cabinet) recommandée vs Option 3 (admin+expert+cabinet)
3. Stockage credentials : Streamlit Secrets / YAML versionné / Google Sheet
4. Niveau logs : minimal / standard / détaillé
5. RGPD granularité paramètres : exact / arrondi 10k / bandes
6. Fallback Google Sheets indisponible : bloquer / continuer silencieux / continuer avec warning

**Pré-requis Google Cloud Console** (~15-20 min à faire) :
- Créer projet `outil-arbitrage`
- Activer API Google Sheets + Drive
- Créer Service Account `outil-logs@...`
- Télécharger credentials JSON
- Créer Google Sheet `Logs Pilote Outil 2026`
- Partager Sheet avec Service Account (éditeur)
- Mettre credentials JSON dans Streamlit Secrets sous clé `gcp_service_account`

#### Commits

```
5edafe3 chore: hide Streamlit toolbar (GitHub link masked for pilote phase)
9ead385 chore: remove debug line after secrets fix
a2bdca3 debug: secrets visibility check
8b39884 feat: masquage pages admin + alignement FS_PERO 16% + sources legales
```

#### Questions fonctionnelles élucidées

**`benefice_is` selon régime** :
- En **TNS** (`regime/tns.py`) : `benefice_is` EST l'enveloppe arbitrée. Vrai bouclage `benefice_retenu = (benefice_is - cout_rem) - IS` ligne 409. Allocations 85%/50%/30% selon stratégie T1/T3/T4.
- En **Assimilé** (`strategy/assimile.py`) : `benefice_is` n'apparaît PAS dans le calcul. Seul `profil.enveloppe` (Coût employeur global) pilote l'arbitrage. `benefice_is` ne sert qu'à l'affichage PDF.

**Conséquence ergonomique v1.4** : masquer conditionnellement le champ Bénéfice IS si régime Assimilé (champ décoratif sans impact).

**Plafonds dispositifs non bloqués en saisie** :
- Aucun `max_value=` sur inputs Participation, Intéressement, Abondement PEE/PERECO, PERIN, périphériques
- L'outil borne au calcul mais sans alerte visuelle explicite (vu dans PDF audit : `REC_PERIN_FLUX_EXCEDENT = 194€` quand 5000 saisi sur plafond 4806)
- À ajouter v1.4 : `max_value=`, caption plafond légal, % utilisation temps réel, highlight rouge si dépassement

#### Parcours dirigeant SAS Stratégie D (préparé pour entretien)

55-60 min, 6 étapes :
1. Sidebar (5 min) — Profil SAS, marié 2 parts, enveloppe ~80k
2. 🎯 Arbitrage stratégique (10 min) — Vue 4 stratégies, focus D
3. 🧮 Comparateur de dispositifs (15 min) — Configuration plafonds
4. 🧰 Réceptacles auditables (10 min) — PDF audit cabinet
5. 📋 Synthèse dirigeant (10 min) — Radar 6D, PDF perso
6. 🔀 Scénarios A vs B (5-10 min, optionnel)

**Pré-requis cabinet** : conjointe salariée SAS pour éligibilité dispositifs collectifs.

#### Mécanique PERO (didactique)

PERO = cotisation employeur obligatoire (pas versement volontaire), nécessite accord d'entreprise + catégorie objective. Rare en TPE/PME.

Chaîne calcul 7 étapes :
1. Flux employeur brut = salaire_brut × taux_PERO
2. Plafond exonération = min(8% × salaire_brut, 8 × PASS) — CGI 83 2°
3. Économie fiscale immédiate = cotisation_exonérée × TMI
4. CSG/CRDS = cotisation × 9,7% (à charge salarié)
5. Forfait social = cotisation × 16% (CSS L. 137-16 al. 3)
6. Coût entreprise = cotisation + forfait social
7. Effort réel = CSG/CRDS - économie_IR (souvent négatif → gain immédiat salarié)

**Cas type 80 000 € × 3%** : cotisation 2 400 €, forfait social 384 €, coût entreprise 2 784 €, CSG-CRDS 232,80 €, économie IR 720 € (TMI 30%), effort réel -487,20 € (gain salarié).

**Limitation v1.3** : sortie modélisée en capital alors que PERO sert principalement en rente viagère.

---

### Session du 29 mai 2026 — Masquage admin (Tentative 2 réussie)

**État** : Tentative 1 (Notepad) avait échoué le 27 mai. Cette session = Tentative 2 via script Python `apply_patch.py`.

#### Livré
- Script `apply_patch.py` (283 lignes) avec backups + vérification syntaxique
- 5 modifications appliquées avec succès :
  - A1 : Bloc admin après dict PAGES
  - A2 : Filtrage PAGES_VISIBLES selon `is_admin`
  - A3 : Expander "🔐 Acces admin" en bas sidebar
  - B1 : FS_PERO 16% + source légale + note PACTE
  - B2 : PLAF_ABO_PERECO source CMF L. 224-13
- Diagnostic du bug secrets (clé en minuscules vs majuscules)
- Configuration ADMIN_PASSWORD propre

#### Commits
- `8b39884 feat: masquage pages admin + alignement FS_PERO 16% + sources legales`

---

### Session du 27 mai 2026 (matin) — Tentative 1 masquage admin (ÉCHEC Notepad)

**État** : Indentation cassée à plusieurs reprises via édition Notepad → annulation propre via `git checkout app.py`. Démo cabinet reportée.

**Leçon** : éviter l'édition manuelle Notepad sur Python (sensibilité à l'indentation). Préférer scripts PowerShell/Python avec marqueurs.

---

### Session du 26 mai 2026 (soir) — Préparation démo cabinet : P1 v3 + Livret v2

**Durée** : Longue session de génération de livrables

#### Livré
1. **Audit réglementaire P1 v3** (`Audit_reglementaire_valeurs_2026_v3.docx` + `.pdf`)
   - 6 points critiques / 8 importants / 6 vigilants
   - Vérification 3 points clés : PFU 31,4% conforme LFSS 2026, FS PERO 16% conforme L.137-16 al.3 (sous condition PACTE), PASS 48 060 € cohérent

2. **Livret de prise en main v2** (`Livret_prise_en_main_v2.docx` + `.pdf`)

#### Architecture régimes élucidée
- 4 régimes cibles utilisateur : Assimilé salarié, TNS, BNC, Salarié
- SCP absorbée dans "Profession libérale (BNC)"

#### Points P1 v3 identifiés
- **15.b** (CRITIQUE) : incohérence moteur 16% / admin 8% pour FS_PERO → **résolu le 29 mai**
- **15.c** (IMPORTANT) : sources légales fausses dans le catalogue admin → **résolu le 29 mai**
- **4.b** : PFU PER 30% vs 31,4% (posture Hagnéré-Altis vs DGFiP) → **toggle paramétrable à ajouter v1.4**

---

## Pending — Priorités

### Court terme (J+1 à J+7)
- [ ] Mini-revue 30 min fiscaliste sur P1 v3 (5 points : PFU PER 4.b, FS PERO L.137-16, incohérence moteur/admin 15.b résolue, sources légales 15.c résolu, PASS LFSS 2026)
- [ ] Envoi P1 v3 au cabinet pilote (après mini-revue fiscaliste)
- [ ] Reprise cadrage auth+logs (5 questions restantes + config Google Cloud Console)
- [ ] Valider/corriger les 6 reconstitutions surlignées jaune dans Livret v2
- [ ] Onboarding 2-3 cabinets pilotes

### Moyen terme — v1.4 (J+30)
- [ ] Toggle PFU gains PER 30%/31,4% paramétrable (point 4.b P1 v3)
- [ ] Masquage conditionnel champs Coût employeur/Bénéfice IS selon régime
- [ ] `max_value=` sur inputs Comparateur + caption plafonds + % utilisation temps réel + highlight rouge si dépassement
- [ ] Modéliser sortie PERO en rente (actuellement capital simulation)
- [ ] Modéliser plafond PERECO 16% PASS réel (vs 8% bridé v1.3)
- [ ] Actualiser commentaire `receptacles_perin.py:77` (hausse CSG LFSS 2026)
- [ ] Personnalisation cabinet PDF audit (nom/logo/mentions)
- [ ] Module feedback intégré
- [ ] Docstring obsolète `ui/pdf_audit_export.py:237` (PASS 47100 → 48060)
- [ ] Source légale FS_PERO dans wordings PDF (page 22 cite encore L137-15)
- [ ] Résoudre divergence inter-modules `scenarios.py` (5%) vs `receptacles_pero.py` (16%)
- [ ] Implémentation auth `streamlit-authenticator` + Google Sheets logs (~4h)

---

## Conventions de travail

- **Patches** : scripts PowerShell avec marqueurs exacts (find/replace string-based). Pas d'édition Notepad sur Python.
- **Backups** : systématiques avant toute modif (`fichier.py.backup`)
- **Vérifications** : `py_compile` ou `git diff` avant `git commit`
- **Commits** : messages clairs en anglais (`feat:`, `chore:`, `docs:`, `fix:`)
- **Sources légales** : rigoureuses (CGI, CMF, CSS, Code travail) avec numéro d'article exact
- **Communication EC** : vouvoiement en cold outreach, non-salesy
- **Livrables PDF** : McKinsey/BCG-grade (DejaVu Sans, palette définie, 150 DPI)
- **Modifications** : pas de modif unilatérale du code sans validation explicite (governance)

---

## Contacts et stack annexe

- **Streamlit Cloud** : compte connecté, repo `flrobin75-cmd/outil-arbitrage-proto`, secret `ADMIN_PASSWORD` configuré
- **Local dev** : Windows 10 UX3402, `C:\Users\UX3402\migration-pero\repo-git\` (clone Git connecté)
- **PowerShell** : version par défaut Windows 10
- **Python** : 3.14.5 (Streamlit Cloud), local à confirmer

---

*Dernière mise à jour : 1er juin 2026*
