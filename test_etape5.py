"""
Tests dédiés Étape 5 Phase B.2 — Réceptacles différenciés par régime.

Vérifie :
1. Fonction de résolution unique regime_effectif_receptacles()
2. Matrice §5 du Cadre v1.0.1 (accessibilité par régime effectif)
3. Filtre intégré dans calcul_comparateur (lignes accessibles/inaccessibles)
4. Exclusion des inaccessibles du Top 3
5. Mention Madelin / PER TNS systématique
6. Garde-fous (pas de duplication de la règle SELARL/SELAS ailleurs)
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from strategy.receptacles import (
    regime_effectif_receptacles,
    est_accessible, motif_inaccessibilite,
    liste_receptacles_par_regime, mention_madelin,
    MATRICE_RECEPTACLES, MADELIN_PER_TNS_MENTION,
    REGIME_EFF_ASSIMILE, REGIME_EFF_TNS, REGIME_EFF_LIBERAL_BNC, REGIME_EFF_SALARIE,
)
from strategy.comparateur import calcul_comparateur, ConfigComparateur, FluxEpargne
from core.profil import Profil


def check(label, py, expected):
    if isinstance(expected, bool):
        ok = py == expected
    elif isinstance(expected, (int, float)):
        ok = py == expected
    else:
        ok = py == expected
    return ("✓" if ok else "✗"), ok


# ============================================================
# 5.A — Fonction de résolution unique
# ============================================================
def test_resolution_unique():
    print("=" * 90)
    print("  5.A — Tests fonction unique regime_effectif_receptacles()")
    print("=" * 90)

    checks = [
        ("SAS → Assimilé",
         regime_effectif_receptacles(Profil(forme_juridique="SAS / SASU")),
         REGIME_EFF_ASSIMILE),
        ("SARL minoritaire → Assimilé",
         regime_effectif_receptacles(Profil(forme_juridique="SARL (gérance minoritaire)")),
         REGIME_EFF_ASSIMILE),
        ("SARL majoritaire / EURL → TNS",
         regime_effectif_receptacles(Profil(forme_juridique="SARL (gérance majoritaire) / EURL")),
         REGIME_EFF_TNS),
        ("EI / EI à l'IS → TNS",
         regime_effectif_receptacles(Profil(forme_juridique="EI / EI à l'IS")),
         REGIME_EFF_TNS),
        ("Profession libérale (BNC) → Libéral BNC",
         regime_effectif_receptacles(Profil(forme_juridique="Profession libérale (BNC)")),
         REGIME_EFF_LIBERAL_BNC),
        # Cas critiques SEL
        ("SELARL → TNS (règle critique)",
         regime_effectif_receptacles(Profil(forme_juridique="SELARL / SELAS", forme_sel="SELARL")),
         REGIME_EFF_TNS),
        ("SELAS → Assimilé (règle critique)",
         regime_effectif_receptacles(Profil(forme_juridique="SELARL / SELAS", forme_sel="SELAS")),
         REGIME_EFF_ASSIMILE),
    ]

    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 5.A : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 5.B — Matrice §5 du Cadre v1.0.1
# ============================================================
def test_matrice_5():
    print("\n" + "=" * 90)
    print("  5.B — Tests matrice §5 (Cadre méthodologique v1.0.1)")
    print("=" * 90)

    # Profils représentatifs
    p_assimile = Profil(forme_juridique="SAS / SASU")
    p_tns = Profil(forme_juridique="SARL (gérance majoritaire) / EURL")
    p_bnc = Profil(forme_juridique="Profession libérale (BNC)")
    p_selarl = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELARL")
    p_selas = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELAS")

    # Règles attendues
    checks = []

    # PERIN : accessible à TOUS les régimes
    for label, p in [("Assimilé", p_assimile), ("TNS", p_tns),
                      ("BNC", p_bnc), ("SELARL", p_selarl), ("SELAS", p_selas)]:
        checks.append((f"PERIN {label} : accessible", est_accessible("PERIN", p), True))

    # PEE/PERECO/PERO : accessible à Assimilé + SELAS, fermé pour TNS / BNC / SELARL
    for rec in ["PEE", "PERECO", "PERO"]:
        checks.append((f"{rec} Assimilé : accessible", est_accessible(rec, p_assimile), True))
        checks.append((f"{rec} SELAS : accessible", est_accessible(rec, p_selas), True))
        checks.append((f"{rec} TNS : fermé", est_accessible(rec, p_tns), False))
        checks.append((f"{rec} BNC : fermé", est_accessible(rec, p_bnc), False))
        checks.append((f"{rec} SELARL : fermé", est_accessible(rec, p_selarl), False))

    # Intéressement / Participation : même règle que PEE
    for rec in ["Intéressement", "Participation"]:
        checks.append((f"{rec} Assimilé : accessible", est_accessible(rec, p_assimile), True))
        checks.append((f"{rec} TNS : fermé", est_accessible(rec, p_tns), False))
        checks.append((f"{rec} SELARL : fermé", est_accessible(rec, p_selarl), False))
        checks.append((f"{rec} SELAS : accessible", est_accessible(rec, p_selas), True))

    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 5.B : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 5.C — Filtre intégré dans calcul_comparateur
# ============================================================
def test_filtre_comparateur():
    print("\n" + "=" * 90)
    print("  5.C — Tests filtre intégré dans calcul_comparateur")
    print("=" * 90)

    config = ConfigComparateur(
        participation=FluxEpargne(actif=True, montant=1500, receptacle="PEE"),
        interessement=FluxEpargne(actif=True, montant=2500, receptacle="PEE"),
        abondement_pee=FluxEpargne(actif=True, montant=1500, receptacle="PEE"),
        abondement_pereco=FluxEpargne(actif=True, montant=3000, receptacle="PERECO"),
        versement_perin=FluxEpargne(actif=True, montant=5000, receptacle="PERIN"),
    )

    # Test 1 : Assimilé → 0 inaccessible
    profil_assimile = Profil(forme_juridique="SAS / SASU")
    res_a = calcul_comparateur(profil_assimile, config)
    inacc_a = sum(1 for l in res_a.lignes if not l.accessible)

    # Test 2 : TNS → 5 inaccessibles
    profil_tns = Profil(forme_juridique="SARL (gérance majoritaire) / EURL",
                        benefice_is=200_000)
    res_t = calcul_comparateur(profil_tns, config)
    inacc_t = sum(1 for l in res_t.lignes if not l.accessible)

    # Test 3 : SELARL → traité comme TNS
    profil_selarl = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELARL")
    res_sl = calcul_comparateur(profil_selarl, config)
    inacc_sl = sum(1 for l in res_sl.lignes if not l.accessible)

    # Test 4 : SELAS → traité comme Assimilé
    profil_selas = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELAS")
    res_ss = calcul_comparateur(profil_selas, config)
    inacc_ss = sum(1 for l in res_ss.lignes if not l.accessible)

    checks = [
        # Décomptes
        ("Assimilé : 0 lignes inaccessibles", inacc_a, 0),
        ("TNS : 5 lignes inaccessibles", inacc_t, 5),
        ("SELARL : 5 lignes inaccessibles (= TNS)", inacc_sl, 5),
        ("SELAS : 0 lignes inaccessibles (= Assimilé)", inacc_ss, 0),

        # PERIN toujours accessible
        ("TNS PERIN (idx 6) : accessible", res_t.lignes[6].accessible, True),
        ("SELARL PERIN (idx 6) : accessible", res_sl.lignes[6].accessible, True),

        # Salaire et dividendes toujours accessibles
        ("TNS Salaire (idx 0) : accessible", res_t.lignes[0].accessible, True),
        ("TNS Dividendes (idx 1) : accessible", res_t.lignes[1].accessible, True),

        # Motif présent quand inaccessible
        ("TNS PEE (idx 4) : motif non vide",
         res_t.lignes[4].motif_inaccessibilite != "", True),
        ("TNS PEE motif contient 'TNS'",
         "TNS" in res_t.lignes[4].motif_inaccessibilite, True),

        # Lignes accessibles ont motif vide
        ("Assimilé toutes lignes : motif vide",
         all(l.motif_inaccessibilite == "" for l in res_a.lignes), True),
    ]

    # Top 3 : aucune ligne inaccessible dans le top 3 TNS
    top3_tns = [l for l in res_t.lignes if l.top3_rang is not None]
    checks.append(("TNS : top 3 ne contient que des lignes accessibles",
                   all(l.accessible for l in top3_tns), True))

    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 5.C : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 5.D — Mention Madelin + helpers
# ============================================================
def test_mention_madelin_et_helpers():
    print("\n" + "=" * 90)
    print("  5.D — Mention Madelin / PER TNS + fonctions utilitaires")
    print("=" * 90)

    # Mention Madelin
    mention = mention_madelin()
    checks = [
        ("mention_madelin() non vide", len(mention) > 0, True),
        ("mention_madelin() contient 'Madelin'", "Madelin" in mention, True),
        ("mention_madelin() contient 'cabinet'", "cabinet" in mention.lower(), True),
        ("mention_madelin() contient 'PERIN reste'",
         "PERIN reste" in mention, True),
        ("constante MADELIN_PER_TNS_MENTION exposée",
         isinstance(MADELIN_PER_TNS_MENTION, str), True),
    ]

    # liste_receptacles_par_regime
    profil = Profil(forme_juridique="SARL (gérance majoritaire) / EURL")
    liste = liste_receptacles_par_regime(profil)
    checks.append(("liste_receptacles_par_regime contient 6 entrées", len(liste), 6))
    checks.append(("liste : PERIN accessible pour TNS",
                   liste["PERIN"]["accessible"], True))
    checks.append(("liste : PEE inaccessible pour TNS",
                   liste["PEE"]["accessible"], False))
    checks.append(("liste : PEE motif non vide pour TNS",
                   liste["PEE"]["motif"] is not None, True))

    # motif_inaccessibilite renvoie None si accessible
    checks.append(("motif PERIN TNS : None (car accessible)",
                   motif_inaccessibilite("PERIN", profil), None))
    checks.append(("motif PEE TNS : chaîne non vide",
                   motif_inaccessibilite("PEE", profil) is not None, True))

    nb_ok = 0
    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 5.D : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# 5.E — Garde-fous (unicité de la règle SELARL/SELAS)
# ============================================================
def test_garde_fous():
    print("\n" + "=" * 90)
    print("  5.E — Garde-fous (unicité règle SELARL/SELAS)")
    print("=" * 90)

    nb_ok = 0
    checks = []

    # Garde-fou : la règle SELARL→TNS / SELAS→Assimilé ne doit pas être
    # recodée dans des modules ne traitant pas directement de la fiscalité SEL.
    #
    # Modules autorisés à utiliser forme_sel == "SELARL" / "SELAS" directement :
    # - strategy/receptacles.py  (matrice §5 — usage canonique pour réceptacles)
    # - strategy/liberal.py      (calcul fiscal selon forme SEL — usage métier propre)
    # - core/profil.py           (validation enum dans __post_init__)
    #
    # Toute apparition de cette règle dans un autre module = duplication
    # non-justifiée qu'il faut centraliser.

    import subprocess
    result = subprocess.run(
        ["grep", "-rn", '"SELARL"', "core/", "regime/", "strategy/"],
        capture_output=True, text=True, cwd="."
    )
    occurrences = result.stdout.strip().split("\n") if result.stdout else []

    MODULES_AUTORISES = (
        "strategy/receptacles.py",
        "strategy/liberal.py",
        "core/profil.py",
    )

    occurrences_problematiques = []
    for line in occurrences:
        if not line:
            continue
        # Module dans la whitelist : autorisé
        if any(m in line for m in MODULES_AUTORISES):
            continue
        # Mapping forme_juridique = "SELARL / SELAS" (label, pas une règle métier)
        if 'SELARL / SELAS' in line:
            continue
        # Sinon : duplication problématique
        if "forme_sel ==" in line or "forme_sel !=" in line:
            occurrences_problematiques.append(line)

    checks.append(("Aucune duplication règle SELARL/SELAS hors modules autorisés",
                   len(occurrences_problematiques), 0))
    if occurrences_problematiques:
        print(f"    Occurrences problématiques détectées :")
        for o in occurrences_problematiques:
            print(f"      {o}")

    # Garde-fou 2 : MATRICE_RECEPTACLES expose bien les 6 réceptacles attendus
    receptacles_attendus = {"PEE", "PERECO", "PERO", "PERIN", "Intéressement", "Participation"}
    checks.append(("MATRICE_RECEPTACLES : 6 réceptacles modélisés",
                   set(MATRICE_RECEPTACLES.keys()), receptacles_attendus))

    # Garde-fou 3 : pas de réceptacle "Madelin" dans la matrice (hors périmètre v1)
    checks.append(("Madelin PAS dans MATRICE_RECEPTACLES (hors v1)",
                   "Madelin" not in MATRICE_RECEPTACLES, True))

    for label, actuel, attendu in checks:
        marker, ok = check(label, actuel, attendu)
        print(f"  {marker} {label:55s} obtenu={actuel}")
        if ok: nb_ok += 1
    print(f"\n  Résultat 5.E : {nb_ok}/{len(checks)}")
    return nb_ok, len(checks)


# ============================================================
# EXÉCUTION
# ============================================================
if __name__ == "__main__":
    r_a = test_resolution_unique()
    r_b = test_matrice_5()
    r_c = test_filtre_comparateur()
    r_d = test_mention_madelin_et_helpers()
    r_e = test_garde_fous()

    print("\n" + "=" * 90)
    print("  SYNTHÈSE TESTS ÉTAPE 5")
    print("=" * 90)
    print(f"  5.A — Résolution unique             : {r_a[0]}/{r_a[1]}")
    print(f"  5.B — Matrice §5                    : {r_b[0]}/{r_b[1]}")
    print(f"  5.C — Filtre Comparateur            : {r_c[0]}/{r_c[1]}")
    print(f"  5.D — Mention Madelin + helpers     : {r_d[0]}/{r_d[1]}")
    print(f"  5.E — Garde-fous unicité règle      : {r_e[0]}/{r_e[1]}")

    total_ok = sum(r[0] for r in [r_a, r_b, r_c, r_d, r_e])
    total = sum(r[1] for r in [r_a, r_b, r_c, r_d, r_e])
    print(f"\n  TOTAL : {total_ok}/{total}")
    sys.exit(0 if total_ok == total else 1)
