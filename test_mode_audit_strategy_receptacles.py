"""
test_mode_audit_strategy_receptacles.py — Tests dédiés à l'instrumentation
MODE_AUDIT du strategy/receptacles (G3f-receptacles, spec 1.1.0).

Spécificités G3f-receptacles :
- **Namespace dédié `RECEPT_*`** distinct de tous les autres namespaces.
- **Composition interne 3 niveaux** : `motif_inaccessibilite` attache
  `accessibilite` qui attache lui-même `regime_effectif`.
- **Trace plate volontaire** pour `liste_receptacles_par_regime` :
  6 réceptacles itérés en codes plats (`RECEPT_RECEPTACLE_<NOM>`), pas
  12 sous-traces (`est_accessible` + `motif_inaccessibilite` × 6).
- **Branche short-circuit** : `est_accessible` retourne True sans
  composer `regime_effectif` si le réceptacle est inconnu (sécurité —
  ne pas bloquer un futur réceptacle non documenté).
- **Règle d'or SELARL/SELAS** : `regime_effectif_receptacles` est la
  SEULE source de vérité. Branches tracées en hypotheses.

Vérifie :
1. Rétrocompat parfaite — 5 fonctions × scénarios variés
2. Structure `regime_effectif_receptacles` (4 étapes plates)
3. Structure `est_accessible` (3-4 étapes + sous-trace conditionnelle)
4. Structure `motif_inaccessibilite` (1 étape + sous-trace)
5. Profondeur 3 niveaux pour `motif_inaccessibilite`
6. Structure `liste_receptacles_par_regime` (NB + 6 réceptacles, trace plate)
7. Structure `mention_madelin` (1 étape, texte intégral en hypotheses)
8. Règle SELARL → TNS / SELAS → Assimilé tracée
9. Branche short-circuit (réceptacle inconnu) sans sous-trace
10. Cohérence valeurs trace vs valeurs retournées
11. **Test non-prescriptif renforcé** (14 patterns × tout le graphe)
12. Isolation `RECEPT_*` ⊥ tous les autres namespaces

Usage : python3 test_mode_audit_strategy_receptacles.py
Exit code 0 si tous les tests passent.
"""

import sys
import re

from core.profil import Profil
from core.audit import TraceAudit, AUDIT_SPEC_VERSION
from strategy.receptacles import (
    regime_effectif_receptacles, est_accessible, motif_inaccessibilite,
    liste_receptacles_par_regime, mention_madelin,
    REGIME_EFF_ASSIMILE, REGIME_EFF_TNS,
    REGIME_EFF_LIBERAL_BNC, REGIME_EFF_SALARIE,
    REGIMES_EFFECTIFS, MATRICE_RECEPTACLES, MADELIN_PER_TNS_MENTION,
)


# ============================================================
# PATTERNS NON-PRESCRIPTIFS RENFORCÉS G3e (14 patterns)
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
    r"\bprioritaire(?:s)?\b",
    r"\bprivilégi\w*\b",
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


def compter_etapes(t):
    n = len(t.etapes)
    for nom in t.noms_sous_traces():
        n += compter_etapes(t.get_sous_trace(nom))
    return n


def scanner_prescriptif(t, chemin=""):
    violations = []
    for e in t.etapes:
        for champ, texte in [("label", e.label), ("notes", e.notes)]:
            for pattern in TERMES_INTERDITS:
                if re.search(pattern, texte, re.IGNORECASE):
                    violations.append((chemin or t.regime, e.code,
                                       pattern, champ, texte))
    for nom in t.noms_sous_traces():
        sub = t.get_sous_trace(nom)
        violations.extend(scanner_prescriptif(
            sub, chemin=f"{chemin}/{nom}" if chemin else nom))
    return violations


def collecter_codes(t):
    codes = set(t.codes())
    for nom in t.noms_sous_traces():
        codes |= collecter_codes(t.get_sous_trace(nom))
    return codes


def profondeur(t):
    if not t.noms_sous_traces():
        return 1
    return 1 + max(profondeur(t.get_sous_trace(n))
                   for n in t.noms_sous_traces())


# ============================================================
# PROFILS DE TEST
# ============================================================
profil_assim = Profil(forme_juridique="SAS / SASU")
profil_tns = Profil(forme_juridique="SARL (gérance majoritaire) / EURL")
profil_selarl = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELARL")
profil_selas = Profil(forme_juridique="SELARL / SELAS", forme_sel="SELAS")
profil_lib = Profil(forme_juridique="Profession libérale (BNC)")


# ============================================================
# TEST 1 — RÉTROCOMPAT 5 FONCTIONS
# ============================================================
print("=" * 95)
print("  TEST 1 — Rétrocompat parfaite (5 fonctions × scénarios variés)")
print("=" * 95)

# 1.a regime_effectif_receptacles
for label, profil in [("Assimilé", profil_assim), ("TNS", profil_tns),
                       ("SELARL", profil_selarl), ("SELAS", profil_selas),
                       ("Libéral BNC", profil_lib)]:
    r_sans = regime_effectif_receptacles(profil)
    t = TraceAudit(regime=f"RE {label}")
    r_avec = regime_effectif_receptacles(profil, audit=t)
    check(f"regime_effectif_receptacles {label}", r_sans == r_avec)

# 1.b est_accessible (matrice × 4 régimes)
for receptacle in ["PEE", "PERECO", "PERO", "PERIN", "Intéressement", "Participation"]:
    for label, profil in [("Assimilé", profil_assim), ("TNS", profil_tns),
                           ("SELAS", profil_selas)]:
        r_sans = est_accessible(receptacle, profil)
        t = TraceAudit(regime=f"acc {receptacle} {label}")
        r_avec = est_accessible(receptacle, profil, audit=t)
        check(f"est_accessible {receptacle} {label}", r_sans == r_avec)

# 1.c motif_inaccessibilite
for receptacle in ["PEE", "PERIN"]:
    for label, profil in [("TNS", profil_tns), ("SELARL", profil_selarl)]:
        r_sans = motif_inaccessibilite(receptacle, profil)
        t = TraceAudit(regime=f"motif {receptacle} {label}")
        r_avec = motif_inaccessibilite(receptacle, profil, audit=t)
        check(f"motif_inaccessibilite {receptacle} {label}", r_sans == r_avec)

# 1.d liste_receptacles_par_regime
r_sans = liste_receptacles_par_regime(profil_tns)
t = TraceAudit(regime="liste TNS")
r_avec = liste_receptacles_par_regime(profil_tns, audit=t)
check("liste_receptacles_par_regime", r_sans == r_avec)

# 1.e mention_madelin
t = TraceAudit(regime="Mention")
check("mention_madelin", mention_madelin() == mention_madelin(audit=t))


# ============================================================
# TEST 2 — Structure regime_effectif_receptacles (4 étapes plates)
# ============================================================
print()
print("=" * 95)
print("  TEST 2 — Structure regime_effectif_receptacles (4 étapes plates)")
print("=" * 95)

t_re = TraceAudit(regime="RE Assimilé")
regime_effectif_receptacles(profil_assim, audit=t_re)
codes_re = set(t_re.codes())

attendus_re = {
    "RECEPT_REGIME_SOCIAL_PROFIL",
    "RECEPT_FORME_JURIDIQUE_PROFIL",
    "RECEPT_FORME_SEL_PROFIL",
    "RECEPT_REGIME_EFFECTIF",
}
check(f"4 codes attendus", attendus_re.issubset(codes_re),
      f"manquants={attendus_re - codes_re}")
check("Trace plate (aucune sous-trace)",
      len(t_re.noms_sous_traces()) == 0)

# Branche tracée
e_re = t_re.get("RECEPT_REGIME_EFFECTIF")
check("RECEPT_REGIME_EFFECTIF.hypotheses['branche_appliquee'] présent",
      "branche_appliquee" in e_re.hypotheses)


# ============================================================
# TEST 3 — Structure est_accessible (3-4 étapes + sous-trace conditionnelle)
# ============================================================
print()
print("=" * 95)
print("  TEST 3 — Structure est_accessible (avec composition regime_effectif)")
print("=" * 95)

t_acc = TraceAudit(regime="PEE Assimilé acc")
est_accessible("PEE", profil_assim, audit=t_acc)
codes_acc = set(t_acc.codes())

attendus_acc = {
    "RECEPT_RECEPTACLE_INPUT",
    "RECEPT_RECEPTACLE_CONNU",
    "RECEPT_ACCESSIBLE",
}
check("Codes méta attendus", attendus_acc.issubset(codes_acc))
check("Sous-trace 'regime_effectif' attachée (réceptacle connu)",
      "regime_effectif" in t_acc.noms_sous_traces())
check("Sous-trace regime_effectif : codes préfixés RECEPT_",
      all(c.startswith("RECEPT_")
          for c in t_acc.get_sous_trace("regime_effectif").codes()))


# ============================================================
# TEST 4 — Structure motif_inaccessibilite (1 étape + sous-trace)
# ============================================================
print()
print("=" * 95)
print("  TEST 4 — Structure motif_inaccessibilite (avec composition accessibilite)")
print("=" * 95)

t_motif = TraceAudit(regime="Motif PEE TNS")
r_motif = motif_inaccessibilite("PEE", profil_tns, audit=t_motif)
codes_motif = set(t_motif.codes())

check("RECEPT_MOTIF_RETOURNE présent",
      "RECEPT_MOTIF_RETOURNE" in codes_motif)
check("Sous-trace 'accessibilite' attachée",
      "accessibilite" in t_motif.noms_sous_traces())

# motif retourné = string formaté
check(f"motif retourné = 'Non accessible en régime TNS.'",
      r_motif == "Non accessible en régime TNS.")

# Cas accessible : motif None
t_motif_ok = TraceAudit(regime="Motif PEE Assimilé")
r = motif_inaccessibilite("PEE", profil_assim, audit=t_motif_ok)
check("Cas accessible : motif=None retourné",
      r is None)
e_m = t_motif_ok.get("RECEPT_MOTIF_RETOURNE")
check("  hypotheses['valeur_python_retournee'] is None",
      e_m.hypotheses.get("valeur_python_retournee") is None)


# ============================================================
# TEST 5 — Profondeur 3 niveaux pour motif_inaccessibilite
# ============================================================
print()
print("=" * 95)
print("  TEST 5 — Profondeur 3 niveaux : motif → accessibilite → regime_effectif")
print("=" * 95)

prof = profondeur(t_motif)
check(f"profondeur(motif_inaccessibilite) == 3", prof == 3,
      f"obtenu {prof}")

sub_acc = t_motif.get_sous_trace("accessibilite")
check("Niveau 2 : sous-trace 'accessibilite' existe",
      sub_acc is not None)
sub_re = sub_acc.get_sous_trace("regime_effectif")
check("Niveau 3 : sous-trace 'regime_effectif' existe",
      sub_re is not None)
check("Niveau 3 : codes préfixés RECEPT_",
      all(c.startswith("RECEPT_") for c in sub_re.codes()))


# ============================================================
# TEST 6 — Structure liste_receptacles_par_regime (trace plate)
# ============================================================
print()
print("=" * 95)
print("  TEST 6 — Structure liste_receptacles_par_regime (NB + 6 réceptacles, plate)")
print("=" * 95)

t_liste = TraceAudit(regime="Liste TNS")
liste_receptacles_par_regime(profil_tns, audit=t_liste)
codes_liste = set(t_liste.codes())

check("RECEPT_NB_RECEPTACLES_MODELISES présent",
      "RECEPT_NB_RECEPTACLES_MODELISES" in codes_liste)
check(f"Nombre total étapes = 1 + {len(MATRICE_RECEPTACLES)} = "
      f"{1 + len(MATRICE_RECEPTACLES)}",
      len(t_liste.etapes) == 1 + len(MATRICE_RECEPTACLES))
check("Aucune sous-trace (trace plate volontaire)",
      len(t_liste.noms_sous_traces()) == 0)

# Vérif chaque réceptacle a son code
for rec in MATRICE_RECEPTACLES:
    nom_court = (rec.upper().replace("É", "E").replace("È", "E")
                 .replace("Ê", "E").replace("À", "A"))
    code = f"RECEPT_RECEPTACLE_{nom_court}"
    check(f"  {code} présent", code in codes_liste)


# ============================================================
# TEST 7 — Structure mention_madelin (1 étape, texte intégral en hypotheses)
# ============================================================
print()
print("=" * 95)
print("  TEST 7 — mention_madelin (texte intégral en hypotheses, pas en label)")
print("=" * 95)

t_mention = TraceAudit(regime="Mention Madelin")
mention_madelin(audit=t_mention)
check("1 étape", len(t_mention.etapes) == 1)
e_m = t_mention.get("RECEPT_MENTION_LONGUEUR")
check("Texte intégral en hypotheses",
      e_m.hypotheses.get("MADELIN_PER_TNS_MENTION") == MADELIN_PER_TNS_MENTION)
# Fragments-clés absents du label/notes
for fragment in ("Madelin / PER TNS", "comparateur v1", "à traiter"):
    check(f"  Fragment {fragment!r} absent du label",
          fragment not in e_m.label)
    check(f"  Fragment {fragment!r} absent des notes",
          fragment not in e_m.notes)


# ============================================================
# TEST 8 — Règle SELARL → TNS / SELAS → Assimilé
# ============================================================
print()
print("=" * 95)
print("  TEST 8 — Règle d'or SELARL → TNS / SELAS → Assimilé tracée")
print("=" * 95)

# SELARL → TNS
t_selarl = TraceAudit(regime="RE SELARL")
r = regime_effectif_receptacles(profil_selarl, audit=t_selarl)
check("SELARL → TNS (valeur retournée)", r == REGIME_EFF_TNS)
e_selarl = t_selarl.get("RECEPT_REGIME_EFFECTIF")
check("  branche tracée 'selarl_vers_tns'",
      e_selarl.hypotheses.get("branche_appliquee") == "selarl_vers_tns")

# SELAS → Assimilé
t_selas = TraceAudit(regime="RE SELAS")
r = regime_effectif_receptacles(profil_selas, audit=t_selas)
check("SELAS → Assimilé (valeur retournée)", r == REGIME_EFF_ASSIMILE)
e_selas = t_selas.get("RECEPT_REGIME_EFFECTIF")
check("  branche tracée 'selas_vers_assimile'",
      e_selas.hypotheses.get("branche_appliquee") == "selas_vers_assimile")


# ============================================================
# TEST 9 — Branche short-circuit (réceptacle inconnu)
# ============================================================
print()
print("=" * 95)
print("  TEST 9 — Réceptacle inconnu : True par défaut + pas de sous-trace")
print("=" * 95)

t_unk = TraceAudit(regime="Inconnu")
r = est_accessible("UNKNOWN_NEW_PRODUCT", profil_tns, audit=t_unk)
check("Réceptacle inconnu retourne True", r is True)
check("Aucune sous-trace 'regime_effectif' (short-circuit)",
      "regime_effectif" not in t_unk.noms_sous_traces())
e_acc = t_unk.get("RECEPT_ACCESSIBLE")
check("  hypotheses['branche'] == 'receptacle_inconnu_fallback'",
      e_acc.hypotheses.get("branche") == "receptacle_inconnu_fallback")


# ============================================================
# TEST 10 — Cohérence valeurs trace vs valeurs retournées
# ============================================================
print()
print("=" * 95)
print("  TEST 10 — Cohérence valeurs trace vs valeurs retournées")
print("=" * 95)

# regime_effectif_receptacles : valeur dans trace == valeur retournée
for label, profil in [("SELARL", profil_selarl), ("SELAS", profil_selas)]:
    t = TraceAudit(regime=f"coh {label}")
    r = regime_effectif_receptacles(profil, audit=t)
    e = t.get("RECEPT_REGIME_EFFECTIF")
    check(f"{label}: trace.valeur == retour", e.valeur == r)

# est_accessible : valeur dans trace == valeur retournée
for label, receptacle, profil in [
    ("PEE Assimilé", "PEE", profil_assim),
    ("PEE TNS", "PEE", profil_tns),
    ("PERIN TNS", "PERIN", profil_tns),
]:
    t = TraceAudit(regime=f"coh {label}")
    r = est_accessible(receptacle, profil, audit=t)
    e = t.get("RECEPT_ACCESSIBLE")
    val_attendue = 1.0 if r else 0.0
    check(f"{label}: trace.valeur ({e.valeur}) == retour ({r})",
          e.valeur == val_attendue)


# ============================================================
# TEST 11 — Non-prescriptif RENFORCÉ
# ============================================================
print()
print("=" * 95)
print("  TEST 11 — Non-prescriptif RENFORCÉ G3e (14 patterns × tout le graphe)")
print("=" * 95)

traces = [t_re, t_acc, t_motif, t_motif_ok, t_liste, t_mention,
          t_selarl, t_selas, t_unk]
total_etapes = sum(compter_etapes(t) for t in traces)
total_violations = 0
for trace_obj in traces:
    violations = scanner_prescriptif(trace_obj)
    total_violations += len(violations)
    if violations:
        for v in violations[:3]:
            print(f"     ⚠ {v[0]} / {v[1]} / {v[3]}: pattern={v[2]} dans {v[4]!r}")
check(f"0 violation sur {total_etapes} étapes × 14 patterns",
      total_violations == 0,
      f"obtenu {total_violations}")


# ============================================================
# TEST 12 — Isolation RECEPT_* ⊥ {tous les autres namespaces}
# ============================================================
print()
print("=" * 95)
print("  TEST 12 — Isolation RECEPT_* ⊥ {tous autres namespaces}")
print("=" * 95)

tous_codes = set()
for t in traces:
    tous_codes |= collecter_codes(t)
check(f"Tous codes préfixés RECEPT_ ({len(tous_codes)} codes scannés)",
      all(c.startswith("RECEPT_") for c in tous_codes))

prefixes_etrangers = ("STRAT_", "COMP_", "SYNTH_", "SCEN_", "PERIN_",
                       "TNS_", "LIB_BNC_", "LIB_SEL_", "SAL_", "ASSIM_")
intrus = [c for c in tous_codes
          if any(c.startswith(p) for p in prefixes_etrangers)]
check("Aucune intrusion de préfixe étranger",
      not intrus, f"intrus={intrus}")


# ============================================================
# SYNTHÈSE
# ============================================================
print()
print("=" * 95)
if not echecs:
    print(f"  ✓ Tous les tests MODE_AUDIT Strategy/Receptacles passent (G3f-receptacles)")
    sys.exit(0)
else:
    print(f"  ✗ {len(echecs)} test(s) en échec :")
    for label in echecs:
        print(f"     - {label}")
    sys.exit(1)
