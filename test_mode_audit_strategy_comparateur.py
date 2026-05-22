"""
test_mode_audit_strategy_comparateur.py — Tests dédiés à l'instrumentation
MODE_AUDIT du strategy/comparateur (G3d, spec 1.1.0).

Spécificités G3d :
- **Namespace dédié `COMP_*`** (pas `STRAT_*`) : ce module est un
  comparateur/réceptacle, pas une stratégie mono-régime classique.
- **Aucune sous-trace attachée** : `strategy/comparateur.py` n'importe
  ni `regime/*` ni `strategy/{tns,liberal,assimile}.py`. La trace est
  plate, structurée par `parent_id`. Premier module G3 sans imbrication.
- **Risque sémantique maximal** : top 3 facilement perçu comme prescriptif.
  Discipline renforcée : labels strictement mécaniques (« rang dans le
  classement par score »), pas de « meilleur/optimal/recommandé ».
- **6 alertes structurelles** (5 conditionnelles + 1 info systématique) :
  wording métier intégral en `hypotheses["textes_alertes_integraux"]`,
  counts factuels par sévérité dans la trace.

Vérifie :
1. Rétrocompat parfaite (audit=None ⇒ comportement historique)
2. Structure section A (6 codes paramètres dérivés)
3. Structure section B (1 NB_LIGNES + 15 LIGNE_<NN>_*)
4. Structure top 3 (CRITERE + NB + 0 à 3 RANG_*)
5. Structure réceptacles (NB + 4 RECEPTACLE_*)
6. Structure alertes (NB + 3 counts par sévérité)
7. Cohérence valeurs tracées vs `ResultatComparateur`
8. Résolution doctrinale
9. Aucune sous-trace attachée (le module est autonome)
10. Isolation `COMP_*` ⊥ {`STRAT_*`, `TNS_*`, `LIB_*`, `SAL_*`, `ASSIM_*`}
11. **Test non-prescriptif** : 0 wording prescriptif sur tout le graphe
12. Top 3 : labels mécaniques (pas de « meilleur », « gagnant »)
13. Alertes : wording métier en hypotheses, pas en label/notes
14. Rendu console fonctionnel

Usage : python3 test_mode_audit_strategy_comparateur.py
Exit code 0 si tous les tests passent.
"""

import sys
import re

from core.profil import Profil
from core.audit import (
    TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref,
)
from strategy.comparateur import (
    calcul_comparateur, ConfigComparateur,
)
from ui.audit_render import rendre_trace_console


# ============================================================
# REGISTRES — Contrat G3d
# ============================================================
CODES_SECTION_A = {
    "COMP_REVENU_IMPOSABLE_PAR_PART",
    "COMP_TMI_ESTIMEE",
    "COMP_FS_PARTICIPATION",
    "COMP_FS_INTERESSEMENT",
    "COMP_FS_ABO_PEE",
    "COMP_MONTANT_PERO",
}

CODES_LIGNES_ATTENDUS = {
    "COMP_NB_LIGNES",
    "COMP_LIGNE_00_SALAIRE",
    "COMP_LIGNE_01_DIVIDENDES",
    "COMP_LIGNE_02_PARTICIPATION",
    "COMP_LIGNE_03_INTERESSEMENT",
    "COMP_LIGNE_04_ABONDEMENT_PEE",
    "COMP_LIGNE_05_ABONDEMENT_PERECO",
    "COMP_LIGNE_06_PERIN",
    "COMP_LIGNE_07_AVANTAGES_NATURE",
    "COMP_LIGNE_08_TICKETS_RESTAURANT",
    "COMP_LIGNE_09_CESU",
    "COMP_LIGNE_10_CHEQUES_CADEAUX",
    "COMP_LIGNE_11_MUTUELLE",
    "COMP_LIGNE_12_INDEMNITES_KILOMETRIQUES",
    "COMP_LIGNE_13_CASHBACK",
    "COMP_LIGNE_14_PERO",
}

CODES_TOP3_BASE = {  # toujours présents
    "COMP_TOP3_CRITERE",
    "COMP_TOP3_NB",
}

CODES_RECEPTACLES = {
    "COMP_NB_RECEPTACLES",
    "COMP_RECEPTACLE_PEE",
    "COMP_RECEPTACLE_PERECO",
    "COMP_RECEPTACLE_PERO",
    "COMP_RECEPTACLE_PERIN",
}

CODES_ALERTES = {
    "COMP_ALERTES_NB",
    "COMP_ALERTES_ERROR_NB",
    "COMP_ALERTES_WARNING_NB",
    "COMP_ALERTES_INFO_NB",
}


# ============================================================
# VOCABULAIRE PRESCRIPTIF INTERDIT (élargi G3b à \boptim\w*\b)
# ============================================================
TERMES_INTERDITS = [
    r"\boptim\w*\b",
    r"\bmeilleur(?:e|s|es)?\b",
    r"\bgagnant(?:e|s|es)?\b",
    r"\bperdant(?:e|s|es)?\b",
    r"\bavantageu(?:x|se|ses)\b",
    r"\brecommand(?:é|ée|és|ées|er|ation|ations)\b",
    r"\bpréconis(?:é|ée|er|ation)\b",
    r"\bconseill(?:é|ée|er)\b",
    r"\bidéal(?:e|s|es)?\b",
    r"\bparfait(?:e|s|es)?\b",
    r"\bsupérieur(?:e|s|es)?\b",
    r"\binférieur(?:e|s|es)?\b",
]


# ============================================================
# OUTIL DE TEST
# ============================================================
TOL = 0.001
echecs = []


def check(label, condition, detail=""):
    marker = "✓" if condition else "✗"
    suffix = f"  ({detail})" if detail else ""
    print(f"  {marker} {label}{suffix}")
    if not condition:
        echecs.append(label)


# ============================================================
# TEST 1 — RÉTROCOMPAT
# ============================================================
print("=" * 95)
print("  TEST 1 — Rétrocompat parfaite (audit=None ⇒ comportement historique)")
print("=" * 95)

profil = Profil()
config = ConfigComparateur()

r_sans = calcul_comparateur(profil, config)
trace = TraceAudit(regime="Strategy/Comparateur")
r_avec = calcul_comparateur(profil, config, audit=trace)

# Comparaison attribut par attribut
import dataclasses
all_eq = True
for f in dataclasses.fields(type(r_sans)):
    v_sans = getattr(r_sans, f.name)
    v_avec = getattr(r_avec, f.name)
    if isinstance(v_sans, float):
        if abs(v_sans - v_avec) >= TOL:
            all_eq = False
            check(f"Attribut {f.name}", False, f"sans={v_sans} avec={v_avec}")
    elif v_sans != v_avec:
        all_eq = False
        check(f"Attribut {f.name}", False)
check("Tous les attributs scalaires identiques avec/sans audit", all_eq)

# Lignes : comparaison structurelle
check("Même nombre de lignes",
      len(r_sans.lignes) == len(r_avec.lignes) == 15)
check("Lignes identiques (net_apres_ir)",
      all(abs(l1.net_apres_ir - l2.net_apres_ir) < TOL
          for l1, l2 in zip(r_sans.lignes, r_avec.lignes)))
check("Réceptacles identiques (montant_total)",
      all(abs(r1.montant_total - r2.montant_total) < TOL
          for r1, r2 in zip(r_sans.receptacles, r_avec.receptacles)))
check("Alertes identiques (nombre + titres)",
      len(r_sans.alertes) == len(r_avec.alertes) and
      all(a1.titre == a2.titre for a1, a2 in zip(r_sans.alertes, r_avec.alertes)))


# ============================================================
# TEST 2 — STRUCTURE SECTION A
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure section A (paramètres dérivés, 6 codes)")
print("=" * 95)

codes_obtenus = set(trace.codes())
manquants_a = CODES_SECTION_A - codes_obtenus
check(f"Section A : {len(CODES_SECTION_A)} codes attendus présents",
      not manquants_a, f"manquants={manquants_a}")

# Toutes les étapes section A sont des racines (pas de parent_id)
for c in CODES_SECTION_A:
    e = trace.get(c)
    check(f"  {c} est une racine",
          e is not None and e.parent_id is None)


# ============================================================
# TEST 3 — STRUCTURE LIGNES (1 NB + 15 LIGNE_*)
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Structure lignes (1 NB_LIGNES + 15 LIGNE_<NN>_*)")
print("=" * 95)

manquants_l = CODES_LIGNES_ATTENDUS - codes_obtenus
check(f"Lignes : {len(CODES_LIGNES_ATTENDUS)} codes attendus présents",
      not manquants_l, f"manquants={manquants_l}")

# COMP_NB_LIGNES est racine ; toutes les LIGNE_<NN>_* ont NB_LIGNES pour parent
for c in CODES_LIGNES_ATTENDUS:
    e = trace.get(c)
    if c == "COMP_NB_LIGNES":
        check(f"  {c} est racine",
              e.parent_id is None)
    else:
        check(f"  {c} a parent_id = COMP_NB_LIGNES",
              e.parent_id == "COMP_NB_LIGNES")

# Valeur de NB_LIGNES = 15
nb_lignes = trace.get("COMP_NB_LIGNES")
check("COMP_NB_LIGNES.valeur == 15", abs(nb_lignes.valeur - 15.0) < TOL)

# Convention de nommage idx_NOM_COURT
nom_courts_attendus = {
    "00_SALAIRE", "01_DIVIDENDES", "02_PARTICIPATION", "03_INTERESSEMENT",
    "04_ABONDEMENT_PEE", "05_ABONDEMENT_PERECO", "06_PERIN", "07_AVANTAGES_NATURE",
    "08_TICKETS_RESTAURANT", "09_CESU", "10_CHEQUES_CADEAUX", "11_MUTUELLE",
    "12_INDEMNITES_KILOMETRIQUES", "13_CASHBACK", "14_PERO",
}
suffixes_obtenus = {c.replace("COMP_LIGNE_", "")
                    for c in codes_obtenus if c.startswith("COMP_LIGNE_")}
check("Convention COMP_LIGNE_<NN>_<NOM> respectée",
      suffixes_obtenus == nom_courts_attendus,
      f"diff={suffixes_obtenus ^ nom_courts_attendus}")


# ============================================================
# TEST 4 — STRUCTURE TOP 3 (CRITERE + NB + 0..3 RANG)
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Structure top 3 (CRITERE + NB + 0 à 3 RANG_*)")
print("=" * 95)

manquants_top3 = CODES_TOP3_BASE - codes_obtenus
check(f"Top 3 base : {len(CODES_TOP3_BASE)} codes attendus présents",
      not manquants_top3, f"manquants={manquants_top3}")

# COMP_TOP3_NB doit refléter le nombre effectif de lignes classées
nb_top3_dans_trace = trace.get("COMP_TOP3_NB").valeur
nb_top3_effectif = sum(1 for l in r_avec.lignes if l.top3_rang is not None)
check(f"COMP_TOP3_NB = nb lignes classées effectivement ({nb_top3_effectif})",
      abs(nb_top3_dans_trace - nb_top3_effectif) < TOL)

# Pour chaque ligne classée, il doit exister une étape COMP_TOP3_RANG_<R>
for ligne in r_avec.lignes:
    if ligne.top3_rang is not None:
        code_attendu = f"COMP_TOP3_RANG_{ligne.top3_rang}"
        check(f"  Présence {code_attendu}",
              code_attendu in codes_obtenus)
        # Et son parent doit être COMP_TOP3_CRITERE
        e = trace.get(code_attendu)
        check(f"    parent_id = COMP_TOP3_CRITERE",
              e is not None and e.parent_id == "COMP_TOP3_CRITERE")


# ============================================================
# TEST 5 — STRUCTURE RÉCEPTACLES
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Structure réceptacles (NB + 4 RECEPTACLE_*)")
print("=" * 95)

manquants_r = CODES_RECEPTACLES - codes_obtenus
check(f"Réceptacles : {len(CODES_RECEPTACLES)} codes attendus présents",
      not manquants_r, f"manquants={manquants_r}")

# Chaque RECEPTACLE_* a parent = COMP_NB_RECEPTACLES
for c in CODES_RECEPTACLES:
    e = trace.get(c)
    if c == "COMP_NB_RECEPTACLES":
        check(f"  {c} est racine", e.parent_id is None)
    else:
        check(f"  {c} a parent_id = COMP_NB_RECEPTACLES",
              e.parent_id == "COMP_NB_RECEPTACLES")


# ============================================================
# TEST 6 — STRUCTURE ALERTES
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Structure alertes (NB + 3 counts par sévérité)")
print("=" * 95)

manquants_a_count = CODES_ALERTES - codes_obtenus
check(f"Alertes : {len(CODES_ALERTES)} codes attendus présents",
      not manquants_a_count, f"manquants={manquants_a_count}")

# COMP_ALERTES_NB est racine, les 3 counts ont NB pour parent
for c in CODES_ALERTES:
    e = trace.get(c)
    if c == "COMP_ALERTES_NB":
        check(f"  {c} est racine", e.parent_id is None)
    else:
        check(f"  {c} a parent_id = COMP_ALERTES_NB",
              e.parent_id == "COMP_ALERTES_NB")

# Cohérence : total = error + warning + info
total = trace.get("COMP_ALERTES_NB").valeur
err = trace.get("COMP_ALERTES_ERROR_NB").valeur
war = trace.get("COMP_ALERTES_WARNING_NB").valeur
inf = trace.get("COMP_ALERTES_INFO_NB").valeur
check("Cohérence total = error + warning + info",
      abs(total - (err + war + inf)) < TOL,
      f"{total} vs {err}+{war}+{inf}")


# ============================================================
# TEST 7 — COHÉRENCE VALEURS TRACÉES vs RESULTATCOMPARATEUR
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Cohérence valeurs tracées vs attributs ResultatComparateur")
print("=" * 95)

mapping = {
    "COMP_REVENU_IMPOSABLE_PAR_PART": "revenu_imposable_par_part",
    "COMP_TMI_ESTIMEE": "tmi_estimee",
    "COMP_FS_PARTICIPATION": "forfait_social_participation",
    "COMP_FS_INTERESSEMENT": "forfait_social_interessement",
    "COMP_FS_ABO_PEE": "forfait_social_abondement_pee",
}
for code, attr in mapping.items():
    v_trace = trace.get(code).valeur
    v_res = getattr(r_avec, attr)
    check(f"{code} ↔ res.{attr}",
          abs(v_trace - v_res) < TOL,
          f"trace={v_trace} res={v_res}")

# Chaque LIGNE_<NN> = net_apres_ir de la ligne correspondante
for idx in range(15):
    suffixe = None
    for code in codes_obtenus:
        if code.startswith(f"COMP_LIGNE_{idx:02d}_"):
            suffixe = code
            break
    check(f"COMP_LIGNE_{idx:02d}_* présent", suffixe is not None)
    if suffixe:
        v_trace = trace.get(suffixe).valeur
        check(f"  valeur = lignes[{idx}].net_apres_ir",
              abs(v_trace - r_avec.lignes[idx].net_apres_ir) < TOL)


# ============================================================
# TEST 8 — RÉSOLUTION DOCTRINALE
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Doctrine_refs (étapes COMP_*) se résolvent")
print("=" * 95)

refs_uniques = set()
for e in trace.etapes:
    refs_uniques.update(e.doctrine_refs)

check(f"{len(refs_uniques)} doctrine_refs uniques cités",
      len(refs_uniques) >= 6)

# Au moins les plafonds IR + TX_PATRONAL doivent être cités
attendus_min = {"IR_PLAFOND_T1", "IR_PLAFOND_T2", "IR_PLAFOND_T3", "IR_PLAFOND_T4",
                "IR_TAUX_T2", "IR_TAUX_T3", "IR_TAUX_T4", "IR_TAUX_T5",
                "TX_PATRONAL"}
check("Doctrine_refs minimales présentes",
      attendus_min.issubset(refs_uniques),
      f"manquantes={attendus_min - refs_uniques}")

for ref in sorted(refs_uniques):
    try:
        valeur = resoudre_doctrine_ref(ref)
        check(f"  Résolution {ref} = {valeur}", True)
    except AttributeError as e:
        check(f"  Résolution {ref}", False, str(e))


# ============================================================
# TEST 9 — AUCUNE SOUS-TRACE ATTACHÉE
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Aucune sous-trace attachée (module autonome)")
print("=" * 95)

check("Aucune sous-trace attachée à la trace racine",
      trace.noms_sous_traces() == [],
      f"obtenu={trace.noms_sous_traces()}")
check("trace.sous_traces est un dict vide",
      trace.sous_traces == {})


# ============================================================
# TEST 10 — ISOLATION ESPACES DE CODES
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Isolation COMP_* ⊥ {STRAT_*, TNS_*, LIB_*, SAL_*, ASSIM_*}")
print("=" * 95)

prefixes_etrangers = ("STRAT_", "TNS_", "LIB_BNC_", "LIB_SEL_",
                       "SAL_", "ASSIM_")

check("Tous les codes préfixés COMP_",
      all(c.startswith("COMP_") for c in codes_obtenus))

intrus = [c for c in codes_obtenus
          if any(c.startswith(p) for p in prefixes_etrangers)]
check("Aucune intrusion d'un préfixe étranger",
      not intrus, f"intrus={intrus}")


# ============================================================
# TEST 11 — NON-PRESCRIPTIF (scan automatique)
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Aucun wording prescriptif dans labels ou notes")
print("=" * 95)

def scanner_prescriptif(t):
    violations = []
    for e in t.etapes:
        for champ, texte in (("label", e.label), ("notes", e.notes)):
            for pattern in TERMES_INTERDITS:
                if re.search(pattern, texte, re.IGNORECASE):
                    violations.append((e.code, pattern, champ, texte))
    return violations

violations = scanner_prescriptif(trace)
if violations:
    check("Aucun wording prescriptif", False,
          f"{len(violations)} violation(s)")
    for code, pattern, champ, texte in violations[:5]:
        print(f"       ⚠ {code} / {champ} : pattern={pattern} dans {texte!r}")
else:
    check(f"Aucun wording prescriptif sur {len(trace.etapes)} étapes "
          f"× 12 patterns", True)


# ============================================================
# TEST 12 — TOP 3 : LABELS MÉCANIQUES
# ============================================================
print()
print("=" * 95)
print("  TEST 12 — Top 3 : labels strictement mécaniques")
print("=" * 95)

# Le critère doit être présenté factuellement
e_critere = trace.get("COMP_TOP3_CRITERE")
check("COMP_TOP3_CRITERE valeur = formule factuelle",
      isinstance(e_critere.valeur, str) and
      "score_ajuste" in e_critere.valeur)
check("COMP_TOP3_CRITERE label = 'classement' (factuel)",
      "classement" in e_critere.label.lower())

# Les RANG_* ont des labels factuels "Rang N dans le classement par score"
for c in codes_obtenus:
    if c.startswith("COMP_TOP3_RANG_"):
        e = trace.get(c)
        check(f"  {c}.label commence par 'Rang'",
              e.label.startswith("Rang"))
        check(f"  {c}.label contient 'classement'",
              "classement" in e.label.lower())


# ============================================================
# TEST 13 — ALERTES : WORDING MÉTIER EN HYPOTHESES
# ============================================================
print()
print("=" * 95)
print("  TEST 13 — Alertes : wording métier intégral en hypotheses")
print("=" * 95)

e_alertes_nb = trace.get("COMP_ALERTES_NB")
check("COMP_ALERTES_NB.hypotheses contient 'textes_alertes_integraux'",
      "textes_alertes_integraux" in e_alertes_nb.hypotheses)
textes = e_alertes_nb.hypotheses.get("textes_alertes_integraux", [])
check(f"{len(textes)} alertes sérialisées",
      len(textes) == len(r_avec.alertes))

# Le label/notes ne contiennent PAS de wording d'alerte (URSSAF, etc.)
for c in CODES_ALERTES:
    e = trace.get(c)
    # Les notes peuvent mentionner "alertes" mais pas reproduire les textes métier
    check(f"  {c}.label ne contient pas de mot prescriptif",
          not any(re.search(p, e.label, re.IGNORECASE)
                  for p in TERMES_INTERDITS))


# ============================================================
# TEST 14 — RENDU CONSOLE
# ============================================================
print()
print("=" * 95)
print("  TEST 14 — Rendu console fonctionnel")
print("=" * 95)

rendu = rendre_trace_console(trace)
check("Rendu non-vide", len(rendu) > 3000)
check("En-tête Comparateur", "Strategy/Comparateur" in rendu)
check("Contient COMP_TOP3_CRITERE", "COMP_TOP3_CRITERE" in rendu)
check("Contient COMP_LIGNE_00_SALAIRE", "COMP_LIGNE_00_SALAIRE" in rendu)
check("Doctrine IR_PLAFOND_T1 résolue", "IR_PLAFOND_T1=" in rendu)
check("Pas de référence introuvable", "référence introuvable" not in rendu)


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Strategy/Comparateur passent (G3d)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
