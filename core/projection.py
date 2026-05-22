"""
Core Engine — Projections de capitalisation temporelle.

Math pure de capitalisation annuelle composée. Indépendante de tout régime,
profil ou stratégie. Réutilisable par les modules Strategy (Synthèse,
Comparateur patrimonial, future Synthèse multi-régimes).

Module pivot : ne dépend d'aucun autre module métier (importe seulement
les rendements depuis core.profil).
"""

from core.profil import RDT_CASH, RDT_EPARGNE


def projection_5_ans(net_annuel: float, fraction_capitalisable: float = 0.0) -> list:
    """
    Projette un net annuel sur 5 ans avec capitalisation composée.

    Args:
        net_annuel: Montant net annuel à projeter (€)
        fraction_capitalisable: Part du net qui capitalise au rendement épargne
            (le reste capitalise au rendement cash défensif).
            Valeur entre 0 (tout en cash) et 1 (tout en épargne capitalisable).

    Returns:
        Liste des 5 valeurs cumulées (année 1 à année 5) en €.

    Formule de capitalisation : rente versée en début d'année.
        V(n) = net × [(1+r)^n - 1] / r × (1+r)

    Cas dégénéré rendement nul : projection linéaire (val = net × n).
    """
    rendement = (fraction_capitalisable * RDT_EPARGNE
                 + (1 - fraction_capitalisable) * RDT_CASH)
    projection = []
    for n in range(1, 6):
        if rendement > 0:
            val = net_annuel * ((1 + rendement) ** n - 1) / rendement * (1 + rendement)
        else:
            val = net_annuel * n
        projection.append(val)
    return projection
