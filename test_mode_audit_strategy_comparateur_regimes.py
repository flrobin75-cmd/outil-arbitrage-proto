"""
test_mode_audit_strategy_comparateur_regimes.py — Tests dédiés à
l'instrumentation MODE_AUDIT du strategy/comparateur_regimes (G3d-bis,
spec 1.1.0).

Spécificités G3d-bis :
- **Namespace dédié `COMP_REG_*`** (distinct de `COMP_*` du comparateur
  de dispositifs G3d). Ce module est une couche distincte —
  comparaison inter-régimes vs comparateur de dispositifs intra-régime.
- **Composition naturelle des 3 stratégies G3a/b/c + module Salarié G2a**
  conformément à §9.2 du MODE_AUDIT. Le module appelle réellement ces
  fonctions, donc il attache leurs traces.
- **Profondeur d'imbrication maximale** atteinte sur le chantier :
  6 niveaux sur la branche `comparateur_regimes → ligne_liberal →
  arbitrage_liberal → strategie_L4 → strategie_l3_deleguee →
  module_tns/salarie`.
- **Risque sémantique le plus élevé du chantier** : comparaison
  inter-régimes ⇒ tentation de prescription implicite maximale.
  Doctrine du module : interdiction stricte de « régime recommandé »
  automatique, indicateurs séparés T4 jamais agrégés.

Vérifie :
1. Rétrocompat parfaite (4 helpers + routeur)
2. Structure trace méta (5 codes COMP_REG_*, terminologie NET_LE_PLUS_ELEVE)
3. Structure des 4 sous-traces ligne_<regime>
4. Composition des 3 arbitrages + module Salarié (sous-traces niveau 2)
5. **Profondeur 6 niveaux atteinte** sur la branche Libéral L4
6. Garde-fou T4 explicite au niveau méta (non-agrégation)
7. Disclaimers en hypotheses (3 textes intégraux préservés)
8. Isolation espaces de codes `COMP_REG_*` ⊥ `COMP_*` ⊥ `STRAT_*`
9. **Test non-prescriptif** sur tout le graphe (>400 étapes)
10. Convention TNS_*/LIB_*/SAL_*/ASSIM_* préservée dans les sous-sous-traces
11. Résolution doctrinale sur tout le graphe
12. Cohérence valeurs trace vs ResultatComparateurRegimes
13. Rendu console (5 niveaux)
14. Spec version 1.1.0

Usage : python3 test_mode_audit_strategy_comparateur_regimes.py
Exit code 0 si tous les tests passent.
"""

import sys
import re

from core.profil import Profil
from core.audit import (
    TraceAudit, AUDIT_SPEC_VERSION, resoudre_doctrine_ref,
)
from strategy.comparateur_regimes import (
    _ligne_assimile, _ligne_tns, _ligne_liberal, _ligne_salarie,
    calcul_comparateur_regimes,
)
from ui.audit_render import rendre_trace_console


# ============================================================
# REGISTRES — Contrat G3d-bis
# ============================================================
CODES_META_ATTENDUS = {
    "COMP_REG_NB_LIGNES",
    "COMP_REG_DISCLAIMERS_NB",
    "COMP_REG_INDICATEURS_SEPARES_T4",
    "COMP_REG_CRITERE_NET",
    "COMP_REG_NET_LE_PLUS_ELEVE",
}

CODES_LIGNE_ASSIM = {
    f"COMP_REG_ASSIM_{s}" for s in (
        "REGIME", "CODE_STRATEGIE_TOP_NET", "NET_DIRIGEANT",
        "GRANDEUR_ENTREE", "MONTANT_ENTREE",
        "BENEFICE_RETENU_SOCIETE", "ALERTES_NB",
    )
}
CODES_LIGNE_TNS = {
    f"COMP_REG_TNS_{s}" for s in (
        "REGIME", "CODE_STRATEGIE_TOP_NET", "NET_DIRIGEANT",
        "GRANDEUR_ENTREE", "MONTANT_ENTREE",
        "BENEFICE_RETENU_SOCIETE", "ALERTES_NB",
    )
}
CODES_LIGNE_LIB = {
    f"COMP_REG_LIB_{s}" for s in (
        "REGIME", "CODE_STRATEGIE_PLUS_EFFICACE", "NET_DIRIGEANT",
        "GRANDEUR_ENTREE", "MONTANT_ENTREE",
        "BENEFICE_RETENU_SOCIETE", "ALERTES_NB",
    )
}
CODES_LIGNE_SAL = {
    f"COMP_REG_SAL_{s}" for s in (
        "REGIME", "CODE_STRATEGIE_TOP_NET", "NET_DIRIGEANT",
        "GRANDEUR_ENTREE", "MONTANT_ENTREE",
        "BENEFICE_RETENU_SOCIETE", "ALERTES_NB",
    )
}

NOMS_SOUS_TRACES_META = {"ligne_assimile", "ligne_tns",
                          "ligne_liberal", "ligne_salarie"}

NOMS_SOUS_TRACES_LIGNE = {
    "ligne_assimile": "arbitrage_assimile",
    "ligne_tns": "arbitrage_tns",
    "ligne_liberal": "arbitrage_liberal",
    "ligne_salarie": "module_salarie",
}


# ============================================================
# VOCABULAIRE PRESCRIPTIF INTERDIT (élargi G3b)
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
print("  TEST 1 — Rétrocompat parfaite (4 helpers + routeur)")
print("=" * 95)

profil = Profil()

for nom, fn in (("ligne_assimile", _ligne_assimile),
                ("ligne_tns", _ligne_tns),
                ("ligne_liberal", _ligne_liberal),
                ("ligne_salarie", _ligne_salarie)):
    r_sans = fn(profil)
    t = TraceAudit(regime=f"Test {nom}")
    r_avec = fn(profil, audit=t)
    check(f"{nom}: dataclass identique avec/sans audit",
          r_sans == r_avec)

r_sans_arb = calcul_comparateur_regimes(profil)
trace = TraceAudit(regime="Strategy/Comparateur_Regimes")
r_avec_arb = calcul_comparateur_regimes(profil, audit=trace)
check("Routeur: même net_le_plus_eleve",
      r_sans_arb.meilleur_net == r_avec_arb.meilleur_net)
check("Routeur: même nombre de lignes",
      len(r_sans_arb.lignes) == len(r_avec_arb.lignes) == 4)
check("Routeur: chaque ligne identique avec/sans audit",
      all(r_sans_arb.lignes[i] == r_avec_arb.lignes[i]
          for i in range(len(r_sans_arb.lignes))))


# ============================================================
# TEST 2 — STRUCTURE MÉTA
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure méta (5 codes, terminologie NET_LE_PLUS_ELEVE)")
print("=" * 95)

codes_meta = set(trace.codes())
check(f"Méta contient les {len(CODES_META_ATTENDUS)} codes attendus",
      codes_meta == CODES_META_ATTENDUS,
      f"manquants={CODES_META_ATTENDUS - codes_meta}, "
      f"extras={codes_meta - CODES_META_ATTENDUS}")

check("COMP_REG_NET_LE_PLUS_ELEVE présent (terminologie factuelle)",
      "COMP_REG_NET_LE_PLUS_ELEVE" in codes_meta)
check("COMP_REG_RETENU ABSENT (terminologie réservée TNS/Assimilé)",
      "COMP_REG_RETENU" not in codes_meta)
check("COMP_REG_MEILLEUR_* ABSENT (terminologie prescriptive)",
      not any("MEILLEUR" in c for c in codes_meta))


# ============================================================
# TEST 3 — STRUCTURE DES 4 SOUS-TRACES LIGNE
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Structure des 4 sous-traces ligne_<regime>")
print("=" * 95)

attendus_par_ligne = {
    "ligne_assimile": CODES_LIGNE_ASSIM,
    "ligne_tns": CODES_LIGNE_TNS,
    "ligne_liberal": CODES_LIGNE_LIB,
    "ligne_salarie": CODES_LIGNE_SAL,
}

for nom, attendus in attendus_par_ligne.items():
    sub = trace.get_sous_trace(nom)
    check(f"Sous-trace '{nom}' attachée", sub is not None)
    if sub is None:
        continue
    codes_obtenus = set(sub.codes())
    check(f"  → {nom} contient les {len(attendus)} codes attendus",
          codes_obtenus == attendus,
          f"manquants={attendus - codes_obtenus}, "
          f"extras={codes_obtenus - attendus}")


# ============================================================
# TEST 4 — COMPOSITION DES ARBITRAGES (sous-traces niveau 2)
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Composition des 3 arbitrages + module Salarié")
print("=" * 95)

for nom_ligne, nom_sous_sous in NOMS_SOUS_TRACES_LIGNE.items():
    sub_ligne = trace.get_sous_trace(nom_ligne)
    noms_lvl2 = set(sub_ligne.noms_sous_traces())
    check(f"{nom_ligne}: sous-trace '{nom_sous_sous}' attachée",
          nom_sous_sous in noms_lvl2,
          f"obtenu={noms_lvl2}")

# Préfixes des codes dans chaque sous-sous-trace
verifs_prefixes = {
    "ligne_assimile/arbitrage_assimile": "STRAT_ASSIM_",
    "ligne_tns/arbitrage_tns": "STRAT_TNS_",
    "ligne_liberal/arbitrage_liberal": "STRAT_LIB_",
    "ligne_salarie/module_salarie": "SAL_",
}
for chemin, prefixe in verifs_prefixes.items():
    nom_l1, nom_l2 = chemin.split("/")
    sub = trace.get_sous_trace(nom_l1).get_sous_trace(nom_l2)
    check(f"  {chemin}: tous codes préfixés {prefixe}",
          all(c.startswith(prefixe) for c in sub.codes()))


# ============================================================
# TEST 5 — PROFONDEUR 6 NIVEAUX SUR LA BRANCHE LIBÉRAL L4
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Profondeur 6 niveaux atteinte (branche L4)")
print("=" * 95)

# Profil SELARL par défaut → L4 contient module_tns en niveau 4
# Chemin complet :
#   trace (niveau 0)
#   → ligne_liberal (niveau 1)
#     → arbitrage_liberal (niveau 2)
#       → strategie_L4 (niveau 3)
#         → strategie_l3_deleguee (niveau 4)
#           → module_tns (niveau 5)

lvl1 = trace.get_sous_trace("ligne_liberal")
check("Niveau 1: ligne_liberal", lvl1 is not None)

lvl2 = lvl1.get_sous_trace("arbitrage_liberal")
check("Niveau 2: arbitrage_liberal", lvl2 is not None)

lvl3 = lvl2.get_sous_trace("strategie_L4")
check("Niveau 3: strategie_L4", lvl3 is not None)

lvl4 = lvl3.get_sous_trace("strategie_l3_deleguee")
check("Niveau 4: strategie_l3_deleguee", lvl4 is not None)

lvl5 = lvl4.get_sous_trace("module_tns")
check("Niveau 5: module_tns (SELARL par défaut)",
      lvl5 is not None and len(lvl5.etapes) == 24 and
      all(c.startswith("TNS_") for c in lvl5.codes()))


def profondeur(t):
    if not t.noms_sous_traces():
        return 1
    return 1 + max(profondeur(t.get_sous_trace(n)) for n in t.noms_sous_traces())

p_max = profondeur(trace)
check(f"Profondeur maximale du graphe = 6 (obtenu : {p_max})",
      p_max == 6)


# ============================================================
# TEST 6 — GARDE-FOU T4 EXPLICITE AU NIVEAU MÉTA
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Garde-fou T4 (non-agrégation explicite)")
print("=" * 95)

e_t4 = trace.get("COMP_REG_INDICATEURS_SEPARES_T4")
check("COMP_REG_INDICATEURS_SEPARES_T4 présent", e_t4 is not None)
check("  hypothèse 'convention' contient 'non-agrégation'",
      "non-agrégation" in e_t4.hypotheses.get("convention", ""))
check("  hypothèse 'regle' explicite l'interdiction de sommer",
      "Ne PAS sommer" in e_t4.hypotheses.get("regle", ""))

# Valeur = benefice_retenu de la ligne TNS
ligne_tns_obj = next(l for l in r_avec_arb.lignes if l.regime == "TNS")
check("  valeur = benefice_retenu_societe de la ligne TNS",
      abs(e_t4.valeur - ligne_tns_obj.benefice_retenu_societe) < TOL)


# ============================================================
# TEST 7 — DISCLAIMERS EN HYPOTHESES
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — Disclaimers permanents en hypotheses (3 textes intégraux)")
print("=" * 95)

e_disc = trace.get("COMP_REG_DISCLAIMERS_NB")
check("COMP_REG_DISCLAIMERS_NB présent", e_disc is not None)
check("  valeur = 3", abs(e_disc.valeur - 3.0) < TOL)
for cle_attendue in ("DISCLAIMER_CHANGEMENT_REGIME",
                      "DISCLAIMER_COMPARABILITE",
                      "NOTE_RADAR_INTRA_REGIME"):
    check(f"  {cle_attendue} dans hypotheses",
          cle_attendue in e_disc.hypotheses)

# Textes contiennent les mots-clés attendus (preuve de l'intégralité)
texte_changement = e_disc.hypotheses.get("DISCLAIMER_CHANGEMENT_REGIME", "")
check("  DISCLAIMER_CHANGEMENT_REGIME contient 'cadrage indicatif'",
      "cadrage indicatif" in texte_changement)
texte_comparabilite = e_disc.hypotheses.get("DISCLAIMER_COMPARABILITE", "")
check("  DISCLAIMER_COMPARABILITE contient 'ordres de grandeur'",
      "ordres de grandeur" in texte_comparabilite)


# ============================================================
# TEST 8 — ISOLATION ESPACES DE CODES
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Isolation COMP_REG_* ⊥ COMP_* ⊥ STRAT_* ⊥ régimes")
print("=" * 95)

# Méta : tous préfixés COMP_REG_
check("Méta : tous codes préfixés COMP_REG_",
      all(c.startswith("COMP_REG_") for c in codes_meta))
# Aucune intrusion COMP_* (sans REG)
check("Méta : aucune intrusion COMP_<autre>_ (sans REG)",
      not any(c.startswith("COMP_") and not c.startswith("COMP_REG_")
              for c in codes_meta))

# Chaque sous-trace ligne_* : tous préfixés COMP_REG_<X>_
for nom_l1, codes_l1 in (("ligne_assimile", "COMP_REG_ASSIM_"),
                          ("ligne_tns", "COMP_REG_TNS_"),
                          ("ligne_liberal", "COMP_REG_LIB_"),
                          ("ligne_salarie", "COMP_REG_SAL_")):
    sub = trace.get_sous_trace(nom_l1)
    check(f"{nom_l1}: tous préfixés {codes_l1}",
          all(c.startswith(codes_l1) for c in sub.codes()))


# ============================================================
# TEST 9 — NON-PRESCRIPTIF (scan complet sur >400 étapes)
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Aucun wording prescriptif (scan récursif tout le graphe)")
print("=" * 95)

def scanner_prescriptif(t, chemin=""):
    violations = []
    for e in t.etapes:
        for champ, texte in (("label", e.label), ("notes", e.notes)):
            for pattern in TERMES_INTERDITS:
                if re.search(pattern, texte, re.IGNORECASE):
                    violations.append((chemin or t.regime, e.code, pattern, champ, texte))
    for nom in t.noms_sous_traces():
        sub = t.get_sous_trace(nom)
        violations.extend(scanner_prescriptif(
            sub, chemin=f"{chemin}/{nom}" if chemin else nom))
    return violations

def compter_etapes(t):
    n = len(t.etapes)
    for nom in t.noms_sous_traces():
        n += compter_etapes(t.get_sous_trace(nom))
    return n

violations = scanner_prescriptif(trace)
n_total = compter_etapes(trace)

if violations:
    check(f"Aucun wording prescriptif détecté", False,
          f"{len(violations)} violation(s) sur {n_total} étapes scannées")
    for chemin, code, pattern, champ, texte in violations[:10]:
        print(f"       ⚠ {chemin} / {code} / {champ} : pattern={pattern} dans {texte!r}")
else:
    check(f"Aucun wording prescriptif dans tout le graphe", True,
          f"{n_total} étapes scannées sur 12 patterns")


# ============================================================
# TEST 10 — CONVENTION DES PRÉFIXES PRÉSERVÉE
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Conventions de préfixes préservées dans tout le graphe")
print("=" * 95)

# Pour chaque sous-trace, vérifier que le préfixe attendu est respecté
verifs = [
    ("ligne_assimile/arbitrage_assimile/tx_ir_moy", "ASSIM_TX_IR_MOY_"),
    ("ligne_tns/arbitrage_tns/strategie_T1/module_tns", "TNS_"),
    ("ligne_liberal/arbitrage_liberal/strategie_L1/module_bnc", "LIB_BNC_"),
    ("ligne_salarie/module_salarie", "SAL_"),
]
for chemin, prefixe in verifs:
    parts = chemin.split("/")
    t = trace
    for p in parts:
        t = t.get_sous_trace(p) if t else None
        if t is None:
            break
    if t is not None:
        check(f"{chemin}: tous codes préfixés {prefixe}",
              all(c.startswith(prefixe) for c in t.codes()))
    else:
        check(f"{chemin}: chemin résolu", False)


# ============================================================
# TEST 11 — RÉSOLUTION DOCTRINALE
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Doctrine_refs se résolvent sur tout le graphe")
print("=" * 95)

refs_uniques = set()
def collecter_refs(t):
    for e in t.etapes:
        refs_uniques.update(e.doctrine_refs)
    for n in t.noms_sous_traces():
        collecter_refs(t.get_sous_trace(n))
collecter_refs(trace)

check(f"{len(refs_uniques)} doctrine_refs uniques dans le graphe complet",
      len(refs_uniques) >= 15)

for ref in sorted(refs_uniques):
    try:
        resoudre_doctrine_ref(ref)
        check(f"  Résolution {ref} OK", True)
    except AttributeError as e:
        check(f"  Résolution {ref}", False, str(e))


# ============================================================
# TEST 12 — COHÉRENCE VALEURS
# ============================================================
print()
print("=" * 95)
print("  TEST 12 — Cohérence valeurs tracées vs ResultatComparateurRegimes")
print("=" * 95)

# Méta : NET_LE_PLUS_ELEVE = meilleur_net
e_net = trace.get("COMP_REG_NET_LE_PLUS_ELEVE")
check("COMP_REG_NET_LE_PLUS_ELEVE.valeur == résultat.meilleur_net",
      e_net.valeur == r_avec_arb.meilleur_net)

# Méta : NB_LIGNES = len(lignes)
e_nb = trace.get("COMP_REG_NB_LIGNES")
check("COMP_REG_NB_LIGNES.valeur == 4",
      abs(e_nb.valeur - 4.0) < TOL)

# Pour chaque ligne, NET_DIRIGEANT de la sous-trace == net_dirigeant de la dataclass
for nom_l1, suffixe_code, regime_attendu in (
    ("ligne_assimile", "COMP_REG_ASSIM_NET_DIRIGEANT", "Assimilé salarié"),
    ("ligne_tns", "COMP_REG_TNS_NET_DIRIGEANT", "TNS"),
    ("ligne_salarie", "COMP_REG_SAL_NET_DIRIGEANT", "Salarié (référence)"),
):
    ligne = next(l for l in r_avec_arb.lignes if l.regime == regime_attendu)
    sub = trace.get_sous_trace(nom_l1)
    e = sub.get(suffixe_code)
    check(f"{suffixe_code} = ligne.net_dirigeant",
          abs(e.valeur - ligne.net_dirigeant) < TOL)


# ============================================================
# TEST 13 — RENDU CONSOLE
# ============================================================
print()
print("=" * 95)
print("  TEST 13 — Rendu console (6 niveaux d'imbrication)")
print("=" * 95)

rendu = rendre_trace_console(trace)
check("Rendu non-vide", len(rendu) > 10000)
check("En-tête Comparateur Régimes", "Strategy/Comparateur_Regimes" in rendu)
check("Contient COMP_REG_NET_LE_PLUS_ELEVE",
      "COMP_REG_NET_LE_PLUS_ELEVE" in rendu)
check("Sous-traces niveau 1 (4 lignes)",
      "Sous-traces attachées (4)" in rendu)
for nom in ("ligne_assimile", "ligne_tns", "ligne_liberal", "ligne_salarie"):
    check(f"  rendu sous-trace {nom!r}",
          f"nom d'attachement : {nom!r}" in rendu)

# Présence de codes des niveaux profonds
check("Codes ASSIM_TX_IR_MOY_* présents (niveau 3)",
      "ASSIM_TX_IR_MOY_" in rendu)
check("Codes TNS_* présents (niveau 5 via L4 délégué)",
      "TNS_" in rendu)
check("Pas de référence introuvable", "référence introuvable" not in rendu)


# ============================================================
# TEST 14 — SPEC VERSION
# ============================================================
print()
print("=" * 95)
print("  TEST 14 — Spec version 1.1.0")
print("=" * 95)

check(f"Spec version {AUDIT_SPEC_VERSION}",
      trace.spec_version == AUDIT_SPEC_VERSION == "1.1.0")
for nom in trace.noms_sous_traces():
    sub = trace.get_sous_trace(nom)
    check(f"  sous-trace {nom!r} porte la spec 1.1.0",
          sub.spec_version == "1.1.0")


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Strategy/Comparateur_Regimes passent (G3d-bis)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
