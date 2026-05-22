"""
Tests de cohérence Comparateur Option 2.

Test 1 : PEE seul, sans PERO, routage v19 par défaut → PARITÉ V19 STRICTE
Test 2 : PERECO substitué à PEE → divergence attendue documentée
Test 3 : PERO activé + dirigeant éligible → extension validée par cohérence interne

Tolérance Test 1 : 0,01 €
Tolérance Tests 2 et 3 : validation par cohérence interne (sommes, signes, plafonds)
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from core.profil import Profil
from strategy.comparateur import (
    calcul_comparateur, ConfigComparateur, FluxEpargne,
    PLAF_CUMUL_ABONDEMENTS, PLAF_ABO_PERECO, FS_PERO, FS_ABO_PERECO,
)


def fmt(v):
    if v is None: return "       None"
    if isinstance(v, (int, float)): return f"{v:>15,.4f}"
    return f"{str(v):>15s}"


def comparer(label, py, xl, tol=0.01):
    if xl is None: return None, f"  ⚠ {label:55s}"
    if py is None: return False, f"  ✗ {label:55s} Python=None  Excel={fmt(xl)}"
    if isinstance(xl, str):
        try: xl = float(xl)
        except: return None, f"  ⚠ {label:55s} Excel non numérique"
    ecart = py - xl
    ok = abs(ecart) <= tol
    marker = "✓" if ok else "✗"
    return ok, f"  {marker} {label:55s} Python={fmt(py)}  Excel={fmt(xl)}  écart={ecart:+10,.4f}"


# ============================================================
# TEST 1 - PARITÉ V19 STRICTE (PEE seul, sans PERO)
# ============================================================
def test_1_parite_v19():
    """
    Configuration v19 par défaut :
    - Réceptacles : PEE + PERECO + PERIN (PERO désactivé)
    - Pas d'éligibilité PERO
    - Tous les flux v19 activés, dispositifs autonomes v19
    - Routage par défaut v19 : participation/intéressement → PEE,
      abondement PEE → PEE, abondement PERECO → PERECO, versement → PERIN
    """
    print("=" * 110)
    print("  TEST 1 — PARITÉ V19 STRICTE (configuration sans PERO)")
    print("=" * 110)

    profil = Profil(
        forme_juridique="SAS / SASU",
        effectif="11-49 salariés",
        situation="Marié / pacsé",
        parts=2.0,
        autres_revenus=0,
        dividendes_foyer_hors_enveloppe=0,
        enveloppe=120_000,
    )

    config = ConfigComparateur(
        pee_actif=True, pereco_actif=True, pero_actif=False, perin_actif=True,
        dirigeant_eligible_pero=False,
        participation=FluxEpargne(True, 1500, "PEE"),
        interessement=FluxEpargne(True, 2500, "PEE"),
        abondement_pee=FluxEpargne(True, 1500, "PEE"),
        abondement_pereco=FluxEpargne(True, 3000, "PERECO"),
        versement_perin=FluxEpargne(True, 5000, "PERIN"),
        avantages_actif=True, avantages_montant=3600,
        tr_actif=True, tr_montant=1742,
        cesu_actif=True, cesu_montant=2000,
        cado_actif=True, cado_montant=500,
        mutuelle_actif=True, mutuelle_montant=1200,
        ik_actif=False, ik_montant=0,
        cashback_actif=False, cashback_montant=360,
    )

    res = calcul_comparateur(profil, config)

    # Cibles v19 (cas par défaut)
    # Section A
    cibles_section_a = {
        "Revenu imposable par part (C6)": 33_000.00,
        "TMI estimée (C7)": 0.30,
        "Forfait social Participation (C8)": 0.00,
        "Forfait social Intéressement (C9)": 0.00,
        "Forfait social Abondement (C10)": 0.00,
    }

    valeurs_python_a = {
        "Revenu imposable par part (C6)": res.revenu_imposable_par_part,
        "TMI estimée (C7)": res.tmi_estimee,
        "Forfait social Participation (C8)": res.forfait_social_participation,
        "Forfait social Intéressement (C9)": res.forfait_social_interessement,
        "Forfait social Abondement (C10)": res.forfait_social_abondement_pee,
    }

    # Cibles matrice v19 (lignes 14-27 du Comparateur)
    # Note : abondement PERECO en v19 utilise FS_ABO_PEE (effectif), mais en Option 2
    # on a routé l'abondement_pereco vers PERECO donc FS = 0 %. Sauf que pour 11-49 sal.
    # FS_ABO_PEE = 0 %, donc le résultat reste identique. C'est volontaire pour Test 1.
    cibles_matrice = {
        # Ligne salaire (idx 0)
        ("Salaire", "montant_input"): 84_507.0423,
        ("Salaire", "cout_societe"): 120_000.00,
        ("Salaire", "cotis_ps"): 18_194.5775,
        ("Salaire", "net_imposable"): 68_720.2817,
        ("Salaire", "ir_estime"): 20_616.0845,
        ("Salaire", "net_apres_ir"): 45_696.3803,
        ("Salaire", "ratio_net_cout"): 0.3808,
        ("Salaire", "score_ajuste"): 0.3808,
        # Dividendes (idx 1)
        ("Dividendes", "montant_input"): 10_000.00,
        ("Dividendes", "cout_societe"): 13_333.3333,
        ("Dividendes", "cotis_ps"): 3_140.00,
        ("Dividendes", "net_apres_ir"): 6_860.00,
        ("Dividendes", "ratio_net_cout"): 0.5145,
        # Participation (idx 2)
        ("Participation", "montant_input"): 1_500.00,
        ("Participation", "cout_societe"): 1_500.00,
        ("Participation", "cotis_ps"): 145.50,
        ("Participation", "net_apres_ir"): 1_354.50,
        ("Participation", "ratio_net_cout"): 0.9030,
        ("Participation", "score_ajuste"): 0.9030,
        # Intéressement (idx 3)
        ("Intéressement", "montant_input"): 2_500.00,
        ("Intéressement", "cout_societe"): 2_500.00,
        ("Intéressement", "cotis_ps"): 242.50,
        ("Intéressement", "net_apres_ir"): 2_257.50,
        # Abondement PEE (idx 4)
        ("Abondement PEE", "cout_societe"): 1_500.00,
        ("Abondement PEE", "net_apres_ir"): 1_354.50,
        # Abondement PERECO (idx 5) - en v19, mêmes valeurs que PEE pour effectif 11-49
        ("Abondement PERECO", "cout_societe"): 3_000.00,
        ("Abondement PERECO", "net_apres_ir"): 2_709.00,
        # PERIN (idx 6)
        ("PERIN", "montant_input"): 5_000.00,
        ("PERIN", "cout_societe"): 0.00,
        ("PERIN", "cout_beneficiaire"): 3_500.00,
        ("PERIN", "net_imposable"): -5_000.00,
        ("PERIN", "ir_estime"): -1_500.00,
        ("PERIN", "net_apres_ir"): 1_500.00,
        # Avantages en nature (idx 7)
        ("Avantages", "cout_societe"): 5_112.00,
        ("Avantages", "cotis_ps"): 672.5160,
        ("Avantages", "net_imposable"): 2_927.4840,
        ("Avantages", "ir_estime"): 878.2452,
        ("Avantages", "net_apres_ir"): 2_049.2388,
        # TR (idx 8)
        ("TR", "cout_societe"): 1_742.00,
        ("TR", "net_apres_ir"): 1_742.00,
        # CESU (idx 9)
        ("CESU", "cout_societe"): 2_000.00,
        ("CESU", "net_apres_ir"): 2_000.00,
        # Cadeaux (idx 10)
        ("Cadeaux", "net_apres_ir"): 500.00,
        # Mutuelle (idx 11)
        ("Mutuelle", "cout_societe"): 1_200.00,
        ("Mutuelle", "cotis_ps"): 116.40,
        ("Mutuelle", "net_apres_ir"): 1_083.60,
    }

    # Mapping idx → label court
    LABELS = {0: "Salaire", 1: "Dividendes", 2: "Participation", 3: "Intéressement",
              4: "Abondement PEE", 5: "Abondement PERECO", 6: "PERIN",
              7: "Avantages", 8: "TR", 9: "CESU", 10: "Cadeaux", 11: "Mutuelle"}

    ok_count = 0
    total_count = 0

    # Comparer Section A
    print("\n  -- Section A : Paramètres dérivés --")
    for label, cible in cibles_section_a.items():
        ok, ligne = comparer(label, valeurs_python_a[label], cible)
        print(ligne)
        if ok is not None:
            total_count += 1
            if ok: ok_count += 1

    # Comparer matrice
    print("\n  -- Section B : Matrice des dispositifs --")
    for (idx_label, attr), cible in cibles_matrice.items():
        # Trouver l'index correspondant au label
        idx = next(i for i, lbl in LABELS.items() if lbl == idx_label)
        py_val = getattr(res.lignes[idx], attr)
        ok, ligne = comparer(f"{idx_label}.{attr}", py_val, cible)
        print(ligne)
        if ok is not None:
            total_count += 1
            if ok: ok_count += 1

    print(f"\n  RÉSULTAT TEST 1 : {ok_count}/{total_count} cellules en parité")
    return ok_count, total_count, res


# ============================================================
# TEST 2 - PERECO substitué à PEE (divergence attendue documentée)
# ============================================================
def test_2_pereco_substitue():
    """
    Configuration : on route la participation et l'intéressement vers PERECO
    au lieu de PEE. Le forfait social devient 0 % au lieu de l'effectif.
    
    Pour effectif "≥ 250 salariés", divergence v19 = 20 % FS, Option 2 = 0 % FS.
    """
    print("\n" + "=" * 110)
    print("  TEST 2 — PERECO substitué à PEE (extension PACTE - divergence attendue)")
    print("=" * 110)

    profil = Profil(
        forme_juridique="SAS / SASU",
        effectif="≥ 250 salariés",  # Effectif qui déclenche FS 20% en PEE
        situation="Marié / pacsé",
        parts=2.0,
        autres_revenus=0,
        enveloppe=120_000,
    )

    config = ConfigComparateur(
        pee_actif=True, pereco_actif=True, pero_actif=False,
        dirigeant_eligible_pero=False,
        participation=FluxEpargne(True, 1500, "PERECO"),  # ← routé PERECO
        interessement=FluxEpargne(True, 2500, "PERECO"),   # ← routé PERECO
        abondement_pee=FluxEpargne(True, 0, "PEE"),
        abondement_pereco=FluxEpargne(True, 3000, "PERECO"),
        versement_perin=FluxEpargne(False, 0, "PERIN"),
        avantages_actif=False, tr_actif=False, cesu_actif=False,
        cado_actif=False, mutuelle_actif=False, ik_actif=False, cashback_actif=False,
    )

    res = calcul_comparateur(profil, config)

    # Validations par cohérence interne :
    # 1. Coût société participation = montant × (1 + 0) = montant brut (pas de FS)
    # 2. Coût société intéressement = idem
    # 3. Si on avait routé en PEE avec effectif ≥250, FS = 20%
    
    checks = []
    
    # Participation routée PERECO → FS = 0 %
    part_cout = res.lignes[2].cout_societe
    if abs(part_cout - 1_500.00) <= 0.01:
        checks.append(("✓", "Participation PERECO : coût société sans forfait social", 
                       part_cout, 1500.00))
    else:
        checks.append(("✗", "Participation PERECO : coût société sans forfait social", 
                       part_cout, 1500.00))
    
    # Intéressement routé PERECO → FS = 0 %
    int_cout = res.lignes[3].cout_societe
    if abs(int_cout - 2_500.00) <= 0.01:
        checks.append(("✓", "Intéressement PERECO : coût société sans forfait social",
                       int_cout, 2500.00))
    else:
        checks.append(("✗", "Intéressement PERECO : coût société sans forfait social",
                       int_cout, 2500.00))
    
    # Vue consolidée PERECO : doit contenir Participation + Intéressement + Abondement
    pereco_view = next(r for r in res.receptacles if r.nom == "PERECO")
    flux_pereco_total = sum(m for _, m in pereco_view.flux_entrants)
    if abs(flux_pereco_total - 7_000.00) <= 0.01:
        checks.append(("✓", "Vue PERECO : total des flux routés", flux_pereco_total, 7000.00))
    else:
        checks.append(("✗", "Vue PERECO : total des flux routés", flux_pereco_total, 7000.00))
    
    # Vue consolidée PEE : doit être à 0 (aucun flux routé)
    pee_view = next(r for r in res.receptacles if r.nom == "PEE")
    flux_pee_total = sum(m for _, m in pee_view.flux_entrants)
    if abs(flux_pee_total - 0) <= 0.01:
        checks.append(("✓", "Vue PEE : aucun flux routé (vide attendu)", flux_pee_total, 0))
    else:
        checks.append(("✗", "Vue PEE : aucun flux routé (vide attendu)", flux_pee_total, 0))
    
    # Alerte info "Lecture consolidée prudente" doit être présente
    alerte_lecture = any("Lecture consolidée" in a.titre for a in res.alertes)
    if alerte_lecture:
        checks.append(("✓", "Alerte 'Lecture consolidée prudente' présente", "OK", "OK"))
    else:
        checks.append(("✗", "Alerte 'Lecture consolidée prudente' présente", "manquante", "OK"))
    
    print("\n  Validations par cohérence interne :")
    ok_count = 0
    total = len(checks)
    for marker, label, py, expected in checks:
        print(f"  {marker} {label:60s} obtenu={py}  attendu={expected}")
        if marker == "✓": ok_count += 1
    
    # Documentation de la divergence
    print(f"\n  DIVERGENCE V19 ATTENDUE :")
    print(f"    En v19 (effectif ≥250) : participation routée PEE → FS 20 % → coût 1 800 €")
    print(f"    En Option 2 PERECO    : participation routée PERECO → FS 0 % → coût 1 500 €")
    print(f"    Justification : PACTE - abondement PERECO universellement exonéré")
    
    print(f"\n  RÉSULTAT TEST 2 : {ok_count}/{total} validations cohérence interne")
    return ok_count, total, res


# ============================================================
# TEST 3 - PERO activé + dirigeant éligible (extension hors v19)
# ============================================================
def test_3_pero_actif():
    """
    Configuration : PERO activé sur dirigeant assimilé salarié éligible.
    Saisie en pourcentage (3 % de la rémunération brute).
    
    Validations :
    - La ligne PERO existe et a un score
    - Le montant PERO est correctement calculé
    - Le forfait social PERO 8 % est appliqué
    - La vue consolidée PERO existe
    - Si le plafond cumulé est dépassé, une alerte d'erreur apparaît
    """
    print("\n" + "=" * 110)
    print("  TEST 3 — PERO activé sur dirigeant éligible (extension hors v19)")
    print("=" * 110)

    profil = Profil(
        forme_juridique="SAS / SASU",
        effectif="11-49 salariés",
        situation="Marié / pacsé",
        parts=2.0,
        enveloppe=120_000,
    )

    config = ConfigComparateur(
        pee_actif=True, pereco_actif=True, pero_actif=True, perin_actif=True,
        dirigeant_eligible_pero=True,   # ← éligibilité cochée
        participation=FluxEpargne(True, 1500, "PEE"),
        interessement=FluxEpargne(True, 2500, "PEE"),
        abondement_pee=FluxEpargne(True, 1000, "PEE"),       # 1 000 €
        abondement_pereco=FluxEpargne(True, 2000, "PERECO"), # 2 000 €
        versement_perin=FluxEpargne(True, 5000, "PERIN"),
        pero_mode_saisie="pourcentage",
        pero_taux=0.03,   # 3 % de la rém brute
        avantages_actif=False, tr_actif=True, tr_montant=1742,
        cesu_actif=True, cesu_montant=2000,
        cado_actif=False, mutuelle_actif=True, mutuelle_montant=1200,
        ik_actif=False, cashback_actif=False,
    )

    res = calcul_comparateur(profil, config)

    checks = []
    
    # Montant PERO calculé : 3 % × (120 000 / 1,42) = 3 % × 84 507,04 = 2 535,21
    montant_pero_attendu = 0.03 * (120_000 / 1.42)
    pero_ligne = res.lignes[14]
    if abs(pero_ligne.montant_input - montant_pero_attendu) <= 0.01:
        checks.append(("✓", "Montant PERO calculé (3% × rém brute)",
                       pero_ligne.montant_input, montant_pero_attendu))
    else:
        checks.append(("✗", "Montant PERO calculé (3% × rém brute)",
                       pero_ligne.montant_input, montant_pero_attendu))
    
    # Coût société PERO = montant × (1 + 8 %) = forfait social 8 %
    cout_pero_attendu = montant_pero_attendu * (1 + FS_PERO)
    if abs(pero_ligne.cout_societe - cout_pero_attendu) <= 0.01:
        checks.append(("✓", "Coût société PERO (FS 8 %)",
                       pero_ligne.cout_societe, cout_pero_attendu))
    else:
        checks.append(("✗", "Coût société PERO (FS 8 %)",
                       pero_ligne.cout_societe, cout_pero_attendu))
    
    # CSG/CRDS PERO = montant × 9,7 %
    csg_pero_attendu = montant_pero_attendu * 0.097
    if abs(pero_ligne.cotis_ps - csg_pero_attendu) <= 0.01:
        checks.append(("✓", "CSG/CRDS PERO (9,7 %)",
                       pero_ligne.cotis_ps, csg_pero_attendu))
    else:
        checks.append(("✗", "CSG/CRDS PERO (9,7 %)",
                       pero_ligne.cotis_ps, csg_pero_attendu))
    
    # Net après IR PERO = montant - CSG/CRDS
    net_pero_attendu = montant_pero_attendu - csg_pero_attendu
    if abs(pero_ligne.net_apres_ir - net_pero_attendu) <= 0.01:
        checks.append(("✓", "Net après IR PERO",
                       pero_ligne.net_apres_ir, net_pero_attendu))
    else:
        checks.append(("✗", "Net après IR PERO",
                       pero_ligne.net_apres_ir, net_pero_attendu))
    
    # Coefficient de risque = 0,90
    if abs(pero_ligne.coef_risque - 0.90) <= 0.001:
        checks.append(("✓", "Coefficient de risque PERO = 0,90",
                       pero_ligne.coef_risque, 0.90))
    else:
        checks.append(("✗", "Coefficient de risque PERO = 0,90",
                       pero_ligne.coef_risque, 0.90))
    
    # Score = ratio × coef_risque
    score_attendu = pero_ligne.ratio_net_cout * 0.90
    if abs(pero_ligne.score_ajuste - score_attendu) <= 0.001:
        checks.append(("✓", "Score ajusté PERO",
                       pero_ligne.score_ajuste, score_attendu))
    else:
        checks.append(("✗", "Score ajusté PERO",
                       pero_ligne.score_ajuste, score_attendu))
    
    # Vue consolidée PERO existe
    pero_view = next((r for r in res.receptacles if r.nom == "PERO"), None)
    if pero_view and pero_view.actif and pero_view.montant_total > 0:
        checks.append(("✓", "Vue consolidée PERO active",
                       f"{pero_view.montant_total:.2f}", ">0"))
    else:
        checks.append(("✗", "Vue consolidée PERO active",
                       "absente/vide", "active"))
    
    # Plafond cumulé : abondement PEE (1000) + PERECO (2000) + PERO (2535,21) = 5535,21
    # < 7689,60 → pas d'alerte d'erreur sur le cumul
    cumul = 1000 + 2000 + montant_pero_attendu
    alerte_cumul_error = any(a.severite == "error" and "Cumul" in a.titre for a in res.alertes)
    if cumul < PLAF_CUMUL_ABONDEMENTS and not alerte_cumul_error:
        checks.append(("✓", f"Pas d'alerte cumul (cumul {cumul:.2f} < plafond {PLAF_CUMUL_ABONDEMENTS:.2f})",
                       "absente", "absente"))
    elif cumul >= PLAF_CUMUL_ABONDEMENTS and alerte_cumul_error:
        checks.append(("✓", f"Alerte cumul présente (cumul {cumul:.2f} >= plafond)",
                       "présente", "présente"))
    else:
        checks.append(("✗", "Cohérence alerte cumul",
                       "incohérent", "cohérent"))
    
    print("\n  Validations par cohérence interne :")
    ok_count = 0
    total = len(checks)
    for marker, label, py, expected in checks:
        if isinstance(py, float) and isinstance(expected, float):
            print(f"  {marker} {label:55s} obtenu={py:>12,.2f}  attendu={expected:>12,.2f}")
        else:
            print(f"  {marker} {label:55s} obtenu={py}  attendu={expected}")
        if marker == "✓": ok_count += 1
    
    print(f"\n  RÉSULTAT TEST 3 : {ok_count}/{total} validations cohérence interne")
    return ok_count, total, res


# ============================================================
# EXÉCUTION
# ============================================================
if __name__ == "__main__":
    r1 = test_1_parite_v19()
    r2 = test_2_pereco_substitue()
    r3 = test_3_pero_actif()
    
    print("\n" + "=" * 110)
    print("  SYNTHÈSE TESTS DE COHÉRENCE COMPARATEUR")
    print("=" * 110)
    print(f"  Test 1 (parité v19 stricte)        : {r1[0]}/{r1[1]}")
    print(f"  Test 2 (PERECO extension PACTE)   : {r2[0]}/{r2[1]}")
    print(f"  Test 3 (PERO extension Option 2)  : {r3[0]}/{r3[1]}")
    print(f"  TOTAL                              : {r1[0]+r2[0]+r3[0]}/{r1[1]+r2[1]+r3[1]}")
