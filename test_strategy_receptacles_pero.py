"""
test_strategy_receptacles_pero.py — Test structurel et algébrique
du module métier PERO (SP24).

Couvre :
- Imports et surface publique
- Providers doctrinaux (taux, plafond, éligibilité) + override tests
- Dataclass ResultatAllocationPero (héritage)
- Fonction allocation_pero (cas standard + cas dégénéré)
- Invariants algébriques (LigneHorizonReceptacle.__post_init__ +
  verifier_invariants_pero PERO-spécifiques)
- TraceAudit produite (étapes racine + sous-traces D-R10)
- Plafonds (cotisation > plafond → reprise IR)
- Cohérence cross-enveloppes (effort_reel négatif possible)

Pattern : calqué sur test_strategy_receptacles.py SP14
(StructureRunner). Pas de framework de test externe.
"""

import sys
from pathlib import Path

# Permettre l'exécution depuis n'importe où
RACINE = Path(__file__).resolve().parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))


class StructureRunner:
    """Runner d'assertions structurelles (calque SP14)."""

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
            self.failures.append(
                label + (f"  [{detail}]" if detail else "")
            )

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
    print("  TEST STRUCTUREL ET ALGÉBRIQUE — Réceptacles PERO (SP24)")
    print("=" * 90)

    runner = StructureRunner()

    # ============================================================
    # SECTION 1 — IMPORTS ET SURFACE PUBLIQUE
    # ============================================================
    runner.section("1. Imports et surface publique")

    try:
        from strategy import receptacles_pero
        runner.check("1.1 Module strategy.receptacles_pero importable",
                     True)
    except ImportError as e:
        runner.check("1.1 Module strategy.receptacles_pero importable",
                     False, detail=str(e))
        return runner.synthese("PERO SP24")

    # Surface publique attendue (cohérent SP15-SP17 + ajouts PERO)
    symboles_attendus = [
        # Constantes
        "TX_FORFAIT_SOCIAL_PERO",
        "TX_CSG_CRDS_PERO",
        "TX_PLAFOND_EXONERATION_REM",
        "PLAFOND_EXONERATION_PASS",
        "TX_PFU_GAINS_PERO",
        # Providers
        "obtenir_taux_forfait_social_pero",
        "obtenir_taux_ps_pero",
        "obtenir_plafond_pero",
        "est_eligible_pero",
        # Dataclass + fonction
        "ResultatAllocationPero",
        "allocation_pero",
        # Helper
        "verifier_invariants_pero",
    ]
    for sym in symboles_attendus:
        runner.check(
            f"1.2 Symbole `{sym}` exposé",
            hasattr(receptacles_pero, sym),
        )

    # Vérification __all__
    all_module = getattr(receptacles_pero, "__all__", None)
    runner.check(
        "1.3 __all__ défini et contient les 12 symboles attendus",
        all_module is not None and all(
            sym in all_module for sym in symboles_attendus
        ),
        detail=(f"observé: {sorted(all_module or [])}"
                if all_module else "absent"),
    )

    # ============================================================
    # SECTION 2 — CONSTANTES DOCTRINALES (FRANCE 2026)
    # ============================================================
    runner.section("2. Constantes doctrinales France 2026")

    runner.check(
        "2.1 TX_FORFAIT_SOCIAL_PERO = 0.16",
        abs(receptacles_pero.TX_FORFAIT_SOCIAL_PERO - 0.16) < 1e-9,
        detail=f"observé: {receptacles_pero.TX_FORFAIT_SOCIAL_PERO}",
    )
    runner.check(
        "2.2 TX_CSG_CRDS_PERO = 0.097",
        abs(receptacles_pero.TX_CSG_CRDS_PERO - 0.097) < 1e-9,
        detail=f"observé: {receptacles_pero.TX_CSG_CRDS_PERO}",
    )
    runner.check(
        "2.3 TX_PLAFOND_EXONERATION_REM = 0.08",
        abs(receptacles_pero.TX_PLAFOND_EXONERATION_REM - 0.08) < 1e-9,
        detail=f"observé: {receptacles_pero.TX_PLAFOND_EXONERATION_REM}",
    )
    runner.check(
        "2.4 PLAFOND_EXONERATION_PASS = 8.0",
        abs(receptacles_pero.PLAFOND_EXONERATION_PASS - 8.0) < 1e-9,
        detail=f"observé: {receptacles_pero.PLAFOND_EXONERATION_PASS}",
    )
    runner.check(
        "2.5 TX_PFU_GAINS_PERO = 0.30",
        abs(receptacles_pero.TX_PFU_GAINS_PERO - 0.30) < 1e-9,
        detail=f"observé: {receptacles_pero.TX_PFU_GAINS_PERO}",
    )

    # ============================================================
    # SECTION 3 — PROVIDERS DOCTRINAUX (runtime normal)
    # ============================================================
    runner.section("3. Providers doctrinaux (runtime normal)")

    from core.profil import Profil
    profil = Profil()

    runner.check(
        "3.1 obtenir_taux_forfait_social_pero(profil) = 0.16",
        abs(receptacles_pero.obtenir_taux_forfait_social_pero(profil)
            - 0.16) < 1e-9,
    )
    runner.check(
        "3.2 obtenir_taux_ps_pero(profil) = 0.097",
        abs(receptacles_pero.obtenir_taux_ps_pero(profil)
            - 0.097) < 1e-9,
    )

    # Plafond : 80 000 € × 8 % = 6 400 € (sous le plafond 8 PASS)
    from core.profil import PASS_2026
    plafond = receptacles_pero.obtenir_plafond_pero(profil, 80_000.0)
    runner.check(
        "3.3 obtenir_plafond_pero(80k €) = 6 400 € (8 % rém < 8 PASS)",
        abs(plafond - 6_400.0) < 0.01,
        detail=f"observé: {plafond}",
    )

    # Plafond très haut salaire : pour activer le cap 8 × PASS,
    # il faut 8 % × salaire > 8 × PASS_2026
    # soit salaire > 100 × PASS_2026 = 4 806 000 €
    salaire_cap_pass = 100.0 * PASS_2026 + 100_000.0  # = 4 906 000 €
    plafond_cap = receptacles_pero.obtenir_plafond_pero(
        profil, salaire_cap_pass,
    )
    runner.check(
        "3.4 obtenir_plafond_pero(salaire très haut) = 8 × PASS "
        "(cap PASS atteint)",
        abs(plafond_cap - 8.0 * PASS_2026) < 0.01,
        detail=f"observé: {plafond_cap}, attendu: {8.0 * PASS_2026}",
    )

    runner.check(
        "3.5 est_eligible_pero(profil) = True (SP24)",
        receptacles_pero.est_eligible_pero(profil) is True,
    )

    # ============================================================
    # SECTION 4 — PROVIDERS AVEC OVERRIDE TESTS (subsidiaire)
    # ============================================================
    runner.section("4. Providers avec override (subsidiaire validé)")

    override = {
        "forfait_social": 0.20,
        "csg_crds": 0.10,
        "plafond_taux": 0.05,
        "plafond_pass": 5.0,
    }
    runner.check(
        "4.1 obtenir_taux_forfait_social_pero avec override = 0.20",
        abs(receptacles_pero.obtenir_taux_forfait_social_pero(
            profil, _override_taux=override) - 0.20) < 1e-9,
    )
    runner.check(
        "4.2 obtenir_taux_ps_pero avec override = 0.10",
        abs(receptacles_pero.obtenir_taux_ps_pero(
            profil, _override_taux=override) - 0.10) < 1e-9,
    )
    runner.check(
        "4.3 obtenir_plafond_pero avec override (5 % rém, 5 PASS)",
        abs(receptacles_pero.obtenir_plafond_pero(
            profil, 80_000.0, _override_taux=override)
            - 0.05 * 80_000.0) < 0.01,
    )
    # Pour activer le cap 5 PASS avec override taux 5 %, il faut
    # 5 % × salaire > 5 × PASS_2026, soit salaire > 100 × PASS_2026.
    salaire_cap_override = 100.0 * PASS_2026 + 100_000.0
    runner.check(
        "4.4 obtenir_plafond_pero override (salaire très haut, "
        "cap 5 PASS atteint)",
        abs(receptacles_pero.obtenir_plafond_pero(
            profil, salaire_cap_override, _override_taux=override)
            - 5.0 * PASS_2026) < 0.01,
        detail=f"attendu: {5.0 * PASS_2026}",
    )

    # ============================================================
    # SECTION 5 — ALLOCATION PERO CAS STANDARD
    # ============================================================
    runner.section("5. allocation_pero — cas standard "
                   "(80k €, 3 %, TMI 30 %, horizons 5/10/20)")

    from core.audit import TraceAudit
    profil.tmi = 0.30
    trace_std = TraceAudit(
        regime="PERO test standard",
        profil_resume="Test SP24",
    )
    resultat = receptacles_pero.allocation_pero(
        profil=profil,
        salaire_brut_annuel=80_000.0,
        taux_cotisation_pero=0.03,
        horizons=(5, 10, 20),
        audit=trace_std,
    )

    runner.check(
        "5.1 Résultat est ResultatAllocationPero",
        isinstance(resultat, receptacles_pero.ResultatAllocationPero),
    )
    runner.check(
        "5.2 Enveloppe = 'PERO'",
        resultat.enveloppe == "PERO",
        detail=f"observé: {resultat.enveloppe}",
    )
    runner.check(
        "5.3 Accessible = True",
        resultat.accessible is True,
    )
    runner.check(
        "5.4 3 lignes par horizon",
        len(resultat.lignes_par_horizon) == 3,
        detail=f"observé: {len(resultat.lignes_par_horizon)}",
    )
    runner.check(
        "5.5 Horizons ordonnés 5/10/20",
        [l.horizon_annees for l in resultat.lignes_par_horizon]
        == [5, 10, 20],
        detail=(f"observé: "
                f"{[l.horizon_annees for l in resultat.lignes_par_horizon]}"),
    )

    # Valeurs économiques attendues (cas standard)
    # flux employeur = 80 000 × 0.03 = 2 400 €/an
    # csg_crds = 2 400 × 0.097 = 232.80 €
    # cotisation entièrement exonérée (2 400 < 6 400 plafond)
    # economie_fiscale = 2 400 × 0.30 = 720 €
    # effort_reel = 232.80 − 720 = −487.20 €
    # cout_entreprise = 2 400 × 1.16 = 2 784 €
    ligne5 = resultat.lignes_par_horizon[0]
    runner.check(
        "5.6 flux_entrant_brut (CSG/CRDS) = 232.80 €",
        abs(ligne5.flux_entrant_brut - 232.80) < 0.01,
        detail=f"observé: {ligne5.flux_entrant_brut}",
    )
    runner.check(
        "5.7 economie_fiscale_immediate = 720 €",
        abs(ligne5.economie_fiscale_immediate - 720.0) < 0.01,
        detail=f"observé: {ligne5.economie_fiscale_immediate}",
    )
    runner.check(
        "5.8 effort_reel = −487.20 € (gain net immédiat, "
        "TMI > CSG/CRDS)",
        abs(ligne5.effort_reel - (-487.20)) < 0.01,
        detail=f"observé: {ligne5.effort_reel}",
    )
    runner.check(
        "5.9 cout_entreprise = 2 784 € (= 2 400 × 1.16)",
        abs(ligne5.cout_entreprise - 2_784.0) < 0.01,
        detail=f"observé: {ligne5.cout_entreprise}",
    )

    # ============================================================
    # SECTION 6 — INVARIANTS ALGÉBRIQUES
    # ============================================================
    runner.section("6. Invariants algébriques (LigneHorizonReceptacle "
                   "+ PERO-spécifiques)")

    # Invariant générique 1 (LigneHorizonReceptacle.__post_init__) :
    # effort_reel = flux_entrant_brut - economie_fiscale_immediate
    for ligne in resultat.lignes_par_horizon:
        attendu = (ligne.flux_entrant_brut
                   - ligne.economie_fiscale_immediate)
        runner.check(
            f"6.1.{ligne.horizon_annees}ans Invariant générique 1 : "
            f"effort_reel == flux_entrant_brut − economie_fiscale",
            abs(ligne.effort_reel - attendu) < 0.01,
            detail=f"observé: {ligne.effort_reel}, attendu: {attendu}",
        )

    # Invariant générique 2 :
    # valeur_nette = capital_projete - fiscalite_sortie
    for ligne in resultat.lignes_par_horizon:
        attendu = ligne.capital_projete - ligne.fiscalite_sortie
        runner.check(
            f"6.2.{ligne.horizon_annees}ans Invariant générique 2 : "
            f"valeur_nette == capital_projete − fiscalite_sortie",
            abs(ligne.valeur_nette - attendu) < 0.01,
            detail=f"observé: {ligne.valeur_nette}, attendu: {attendu}",
        )

    # Invariants PERO-spécifiques (PERO-1, PERO-1bis, PERO-2)
    flux_annuel = 80_000.0 * 0.03
    for ligne in resultat.lignes_par_horizon:
        try:
            receptacles_pero.verifier_invariants_pero(
                flux_employeur_brut_annuel=flux_annuel,
                tx_forfait_social=receptacles_pero.TX_FORFAIT_SOCIAL_PERO,
                cout_entreprise_annuel=(flux_annuel
                                        * (1.0 + receptacles_pero
                                           .TX_FORFAIT_SOCIAL_PERO)),
                ligne=ligne,
            )
            invariants_ok = True
        except ValueError as e:
            invariants_ok = False
            details_inv = str(e)
        else:
            details_inv = ""
        runner.check(
            f"6.3.{ligne.horizon_annees}ans Invariants PERO-1 "
            f"(coût entreprise) + PERO-2 (capital annuité)",
            invariants_ok,
            detail=details_inv,
        )

    # ============================================================
    # SECTION 7 — TRACE AUDIT (D-R10)
    # ============================================================
    runner.section("7. TraceAudit produite — étapes plates D-R10")

    # Étapes racine attendues (pattern SP15-SP17)
    codes_attendus_racine = [
        "REC_PERO_ELIGIBILITE",
        "REC_PERO_TAUX_COTISATION_APPLIQUE",
        "REC_PERO_FLUX_EMPLOYEUR_BRUT_ANNUEL",
        "REC_PERO_PLAFOND_EXONERATION",
        "REC_PERO_COTISATION_EXONEREE",
        "REC_PERO_TMI_APPLIQUEE",
        "REC_PERO_ECONOMIE_FISCALE_IMMEDIATE",
        "REC_PERO_CSG_CRDS",
        "REC_PERO_FORFAIT_SOCIAL",
        "REC_PERO_COUT_ENTREPRISE_ANNUEL",
        "REC_PERO_EFFORT_REEL_ANNUEL",
        "REC_PERO_DISPONIBILITE",
    ]
    codes_observes = [e.code for e in trace_std.etapes]
    for code in codes_attendus_racine:
        runner.check(
            f"7.1 Code étape racine `{code}` présent",
            code in codes_observes,
            detail=f"observés: {codes_observes}",
        )

    # D-R10 : aucune étape parent_id != None
    etapes_avec_parent = [e for e in trace_std.etapes
                          if getattr(e, "parent_id", None) is not None]
    runner.check(
        "7.2 D-R10 : aucune étape avec parent_id != None dans "
        "la trace racine",
        len(etapes_avec_parent) == 0,
        detail=f"observés: {len(etapes_avec_parent)} étapes parentées",
    )

    # Sous-traces : 3 (une par horizon)
    noms_sous_traces = trace_std.noms_sous_traces()
    runner.check(
        "7.3 3 sous-traces horizons attachées",
        len(noms_sous_traces) == 3,
        detail=f"observés: {noms_sous_traces}",
    )
    for h in [5, 10, 20]:
        runner.check(
            f"7.4 Sous-trace `horizon_{h}ans` présente",
            f"horizon_{h}ans" in noms_sous_traces,
        )

    # Codes étapes dans sous-trace horizon 5 ans
    sous_trace_5 = trace_std.get_sous_trace("horizon_5ans")
    codes_attendus_horizon = [
        "REC_PERO_CAPITAL_PROJETE_5ANS",
        "REC_PERO_FISCALITE_SORTIE_5ANS",
        "REC_PERO_VALEUR_NETTE_5ANS",
    ]
    codes_observes_horizon = ([e.code for e in sous_trace_5.etapes]
                              if sous_trace_5 else [])
    for code in codes_attendus_horizon:
        runner.check(
            f"7.5 Code sous-trace horizon `{code}` présent",
            code in codes_observes_horizon,
        )

    # Wordings doctrinaux attachés (échantillon)
    etape_csg = next((e for e in trace_std.etapes
                      if e.code == "REC_PERO_CSG_CRDS"), None)
    runner.check(
        "7.6 Wording WORDING_PERO_CSG_CRDS_COTISATION attaché à "
        "REC_PERO_CSG_CRDS",
        (etape_csg is not None
         and "WORDING_PERO_CSG_CRDS_COTISATION" in (etape_csg.hypotheses or {})),
    )

    # ============================================================
    # SECTION 8 — CAS DÉPASSEMENT PLAFOND (reprise IR)
    # ============================================================
    runner.section("8. Cas plafond dépassé — fraction non exonérée")

    # Cotisation 10 % sur 80k = 8 000 € > plafond 6 400 €
    trace_plafond = TraceAudit(
        regime="PERO test plafond",
        profil_resume="Test plafond dépassé",
    )
    resultat_plafond = receptacles_pero.allocation_pero(
        profil=profil,
        salaire_brut_annuel=80_000.0,
        taux_cotisation_pero=0.10,
        horizons=(5, 10, 20),
        audit=trace_plafond,
    )

    # Vérifier que cotisation_exoneree = 6 400 € (et non 8 000 €)
    etape_cot_ex = next((e for e in trace_plafond.etapes
                         if e.code == "REC_PERO_COTISATION_EXONEREE"),
                        None)
    runner.check(
        "8.1 Cotisation exonérée plafonnée à 6 400 € (sur 8 000 € versés)",
        (etape_cot_ex is not None
         and abs(float(etape_cot_ex.valeur) - 6_400.0) < 0.01),
        detail=(f"observé: {etape_cot_ex.valeur if etape_cot_ex else 'absent'}"),
    )

    # Vérifier présence de REC_PERO_COTISATION_NON_EXONEREE
    codes_plafond = [e.code for e in trace_plafond.etapes]
    runner.check(
        "8.2 Étape REC_PERO_COTISATION_NON_EXONEREE présente "
        "(fraction au-dessus du plafond)",
        "REC_PERO_COTISATION_NON_EXONEREE" in codes_plafond,
    )

    # Économie fiscale = 6 400 × 0.30 = 1 920 € (pas 8 000 × 0.30 = 2 400 €)
    ligne_pl = resultat_plafond.lignes_par_horizon[0]
    runner.check(
        "8.3 economie_fiscale_immediate plafonnée = 1 920 €",
        abs(ligne_pl.economie_fiscale_immediate - 1_920.0) < 0.01,
        detail=f"observé: {ligne_pl.economie_fiscale_immediate}",
    )

    # ============================================================
    # SECTION 9 — APPEL SANS TRACE (audit=None)
    # ============================================================
    runner.section("9. allocation_pero(audit=None) — pas de trace produite")

    resultat_sans_trace = receptacles_pero.allocation_pero(
        profil=profil,
        salaire_brut_annuel=80_000.0,
        taux_cotisation_pero=0.03,
        horizons=(5, 10, 20),
        audit=None,
    )
    runner.check(
        "9.1 Résultat identique avec audit=None (3 lignes)",
        len(resultat_sans_trace.lignes_par_horizon) == 3,
    )
    runner.check(
        "9.2 Valeurs identiques avec audit=None "
        "(pas d'effet de bord trace)",
        all(
            abs(l1.valeur_nette - l2.valeur_nette) < 0.01
            for l1, l2 in zip(resultat.lignes_par_horizon,
                              resultat_sans_trace.lignes_par_horizon)
        ),
    )

    # ============================================================
    # SECTION 10 — INVARIANT NÉGATIF : violation détectée
    # ============================================================
    runner.section("10. Invariants — violation détectée correctement")

    # Construire une ligne avec un coût entreprise incohérent
    from strategy.receptacles_orchestrateur import LigneHorizonReceptacle
    ligne_buggee = LigneHorizonReceptacle(
        horizon_annees=5,
        flux_entrant_brut=232.80,
        economie_fiscale_immediate=720.0,
        effort_reel=-487.20,
        capital_projete=12489.70,
        fiscalite_sortie=146.91,
        valeur_nette=12342.79,
        cout_entreprise=9999.99,  # ← INCOHÉRENT (devrait être 2 784 €)
        disponibilite="test",
    )
    try:
        receptacles_pero.verifier_invariants_pero(
            flux_employeur_brut_annuel=2_400.0,
            tx_forfait_social=0.16,
            cout_entreprise_annuel=2_784.0,
            ligne=ligne_buggee,
        )
        violation_detectee = False
    except ValueError:
        violation_detectee = True
    runner.check(
        "10.1 verifier_invariants_pero détecte un cout_entreprise "
        "incohérent (ValueError)",
        violation_detectee,
    )

    return runner.synthese("PERO SP24")


if __name__ == "__main__":
    sys.exit(main())
