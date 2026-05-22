"""
Moteur Comparateur Option 2 - Architecture de réceptacle.

Extensions vs v19 :
- Ajout du PERO (article 83 nouvelle formule, PACTE 2019)
- Architecture de réceptacle (PEE / PERECO / PERO / PERIN)
- Routage explicite des flux vers les réceptacles
- Validation des plafonds croisés (lecture URSSAF prudente)
- Vue consolidée par réceptacle

Test 1 (PEE seul, sans PERO, routage par défaut) doit donner parité v19 stricte.

Tous les paramètres réglementaires sont définis dans PARAM_REGLEMENTAIRES.
Date de dernière mise à jour réglementaire : 01/01/2026.
"""

from dataclasses import dataclass, field
from typing import Optional
from core.profil import (
    Profil, PASS_2026, TX_PATRONAL, TX_SALARIAL, TX_CSG_CRDS_ACT, ASSIETTE_CSG_SAL,
    TX_PFU, TX_IS_REDUIT, TX_IS_NORMAL,
    IR_PLAFOND_T1, IR_PLAFOND_T2, IR_PLAFOND_T3, IR_PLAFOND_T4,
    IR_TAUX_T2, IR_TAUX_T3, IR_TAUX_T4, IR_TAUX_T5,
)


# ============================================================
# PARAMÈTRES RÉGLEMENTAIRES — Onglet PARAM_REGLEMENTAIRES
# ============================================================
DATE_MAJ_REGLEMENTAIRE = "01/01/2026"

# Coefficients de risque (lecture v19, lignes L107-L121 onglet 4. Paramètres)
RISK_SALAIRE = 1.00
RISK_DIVIDENDES = 0.95
RISK_PARTICIPATION = 1.00
RISK_INTERESSEMENT = 1.00
RISK_ABO_PEE = 1.00
RISK_ABO_PER = 1.00       # = abondement PERECO (cohérence terminologique v19)
RISK_PERIN = 0.95
RISK_PERO = 0.90          # NOUVEAU - validation utilisateur
RISK_AVANTAGES = 0.90
RISK_TR = 1.00
RISK_CESU = 1.00
RISK_CADO = 0.85
RISK_MUTUELLE = 1.00
RISK_IK = 0.85
RISK_CASHBACK = 0.85

# Plafonds dispositifs (lignes L46-L54 onglet 4. Paramètres)
PLAF_PARTICIPATION_INDIV = 36_045.00    # 75 % PASS
PLAF_INTERESSEMENT_INDIV = 36_045.00    # 75 % PASS
PLAF_ABO_PEE = 3_844.80                 # 8 % PASS
PLAF_ABO_PERECO = 7_689.60              # 16 % PASS
PLAF_CESU = 2_540.00                    # exonération annuelle
PLAF_CUMUL_ABONDEMENTS = 7_689.60       # 16 % PASS - lecture consolidée prudente
PLAF_PERIN_MAX = 8 * PASS_2026          # 8 PASS

# Forfaits sociaux (lignes L36-L42)
FS_PARTICIPATION = {
    "Sans salarié": 0.00, "1-10 salariés": 0.00, "11-49 salariés": 0.00,
    "50-249 salariés": 0.20, "≥ 250 salariés": 0.20,
}
FS_INTERESSEMENT = {
    "Sans salarié": 0.00, "1-10 salariés": 0.00, "11-49 salariés": 0.00,
    "50-249 salariés": 0.00, "≥ 250 salariés": 0.20,
}
FS_ABO_PEE = {
    "Sans salarié": 0.00, "1-10 salariés": 0.00, "11-49 salariés": 0.00,
    "50-249 salariés": 0.20, "≥ 250 salariés": 0.20,
}
FS_ABO_PERECO = 0.00      # PACTE - exonéré universellement jusqu'à fin 2027
FS_PERO = 0.08            # PACTE PER obligatoire - paramètre expert

# Constantes UX (heuristiques v19)
RATIO_NET_IMPOSABLE = {
    "Assimilé salarié": 0.55,
    "TNS": 0.70,
    "TNS (libéral)": 0.70,
    "Salarié": 0.55,
}


# ============================================================
# DATACLASSES
# ============================================================
@dataclass
class FluxEpargne:
    """Configuration d'un flux d'épargne et son routage."""
    actif: bool = False
    montant: float = 0.0
    receptacle: str = "PEE"   # Réceptacle de destination

@dataclass
class ConfigComparateur:
    """Configuration complète du Comparateur Option 2."""
    # Réceptacles activés
    pee_actif: bool = True
    pereco_actif: bool = True
    pero_actif: bool = False
    perin_actif: bool = True

    # Éligibilité PERO du dirigeant
    dirigeant_eligible_pero: bool = False

    # Flux d'épargne salariale
    participation: FluxEpargne = field(default_factory=lambda: FluxEpargne(True, 1500, "PEE"))
    interessement: FluxEpargne = field(default_factory=lambda: FluxEpargne(True, 2500, "PEE"))
    abondement_pee: FluxEpargne = field(default_factory=lambda: FluxEpargne(True, 1500, "PEE"))
    abondement_pereco: FluxEpargne = field(default_factory=lambda: FluxEpargne(True, 3000, "PERECO"))
    versement_perin: FluxEpargne = field(default_factory=lambda: FluxEpargne(True, 5000, "PERIN"))

    # PERO (mode de saisie asymétrique)
    pero_mode_saisie: str = "pourcentage"   # "pourcentage" ou "euros"
    pero_taux: float = 0.03                  # 3 % par défaut
    pero_montant: float = 0.0                # Calculé auto si mode pourcentage

    # Dispositifs autonomes (toggles + montants)
    avantages_actif: bool = True
    avantages_montant: float = 3600
    tr_actif: bool = True
    tr_montant: float = 1742
    cesu_actif: bool = True
    cesu_montant: float = 2000
    cado_actif: bool = True
    cado_montant: float = 500
    mutuelle_actif: bool = True
    mutuelle_montant: float = 1200
    ik_actif: bool = False
    ik_montant: float = 0
    cashback_actif: bool = False
    cashback_montant: float = 360


@dataclass
class LigneDispositif:
    """Résultat de calcul pour un dispositif (11 colonnes v19)."""
    nom: str
    active: str               # "Réf." / "Variable" / "Oui" / "Non"
    montant_input: float      # D
    cout_societe: float       # E
    cout_beneficiaire: float  # F
    cotis_ps: float           # G
    net_imposable: float      # H
    ir_estime: float          # I
    net_apres_ir: float       # J
    ratio_net_cout: float     # K
    coef_risque: float        # L
    score_ajuste: float       # M
    top3_rang: Optional[int] = None   # 1, 2, 3 ou None
    # ──────────── Phase B.2 Étape 5 — réceptacles différenciés ────────────
    # Champs additifs : valeur par défaut True/vide pour préserver
    # rétrocompat totale (les 64 tests cohérence Comparateur sont inchangés).
    # Renseignés par calcul_comparateur() selon profil.regime_social.
    accessible: bool = True
    motif_inaccessibilite: str = ""


@dataclass
class VueReceptacle:
    """Vue consolidée d'un réceptacle (PEE, PERECO, PERO, PERIN)."""
    nom: str                    # "PEE", "PERECO", "PERO", "PERIN"
    actif: bool
    flux_entrants: list         # Liste de tuples (nom_flux, montant)
    montant_total: float
    plafond_legal: float
    plafond_label: str          # Label descriptif du plafond
    taux_utilisation: float     # % d'utilisation du plafond
    statut: str                 # "✓" ou "⚠"
    message: str                # Vide si OK, message d'alerte sinon


@dataclass
class AlertePlafond:
    """Alerte sur un plafond dépassé ou un point de vigilance."""
    severite: str               # "warning" / "error" / "info"
    titre: str
    message: str


@dataclass
class ResultatComparateur:
    """Résultat complet du Comparateur Option 2."""
    # Section A - Paramètres dérivés
    revenu_imposable_par_part: float
    tmi_estimee: float
    forfait_social_participation: float
    forfait_social_interessement: float
    forfait_social_abondement_pee: float

    # Section B - Matrice des dispositifs
    lignes: list           # Liste de LigneDispositif

    # Section C - Vue consolidée par réceptacle
    receptacles: list      # Liste de VueReceptacle

    # Section D - Alertes
    alertes: list          # Liste de AlertePlafond

    # Métadonnées
    date_maj_reglementaire: str = DATE_MAJ_REGLEMENTAIRE


# ============================================================
# CALCULS AUXILIAIRES
# ============================================================
def estimer_revenu_imposable_par_part(profil: Profil) -> float:
    """Heuristique v19 : enveloppe × ratio / parts + autres_rev/parts."""
    ratio = RATIO_NET_IMPOSABLE.get(profil.regime_social, 0.55)
    return (profil.enveloppe * ratio + profil.autres_revenus) / profil.parts


def estimer_tmi(revenu_par_part: float) -> float:
    """TMI selon barème pour un revenu par part."""
    if revenu_par_part <= IR_PLAFOND_T1: return 0.0
    if revenu_par_part <= IR_PLAFOND_T2: return IR_TAUX_T2
    if revenu_par_part <= IR_PLAFOND_T3: return IR_TAUX_T3
    if revenu_par_part <= IR_PLAFOND_T4: return IR_TAUX_T4
    return IR_TAUX_T5


def calcul_montant_pero(config: ConfigComparateur, remuneration_brute: float) -> float:
    """Calcule le montant PERO selon le mode de saisie asymétrique."""
    if not (config.pero_actif and config.dirigeant_eligible_pero):
        return 0.0
    if config.pero_mode_saisie == "pourcentage":
        return config.pero_taux * remuneration_brute
    else:
        return config.pero_montant


# ============================================================
# CALCUL D'UNE LIGNE DE DISPOSITIF
# ============================================================
def _ligne_salaire(profil: Profil, tmi: float) -> LigneDispositif:
    """Ligne 14 v19 - Salaire classique (référence forcée)."""
    D = profil.enveloppe / (1 + TX_PATRONAL)
    E = profil.enveloppe
    F = 0.0
    G = D * TX_SALARIAL + D * ASSIETTE_CSG_SAL * TX_CSG_CRDS_ACT
    H = D - D * TX_SALARIAL - D * ASSIETTE_CSG_SAL * 0.068
    I = H * tmi
    J = D - G - I
    K = J / (E + F) if (E + F) > 0 else 0.0
    L = RISK_SALAIRE
    M = K * L
    return LigneDispositif(
        nom="Salaire classique (référence)", active="Réf.",
        montant_input=D, cout_societe=E, cout_beneficiaire=F, cotis_ps=G,
        net_imposable=H, ir_estime=I, net_apres_ir=J,
        ratio_net_cout=K, coef_risque=L, score_ajuste=M,
    )


def _ligne_dividendes(montant: float = 10000) -> LigneDispositif:
    """Ligne 15 v19 - Dividendes PFU 30 % (référence variable)."""
    D = montant
    E = D / (1 - TX_IS_NORMAL)
    F = 0.0
    G = D * TX_PFU
    H = 0.0
    I = 0.0
    J = D - G
    K = J / E if E > 0 else 0.0
    L = RISK_DIVIDENDES
    M = K * L
    return LigneDispositif(
        nom="Dividendes - PFU 30 %", active="Variable",
        montant_input=D, cout_societe=E, cout_beneficiaire=F, cotis_ps=G,
        net_imposable=H, ir_estime=I, net_apres_ir=J,
        ratio_net_cout=K, coef_risque=L, score_ajuste=M,
    )


def _ligne_flux_epargne(nom: str, flux: FluxEpargne, forfait_social: float,
                       coef_risque: float, profil: Profil) -> LigneDispositif:
    """Ligne générique pour participation, intéressement, abondements."""
    active = "Oui" if flux.actif else "Non"
    D = flux.montant if flux.actif else 0.0
    E = D * (1 + forfait_social) if flux.actif else 0.0
    F = 0.0
    G = D * TX_CSG_CRDS_ACT if flux.actif else 0.0
    H = 0.0
    I = 0.0
    J = (D - G) if flux.actif else 0.0
    K = J / E if E > 0 else 0.0
    L = coef_risque
    M = K * L
    return LigneDispositif(
        nom=nom, active=active,
        montant_input=D, cout_societe=E, cout_beneficiaire=F, cotis_ps=G,
        net_imposable=H, ir_estime=I, net_apres_ir=J,
        ratio_net_cout=K, coef_risque=L, score_ajuste=M,
    )


def _ligne_perin(flux: FluxEpargne, tmi: float) -> LigneDispositif:
    """Ligne 20 v19 - PER individuel (calcul spécial)."""
    active = "Oui" if flux.actif else "Non"
    D = flux.montant if flux.actif else 0.0
    E = 0.0
    F = D * (1 - tmi) if flux.actif else 0.0
    G = 0.0
    H = -D if flux.actif else 0.0
    I = -D * tmi if flux.actif else 0.0
    J = (D - F) if flux.actif else 0.0
    K = J / max(F, 1) if flux.actif else 0.0
    L = RISK_PERIN
    M = K * L
    return LigneDispositif(
        nom="PER individuel (versement déductible)", active=active,
        montant_input=D, cout_societe=E, cout_beneficiaire=F, cotis_ps=G,
        net_imposable=H, ir_estime=I, net_apres_ir=J,
        ratio_net_cout=K, coef_risque=L, score_ajuste=M,
    )


def _ligne_pero(montant_pero: float, est_actif_complet: bool) -> LigneDispositif:
    """Nouvelle ligne PERO (extension Option 2 hors v19)."""
    active = "Oui" if est_actif_complet else "Non"
    D = montant_pero if est_actif_complet else 0.0
    E = D * (1 + FS_PERO) if est_actif_complet else 0.0
    F = 0.0
    G = D * TX_CSG_CRDS_ACT if est_actif_complet else 0.0
    H = 0.0
    I = 0.0
    J = (D - G) if est_actif_complet else 0.0
    K = J / E if E > 0 else 0.0
    L = RISK_PERO
    M = K * L
    return LigneDispositif(
        nom="Cotisation employeur PERO (art. 83 nouvelle formule)", active=active,
        montant_input=D, cout_societe=E, cout_beneficiaire=F, cotis_ps=G,
        net_imposable=H, ir_estime=I, net_apres_ir=J,
        ratio_net_cout=K, coef_risque=L, score_ajuste=M,
    )


def _ligne_avantages_nature(montant: float, actif: bool, tmi: float) -> LigneDispositif:
    """Ligne 21 v19 - Avantages en nature."""
    active = "Oui" if actif else "Non"
    D = montant if actif else 0.0
    E = D * (1 + TX_PATRONAL) if actif else 0.0
    F = 0.0
    G = D * (TX_SALARIAL + ASSIETTE_CSG_SAL * 0.068) if actif else 0.0
    H = D * (1 - TX_SALARIAL - ASSIETTE_CSG_SAL * 0.068) if actif else 0.0
    I = H * tmi if actif else 0.0
    J = (D - G - I) if actif else 0.0
    K = J / E if E > 0 else 0.0
    L = RISK_AVANTAGES
    M = K * L
    return LigneDispositif(
        nom="Avantages en nature (véhicule, NTIC...)", active=active,
        montant_input=D, cout_societe=E, cout_beneficiaire=F, cotis_ps=G,
        net_imposable=H, ir_estime=I, net_apres_ir=J,
        ratio_net_cout=K, coef_risque=L, score_ajuste=M,
    )


def _ligne_exo_pure(nom: str, montant: float, actif: bool,
                    coef_risque: float, csg_applicable: bool = False) -> LigneDispositif:
    """Lignes 22-26 v19 - Dispositifs largement exonérés (TR, CESU, cado, mutuelle, IK)."""
    active = "Oui" if actif else "Non"
    D = montant if actif else 0.0
    E = D if actif else 0.0
    F = 0.0
    G = D * TX_CSG_CRDS_ACT if (actif and csg_applicable) else 0.0
    H = 0.0
    I = 0.0
    J = (D - G) if actif else 0.0
    K = J / E if E > 0 else 0.0
    L = coef_risque
    M = K * L
    return LigneDispositif(
        nom=nom, active=active,
        montant_input=D, cout_societe=E, cout_beneficiaire=F, cotis_ps=G,
        net_imposable=H, ir_estime=I, net_apres_ir=J,
        ratio_net_cout=K, coef_risque=L, score_ajuste=M,
    )


def _ligne_cashback(montant: float, actif: bool) -> LigneDispositif:
    """Ligne 27 v19 - Cashback (cas spécial, ratio sécurisé)."""
    active = "Oui" if actif else "Non"
    D = montant if actif else 0.0
    E = D if actif else 0.0
    F = 0.0
    G = 0.0
    H = 0.0
    I = 0.0
    J = D if actif else 0.0
    K = J / max(E, 1) if actif else 0.0
    L = RISK_CASHBACK
    M = K * L
    return LigneDispositif(
        nom="💸 Cashback (programme partenaire)", active=active,
        montant_input=D, cout_societe=E, cout_beneficiaire=F, cotis_ps=G,
        net_imposable=H, ir_estime=I, net_apres_ir=J,
        ratio_net_cout=K, coef_risque=L, score_ajuste=M,
    )


# ============================================================
# PODIUM TOP 3 (logique v19 reproduite fidèlement)
# ============================================================
def appliquer_top3(lignes: list, lignes_eligibles_idx: list) -> None:
    """
    Reproduit la formule v19 SUMPRODUCT/RANK avec gestion des égalités.
    Seules les lignes activées (toggle "Oui") participent au podium.
    Pour les égalités : priorité à la ligne au-dessus dans le tableau.
    """
    # Construire liste des (idx, score) pour les lignes éligibles activées
    candidats = []
    for idx in lignes_eligibles_idx:
        if lignes[idx].active == "Oui":
            candidats.append((idx, lignes[idx].score_ajuste))

    if not candidats:
        return

    # Trier par score décroissant, puis par index croissant (priorité haut du tableau)
    candidats.sort(key=lambda x: (-x[1], x[0]))

    # Attribuer rang 1, 2, 3
    for rang, (idx, _) in enumerate(candidats[:3], start=1):
        lignes[idx].top3_rang = rang


# ============================================================
# VUE CONSOLIDÉE PAR RÉCEPTACLE
# ============================================================
def construire_vues_receptacles(config: ConfigComparateur,
                                 montant_pero: float) -> list:
    """Construit la liste des vues consolidées par réceptacle."""
    vues = []

    # PEE
    flux_pee = []
    if config.participation.actif and config.participation.receptacle == "PEE":
        flux_pee.append(("Participation", config.participation.montant))
    if config.interessement.actif and config.interessement.receptacle == "PEE":
        flux_pee.append(("Intéressement", config.interessement.montant))
    if config.abondement_pee.actif:
        flux_pee.append(("Abondement PEE", config.abondement_pee.montant))
    total_pee = sum(m for _, m in flux_pee)
    vues.append(VueReceptacle(
        nom="PEE", actif=config.pee_actif, flux_entrants=flux_pee,
        montant_total=total_pee,
        plafond_legal=PLAF_ABO_PEE,
        plafond_label="8 % PASS (abondement employeur uniquement)",
        taux_utilisation=(config.abondement_pee.montant / PLAF_ABO_PEE
                          if PLAF_ABO_PEE > 0 else 0.0),
        statut="✓" if config.abondement_pee.montant <= PLAF_ABO_PEE else "⚠",
        message=("" if config.abondement_pee.montant <= PLAF_ABO_PEE
                 else f"Abondement PEE {config.abondement_pee.montant:,.2f} € dépasse "
                      f"le plafond légal {PLAF_ABO_PEE:,.2f} €")
    ))

    # PERECO
    flux_pereco = []
    if config.participation.actif and config.participation.receptacle == "PERECO":
        flux_pereco.append(("Participation", config.participation.montant))
    if config.interessement.actif and config.interessement.receptacle == "PERECO":
        flux_pereco.append(("Intéressement", config.interessement.montant))
    if config.abondement_pereco.actif:
        flux_pereco.append(("Abondement PERECO", config.abondement_pereco.montant))
    total_pereco = sum(m for _, m in flux_pereco)
    vues.append(VueReceptacle(
        nom="PERECO", actif=config.pereco_actif, flux_entrants=flux_pereco,
        montant_total=total_pereco,
        plafond_legal=PLAF_ABO_PERECO,
        plafond_label="16 % PASS (abondement employeur)",
        taux_utilisation=(config.abondement_pereco.montant / PLAF_ABO_PERECO
                          if PLAF_ABO_PERECO > 0 else 0.0),
        statut="✓" if config.abondement_pereco.montant <= PLAF_ABO_PERECO else "⚠",
        message=("" if config.abondement_pereco.montant <= PLAF_ABO_PERECO
                 else f"Abondement PERECO {config.abondement_pereco.montant:,.2f} € "
                      f"dépasse plafond {PLAF_ABO_PERECO:,.2f} €")
    ))

    # PERO
    flux_pero = []
    pero_eligible = config.pero_actif and config.dirigeant_eligible_pero
    if pero_eligible:
        flux_pero.append(("Cotisation employeur PERO", montant_pero))
    total_pero = montant_pero if pero_eligible else 0.0
    vues.append(VueReceptacle(
        nom="PERO", actif=pero_eligible, flux_entrants=flux_pero,
        montant_total=total_pero,
        plafond_legal=PLAF_CUMUL_ABONDEMENTS,
        plafond_label="16 % PASS (cumul abondements - lecture consolidée)",
        taux_utilisation=(total_pero / PLAF_CUMUL_ABONDEMENTS
                          if PLAF_CUMUL_ABONDEMENTS > 0 else 0.0),
        statut="✓" if total_pero <= PLAF_CUMUL_ABONDEMENTS else "⚠",
        message=("" if total_pero <= PLAF_CUMUL_ABONDEMENTS
                 else f"Cotisation PERO {total_pero:,.2f} € dépasse plafond cumulé "
                      f"{PLAF_CUMUL_ABONDEMENTS:,.2f} €")
    ))

    # PERIN
    flux_perin = []
    if config.versement_perin.actif and config.versement_perin.receptacle == "PERIN":
        flux_perin.append(("Versement individuel", config.versement_perin.montant))
    total_perin = sum(m for _, m in flux_perin)
    vues.append(VueReceptacle(
        nom="PERIN", actif=config.perin_actif, flux_entrants=flux_perin,
        montant_total=total_perin,
        plafond_legal=PLAF_PERIN_MAX,
        plafond_label="10 % rev. pro. N-1 (max 8 PASS, mutualisable conjoints)",
        taux_utilisation=total_perin / PLAF_PERIN_MAX if PLAF_PERIN_MAX > 0 else 0.0,
        statut="✓" if total_perin <= PLAF_PERIN_MAX else "⚠",
        message=("" if total_perin <= PLAF_PERIN_MAX
                 else f"Versement PERIN {total_perin:,.2f} € dépasse 8 PASS")
    ))

    return vues


# ============================================================
# ALERTES PLAFONDS CROISÉS
# ============================================================
def construire_alertes(config: ConfigComparateur, profil: Profil,
                       montant_pero: float) -> list:
    """Construit la liste des alertes de plafonds croisés et points de vigilance."""
    alertes = []

    # Alerte 1 - Plafond cumulé abondements (lecture URSSAF prudente)
    cumul = (config.abondement_pee.montant
             + config.abondement_pereco.montant
             + (montant_pero if config.pero_actif and config.dirigeant_eligible_pero else 0))
    if cumul > PLAF_CUMUL_ABONDEMENTS:
        alertes.append(AlertePlafond(
            severite="error",
            titre="Cumul des abondements PER dépassé",
            message=f"Total {cumul:,.2f} € (PEE {config.abondement_pee.montant:,.2f} € "
                    f"+ PERECO {config.abondement_pereco.montant:,.2f} € "
                    f"+ PERO {montant_pero:,.2f} €) > plafond consolidé "
                    f"{PLAF_CUMUL_ABONDEMENTS:,.2f} €. Lecture consolidée prudente "
                    f"selon URSSAF 2024."
        ))

    # Alerte 2 - PERO activé sans éligibilité
    if config.pero_actif and not config.dirigeant_eligible_pero:
        alertes.append(AlertePlafond(
            severite="info",
            titre="PERO neutralisé",
            message="Le PERO est activé mais le dirigeant n'est pas marqué comme "
                    "éligible à la catégorie objective. Aucun montant n'est appliqué."
        ))

    # Alerte 3 - PERO activé sur régime non éligible (TNS)
    if config.pero_actif and "TNS" in profil.regime_social:
        alertes.append(AlertePlafond(
            severite="error",
            titre="PERO incompatible avec le régime TNS",
            message="Le PERO (article 83) est réservé aux salariés et assimilés "
                    f"salariés. Régime actuel : {profil.regime_social}. "
                    "Désactivez le PERO ou modifiez le régime."
        ))

    # Alerte 4 - Plafonds individuels
    if config.participation.actif and config.participation.montant > PLAF_PARTICIPATION_INDIV:
        alertes.append(AlertePlafond(
            severite="warning",
            titre="Plafond individuel participation dépassé",
            message=f"Participation {config.participation.montant:,.2f} € > "
                    f"{PLAF_PARTICIPATION_INDIV:,.2f} € (75 % PASS)."
        ))
    if config.interessement.actif and config.interessement.montant > PLAF_INTERESSEMENT_INDIV:
        alertes.append(AlertePlafond(
            severite="warning",
            titre="Plafond individuel intéressement dépassé",
            message=f"Intéressement {config.interessement.montant:,.2f} € > "
                    f"{PLAF_INTERESSEMENT_INDIV:,.2f} € (75 % PASS)."
        ))

    # Alerte 5 - CESU plafond
    if config.cesu_actif and config.cesu_montant > PLAF_CESU:
        alertes.append(AlertePlafond(
            severite="warning",
            titre="Plafond CESU dépassé",
            message=f"CESU {config.cesu_montant:,.2f} € > exonération annuelle "
                    f"{PLAF_CESU:,.2f} €."
        ))

    # Info systématique - Lecture consolidée
    alertes.append(AlertePlafond(
        severite="info",
        titre="Lecture consolidée prudente",
        message="Le moteur applique une lecture consolidée prudente des plafonds "
                "sociaux afin de sécuriser les simulations. Cf. onglet "
                "Paramètres réglementaires pour le détail."
    ))

    return alertes


# ============================================================
# FONCTION PRINCIPALE
# ============================================================
def calcul_comparateur(profil: Profil, config: ConfigComparateur,
                       remuneration_brute_pour_pero: Optional[float] = None) -> ResultatComparateur:
    """
    Calcule la matrice complète du Comparateur Option 2.

    Args:
        profil: Profil client
        config: Configuration complète (réceptacles, flux, dispositifs)
        remuneration_brute_pour_pero: Base de calcul pour le PERO (stratégie D :
            salaire effectivement versé, pas enveloppe). Si None, on prend
            enveloppe / (1 + TX_PATRONAL) comme proxy (cas stratégie A = salaire pur).
    """
    # === Section A - Paramètres dérivés ===
    revenu_par_part = estimer_revenu_imposable_par_part(profil)
    tmi = estimer_tmi(revenu_par_part)
    fs_part = FS_PARTICIPATION[profil.effectif]
    fs_int = FS_INTERESSEMENT[profil.effectif]
    fs_abo_pee = FS_ABO_PEE[profil.effectif]

    # === PERO - calcul du montant selon mode de saisie ===
    if remuneration_brute_pour_pero is None:
        remuneration_brute_pour_pero = profil.enveloppe / (1 + TX_PATRONAL)
    montant_pero = calcul_montant_pero(config, remuneration_brute_pour_pero)

    # === Section B - Matrice des dispositifs ===
    lignes = []
    lignes.append(_ligne_salaire(profil, tmi))                       # 0
    lignes.append(_ligne_dividendes())                                # 1
    # Participation - forfait social selon réceptacle
    fs_part_effectif = (FS_ABO_PERECO if config.participation.receptacle == "PERECO"
                       else fs_part)
    lignes.append(_ligne_flux_epargne("Participation (placée 5 ans en PEE)",
                                      config.participation, fs_part_effectif,
                                      RISK_PARTICIPATION, profil))    # 2
    # Intéressement - forfait social selon réceptacle
    fs_int_effectif = (FS_ABO_PERECO if config.interessement.receptacle == "PERECO"
                      else fs_int)
    lignes.append(_ligne_flux_epargne("Intéressement (placé 5 ans en PEE)",
                                      config.interessement, fs_int_effectif,
                                      RISK_INTERESSEMENT, profil))    # 3
    # Abondement PEE - forfait social effectif
    lignes.append(_ligne_flux_epargne("Abondement employeur PEE",
                                      config.abondement_pee, fs_abo_pee,
                                      RISK_ABO_PEE, profil))          # 4
    # Abondement PERECO - 0 % par défaut (PACTE)
    lignes.append(_ligne_flux_epargne("Abondement employeur PER collectif",
                                      config.abondement_pereco, FS_ABO_PERECO,
                                      RISK_ABO_PER, profil))          # 5
    # PERIN
    lignes.append(_ligne_perin(config.versement_perin, tmi))          # 6
    # Avantages en nature
    lignes.append(_ligne_avantages_nature(config.avantages_montant,
                                          config.avantages_actif, tmi))  # 7
    # TR
    lignes.append(_ligne_exo_pure("Tickets restaurant (part employeur exonérée)",
                                  config.tr_montant, config.tr_actif, RISK_TR))   # 8
    # CESU
    lignes.append(_ligne_exo_pure("CESU préfinancé (exonéré ≤ 2 540 €)",
                                  config.cesu_montant, config.cesu_actif,
                                  RISK_CESU))                          # 9
    # Chèques cadeaux
    lignes.append(_ligne_exo_pure("Chèques cadeaux & vacances (tolérance URSSAF)",
                                  config.cado_montant, config.cado_actif,
                                  RISK_CADO))                          # 10
    # Mutuelle
    lignes.append(_ligne_exo_pure("Mutuelle / prévoyance employeur",
                                  config.mutuelle_montant,
                                  config.mutuelle_actif, RISK_MUTUELLE,
                                  csg_applicable=True))                # 11
    # IK
    lignes.append(_ligne_exo_pure("Indemnités kilométriques (barème fiscal)",
                                  config.ik_montant, config.ik_actif, RISK_IK))  # 12
    # Cashback
    lignes.append(_ligne_cashback(config.cashback_montant, config.cashback_actif))  # 13
    # PERO - ligne nouvelle (Option 2)
    pero_actif_complet = (config.pero_actif and config.dirigeant_eligible_pero
                          and "TNS" not in profil.regime_social)
    lignes.append(_ligne_pero(montant_pero, pero_actif_complet))      # 14

    # === Section B.1 - Phase B.2 Étape 5 : différenciation par régime ===
    # Mapping ligne → réceptacle de référence pour la matrice §5.
    # Les lignes sans réceptacle (salaire, dividendes, périphériques)
    # restent accessibles à tous les régimes.
    from strategy.receptacles import est_accessible, motif_inaccessibilite
    _MAPPING_RECEPTACLE = {
        2: "Participation",
        3: "Intéressement",
        4: "PEE",
        5: "PERECO",
        6: "PERIN",
        14: "PERO",
    }
    for idx, ligne in enumerate(lignes):
        rec = _MAPPING_RECEPTACLE.get(idx)
        if rec is None:
            continue   # Ligne hors matrice (salaire, dividendes, avantages, etc.)
        if not est_accessible(rec, profil):
            ligne.accessible = False
            ligne.motif_inaccessibilite = motif_inaccessibilite(rec, profil) or ""

    # === Application du podium top 3 ===
    # Lignes éligibles au podium : tous les dispositifs conditionnels (idx 2 à 14)
    # Salaire (0) et Dividendes (1) sont exclus
    # Les lignes inaccessibles sont également exclues du top 3 (cohérence régime).
    lignes_eligibles = [i for i in range(2, 15)
                        if lignes[i].accessible]
    appliquer_top3(lignes, lignes_eligibles)

    # === Section C - Vue consolidée par réceptacle ===
    receptacles = construire_vues_receptacles(config, montant_pero)

    # === Section D - Alertes ===
    alertes = construire_alertes(config, profil, montant_pero)

    return ResultatComparateur(
        revenu_imposable_par_part=revenu_par_part,
        tmi_estimee=tmi,
        forfait_social_participation=fs_part,
        forfait_social_interessement=fs_int,
        forfait_social_abondement_pee=fs_abo_pee,
        lignes=lignes,
        receptacles=receptacles,
        alertes=alertes,
    )
