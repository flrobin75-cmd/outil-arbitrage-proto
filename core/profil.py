"""
Core Engine — Profil client et constantes fiscales/sociales.

Référentiel fiscal & social applicable au 01/01/2026 (régime PACTE).
Source : onglet "4. Paramètres" du classeur v19, mis à jour 2026.

Module pivot : aucun import dépendant. Tout autre module peut consommer celui-ci.
"""

from dataclasses import dataclass

# ============================================================
# RÉFÉRENTIEL FISCAL & SOCIAL (onglet "4. Paramètres" v19)
# ============================================================
PASS_2026 = 48_060

# Cotisations
TX_PATRONAL = 0.42
TX_SALARIAL = 0.12
TX_TNS = 0.45
TX_LIB = 0.45
TX_CSG_CRDS_ACT = 0.097
TX_CSG_DEDUCTIBLE = 0.068   # MODE_AUDIT G2a : promu de constante locale TNS/Salarié
TX_CSG_NON_DEDUCTIBLE = 0.029  # MODE_AUDIT G2a : promu de constante locale TNS/Libéral/Salarié
ASSIETTE_CSG_SAL = 0.9825

# IR - barème 2026
IR_PLAFOND_T1 = 11_600
IR_PLAFOND_T2 = 29_579
IR_PLAFOND_T3 = 84_577
IR_PLAFOND_T4 = 181_917
IR_TAUX_T2 = 0.11
IR_TAUX_T3 = 0.30
IR_TAUX_T4 = 0.41
IR_TAUX_T5 = 0.45

# Abattement salarial (v19)
PLAFOND_ABAT_10PCT_SAL = 14_426  # MODE_AUDIT G2a : promu de constante locale Salarié
TX_ABAT_10PCT_SAL = 0.10         # Taux abattement forfaitaire salarié

# Plafonnement QF
PLAF_QF_DEMI_PART = 1_807
PLAF_QF_PARENT_ISOLE = 4_262          # case T - 1ère pers. à charge
PLAF_QF_PERS_SEULE_L = 1_079          # case L
PLAF_QF_VEUF = 5_625                  # veuf avec enfants à charge
PLAF_QF_INVALIDE = 3_608              # ancien combattant > 74 ans ou invalide

# CEHR
CEHR_SEUIL_C1, CEHR_SEUIL_C2 = 250_000, 500_000
CEHR_SEUIL_M1, CEHR_SEUIL_M2 = 500_000, 1_000_000
CEHR_TX_1, CEHR_TX_2 = 0.03, 0.04

# CDHR (plancher 20 %)
CDHR_TAUX_PLANCHER = 0.20
CDHR_SEUIL_C, CDHR_SEUIL_M = 250_000, 500_000
CDHR_SEUIL_C_HAUT, CDHR_SEUIL_M_HAUT = 330_000, 660_000

# Dividendes
TX_PFU = 0.314
TX_PFU_IR = 0.128
SEUIL_DIV_TNS = 0.10  # 10 % capital + primes + CCA

# IS
TX_IS_REDUIT = 0.15
TX_IS_NORMAL = 0.25
IS_PLAF_REDUIT = 42_500

# Forfait social par effectif
FS_PART = {"Sans salarié": 0.0, "1-10 salariés": 0.0, "11-49 salariés": 0.0,
           "50-249 salariés": 0.20, "≥ 250 salariés": 0.20}
FS_INT = {"Sans salarié": 0.0, "1-10 salariés": 0.0, "11-49 salariés": 0.0,
          "50-249 salariés": 0.0, "≥ 250 salariés": 0.20}
FS_ABO = {"Sans salarié": 0.0, "1-10 salariés": 0.0, "11-49 salariés": 0.0,
          "50-249 salariés": 0.20, "≥ 250 salariés": 0.20}

# Rendements
RDT_CASH = 0.02
RDT_EPARGNE = 0.04


# ============================================================
# FORMES SEL VALIDES (enum contrôlé - garde-fou utilisateur)
# ============================================================
FORMES_SEL_VALIDES = ("SELARL", "SELAS")
# - SELARL : gérant majoritaire = TNS (cotisations ~45%)
# - SELAS  : président = Assimilé salarié (cotisations patronales 42% + salariales 12%)


# ============================================================
# PROFIL CLIENT
# ============================================================
@dataclass
class Profil:
    forme_juridique: str = "SAS / SASU"
    effectif: str = "11-49 salariés"
    situation: str = "Marié / pacsé"
    parts: float = 2.0
    situation_part: str = "Aucune (cas général)"
    autres_revenus: float = 0.0
    dividendes_foyer_hors_enveloppe: float = 0.0
    enveloppe: float = 120_000.0
    benefice_is: float = 200_000.0
    capital_cca: float = 100_000.0
    salaire_brut_assimile: float = 80_000.0

    # ──────────── Inputs spécifiques Libéral (Phase B.2 Étape 3) ────────────
    # Utilisés par strategy/liberal.py uniquement. Valeurs par défaut neutres
    # pour ne pas casser la baseline existante (les modules Assimilé/TNS
    # n'utilisent pas ces champs).
    recettes_bnc: float = 150_000.0              # CA libéral annuel
    frais_pro_bnc: float = 30_000.0              # Frais professionnels déductibles
    remuneration_sel_souhaitee: float = 80_000.0  # Rémunération brute versée par la SEL
    forme_sel: str = "SELARL"                    # "SELARL" ou "SELAS" — valeur contrôlée

    # ──────────── Inputs spécifiques PERO (SP25) ────────────
    # Utilisé par strategy/receptacles_pero.py via l'orchestrateur.
    # Valeur par défaut 0 % : PERO calculé à zéro pour ne pas créer
    # artificiellement un PERO actif (b1 validé SP25). L'assiette
    # de cotisation PERO est lue depuis `salaire_brut_assimile`
    # (champ existant).
    taux_cotisation_pero: float = 0.0            # Taux cotisation employeur PERO (0..1)

    def __post_init__(self):
        """Validation des champs à valeurs contrôlées (enum)."""
        if self.forme_sel not in FORMES_SEL_VALIDES:
            raise ValueError(
                f"forme_sel invalide : {self.forme_sel!r}. "
                f"Valeurs autorisées : {FORMES_SEL_VALIDES}"
            )

    @property
    def regime_social(self) -> str:
        mapping = {
            "SAS / SASU": "Assimilé salarié",
            "SARL (gérance minoritaire)": "Assimilé salarié",
            "SARL (gérance majoritaire) / EURL": "TNS",
            "EI / EI à l'IS": "TNS",
            "Profession libérale (BNC)": "TNS (libéral)",
            "SELARL / SELAS": "TNS (libéral)",
        }
        return mapping.get(self.forme_juridique, "Assimilé salarié")


# ============================================================
# SITUATIONS PARTICULIÈRES QUOTIENT FAMILIAL
# ============================================================
SITUATIONS_PARTICULIERES = {
    "Aucune (cas général)": None,
    "Parent isolé (case T)": ("parent_isole", PLAF_QF_PARENT_ISOLE),
    "Personne seule ayant élevé un enfant ≥ 5 ans (case L)": ("case_l", PLAF_QF_PERS_SEULE_L),
    "Veuf avec enfants à charge": ("veuf", PLAF_QF_VEUF),
    "Ancien combattant > 74 ans ou invalide": ("invalide", PLAF_QF_INVALIDE),
}
