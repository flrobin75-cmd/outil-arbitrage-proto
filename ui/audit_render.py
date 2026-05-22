"""
ui/audit_render.py — Renderer console pour TraceAudit (MODE_AUDIT).

Cette couche **présentation** consomme un objet `core.audit.TraceAudit` et
produit une représentation textuelle structurée, lisible en console ou
exportable en log.

Le rendu PDF audit-ready sera ajouté ultérieurement dans `ui/pdf_export.py`
en consommant la même `TraceAudit` (source unique de vérité).

Principes :

1. **Source unique** : le renderer ne calcule rien, il formate. Toute valeur
   affichée vient directement de la trace.
2. **Résolution doctrinale paresseuse** : les `doctrine_ref` sont résolues
   au moment du rendu (pas à l'instrumentation). Permet de comparer la
   valeur effectivement utilisée (`etape.hypotheses[ref]`) à la valeur
   doctrinale courante (`resoudre_doctrine_ref(ref)`).
3. **Vocabulaire prudent** : le rendu applique les restrictions terminologiques
   définies dans TERMINOLOGY.md §2. Il reste descriptif, factuel et non prescriptif.
"""

from core.audit import TraceAudit, EtapeAudit, resoudre_doctrine_ref


# ============================================================
# FORMATAGE D'UNE VALEUR
# ============================================================
def _formater_valeur(valeur, unite: str) -> str:
    """Formate une valeur selon son unité.

    - EUR : 2 décimales avec espaces milliers
    - %, ratio : 4 décimales
    - autres : repr() court
    """
    if isinstance(valeur, (int, float)):
        if unite == "EUR":
            return f"{valeur:>14,.2f} €".replace(",", " ")
        if unite == "%":
            return f"{valeur:>10.4f} %"
        if unite == "ratio":
            return f"{valeur:>10.4f}"
        return f"{valeur:>14,.2f} {unite}".rstrip()
    return f"{valeur!r}"


# ============================================================
# RENDU D'UNE ÉTAPE (UNE LIGNE)
# ============================================================
def _rendre_etape(etape: EtapeAudit, indent: int = 0) -> list[str]:
    """Rend une étape sur une ou plusieurs lignes selon ce qu'elle contient."""
    lignes = []
    prefixe = "  " + ("  │  " * indent)
    valeur_str = _formater_valeur(etape.valeur, etape.unite)

    # Ligne principale : code + valeur + label
    lignes.append(f"{prefixe}├─ {etape.code:<32} {valeur_str}")
    lignes.append(f"{prefixe}│    « {etape.label} »")

    # Doctrine refs résolues
    if etape.doctrine_refs:
        for ref in etape.doctrine_refs:
            try:
                valeur_doctrinale = resoudre_doctrine_ref(ref)
                valeur_utilisee = etape.hypotheses.get(ref)
                if valeur_utilisee is not None and valeur_utilisee != valeur_doctrinale:
                    lignes.append(
                        f"{prefixe}│    ⚠ doctrine {ref}={valeur_doctrinale} "
                        f"(valeur appliquée: {valeur_utilisee} — override)"
                    )
                else:
                    lignes.append(
                        f"{prefixe}│    doctrine: {ref}={valeur_doctrinale}"
                    )
            except AttributeError:
                lignes.append(
                    f"{prefixe}│    ⚠ doctrine: {ref} (référence introuvable)"
                )

    # Hypothèses chiffrées non-rattachées à une doctrine_ref
    hyp_orphelines = {
        k: v for k, v in etape.hypotheses.items()
        if k not in etape.doctrine_refs
    }
    if hyp_orphelines:
        for k, v in hyp_orphelines.items():
            lignes.append(f"{prefixe}│    hypothèse: {k} = {v}")

    # Notes
    if etape.notes:
        lignes.append(f"{prefixe}│    note: {etape.notes}")

    return lignes


# ============================================================
# RENDU DE LA TRACE COMPLÈTE
# ============================================================
def rendre_trace_console(trace: TraceAudit, _niveau: int = 0) -> str:
    """Produit la représentation textuelle complète d'une trace d'audit.

    À partir de la spec 1.1.0 (G3a), si la trace contient des sous-traces
    (`trace.sous_traces`), elles sont rendues récursivement, avec un
    en-tête indiquant le nom d'attachement et le régime de la sous-trace.

    Args:
        trace: La TraceAudit à formater.
        _niveau: Profondeur de récursion interne (usage interne, ne pas
            spécifier à l'appel principal).

    Returns:
        Chaîne multi-lignes prête à être affichée ou loggée.
    """
    lignes = []
    sep_principal = "=" if _niveau == 0 else "─"
    indent_externe = "  " * _niveau

    lignes.append(indent_externe + sep_principal * 80)
    titre = f"AUDIT — Régime {trace.regime}"
    if _niveau > 0:
        titre = f"SOUS-TRACE — {trace.regime}"
    lignes.append(f"{indent_externe}  {titre}")
    if _niveau == 0:
        lignes.append(f"{indent_externe}  Spec version : {trace.spec_version}")
    if trace.profil_resume:
        lignes.append(f"{indent_externe}  Profil : {trace.profil_resume}")
    lignes.append(indent_externe + sep_principal * 80)
    lignes.append("")

    def _rendre_branche(etape: EtapeAudit, profondeur: int):
        for ligne in _rendre_etape(etape, indent=profondeur):
            lignes.append(indent_externe + ligne)
        for enfant in trace.enfants(etape.code):
            _rendre_branche(enfant, profondeur + 1)

    for racine in trace.racines():
        _rendre_branche(racine, 0)

    # Pied de la trace courante
    lignes.append("")
    lignes.append(indent_externe + "─" * 80)
    profondeur_max = max(
        (_profondeur(trace, e) for e in trace.etapes), default=0
    )
    lignes.append(
        f"{indent_externe}  Total étapes : {len(trace.etapes)}  "
        f"(racines: {len(trace.racines())}, "
        f"profondeur max : {profondeur_max})"
    )

    # Rendu récursif des sous-traces attachées (spec 1.1.0)
    if trace.sous_traces:
        lignes.append("")
        lignes.append(indent_externe + f"  Sous-traces attachées ({len(trace.sous_traces)}) :")
        for nom in trace.noms_sous_traces():
            sub = trace.get_sous_trace(nom)
            lignes.append("")
            lignes.append(indent_externe + f"  ┌── nom d'attachement : {nom!r}")
            lignes.append(rendre_trace_console(sub, _niveau=_niveau + 1))

    return "\n".join(lignes)


def _profondeur(trace: TraceAudit, etape: EtapeAudit) -> int:
    """Calcule la profondeur d'une étape (0 = racine)."""
    p = 0
    courante = etape
    while courante.parent_id is not None:
        parent = trace.get(courante.parent_id)
        if parent is None:
            break  # parent_id orphelin (anomalie, ne devrait pas arriver)
        p += 1
        courante = parent
    return p


__all__ = [
    "rendre_trace_console",
]
