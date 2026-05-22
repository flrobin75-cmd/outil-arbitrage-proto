"""
Test de parité complet TNS — 6 cas comparés Python vs Excel v19.
"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from core.profil import Profil
from regime.tns import calcul_module_tns
from generer_cibles import CAS


def fmt(val):
    if val is None:
        return "       None"
    if isinstance(val, (int, float)):
        return f"{val:>15,.4f}"
    return f"{str(val):>15s}"


def comparer(label, python_val, excel_val, tolerance=0.01):
    if excel_val is None:
        return None, f"  ⚠ {label:55s} Excel=None - ignoré"
    if python_val is None:
        return False, f"  ✗ {label:55s} Python=None  Excel={fmt(excel_val)}"
    ecart = python_val - excel_val
    ok = abs(ecart) <= tolerance
    marker = "✓" if ok else "✗"
    return ok, f"  {marker} {label:55s} Python={fmt(python_val)}  Excel={fmt(excel_val)}  écart={ecart:+10,.4f}"


# Charger les cibles générées
with open('/home/claude/tns_dev/cibles_excel.json') as f:
    cibles_tous = json.load(f)

# Cas 1 - valeurs manuelles (déjà connues du cas par défaut)
cibles_tous["Cas 1 - Cas par défaut v19"] = {
    "Cotisations TNS totales (C10)": 31_500.00,
    "CSG déductible (C11)": 6_902.00,
    "CSG/CRDS non déd. (C12)": 2_943.50,
    "Revenu net pro (C15)": 70_000.00,
    "Revenu imposable (C16)": 72_943.50,
    "Revenu imposable foyer (C17)": 72_943.50,
    "IR foyer après plafond QF (C23)": 8_091.03,
    "CEHR (C25)": 0.00,
    "CDHR (C27)": 0.00,
    "Total impôts foyer (C28)": 8_091.03,
    "Taux moyen IR (C29)": 0.110923,
    "Coût total société (C38)": 101_500.00,
    "Seuil 10 % div (C43)": 10_000.00,
    "Fraction cotis TNS (C45)": 40_000.00,
    "Cotis TNS sur div (C46)": 18_000.00,
    "Fraction PFU (C47)": 10_000.00,
    "PFU sur fraction (C48)": 3_140.00,
    "IR sur fraction TNS (C49)": 12_000.00,
    "Net dividendes (C50)": 16_860.00,
}

# Inputs cas 1
CAS["Cas 1 - Cas par défaut v19"] = dict(
    forme_juridique="SARL (gérance majoritaire) / EURL",
    situation="Marié / pacsé",
    parts=2.0,
    autres_rev=0,
    div_foyer=0,
    capital_cca=100_000,
    rem_nette=70_000,
    frais_reels=0,
    div_bruts=50_000,
)

resume = []
total_ok = 0
total_compar = 0

ordre_cas = ["Cas 1 - Cas par défaut v19",
             "Cas 2 - Célibataire 1 part TMI 30%",
             "Cas 3 - Marié 4 parts (2 enfants) revenu élevé",
             "Cas 4 - Foyer riche déclenchant CEHR",
             "Cas 5 - CDHR plancher 20%",
             "Cas 6 - Dividendes sous le seuil 10%"]

for nom_cas in ordre_cas:
    print("=" * 110)
    print(f"  {nom_cas}")
    print("=" * 110)

    inputs = CAS[nom_cas]
    profil = Profil(
        forme_juridique=inputs["forme_juridique"],
        situation=inputs["situation"],
        parts=inputs["parts"],
        autres_revenus=inputs["autres_rev"],
        dividendes_foyer_hors_enveloppe=inputs["div_foyer"],
        capital_cca=inputs["capital_cca"],
    )
    res = calcul_module_tns(profil,
                            rem_nette_souhaitee=inputs["rem_nette"],
                            frais_reels=inputs["frais_reels"],
                            div_bruts=inputs["div_bruts"])

    correspondances = {
        "Cotisations TNS totales (C10)": res.cotisations_tns,
        "CSG déductible (C11)": res.csg_deductible,
        "CSG/CRDS non déd. (C12)": res.csg_non_deductible,
        "Revenu net pro (C15)": res.revenu_net_pro,
        "Revenu imposable (C16)": res.revenu_imposable,
        "Revenu imposable foyer (C17)": res.revenu_imposable_foyer,
        "IR foyer après plafond QF (C23)": res.ir_foyer,
        "CEHR (C25)": res.cehr,
        "CDHR (C27)": res.cdhr,
        "Total impôts foyer (C28)": res.total_impots_foyer,
        "Taux moyen IR (C29)": res.taux_moyen_ir,
        "Coût total société (C38)": res.cout_total_societe,
        "Seuil 10 % div (C43)": res.seuil_10pct,
        "Fraction cotis TNS (C45)": res.fraction_cotis_tns,
        "Cotis TNS sur div (C46)": res.cotis_tns_sur_div,
        "Fraction PFU (C47)": res.fraction_pfu,
        "PFU sur fraction (C48)": res.pfu_sur_fraction,
        "IR sur fraction TNS (C49)": res.ir_sur_fraction_tns,
        "Net dividendes (C50)": res.net_dividendes,
    }

    cibles_cas = cibles_tous[nom_cas]
    ok_cas = 0
    total_cas = 0
    for label, val_py in correspondances.items():
        # Convertir les valeurs cibles JSON en float si stockées en str
        val_xl = cibles_cas.get(label)
        if isinstance(val_xl, str):
            try:
                val_xl = float(val_xl)
            except (ValueError, TypeError):
                pass
        ok, ligne = comparer(label, val_py, val_xl)
        print(ligne)
        if ok is not None:
            total_cas += 1
            if ok:
                ok_cas += 1
    print(f"\n  Résultat : {ok_cas}/{total_cas} OK\n")
    resume.append((nom_cas, ok_cas, total_cas))
    total_ok += ok_cas
    total_compar += total_cas

print("=" * 110)
print("  SYNTHÈSE")
print("=" * 110)
for nom, ok, total in resume:
    status = "✓" if ok == total else "✗"
    print(f"  {status} {nom:55s} : {ok}/{total}")
print(f"\n  TOTAL : {total_ok}/{total_compar} cellules en parité exacte")
