"""
core/audit.py — Trace d'audit déterministe (MODE_AUDIT).

Cette couche fournit un *side channel* d'instrumentation des moteurs métier.
Quand un calcul est exécuté avec une `TraceAudit` non-nulle, chaque étape
significative y dépose un enregistrement structuré (`EtapeAudit`) qui décrit :

- ce qui a été calculé (code stable, label libre)
- avec quelles hypothèses doctrinales (doctrine_ref → valeur résolue)
- avec quelle position dans la hiérarchie du calcul (parent_id)

Garanties non-négociables :

1. **Aucune modification du résultat numérique** quand `audit=None` (rétrocompat
   parfaite). Hash baseline `8863991f27f67847` conservé.
2. **Aucune logique métier déplacée**. L'instrumentation est un side channel,
   jamais une modification du calcul.
3. **Couche neutre** : `core/audit.py` ne dépend que de `typing` et `dataclasses`.
   Le formatage console et PDF reste dans `ui/`.
4. **Vocabulaire prudent** dans tous les libellés (vérifié par
   `semantic_guardrails.py` — patterns audit ajoutés en M5).

Convention de nommage des `code` :

    <REGIME>_<DOMAINE>_<ETAPE>

en SCREAMING_SNAKE_CASE. Exemples tirés du contrat M2 (`regime/tns.py`,
instrumentation TNS v1) — ces codes existent réellement et servent de
référence pour tout nouveau régime instrumenté :

    TNS_REM_BRUTE                  # racine, input
    TNS_COTIS_SOCIALES             # racine, agrégat de cotisations
    TNS_COTIS_TNS_BASE             # enfant de TNS_COTIS_SOCIALES
    TNS_CSG_DEDUCTIBLE             # enfant de TNS_COTIS_SOCIALES
    TNS_CSG_NON_DEDUCTIBLE         # enfant de TNS_COTIS_SOCIALES
    TNS_REVENU_NET_PRO             # racine
    TNS_REVENU_IMPOSABLE           # racine
    TNS_REVENU_IMPOSABLE_FOYER     # racine
    TNS_IR_FOYER_AGGREGE           # racine, agrégat IR + CEHR + CDHR
    TNS_IR_FOYER_BRUT              # enfant de TNS_IR_FOYER_AGGREGE
    TNS_CEHR                       # enfant
    TNS_CDHR                       # enfant
    TNS_TAUX_MOYEN_IR              # enfant
    TNS_IMPOTS_IMPUTABLES_REM      # enfant
    TNS_NET_APRES_IR               # racine
    TNS_COUT_SOCIETE               # racine
    TNS_DIVIDENDES                 # racine, agrégat dividendes
    TNS_DIV_SEUIL_10PCT            # enfant de TNS_DIVIDENDES
    TNS_DIV_FRACTION_COTIS_TNS     # enfant
    TNS_DIV_COTIS_TNS_SUR_DIV      # enfant
    TNS_DIV_FRACTION_PFU           # enfant
    TNS_DIV_PFU_SUR_FRACTION       # enfant
    TNS_DIV_IR_SUR_FRACTION_TNS    # enfant
    TNS_DIV_NET                    # enfant

Politique de versionning des codes : un code est **stable** une fois publié.
Si la sémantique d'une étape change, on incrémente le suffixe (par exemple
`TNS_IR_FOYER_BRUT_V2`). On ne renomme jamais un code existant.

Convention pour `doctrine_ref` : utiliser le **nom de la constante/variable**
exposée par `doctrine.py` ou par `core/profil.py`. Exemples utilisés dans
l'instrumentation TNS : `PASS_2026`, `TX_TNS`, `TX_PFU`, `SEUIL_DIV_TNS`,
`IR_PLAFOND_T1`, `IR_PLAFOND_T2`, `IR_PLAFOND_T3`, `IR_PLAFOND_T4`.
Le renderer résout via `core.audit.resoudre_doctrine_ref(ref)` pour afficher
la valeur courante.

Politique sémantique : les `label` sont libres mais soumis aux mêmes garde-fous
que les libellés PDF. Vocabulaire prudent obligatoire :
- « valeur appliquée », « hypothèse retenue » : OK
- « valeur correcte », « stratégie optimale », « recommandée » : INTERDIT
"""

from dataclasses import dataclass, field
from typing import Any


# ============================================================
# VERSIONING DE LA SPEC D'AUDIT
# ============================================================
AUDIT_SPEC_VERSION = "1.1.0"
"""Version de la structure de données TraceAudit/EtapeAudit.

Historique :

- 1.0.0 (M1, MODE_AUDIT v1) : structure initiale `TraceAudit` + `EtapeAudit`
  avec liste plate d'étapes et hiérarchie via `parent_id`.

- 1.1.0 (G3a, MODE_AUDIT v1.3) : ajout de la **composition par sous-traces
  nommées**. Une `TraceAudit` peut attacher d'autres `TraceAudit` sous une
  clé symbolique (`attacher_sous_trace(nom, trace)`). Permet aux couches
  méta (stratégies) de référencer les traces régime sans dupliquer leurs
  étapes ni risquer la collision de codes (cas du comparateur qui appelle
  le même régime plusieurs fois avec des inputs différents).

  Garanties d'immutabilité après attachement (G3a) :
  - refus des doublons de noms,
  - refus du réattachement d'une même `TraceAudit`,
  - refus des cycles (une trace ne peut pas se contenir elle-même),
  - la `TraceAudit` parente garde la propriété intellectuelle des étapes
    qu'elle ajoute via `add()` ; les sous-traces conservent leur propre
    liste d'étapes.

Toute modification rétro-incompatible de la structure doit incrémenter ce
numéro et être documentée dans `AUDIT_MODE.md`. Les tests d'audit doivent
vérifier la version attendue.
"""


# ============================================================
# OBJET ATOMIQUE — UNE ÉTAPE
# ============================================================
@dataclass
class EtapeAudit:
    """Enregistrement atomique d'une étape de calcul tracée.

    Attributs :
        code : Identifiant stable de l'étape (cf. convention SCREAMING_SNAKE_CASE
            ci-dessus). Sert de clé pour les tests et pour les renderers futurs.
            Une fois publié, il n'est plus renommé — seulement versionné par
            suffixe (`_V2`).

        label : Libellé humain libre, en français, vocabulaire prudent. Affiché
            par les renderers (console, PDF). Peut évoluer librement entre
            versions. Ne doit jamais être utilisé comme clé en test.

        valeur : Valeur calculée par l'étape (typiquement un float monétaire
            mais peut être n'importe quoi de sérialisable). C'est le résultat
            *factuel* de l'étape.

        unite : Unité de la valeur (`"EUR"`, `"%"`, `"PASS"`, etc.). Permet
            au renderer de formater. `""` si sans unité.

        doctrine_refs : Liste des identifiants doctrinaux (noms de constantes
            de `doctrine.py`) auxquels l'étape se rattache. Résolus côté
            renderer pour afficher la citation.

        hypotheses : Snapshot des hypothèses chiffrées effectivement utilisées
            par l'étape, sous forme `{doctrine_ref: valeur_utilisée}`. Permet
            de détecter immédiatement un override local d'une constante
            doctrinale.

        parent_id : `code` de l'étape parente, ou `None` pour une étape de
            premier niveau. Permet au renderer de reconstruire l'arbre du
            calcul (ex. IR_TOTAL > IR_TRANCHE_1, IR_TRANCHE_2, IR_DECOTE).

        notes : Annotations libres, vocabulaire prudent. Optionnel.
    """
    code: str
    label: str
    valeur: Any
    unite: str = ""
    doctrine_refs: tuple = field(default_factory=tuple)
    hypotheses: dict = field(default_factory=dict)
    parent_id: str | None = None
    notes: str = ""


# ============================================================
# CONTENEUR — UNE TRACE COMPLÈTE
# ============================================================
@dataclass
class TraceAudit:
    """Conteneur d'étapes d'audit pour un calcul donné.

    Une `TraceAudit` est créée vide par l'appelant, passée aux fonctions
    instrumentées, qui y ajoutent des `EtapeAudit` via `add()`.

    L'objet est inspectable directement (`trace.etapes`) ou via les helpers
    (`get(code)`, `enfants(code)`).

    À partir de la spec 1.1.0 (G3a), une `TraceAudit` peut également
    **attacher des sous-traces** sous une clé symbolique :

        strat_trace = TraceAudit(regime="Strategy/Assimilé/A")
        sub = TraceAudit(regime="Assimilé (TX_IR_MOY)")
        calcul_tx_ir_moyen(profil, audit=sub)
        strat_trace.attacher_sous_trace("tx_ir_moy_contexte_A", sub)

    Ce mécanisme permet aux couches méta (stratégies) de référencer des
    traces régime sans dupliquer leurs étapes. Le renderer reconstitue
    le graphe à l'affichage.

    Convention d'usage :

        >>> trace = TraceAudit(regime="TNS", profil_resume="div=20k, salaire=60k")
        >>> resultat = arbitrage_complet_tns(profil, audit=trace)
        >>> # trace.etapes contient maintenant la liste ordonnée des étapes
        >>> # resultat est identique à ce qui aurait été retourné sans audit
    """
    regime: str
    profil_resume: str = ""
    spec_version: str = AUDIT_SPEC_VERSION
    etapes: list[EtapeAudit] = field(default_factory=list)
    sous_traces: dict = field(default_factory=dict)

    def add(self,
            code: str,
            label: str,
            valeur: Any,
            *,
            unite: str = "",
            doctrine_refs: tuple = (),
            hypotheses: dict | None = None,
            parent_id: str | None = None,
            notes: str = "") -> EtapeAudit:
        """Ajoute une étape à la trace et la retourne.

        Args:
            code: Identifiant stable (cf. convention).
            label: Libellé humain prudent.
            valeur: Valeur calculée.
            unite: Unité de la valeur ("EUR", "%", etc.).
            doctrine_refs: Tuple de références doctrinales.
            hypotheses: Dict des hypothèses chiffrées utilisées.
            parent_id: Code parent ou None.
            notes: Annotation libre.

        Returns:
            L'EtapeAudit créée (pour chaînage éventuel).

        Raises:
            ValueError: Si `code` est déjà présent dans la trace (les codes
                doivent être uniques par TraceAudit).
        """
        if any(e.code == code for e in self.etapes):
            raise ValueError(
                f"Code d'étape déjà présent dans la trace : {code!r}. "
                f"Les codes doivent être uniques par TraceAudit."
            )
        etape = EtapeAudit(
            code=code,
            label=label,
            valeur=valeur,
            unite=unite,
            doctrine_refs=tuple(doctrine_refs),
            hypotheses=dict(hypotheses) if hypotheses else {},
            parent_id=parent_id,
            notes=notes,
        )
        self.etapes.append(etape)
        return etape

    def get(self, code: str) -> EtapeAudit | None:
        """Retourne l'étape de code donné, ou None si absente."""
        for e in self.etapes:
            if e.code == code:
                return e
        return None

    def enfants(self, code: str) -> list[EtapeAudit]:
        """Retourne la liste ordonnée des étapes ayant `code` comme parent."""
        return [e for e in self.etapes if e.parent_id == code]

    def racines(self) -> list[EtapeAudit]:
        """Retourne la liste ordonnée des étapes de premier niveau."""
        return [e for e in self.etapes if e.parent_id is None]

    def codes(self) -> list[str]:
        """Retourne la liste ordonnée des codes présents."""
        return [e.code for e in self.etapes]

    # ============================================================
    # COMPOSITION PAR SOUS-TRACES (spec 1.1.0, G3a)
    # ============================================================
    def attacher_sous_trace(self, nom: str, sous_trace: "TraceAudit") -> None:
        """Attache une `TraceAudit` enfant sous une clé symbolique.

        Permet aux couches méta (stratégies) de référencer des traces
        régime sans dupliquer leurs étapes. Le graphe résultant est
        navigable via `self.sous_traces[nom]`.

        Args:
            nom: Identifiant symbolique de l'attachement, unique par trace
                parente. Utiliser une convention descriptive du contexte
                (ex. `"tx_ir_moy_strategie_A"`, `"appel_tns_scenario_2"`).
            sous_trace: La `TraceAudit` à attacher. Doit être différente
                de `self` (pas de cycle direct).

        Raises:
            ValueError: Si `nom` est déjà utilisé pour un autre attachement
                (refus des doublons de noms).
            ValueError: Si `sous_trace` est déjà attachée sous un autre nom
                (refus du réattachement — les traces ne sont pas partagées).
            ValueError: Si `sous_trace is self` (refus du cycle direct).
            TypeError: Si `sous_trace` n'est pas une `TraceAudit`.

        Note : la détection des cycles indirects (A → B → A) n'est pas
        assurée en v1.1.0 — éviter par convention. La structure attendue
        est arborescente, pas un graphe quelconque.
        """
        if not isinstance(sous_trace, TraceAudit):
            raise TypeError(
                f"sous_trace doit être une TraceAudit, "
                f"reçu {type(sous_trace).__name__}"
            )
        if sous_trace is self:
            raise ValueError(
                "Refus de cycle : une TraceAudit ne peut pas s'attacher elle-même."
            )
        if nom in self.sous_traces:
            raise ValueError(
                f"Nom de sous-trace déjà attaché : {nom!r}. "
                f"Les noms d'attachement doivent être uniques par trace parente."
            )
        # Refus du réattachement : on parcourt déjà-attachées pour vérifier
        # qu'on ne réattache pas la même instance ailleurs dans cette trace.
        for nom_existant, deja in self.sous_traces.items():
            if deja is sous_trace:
                raise ValueError(
                    f"TraceAudit déjà attachée sous le nom {nom_existant!r}. "
                    f"Refus du réattachement."
                )
        self.sous_traces[nom] = sous_trace

    def get_sous_trace(self, nom: str) -> "TraceAudit | None":
        """Retourne la sous-trace attachée sous `nom`, ou None si absente."""
        return self.sous_traces.get(nom)

    def noms_sous_traces(self) -> list[str]:
        """Retourne la liste ordonnée des noms de sous-traces attachées."""
        return list(self.sous_traces.keys())


# ============================================================
# RÉSOLUTION DOCTRINALE
# ============================================================
def resoudre_doctrine_ref(ref: str) -> Any:
    """Résout un identifiant doctrinal en sa valeur courante.

    Importe `doctrine` à la demande pour éviter une dépendance circulaire
    au niveau module (core ← doctrine est OK, mais on garde l'import lazy
    pour permettre un test isolé de la couche audit).

    Args:
        ref: Nom de la constante/variable exposée par `doctrine.py`.
            Exemples : `"PASS_2026"`, `"TX_TNS"`, `"TX_PFU"`.

    Returns:
        La valeur courante de la constante.

    Raises:
        AttributeError: Si la référence n'existe pas dans `doctrine.py`.
            Le message indique le nom recherché, pour faciliter le diagnostic
            quand une instrumentation cite un `doctrine_ref` qui n'existe pas
            (ou plus) dans la doctrine courante.

    Note : les noms `PASS_2026`, `TX_TNS`, etc. sont définis dans `core/profil.py`
    en pratique (pas dans `doctrine.py` direct), donc on cherche d'abord dans
    `doctrine`, puis dans `core.profil` en repli, puis on lève.
    """
    import doctrine
    if hasattr(doctrine, ref):
        return getattr(doctrine, ref)
    # Repli : beaucoup de constantes effectives vivent dans core.profil
    try:
        import core.profil as profil_mod
        if hasattr(profil_mod, ref):
            return getattr(profil_mod, ref)
    except ImportError:
        pass
    raise AttributeError(
        f"Référence doctrinale inconnue : {ref!r}. "
        f"Vérifier que la constante existe dans `doctrine.py` ou `core/profil.py`."
    )


__all__ = [
    "AUDIT_SPEC_VERSION",
    "EtapeAudit",
    "TraceAudit",
    "resoudre_doctrine_ref",
]
