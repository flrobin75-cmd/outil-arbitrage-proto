"""
test_ui_receptacles_neutralite.py — Test de neutralité UI Réceptacles (SP20).

Couvre les 5 invariants UI doctrinaux définis dans
`ARCHITECTURE_UI_RECEPTACLES.md` §6 :

  UI-I1 — Ordre fixe doctrinal PERIN → PEE → PERECO
  UI-I2 — Aucun mot interdit dans le code UI (chaînes affichées)
  UI-I3 — Pas d'import direct de modules métier depuis Streamlit
  UI-I4 — Adapter sans Streamlit
  UI-I5 — Interdiction de composants à connotation valeur

Conventions du test :
  - 6 sections distinctes (1 par invariant + ordre + composants
    interdits + extraction PDF)
  - Auto-scan textuel sur les 3 fichiers UI Réceptacles
  - Whitelist explicite des citations doctrinales autorisées
    (commentaires + docstrings + noms de constantes)
  - Vérification par AST des imports pour UI-I3, UI-I4

Usage : python3 test_ui_receptacles_neutralite.py
Exit code 0 si tous les contrôles passent.

Référence doctrinale : `ARCHITECTURE_UI_RECEPTACLES.md` §6 (invariants),
§7.2 (whitelist).
"""

import ast
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))


# ============================================================
# CONFIGURATION
# ============================================================
RACINE = Path(__file__).parent
FICHIERS_UI = [
    RACINE / "ui" / "adapter_receptacles.py",
    RACINE / "ui" / "composants_receptacles.py",
    RACINE / "ui" / "page_receptacles.py",
]


# 14 patterns proscrits (cf. doctrine.py §6.2 + auto-scan v1.0+)
PATTERNS_INTERDITS = [
    (r"\boptim\w*\b", "optimal"),
    (r"\bmeilleur(?:e|s|es)?\b", "meilleur"),
    (r"\bgagnant(?:e|s|es)?\b", "gagnant"),
    (r"\bperdant(?:e|s|es)?\b", "perdant"),
    (r"\bavantageu(?:x|se|ses)\b", "avantageux"),
    (r"\brecommand(?:é|ée|és|ées|er|ation|ations)\b", "recommandation"),
    (r"\bpréconis(?:é|ée|er|ation)\b", "préconisation"),
    (r"\bconseill(?:é|ée|er)\b", "conseil"),
    (r"\bidéal(?:e|s|es)?\b", "idéal"),
    (r"\bparfait(?:e|s|es)?\b", "parfait"),
    (r"\bsupérieur(?:e|s|es)?\b", "supérieur"),
    (r"\binférieur(?:e|s|es)?\b", "inférieur"),
    (r"\bprioritaire(?:s)?\b", "prioritaire"),
    (r"\bprivilégi\w*\b", "privilégier"),
]


# Mots interdits SP18 dans le contenu visible (cf. test SP18 16.5)
MOTS_INTERDITS_SP18 = [
    "score", "ranking", "indice de performance",
    "efficacité fiscale", "performance", "rendement supérieur",
]


# 15 patterns interdits SP21 — qualification subjective des hypothèses
# (cf. ARCHITECTURE_UI_RECEPTACLES.md §4.6 bis et §6.6 invariant UI-I6).
# Liste illustrative non limitative ; étend A6 (wording prescriptif libre).
# Note : "optimisé", "avantageux", "idéal" sont déjà couverts par
# PATTERNS_INTERDITS SP18 (regex \boptim\w*\b, etc.). Inclus ici pour
# rappel doctrinal et lisibilité de la liste SP21.
PATTERNS_INTERDITS_SP21 = [
    (r"\bsécuris(?:é|ée|és|ées)\b", "sécurisé"),
    (r"\bperformant(?:e|s|es)?\b", "performant"),
    (r"\bintéressant(?:e|s|es)?\b", "intéressant"),
    (r"\bprudent(?:e|s|es)?\b", "prudent"),
    (r"\braisonnable(?:s)?\b", "raisonnable"),
    (r"\béquilibré(?:e|s|es)?\b", "équilibré"),
    (r"\bconservateur(?:s)?\b", "conservateur"),
    (r"\bconservatrice(?:s)?\b", "conservatrice"),
    (r"\bfavorable(?:s)?\b", "favorable"),
    (r"\bdéfavorable(?:s)?\b", "défavorable"),
    (r"\battractif(?:s)?\b", "attractif"),
    (r"\battractive(?:s)?\b", "attractive"),
    (r"\bpertinent(?:e|s|es)?\b", "pertinent"),
    (r"\befficace(?:s)?\b", "efficace"),
    # Note : "optimisé", "avantageux", "idéal" déjà dans
    # PATTERNS_INTERDITS SP18 mais inclus dans la liste SP21
    # doctrinale pour cohérence (cf. doctrine §4.6 bis).
]


# Composants Streamlit interdits par défaut (§4.2)
COMPOSANTS_INTERDITS = [
    "st.success", "st.balloons", "st.toast", "st.snow",
]


# Emojis valorisants (§4.3) — liste illustrative non limitative
EMOJIS_INTERDITS = ["✅", "🏆", "🚀", "💰", "🥇", "🥈", "🥉", "🔥", "⭐"]


# Imports interdits dans la couche Streamlit (§6.3 UI-I3)
# La couche Streamlit (page + composants) ne doit pas importer
# directement les modules métier des enveloppes (PERIN, PEE, PERECO).
IMPORTS_INTERDITS_STREAMLIT = [
    "strategy.receptacles_perin",
    "strategy.receptacles_pee",
    "strategy.receptacles_pereco",
]


# ============================================================
# UTILITAIRES
# ============================================================
class AssertionRunner:
    """Runner minimaliste pour résultats sectionnés."""

    def __init__(self):
        self.section_courante = ""
        self.ok = 0
        self.ko = 0
        self.echecs = []

    def section(self, titre: str):
        print()
        print("=" * 95)
        print(f"  {titre}")
        print("=" * 95)
        self.section_courante = titre

    def check(self, label: str, condition: bool, detail: str = ""):
        if condition:
            print(f"  ✓ {label}")
            self.ok += 1
        else:
            print(f"  ✗ {label}")
            if detail:
                print(f"      → {detail}")
            self.ko += 1
            self.echecs.append((self.section_courante, label, detail))

    def synthese(self, titre_global: str) -> int:
        print()
        print("=" * 95)
        print("  SYNTHÈSE")
        print("=" * 95)
        print(f"  Contrôles OK : {self.ok}")
        print(f"  Contrôles KO : {self.ko}")
        print()
        if self.ko == 0:
            print(f"  ✓ {titre_global} PASS")
            return 0
        print(f"  ✗ {titre_global} FAIL :")
        for sec, label, det in self.echecs[:10]:
            print(f"    - [{sec}] {label}")
            if det:
                print(f"        {det}")
        return 1


def _extraire_imports(path: Path) -> list:
    """Retourne la liste des modules importés par un fichier Python."""
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _extraire_chaines_visibles(path: Path) -> list:
    """Extrait les chaînes littérales potentiellement visibles
    (paramètres de fonctions, sans docstrings).

    Pour SP20, heuristique simple : les chaînes qui apparaissent dans
    un appel de fonction (ast.Call) sont considérées comme « visibles
    utilisateur » et soumises à l'auto-scan strict. Les chaînes en
    position de docstring (premier child d'un module/classe/fonction)
    sont **exemptées** par la whitelist §7.2.

    Returns:
        Liste de tuples (numéro_ligne, chaîne).
    """
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)

    # Repérer les nodes Constant qui sont docstrings
    docstrings_id = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef,
                              ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                docstrings_id.add(id(node.body[0].value))

    # Collecter les chaînes en position d'argument de Call
    chaines_visibles = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Args positionnels
            for arg in node.args:
                if (isinstance(arg, ast.Constant)
                        and isinstance(arg.value, str)
                        and id(arg) not in docstrings_id):
                    chaines_visibles.append((arg.lineno, arg.value))
            # Args nommés
            for kw in node.keywords:
                if (isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                        and id(kw.value) not in docstrings_id):
                    chaines_visibles.append((kw.value.lineno, kw.value.value))

    return chaines_visibles


def _scanner_chaine_pour_pattern(chaine: str, patterns: list) -> list:
    """Retourne la liste des matches (nom, regex_str) trouvés dans
    la chaîne."""
    matches = []
    for regex, nom in patterns:
        if re.search(regex, chaine, flags=re.IGNORECASE):
            matches.append(nom)
    return matches


# ============================================================
# MAIN
# ============================================================
def main() -> int:
    print()
    print("=" * 95)
    print("  TEST NEUTRALITÉ UI RÉCEPTACLES (SP20)")
    print("=" * 95)

    runner = AssertionRunner()

    # === Vérification préliminaire : les 3 fichiers existent ===
    runner.section("Préliminaire : existence des fichiers UI")
    for f in FICHIERS_UI:
        runner.check(
            f"Fichier {f.name} présent",
            f.exists(),
            detail=str(f),
        )
    if runner.ko > 0:
        return runner.synthese("UI Réceptacles neutralité")

    # === UI-I1 : Ordre fixe doctrinal PERIN → PEE → PERECO ===
    runner.section("UI-I1 — Ordre fixe doctrinal PERIN → PEE → PERECO")

    from ui.adapter_receptacles import (
        enveloppes_dans_ordre_doctrinal,
        ORDRE_DOCTRINAL_ENVELOPPES,
    )

    runner.check(
        "UI-I1.1 Constante ORDRE_DOCTRINAL_ENVELOPPES exposée",
        True,  # déjà importé, donc présente
    )
    ordre = enveloppes_dans_ordre_doctrinal()
    runner.check(
        "UI-I1.2 enveloppes_dans_ordre_doctrinal() retourne "
        "('PERIN', 'PEE', 'PERECO', 'PERO') depuis SP26",
        ordre == ("PERIN", "PEE", "PERECO", "PERO"),
        detail=f"observé: {ordre}",
    )
    runner.check(
        "UI-I1.3 ORDRE_DOCTRINAL_ENVELOPPES est immutable (tuple)",
        isinstance(ORDRE_DOCTRINAL_ENVELOPPES, tuple),
        detail=f"type observé: {type(ORDRE_DOCTRINAL_ENVELOPPES).__name__}",
    )

    # Vérifier empiriquement l'ordre dans le résultat de l'adapter
    from core.audit import TraceAudit
    from core.profil import Profil
    from strategy.receptacles_orchestrateur import allocation_receptacles
    from ui.adapter_receptacles import (
        extraire_tableau_multi_horizon,
        extraire_tableau_par_horizon,
        extraire_etapes_recapitulatives,
    )

    profil = Profil()
    trace_test = TraceAudit(regime="Test neutralité", profil_resume="")
    resultat_test = allocation_receptacles(
        profil, flux_disponible=5000.0, audit=trace_test,
    )

    df_multi = extraire_tableau_multi_horizon(resultat_test)
    enveloppes_observees_multi = df_multi["Enveloppe"].tolist()
    # Vérifier que toutes les lignes PERIN viennent avant les lignes
    # PEE, qui viennent avant les lignes PERECO, qui viennent avant
    # les lignes PERO (ordre doctrinal SP26 étendu à 4 enveloppes)
    indices_perin = [i for i, e in enumerate(enveloppes_observees_multi)
                     if e == "PERIN"]
    indices_pee = [i for i, e in enumerate(enveloppes_observees_multi)
                   if e == "PEE"]
    indices_pereco = [i for i, e in enumerate(enveloppes_observees_multi)
                      if e == "PERECO"]
    indices_pero = [i for i, e in enumerate(enveloppes_observees_multi)
                    if e == "PERO"]
    runner.check(
        "UI-I1.4 extraire_tableau_multi_horizon : ordre "
        "PERIN < PEE < PERECO < PERO (SP26)",
        (max(indices_perin) < min(indices_pee)
         and max(indices_pee) < min(indices_pereco)
         and max(indices_pereco) < min(indices_pero)),
        detail=f"indices PERIN {indices_perin}, PEE {indices_pee}, "
               f"PERECO {indices_pereco}, PERO {indices_pero}",
    )

    df_h5 = extraire_tableau_par_horizon(resultat_test, 5)
    runner.check(
        "UI-I1.5 extraire_tableau_par_horizon : ordre "
        "PERIN, PEE, PERECO, PERO (SP26)",
        df_h5["Enveloppe"].tolist() == ["PERIN", "PEE", "PERECO", "PERO"],
        detail=f"observé: {df_h5['Enveloppe'].tolist()}",
    )

    etapes_recap = extraire_etapes_recapitulatives(trace_test)
    erreurs_ordre_recap = []
    for r in etapes_recap:
        noms = [t[0] for t in r["valeurs_par_enveloppe"]]
        if noms != ["PERIN", "PEE", "PERECO", "PERO"]:
            erreurs_ordre_recap.append((r["code"], noms))
    runner.check(
        "UI-I1.6 extraire_etapes_recapitulatives : ordre "
        "PERIN → PEE → PERECO → PERO dans valeurs_par_enveloppe (SP26)",
        not erreurs_ordre_recap,
        detail=f"erreurs: {erreurs_ordre_recap[:2]}",
    )

    # === UI-I2 : Aucun mot interdit dans les chaînes affichées ===
    runner.section("UI-I2 — Aucun mot interdit dans le code UI "
                   "(chaînes affichées)")

    # Whitelist §7.2 : les chaînes en docstring + commentaires sont
    # exemptées. On scanne uniquement les chaînes en position d'argument
    # de Call AST (qui sont les chaînes potentiellement affichées).
    for f in FICHIERS_UI:
        chaines = _extraire_chaines_visibles(f)
        erreurs_fichier = []
        for ligne_no, chaine in chaines:
            matches = _scanner_chaine_pour_pattern(
                chaine, PATTERNS_INTERDITS,
            )
            if matches:
                erreurs_fichier.append(
                    (ligne_no, ", ".join(matches), chaine[:80])
                )
            # Mots interdits SP18 dans contenu visible
            for mot in MOTS_INTERDITS_SP18:
                if mot.lower() in chaine.lower():
                    erreurs_fichier.append(
                        (ligne_no, f"SP18 mot interdit '{mot}'",
                         chaine[:80])
                    )
        runner.check(
            f"UI-I2.{f.name} Aucun mot interdit dans les chaînes "
            f"visibles ({len(chaines)} chaînes scannées)",
            not erreurs_fichier,
            detail=f"erreurs: {erreurs_fichier[:2]}",
        )

    # === UI-I3 : Imports interdits depuis la couche Streamlit ===
    runner.section("UI-I3 — Pas d'import direct de modules métier "
                   "depuis la couche Streamlit")

    fichiers_streamlit = [
        RACINE / "ui" / "composants_receptacles.py",
        RACINE / "ui" / "page_receptacles.py",
    ]
    for f in fichiers_streamlit:
        imports = _extraire_imports(f)
        imports_interdits_trouves = [
            i for i in imports if i in IMPORTS_INTERDITS_STREAMLIT
        ]
        runner.check(
            f"UI-I3.{f.name} N'importe aucun module enveloppe direct "
            f"(strategy.receptacles_perin/pee/pereco)",
            not imports_interdits_trouves,
            detail=f"imports interdits trouvés: {imports_interdits_trouves}",
        )

    # === UI-I4 : Adapter sans Streamlit ===
    runner.section("UI-I4 — Adapter sans Streamlit (frontière doctrinale)")

    imports_adapter = _extraire_imports(
        RACINE / "ui" / "adapter_receptacles.py"
    )
    runner.check(
        "UI-I4.1 ui/adapter_receptacles.py n'importe pas streamlit",
        "streamlit" not in imports_adapter,
        detail=f"imports: {imports_adapter}",
    )
    runner.check(
        "UI-I4.2 ui/adapter_receptacles.py n'importe aucun module "
        "ui.composants_* ni ui.page_*",
        not any(i.startswith("ui.composants")
                or i.startswith("ui.page") for i in imports_adapter),
        detail=f"imports: {imports_adapter}",
    )

    # === UI-I5 : Composants à connotation valeur interdits ===
    runner.section("UI-I5 — Composants Streamlit interdits "
                   "(st.success, st.balloons, st.toast, st.snow)")

    for f in FICHIERS_UI:
        with open(f, "r", encoding="utf-8") as fh:
            contenu = fh.read()
        composants_trouves = []
        for comp in COMPOSANTS_INTERDITS:
            # Pattern : "st.success(" ou "st.success " etc.
            # Mais on exclut les commentaires (lignes commençant par # ou contenant
            # le composant après un #)
            for match in re.finditer(re.escape(comp) + r"\s*\(", contenu):
                start = match.start()
                # Trouver le début de la ligne
                ligne_start = contenu.rfind("\n", 0, start) + 1
                ligne = contenu[ligne_start:contenu.find("\n", start)]
                # Vérifier si l'occurrence est dans un commentaire
                # (caractère # avant l'occurrence sur cette ligne)
                hash_pos = ligne.find("#")
                col_match = start - ligne_start
                if hash_pos == -1 or hash_pos >= col_match:
                    # Pas dans un commentaire
                    no_ligne = contenu[:start].count("\n") + 1
                    composants_trouves.append((no_ligne, comp))
        runner.check(
            f"UI-I5.{f.name} N'utilise aucun composant interdit "
            f"({', '.join(COMPOSANTS_INTERDITS)})",
            not composants_trouves,
            detail=f"trouvés: {composants_trouves[:3]}",
        )

    # === UI-I5 bis : Emojis valorisants interdits dans chaînes visibles ===
    runner.section("UI-I5 bis — Emojis valorisants interdits dans "
                   "chaînes visibles")

    for f in FICHIERS_UI:
        chaines = _extraire_chaines_visibles(f)
        emojis_trouves = []
        for ligne_no, chaine in chaines:
            for emoji in EMOJIS_INTERDITS:
                if emoji in chaine:
                    emojis_trouves.append(
                        (ligne_no, emoji, chaine[:60])
                    )
        runner.check(
            f"UI-I5b.{f.name} Aucun emoji valorisant "
            f"({' '.join(EMOJIS_INTERDITS)}) dans les chaînes visibles",
            not emojis_trouves,
            detail=f"trouvés: {emojis_trouves[:2]}",
        )

    # === UI-I6 : Vocabulaire de qualification subjective interdit (SP21) ===
    # Scan global (votre apport SP21) sur tous les fichiers UI.
    # cf. ARCHITECTURE_UI_RECEPTACLES.md §4.6 bis et §6.6.
    runner.section("UI-I6 — Vocabulaire de qualification subjective "
                   "interdit dans chaînes visibles (SP21, scan global)")

    for f in FICHIERS_UI:
        chaines = _extraire_chaines_visibles(f)
        erreurs_fichier = []
        for ligne_no, chaine in chaines:
            matches = _scanner_chaine_pour_pattern(
                chaine, PATTERNS_INTERDITS_SP21,
            )
            if matches:
                erreurs_fichier.append(
                    (ligne_no, ", ".join(matches), chaine[:80])
                )
        runner.check(
            f"UI-I6.{f.name} Aucun mot SP21 de qualification "
            f"subjective ({len(PATTERNS_INTERDITS_SP21)} patterns "
            f"scannés sur {len(chaines)} chaînes)",
            not erreurs_fichier,
            detail=f"erreurs: {erreurs_fichier[:2]}",
        )

    # === Section bonus : test fonctionnel adapter avec mock streamlit ===
    runner.section("Bonus — Tests fonctionnels adapter (déterminisme, "
                   "pureté)")

    # Déterminisme : appeler 2 fois doit donner le même résultat
    trace_a = TraceAudit(regime="A", profil_resume="")
    res_a = allocation_receptacles(profil, flux_disponible=5000.0,
                                    audit=trace_a)
    trace_b = TraceAudit(regime="B", profil_resume="")
    res_b = allocation_receptacles(profil, flux_disponible=5000.0,
                                    audit=trace_b)
    df_a = extraire_tableau_multi_horizon(res_a)
    df_b = extraire_tableau_multi_horizon(res_b)
    runner.check(
        "Bonus-1 extraire_tableau_multi_horizon est déterministe",
        df_a.equals(df_b),
        detail="DataFrames divergent entre 2 appels identiques",
    )

    # Pureté : appeler l'adapter ne modifie pas le résultat moteur
    valeurs_avant = [l.valeur_nette
                     for l in res_a.perin.lignes_par_horizon]
    extraire_tableau_multi_horizon(res_a)
    valeurs_apres = [l.valeur_nette
                     for l in res_a.perin.lignes_par_horizon]
    runner.check(
        "Bonus-2 extraire_tableau_multi_horizon ne mute pas son entrée",
        valeurs_avant == valeurs_apres,
        detail=f"avant: {valeurs_avant}, après: {valeurs_apres}",
    )

    # === Bonus SP21 : extraction hypothèses + composants exposés ===
    runner.section("Bonus SP21 — Auditabilité visible : extraction "
                   "hypothèses + composants exposés")

    from ui.adapter_receptacles import extraire_hypotheses_doctrinales
    hyp_test = extraire_hypotheses_doctrinales(trace_a)

    runner.check(
        "Bonus-SP21-1 rendement_annuel extrait depuis trace",
        hyp_test.get("rendement_annuel") is not None,
        detail=f"observé: {hyp_test.get('rendement_annuel')!r}",
    )
    runner.check(
        "Bonus-SP21-2 horizons_demandes extrait depuis trace "
        "(correction SP21 du bug SP20)",
        hyp_test.get("horizons_demandes") == [5, 10, 20],
        detail=f"observé: {hyp_test.get('horizons_demandes')!r}",
    )
    runner.check(
        "Bonus-SP21-3 par_enveloppe contient les 4 enveloppes en "
        "ordre fixe PERIN → PEE → PERECO → PERO (SP26)",
        list(hyp_test.get("par_enveloppe", {}).keys()) ==
        ["PERIN", "PEE", "PERECO", "PERO"],
        detail=f"observé: {list(hyp_test.get('par_enveloppe', {}).keys())!r}",
    )
    # Hypothèses minimales attendues par enveloppe
    runner.check(
        "Bonus-SP21-4 hypothèses PERIN contiennent au moins éligibilité, "
        "TMI, plafond_versement",
        all(c in hyp_test["par_enveloppe"]["PERIN"]
            for c in ["eligible", "tmi", "plafond_versement"]),
        detail=f"observé: {hyp_test['par_enveloppe']['PERIN']!r}",
    )
    runner.check(
        "Bonus-SP21-5 hypothèses PEE contiennent au moins éligibilité, "
        "taux_abondement, plafond_abondement",
        all(c in hyp_test["par_enveloppe"]["PEE"]
            for c in ["eligible", "taux_abondement", "plafond_abondement"]),
        detail=f"observé: {hyp_test['par_enveloppe']['PEE']!r}",
    )
    runner.check(
        "Bonus-SP21-6 hypothèses PERECO contiennent au moins éligibilité, "
        "TMI, taux_abondement, plafond_abondement",
        all(c in hyp_test["par_enveloppe"]["PERECO"]
            for c in ["eligible", "tmi", "taux_abondement",
                      "plafond_abondement"]),
        detail=f"observé: {hyp_test['par_enveloppe']['PERECO']!r}",
    )

    # Composants SP21 exposés depuis ui.composants_receptacles
    # (vérification par AST pour éviter d'importer streamlit dans le test)
    composants_src = (
        RACINE / "ui" / "composants_receptacles.py"
    ).read_text(encoding="utf-8")
    composants_exposes_attendus = [
        "tableau_conventions_transverses",
        "tableau_hypotheses_par_enveloppe",
        "panneau_hypotheses_doctrinales",
    ]
    for nom in composants_exposes_attendus:
        runner.check(
            f"Bonus-SP21-expose `{nom}` défini dans composants_receptacles.py",
            f"def {nom}(" in composants_src,
            detail="non trouvé via grep textuel",
        )

    # === Bonus SP22 : Navigation audit ===
    # Pas de nouvel invariant UI-I7 (E-Q1=pas d'UI-I7) ; les labels de
    # boutons sont déjà couverts par UI-I2 + UI-I6 (auto-scan global).
    # Bonus contrôles structurels uniquement.
    runner.section("Bonus SP22 — Navigation audit : présence, label "
                   "fonctionnel, métadonnées doctrinales")

    composants_sp22_attendus = [
        "tableau_structure_audit",
        "afficher_metadonnees_doctrinales",
        "panneau_navigation_audit",
    ]
    for nom in composants_sp22_attendus:
        runner.check(
            f"Bonus-SP22-expose `{nom}` défini dans composants_receptacles.py",
            f"def {nom}(" in composants_src,
            detail="non trouvé via grep textuel",
        )

    # Vérifier la présence de la constante LABEL_TELECHARGER_PDF
    runner.check(
        "Bonus-SP22-label LABEL_TELECHARGER_PDF défini comme "
        "constante module",
        "LABEL_TELECHARGER_PDF" in composants_src
        and 'LABEL_TELECHARGER_PDF = "Télécharger le PDF audit"' in composants_src,
        detail="constante non trouvée ou valeur différente",
    )

    # Vérifier l'absence de label de bouton à verbe interprétatif
    # (§4.9 : verbes interprétatifs interdits)
    page_src = (RACINE / "ui" / "page_receptacles.py").read_text(
        encoding="utf-8",
    )
    verbes_interpretatifs_interdits = [
        "Explorer", "Approfondir", "Analyser",
        "Comparer en détail", "Découvrir",
    ]
    composants_et_page = composants_src + "\n" + page_src
    verbes_trouves = [
        v for v in verbes_interpretatifs_interdits
        if v in composants_et_page
    ]
    runner.check(
        "Bonus-SP22-verbes Aucun verbe interprétatif dans le code UI "
        f"(scan : {' / '.join(verbes_interpretatifs_interdits)})",
        not verbes_trouves,
        detail=f"trouvés: {verbes_trouves}",
    )

    # Vérifier qu'aucun bouton n'est conditionné par une comparaison
    # de valeur économique (A10 : symétrie d'accès).
    # Heuristique : on cherche un pattern "if ...valeur_nette...:" suivi
    # d'un appel st.button/st.download_button dans les lignes proches.
    import re as _re
    pattern_conditionnel = _re.compile(
        r"if\s+.*valeur_nette.*:\s*\n(?:\s+.*\n){0,3}\s+st\.(?:button|download_button)\(",
        flags=_re.MULTILINE,
    )
    matchs_conditionnels = (
        pattern_conditionnel.findall(composants_src)
        + pattern_conditionnel.findall(page_src)
    )
    runner.check(
        "Bonus-SP22-symetrie Aucun bouton conditionné par "
        "valeur_nette dans le code UI (A10)",
        not matchs_conditionnels,
        detail=f"matches: {matchs_conditionnels[:2]}",
    )

    # Bouton st.download_button effectivement appelé dans la page
    runner.check(
        "Bonus-SP22-presence st.download_button utilisé dans "
        "page_receptacles.py (via panneau_navigation_audit)",
        # st.download_button est dans le composant panneau_navigation_audit,
        # appelé par page_receptacles ; on vérifie la chaîne d'appel.
        "panneau_navigation_audit" in page_src
        and "st.download_button" in composants_src,
        detail="chaîne d'appel téléchargement PDF non détectée",
    )

    # ============================================================
    # SECTION SP26 — PERO en 4e enveloppe (intégration UI)
    # ============================================================
    # Cohérent SP25 (section 17 test_strategy_receptacles) : vérifier
    # que PERO est absorbé comme 4e enveloppe au même titre que les
    # 3 autres, sans traitement UX spécifique côté UI/adapter.
    runner.section("SP26 — Intégration PERO côté UI (4e enveloppe)")

    # SP26-1 : ORDRE_DOCTRINAL_ENVELOPPES adapter étendu à 4
    runner.check(
        "SP26-1 ORDRE_DOCTRINAL_ENVELOPPES adapter UI à 4 enveloppes "
        "(désynchronisation SP25 refermée)",
        ORDRE_DOCTRINAL_ENVELOPPES == ("PERIN", "PEE", "PERECO", "PERO"),
        detail=f"observé: {ORDRE_DOCTRINAL_ENVELOPPES}",
    )

    # SP26-2 : adapter + orchestrateur alignés (cohérence cross-niveau)
    from strategy.receptacles_orchestrateur import ENVELOPPES_V1_3
    runner.check(
        "SP26-2 ORDRE_DOCTRINAL_ENVELOPPES adapter == ENVELOPPES_V1_3 "
        "orchestrateur (alignement levé désynchronisation SP25)",
        tuple(ORDRE_DOCTRINAL_ENVELOPPES) == tuple(ENVELOPPES_V1_3),
        detail=(f"adapter: {ORDRE_DOCTRINAL_ENVELOPPES}, "
                f"orchestrateur: {ENVELOPPES_V1_3}"),
    )

    # SP26-3 : DataFrame multi-horizon avec PERO actif inclut 4 enveloppes
    profil_pero_actif = Profil(taux_cotisation_pero=0.03)
    profil_pero_actif.tmi = 0.30
    trace_pero = TraceAudit(regime="Test SP26 PERO actif",
                            profil_resume="")
    res_pero = allocation_receptacles(
        profil_pero_actif, flux_disponible=5000.0, audit=trace_pero,
    )
    df_pero = extraire_tableau_multi_horizon(res_pero)
    runner.check(
        "SP26-3 DataFrame multi-horizon contient 4 enveloppes uniques "
        "(PERIN/PEE/PERECO/PERO)",
        sorted(df_pero["Enveloppe"].unique().tolist()) ==
        ["PEE", "PERECO", "PERIN", "PERO"],
        detail=f"observé: {sorted(df_pero['Enveloppe'].unique().tolist())}",
    )

    # SP26-4 : pas de logique économique conditionnelle UI :
    # PERO inactif (taux 0%) doit toujours apparaître dans le tableau
    # (C-Q1=α : neutralité totale, pas de masquage selon valeur)
    profil_pero_inactif = Profil()  # taux_cotisation_pero=0.0 par défaut
    trace_inactif = TraceAudit(regime="Test SP26 PERO inactif",
                               profil_resume="")
    res_inactif = allocation_receptacles(
        profil_pero_inactif, flux_disponible=5000.0, audit=trace_inactif,
    )
    df_inactif = extraire_tableau_multi_horizon(res_inactif)
    pero_lignes = df_inactif[df_inactif["Enveloppe"] == "PERO"]
    runner.check(
        "SP26-4 PERO inactif (taux 0%) reste affiché dans le DataFrame "
        "(C-Q1=α : neutralité, pas de masquage conditionnel UI)",
        len(pero_lignes) == 3,  # 3 horizons
        detail=f"lignes PERO observées: {len(pero_lignes)}",
    )

    # SP26-5 : aucun composant UI spécifique PERO dans composants_receptacles
    runner.check(
        "SP26-5 Aucun composant Streamlit spécifique PERO "
        "(directive SP26 : aucun composant spécifique)",
        ("def saisir_inputs_pero" not in composants_src
         and "def tableau_pero" not in composants_src
         and "def afficher_pero" not in composants_src
         and "def panneau_pero" not in composants_src),
        detail="composant dédié PERO détecté dans composants_receptacles.py",
    )

    # SP26-6 : page_receptacles.py n'a pas de logique conditionnelle PERO
    # (pas de `if pero` ou `if taux_cotisation_pero` modifiant l'affichage)
    runner.check(
        "SP26-6 page_receptacles.py : aucune logique conditionnelle "
        "d'affichage PERO (pas de masquage/grisage selon valeur)",
        # On vérifie l'absence des patterns conditionnels de masquage
        ("if pero" not in page_src.lower().replace("if pero =", "")
         and "hide_pero" not in page_src
         and "masquer_pero" not in page_src),
        detail="logique conditionnelle PERO détectée",
    )

    # SP26-7 : aucun wording interprétatif PERO dans les chaînes UI
    # On scanne les chaînes affichées à l'utilisateur dans page +
    # composants : « optimal », « meilleur », « avantageux » associé
    # à « PERO » serait une violation directe.
    import re as re_sp26
    wordings_interdits_pero = []
    for source, nom_fichier in [(page_src, "page_receptacles.py"),
                                 (composants_src, "composants_receptacles.py")]:
        for match in re_sp26.finditer(
            r'"[^"]*\b(PERO)\b[^"]*"', source,
        ):
            chaine = match.group(0)
            for mot_interdit in ["optimal", "meilleur", "avantageux",
                                 "performant", "idéal", "recommandé",
                                 "favorable", "intéressant"]:
                if mot_interdit.lower() in chaine.lower():
                    wordings_interdits_pero.append(
                        (nom_fichier, chaine[:80])
                    )
    runner.check(
        "SP26-7 Aucun wording interprétatif (optimal/meilleur/...) "
        "associé à PERO dans les chaînes UI",
        not wordings_interdits_pero,
        detail=f"violations: {wordings_interdits_pero[:3]}",
    )

    # Cas limite : DataFrame vide possible si horizons vides
    # (l'orchestrateur ne crash pas, l'adapter doit suivre)
    return runner.synthese("UI Réceptacles neutralité")


if __name__ == "__main__":
    sys.exit(main())
