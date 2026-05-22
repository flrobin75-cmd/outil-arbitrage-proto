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

MODE_AUDIT (G3f-receptacles, spec 1.1.0) :
- 5 fonctions publiques acceptent un paramètre opt-in `audit: TraceAudit | None`.
  Codes émis : `RECEPT_*` (namespace dédié).
- Composition interne : `est_accessible` attache `regime_effectif`,
  `motif_inaccessibilite` attache `accessibilite` (qui contient
  lui-même `regime_effectif`). Profondeur jusqu'à 3 niveaux internes.
- `liste_receptacles_par_regime` : trace plate volontairement
  (6 réceptacles itérés en codes plats — pas 12 sous-traces).
- `mention_madelin` : 1 étape constante (texte intégral en hypotheses).
- Discipline non-prescriptive renforcée G3e (14 patterns) : 0 occurrence
  dans le source.
- Note dette d'instrumentation : `strategy/comparateur.py` (G3d) consomme
  silencieusement `est_accessible`/`motif_inaccessibilite` sans propager
  l'audit. Documenté dans KNOWN_LIMITATIONS (rétro-instrumentation G3d-ter
  reportée).
"""

from dataclasses import dataclass
from typing import Optional

from core.profil import Profil
from core.audit import TraceAudit


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
def regime_effectif_receptacles(profil: Profil,
                                 *,
                                 audit: TraceAudit | None = None) -> str:
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
        audit: Trace d'audit optionnelle (G3f-receptacles.1). Side channel.
            Codes émis : `RECEPT_*`. Aucune sous-trace (trace plate).

    Returns:
        L'un des 4 régimes effectifs (REGIME_EFF_*).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("RECEPT_" + suffixe, label, valeur, **kw)

    regime_social = profil.regime_social

    _log("REGIME_SOCIAL_PROFIL",
         "Régime social du profil (input)",
         regime_social, unite="",
         hypotheses={"valeurs_attendues": ["Assimilé salarié", "TNS",
                                            "TNS (libéral)", "Salarié"]})
    _log("FORME_JURIDIQUE_PROFIL",
         "Forme juridique du profil (utilisée pour distinguer SEL)",
         profil.forme_juridique, unite="")
    _log("FORME_SEL_PROFIL",
         "Forme SEL du profil (utilisée pour distinguer SELARL/SELAS)",
         profil.forme_sel or "(non applicable)", unite="",
         hypotheses={"applicable_si": "forme_juridique == 'SELARL / SELAS'",
                     "valeurs_attendues_si_applicable": ["SELARL", "SELAS"]})

    if regime_social == "Assimilé salarié":
        resultat = REGIME_EFF_ASSIMILE
        branche = "assimile_direct"
    elif regime_social == "TNS":
        resultat = REGIME_EFF_TNS
        branche = "tns_direct"
    elif regime_social == "TNS (libéral)":
        # Libéral : distinguer BNC pur des SEL
        if profil.forme_juridique == "SELARL / SELAS":
            # SEL : résolution selon forme_sel (validée par enum Profil)
            if profil.forme_sel == "SELARL":
                resultat = REGIME_EFF_TNS         # SELARL = gérant TNS
                branche = "selarl_vers_tns"
            else:  # SELAS
                resultat = REGIME_EFF_ASSIMILE    # SELAS = président Assimilé
                branche = "selas_vers_assimile"
        else:
            # Profession libérale (BNC) classique
            resultat = REGIME_EFF_LIBERAL_BNC
            branche = "liberal_bnc_pur"
    else:
        # Cas par défaut (Salarié non dirigeant, ou inconnu)
        resultat = REGIME_EFF_SALARIE
        branche = "salarie_ou_inconnu_fallback"

    _log("REGIME_EFFECTIF",
         "Régime effectif appliqué pour les réceptacles (résolution SELARL/SELAS incluse)",
         resultat, unite="",
         hypotheses={"branche_appliquee": branche,
                     "regimes_effectifs_possibles": list(REGIMES_EFFECTIFS),
                     "regle_or": "SELARL → TNS / SELAS → Assimilé "
                                 "(centralisée ici, à ne PAS recoder ailleurs)"})

    return resultat


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
def est_accessible(receptacle: str, profil: Profil,
                    *,
                    audit: TraceAudit | None = None) -> bool:
    """
    Détermine si un réceptacle est accessible pour le profil donné.

    Args:
        receptacle: Nom du réceptacle (ex: "PEE", "PERIN", ...)
        profil: Profil client
        audit: Trace d'audit optionnelle (G3f-receptacles.1). Codes émis :
            `RECEPT_*` méta. Attache 1 sous-trace `regime_effectif` qui compose
            `regime_effectif_receptacles`.

    Returns:
        True si le réceptacle est accessible, False sinon.
        True par défaut si le réceptacle n'est pas dans la matrice
        (par sécurité — ne pas bloquer un futur réceptacle non documenté).
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("RECEPT_" + suffixe, label, valeur, **kw)

    _log("RECEPTACLE_INPUT",
         "Nom du réceptacle évalué (input)",
         receptacle, unite="",
         hypotheses={"receptacles_modelises_v1": list(MATRICE_RECEPTACLES.keys())})

    receptacle_connu = receptacle in MATRICE_RECEPTACLES

    _log("RECEPTACLE_CONNU",
         "Présence du réceptacle dans la matrice §5",
         1.0 if receptacle_connu else 0.0, unite="bool",
         hypotheses={"valeur_bool": receptacle_connu,
                     "convention_inconnu": "True par défaut (ne pas bloquer "
                                            "un futur réceptacle non documenté)"})

    if not receptacle_connu:
        _log("ACCESSIBLE",
             "Accessibilité finale (réceptacle inconnu → True par convention)",
             1.0, unite="bool",
             hypotheses={"valeur_bool": True,
                         "branche": "receptacle_inconnu_fallback"})
        return True

    # Réceptacle connu : composer la résolution du régime effectif
    if audit is not None:
        st_re = TraceAudit(regime="Résolution régime effectif",
                            profil_resume=f"profil={profil.regime_social}")
        regime_eff = regime_effectif_receptacles(profil, audit=st_re)
        audit.attacher_sous_trace("regime_effectif", st_re)
    else:
        regime_eff = regime_effectif_receptacles(profil)

    accessible = MATRICE_RECEPTACLES[receptacle].get(regime_eff, True)

    _log("ACCESSIBLE",
         "Accessibilité finale (lecture matrice §5 pour le régime effectif)",
         1.0 if accessible else 0.0, unite="bool",
         hypotheses={"valeur_bool": accessible,
                     "regime_effectif_resolu": regime_eff,
                     "ligne_matrice": MATRICE_RECEPTACLES[receptacle],
                     "convention_regime_inconnu": "True par défaut"},
         notes="Détails de la résolution du régime effectif "
               "dans la sous-trace 'regime_effectif'.")

    return accessible


def motif_inaccessibilite(receptacle: str, profil: Profil,
                           *,
                           audit: TraceAudit | None = None) -> Optional[str]:
    """
    Renvoie le motif d'inaccessibilité du réceptacle pour le profil.

    Args:
        receptacle: Nom du réceptacle
        profil: Profil client
        audit: Trace d'audit optionnelle (G3f-receptacles.1). Codes émis :
            `RECEPT_*` méta. Attache 1 sous-trace `accessibilite` qui compose
            `est_accessible` (qui contient lui-même `regime_effectif`).

    Returns:
        Une chaîne explicative si le réceptacle est inaccessible,
        None si accessible.
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("RECEPT_" + suffixe, label, valeur, **kw)

    # Composer est_accessible
    if audit is not None:
        st_acc = TraceAudit(regime="Évaluation accessibilité",
                             profil_resume=f"receptacle={receptacle}")
        accessible = est_accessible(receptacle, profil, audit=st_acc)
        audit.attacher_sous_trace("accessibilite", st_acc)
    else:
        accessible = est_accessible(receptacle, profil)

    if accessible:
        _log("MOTIF_RETOURNE",
             "Motif d'inaccessibilité retourné (None si accessible)",
             "(None)", unite="",
             hypotheses={"valeur_python_retournee": None,
                         "accessible": True,
                         "branche": "accessible_pas_de_motif"},
             notes="Détails de l'évaluation d'accessibilité "
                   "dans la sous-trace 'accessibilite'.")
        return None

    regime_eff = regime_effectif_receptacles(profil)
    motif = f"Non accessible en régime {regime_eff}."

    _log("MOTIF_RETOURNE",
         "Motif d'inaccessibilité retourné (texte structuré générique)",
         motif, unite="",
         hypotheses={"accessible": False,
                     "regime_effectif_pour_motif": regime_eff,
                     "branche": "inaccessible_motif_construit",
                     "format_motif": "f'Non accessible en régime {regime_eff}.'"},
         notes="Détails de l'évaluation d'accessibilité "
               "dans la sous-trace 'accessibilite'.")

    return motif


def liste_receptacles_par_regime(profil: Profil,
                                  *,
                                  audit: TraceAudit | None = None) -> dict:
    """
    Renvoie le dict des réceptacles modélisés avec leur statut pour ce profil.

    Args:
        profil: Profil client
        audit: Trace d'audit optionnelle (G3f-receptacles.1). Codes émis :
            `RECEPT_*` à plat. **Aucune sous-trace** : les appels à
            `est_accessible` et `motif_inaccessibilite` (12 au total pour
            6 réceptacles) sont consommés sans propagation pour éviter
            la surcharge structurelle (cf. cadrage G3f).

    Returns:
        Dict {receptacle: {"accessible": bool, "motif": str | None}}
    """
    def _log(suffixe, label, valeur, **kw):
        if audit is not None:
            audit.add("RECEPT_" + suffixe, label, valeur, **kw)

    resultat = {
        rec: {
            "accessible": est_accessible(rec, profil),
            "motif": motif_inaccessibilite(rec, profil),
        }
        for rec in MATRICE_RECEPTACLES
    }

    _log("NB_RECEPTACLES_MODELISES",
         "Nombre de réceptacles modélisés dans la matrice §5",
         float(len(MATRICE_RECEPTACLES)), unite="count",
         hypotheses={"receptacles_modelises": list(MATRICE_RECEPTACLES.keys()),
                     "convention_trace": "Trace plate volontaire — "
                                          "pas de sous-trace par réceptacle "
                                          "pour éviter surcharge structurelle"})

    for rec in MATRICE_RECEPTACLES:
        est_acc = resultat[rec]["accessible"]
        motif = resultat[rec]["motif"]
        # Code sécurisé en snake_case (gérer les caractères accentués)
        nom_court = (rec.upper()
                     .replace("É", "E").replace("È", "E")
                     .replace("Ê", "E").replace("À", "A"))
        _log(
            f"RECEPTACLE_{nom_court}",
            f"Statut d'accessibilité du réceptacle {rec} pour ce profil",
            1.0 if est_acc else 0.0, unite="bool",
            parent_id="RECEPT_NB_RECEPTACLES_MODELISES",
            hypotheses={"receptacle": rec,
                        "accessible": est_acc,
                        "motif": motif,
                        "ligne_matrice": MATRICE_RECEPTACLES[rec]},
        )

    return resultat


def mention_madelin(*, audit: TraceAudit | None = None) -> str:
    """
    Renvoie la mention informative Madelin / PER TNS.

    Cette mention est destinée à être affichée systématiquement à côté
    du Comparateur pour les régimes TNS et Libéral. Elle évite que les
    utilisateurs croient à un oubli.

    Args:
        audit: Trace d'audit optionnelle (G3f-receptacles.1). Codes émis :
            `RECEPT_*` (1 étape constante). Aucune sous-trace.

    Returns:
        Le texte intégral de la mention.
    """
    if audit is not None:
        audit.add("RECEPT_MENTION_LONGUEUR",
                  "Longueur (caractères) de la mention informative Madelin/PER TNS",
                  float(len(MADELIN_PER_TNS_MENTION)), unite="chars",
                  hypotheses={"MADELIN_PER_TNS_MENTION": MADELIN_PER_TNS_MENTION,
                              "convention": "Texte intégral en hypotheses, "
                                            "valeur de l'étape = longueur factuelle",
                              "destinataire_affichage": "TNS et Libéral (informatif)"},
                  notes="Wording métier intégral préservé en hypotheses — "
                        "pattern G3b/c/d/e")
    return MADELIN_PER_TNS_MENTION
