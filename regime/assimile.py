"""
Regime Engine — Module Assimilé salarié.

Helpers de calcul propres au régime Assimilé salarié, consommés par le
Strategy Engine Assimilé (stratégies A/B/C/D).

Décisions méthodologiques (cf. Cadre v1.0.1 §3.1) :
- Taux moyen IR calculé via module Assimilé sur salaire brut de référence
  (par défaut 80 000 € comme dans la v19)
- Application uniforme du tx_ir_moy aux 4 stratégies dans le Strategy Engine
- Forfait social moyen pondéré selon effectif

Module : consomme uniquement core. Aucun import croisé vers regime/* ou strategy/*.

MODE_AUDIT (G2b) : les deux helpers (`calcul_tx_ir_moyen`, `fs_moyen_epargne`)
acceptent un paramètre opt-in `audit: TraceAudit | None`. Codes émis :
`ASSIM_TX_IR_MOY_*` et `ASSIM_FS_*`. Rétrocompat parfaite quand `audit=None`.

Note G2b : `PLAFOND_ABAT_10PCT_REF` (duplication locale de la constante
v19 14 426 €) a été supprimée au profit de `PLAFOND_ABAT_10PCT_SAL` désormais
centralisée dans `core/profil.py` (G2a). Idem pour `0.068` → `TX_CSG_DEDUCTIBLE`
et `0.10` → `TX_ABAT_10PCT_SAL`. La contrainte « éviter dépendance régime ↔
régime » est désormais respectée par construction (les constantes vivent
dans la couche `core/`, pas dans un autre régime).
"""

from core.profil import (
    Profil,
    TX_SALARIAL, TX_CSG_CRDS_ACT, ASSIETTE_CSG_SAL,
    TX_CSG_DEDUCTIBLE, PLAFOND_ABAT_10PCT_SAL, TX_ABAT_10PCT_SAL,
)
from core.ir_foyer import calcul_ir_foyer
from core.audit import TraceAudit


# ============================================================
# HELPER 1 — Taux moyen IR sur salaire de référence
# ============================================================
def calcul_tx_ir_moyen(profil: Profil,
                       *,
                       audit: TraceAudit | None = None) -> float:
    """
    TX_IR_MOY_ASS : taux moyen calculé via module Assimilé sur salaire de référence.

    Reproduit fidèlement la formule v19 cellule C33 du module 7.
    Le salaire brut utilisé est celui saisi dans le module Assimilé
    (par défaut 80 000 € comme dans la v19).

    Plancher : 5 % minimum (sécurité v19).

    Args:
        profil: Profil client (utilise `salaire_brut_assimile` et `autres_revenus`).
        audit: Trace d'audit optionnelle (MODE_AUDIT G2b). Side channel —
            n'affecte jamais la valeur retournée.
    """
    # Helper local : no-op si audit None.
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    brut = profil.salaire_brut_assimile
    cotis_salariales = brut * TX_SALARIAL
    csg_crds = brut * ASSIETTE_CSG_SAL * TX_CSG_CRDS_ACT
    csg_deductible = brut * ASSIETTE_CSG_SAL * TX_CSG_DEDUCTIBLE
    net_avant_ir = brut - cotis_salariales - csg_crds
    rev_sal_imp = net_avant_ir + csg_crds - csg_deductible
    abat = min(rev_sal_imp * TX_ABAT_10PCT_SAL, PLAFOND_ABAT_10PCT_SAL)
    rev_imp_net = max(0, rev_sal_imp - abat)
    rev_imp_foyer = rev_imp_net + profil.autres_revenus

    impots = calcul_ir_foyer(rev_imp_foyer, profil)
    tx_moy_calc = impots["total_impots"] / rev_imp_foyer if rev_imp_foyer > 0 else 0
    tx_moy_final = max(tx_moy_calc, 0.05)

    # --- Instrumentation : trace structurée des 10 étapes intermédiaires ---
    _log("ASSIM_TX_IR_MOY_BRUT_REF",
         "Salaire brut de référence Assimilé",
         brut, unite="EUR",
         notes="Profil.salaire_brut_assimile (par défaut 80 000 € v19)")
    _log("ASSIM_TX_IR_MOY_COTIS_SALARIALES",
         "Cotisations salariales sur brut de référence",
         cotis_salariales, unite="EUR",
         doctrine_refs=("TX_SALARIAL",),
         hypotheses={"TX_SALARIAL": TX_SALARIAL})
    _log("ASSIM_TX_IR_MOY_CSG_CRDS",
         "CSG + CRDS totale sur brut de référence",
         csg_crds, unite="EUR",
         doctrine_refs=("ASSIETTE_CSG_SAL", "TX_CSG_CRDS_ACT"),
         hypotheses={"ASSIETTE_CSG_SAL": ASSIETTE_CSG_SAL,
                     "TX_CSG_CRDS_ACT": TX_CSG_CRDS_ACT})
    _log("ASSIM_TX_IR_MOY_CSG_DEDUCTIBLE",
         "CSG déductible sur brut de référence",
         csg_deductible, unite="EUR",
         doctrine_refs=("ASSIETTE_CSG_SAL", "TX_CSG_DEDUCTIBLE"),
         hypotheses={"ASSIETTE_CSG_SAL": ASSIETTE_CSG_SAL,
                     "TX_CSG_DEDUCTIBLE": TX_CSG_DEDUCTIBLE})
    _log("ASSIM_TX_IR_MOY_NET_AVANT_IR",
         "Net avant IR (brut − cotis − CSG/CRDS)",
         net_avant_ir, unite="EUR")
    _log("ASSIM_TX_IR_MOY_REV_SAL_IMP",
         "Revenu salarial imposable (avant abattement)",
         rev_sal_imp, unite="EUR",
         notes="Réintégration de la CSG non déductible")
    _log("ASSIM_TX_IR_MOY_ABATTEMENT",
         "Abattement forfaitaire 10 % (plafonné)",
         abat, unite="EUR",
         doctrine_refs=("TX_ABAT_10PCT_SAL", "PLAFOND_ABAT_10PCT_SAL"),
         hypotheses={"TX_ABAT_10PCT_SAL": TX_ABAT_10PCT_SAL,
                     "PLAFOND_ABAT_10PCT_SAL": PLAFOND_ABAT_10PCT_SAL})
    _log("ASSIM_TX_IR_MOY_REV_IMP_NET",
         "Revenu imposable net (après abattement)",
         rev_imp_net, unite="EUR",
         notes="Plancher à 0")
    _log("ASSIM_TX_IR_MOY_REV_IMP_FOYER",
         "Revenu imposable foyer (consolidé)",
         rev_imp_foyer, unite="EUR",
         notes="Inclut autres revenus du foyer")
    _log("ASSIM_TX_IR_MOY_TOTAL_IMPOTS",
         "Total impôts foyer (IR + CEHR + CDHR)",
         impots["total_impots"], unite="EUR",
         doctrine_refs=("IR_PLAFOND_T1", "IR_PLAFOND_T2",
                        "IR_PLAFOND_T3", "IR_PLAFOND_T4"),
         notes="Délégation à core.ir_foyer")
    _log("ASSIM_TX_IR_MOY_RESULTAT",
         "Taux moyen IR foyer (avec plancher 5 %)",
         tx_moy_final, unite="ratio",
         hypotheses={"plancher_v19": 0.05,
                     "tx_moy_avant_plancher": tx_moy_calc},
         notes=f"Plancher v19 appliqué : {tx_moy_calc:.4f} → {tx_moy_final:.4f}")

    return tx_moy_final


# ============================================================
# HELPER 2 — Forfait social moyen selon effectif
# ============================================================
def fs_moyen_epargne(profil: Profil,
                     *,
                     audit: TraceAudit | None = None) -> float:
    """
    Forfait social moyen pondéré v19 selon effectif.

    - Sans salarié à 11-49 : 0 %
    - 50-249 salariés : 13,3 % (moyenne pondérée des dispositifs)
    - ≥ 250 salariés : 20 %

    Args:
        profil: Profil client (utilise `effectif`).
        audit: Trace d'audit optionnelle (MODE_AUDIT G2b). Side channel.
    """
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    if profil.effectif in ["Sans salarié", "1-10 salariés", "11-49 salariés"]:
        fs = 0.0
    elif profil.effectif == "50-249 salariés":
        fs = 0.133
    else:
        fs = 0.20

    _log("ASSIM_FS_MOYEN",
         "Forfait social moyen pondéré (selon effectif)",
         fs, unite="ratio",
         hypotheses={"effectif_profil": profil.effectif,
                     "fs_sans_salarie_11_49": 0.0,
                     "fs_50_249": 0.133,
                     "fs_250_plus": 0.20},
         notes=f"Table v19 — effectif retenu : {profil.effectif}")

    return fs
