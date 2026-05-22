"""
Regime Engine — Module Libéral (BNC + SEL).

Transposition fidèle de l'onglet "9. Libéral" du classeur v19.

Décisions validées (cf. Cadre méthodologique v1.0.1 §3.3) :
- Fiscalité dirigeant SEL : périmètre v19 conservé (uniquement IS société dans ce module)
- Dissymétrie CSG non déductible (Libéral sur bénéfice seul vs TNS sur net+cot) : reproduite
- Taux réduit IS appliqué jusqu'à 42 500 € sans vérification éligibilité PME : reproduit

Structure :
    1. Imports et constantes
    2. Dataclasses résultats BNC / SEL
    3. calcul_module_bnc()    — instrumenté MODE_AUDIT (G1a)
    4. calcul_module_sel()    — non instrumenté à ce jour (G1b prévu)

MODE_AUDIT (G1a) : `calcul_module_bnc()` accepte un paramètre opt-in
`audit: TraceAudit | None`. Codes émis : `LIB_BNC_*`. Rétrocompat parfaite
quand `audit=None`.
"""

# ============================================================
# 1. IMPORTS
# ============================================================
from dataclasses import dataclass

from core.profil import (
    Profil, TX_LIB,
    TX_IS_REDUIT, TX_IS_NORMAL, IS_PLAF_REDUIT,
)
from core.ir_foyer import calcul_ir_foyer
from core.audit import TraceAudit


# ============================================================
# 2. DATACLASSES RÉSULTATS BNC / SEL
# ============================================================
@dataclass
class ResultatBNC:
    """Résultat scénario BNC (exercice individuel)."""
    # Inputs
    recettes: float
    frais_pro: float

    # Section BNC (formules C7-C25)
    benefice_bnc: float
    cotisations: float
    csg_non_deductible: float
    benefice_net_apres_cotis: float       # C10 - base du net cash
    revenu_imposable_lib: float           # C11 - réintégration CSG non déd.
    revenu_imposable_foyer: float         # C12
    ir_foyer: float
    cehr: float
    cdhr: float
    total_impots_foyer: float
    impots_imputables_libéral: float       # C24
    net_apres_impots: float                # C25


@dataclass
class ResultatSEL:
    """Résultat scénario SEL (SELARL/SELAS - double couche IS + IR)."""
    # Inputs
    benefice_avant_rem: float
    remuneration_dirigeant: float

    # Section SEL (formules C28-C33)
    benefice_imposable_is: float
    is_du: float
    resultat_net_distribuable: float
    dividendes_envisages: float


# ============================================================
# 3. CALCUL SCÉNARIO BNC (formules C5-C25)
# ============================================================
def calcul_module_bnc(profil: Profil,
                      recettes: float,
                      frais_pro: float = 0.0,
                      *,
                      audit: TraceAudit | None = None) -> ResultatBNC:
    """
    Transposition fidèle du scénario BNC (formules C5-C25 onglet 9).

    Note : aucune correction silencieuse n'est nécessaire ici.
    La formule C24 est mathématiquement correcte (contrairement au TNS C32).

    Args:
        profil: Profil client.
        recettes: Recettes brutes annuelles (€).
        frais_pro: Frais professionnels déductibles (€).
        audit: Trace d'audit optionnelle (MODE_AUDIT G1a). Side channel —
            n'affecte jamais le résultat numérique.
    """
    # Helper local : no-op si audit None, ajout d'étape sinon.
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    # --- Inputs ---
    _log("LIB_BNC_RECETTES", "Recettes brutes annuelles BNC",
         recettes, unite="EUR")

    # --- Section calcul du bénéfice et des cotisations ---
    benefice_bnc = recettes - frais_pro                              # C7
    cotisations = benefice_bnc * TX_LIB                              # C8 - inclut CSG/CRDS selon E8
    csg_non_deductible = benefice_bnc * 0.029                        # C9 - sur bénéfice (pas sur net+cot, différence avec TNS)
    benefice_net_apres_cotis = benefice_bnc - cotisations            # C10 - cash réellement perçu

    _log("LIB_BNC_BENEFICE", "Bénéfice BNC (recettes − frais)",
         benefice_bnc, unite="EUR",
         notes="Formule C7 onglet 9 v19")
    _log("LIB_BNC_FRAIS_PRO", "Frais professionnels déductibles",
         frais_pro, unite="EUR",
         parent_id="LIB_BNC_BENEFICE")
    _log("LIB_BNC_BENEFICE_NET", "Bénéfice net après cotisations (cash perçu)",
         benefice_net_apres_cotis, unite="EUR",
         parent_id="LIB_BNC_BENEFICE",
         notes="Formule C10 — base du calcul de net cash")

    _log("LIB_BNC_COTISATIONS", "Cotisations sociales Libéral (agrégat)",
         cotisations + csg_non_deductible, unite="EUR")
    _log("LIB_BNC_COTIS_BASE",
         "Cotisations Libéral base (inclut CSG/CRDS selon E8)",
         cotisations, unite="EUR",
         doctrine_refs=("TX_LIB",),
         hypotheses={"TX_LIB": TX_LIB},
         parent_id="LIB_BNC_COTISATIONS",
         notes="Formule C8 onglet 9 v19")
    _log("LIB_BNC_CSG_NON_DEDUCTIBLE",
         "CSG non déductible (2,9 %) — appliquée sur bénéfice (dissymétrie vs TNS)",
         csg_non_deductible, unite="EUR",
         hypotheses={"TX_CSG_NON_DEDUCTIBLE": 0.029},
         parent_id="LIB_BNC_COTISATIONS",
         notes="Formule C9 — dissymétrie v1.0.1 §3.3 : assiette = bénéfice "
               "(et non net+cotisations comme en TNS)")

    # --- Section IR ---
    revenu_imposable_lib = benefice_net_apres_cotis + csg_non_deductible   # C11 - réintégration CSG
    revenu_imposable_foyer = revenu_imposable_lib + profil.autres_revenus  # C12

    _log("LIB_BNC_REVENU_IMPOSABLE_LIB",
         "Revenu imposable individuel Libéral",
         revenu_imposable_lib, unite="EUR",
         notes="Formule C11 — bénéfice net + réintégration CSG non déd.")
    _log("LIB_BNC_REVENU_IMPOSABLE_FOYER",
         "Revenu imposable foyer (consolidé)",
         revenu_imposable_foyer, unite="EUR",
         notes="Formule C12 — inclut autres revenus du foyer")

    # Délégation à calcul_ir_foyer pour la chaîne IR + QF + CEHR + CDHR
    impots = calcul_ir_foyer(revenu_imposable_foyer, profil)

    # Impôts imputables à l'activité libérale (formule C24 - mathématiquement correcte)
    # C24 = C23 × (C11/C12) = total_impots × (rev_lib / rev_foyer)
    prorata_lib = revenu_imposable_lib / revenu_imposable_foyer if revenu_imposable_foyer > 0 else 1.0
    impots_imputables = impots["total_impots"] * prorata_lib

    _log("LIB_BNC_IR_FOYER_AGGREGE",
         "Impôts foyer agrégés (IR + CEHR + CDHR)",
         impots["total_impots"], unite="EUR",
         doctrine_refs=("IR_PLAFOND_T1", "IR_PLAFOND_T2",
                        "IR_PLAFOND_T3", "IR_PLAFOND_T4"),
         notes="Délégation à core.ir_foyer (chaîne IR + QF + CEHR + CDHR)")
    _log("LIB_BNC_IR_FOYER_BRUT", "IR foyer (barème + QF)",
         impots["ir_foyer"], unite="EUR",
         parent_id="LIB_BNC_IR_FOYER_AGGREGE")
    _log("LIB_BNC_CEHR", "Contribution exceptionnelle sur hauts revenus",
         impots["cehr"], unite="EUR",
         parent_id="LIB_BNC_IR_FOYER_AGGREGE")
    _log("LIB_BNC_CDHR", "Contribution différentielle sur hauts revenus",
         impots["cdhr"], unite="EUR",
         parent_id="LIB_BNC_IR_FOYER_AGGREGE")
    _log("LIB_BNC_TAUX_MOYEN_IR", "Taux moyen IR foyer appliqué",
         impots["taux_moyen"], unite="ratio",
         parent_id="LIB_BNC_IR_FOYER_AGGREGE")

    _log("LIB_BNC_IMPOTS_IMPUTABLES",
         "Impôts imputables à l'activité libérale (prorata)",
         impots_imputables, unite="EUR",
         notes=f"Formule C24 — prorata appliqué = {prorata_lib:.4f}")

    # Net libéral après impôts (formule C25)
    # = bénéfice net cash (C10) − impôts imputables
    net_apres_impots = benefice_net_apres_cotis - impots_imputables

    _log("LIB_BNC_NET_APRES_IMPOTS",
         "Net libéral après impôts (formule C25)",
         net_apres_impots, unite="EUR")

    return ResultatBNC(
        recettes=recettes,
        frais_pro=frais_pro,
        benefice_bnc=benefice_bnc,
        cotisations=cotisations,
        csg_non_deductible=csg_non_deductible,
        benefice_net_apres_cotis=benefice_net_apres_cotis,
        revenu_imposable_lib=revenu_imposable_lib,
        revenu_imposable_foyer=revenu_imposable_foyer,
        ir_foyer=impots["ir_foyer"],
        cehr=impots["cehr"],
        cdhr=impots["cdhr"],
        total_impots_foyer=impots["total_impots"],
        impots_imputables_libéral=impots_imputables,
        net_apres_impots=net_apres_impots,
    )


# ============================================================
# 4. CALCUL SCÉNARIO SEL (formules C28-C33)
# ============================================================
def calcul_module_sel(benefice_avant_rem: float,
                      remuneration_dirigeant: float,
                      *,
                      audit: TraceAudit | None = None) -> ResultatSEL:
    """
    Transposition fidèle du scénario SEL (formules C28-C33 onglet 9).

    Périmètre v19 : uniquement IS société (la fiscalité du dirigeant SEL
    est traitée dans le module 7 Assimilé pour SELAS ou module 8 TNS pour SELARL).

    Note : applique systématiquement le taux IS réduit 15 % jusqu'à 42 500 €
    sans vérifier l'éligibilité PME — simplification v19 reproduite.

    Args:
        benefice_avant_rem: Bénéfice avant rémunération dirigeant (€).
        remuneration_dirigeant: Rémunération dirigeant prélevée (€).
        audit: Trace d'audit optionnelle (MODE_AUDIT G1b). Side channel —
            n'affecte jamais le résultat numérique.
    """
    # Helper local : no-op si audit None, ajout d'étape sinon.
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    # --- Inputs ---
    _log("LIB_SEL_BENEFICE_AVANT_REM",
         "Bénéfice avant rémunération dirigeant",
         benefice_avant_rem, unite="EUR")
    _log("LIB_SEL_REMUNERATION_DIRIGEANT",
         "Rémunération dirigeant prélevée (charge déductible)",
         remuneration_dirigeant, unite="EUR")

    # Bénéfice imposable IS (formule C30)
    benefice_imposable_is = max(0, benefice_avant_rem - remuneration_dirigeant)

    _log("LIB_SEL_BENEFICE_IMPOSABLE_IS",
         "Bénéfice imposable à l'IS (agrégat)",
         benefice_imposable_is, unite="EUR",
         notes="Formule C30 onglet 9 v19 — plancher à 0")

    # IS dû (formule C31)
    fraction_reduite = min(benefice_imposable_is, IS_PLAF_REDUIT)
    fraction_normale = max(0, benefice_imposable_is - IS_PLAF_REDUIT)
    is_du = fraction_reduite * TX_IS_REDUIT + fraction_normale * TX_IS_NORMAL

    _log("LIB_SEL_FRACTION_REDUITE",
         "Fraction imposée au taux IS réduit (15 %)",
         fraction_reduite, unite="EUR",
         doctrine_refs=("IS_PLAF_REDUIT", "TX_IS_REDUIT"),
         hypotheses={"IS_PLAF_REDUIT": IS_PLAF_REDUIT,
                     "TX_IS_REDUIT": TX_IS_REDUIT},
         parent_id="LIB_SEL_BENEFICE_IMPOSABLE_IS",
         notes="Simplification v19 : éligibilité PME non vérifiée")
    _log("LIB_SEL_FRACTION_NORMALE",
         "Fraction imposée au taux IS normal (25 %)",
         fraction_normale, unite="EUR",
         doctrine_refs=("TX_IS_NORMAL",),
         hypotheses={"TX_IS_NORMAL": TX_IS_NORMAL},
         parent_id="LIB_SEL_BENEFICE_IMPOSABLE_IS")
    _log("LIB_SEL_IS_DU",
         "Impôt sur les sociétés total dû",
         is_du, unite="EUR",
         parent_id="LIB_SEL_BENEFICE_IMPOSABLE_IS",
         notes="Formule C31 — somme fraction réduite + fraction normale")

    # Résultat net distribuable (formule C32)
    resultat_net_distribuable = benefice_imposable_is - is_du

    _log("LIB_SEL_RESULTAT_NET_DISTRIBUABLE",
         "Résultat net distribuable (après IS)",
         resultat_net_distribuable, unite="EUR",
         notes="Formule C32 — bénéfice imposable − IS dû")

    # Dividendes envisagés - par défaut = totalité du résultat net (formule C33)
    dividendes_envisages = resultat_net_distribuable

    _log("LIB_SEL_DIVIDENDES_ENVISAGES",
         "Dividendes envisagés (= totalité résultat net par défaut)",
         dividendes_envisages, unite="EUR",
         notes="Formule C33 — fiscalité dirigeant traitée dans module Assimilé "
               "(SELAS) ou TNS (SELARL), hors périmètre SEL v19")

    return ResultatSEL(
        benefice_avant_rem=benefice_avant_rem,
        remuneration_dirigeant=remuneration_dirigeant,
        benefice_imposable_is=benefice_imposable_is,
        is_du=is_du,
        resultat_net_distribuable=resultat_net_distribuable,
        dividendes_envisages=dividendes_envisages,
    )
