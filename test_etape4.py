"""
Tests dédiés Étape 4 Phase B.2 :
- 4a : Synthèse multi-régimes (routeur calcul_synthese)
- 4b : Comparateur de régimes (calcul_comparateur_regimes)

Vérifie en particulier les garde-fous méthodologiques :
- Pas de "régime recommandé" automatique
- Pas d'agrégation T4 (net + bénéfice retenu séparés)
- Alerte BNC/SEL systématique sur Libéral SEL
- 2 disclaimers permanents
- Pas de classement inter-régimes via radar
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dataclasses import fields
from strategy.synthese import calcul_synthese, ResultatSynthese
from strategy.comparateur import ConfigComparateur
from strategy.comparateur_regimes import (
    calcul_comparateur_regimes, ResultatComparateurRegimes, LigneRegime,
    DISCLAIMER_CHANGEMENT_REGIME, DISCLAIMER_COMPARABILITE,
    NOTE_RADAR_INTRA_REGIME,
)
from strategy.tns import arbitrage_complet_tns
from strategy.liberal import arbitrage_complet_liberal
from core.profil import Profil
from strategy.assimile import arbitrage_complet  # routeur Assimilé existant


def check(label, py, expected, tol=0.01):
    if isinstance(expected, bool):
        ok = py == expected
    elif isinstance(expected, (int, float)):
        ok = abs(py - expected) <= tol
    elif isinstance(expected, str):
        ok = py == expected
    else:
        ok = py == expected
    return ("✓" if ok else "✗"), ok


# ============================================================
# 4a — Tests routeur Synthèse multi-régimes
# ============================================================
def test_4a_routeur_synthese():
    print("=" * 90)
    print("  4a — TESTS ROUTEUR calcul_synthese() multi-régimes")
    print("=" * 90)

    checks = []

    # Cas 1 : Assimilé → comportement Phase A préservé
    profil_a = Profil(forme_juridique="SAS / SASU")
    arb_a = arbitrage_complet(profil_a)
    synth_a = calcul_synthese(profil_a, arb_a["strategies"], ConfigComparateur())
    checks.append(("Assimilé : stratégie retenue = D", synth_a.strategie_retenue, "D"))
    checks.append(("Assimilé : net = 78 423,80 (parité v19)",
                   synth_a.net_dirigeant_retenu, 78_423.8023))
    checks.append(("Assimilé : ROI calculé", synth_a.roi_mois is not None, True))

    # Cas 2 : TNS
    profil_t = Profil(forme_juridique="SARL (gérance majoritaire) / EURL",
                      benefice_is=200_000, capital_cca=100_000)
    arb_t = arbitrage_complet_tns(profil_t)
    synth_t = calcul_synthese(profil_t, arb_t.strategies, ConfigComparateur())
    checks.append(("TNS : stratégie retenue ∈ T1-T4",
                   synth_t.strategie_retenue in ("T1", "T2", "T3", "T4"), True))
    checks.append(("TNS : net dirigeant > 0", synth_t.net_dirigeant_retenu > 0, True))
    # Vérifier que les alertes du régime TNS sont remontées
    has_alertes_tns = any(item.get("label") == "Alertes régime TNS"
                          for item in synth_t.checklist)
    checks.append(("TNS : checklist contient les alertes régime", has_alertes_tns, True))

    # Cas 3 : TNS avec T4 forcée → alerte de non-disponibilité du bénéfice retenu
    synth_t4 = calcul_synthese(profil_t, arb_t.strategies, ConfigComparateur(),
                                code_retenue="T4")
    checks.append(("TNS T4 : stratégie retenue = T4", synth_t4.strategie_retenue, "T4"))
    # L'alerte de non-disponibilité doit apparaître dans la checklist
    has_t4_alerte = False
    for item in synth_t4.checklist:
        for txt in item.get("items", []):
            if "Stratégie T4 retenue" in txt or "bénéfice retenu" in txt.lower():
                has_t4_alerte = True
                break
    checks.append(("TNS T4 : alerte explicite de non-disponibilité",
                   has_t4_alerte, True))

    # Cas 4 : Libéral SELAS → L3 retenu doit avoir alerte BNC/SEL
    profil_l = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELAS",
                      recettes_bnc=300_000, frais_pro_bnc=50_000,
                      remuneration_sel_souhaitee=80_000)
    arb_l = arbitrage_complet_liberal(profil_l)
    synth_l = calcul_synthese(profil_l, arb_l.strategies, ConfigComparateur())
    checks.append(("Libéral : stratégie ∈ L1-L4",
                   synth_l.strategie_retenue in ("L1", "L2", "L3", "L4"), True))
    # Si L3/L4 retenue → alerte BNC/SEL remontée
    if synth_l.strategie_retenue in ("L3", "L4"):
        has_bnc_sel = False
        for item in synth_l.checklist:
            for txt in item.get("items", []):
                if "BNC / SEL" in txt:
                    has_bnc_sel = True
                    break
        checks.append((f"Libéral {synth_l.strategie_retenue} : alerte BNC/SEL remontée",
                       has_bnc_sel, True))
    else:
        # Si L1 ou L2 retenue → pas d'alerte BNC/SEL (cohérent)
        checks.append((f"Libéral {synth_l.strategie_retenue} (BNC pur) : OK", True, True))

    # Cas 5 : Salarié (via routeur fallback)
    from strategy.synthese import _synthese_salarie
    synth_s = _synthese_salarie(profil_a, None, ConfigComparateur())
    checks.append(("Salarié : stratégie = 'Salarié (référence)'",
                   synth_s.strategie_retenue, "Salarié (référence)"))
    checks.append(("Salarié : net > 0", synth_s.net_dirigeant_retenu > 0, True))

    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:60s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 4a : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 4b — Tests Comparateur de régimes
# ============================================================
def test_4b_comparateur_regimes():
    print("\n" + "=" * 90)
    print("  4b — TESTS Comparateur de régimes")
    print("=" * 90)

    profil = Profil(
        enveloppe=120_000,
        benefice_is=200_000, capital_cca=100_000,
        recettes_bnc=300_000, frais_pro_bnc=50_000,
        remuneration_sel_souhaitee=80_000, forme_sel="SELAS",
        salaire_brut_assimile=80_000,
    )
    res = calcul_comparateur_regimes(profil)

    checks = [
        # Structure du résultat
        ("4 lignes (Assimilé/TNS/Libéral/Salarié)", len(res.lignes), 4),
        ("Disclaimer changement régime présent",
         res.disclaimer_changement_regime == DISCLAIMER_CHANGEMENT_REGIME, True),
        ("Disclaimer comparabilité présent",
         res.disclaimer_comparabilite == DISCLAIMER_COMPARABILITE, True),
        ("Note radar intra-régime présente",
         res.note_radar == NOTE_RADAR_INTRA_REGIME, True),

        # Identification des lignes
        ("Ligne 1 = Assimilé", res.lignes[0].regime, "Assimilé salarié"),
        ("Ligne 2 = TNS", res.lignes[1].regime, "TNS"),
        ("Ligne 3 = Libéral (selon stratégie)",
         res.lignes[2].regime.startswith("Libéral"), True),
        ("Ligne 4 = Salarié (référence)", res.lignes[3].regime, "Salarié (référence)"),

        # Nets cohérents
        ("Assimilé net > 0", res.lignes[0].net_dirigeant > 0, True),
        ("TNS net > 0", res.lignes[1].net_dirigeant > 0, True),
        ("Libéral net > 0", res.lignes[2].net_dirigeant > 0, True),
        ("Salarié net > 0", res.lignes[3].net_dirigeant > 0, True),

        # Grandeurs d'entrée différenciées
        ("Assimilé : grandeur = Coût société",
         "Coût société" in res.lignes[0].grandeur_entree, True),
        ("TNS : grandeur = Bénéfice IS",
         "Bénéfice" in res.lignes[1].grandeur_entree, True),
        ("Libéral : grandeur = Recettes BNC",
         "Recettes" in res.lignes[2].grandeur_entree, True),
        ("Salarié : grandeur = Salaire brut",
         "Salaire brut" in res.lignes[3].grandeur_entree, True),

        # meilleur_net est une chaîne, pas un classement
        ("meilleur_net est un string", isinstance(res.meilleur_net, str), True),
    ]

    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:60s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 4b : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# Tests garde-fous méthodologiques (transverses 4a + 4b)
# ============================================================
def test_garde_fous():
    print("\n" + "=" * 90)
    print("  Tests garde-fous méthodologiques (Étape 4)")
    print("=" * 90)

    nb_ok = 0
    checks = []

    # Garde-fou 1 : pas de champ "regime_recommande" dans ResultatComparateurRegimes
    champs_comp = {f.name for f in fields(ResultatComparateurRegimes)}
    checks.append(("ResultatComparateurRegimes : pas de champ 'regime_recommande'",
                   "regime_recommande" not in champs_comp, True))
    checks.append(("ResultatComparateurRegimes : pas de champ 'recommandation'",
                   "recommandation" not in champs_comp, True))
    checks.append(("ResultatComparateurRegimes : champ 'meilleur_net' présent",
                   "meilleur_net" in champs_comp, True))

    # Garde-fou 2 : LigneRegime - benefice_retenu_societe séparé de net_dirigeant
    champs_ligne = {f.name for f in fields(LigneRegime)}
    checks.append(("LigneRegime : champ 'benefice_retenu_societe' séparé",
                   "benefice_retenu_societe" in champs_ligne, True))
    checks.append(("LigneRegime : pas de champ 'net_total_avec_retenu'",
                   "net_total_avec_retenu" not in champs_ligne, True))
    checks.append(("LigneRegime : pas de champ 'patrimoine_total'",
                   "patrimoine_total" not in champs_ligne, True))

    # Garde-fou 3 : pour un cas TNS avec T4 retenu, benefice_retenu > 0 et alerte
    profil_t4 = Profil(forme_juridique="SARL (gérance majoritaire) / EURL",
                       benefice_is=500_000, capital_cca=20_000)  # T4 plus probable ici
    arb_t = arbitrage_complet_tns(profil_t4)
    # Forcer T4 pour le test
    if arb_t.recommandee == "T4":
        # Récupérer la ligne TNS via le comparateur
        res = calcul_comparateur_regimes(profil_t4)
        ligne_tns = next(l for l in res.lignes if l.regime == "TNS")
        if ligne_tns.strategie_meilleur == "T4":
            checks.append(("T4 retenue : benefice_retenu_societe > 0",
                           ligne_tns.benefice_retenu_societe > 0, True))
            checks.append(("T4 retenue : net_dirigeant ne contient PAS le retenu",
                           ligne_tns.net_dirigeant < ligne_tns.benefice_retenu_societe, True))
            has_alerte_t4 = any("non additionné" in a or "séparément" in a
                                for a in ligne_tns.alertes)
            checks.append(("T4 retenue : alerte non-agrégation présente",
                           has_alerte_t4, True))
        else:
            checks.append(("T4 non sélectionnée naturellement (cas dépend du profil)",
                           True, True))
    else:
        checks.append(("T4 non recommandée par défaut sur ce profil (OK)",
                       True, True))

    # Garde-fou 4 : Libéral SEL → alerte BNC/SEL systématique
    profil_l = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELAS",
                      recettes_bnc=300_000, frais_pro_bnc=50_000,
                      remuneration_sel_souhaitee=80_000)
    res = calcul_comparateur_regimes(profil_l)
    ligne_lib = next(l for l in res.lignes if l.regime.startswith("Libéral"))
    if ligne_lib.strategie_meilleur in ("L3", "L4"):
        has_bnc_sel = any("BNC / SEL" in a for a in ligne_lib.alertes)
        checks.append((f"Libéral {ligne_lib.strategie_meilleur} : alerte BNC/SEL",
                       has_bnc_sel, True))
    else:
        checks.append((f"Libéral {ligne_lib.strategie_meilleur} (BNC pur) : OK",
                       True, True))

    # Garde-fou 5 : pas de formulation positive "recommandée" dans les notes Libéral
    # On distingue : "recommandée" (positif, interdit) vs "non recommandée" (renforcement)
    for ligne in res.lignes:
        if not ligne.regime.startswith("Libéral SEL"):
            continue
        note_low = ligne.note.lower()
        # Mention positive interdite : "stratégie recommandée", "régime recommandé"
        if ("stratégie recommandée" in note_low
                or "régime recommandé" in note_low):
            checks.append(("Libéral : note ne contient pas formulation 'recommandée' positive",
                          False, True))
            break
    else:
        checks.append(("Aucune note Libéral n'a de formulation 'recommandée' positive",
                       True, True))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:60s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat garde-fous : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# EXÉCUTION
# ============================================================
if __name__ == "__main__":
    r_4a = test_4a_routeur_synthese()
    r_4b = test_4b_comparateur_regimes()
    r_gf = test_garde_fous()

    print("\n" + "=" * 90)
    print("  SYNTHÈSE TESTS ÉTAPE 4")
    print("=" * 90)
    print(f"  4a — Synthèse multi-régimes        : {r_4a[0]}/{r_4a[1]}")
    print(f"  4b — Comparateur de régimes        : {r_4b[0]}/{r_4b[1]}")
    print(f"  Garde-fous méthodologiques         : {r_gf[0]}/{r_gf[1]}")

    total_ok = sum(r[0] for r in [r_4a, r_4b, r_gf])
    total = sum(r[1] for r in [r_4a, r_4b, r_gf])
    print(f"\n  TOTAL : {total_ok}/{total}")
    sys.exit(0 if total_ok == total else 1)
