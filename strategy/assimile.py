"""
Strategy Engine — Stratégies Assimilé salarié.

Quatre stratégies d'allocation d'enveloppe à coût société constant :
- A : 100 % rémunération
- B : 60 % rémunération / 40 % dividendes
- C : + Épargne salariale & PER (50/30/20)
- D : + Périphériques & cashback (45/25/20/10)

Décisions méthodologiques (cf. Cadre v1.0.1 §4.1) :
- Allocation à enveloppe constante (coût total société)
- Application uniforme du taux moyen IR (calculé par regime/assimile.py)
- Stratégie « retenue par défaut » = stratégie qui maximise le net dirigeant
  immédiat (clé technique `recommandee` du dict, conservée pour rétrocompat
  Phase A — l'UI / PDF affichent désormais "stratégie retenue" et non
  "recommandée").

Module : consomme core (profil, constantes) + regime/assimile (helpers).
Aucun import vers d'autres strategy/*.

MODE_AUDIT (G3a, spec 1.1.0) :
- `calcul_strategie()` accepte un paramètre opt-in `audit: TraceAudit | None`.
  Codes émis : `STRAT_ASSIM_<X>_*` où `<X>` est la stratégie (A/B/C/D).
- `arbitrage_complet()` accepte le même paramètre. Codes émis : `STRAT_ASSIM_*`
  (niveau méta), et **attache des sous-traces nommées** pour les 4 stratégies
  et l'appel à `calcul_tx_ir_moyen`. Modèle composable : pas de duplication
  des étapes régime, navigation par `trace.sous_traces[nom]`.

Conventions appliquées :
- Vocabulaire strictement non-prescriptif : `STRAT_ASSIM_RETENU`,
  `STRAT_ASSIM_CRITERE_RETENU`, `STRAT_ASSIM_DELTA_X_VS_A` (factuels).
- Les labels et notes respectent les restrictions terminologiques définies
  dans TERMINOLOGY.md §2. Aucun wording prescriptif dans la trace.
- Le critère de sélection est explicité comme hypothèse (`critere`),
  le résultat dérive mécaniquement.
"""

from core.profil import (
    Profil,
    TX_PATRONAL, TX_SALARIAL, TX_CSG_CRDS_ACT, ASSIETTE_CSG_SAL,
    TX_PFU, TX_IS_REDUIT, TX_IS_NORMAL, IS_PLAF_REDUIT,
)
from core.audit import TraceAudit
from regime.assimile import calcul_tx_ir_moyen, fs_moyen_epargne


# ============================================================
# DÉFINITION DES STRATÉGIES A/B/C/D
# ============================================================
STRATEGIES = {
    "A": {"nom": "100 % rémunération",
          "salaire": 1.00, "dividendes": 0.00, "epargne": 0.00, "peripheriques": 0.00},
    "B": {"nom": "60 % rém / 40 % dividendes",
          "salaire": 0.60, "dividendes": 0.40, "epargne": 0.00, "peripheriques": 0.00},
    "C": {"nom": "+ Épargne salariale & PER",
          "salaire": 0.50, "dividendes": 0.30, "epargne": 0.20, "peripheriques": 0.00},
    "D": {"nom": "+ Périphériques & cashback",
          "salaire": 0.45, "dividendes": 0.25, "epargne": 0.20, "peripheriques": 0.10},
}


# ============================================================
# CALCUL D'UNE STRATÉGIE
# ============================================================
def calcul_strategie(profil: Profil,
                     code: str,
                     tx_ir_moy: float,
                     *,
                     audit: TraceAudit | None = None) -> dict:
    """
    Calcule une stratégie A/B/C/D pour un profil donné.

    Args:
        profil: Profil client (avec enveloppe à arbitrer).
        code: "A", "B", "C" ou "D".
        tx_ir_moy: Taux moyen IR pré-calculé (via regime.assimile).
        audit: Trace d'audit optionnelle (MODE_AUDIT G3a). Side channel —
            n'affecte jamais le résultat. Codes émis : `STRAT_ASSIM_<code>_*`.

    Returns:
        dict avec décomposition coûts, nets et efficacité.
    """
    # Helper local : préfixe les codes avec STRAT_ASSIM_<code>_ pour
    # éviter les collisions quand le caller appelle 4 fois cette fonction.
    prefix = f"STRAT_ASSIM_{code}_"

    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add(prefix + suffixe, label, valeur, **kw)

    strat = STRATEGIES[code]
    env = profil.enveloppe

    cout_salaire = env * strat["salaire"]
    cout_div = env * strat["dividendes"]
    cout_epargne = env * strat["epargne"]
    cout_periph = env * strat["peripheriques"]
    cout_total = cout_salaire + cout_div + cout_epargne + cout_periph

    _log("ENVELOPPE", "Enveloppe coût société (input)",
         env, unite="EUR",
         hypotheses={"strategie_code": code, "strategie_nom": strat["nom"]})
    _log("TX_IR_MOY_APPLIQUE",
         "Taux moyen IR appliqué (en provenance amont)",
         tx_ir_moy, unite="ratio",
         notes="Hypothèse uniforme v19 : taux moyen IR identique aux 4 stratégies")

    _log("ALLOCATION",
         "Allocation enveloppe en 4 postes (agrégat)",
         cout_total, unite="EUR",
         hypotheses={"part_salaire": strat["salaire"],
                     "part_dividendes": strat["dividendes"],
                     "part_epargne": strat["epargne"],
                     "part_peripheriques": strat["peripheriques"]})
    _log("ALLOC_SALAIRE", "Coût salaire (part de l'enveloppe)",
         cout_salaire, unite="EUR",
         parent_id=prefix + "ALLOCATION")
    _log("ALLOC_DIVIDENDES", "Coût dividendes (part de l'enveloppe)",
         cout_div, unite="EUR",
         parent_id=prefix + "ALLOCATION")
    _log("ALLOC_EPARGNE", "Coût épargne salariale (part de l'enveloppe)",
         cout_epargne, unite="EUR",
         parent_id=prefix + "ALLOCATION")
    _log("ALLOC_PERIPHERIQUES", "Coût périphériques (part de l'enveloppe)",
         cout_periph, unite="EUR",
         parent_id=prefix + "ALLOCATION")

    # Net salaire (formule C21 v19)
    if cout_salaire > 0:
        brut = cout_salaire / (1 + TX_PATRONAL)
        net_avant_ir = brut * (1 - TX_SALARIAL - ASSIETTE_CSG_SAL * 0.097)
        net_salaire = net_avant_ir * (1 - tx_ir_moy)
    else:
        brut = 0.0
        net_avant_ir = 0.0
        net_salaire = 0.0

    _log("NET_SALAIRE",
         "Net salaire après cotisations + IR",
         net_salaire, unite="EUR",
         doctrine_refs=("TX_PATRONAL", "TX_SALARIAL",
                        "ASSIETTE_CSG_SAL", "TX_CSG_CRDS_ACT"),
         hypotheses={"TX_PATRONAL": TX_PATRONAL,
                     "TX_SALARIAL": TX_SALARIAL,
                     "ASSIETTE_CSG_SAL": ASSIETTE_CSG_SAL,
                     "brut_calcule": brut,
                     "net_avant_ir_calcule": net_avant_ir},
         notes="Formule C21 v19 — chaîne brut/net unique stratégie")

    # Net dividendes (formule C22 v19 branche non-TNS)
    if cout_div > 0:
        is_reduit = min(cout_div, IS_PLAF_REDUIT) * TX_IS_REDUIT
        is_normal = max(0, cout_div - IS_PLAF_REDUIT) * TX_IS_NORMAL
        distribuable = cout_div - is_reduit - is_normal
        net_div = distribuable * (1 - TX_PFU)
    else:
        is_reduit = 0.0
        is_normal = 0.0
        distribuable = 0.0
        net_div = 0.0

    _log("NET_DIVIDENDES",
         "Net dividendes après IS + PFU",
         net_div, unite="EUR",
         doctrine_refs=("TX_IS_REDUIT", "TX_IS_NORMAL",
                        "IS_PLAF_REDUIT", "TX_PFU"),
         hypotheses={"TX_IS_REDUIT": TX_IS_REDUIT,
                     "TX_IS_NORMAL": TX_IS_NORMAL,
                     "IS_PLAF_REDUIT": IS_PLAF_REDUIT,
                     "TX_PFU": TX_PFU,
                     "is_reduit_calcule": is_reduit,
                     "is_normal_calcule": is_normal,
                     "distribuable_calcule": distribuable},
         notes="Formule C22 v19 (branche non-TNS)")

    # Net épargne (formule C23 v19)
    if cout_epargne > 0:
        fs = fs_moyen_epargne(profil)
        montant_brut = cout_epargne / (1 + fs)
        net_epargne = montant_brut * (1 - TX_CSG_CRDS_ACT)
    else:
        fs = 0.0
        montant_brut = 0.0
        net_epargne = 0.0

    _log("NET_EPARGNE",
         "Net épargne salariale après FS + CSG/CRDS",
         net_epargne, unite="EUR",
         doctrine_refs=("TX_CSG_CRDS_ACT",),
         hypotheses={"TX_CSG_CRDS_ACT": TX_CSG_CRDS_ACT,
                     "fs_applique": fs,
                     "montant_brut_calcule": montant_brut},
         notes="Formule C23 v19. FS pondéré selon effectif — détail "
               "dans sous-trace fs_moyen_epargne (si attachée)")

    # Net périphériques (formule C24 v19)
    net_periph = cout_periph * 0.95

    _log("NET_PERIPHERIQUES",
         "Net périphériques (forfait 95 % du coût)",
         net_periph, unite="EUR",
         hypotheses={"tx_efficacite_periph": 0.95},
         notes="Formule C24 v19 — forfait de transformation")

    total_net = net_salaire + net_div + net_epargne + net_periph
    efficacite = total_net / cout_total if cout_total > 0 else 0

    _log("TOTAL_NET",
         "Total net 4 postes (salaire + div + épargne + périph)",
         total_net, unite="EUR")
    _log("EFFICACITE",
         "Ratio total_net / coût_total",
         efficacite, unite="ratio")

    return {
        "code": code,
        "nom": strat["nom"],
        "cout_salaire": cout_salaire,
        "cout_dividendes": cout_div,
        "cout_epargne": cout_epargne,
        "cout_peripheriques": cout_periph,
        "cout_total": cout_total,
        "net_salaire": net_salaire,
        "net_dividendes": net_div,
        "net_epargne": net_epargne,
        "net_peripheriques": net_periph,
        "total_net": total_net,
        "efficacite": efficacite,
        "gain_vs_a": 0,
        "tx_ir_moy": tx_ir_moy,
    }


# ============================================================
# ARBITRAGE COMPLET (boucle sur les 4 stratégies)
# ============================================================
def arbitrage_complet(profil: Profil,
                      *,
                      audit: TraceAudit | None = None) -> dict:
    """
    Calcule les 4 stratégies A/B/C/D et identifie la stratégie au meilleur net.

    Note terminologique : la clé `recommandee` du dict de retour est
    historique (Phase A). Elle référence le code de la stratégie au plus
    haut `total_net`, c'est-à-dire un indicateur **technique**, pas une
    recommandation au sens conseil. L'UI et le PDF utilisent désormais
    « stratégie retenue » dans leur rendu visuel.

    Args:
        profil: Profil client.
        audit: Trace d'audit optionnelle (MODE_AUDIT G3a, spec 1.1.0).
            Side channel. Si fournie, attache 5 sous-traces nommées :
            - `"tx_ir_moy"` : trace de `calcul_tx_ir_moyen`
            - `"strategie_A"`, `"strategie_B"`, `"strategie_C"`, `"strategie_D"` :
              traces de `calcul_strategie` pour chaque code.

    Returns:
        dict avec :
        - strategies: dict {code: résultat}
        - recommandee: code de la stratégie au plus haut net (indicateur technique)
        - tx_ir_moy: taux moyen IR appliqué uniformément
    """
    def _log(code, label, valeur, **kw):
        if audit is not None:
            audit.add(code, label, valeur, **kw)

    # --- Étape amont : taux moyen IR (avec sous-trace si audit demandé) ---
    if audit is not None:
        sous_trace_tx_ir = TraceAudit(
            regime="Assimilé (TX_IR_MOY)",
            profil_resume=f"contexte arbitrage Assimilé, brut_ref={profil.salaire_brut_assimile}",
        )
        tx_ir_moy = calcul_tx_ir_moyen(profil, audit=sous_trace_tx_ir)
        audit.attacher_sous_trace("tx_ir_moy", sous_trace_tx_ir)
    else:
        tx_ir_moy = calcul_tx_ir_moyen(profil)

    _log("STRAT_ASSIM_TX_IR_MOY_RACINE",
         "Taux moyen IR de référence (calculé en amont, partagé par les 4 stratégies)",
         tx_ir_moy, unite="ratio",
         notes="Voir sous-trace 'tx_ir_moy' pour la chaîne de calcul détaillée")

    # --- Calcul des 4 stratégies (chacune dans sa sous-trace) ---
    strategies = {}
    for code in STRATEGIES:
        if audit is not None:
            sous_strat = TraceAudit(
                regime=f"Stratégie Assimilé/{code}",
                profil_resume=f"enveloppe={profil.enveloppe}, "
                              f"tx_ir_moy={tx_ir_moy:.4f}",
            )
            strategies[code] = calcul_strategie(profil, code, tx_ir_moy,
                                                audit=sous_strat)
            audit.attacher_sous_trace(f"strategie_{code}", sous_strat)
        else:
            strategies[code] = calcul_strategie(profil, code, tx_ir_moy)

    # --- Calcul des deltas vs stratégie A ---
    net_a = strategies["A"]["total_net"]
    for code in strategies:
        strategies[code]["gain_vs_a"] = strategies[code]["total_net"] - net_a

    if audit is not None:
        audit.add("STRAT_ASSIM_COMPARE_AB",
                  "Comparaison delta net par rapport à la stratégie A (agrégat)",
                  net_a, unite="EUR",
                  notes="Stratégie A retenue comme référence par convention v19")
        for code in ("B", "C", "D"):
            delta = strategies[code]["gain_vs_a"]
            audit.add(f"STRAT_ASSIM_DELTA_{code}_VS_A",
                      f"Écart total_net stratégie {code} vs stratégie A",
                      delta, unite="EUR",
                      parent_id="STRAT_ASSIM_COMPARE_AB",
                      hypotheses={"code_strategie": code,
                                  "net_strategie": strategies[code]["total_net"],
                                  "net_reference_A": net_a})

    # --- Sélection de la stratégie retenue (critère factuel) ---
    critere = "max(total_net)"
    recommandee = max(strategies, key=lambda c: strategies[c]["total_net"])

    _log("STRAT_ASSIM_CRITERE_RETENU",
         "Critère de sélection appliqué",
         critere, unite="",
         notes="Sélection mécanique : aucune appréciation prescriptive")
    _log("STRAT_ASSIM_RETENU",
         "Code de la stratégie retenue par le critère ci-dessus",
         recommandee, unite="",
         hypotheses={"critere": critere,
                     "net_retenu": strategies[recommandee]["total_net"]},
         notes="Clé technique 'recommandee' conservée pour rétrocompat Phase A. "
               "Indicateur factuel — voir TERMINOLOGY.md.")

    return {
        "strategies": strategies,
        "recommandee": recommandee,
        "tx_ir_moy": tx_ir_moy,
    }
