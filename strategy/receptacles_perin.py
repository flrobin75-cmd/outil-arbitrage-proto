"""
strategy/receptacles_perin.py — Module métier PERIN (v1.1 SP15).

Module d'allocation d'un flux donné dans le PERIN (Plan d'Épargne
Retraite Individuel), avec projection multi-horizon, économie fiscale
immédiate à l'entrée, capitalisation conventionnelle, et fiscalité
de sortie en capital.

Périmètre SP15 (Q1=b validé)
─────────────────────────────
- Plafond annuel complet (consommé via le legacy `strategy.perin`)
- Économie fiscale immédiate à l'entrée (déductibilité IR)
- Capitalisation conventionnelle annuelle simple (D-R8, 2 %)
- Sortie capital uniquement (sortie rente ajoutée plus tard si validé
  comme rentable produit)
- Fiscalité de sortie capital : IR sur les versements + PFU sur les
  gains
- Aucun rattrapage de plafonds N-1/N-2/N-3 (hors périmètre SP15, cf.
  ARCHITECTURE_RECEPTACLES.md §10.3)
- Aucun abondement entreprise (hors périmètre v1.1, cf. D-R11)

Discipline d'implémentation (résultante des arbitrages SP15)
─────────────────────────────────────────────────────────────
- Q2=c : tous régimes supportés via **providers doctrinaux** dédiés
  (zéro `if profil.regime == ...` dans ce module). Les providers vivent
  au plus près des constantes, soit ici dans une section dédiée
  PROVIDERS DOCTRINAUX, soit déléguées au legacy `strategy.perin`.
- Q3=b : trace structurée = ~10 étapes racines au niveau enveloppe
  + 1 sous-trace par horizon (3 sous-traces × ~6 étapes = 18 étapes)
  → total ~25-30 étapes par appel.
- Q5=a : un seul taux 2 % conventionnel figé (D-R8).
- Q7=b+c : type-aliases consommés (`Euros`, `TauxAnnuel`, `Annees`),
  invariants algébriques validés par `LigneHorizonReceptacle.__post_init__`.
- Q8=a : aucune redéclaration de paramètre réglementaire — tout vient
  soit du legacy `strategy.perin`, soit de `core/profil.py`, soit de
  constantes locales clairement nommées et documentées (taux de
  fiscalité de sortie).
- D-R10 : aucune étape `parent_id != None`.

Référence doctrinale : `ARCHITECTURE_RECEPTACLES.md` §6.2, §6.4, §7.
"""

from dataclasses import dataclass
from typing import Optional

from core.audit import TraceAudit
from core.profil import Profil, TX_PFU_IR

# Consommation du legacy : plafond PERIN (D-R5 indirect : ne pas
# redéclarer un paramètre réglementaire — cohérence Q8=a)
from strategy.perin import calcul_plafond_perin

from strategy.receptacles_orchestrateur import (
    Euros, TauxAnnuel, Annees,
    LigneHorizonReceptacle, ResultatAllocationPerin,
    RENDEMENT_NOMINAL_ANNUEL,
)
from strategy.receptacles_wordings import (
    WORDING_REC_CONVENTION_RENDEMENT,
    WORDING_PERIN_REGLE_PLAFOND,
    WORDING_PERIN_DEDUCTIBILITE_IR_ENTREE,
    WORDING_PERIN_FISCALITE_SORTIE_CAPITAL,
    WORDING_PERIN_DISPONIBILITE_RETRAITE,
)


# ============================================================
# CONSTANTES SPÉCIFIQUES PERIN (sortie capital)
# ============================================================
# Taux de fiscalité de sortie en capital. Référence DGFIP :
#   - Versements volontaires PERIN : à la sortie capital, les versements
#     déduits à l'entrée sont imposés à l'IR (barème) ; les gains sont
#     soumis au PFU (12,8 % IR + 17,2 % PS = 30 %).
#   - Aucun abattement spécifique sur capital sortie PERIN.
# Ces constantes sont **alignées sur `core/profil.py`** :
#   - TX_PFU_IR = 0.128 (déjà défini)
#   - le TX_PFU global (0.314) inclut une contribution exceptionnelle ;
#     pour la sortie PERIN classique on prend IR + PS séparément.
# Convention SP15 : on isole le taux PS pour clarté sémantique.
TX_PS_GAINS_PERIN: TauxAnnuel = 0.172      # 17,2 % prélèvements sociaux sur gains
TX_PFU_GAINS_PERIN: TauxAnnuel = 0.30      # 30 % PFU global sur gains (12,8 % IR + 17,2 % PS)


# ============================================================
# PROVIDERS DOCTRINAUX (Q8=a, G-2)
# ============================================================
# Toute distinction par régime, toute lecture de paramètre
# réglementaire passe par ces fonctions. Aucun branchement direct sur
# `profil.regime` ou sur des constantes hors d'ici.
#
# Si SP16-SP17 (PEE/PERECO) ont des providers similaires, ils suivront
# le même pattern dans leurs propres modules.
def obtenir_plafond_perin(profil: Profil) -> Euros:
    """Provider doctrinal : plafond annuel PERIN du dirigeant pour ce profil.

    Délègue au legacy `strategy.perin.calcul_plafond_perin`, qui
    encapsule la règle CGI art. 154 bis (10 % BNC ou 10 % PASS, plafonné
    à 8 PASS pour la fraction au-delà). Pas de mutualisation conjoint
    en SP15 (hors périmètre Q1=b).

    Args:
        profil: Profil du dirigeant.

    Returns:
        Plafond annuel en euros.
    """
    # Le legacy attend un revenu_pro_n_moins_1. On utilise la
    # rémunération brute du profil comme proxy raisonnable (cohérent
    # avec les autres modules métier existants).
    revenu_proxy = float(getattr(profil, "remuneration_brute", 0.0))
    plafond_obj = calcul_plafond_perin(
        titulaire="Dirigeant",
        revenu_pro_n_moins_1=revenu_proxy,
    )
    return float(plafond_obj.plafond_individuel)


def obtenir_tmi_dirigeant(profil: Profil) -> TauxAnnuel:
    """Provider doctrinal : TMI estimée du dirigeant pour la déductibilité.

    Lecture du profil. Si la TMI n'est pas explicitement renseignée,
    fallback prudent à 0.30 (tranche médiane).

    Note : ce provider est **commun à PERIN et PERECO** (les 2 produits
    bénéficient de la même déductibilité IR à l'entrée). SP17 pourra
    le réutiliser.

    Args:
        profil: Profil du dirigeant.

    Returns:
        Taux marginal d'imposition à appliquer pour le calcul de
        l'économie fiscale immédiate.
    """
    tmi = getattr(profil, "tmi", None)
    if tmi is None:
        return 0.30  # fallback prudent — tranche médiane
    return float(tmi)


def est_eligible_perin(profil: Profil) -> bool:
    """Provider doctrinal : éligibilité PERIN du profil.

    Le PERIN est ouvert à tous les profils v1.1 (TNS, Assimilé,
    Libéral, Salarié). C'est un produit individuel, indépendant du
    statut du dirigeant.

    Args:
        profil: Profil du dirigeant.

    Returns:
        True systématiquement en SP15 (périmètre v1.1).
    """
    return True


# ============================================================
# CALCULS ÉCONOMIQUES (helpers privés)
# ============================================================
def _capitaliser(flux_initial: Euros, taux_annuel: TauxAnnuel,
                 nb_annees: Annees) -> Euros:
    """Capitalisation conventionnelle annuelle simple.

    Formule : flux × (1 + taux)^nb_annees

    Convention SP15 D-R8 : taux fixe 2 %, capitalisation annuelle
    déterministe. Pas d'inflation, pas de frais explicites (le 2 %
    conservateur est censé absorber les frais).

    Args:
        flux_initial: Montant initial en euros.
        taux_annuel: Taux annuel (ex. 0.02 = 2 %).
        nb_annees: Horizon en années pleines.

    Returns:
        Capital projeté à l'horizon.
    """
    if nb_annees < 0:
        return 0.0
    return flux_initial * ((1.0 + taux_annuel) ** nb_annees)


def _calculer_horizon(
    flux_verse: Euros,
    tmi: TauxAnnuel,
    horizon: Annees,
    audit: Optional[TraceAudit] = None,
) -> LigneHorizonReceptacle:
    """Calcule les 8 dimensions économiques pour un horizon donné.

    Logique économique SP15 :
      1. Économie fiscale immédiate : flux_verse × tmi (déductibilité IR
         à l'entrée, plafonnée par le plafond PERIN qui a déjà borné
         flux_verse en amont).
      2. Effort réel : flux_verse - économie fiscale.
      3. Capital projeté : capitalisation à 2 %/an pendant horizon ans.
      4. Fiscalité de sortie (capital) :
         - Sur la fraction « versements » : IR au TMI estimé
           (les versements étaient déductibles → réintégrés à la sortie).
         - Sur la fraction « gains » : PFU 30 % (12,8 % IR + 17,2 % PS).
      5. Valeur nette : capital projeté - fiscalité de sortie.
      6. Coût entreprise : 0,00 € (PERIN est un produit individuel,
         pas employeur).
      7. Disponibilité : retraite (déblocage anticipé limité aux
         cas légaux : invalidité, surendettement, etc.).

    Args:
        flux_verse: Montant effectivement versé (borné par plafond).
        tmi: Taux marginal d'imposition.
        horizon: Années avant sortie.
        audit: TraceAudit pour instrumentation des étapes par horizon.

    Returns:
        LigneHorizonReceptacle pour cet horizon.
    """
    # 1-2. Économie fiscale + effort réel
    economie_fiscale = flux_verse * tmi
    effort_reel = flux_verse - economie_fiscale

    # 3. Capital projeté
    capital_projete = _capitaliser(
        flux_verse, RENDEMENT_NOMINAL_ANNUEL, horizon,
    )

    # 4. Fiscalité de sortie capital
    gains = max(0.0, capital_projete - flux_verse)
    fiscalite_versements = flux_verse * tmi  # IR sur versements à la sortie
    fiscalite_gains = gains * TX_PFU_GAINS_PERIN
    fiscalite_sortie = fiscalite_versements + fiscalite_gains

    # 5. Valeur nette
    valeur_nette = capital_projete - fiscalite_sortie

    # 6-7. Coût entreprise + disponibilité
    cout_entreprise = 0.0  # PERIN individuel
    disponibilite_txt = (
        "Bloqué jusqu'à la retraite (sauf cas légaux : invalidité, "
        "surendettement, acquisition résidence principale)."
    )

    # Instrumentation sous-trace horizon
    if audit is not None:
        audit.add(
            code=f"REC_PERIN_FLUX_VERSE_{horizon}ANS",
            label=f"Flux versé alloué (horizon {horizon} ans)",
            valeur=round(flux_verse, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PERIN_ECO_FISCALE_ENTREE_{horizon}ANS",
            label=f"Économie fiscale immédiate (déduction IR entrée)",
            valeur=round(economie_fiscale, 2), unite="EUR",
            hypotheses={
                "tmi_appliquee": tmi,
                "WORDING_PERIN_DEDUCTIBILITE_IR_ENTREE":
                    WORDING_PERIN_DEDUCTIBILITE_IR_ENTREE,
            },
        )
        audit.add(
            code=f"REC_PERIN_EFFORT_REEL_{horizon}ANS",
            label="Effort réel (flux brut − économie fiscale)",
            valeur=round(effort_reel, 2), unite="EUR",
        )
        audit.add(
            code=f"REC_PERIN_CAPITAL_PROJETE_{horizon}ANS",
            label=f"Capital projeté à {horizon} ans (capitalisation conventionnelle)",
            valeur=round(capital_projete, 2), unite="EUR",
            hypotheses={
                "rendement_annuel": RENDEMENT_NOMINAL_ANNUEL,
                "convention": "Capitalisation annuelle simple, déterministe (D-R8).",
                "WORDING_REC_CONVENTION_RENDEMENT": WORDING_REC_CONVENTION_RENDEMENT,
            },
        )
        audit.add(
            code=f"REC_PERIN_FISC_SORTIE_{horizon}ANS",
            label=f"Fiscalité de sortie (capital) à {horizon} ans",
            valeur=round(fiscalite_sortie, 2), unite="EUR",
            hypotheses={
                "fiscalite_versements_ir_tmi": round(fiscalite_versements, 2),
                "fiscalite_gains_pfu": round(fiscalite_gains, 2),
                "tx_pfu_gains": TX_PFU_GAINS_PERIN,
                "WORDING_PERIN_FISCALITE_SORTIE_CAPITAL":
                    WORDING_PERIN_FISCALITE_SORTIE_CAPITAL,
            },
        )
        audit.add(
            code=f"REC_PERIN_VALEUR_NETTE_{horizon}ANS",
            label=f"Valeur nette à {horizon} ans (capital projeté − fiscalité sortie)",
            valeur=round(valeur_nette, 2), unite="EUR",
        )

    # Note SP15 : arrondi cohérent à 2 décimales. La valeur nette est
    # calculée à partir des champs déjà arrondis (capital projeté,
    # fiscalité sortie) pour éviter une divergence d'un cent qui
    # déclencherait faussement l'invariant `__post_init__` de
    # `LigneHorizonReceptacle`. Pattern : on arrondit les valeurs
    # sources, puis on compose à partir d'elles.
    capital_projete_arr = round(capital_projete, 2)
    fiscalite_sortie_arr = round(fiscalite_sortie, 2)
    effort_reel_arr = round(flux_verse - economie_fiscale, 2)
    # flux_verse et economie_fiscale doivent eux aussi être arrondis
    # à la même précision pour garantir effort_reel == brut - éco.
    flux_verse_arr = round(flux_verse, 2)
    economie_fiscale_arr = round(economie_fiscale, 2)
    # Recompute effort_reel from arrondis pour cohérence stricte
    effort_reel_arr = round(flux_verse_arr - economie_fiscale_arr, 2)
    # Valeur nette = capital projeté arrondi - fiscalité sortie arrondie
    valeur_nette_arr = round(capital_projete_arr - fiscalite_sortie_arr, 2)

    return LigneHorizonReceptacle(
        horizon_annees=horizon,
        flux_entrant_brut=flux_verse_arr,
        economie_fiscale_immediate=economie_fiscale_arr,
        effort_reel=effort_reel_arr,
        capital_projete=capital_projete_arr,
        fiscalite_sortie=fiscalite_sortie_arr,
        valeur_nette=valeur_nette_arr,
        cout_entreprise=cout_entreprise,
        disponibilite=disponibilite_txt,
    )


# ============================================================
# FONCTION PUBLIQUE — SIGNATURE D-R5
# ============================================================
def allocation_perin(
    profil: Profil,
    *,
    flux_disponible: Euros,
    horizons: tuple = (5, 10, 20),
    audit: Optional[TraceAudit] = None,
) -> ResultatAllocationPerin:
    """Alloue un flux disponible dans le PERIN sur N horizons.

    Signature standardisée D-R5. Module métier consommé par
    l'orchestrateur `allocation_receptacles` ; peut être appelé
    autonomement pour analyse PERIN isolée.

    Logique SP15 :
      1. Vérifier éligibilité (provider).
      2. Lire plafond annuel (provider, délègue au legacy).
      3. Borner flux_disponible au plafond annuel.
      4. Lire TMI (provider).
      5. Pour chaque horizon : calculer les 8 dimensions économiques.
      6. Instrumenter trace + retourner dataclass.

    Args:
        profil: Profil du dirigeant.
        flux_disponible: Montant à allouer (input, pas dimensionné, D-R12).
        horizons: Tuple d'années (défaut (5, 10, 20)).
        audit: TraceAudit optionnelle.

    Returns:
        ResultatAllocationPerin contenant 1 LigneHorizonReceptacle par horizon.
    """
    # 1. Éligibilité (toujours True en SP15)
    eligible = est_eligible_perin(profil)

    # 2-3. Plafond + bornage
    plafond_annuel = obtenir_plafond_perin(profil)
    flux_verse = min(float(flux_disponible), plafond_annuel)
    flux_excedent = max(0.0, float(flux_disponible) - plafond_annuel)

    # 4. TMI
    tmi = obtenir_tmi_dirigeant(profil)

    # Instrumentation racine de la sous-trace enveloppe
    if audit is not None:
        audit.add(
            code="REC_PERIN_ELIGIBILITE",
            label="Éligibilité PERIN du profil",
            valeur=1 if eligible else 0, unite="bool",
            hypotheses={
                "regle": "PERIN ouvert à tous les profils v1.1 (produit individuel).",
                "WORDING_PERIN_DISPONIBILITE_RETRAITE":
                    WORDING_PERIN_DISPONIBILITE_RETRAITE,
            },
        )
        audit.add(
            code="REC_PERIN_PLAFOND_ANNUEL",
            label="Plafond annuel PERIN applicable",
            valeur=round(plafond_annuel, 2), unite="EUR",
            doctrine_refs=("PASS_2026",),
            hypotheses={
                "regle_resume": (
                    "Plafond = max(10 % revenu pro N-1 ; 10 % PASS), "
                    "plafonné à 8 PASS. Référence CGI art. 154 bis."
                ),
                "PASS_2026_consomme": True,
                "WORDING_PERIN_REGLE_PLAFOND": WORDING_PERIN_REGLE_PLAFOND,
            },
        )
        audit.add(
            code="REC_PERIN_FLUX_VERSE_EFFECTIF",
            label="Flux effectivement versé (borné par plafond)",
            valeur=round(flux_verse, 2), unite="EUR",
            hypotheses={
                "flux_disponible_input": round(float(flux_disponible), 2),
                "plafond_annuel": round(plafond_annuel, 2),
                "regle_bornage": "min(flux_disponible, plafond_annuel)",
            },
        )
        if flux_excedent > 0.01:
            audit.add(
                code="REC_PERIN_FLUX_EXCEDENT",
                label="Fraction du flux disponible non-versée (au-delà du plafond)",
                valeur=round(flux_excedent, 2), unite="EUR",
                hypotheses={
                    "interpretation": (
                        "Cette fraction peut être allouée à d'autres "
                        "enveloppes (PEE, PERECO) selon contraintes "
                        "propres à chaque enveloppe. Décision cabinet."
                    ),
                },
            )
        audit.add(
            code="REC_PERIN_TMI_APPLIQUEE",
            label="TMI appliquée pour déductibilité IR",
            valeur=tmi, unite="ratio",
            hypotheses={
                "source": "Profil dirigeant (fallback 30 % si non renseignée)",
            },
        )

    # 5. Calcul par horizon (sous-traces dédiées)
    lignes: list = []
    for h in horizons:
        if audit is not None:
            sub_horizon = TraceAudit(
                regime=f"PERIN — Horizon {h} ans",
                profil_resume=(
                    f"Versement {flux_verse:.0f} €, TMI {tmi*100:.1f}%, "
                    f"capitalisation {RENDEMENT_NOMINAL_ANNUEL*100:.0f}%/an"
                ),
            )
            ligne = _calculer_horizon(flux_verse, tmi, h, audit=sub_horizon)
            audit.attacher_sous_trace(f"horizon_{h}ans", sub_horizon)
        else:
            ligne = _calculer_horizon(flux_verse, tmi, h, audit=None)
        lignes.append(ligne)

    # 6. Dataclass de résultat
    return ResultatAllocationPerin(
        enveloppe="PERIN",
        accessible=eligible,
        motif_inaccessibilite="" if eligible else "Non éligible (SP15: cas non rencontré)",
        lignes_par_horizon=lignes,
    )


# ============================================================
# SURFACE PUBLIQUE
# ============================================================
__all__ = [
    # Constantes SP15
    "TX_PS_GAINS_PERIN",
    "TX_PFU_GAINS_PERIN",
    # Providers doctrinaux
    "obtenir_plafond_perin",
    "obtenir_tmi_dirigeant",
    "est_eligible_perin",
    # Fonction principale
    "allocation_perin",
]
