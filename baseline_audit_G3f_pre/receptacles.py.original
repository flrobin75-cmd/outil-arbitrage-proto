"""
Strategy Engine — Matrice des réceptacles d'épargne par régime.

Reproduit fidèlement la matrice §5 du Cadre méthodologique v1.0.1 :
réceptacles d'épargne salariale et retraite, accessibilité par régime
fiscal et social du dirigeant.

Décisions méthodologiques (validées par l'utilisateur) :

1. Module dédié (Option B) : centralise la matrice, évite duplication ailleurs
2. Filtre par accessible/motif (Option A) : les lignes inaccessibles restent
   visibles avec un motif d'inaccessibilité (pas masquées)
3. SEL : règle de résolution fonction de profil.forme_sel
   - SELARL (gérant majoritaire = TNS) → traité comme TNS
   - SELAS (président = Assimilé)     → traité comme Assimilé
4. Madelin/PER TNS : non modélisé dans le Comparateur v1 — mention informative
   conservée (pas absente), traitement séparé en cabinet

────────────────────────────────────────────────────────────────────────
RÈGLE D'OR — Résolution du régime effectif

Toute logique qui distingue les réceptacles par régime PASSE par la
fonction `regime_effectif_receptacles()`. La règle SELARL→TNS / SELAS→
Assimilé NE DOIT PAS être recodée ailleurs dans le projet.

Si on a besoin de cette règle dans `comparateur.py`, dans `ui/`, ou dans
un futur module, on importe `regime_effectif_receptacles` depuis ce
fichier.
────────────────────────────────────────────────────────────────────────

Module : consomme uniquement core.profil. Aucun import vers regime/* ou
strategy/* (pour éviter dépendances circulaires — ce module est consommé
par strategy/comparateur.py).
"""

from dataclasses import dataclass
from typing import Optional

from core.profil import Profil


# ============================================================
# CONSTANTES — Régimes effectifs pour les réceptacles
# ============================================================
# Régime "effectif" au sens des réceptacles : 4 valeurs possibles
REGIME_EFF_ASSIMILE = "Assimilé salarié"
REGIME_EFF_TNS = "TNS"
REGIME_EFF_LIBERAL_BNC = "Libéral BNC"
REGIME_EFF_SALARIE = "Salarié (non dirigeant)"

REGIMES_EFFECTIFS = (
    REGIME_EFF_ASSIMILE,
    REGIME_EFF_TNS,
    REGIME_EFF_LIBERAL_BNC,
    REGIME_EFF_SALARIE,
)


# ============================================================
# FONCTION DE RÉSOLUTION UNIQUE — Garde-fou central
# ============================================================
def regime_effectif_receptacles(profil: Profil) -> str:
    """
    Renvoie le régime effectif au sens des réceptacles d'épargne.

    Cette fonction est la SEULE source de vérité pour la règle SEL :
    - SELARL (gérant majoritaire = TNS) → REGIME_EFF_TNS
    - SELAS (président = Assimilé)     → REGIME_EFF_ASSIMILE

    Toute logique d'accessibilité des réceptacles dans le projet DOIT
    passer par cette fonction. Ne JAMAIS recoder la règle SELARL/SELAS
    ailleurs.

    Args:
        profil: Profil client

    Returns:
        L'un des 4 régimes effectifs (REGIME_EFF_*).
    """
    regime_social = profil.regime_social

    if regime_social == "Assimilé salarié":
        return REGIME_EFF_ASSIMILE

    if regime_social == "TNS":
        return REGIME_EFF_TNS

    if regime_social == "TNS (libéral)":
        # Libéral : distinguer BNC pur des SEL
        if profil.forme_juridique == "SELARL / SELAS":
            # SEL : résolution selon forme_sel (validée par enum Profil)
            if profil.forme_sel == "SELARL":
                return REGIME_EFF_TNS         # SELARL = gérant TNS
            else:  # SELAS
                return REGIME_EFF_ASSIMILE    # SELAS = président Assimilé
        else:
            # Profession libérale (BNC) classique
            return REGIME_EFF_LIBERAL_BNC

    # Cas par défaut (Salarié non dirigeant, ou inconnu)
    return REGIME_EFF_SALARIE


# ============================================================
# MATRICE §5 DU CADRE MÉTHODOLOGIQUE v1.0.1
# ============================================================
# Pour chaque réceptacle, dict {régime effectif : accessible (bool)}
#
# Réceptacles modélisés dans le Comparateur v1 : PEE, PERECO, PERO,
# PERIN, intéressement, participation.
#
# Réceptacles MENTIONNÉS mais non modélisés v1 : Madelin / PER TNS
# (à traiter séparément en cabinet).

MATRICE_RECEPTACLES = {
    "PEE": {
        REGIME_EFF_ASSIMILE: True,
        REGIME_EFF_TNS: False,
        REGIME_EFF_LIBERAL_BNC: False,
        REGIME_EFF_SALARIE: True,  # accessible si le salarié y a droit chez son employeur
    },
    "PERECO": {
        REGIME_EFF_ASSIMILE: True,
        REGIME_EFF_TNS: False,
        REGIME_EFF_LIBERAL_BNC: False,
        REGIME_EFF_SALARIE: True,
    },
    "PERO": {
        REGIME_EFF_ASSIMILE: True,
        REGIME_EFF_TNS: False,
        REGIME_EFF_LIBERAL_BNC: False,
        REGIME_EFF_SALARIE: True,
    },
    "PERIN": {
        REGIME_EFF_ASSIMILE: True,
        REGIME_EFF_TNS: True,
        REGIME_EFF_LIBERAL_BNC: True,
        REGIME_EFF_SALARIE: True,
    },
    "Intéressement": {
        REGIME_EFF_ASSIMILE: True,
        REGIME_EFF_TNS: False,
        REGIME_EFF_LIBERAL_BNC: False,
        REGIME_EFF_SALARIE: True,
    },
    "Participation": {
        REGIME_EFF_ASSIMILE: True,
        REGIME_EFF_TNS: False,
        REGIME_EFF_LIBERAL_BNC: False,
        REGIME_EFF_SALARIE: True,
    },
}


# ============================================================
# Réceptacles MENTIONNÉS mais non modélisés en v1
# ============================================================
MADELIN_PER_TNS_MENTION = (
    "Madelin / PER TNS : non modélisé dans ce comparateur v1 — "
    "à traiter séparément en cabinet. Pour les dirigeants TNS, le "
    "PERIN reste pleinement accessible et capturé dans ce comparateur."
)


# ============================================================
# API publique
# ============================================================
def est_accessible(receptacle: str, profil: Profil) -> bool:
    """
    Détermine si un réceptacle est accessible pour le profil donné.

    Args:
        receptacle: Nom du réceptacle (ex: "PEE", "PERIN", ...)
        profil: Profil client

    Returns:
        True si le réceptacle est accessible, False sinon.
        True par défaut si le réceptacle n'est pas dans la matrice
        (par sécurité — ne pas bloquer un futur réceptacle non documenté).
    """
    if receptacle not in MATRICE_RECEPTACLES:
        return True  # Inconnu → ne pas bloquer

    regime_eff = regime_effectif_receptacles(profil)
    return MATRICE_RECEPTACLES[receptacle].get(regime_eff, True)


def motif_inaccessibilite(receptacle: str, profil: Profil) -> Optional[str]:
    """
    Renvoie le motif d'inaccessibilité du réceptacle pour le profil.

    Args:
        receptacle: Nom du réceptacle
        profil: Profil client

    Returns:
        Une chaîne explicative si le réceptacle est inaccessible,
        None si accessible.
    """
    if est_accessible(receptacle, profil):
        return None

    regime_eff = regime_effectif_receptacles(profil)

    # Message générique formaté
    return f"Non accessible en régime {regime_eff}."


def liste_receptacles_par_regime(profil: Profil) -> dict:
    """
    Renvoie le dict des réceptacles modélisés avec leur statut pour ce profil.

    Args:
        profil: Profil client

    Returns:
        Dict {receptacle: {"accessible": bool, "motif": str | None}}
    """
    return {
        rec: {
            "accessible": est_accessible(rec, profil),
            "motif": motif_inaccessibilite(rec, profil),
        }
        for rec in MATRICE_RECEPTACLES
    }


def mention_madelin() -> str:
    """
    Renvoie la mention informative Madelin / PER TNS.

    Cette mention est destinée à être affichée systématiquement à côté
    du Comparateur pour les régimes TNS et Libéral. Elle évite que les
    utilisateurs croient à un oubli.
    """
    return MADELIN_PER_TNS_MENTION
