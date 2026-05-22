"""
Regime Engine — Module TNS (gérant majoritaire / EURL).

Transposition fidèle de l'onglet "8. TNS" du classeur v19, avec corrections
documentées des anomalies identifiées en phase d'audit.

Décisions validées (cf. Cadre méthodologique v1.0.1 §3.2) :
- Anomalie A (C32 buggué utilisant C31 au lieu de C29) → CORRIGÉE silencieusement
- Anomalie B (doublon capital social Profil/Module) → INPUT PROFIL unique
- Anomalie C (TMI approximé sur fraction TNS-imposée) → REPRODUITE telle quelle pour parité

Module : consomme uniquement core (Profil, IR foyer). Aucun import croisé vers
d'autres regimes ou strategies.

MODE_AUDIT (B.2.5 → M2) : la fonction `calcul_module_tns` accepte un paramètre
optionnel `audit: TraceAudit | None`. Si fourni, chaque étape significative
du calcul est tracée dans l'objet. Si None (par défaut), le comportement est
strictement identique au comportement historique — aucune surcharge, aucune
modification du résultat.
"""

from dataclasses import dataclass

from core.profil import Profil, TX_TNS, TX_PFU, SEUIL_DIV_TNS
from core.ir_foyer import calcul_ir_foyer
from core.audit import TraceAudit


# ============================================================
# RÉSULTAT TNS
# ============================================================
@dataclass
class ResultatTNS:
    """Résultat complet d'un calcul TNS pour une rémunération souhaitée."""
    # Inputs
    rem_nette_souhaitee: float
    frais_reels: float

    # Section 2 - Cotisations TNS (formules C9-C12)
    cotisations_tns: float
    csg_deductible: float
    csg_non_deductible: float

    # Section 3 - IR (formules C15-C32)
    revenu_net_pro: float
    revenu_imposable: float
    revenu_imposable_foyer: float
    ir_foyer: float
    cehr: float
    cdhr: float
    total_impots_foyer: float
    taux_moyen_ir: float
    impots_imputables_rem: float

    # Section 4 - Net (formule C35)
    net_apres_ir: float

    # Section 5 - Coût (formules C38-C39)
    cout_total_societe: float
    ratio_net_cout: float

    # Section 6 - Dividendes TNS gérant maj. (formules C42-C50)
    capital_cca: float
    seuil_10pct: float
    div_bruts: float
    fraction_cotis_tns: float
    cotis_tns_sur_div: float
    fraction_pfu: float
    pfu_sur_fraction: float
    ir_sur_fraction_tns: float
    net_dividendes: float


# ============================================================
# CALCUL MODULE TNS
# ============================================================
def calcul_module_tns(profil: Profil,
                      rem_nette_souhaitee: float,
                      frais_reels: float = 0.0,
                      div_bruts: float = 0.0,
                      *,
                      audit: TraceAudit | None = None) -> ResultatTNS:
    """
    Transposition fidèle du module "8. TNS" v19.

    Correction silencieuse de l'anomalie A : formule C32 corrigée pour utiliser
    le bon taux moyen IR (C29) au lieu du bug de double division (C31).

    Args:
        profil: Profil client (avec capital_cca pris du Profil, décision B)
        rem_nette_souhaitee: Rémunération nette annuelle souhaitée (€)
        frais_reels: Frais réels professionnels déductibles (€)
        div_bruts: Dividendes bruts envisagés (€)
        audit: Trace d'audit optionnelle (MODE_AUDIT). Si fournie, chaque étape
            significative y est enregistrée. Side channel — n'affecte jamais
            le résultat numérique.
    """
    # Helper local : no-op si audit None, ajout d'étape sinon.
    # Court-circuit éclair pour ne pas pénaliser le hot path quand audit=None.
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    # --- Section 1 : Inputs ---
    _log("TNS_REM_BRUTE", "Rémunération nette souhaitée appliquée",
         rem_nette_souhaitee, unite="EUR")

    # --- Section 2 : Cotisations TNS (formules C9-C12) ---
    cotisations_tns = rem_nette_souhaitee * TX_TNS
    csg_deductible = (rem_nette_souhaitee + cotisations_tns) * 0.068
    csg_non_deductible = (rem_nette_souhaitee + cotisations_tns) * 0.029

    _log("TNS_COTIS_SOCIALES", "Cotisations sociales TNS (agrégat)",
         cotisations_tns + csg_deductible + csg_non_deductible, unite="EUR")
    _log("TNS_COTIS_TNS_BASE",
         "Cotisations TNS base (hors CSG)",
         cotisations_tns, unite="EUR",
         doctrine_refs=("TX_TNS",),
         hypotheses={"TX_TNS": TX_TNS},
         parent_id="TNS_COTIS_SOCIALES",
         notes="Calibrage URSSAF prudent (méthodologie v19)")
    _log("TNS_CSG_DEDUCTIBLE", "CSG déductible (6,8 %)",
         csg_deductible, unite="EUR",
         hypotheses={"TX_CSG_DEDUCTIBLE": 0.068},
         parent_id="TNS_COTIS_SOCIALES")
    _log("TNS_CSG_NON_DEDUCTIBLE", "CSG non déductible (2,9 %)",
         csg_non_deductible, unite="EUR",
         hypotheses={"TX_CSG_NON_DEDUCTIBLE": 0.029},
         parent_id="TNS_COTIS_SOCIALES")

    # --- Section 3 : IR (formules C15-C32) ---
    revenu_net_pro = rem_nette_souhaitee - frais_reels
    revenu_imposable = revenu_net_pro + csg_non_deductible  # formule C16
    revenu_imposable_foyer = revenu_imposable + profil.autres_revenus  # formule C17

    _log("TNS_REVENU_NET_PRO", "Revenu net professionnel après frais réels",
         revenu_net_pro, unite="EUR")
    _log("TNS_REVENU_IMPOSABLE", "Revenu imposable individuel TNS",
         revenu_imposable, unite="EUR",
         notes="Inclut CSG non déductible (formule C16 v19)")
    _log("TNS_REVENU_IMPOSABLE_FOYER", "Revenu imposable foyer (consolidé)",
         revenu_imposable_foyer, unite="EUR",
         notes="Inclut autres revenus du conjoint et hors-pro (formule C17 v19)")

    # Délégation à calcul_ir_foyer pour la chaîne IR + QF + CEHR + CDHR
    impots = calcul_ir_foyer(revenu_imposable_foyer, profil)

    # Impôts imputables à la rémunération (prorata)
    # CORRECTION ANOMALIE A : utilisation du vrai taux moyen (C29) et non C31 buggué
    prorata = revenu_imposable / revenu_imposable_foyer if revenu_imposable_foyer > 0 else 0.0
    impots_imputables_rem = impots["taux_moyen"] * revenu_imposable_foyer * prorata

    _log("TNS_IR_FOYER_AGGREGE", "Impôts foyer agrégés (IR + CEHR + CDHR)",
         impots["total_impots"], unite="EUR",
         doctrine_refs=("IR_PLAFOND_T1", "IR_PLAFOND_T2",
                        "IR_PLAFOND_T3", "IR_PLAFOND_T4"),
         notes="Délégation à core.ir_foyer (chaîne IR + QF + CEHR + CDHR)")
    _log("TNS_IR_FOYER_BRUT", "IR foyer (barème + QF)",
         impots["ir_foyer"], unite="EUR",
         parent_id="TNS_IR_FOYER_AGGREGE")
    _log("TNS_CEHR", "Contribution exceptionnelle sur hauts revenus",
         impots["cehr"], unite="EUR",
         parent_id="TNS_IR_FOYER_AGGREGE")
    _log("TNS_CDHR", "Contribution différentielle sur hauts revenus",
         impots["cdhr"], unite="EUR",
         parent_id="TNS_IR_FOYER_AGGREGE")
    _log("TNS_TAUX_MOYEN_IR", "Taux moyen IR foyer appliqué",
         impots["taux_moyen"], unite="ratio",
         parent_id="TNS_IR_FOYER_AGGREGE",
         notes="Anomalie A v19 corrigée : utilise C29 et non C31 buggué")
    _log("TNS_IMPOTS_IMPUTABLES_REM",
         "Impôts imputables à la rémunération (prorata)",
         impots_imputables_rem, unite="EUR",
         parent_id="TNS_IR_FOYER_AGGREGE",
         notes=f"prorata appliqué = {prorata:.4f}")

    # --- Section 4 : Net dirigeant après IR (formule C35) ---
    net_apres_ir = rem_nette_souhaitee - impots_imputables_rem
    _log("TNS_NET_APRES_IR", "Net dirigeant après IR (formule C35)",
         net_apres_ir, unite="EUR")

    # --- Section 5 : Coût pour la société (formules C38-C39) ---
    cout_total_societe = rem_nette_souhaitee + cotisations_tns
    ratio_net_cout = net_apres_ir / cout_total_societe if cout_total_societe > 0 else 0.0
    _log("TNS_COUT_SOCIETE", "Coût total pour la société",
         cout_total_societe, unite="EUR",
         notes=f"ratio net/coût = {ratio_net_cout:.4f}")

    # --- Section 6 : Dividendes TNS gérant majoritaire (formules C42-C50) ---
    seuil_10pct = profil.capital_cca * SEUIL_DIV_TNS
    fraction_cotis_tns = max(0, div_bruts - seuil_10pct)
    cotis_tns_sur_div = fraction_cotis_tns * TX_TNS
    fraction_pfu = div_bruts - fraction_cotis_tns
    pfu_sur_fraction = fraction_pfu * TX_PFU

    # IR sur fraction TNS-imposée : approximation v19 (TMI selon revenu par part)
    # Anomalie C - reproduite telle quelle (décision C)
    tmi = impots["tmi"]
    ir_sur_fraction_tns = fraction_cotis_tns * tmi

    net_dividendes = div_bruts - cotis_tns_sur_div - pfu_sur_fraction - ir_sur_fraction_tns

    _log("TNS_DIVIDENDES", "Dividendes TNS — agrégat",
         div_bruts, unite="EUR",
         notes="Section 6 v19 (formules C42-C50)")
    _log("TNS_DIV_SEUIL_10PCT", "Seuil 10 % du capital + CCA",
         seuil_10pct, unite="EUR",
         doctrine_refs=("SEUIL_DIV_TNS",),
         hypotheses={"SEUIL_DIV_TNS": SEUIL_DIV_TNS,
                     "capital_cca_profil": profil.capital_cca},
         parent_id="TNS_DIVIDENDES")
    _log("TNS_DIV_FRACTION_COTIS_TNS",
         "Fraction TNS-imposée (au-delà du seuil 10 %)",
         fraction_cotis_tns, unite="EUR",
         parent_id="TNS_DIVIDENDES")
    _log("TNS_DIV_COTIS_TNS_SUR_DIV",
         "Cotisations TNS sur fraction TNS-imposée",
         cotis_tns_sur_div, unite="EUR",
         doctrine_refs=("TX_TNS",),
         hypotheses={"TX_TNS": TX_TNS},
         parent_id="TNS_DIVIDENDES")
    _log("TNS_DIV_FRACTION_PFU", "Fraction PFU (sous le seuil 10 %)",
         fraction_pfu, unite="EUR",
         parent_id="TNS_DIVIDENDES")
    _log("TNS_DIV_PFU_SUR_FRACTION", "PFU sur fraction sous seuil",
         pfu_sur_fraction, unite="EUR",
         doctrine_refs=("TX_PFU",),
         hypotheses={"TX_PFU": TX_PFU},
         parent_id="TNS_DIVIDENDES")
    _log("TNS_DIV_IR_SUR_FRACTION_TNS",
         "IR sur fraction TNS-imposée (TMI v19)",
         ir_sur_fraction_tns, unite="EUR",
         hypotheses={"tmi_appliquee": tmi},
         parent_id="TNS_DIVIDENDES",
         notes="Anomalie C reproduite telle quelle (approximation TMI v19)")
    _log("TNS_DIV_NET", "Dividendes nets après prélèvements",
         net_dividendes, unite="EUR",
         parent_id="TNS_DIVIDENDES")

    return ResultatTNS(
        rem_nette_souhaitee=rem_nette_souhaitee,
        frais_reels=frais_reels,
        cotisations_tns=cotisations_tns,
        csg_deductible=csg_deductible,
        csg_non_deductible=csg_non_deductible,
        revenu_net_pro=revenu_net_pro,
        revenu_imposable=revenu_imposable,
        revenu_imposable_foyer=revenu_imposable_foyer,
        ir_foyer=impots["ir_foyer"],
        cehr=impots["cehr"],
        cdhr=impots["cdhr"],
        total_impots_foyer=impots["total_impots"],
        taux_moyen_ir=impots["taux_moyen"],
        impots_imputables_rem=impots_imputables_rem,
        net_apres_ir=net_apres_ir,
        cout_total_societe=cout_total_societe,
        ratio_net_cout=ratio_net_cout,
        capital_cca=profil.capital_cca,
        seuil_10pct=seuil_10pct,
        div_bruts=div_bruts,
        fraction_cotis_tns=fraction_cotis_tns,
        cotis_tns_sur_div=cotis_tns_sur_div,
        fraction_pfu=fraction_pfu,
        pfu_sur_fraction=pfu_sur_fraction,
        ir_sur_fraction_tns=ir_sur_fraction_tns,
        net_dividendes=net_dividendes,
    )
