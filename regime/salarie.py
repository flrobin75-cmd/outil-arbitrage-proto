"""
Regime Engine — Module Salarié (cadre/non-cadre).

Transposition fidèle de l'onglet "10. Salarié" du classeur v19.

Décision validée : périmètre v19 strict (brut sec, sans accessoires modélisés).
Les dispositifs d'épargne salariale (PEE, PER, etc.) sont modélisés dans le
Strategy Engine Assimilé (stratégies C/D), pas dans ce module de référence.

Structure :
    1. Imports et constantes
    2. Dataclass ResultatSalarie
    3. calcul_module_salarie()    — instrumenté MODE_AUDIT (G2a)

MODE_AUDIT (G2a) : `calcul_module_salarie()` accepte un paramètre opt-in
`audit: TraceAudit | None`. Codes émis : `SAL_*`. Rétrocompat parfaite
quand `audit=None`.

Note G2a : `PLAFOND_ABAT_10PCT_SAL` (14 426 €), `TX_CSG_DEDUCTIBLE` (6,8 %)
et `TX_ABAT_10PCT_SAL` (10 %) ont été promus de constantes locales à constantes
doctrinales centralisées dans `core/profil.py` au moment de l'instrumentation,
afin de pouvoir être citées comme `doctrine_ref` résolvables dans la trace.
"""

# ============================================================
# 1. IMPORTS ET CONSTANTES
# ============================================================
from dataclasses import dataclass

from core.profil import (
    Profil,
    TX_SALARIAL, ASSIETTE_CSG_SAL, TX_CSG_CRDS_ACT,
    TX_CSG_DEDUCTIBLE, PLAFOND_ABAT_10PCT_SAL, TX_ABAT_10PCT_SAL,
)
from core.ir_foyer import calcul_ir_foyer
from core.audit import TraceAudit


# ============================================================
# 2. DATACLASS RÉSULTAT
# ============================================================
@dataclass
class ResultatSalarie:
    """Résultat scénario Salarié."""
    # Inputs
    salaire_brut: float

    # Section 2 - Cotisations & net (formules C8-C11)
    cotis_salariales: float
    csg_crds_totale: float
    csg_deductible: float
    net_avant_impot: float                  # C11

    # Section 3 - IR (formules C14-C30)
    revenu_salarial_imposable: float         # C14
    abattement_10pct: float                  # C15
    revenu_imposable_net: float              # C16
    revenu_imposable_foyer: float            # C17
    ir_foyer: float                          # C23
    cehr: float                              # C25
    cdhr: float                              # C27
    total_impots_foyer: float                # C28
    impots_imputables_rem: float             # C29
    net_apres_impots: float                  # C30


# ============================================================
# 3. CALCUL MODULE SALARIÉ
# ============================================================
def calcul_module_salarie(profil: Profil,
                          salaire_brut: float,
                          *,
                          audit: TraceAudit | None = None) -> ResultatSalarie:
    """
    Transposition fidèle du module Salarié (formules C5-C30 onglet 10).

    Note : aucune correction silencieuse - les formules sont propres.
    Le seul input du module est le salaire brut annuel.

    Args:
        profil: Profil client.
        salaire_brut: Salaire brut annuel (€).
        audit: Trace d'audit optionnelle (MODE_AUDIT G2a). Side channel —
            n'affecte jamais le résultat numérique.
    """
    # Helper local : no-op si audit None, ajout d'étape sinon.
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    # --- Input ---
    _log("SAL_SALAIRE_BRUT", "Salaire brut annuel",
         salaire_brut, unite="EUR")

    # --- Section 2 : Cotisations & net (formules C8-C11) ---
    cotis_salariales = salaire_brut * TX_SALARIAL                              # C8
    csg_crds_totale = salaire_brut * ASSIETTE_CSG_SAL * TX_CSG_CRDS_ACT        # C9
    csg_deductible = salaire_brut * ASSIETTE_CSG_SAL * TX_CSG_DEDUCTIBLE       # C10
    net_avant_impot = salaire_brut - cotis_salariales - csg_crds_totale        # C11

    _log("SAL_COTISATIONS", "Cotisations sociales salarié (agrégat)",
         cotis_salariales + csg_crds_totale, unite="EUR",
         notes="Agrégat C8 + C9 (CSG/CRDS prélevée sur la fiche de paie)")
    _log("SAL_COTIS_SALARIALES", "Cotisations salariales (hors CSG/CRDS)",
         cotis_salariales, unite="EUR",
         doctrine_refs=("TX_SALARIAL",),
         hypotheses={"TX_SALARIAL": TX_SALARIAL},
         parent_id="SAL_COTISATIONS",
         notes="Formule C8 — calibrage URSSAF prudent")
    _log("SAL_CSG_CRDS_TOTALE",
         "CSG + CRDS totale (9,7 % sur 98,25 % du brut)",
         csg_crds_totale, unite="EUR",
         doctrine_refs=("ASSIETTE_CSG_SAL", "TX_CSG_CRDS_ACT"),
         hypotheses={"ASSIETTE_CSG_SAL": ASSIETTE_CSG_SAL,
                     "TX_CSG_CRDS_ACT": TX_CSG_CRDS_ACT},
         parent_id="SAL_COTISATIONS",
         notes="Formule C9 — assiette = 98,25 % du brut")
    _log("SAL_CSG_DEDUCTIBLE",
         "CSG déductible (6,8 % sur 98,25 % du brut)",
         csg_deductible, unite="EUR",
         doctrine_refs=("ASSIETTE_CSG_SAL", "TX_CSG_DEDUCTIBLE"),
         hypotheses={"ASSIETTE_CSG_SAL": ASSIETTE_CSG_SAL,
                     "TX_CSG_DEDUCTIBLE": TX_CSG_DEDUCTIBLE},
         parent_id="SAL_COTISATIONS",
         notes="Formule C10 — fraction CSG déductible du revenu imposable")

    _log("SAL_NET_AVANT_IMPOT",
         "Net avant impôt (brut − cotis − CSG/CRDS totale)",
         net_avant_impot, unite="EUR",
         notes="Formule C11 — net cash avant IR")

    # --- Section 3 : IR ---
    # C14 = C11 + C9 - C10 = brut − cotis hors CSG − CSG déductible
    # La CSG non déductible (2,9 %) reste dans la base imposable
    revenu_salarial_imposable = net_avant_impot + csg_crds_totale - csg_deductible

    _log("SAL_REVENU_SALARIAL_IMPOSABLE",
         "Revenu salarial imposable (avant abattement)",
         revenu_salarial_imposable, unite="EUR",
         notes="Formule C14 — réintégration de la CSG non déductible (2,9 %)")

    # C15 - Abattement 10 % plafonné à 14 426 €
    abattement_10pct = min(revenu_salarial_imposable * TX_ABAT_10PCT_SAL,
                           PLAFOND_ABAT_10PCT_SAL)

    _log("SAL_ABATTEMENT_10PCT",
         "Abattement forfaitaire 10 % (plafonné)",
         abattement_10pct, unite="EUR",
         doctrine_refs=("TX_ABAT_10PCT_SAL", "PLAFOND_ABAT_10PCT_SAL"),
         hypotheses={"TX_ABAT_10PCT_SAL": TX_ABAT_10PCT_SAL,
                     "PLAFOND_ABAT_10PCT_SAL": PLAFOND_ABAT_10PCT_SAL},
         notes="Formule C15 — abattement forfaitaire frais professionnels salariés")

    # C16 - Revenu imposable net
    revenu_imposable_net = max(0, revenu_salarial_imposable - abattement_10pct)

    _log("SAL_REVENU_IMPOSABLE_NET",
         "Revenu imposable net (après abattement 10 %)",
         revenu_imposable_net, unite="EUR",
         notes="Formule C16 — plancher à 0")

    # C17 - Revenu imposable foyer
    revenu_imposable_foyer = revenu_imposable_net + profil.autres_revenus

    _log("SAL_REVENU_IMPOSABLE_FOYER",
         "Revenu imposable foyer (consolidé)",
         revenu_imposable_foyer, unite="EUR",
         notes="Formule C17 — inclut autres revenus du foyer")

    # Délégation à calcul_ir_foyer pour la chaîne IR + QF + CEHR + CDHR
    impots = calcul_ir_foyer(revenu_imposable_foyer, profil)

    # C29 - Impôts imputables à la rémunération (prorata, formule directe et correcte)
    prorata = revenu_imposable_net / revenu_imposable_foyer if revenu_imposable_foyer > 0 else 1.0
    impots_imputables_rem = impots["total_impots"] * prorata

    _log("SAL_IR_FOYER_AGGREGE",
         "Impôts foyer agrégés (IR + CEHR + CDHR)",
         impots["total_impots"], unite="EUR",
         doctrine_refs=("IR_PLAFOND_T1", "IR_PLAFOND_T2",
                        "IR_PLAFOND_T3", "IR_PLAFOND_T4"),
         notes="Délégation à core.ir_foyer (chaîne IR + QF + CEHR + CDHR)")
    _log("SAL_IR_FOYER_BRUT", "IR foyer (barème + QF)",
         impots["ir_foyer"], unite="EUR",
         parent_id="SAL_IR_FOYER_AGGREGE")
    _log("SAL_CEHR", "Contribution exceptionnelle sur hauts revenus",
         impots["cehr"], unite="EUR",
         parent_id="SAL_IR_FOYER_AGGREGE")
    _log("SAL_CDHR", "Contribution différentielle sur hauts revenus",
         impots["cdhr"], unite="EUR",
         parent_id="SAL_IR_FOYER_AGGREGE")
    _log("SAL_TAUX_MOYEN_IR", "Taux moyen IR foyer appliqué",
         impots["taux_moyen"], unite="ratio",
         parent_id="SAL_IR_FOYER_AGGREGE")

    _log("SAL_IMPOTS_IMPUTABLES_REM",
         "Impôts imputables à la rémunération (prorata)",
         impots_imputables_rem, unite="EUR",
         notes=f"Formule C29 — prorata appliqué = {prorata:.4f}")

    # C30 - Net après impôts (sur la base de C11, pas C14)
    net_apres_impots = net_avant_impot - impots_imputables_rem

    _log("SAL_NET_APRES_IMPOTS",
         "Net salarié après impôts (formule C30)",
         net_apres_impots, unite="EUR",
         notes="Base C11 (net avant impôt) − impôts imputables")

    return ResultatSalarie(
        salaire_brut=salaire_brut,
        cotis_salariales=cotis_salariales,
        csg_crds_totale=csg_crds_totale,
        csg_deductible=csg_deductible,
        net_avant_impot=net_avant_impot,
        revenu_salarial_imposable=revenu_salarial_imposable,
        abattement_10pct=abattement_10pct,
        revenu_imposable_net=revenu_imposable_net,
        revenu_imposable_foyer=revenu_imposable_foyer,
        ir_foyer=impots["ir_foyer"],
        cehr=impots["cehr"],
        cdhr=impots["cdhr"],
        total_impots_foyer=impots["total_impots"],
        impots_imputables_rem=impots_imputables_rem,
        net_apres_impots=net_apres_impots,
    )
