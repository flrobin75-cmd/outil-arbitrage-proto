"""
test_strategy_receptacles.py — Test métier du module v1.1 réceptacles.

SP14 — scaffolding initial (assertions structurelles).

Pattern hérité de `test_mode_audit_strategy_*` : test indépendant qui
exerce la signature publique du module métier et valide ses contrats
**sans dépendre du framework PDF audit** (le test PDF audit dédié est
prévu en SP19).

Périmètre SP14 — Assertions structurelles uniquement
─────────────────────────────────────────────────────
Ce test vérifie en SP14 :

  - L'import propre des nouveaux modules `receptacles_*`
  - Les signatures publiques sont conformes à D-R5
  - Les dataclass produits respectent la structure D-R4
  - L'orchestrateur compose correctement (mocks SP14)
  - Les wordings transverses sont définis et utilisables
  - Aucune logique métier dans l'orchestrateur (D-R6)
  - Aucune étape `parent_id != None` produite (D-R10)

Le test est intentionnellement **structurel et léger** : il ne teste
PAS la justesse fiscale des calculs (qui n'existent pas encore — mocks
SP14). Les tests métier complets seront étoffés par SP15-SP17, et le
test PDF audit dédié (validation framework-compatibilité) par SP19.

Référence doctrinale : `ARCHITECTURE_RECEPTACLES.md` §8.3.

Usage : python3 test_strategy_receptacles.py
Exit code 0 si tous les contrôles passent.
"""

import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


# ============================================================
# RUNNER (pattern hérité des autres tests métier)
# ============================================================
class StructureRunner:
    """Runner d'assertions structurelles pour SP14."""

    def __init__(self):
        self.nb_ok = 0
        self.nb_ko = 0
        self.failures: list = []

    def check(self, label: str, condition: bool, detail: str = "") -> None:
        suffix = f"  [{detail}]" if detail and not condition else ""
        symbole = "✓" if condition else "✗"
        print(f"  {symbole} {label}{suffix}")
        if condition:
            self.nb_ok += 1
        else:
            self.nb_ko += 1
            self.failures.append(label + (f"  [{detail}]" if detail else ""))

    def section(self, titre: str) -> None:
        print()
        print("=" * 90)
        print(f"  {titre}")
        print("=" * 90)

    def synthese(self, nom_test: str) -> int:
        print()
        print("=" * 90)
        print("  SYNTHÈSE")
        print("=" * 90)
        print(f"  Contrôles OK     : {self.nb_ok}")
        print(f"  Contrôles KO     : {self.nb_ko}")
        print()
        if self.nb_ko == 0:
            print(f"  ✓ {nom_test} PASS")
            return 0
        else:
            print(f"  ✗ {nom_test} FAIL :")
            for f in self.failures:
                print(f"    - {f}")
            return 1


def main() -> int:
    print()
    print("=" * 90)
    print("  TEST STRUCTUREL v1.1 — Réceptacles (SP14 scaffolding)")
    print("=" * 90)

    runner = StructureRunner()

    # ============================================================
    # SECTION 1 — IMPORTS
    # ============================================================
    runner.section("1. Imports — Modules v1.1 scaffolding")

    try:
        import strategy.receptacles_wordings as wordings
        runner.check("1.1 Import 'strategy.receptacles_wordings' OK", True)
    except ImportError as exc:
        runner.check("1.1 Import 'strategy.receptacles_wordings' OK", False,
                     detail=str(exc))
        return runner.synthese("SP14 Réceptacles")

    try:
        import strategy.receptacles_orchestrateur as orch
        runner.check("1.2 Import 'strategy.receptacles_orchestrateur' OK", True)
    except ImportError as exc:
        runner.check("1.2 Import 'strategy.receptacles_orchestrateur' OK", False,
                     detail=str(exc))
        return runner.synthese("SP14 Réceptacles")

    # Vérification : le module existant `strategy.receptacles` n'est PAS
    # impacté (preuve qu'on n'a pas créé de conflit de nom)
    try:
        import strategy.receptacles as legacy
        runner.check("1.3 Module legacy 'strategy.receptacles' toujours importable",
                     hasattr(legacy, "est_accessible"))
    except ImportError:
        runner.check("1.3 Module legacy 'strategy.receptacles' toujours importable",
                     False, detail="module legacy cassé par SP14")

    # ============================================================
    # SECTION 2 — WORDINGS TRANSVERSES (D-R3)
    # ============================================================
    runner.section("2. Wordings transverses (D-R3, SP14)")

    runner.check("2.1 WORDING_REC_CONVENTION_RENDEMENT défini",
                 hasattr(wordings, "WORDING_REC_CONVENTION_RENDEMENT"))
    runner.check("2.2 WORDING_REC_DISCLAIMER_COMPARABILITE défini",
                 hasattr(wordings, "WORDING_REC_DISCLAIMER_COMPARABILITE"))
    runner.check("2.3 WORDING_REC_DISCLAIMER_PERIMETRE défini",
                 hasattr(wordings, "WORDING_REC_DISCLAIMER_PERIMETRE"))

    for nom in ("WORDING_REC_CONVENTION_RENDEMENT",
                "WORDING_REC_DISCLAIMER_COMPARABILITE",
                "WORDING_REC_DISCLAIMER_PERIMETRE"):
        w = getattr(wordings, nom)
        runner.check(f"2.4 {nom} est une chaîne ≥ 80 chars "
                     "(rendu en encadré, D-R3)",
                     isinstance(w, str) and len(w) >= 80,
                     detail=f"longueur observée: {len(w)}")

    # Convention de nommage : préfixe WORDING_REC_* pour transverse
    transverses = [n for n in wordings.__all__ if n.startswith("WORDING_REC_")]
    runner.check(f"2.5 Convention WORDING_REC_* respectée "
                 f"({len(transverses)} wordings transverses)",
                 len(transverses) == 3,
                 detail=f"observés: {transverses}")

    # ============================================================
    # SECTION 3 — DATACLASS HIÉRARCHIQUE (Q1=b)
    # ============================================================
    runner.section("3. Dataclass hiérarchique (Q1=b, D-R4)")

    runner.check("3.1 LigneHorizonReceptacle exposée",
                 hasattr(orch, "LigneHorizonReceptacle"))
    runner.check("3.2 ResultatAllocationEnveloppe exposée (parent)",
                 hasattr(orch, "ResultatAllocationEnveloppe"))
    runner.check("3.3 ResultatAllocationPerin exposée",
                 hasattr(orch, "ResultatAllocationPerin"))
    runner.check("3.4 ResultatAllocationPee exposée",
                 hasattr(orch, "ResultatAllocationPee"))
    runner.check("3.5 ResultatAllocationPereco exposée",
                 hasattr(orch, "ResultatAllocationPereco"))
    runner.check("3.6 ResultatAllocationReceptacles exposée (racine)",
                 hasattr(orch, "ResultatAllocationReceptacles"))

    # LigneHorizonReceptacle : 8 dimensions économiques + horizon
    ligne = orch.LigneHorizonReceptacle(horizon_annees=5)
    dimensions_attendues = {
        "horizon_annees", "flux_entrant_brut", "economie_fiscale_immediate",
        "effort_reel", "capital_projete", "fiscalite_sortie",
        "valeur_nette", "cout_entreprise", "disponibilite",
    }
    dimensions_observees = set(ligne.__dict__.keys())
    manquantes = dimensions_attendues - dimensions_observees
    runner.check(f"3.7 LigneHorizonReceptacle : 9 dimensions économiques "
                 "verrouillées (§2.3)",
                 not manquantes,
                 detail=f"manquantes: {manquantes}")

    # Héritage : 3 enveloppes héritent de ResultatAllocationEnveloppe
    runner.check("3.8 ResultatAllocationPerin hérite de "
                 "ResultatAllocationEnveloppe",
                 issubclass(orch.ResultatAllocationPerin,
                            orch.ResultatAllocationEnveloppe))
    runner.check("3.9 ResultatAllocationPee hérite",
                 issubclass(orch.ResultatAllocationPee,
                            orch.ResultatAllocationEnveloppe))
    runner.check("3.10 ResultatAllocationPereco hérite",
                 issubclass(orch.ResultatAllocationPereco,
                            orch.ResultatAllocationEnveloppe))

    # ============================================================
    # SECTION 4 — SIGNATURE PUBLIQUE STANDARDISÉE (D-R5)
    # ============================================================
    runner.section("4. Signature publique standardisée (D-R5)")

    runner.check("4.1 'allocation_receptacles' exposée",
                 hasattr(orch, "allocation_receptacles"))

    sig = inspect.signature(orch.allocation_receptacles)
    params_attendus = {"profil", "flux_disponible", "horizons", "audit"}
    params_observes = set(sig.parameters.keys())
    manquants = params_attendus - params_observes
    runner.check(f"4.2 Signature contient tous les paramètres D-R5",
                 not manquants, detail=f"manquants: {manquants}")

    # `profil` est positionnel, le reste keyword-only (cf. signature TNS)
    profil_param = sig.parameters.get("profil")
    runner.check("4.3 'profil' est positionnel ou positional-or-keyword",
                 profil_param.kind in (
                     inspect.Parameter.POSITIONAL_OR_KEYWORD,
                     inspect.Parameter.POSITIONAL_ONLY,
                 ))
    for p in ("flux_disponible", "horizons", "audit"):
        param = sig.parameters.get(p)
        runner.check(f"4.4 '{p}' est keyword-only (cohérence D-R5)",
                     param is not None and
                     param.kind == inspect.Parameter.KEYWORD_ONLY)

    # Pas de paramètre régime-spécifique (cohérence avec G2 framework)
    params_interdits = {"regime", "regime_name", "regime_type"}
    runner.check("4.5 Aucun paramètre régime-spécifique "
                 "(cohérence G2 framework)",
                 not (params_observes & params_interdits))

    # ============================================================
    # SECTION 5 — CONSTANTES TRANSVERSES
    # ============================================================
    runner.section("5. Constantes transverses (D-R9, D-R11)")

    runner.check("5.1 HORIZONS_DEFAUT == (5, 10, 20) (D-R9)",
                 orch.HORIZONS_DEFAUT == (5, 10, 20),
                 detail=f"observé: {orch.HORIZONS_DEFAUT}")
    runner.check("5.2 ENVELOPPES_V1_1 == ('PERIN', 'PEE', 'PERECO') (D-R11)",
                 orch.ENVELOPPES_V1_1 == ("PERIN", "PEE", "PERECO"),
                 detail=f"observé: {orch.ENVELOPPES_V1_1}")
    runner.check("5.3 RENDEMENT_NOMINAL_ANNUEL == 0.02 (D-R8)",
                 orch.RENDEMENT_NOMINAL_ANNUEL == 0.02,
                 detail=f"observé: {orch.RENDEMENT_NOMINAL_ANNUEL}")

    # ============================================================
    # SECTION 6 — ORCHESTRATEUR FONCTIONNEL (mock SP14)
    # ============================================================
    runner.section("6. Orchestrateur fonctionnel (mock SP14, Q3=c)")

    from core.profil import Profil
    from core.audit import TraceAudit

    profil = Profil()
    result = orch.allocation_receptacles(profil, flux_disponible=20000.0)
    runner.check("6.1 Appel sans audit retourne ResultatAllocationReceptacles",
                 isinstance(result, orch.ResultatAllocationReceptacles))
    runner.check("6.2 Résultat contient les 3 enveloppes",
                 result.perin is not None
                 and result.pee is not None
                 and result.pereco is not None)
    runner.check("6.3 flux_disponible préservé dans le résultat",
                 result.flux_disponible == 20000.0)
    runner.check("6.4 horizons par défaut appliqués si omis",
                 result.horizons == orch.HORIZONS_DEFAUT)
    runner.check("6.5 Chaque enveloppe a une ligne par horizon",
                 len(result.perin.lignes_par_horizon) == 3
                 and len(result.pee.lignes_par_horizon) == 3
                 and len(result.pereco.lignes_par_horizon) == 3)

    # Disclaimers permanents dans le résultat
    runner.check("6.6 disclaimer_perimetre attaché au résultat",
                 result.disclaimer_perimetre == wordings.WORDING_REC_DISCLAIMER_PERIMETRE)
    runner.check("6.7 disclaimer_comparabilite attaché",
                 result.disclaimer_comparabilite == wordings.WORDING_REC_DISCLAIMER_COMPARABILITE)
    runner.check("6.8 convention_rendement attachée",
                 result.convention_rendement == wordings.WORDING_REC_CONVENTION_RENDEMENT)

    # ============================================================
    # SECTION 7 — INSTRUMENTATION TRACE AUDIT
    # ============================================================
    runner.section("7. Instrumentation trace audit")

    trace = TraceAudit(regime="Réceptacles", profil_resume="Test SP14")
    result = orch.allocation_receptacles(profil, flux_disponible=20000.0, audit=trace)

    runner.check("7.1 Étapes méta présentes à la racine de la trace",
                 len(trace.etapes) >= 5,
                 detail=f"observé: {len(trace.etapes)}")

    codes_attendus_meta = {
        "REC_NB_ENVELOPPES", "REC_FLUX_DISPONIBLE",
        "REC_HORIZONS_NB", "REC_RENDEMENT_HYPOTHESE",
        "REC_DISCLAIMERS_NB",
    }
    codes_observes = {e.code for e in trace.etapes}
    manquants = codes_attendus_meta - codes_observes
    runner.check("7.2 5 codes méta REC_* présents à la racine",
                 not manquants, detail=f"manquants: {manquants}")

    sous_traces = list(trace.noms_sous_traces())
    runner.check("7.3 4 sous-traces attachées (ligne_perin/pee/pereco/pero, SP25)",
                 sous_traces == ["ligne_perin", "ligne_pee", "ligne_pereco", "ligne_pero"],
                 detail=f"observé: {sous_traces}")

    # ============================================================
    # SECTION 8 — PRÉSERVATION G4 (D-R10)
    # ============================================================
    runner.section("8. Préservation G4 — aucune étape parent_id != None (D-R10)")

    def _toutes_etapes(t):
        for e in t.etapes:
            yield e
        for _, sub in t.sous_traces.items():
            yield from _toutes_etapes(sub)

    nb_etapes_total = sum(1 for _ in _toutes_etapes(trace))
    nb_etapes_filles = sum(
        1 for e in _toutes_etapes(trace) if e.parent_id is not None
    )
    runner.check(f"8.1 Aucune étape fille produite "
                 f"(0/{nb_etapes_total} attendu, D-R10)",
                 nb_etapes_filles == 0,
                 detail=f"observé: {nb_etapes_filles} étapes filles")

    # ============================================================
    # SECTION 9 — FRAMEWORK-COMPATIBILITÉ (PDF audit rendable)
    # ============================================================
    runner.section("9. Framework-compatibilité — PDF audit rendable")

    from ui.pdf_audit_export import generer_pdf_audit
    try:
        pdf = generer_pdf_audit(
            trace, cabinet_nom="Cabinet TestCo",
            client_nom="M. Dupont", expert_comptable="Mme Martin",
            doctrine_date="20/05/2026",
        )
        crash = False
    except Exception as exc:  # noqa: BLE001
        pdf = b""
        crash = True
        crash_msg = f"{type(exc).__name__}: {exc}"

    runner.check("9.1 generer_pdf_audit absorbe la trace v1.1 sans erreur",
                 not crash,
                 detail=crash_msg if crash else "")

    if not crash:
        runner.check("9.2 PDF commence par '%PDF-'", pdf.startswith(b"%PDF-"))
        runner.check("9.3 PDF termine par '%%EOF'", b"%%EOF" in pdf[-30:])
        runner.check("9.4 PDF de taille ≥ 5 ko",
                     len(pdf) >= 5 * 1024,
                     detail=f"taille observée: {len(pdf)} bytes")

    # ============================================================
    # SECTION 10 — ORCHESTRATEUR PASSIF (D-R6, adapté SP15)
    # ============================================================
    runner.section("10. Orchestrateur passif — pas de logique métier (D-R6)")

    # Évolution SP15 :
    #
    # En SP14, les 3 modules enveloppe étaient mockés. La preuve
    # d'orchestrateur passif consistait à vérifier que les résultats
    # étaient identiques quel que soit le flux (les mocks retournaient
    # zéro). Cette preuve n'est plus pertinente dès qu'un module métier
    # réel est branché (SP15 = PERIN).
    #
    # SP15 reformule le test : l'orchestrateur reste passif si :
    #   (a) Il ne contient aucune transformation des résultats reçus.
    #   (b) Le flux_disponible est passé tel quel aux modules.
    #   (c) Aucune décision métier (tri, classement, recommandation)
    #       n'est prise par l'orchestrateur.
    #   (d) Pour les modules encore mockés (PEE/PERECO en SP15), les
    #       valeurs restent identiques quel que soit le flux (preuve
    #       que l'orchestrateur ne les calcule pas lui-même).

    # (a) Cohérence : les ResultatAllocation* sont bien des références
    # directes aux retours des modules, pas des copies/transformations.
    #
    # Note : on utilise des flux tous deux SOUS le plafond annuel PERIN
    # minimum (4806 € = 10 % PASS), sinon le bornage les ramènerait
    # tous deux à la même valeur — ce qui ne prouverait pas qu'on a
    # bien un calcul délégué. Avec 2k€ et 4k€, le bornage ne s'applique
    # pas et les calculs économiques diffèrent strictement.
    r1 = orch.allocation_receptacles(profil, flux_disponible=2000.0)
    r2 = orch.allocation_receptacles(profil, flux_disponible=4000.0)
    runner.check("10.1 PERIN réel : valeurs dépendent du flux "
                 "(preuve calcul délégué au module, pas à l'orchestrateur)",
                 r1.perin.lignes_par_horizon[0].flux_entrant_brut
                 != r2.perin.lignes_par_horizon[0].flux_entrant_brut,
                 detail=f"r1 brut={r1.perin.lignes_par_horizon[0].flux_entrant_brut}, "
                        f"r2 brut={r2.perin.lignes_par_horizon[0].flux_entrant_brut}")

    # (b) flux_disponible préservé : input → output direct
    r3 = orch.allocation_receptacles(profil, flux_disponible=10000.0)
    r4 = orch.allocation_receptacles(profil, flux_disponible=50000.0)
    runner.check("10.2 flux_disponible préservé tel quel "
                 "(pas de transformation orchestrateur)",
                 r3.flux_disponible == 10000.0 and r4.flux_disponible == 50000.0)

    # (c) Aucun champ « recommandation » ou « classement » dans le résultat
    # (preuve absence de décision métier)
    champs_resultat = set(r1.__dataclass_fields__.keys())
    champs_interdits = {"meilleur_enveloppe", "enveloppe_recommandee",
                        "classement", "ranking", "score"}
    runner.check("10.3 Aucun champ de classement/recommandation dans "
                 "ResultatAllocationReceptacles (D-R12 : pas de "
                 "dimensionneur, pas de prescription)",
                 not (champs_resultat & champs_interdits),
                 detail=f"observés interdits: "
                        f"{champs_resultat & champs_interdits}")

    # (d) Tous les modules sont désormais réels depuis SP17. La preuve
    # « valeurs identiques quel que soit le flux » n'a plus d'enveloppe
    # mockée à pointer. À la place, on vérifie que chaque enveloppe
    # produit des valeurs dépendantes du flux (preuve de calcul réel).
    runner.check("10.4 PEE réel SP16 : valeurs dépendent du flux "
                 "(comme PERIN, preuve calcul délégué au module)",
                 r1.pee.lignes_par_horizon[0].flux_entrant_brut
                 != r2.pee.lignes_par_horizon[0].flux_entrant_brut,
                 detail=f"r1 brut={r1.pee.lignes_par_horizon[0].flux_entrant_brut}, "
                        f"r2 brut={r2.pee.lignes_par_horizon[0].flux_entrant_brut}")
    runner.check("10.5 PERECO réel SP17 : valeurs dépendent du flux "
                 "(tous les modules sont maintenant réels)",
                 r1.pereco.lignes_par_horizon[0].flux_entrant_brut
                 != r2.pereco.lignes_par_horizon[0].flux_entrant_brut,
                 detail=f"r1 brut={r1.pereco.lignes_par_horizon[0].flux_entrant_brut}, "
                        f"r2 brut={r2.pereco.lignes_par_horizon[0].flux_entrant_brut}")

    # ============================================================
    # SECTION 11 — HORIZONS PARAMÉTRABLES (D-R9)
    # ============================================================
    runner.section("11. Horizons paramétrables (D-R9)")

    # Test avec horizons non-standards
    result_custom = orch.allocation_receptacles(
        profil, flux_disponible=15000.0, horizons=(3, 7, 15),
    )
    runner.check("11.1 Horizons custom (3, 7, 15) acceptés",
                 result_custom.horizons == (3, 7, 15))
    runner.check("11.2 Lignes par horizon reflètent les horizons custom",
                 [l.horizon_annees for l in result_custom.perin.lignes_par_horizon]
                 == [3, 7, 15])

    # ============================================================
    # SECTION 12 — MODULE PERIN RÉEL (SP15, périmètre Q1=b)
    # ============================================================
    runner.section("12. Module PERIN réel (SP15)")

    try:
        from strategy.receptacles_perin import (
            allocation_perin, obtenir_plafond_perin, obtenir_tmi_dirigeant,
            est_eligible_perin, TX_PFU_GAINS_PERIN, TX_PS_GAINS_PERIN,
        )
        runner.check("12.1 Module receptacles_perin importable + "
                     "providers + constantes exposées", True)
    except ImportError as exc:
        runner.check("12.1 Module receptacles_perin importable",
                     False, detail=str(exc))
        return runner.synthese("SP15 Réceptacles PERIN")

    # Providers doctrinaux (G-2, Q8=a)
    runner.check("12.2 Provider obtenir_plafond_perin retourne float ≥ 0",
                 isinstance(obtenir_plafond_perin(profil), float)
                 and obtenir_plafond_perin(profil) >= 0)
    runner.check("12.3 Provider obtenir_tmi_dirigeant retourne ratio ∈ [0, 1]",
                 0.0 <= obtenir_tmi_dirigeant(profil) <= 1.0)
    runner.check("12.4 Provider est_eligible_perin retourne True (v1.1)",
                 est_eligible_perin(profil) is True)

    # Constantes fiscalité sortie
    runner.check("12.5 TX_PFU_GAINS_PERIN == 0.30 (12,8 % IR + 17,2 % PS)",
                 TX_PFU_GAINS_PERIN == 0.30,
                 detail=f"observé: {TX_PFU_GAINS_PERIN}")
    runner.check("12.6 TX_PS_GAINS_PERIN == 0.172 (17,2 %)",
                 TX_PS_GAINS_PERIN == 0.172,
                 detail=f"observé: {TX_PS_GAINS_PERIN}")

    # Signature allocation_perin conforme D-R5
    sig_perin = inspect.signature(allocation_perin)
    params_perin = set(sig_perin.parameters.keys())
    runner.check("12.7 allocation_perin a la signature D-R5 standardisée",
                 params_perin >= {"profil", "flux_disponible", "horizons", "audit"})

    # Calcul économique : flux 10 000 € (bornable au plafond)
    result_perin = allocation_perin(profil, flux_disponible=10000.0)
    runner.check("12.8 allocation_perin retourne ResultatAllocationPerin",
                 isinstance(result_perin, orch.ResultatAllocationPerin))
    runner.check("12.9 Résultat contient 3 lignes (3 horizons par défaut)",
                 len(result_perin.lignes_par_horizon) == 3)

    # Cohérence économique : flux_entrant_brut > 0 si éligible et plafond > 0
    plafond = obtenir_plafond_perin(profil)
    if plafond > 0:
        runner.check("12.10 Flux entrant brut > 0 (plafond > 0 et flux > 0)",
                     result_perin.lignes_par_horizon[0].flux_entrant_brut > 0)
    else:
        runner.check("12.10 Flux entrant brut == 0 (plafond == 0)",
                     result_perin.lignes_par_horizon[0].flux_entrant_brut == 0)

    # Bornage par plafond : pour un flux > plafond, on borne
    ligne_h5 = result_perin.lignes_par_horizon[0]
    runner.check("12.11 Flux entrant brut ≤ plafond annuel (bornage)",
                 ligne_h5.flux_entrant_brut <= plafond + 0.01)

    # Invariants algébriques (validés par __post_init__ silencieusement
    # mais on les vérifie en assertion explicite ici aussi)
    if ligne_h5.flux_entrant_brut > 0:
        attendu_effort = (ligne_h5.flux_entrant_brut
                          - ligne_h5.economie_fiscale_immediate)
        runner.check("12.12 Invariant : effort_réel == flux_brut − éco_fiscale",
                     abs(ligne_h5.effort_reel - attendu_effort) <= 0.01,
                     detail=f"effort={ligne_h5.effort_reel}, attendu={attendu_effort}")

        attendu_nette = ligne_h5.capital_projete - ligne_h5.fiscalite_sortie
        runner.check("12.13 Invariant : valeur_nette == capital_projeté − fisc_sortie",
                     abs(ligne_h5.valeur_nette - attendu_nette) <= 0.01,
                     detail=f"net={ligne_h5.valeur_nette}, attendu={attendu_nette}")

    # Capitalisation strictement croissante avec l'horizon
    capitaux = [l.capital_projete for l in result_perin.lignes_par_horizon]
    if ligne_h5.flux_entrant_brut > 0:
        runner.check("12.14 Capital projeté croissant avec l'horizon "
                     "(capitalisation positive)",
                     capitaux[0] < capitaux[1] < capitaux[2],
                     detail=f"observés: {capitaux}")

    # Coût entreprise nul (PERIN individuel)
    runner.check("12.15 Coût entreprise == 0 sur tous horizons "
                 "(PERIN est un produit individuel)",
                 all(l.cout_entreprise == 0.0
                     for l in result_perin.lignes_par_horizon))

    # Disponibilité renseignée (texte qualitatif)
    runner.check("12.16 Disponibilité renseignée sur chaque horizon",
                 all(l.disponibilite for l in result_perin.lignes_par_horizon))

    # Préservation D-R10 : aucune étape parent_id != None dans la sous-trace
    trace_perin = TraceAudit(regime="PERIN test", profil_resume="")
    allocation_perin(profil, flux_disponible=10000.0, audit=trace_perin)
    etapes_filles = sum(1 for e in _toutes_etapes(trace_perin)
                        if e.parent_id is not None)
    runner.check("12.17 Aucune étape fille dans la trace PERIN (D-R10)",
                 etapes_filles == 0,
                 detail=f"observé: {etapes_filles}")

    # Volumétrie cohérente avec Q3=b (~25-30 étapes)
    nb_etapes_perin = sum(1 for _ in _toutes_etapes(trace_perin))
    runner.check(f"12.18 Volumétrie PERIN ≈ 25-30 étapes (Q3=b) "
                 f"— observé: {nb_etapes_perin}",
                 20 <= nb_etapes_perin <= 35)

    # ============================================================
    # SECTION 13 — MODULE PEE RÉEL (SP16, périmètre Q1=b)
    # ============================================================
    runner.section("13. Module PEE réel (SP16)")

    try:
        from strategy.receptacles_pee import (
            allocation_pee, obtenir_taux_abondement_pee,
            obtenir_plafond_abondement_pee, est_eligible_pee,
            PLAFOND_ABONDEMENT_PEE, TX_CSG_CRDS_ABONDEMENT_PEE,
            TX_PS_GAINS_PEE,
        )
        runner.check("13.1 Module receptacles_pee importable + "
                     "providers + constantes exposées", True)
    except ImportError as exc:
        runner.check("13.1 Module receptacles_pee importable",
                     False, detail=str(exc))
        return runner.synthese("SP16 Réceptacles PEE")

    # Providers doctrinaux (Q2=c, G-2)
    runner.check("13.2 Provider obtenir_taux_abondement_pee retourne float ≥ 0",
                 isinstance(obtenir_taux_abondement_pee(profil), float)
                 and obtenir_taux_abondement_pee(profil) >= 0)
    runner.check("13.3 Provider obtenir_taux_abondement_pee fallback 100 %",
                 obtenir_taux_abondement_pee(profil) == 1.0)
    runner.check("13.4 Provider obtenir_plafond_abondement_pee == 8 % PASS",
                 abs(obtenir_plafond_abondement_pee(profil)
                     - 0.08 * 48060) < 0.01)
    runner.check("13.5 Provider est_eligible_pee retourne True (v1.1)",
                 est_eligible_pee(profil) is True)

    # Constantes fiscalité
    runner.check("13.6 TX_CSG_CRDS_ABONDEMENT_PEE == 0.097 (9,7 %)",
                 TX_CSG_CRDS_ABONDEMENT_PEE == 0.097,
                 detail=f"observé: {TX_CSG_CRDS_ABONDEMENT_PEE}")
    runner.check("13.7 TX_PS_GAINS_PEE == 0.172 (17,2 % sortie)",
                 TX_PS_GAINS_PEE == 0.172,
                 detail=f"observé: {TX_PS_GAINS_PEE}")
    runner.check("13.8 PLAFOND_ABONDEMENT_PEE == 3 844,80 € (8 % PASS 2026)",
                 abs(PLAFOND_ABONDEMENT_PEE - 3844.80) < 0.01,
                 detail=f"observé: {PLAFOND_ABONDEMENT_PEE}")

    # Signature allocation_pee conforme D-R5
    sig_pee = inspect.signature(allocation_pee)
    params_pee = set(sig_pee.parameters.keys())
    runner.check("13.9 allocation_pee a la signature D-R5 standardisée",
                 params_pee >= {"profil", "flux_disponible", "horizons", "audit"})

    # Calcul économique : flux 5 000 €
    result_pee = allocation_pee(profil, flux_disponible=5000.0)
    runner.check("13.10 allocation_pee retourne ResultatAllocationPee",
                 isinstance(result_pee, orch.ResultatAllocationPee))
    runner.check("13.11 Résultat contient 3 lignes (3 horizons par défaut)",
                 len(result_pee.lignes_par_horizon) == 3)

    ligne_h5_pee = result_pee.lignes_par_horizon[0]

    # Sémantique SP16 : flux_entrant_brut == flux salarié (Q4=III)
    runner.check("13.12 flux_entrant_brut == flux salarié (Q4=III : "
                 "abondement est instrumenté à part, pas inclus ici)",
                 ligne_h5_pee.flux_entrant_brut == 5000.0,
                 detail=f"observé: {ligne_h5_pee.flux_entrant_brut}")

    # Sémantique SP16 : economie_fiscale_immediate == 0 pour PEE (Q5=ii)
    runner.check("13.13 economie_fiscale_immediate == 0 pour PEE "
                 "(Q5=ii : pas de déductibilité IR à l'entrée)",
                 ligne_h5_pee.economie_fiscale_immediate == 0.0)

    # Effort réel == flux salarié (l'abondement est un cadeau, pas un effort)
    runner.check("13.14 effort_reel == flux salarié "
                 "(l'abondement n'augmente pas l'effort du salarié)",
                 ligne_h5_pee.effort_reel == 5000.0)

    # Coût entreprise > 0 (PEE est un produit employeur, contrairement à PERIN)
    runner.check("13.15 cout_entreprise > 0 pour PEE "
                 "(l'employeur a versé un abondement brut)",
                 ligne_h5_pee.cout_entreprise > 0,
                 detail=f"observé: {ligne_h5_pee.cout_entreprise}")

    # Coût entreprise plafonné par PLAFOND_ABONDEMENT_PEE
    runner.check("13.16 cout_entreprise ≤ plafond légal abondement PEE",
                 ligne_h5_pee.cout_entreprise <= PLAFOND_ABONDEMENT_PEE + 0.01,
                 detail=f"observé: {ligne_h5_pee.cout_entreprise}, "
                        f"plafond: {PLAFOND_ABONDEMENT_PEE}")

    # Capital projeté > flux salarié × capitalisation seule
    # (preuve que l'abondement gonfle le capital)
    capital_si_pas_abondement = 5000.0 * (1.02 ** 5)
    runner.check("13.17 Capital projeté > capitalisation flux salarié seul "
                 "(preuve effet abondement)",
                 ligne_h5_pee.capital_projete > capital_si_pas_abondement + 0.01,
                 detail=f"capital observé: {ligne_h5_pee.capital_projete}, "
                        f"capitalisation salarié seul: {capital_si_pas_abondement:.2f}")

    # Invariants algébriques (déjà validés par __post_init__ silencieusement)
    attendu_effort = (ligne_h5_pee.flux_entrant_brut
                      - ligne_h5_pee.economie_fiscale_immediate)
    runner.check("13.18 Invariant : effort_réel == flux_brut − éco_fiscale",
                 abs(ligne_h5_pee.effort_reel - attendu_effort) <= 0.01)
    attendu_nette = ligne_h5_pee.capital_projete - ligne_h5_pee.fiscalite_sortie
    runner.check("13.19 Invariant : valeur_nette == capital_projeté − fisc_sortie",
                 abs(ligne_h5_pee.valeur_nette - attendu_nette) <= 0.01)

    # Capitalisation croissante avec l'horizon
    capitaux_pee = [l.capital_projete for l in result_pee.lignes_par_horizon]
    runner.check("13.20 Capital projeté croissant avec l'horizon (PEE)",
                 capitaux_pee[0] < capitaux_pee[1] < capitaux_pee[2],
                 detail=f"observés: {capitaux_pee}")

    # Disponibilité renseignée et explicite (5 ans)
    runner.check("13.21 Disponibilité renseignée et mentionne 5 ans",
                 all("5 ans" in l.disponibilite
                     for l in result_pee.lignes_par_horizon))

    # Préservation D-R10 : aucune étape parent_id != None
    trace_pee = TraceAudit(regime="PEE test", profil_resume="")
    allocation_pee(profil, flux_disponible=5000.0, audit=trace_pee)
    etapes_filles_pee = sum(1 for e in _toutes_etapes(trace_pee)
                            if e.parent_id is not None)
    runner.check("13.22 Aucune étape fille dans la trace PEE (D-R10)",
                 etapes_filles_pee == 0,
                 detail=f"observé: {etapes_filles_pee}")

    # Volumétrie : PEE a plus d'étapes que PERIN (décomposition abondement)
    nb_etapes_pee = sum(1 for _ in _toutes_etapes(trace_pee))
    runner.check(f"13.23 Volumétrie PEE ≈ 30-40 étapes "
                 f"(décomposition abondement) — observé: {nb_etapes_pee}",
                 25 <= nb_etapes_pee <= 45)

    # Comparabilité cross-enveloppes (le sujet structurant SP16)
    # PERIN et PEE produisent des LigneHorizonReceptacle avec les mêmes
    # champs. La comparaison cabinet doit pouvoir se faire colonne par
    # colonne sans cast.
    perin_h5 = result_perin.lignes_par_horizon[0]
    pee_h5 = result_pee.lignes_par_horizon[0]
    runner.check("13.24 PERIN et PEE produisent le même type LigneHorizonReceptacle "
                 "(comparabilité dataclass)",
                 type(perin_h5) is type(pee_h5))
    runner.check("13.25 Champs identiques entre PERIN et PEE "
                 "(même 8 dimensions économiques)",
                 set(perin_h5.__dict__.keys()) == set(pee_h5.__dict__.keys()))

    # ============================================================
    # SECTION 14 — MODULE PERECO RÉEL (SP17, périmètre Q1=b hybride)
    # ============================================================
    runner.section("14. Module PERECO réel (SP17 — hybride PERIN+PEE)")

    try:
        from strategy.receptacles_pereco import (
            allocation_pereco,
            obtenir_plafond_pereco, obtenir_taux_abondement_pereco,
            obtenir_plafond_abondement_pereco, est_eligible_pereco,
            PLAFOND_ABONDEMENT_PERECO, TX_CSG_CRDS_ABONDEMENT_PERECO,
            TX_PFU_GAINS_PERECO,
        )
        runner.check("14.1 Module receptacles_pereco importable + "
                     "providers + constantes exposées", True)
    except ImportError as exc:
        runner.check("14.1 Module receptacles_pereco importable",
                     False, detail=str(exc))
        return runner.synthese("SP17 Réceptacles PERECO")

    # Providers doctrinaux (G-2)
    runner.check("14.2 Provider obtenir_plafond_pereco = plafond PERIN "
                 "(art. 154 bis identique)",
                 obtenir_plafond_pereco(profil)
                 == obtenir_plafond_perin(profil))
    runner.check("14.3 Provider obtenir_taux_abondement_pereco fallback 100 %",
                 obtenir_taux_abondement_pereco(profil) == 1.0)
    runner.check("14.4 Provider obtenir_plafond_abondement_pereco = 8 % PASS "
                 "(cohérence v1.1 avec PEE)",
                 abs(obtenir_plafond_abondement_pereco(profil)
                     - 0.08 * 48060) < 0.01)
    runner.check("14.5 Provider est_eligible_pereco retourne True (v1.1)",
                 est_eligible_pereco(profil) is True)

    # Constantes hybrides : abondement PEE + PFU PERIN
    runner.check("14.6 PLAFOND_ABONDEMENT_PERECO = PLAFOND_ABONDEMENT_PEE "
                 "(cohérence v1.1)",
                 PLAFOND_ABONDEMENT_PERECO == PLAFOND_ABONDEMENT_PEE)
    runner.check("14.7 TX_CSG_CRDS_ABONDEMENT_PERECO = TX_CSG_CRDS_ABONDEMENT_PEE "
                 "(9,7 % identique)",
                 TX_CSG_CRDS_ABONDEMENT_PERECO == TX_CSG_CRDS_ABONDEMENT_PEE)
    runner.check("14.8 TX_PFU_GAINS_PERECO == 0.30 (logique PERIN sur gains)",
                 TX_PFU_GAINS_PERECO == 0.30,
                 detail=f"observé: {TX_PFU_GAINS_PERECO}")

    # Signature D-R5
    sig_pereco = inspect.signature(allocation_pereco)
    params_pereco = set(sig_pereco.parameters.keys())
    runner.check("14.9 allocation_pereco a la signature D-R5 standardisée",
                 params_pereco >= {"profil", "flux_disponible", "horizons", "audit"})

    # Calcul économique : flux 5 000 €
    result_pereco = allocation_pereco(profil, flux_disponible=5000.0)
    runner.check("14.10 allocation_pereco retourne ResultatAllocationPereco",
                 isinstance(result_pereco, orch.ResultatAllocationPereco))
    runner.check("14.11 Résultat contient 3 lignes (3 horizons par défaut)",
                 len(result_pereco.lignes_par_horizon) == 3)

    ligne_h5_pereco = result_pereco.lignes_par_horizon[0]

    # Sémantique hybride Q2=γ : flux_entrant_brut == flux salarié borné par plafond
    plafond_pereco = obtenir_plafond_pereco(profil)
    runner.check("14.12 flux_entrant_brut ≤ plafond PERIN (= plafond PERECO)",
                 ligne_h5_pereco.flux_entrant_brut <= plafond_pereco + 0.01,
                 detail=f"observé: {ligne_h5_pereco.flux_entrant_brut}, "
                        f"plafond: {plafond_pereco}")

    # Pattern PERIN : economie_fiscale_immediate > 0 (déduction IR)
    # Distingue PERECO du PEE où cette valeur == 0
    runner.check("14.13 economie_fiscale_immediate > 0 pour PERECO "
                 "(Q2=γ : déductibilité IR héritée de PERIN, "
                 "PAS de PEE où ce champ est à zéro)",
                 ligne_h5_pereco.economie_fiscale_immediate > 0,
                 detail=f"observé: {ligne_h5_pereco.economie_fiscale_immediate}")

    # Pattern PEE : cout_entreprise > 0 (abondement)
    # Distingue PERECO du PERIN où cette valeur == 0
    runner.check("14.14 cout_entreprise > 0 pour PERECO "
                 "(Q2=γ : abondement employeur hérité de PEE, "
                 "PAS de PERIN où ce champ est à zéro)",
                 ligne_h5_pereco.cout_entreprise > 0,
                 detail=f"observé: {ligne_h5_pereco.cout_entreprise}")

    # Invariants algébriques (déjà validés par __post_init__ silencieusement)
    attendu_effort = (ligne_h5_pereco.flux_entrant_brut
                      - ligne_h5_pereco.economie_fiscale_immediate)
    runner.check("14.15 Invariant : effort_réel == flux_brut − éco_fiscale",
                 abs(ligne_h5_pereco.effort_reel - attendu_effort) <= 0.01)
    attendu_nette = (ligne_h5_pereco.capital_projete
                     - ligne_h5_pereco.fiscalite_sortie)
    runner.check("14.16 Invariant : valeur_nette == capital_projeté − fisc_sortie",
                 abs(ligne_h5_pereco.valeur_nette - attendu_nette) <= 0.01)

    # Capital projeté croissant
    capitaux_pereco = [l.capital_projete
                       for l in result_pereco.lignes_par_horizon]
    runner.check("14.17 Capital projeté croissant avec l'horizon (PERECO)",
                 capitaux_pereco[0] < capitaux_pereco[1] < capitaux_pereco[2])

    # Disponibilité : retraite (pas 5 ans comme PEE)
    runner.check("14.18 Disponibilité PERECO mentionne 'retraite' "
                 "(pas '5 ans' comme PEE)",
                 all("retraite" in l.disponibilite.lower()
                     for l in result_pereco.lignes_par_horizon))

    # Préservation D-R10
    trace_pereco = TraceAudit(regime="PERECO test", profil_resume="")
    allocation_pereco(profil, flux_disponible=5000.0, audit=trace_pereco)
    etapes_filles_pereco = sum(1 for e in _toutes_etapes(trace_pereco)
                               if e.parent_id is not None)
    runner.check("14.19 Aucune étape fille dans la trace PERECO (D-R10)",
                 etapes_filles_pereco == 0)

    # Volumétrie PERECO : la plus élevée (combine PERIN + PEE)
    nb_etapes_pereco = sum(1 for _ in _toutes_etapes(trace_pereco))
    runner.check(f"14.20 Volumétrie PERECO ≈ 35-50 étapes "
                 f"(hybride PERIN+PEE) — observé: {nb_etapes_pereco}",
                 30 <= nb_etapes_pereco <= 55)

    # ============================================================
    # SECTION 15 — COMPARABILITÉ CROSS-ENVELOPPES (Q2=γ orthogonalité)
    # ============================================================
    runner.section("15. Comparabilité cross-enveloppes (3 enveloppes orthogonales)")

    # Test du tableau doctrinal transverse (cf. votre apport SP17)
    # Pour le même profil et le même flux, les 3 enveloppes produisent
    # des LigneHorizonReceptacle structurellement identiques mais
    # sémantiquement distinctes.
    pereco_h5 = result_pereco.lignes_par_horizon[0]
    perin_h5 = result_perin.lignes_par_horizon[0]
    pee_h5 = result_pee.lignes_par_horizon[0]

    # Type identique (dataclass commun)
    runner.check("15.1 PERIN, PEE, PERECO produisent le même type "
                 "LigneHorizonReceptacle",
                 type(perin_h5) is type(pee_h5) is type(pereco_h5))

    # Champs identiques (8 dimensions)
    champs_perin = set(perin_h5.__dict__.keys())
    champs_pee = set(pee_h5.__dict__.keys())
    champs_pereco = set(pereco_h5.__dict__.keys())
    runner.check("15.2 Champs strictement identiques entre les 3 enveloppes",
                 champs_perin == champs_pee == champs_pereco)

    # Tableau doctrinal : déductibilité IR (PERIN ✓ / PEE ✗ / PERECO ✓)
    runner.check("15.3 Tableau doctrinal — Déductibilité IR : "
                 "PERIN > 0, PEE == 0, PERECO > 0",
                 perin_h5.economie_fiscale_immediate > 0
                 and pee_h5.economie_fiscale_immediate == 0
                 and pereco_h5.economie_fiscale_immediate > 0)

    # Tableau doctrinal : abondement employeur (PERIN ✗ / PEE ✓ / PERECO ✓)
    runner.check("15.4 Tableau doctrinal — Abondement employeur : "
                 "PERIN == 0, PEE > 0, PERECO > 0",
                 perin_h5.cout_entreprise == 0
                 and pee_h5.cout_entreprise > 0
                 and pereco_h5.cout_entreprise > 0)

    # Tableau doctrinal : disponibilité (PERIN retraite / PEE 5 ans / PERECO retraite)
    runner.check("15.5 Tableau doctrinal — Disponibilité : "
                 "PERIN retraite, PEE 5 ans, PERECO retraite",
                 "retraite" in perin_h5.disponibilite.lower()
                 and "5 ans" in pee_h5.disponibilite
                 and "retraite" in pereco_h5.disponibilite.lower())

    # Orthogonalité : PERIN et PERECO ont logique IR similaire, PEE et PERECO ont
    # logique abondement similaire
    runner.check("15.6 Orthogonalité — PERIN et PERECO ont éco_fiscale > 0, "
                 "PEE n'en a pas",
                 perin_h5.economie_fiscale_immediate > 0
                 and pereco_h5.economie_fiscale_immediate > 0
                 and pee_h5.economie_fiscale_immediate == 0)
    runner.check("15.7 Orthogonalité — PEE et PERECO ont coût entreprise > 0, "
                 "PERIN n'en a pas",
                 pee_h5.cout_entreprise > 0
                 and pereco_h5.cout_entreprise > 0
                 and perin_h5.cout_entreprise == 0)

    # ============================================================
    # SECTION 16 — ÉTAPES RÉCAPITULATIVES CROSS-ENVELOPPES (SP18, Q1=c)
    # ============================================================
    runner.section("16. Étapes récapitulatives orchestrateur (SP18)")

    # On régénère une trace via l'orchestrateur pour observer les
    # étapes récapitulatives SP18
    trace_orch = TraceAudit(regime="Test SP18", profil_resume="Récap")
    result_orch = orch.allocation_receptacles(
        profil, flux_disponible=5000.0, audit=trace_orch,
    )

    # 16.1 Présence des 9 codes RECAP attendus (3 dimensions × 3 horizons)
    codes_recap_attendus = {
        f"REC_RECAP_{dim}_{h}ANS"
        for dim in ["VALEUR_NETTE", "EFFORT_REEL", "COUT_ENTREPRISE"]
        for h in [5, 10, 20]
    }
    codes_recap_observes = {
        e.code for e in trace_orch.etapes
        if e.code.startswith("REC_RECAP_")
    }
    manquants_recap = codes_recap_attendus - codes_recap_observes
    runner.check("16.1 9 codes RECAP attendus présents au niveau racine",
                 not manquants_recap,
                 detail=f"manquants: {manquants_recap}")

    # 16.2 Préservation D-R10 : toutes les étapes RECAP sont au niveau racine
    etapes_recap_racine = [
        e for e in trace_orch.etapes if e.code.startswith("REC_RECAP_")
    ]
    runner.check("16.2 Toutes les étapes RECAP sont au niveau racine "
                 "(D-R10 préservée)",
                 all(e.parent_id is None for e in etapes_recap_racine),
                 detail=f"observées: {len(etapes_recap_racine)} étapes RECAP")

    # 16.3 Stabilité d'ordre stricte PERIN → PEE → PERECO dans les hypothèses
    # Contrainte SP18 utilisateur : tous les codes RECAP doivent avoir leurs
    # clés d'hypothèses dans cet ordre exact pour les 3 enveloppes.
    erreurs_ordre = []
    for etape in etapes_recap_racine:
        cles_enveloppes = [
            k for k in etape.hypotheses.keys()
            if any(env in k for env in ["PERIN", "PEE", "PERECO"])
        ]
        # Vérifier l'ordre : PERIN avant PEE, PEE avant PERECO
        idx_perin = next((i for i, k in enumerate(cles_enveloppes)
                          if "PERIN" in k), -1)
        idx_pee = next((i for i, k in enumerate(cles_enveloppes)
                        if k.endswith("PEE") or "_PEE" in k), -1)
        idx_pereco = next((i for i, k in enumerate(cles_enveloppes)
                           if "PERECO" in k), -1)
        if not (idx_perin < idx_pee < idx_pereco):
            erreurs_ordre.append((etape.code, cles_enveloppes))
    runner.check("16.3 Ordre stable PERIN → PEE → PERECO dans toutes "
                 "les hypothèses RECAP (contrainte SP18)",
                 not erreurs_ordre,
                 detail=f"erreurs: {erreurs_ordre[:2]}")

    # 16.4 Cohérence valeurs RECAP avec sous-traces enveloppes
    # Pour chaque horizon, la valeur nette annoncée dans RECAP doit
    # correspondre à la valeur nette de la ligne enveloppe.
    erreurs_coherence = []
    for h in [5, 10, 20]:
        code_recap = f"REC_RECAP_VALEUR_NETTE_{h}ANS"
        etape_recap = next(
            (e for e in trace_orch.etapes if e.code == code_recap), None
        )
        if etape_recap is None:
            continue
        valeur_perin_recap = etape_recap.hypotheses.get("valeur_nette_PERIN")
        valeur_pee_recap = etape_recap.hypotheses.get("valeur_nette_PEE")
        valeur_pereco_recap = etape_recap.hypotheses.get("valeur_nette_PERECO")

        ligne_perin_h = next(
            (l for l in result_orch.perin.lignes_par_horizon
             if l.horizon_annees == h), None
        )
        ligne_pee_h = next(
            (l for l in result_orch.pee.lignes_par_horizon
             if l.horizon_annees == h), None
        )
        ligne_pereco_h = next(
            (l for l in result_orch.pereco.lignes_par_horizon
             if l.horizon_annees == h), None
        )
        if (ligne_perin_h is None or ligne_pee_h is None
                or ligne_pereco_h is None):
            continue
        if abs(valeur_perin_recap - ligne_perin_h.valeur_nette) > 0.01:
            erreurs_coherence.append((h, "PERIN", valeur_perin_recap,
                                      ligne_perin_h.valeur_nette))
        if abs(valeur_pee_recap - ligne_pee_h.valeur_nette) > 0.01:
            erreurs_coherence.append((h, "PEE", valeur_pee_recap,
                                      ligne_pee_h.valeur_nette))
        if abs(valeur_pereco_recap - ligne_pereco_h.valeur_nette) > 0.01:
            erreurs_coherence.append((h, "PERECO", valeur_pereco_recap,
                                      ligne_pereco_h.valeur_nette))
    runner.check("16.4 Valeurs nettes RECAP cohérentes avec sous-traces "
                 "enveloppes (preuve d'agrégation non-déformante)",
                 not erreurs_coherence,
                 detail=f"erreurs: {erreurs_coherence[:2]}")

    # 16.5 Aucun mot interdit dans les hypothèses RECAP rendues
    # (label, code, hypothèses → contenu visible PDF cabinet)
    mots_interdits = ["score", "indice", "ranking", "optimal",
                      "meilleur", "préconis", "recommand",
                      "efficacité", "performance"]
    erreurs_mots = []
    for etape in etapes_recap_racine:
        contenu_visible = etape.label.lower() + " "
        for k, v in etape.hypotheses.items():
            contenu_visible += f"{k} {v} ".lower()
        for mot in mots_interdits:
            if mot in contenu_visible:
                erreurs_mots.append((etape.code, mot))
    runner.check("16.5 Aucun mot interdit (score/ranking/optimal/meilleur/"
                 "recommand/efficacité/performance) dans les étapes RECAP "
                 "(contrainte SP18 : pas de score global, même implicite)",
                 not erreurs_mots,
                 detail=f"erreurs: {erreurs_mots[:3]}")

    # 16.6 La valeur (scalaire) de chaque étape RECAP est neutre = 4
    # depuis SP25 (nombre d'enveloppes alignées : PERIN/PEE/PERECO/PERO,
    # pas une métrique économique)
    erreurs_valeur = [
        e.code for e in etapes_recap_racine if e.valeur != 4
    ]
    runner.check("16.6 Valeur scalaire neutre = 4 (nombre d'enveloppes "
                 "alignées SP25) pour toutes les étapes RECAP",
                 not erreurs_valeur,
                 detail=f"étapes avec valeur ≠ 4: {erreurs_valeur}")

    # 16.7 Présence du champ ordre_stable dans toutes les hypothèses RECAP
    erreurs_ordre_stable = [
        e.code for e in etapes_recap_racine
        if "ordre_stable" not in e.hypotheses
    ]
    runner.check("16.7 Mention 'ordre_stable' présente dans toutes les "
                 "hypothèses RECAP (auditabilité)",
                 not erreurs_ordre_stable,
                 detail=f"manquants: {erreurs_ordre_stable}")

    # ============================================================
    # SECTION 17 — SP25 : Intégration PERO dans l'orchestrateur
    # ============================================================
    # Discipline : tests d'intégration (pas de recalcul algébrique
    # détaillé — déjà couvert par test_strategy_receptacles_pero.py).
    # On vérifie ici que PERO est absorbé comme 4e enveloppe au même
    # titre que PERIN/PEE/PERECO, sans traitement spécifique côté
    # orchestrateur (B-Q1=α, S-Q1=β, subsidiaire 2 validés SP25).
    runner.section("17. SP25 — Intégration PERO orchestrateur")

    from core.profil import Profil as ProfilSP25
    from core.audit import TraceAudit as TraceAuditSP25
    from strategy.receptacles_orchestrateur import (
        allocation_receptacles as alloc_sp25,
        ENVELOPPES_V1_3,
    )

    # 17.1 — ENVELOPPES_V1_3 contient bien 4 enveloppes en ordre stable
    runner.check(
        "17.1 ENVELOPPES_V1_3 = ('PERIN', 'PEE', 'PERECO', 'PERO')",
        ENVELOPPES_V1_3 == ("PERIN", "PEE", "PERECO", "PERO"),
        detail=f"observé: {ENVELOPPES_V1_3}",
    )

    # 17.2 — Cas PERO inactif (taux 0 % par défaut Profil, b1 validé)
    profil_inactif = ProfilSP25()
    trace_inactif = TraceAuditSP25(regime="SP25 PERO inactif",
                                   profil_resume="")
    res_inactif = alloc_sp25(profil_inactif, flux_disponible=5000.0,
                             audit=trace_inactif)

    runner.check(
        "17.2 PERO inactif (taux 0 %) : champ pero présent dans le résultat",
        res_inactif.pero is not None,
    )
    runner.check(
        "17.3 PERO inactif : accessible=True, 3 lignes à zéro "
        "(cohérence b1 : pas de signal prescriptif)",
        (res_inactif.pero.accessible is True
         and len(res_inactif.pero.lignes_par_horizon) == 3
         and all(l.valeur_nette == 0.0
                 for l in res_inactif.pero.lignes_par_horizon)),
    )

    # 17.4 — REC_PERO_INPUTS_LUS_PROFIL présente dans la trace racine
    # (subsidiaire 2 validé SP25 : traçabilité audit)
    codes_racine_inactif = [e.code for e in trace_inactif.etapes]
    runner.check(
        "17.4 Étape REC_PERO_INPUTS_LUS_PROFIL présente "
        "(subsidiaire 2 SP25, traçabilité inputs lus depuis profil)",
        "REC_PERO_INPUTS_LUS_PROFIL" in codes_racine_inactif,
        detail=f"codes racine observés: {codes_racine_inactif}",
    )

    # 17.5 — Sous-trace ligne_pero attachée en 4e position
    noms_sous_traces_inactif = list(trace_inactif.noms_sous_traces())
    runner.check(
        "17.5 Sous-trace 'ligne_pero' attachée en 4e position "
        "(ordre doctrinal SP25)",
        noms_sous_traces_inactif == ["ligne_perin", "ligne_pee",
                                     "ligne_pereco", "ligne_pero"],
        detail=f"observé: {noms_sous_traces_inactif}",
    )

    # 17.6 — Cas PERO actif (taux 3 % via profil)
    profil_actif = ProfilSP25(taux_cotisation_pero=0.03)
    profil_actif.tmi = 0.30  # pour cohérence golden SP24
    trace_actif = TraceAuditSP25(regime="SP25 PERO actif",
                                 profil_resume="")
    res_actif = alloc_sp25(profil_actif, flux_disponible=5000.0,
                           audit=trace_actif)

    # Valeurs attendues : strictement identiques au golden SP24
    # `pero_standard_80k_3pct` (preuve de cohérence cross-niveau).
    ligne_20 = next(l for l in res_actif.pero.lignes_par_horizon
                    if l.horizon_annees == 20)
    runner.check(
        "17.6 PERO actif (taux 3 %) : valeur_nette 20 ans = 55 219,58 € "
        "(cohérence avec golden SP24)",
        abs(ligne_20.valeur_nette - 55_219.58) < 0.01,
        detail=f"observé: {ligne_20.valeur_nette}",
    )

    # 17.7 — RECAP étendus à 4 enveloppes (B-Q1=α : pas de nouvelle
    # dimension, juste extension des 3 RECAP existants)
    recap_vn_20 = next(e for e in trace_actif.etapes
                       if e.code == "REC_RECAP_VALEUR_NETTE_20ANS")
    hypotheses_attendues = {"valeur_nette_PERIN", "valeur_nette_PEE",
                            "valeur_nette_PERECO", "valeur_nette_PERO",
                            "ordre_stable", "nature"}
    runner.check(
        "17.7 RECAP_VALEUR_NETTE_20ANS contient valeur_nette_PERO "
        "(4e enveloppe en 4e position)",
        hypotheses_attendues.issubset(set(recap_vn_20.hypotheses.keys())),
        detail=f"clés observées: {sorted(recap_vn_20.hypotheses.keys())}",
    )

    # 17.8 — Ordre stable inscrit dans hypotheses (mention SP25)
    runner.check(
        "17.8 Ordre stable inscrit : 'PERIN → PEE → PERECO → PERO (SP25)'",
        "PERO (SP25)" in str(recap_vn_20.hypotheses.get("ordre_stable", "")),
        detail=f"observé: {recap_vn_20.hypotheses.get('ordre_stable')}",
    )

    return runner.synthese("SP18 Réceptacles orchestrateur opérationnel")


if __name__ == "__main__":
    sys.exit(main())
