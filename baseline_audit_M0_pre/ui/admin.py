"""
Page d'administration des paramètres réglementaires.

Décisions doctrinales (point 2 de la recommandation utilisateur) :
- Mode SIMPLE par défaut : lecture seule, affichage propre, rassurant pour EC standard
- Mode EXPERT activable : édition des paramètres réglementaires, mot de passe ou toggle
- Historique des modifications versionnées (qui, quand, quoi)
- Bouton "Restaurer doctrine officielle" pour revenir aux valeurs PACTE 2026

⚠ Risques métier identifiés :
- Cabinet qui casse la doctrine par méconnaissance
- Pas de traçabilité des modifications
- Confusion entre paramètre interne et hypothèse client
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# ============================================================
# DATACLASSES
# ============================================================
@dataclass
class ParametreEditable:
    """Un paramètre réglementaire éditable."""
    cle: str                          # Identifiant technique (ex: "FS_PERO")
    libelle: str                      # Libellé affiché
    valeur_actuelle: float
    valeur_doctrine_officielle: float  # Valeur par défaut PACTE 2026 (référence)
    unite: str                        # "€", "%", "fraction" (0-1)
    categorie: str                    # "Forfaits sociaux", "Plafonds", etc.
    source_legale: str
    note: str = ""

    @property
    def est_modifie(self) -> bool:
        """True si la valeur actuelle diffère de la doctrine officielle."""
        return abs(self.valeur_actuelle - self.valeur_doctrine_officielle) > 1e-9


@dataclass
class HistoriqueModif:
    """Trace d'une modification de paramètre."""
    timestamp: str
    utilisateur: str
    cle_parametre: str
    libelle: str
    ancienne_valeur: float
    nouvelle_valeur: float
    motif: str = ""


# ============================================================
# CATALOGUE DES PARAMÈTRES ÉDITABLES (mode expert)
# ============================================================
def construire_catalogue() -> dict:
    """Construit le catalogue initial des paramètres éditables.
    
    Valeurs par défaut alignées sur la doctrine v1.0.0 (01/01/2026).
    """
    return {
        # Forfaits sociaux
        "FS_PERO": ParametreEditable(
            cle="FS_PERO",
            libelle="Forfait social PERO",
            valeur_actuelle=0.08, valeur_doctrine_officielle=0.08,
            unite="%", categorie="Forfaits sociaux",
            source_legale="Loi PACTE 2019, CSS L137-15-1",
            note="Taux retenu pour les versements employeur sur PERO. "
                 "Réservé aux salariés et assimilés salariés.",
        ),
        "FS_PERECO": ParametreEditable(
            cle="FS_PERECO",
            libelle="Forfait social PERECO",
            valeur_actuelle=0.00, valeur_doctrine_officielle=0.00,
            unite="%", categorie="Forfaits sociaux",
            source_legale="Loi PACTE 2019",
            note="Exonération totale jusqu'à fin 2027. Évolution à anticiper pour 2028.",
        ),
        # Plafonds épargne
        "PLAF_ABO_PEE": ParametreEditable(
            cle="PLAF_ABO_PEE",
            libelle="Plafond abondement PEE (annuel)",
            valeur_actuelle=3_844.80, valeur_doctrine_officielle=3_844.80,
            unite="€", categorie="Plafonds épargne",
            source_legale="CSS L3332-11 (8 % du PASS)",
            note="Plafond annuel d'abondement employeur PEE.",
        ),
        "PLAF_ABO_PERECO": ParametreEditable(
            cle="PLAF_ABO_PERECO",
            libelle="Plafond abondement PERECO (annuel)",
            valeur_actuelle=7_689.60, valeur_doctrine_officielle=7_689.60,
            unite="€", categorie="Plafonds épargne",
            source_legale="CSS L3334-8 (16 % du PASS)",
            note="Plafond annuel d'abondement employeur PERECO.",
        ),
        "PLAF_CUMUL_ABONDEMENTS": ParametreEditable(
            cle="PLAF_CUMUL_ABONDEMENTS",
            libelle="Plafond consolidé cumul abondements (PEE + PERECO + PERO)",
            valeur_actuelle=7_689.60, valeur_doctrine_officielle=7_689.60,
            unite="€", categorie="Plafonds épargne",
            source_legale="Lecture consolidée prudente URSSAF 2024",
            note="Lecture la plus prudente. À documenter selon doctrine cabinet.",
        ),
        # Coefficients risque (impact scoring Comparateur)
        "RISK_PERO": ParametreEditable(
            cle="RISK_PERO",
            libelle="Coefficient de risque PERO (scoring Comparateur)",
            valeur_actuelle=0.90, valeur_doctrine_officielle=0.90,
            unite="fraction", categorie="Coefficients de risque",
            source_legale="Convention métier interne",
            note="Pondération du score PERO. Tient compte de la complexité de mise "
                 "en œuvre et de la rigidité catégorielle.",
        ),
        "RISK_CASHBACK_CONFORME": ParametreEditable(
            cle="RISK_CASHBACK_CONFORME",
            libelle="Coefficient de risque Cashback - mode Conforme",
            valeur_actuelle=0.85, valeur_doctrine_officielle=0.85,
            unite="fraction", categorie="Coefficients de risque",
            source_legale="Convention métier interne",
            note="Mode Conforme : souscription nominative + documentation cabinet.",
        ),
        # Hypothèses projection
        "RDT_CASH": ParametreEditable(
            cle="RDT_CASH",
            libelle="Rendement cash défensif (projection)",
            valeur_actuelle=0.02, valeur_doctrine_officielle=0.02,
            unite="%", categorie="Hypothèses projection",
            source_legale="Hypothèse cabinet",
            note="Rendement annuel pour la fraction non capitalisable du gain.",
        ),
        "RDT_EPARGNE": ParametreEditable(
            cle="RDT_EPARGNE",
            libelle="Rendement épargne salariale & PER (projection)",
            valeur_actuelle=0.04, valeur_doctrine_officielle=0.04,
            unite="%", categorie="Hypothèses projection",
            source_legale="Hypothèse cabinet",
            note="Rendement annuel pour les enveloppes capitalisables.",
        ),
    }


# ============================================================
# GESTION DE L'HISTORIQUE
# ============================================================
def enregistrer_modif(historique: list, utilisateur: str,
                      param: ParametreEditable,
                      ancienne_valeur: float, nouvelle_valeur: float,
                      motif: str = "") -> None:
    """Ajoute une trace à l'historique des modifications."""
    historique.append(HistoriqueModif(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        utilisateur=utilisateur,
        cle_parametre=param.cle,
        libelle=param.libelle,
        ancienne_valeur=ancienne_valeur,
        nouvelle_valeur=nouvelle_valeur,
        motif=motif,
    ))


def restaurer_doctrine_officielle(catalogue: dict, historique: list,
                                   utilisateur: str = "Système") -> int:
    """Restaure tous les paramètres aux valeurs doctrine officielle.
    
    Returns: nombre de paramètres effectivement restaurés.
    """
    n_restaures = 0
    for param in catalogue.values():
        if param.est_modifie:
            ancienne = param.valeur_actuelle
            param.valeur_actuelle = param.valeur_doctrine_officielle
            enregistrer_modif(historique, utilisateur, param, ancienne,
                              param.valeur_doctrine_officielle,
                              motif="Restauration doctrine officielle PACTE 2026")
            n_restaures += 1
    return n_restaures


def lister_modifications_actives(catalogue: dict) -> list:
    """Retourne la liste des paramètres qui s'écartent de la doctrine officielle."""
    return [p for p in catalogue.values() if p.est_modifie]


# ============================================================
# FORMATAGE POUR AFFICHAGE
# ============================================================
def formater_valeur(param: ParametreEditable, valeur: Optional[float] = None) -> str:
    """Formate une valeur selon son unité."""
    if valeur is None:
        valeur = param.valeur_actuelle
    if param.unite == "%":
        return f"{valeur*100:.2f} %".replace(".", ",")
    elif param.unite == "€":
        return f"{valeur:,.2f} €".replace(",", " ").replace(".", ",")
    elif param.unite == "fraction":
        return f"{valeur:.2f}".replace(".", ",")
    return str(valeur)


# ============================================================
# DOCTRINE FIGÉE — Valeurs "officielles" intangibles
# ============================================================
DOCTRINE_OFFICIELLE = {
    "version": "1.0.0",
    "date": "01/01/2026",
    "auteur": "Équipe produit Cabinet",
    "intangible": True,
    "description": (
        "Valeurs alignées sur le régime PACTE applicable au 01/01/2026. "
        "Toute modification doit être tracée et motivée. Le bouton "
        "'Restaurer doctrine officielle' permet de revenir à ces valeurs."
    ),
}
