"""
Test de parité complet Libéral - 6 cas Python vs Excel v19.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from core.profil import Profil
from regime.liberal import calcul_module_bnc, calcul_module_sel
from generer_cibles_liberal import CAS_LIBERAL


def fmt(val):
    if val is None: return "       None"
    if isinstance(val, (int, float)): return f"{val:>15,.4f}"
    return f"{str(val):>15s}"


def comparer(label, py, xl, tol=0.01):
    if xl is None: return None, f"  ⚠ {label:55s} Excel=None"
    if py is None: return False, f"  ✗ {label:55s} Python=None  Excel={fmt(xl)}"
    ecart = py - xl
    ok = abs(ecart) <= tol
    marker = "✓" if ok else "✗"
    return ok, f"  {marker} {label:55s} Python={fmt(py)}  Excel={fmt(xl)}  écart={ecart:+10,.4f}"


# Cas 1 - défaut v19 (valeurs déjà connues de l'audit)
CIBLES_CAS_1 = {
    "Bénéfice BNC (C7)": 120_000.00,
    "Cotisations URSSAF (C8)": 54_000.00,
    "CSG/CRDS non déd. (C9)": 3_480.00,
    "Bénéfice net après cotis. (C10)": 66_000.00,
    "Revenu imposable libéral (C11)": 69_480.00,
    "Revenu imposable foyer (C12)": 69_480.00,
    "IR foyer après plafond QF (C18)": 7_051.98,
    "CEHR (C20)": 0.00,
    "CDHR (C22)": 0.00,
    "Total impôts foyer (C23)": 7_051.98,
    "Impôts imputables libéral (C24)": 7_051.98,
    "Net libéral après impôts (C25)": 58_948.02,
    "Bénéfice imposable IS (C30)": 120_000.00,
    "IS dû (C31)": 25_750.00,
    "Résultat net distribuable (C32)": 94_250.00,
    "Dividendes envisagés (C33)": 94_250.00,
}
INPUTS_CAS_1 = dict(
    situation="Marié / pacsé", parts=2.0,
    autres_rev=0, div_foyer=0,
    recettes=150_000, frais_pro=30_000,
    benefice_sel=200_000, rem_sel=80_000,
)

# Charger cibles cas 2-6
with open('/home/claude/tns_dev/cibles_liberal.json') as f:
    cibles_tous = json.load(f)
cibles_tous["Cas 1 - défaut v19"] = CIBLES_CAS_1
CAS_LIBERAL["Cas 1 - défaut v19"] = INPUTS_CAS_1

ordre = ["Cas 1 - défaut v19",
         "Cas 2 - BNC faible revenu célibataire 1 part",
         "Cas 3 - BNC marié 3 parts avec autres revenus",
         "Cas 4 - BNC haut revenu marié déclenchant CEHR",
         "Cas 5 - BNC célibataire CDHR potentielle",
         "Cas 6 - SEL double couche bénéfice élevé"]

total_ok = 0
total = 0
resume = []

for nom in ordre:
    print("=" * 110)
    print(f"  {nom}")
    print("=" * 110)
    inputs = CAS_LIBERAL[nom]
    profil = Profil(
        forme_juridique="Profession libérale (BNC)",
        effectif="Sans salarié",
        situation=inputs["situation"],
        parts=inputs["parts"],
        autres_revenus=inputs["autres_rev"],
        dividendes_foyer_hors_enveloppe=inputs["div_foyer"],
    )
    bnc = calcul_module_bnc(profil, recettes=inputs["recettes"], frais_pro=inputs["frais_pro"])
    sel = calcul_module_sel(benefice_avant_rem=inputs["benefice_sel"],
                            remuneration_dirigeant=inputs["rem_sel"])

    correspondances = {
        "Bénéfice BNC (C7)": bnc.benefice_bnc,
        "Cotisations URSSAF (C8)": bnc.cotisations,
        "CSG/CRDS non déd. (C9)": bnc.csg_non_deductible,
        "Bénéfice net après cotis. (C10)": bnc.benefice_net_apres_cotis,
        "Revenu imposable libéral (C11)": bnc.revenu_imposable_lib,
        "Revenu imposable foyer (C12)": bnc.revenu_imposable_foyer,
        "IR foyer après plafond QF (C18)": bnc.ir_foyer,
        "CEHR (C20)": bnc.cehr,
        "CDHR (C22)": bnc.cdhr,
        "Total impôts foyer (C23)": bnc.total_impots_foyer,
        "Impôts imputables libéral (C24)": bnc.impots_imputables_libéral,
        "Net libéral après impôts (C25)": bnc.net_apres_impots,
        "Bénéfice imposable IS (C30)": sel.benefice_imposable_is,
        "IS dû (C31)": sel.is_du,
        "Résultat net distribuable (C32)": sel.resultat_net_distribuable,
        "Dividendes envisagés (C33)": sel.dividendes_envisages,
    }

    cibles = cibles_tous[nom]
    ok_cas, total_cas = 0, 0
    for label, py in correspondances.items():
        xl = cibles.get(label)
        if isinstance(xl, str):
            try: xl = float(xl)
            except: pass
        ok, ligne = comparer(label, py, xl)
        print(ligne)
        if ok is not None:
            total_cas += 1
            if ok: ok_cas += 1
    print(f"\n  Résultat : {ok_cas}/{total_cas} OK\n")
    resume.append((nom, ok_cas, total_cas))
    total_ok += ok_cas
    total += total_cas

print("=" * 110)
print("  SYNTHÈSE LIBÉRAL")
print("=" * 110)
for nom, ok, t in resume:
    status = "✓" if ok == t else "✗"
    print(f"  {status} {nom:55s} : {ok}/{t}")
print(f"\n  TOTAL : {total_ok}/{total} cellules en parité")
