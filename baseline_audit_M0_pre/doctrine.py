"""
DOCTRINE MÉTIER CENTRALISÉE — Référentiel unique des hypothèses.

Réponse aux 3 sujets critiques identifiés :
1. Gouvernance des hypothèses (centralisation, versionning, documentation)
2. Doctrine métier unique (référentiel commun PERO/dividendes/charges/PFU/...)
3. Niveau de confiance affiché par module

Ce fichier est la SOURCE UNIQUE DE VÉRITÉ pour toutes les hypothèses métier.
Toute divergence entre modules doit être résolue ici.

Date de référence : 01/01/2026.
Version doctrine : 1.0.0
"""

from dataclasses import dataclass
from enum import Enum


# ============================================================
# VERSIONNING DOCTRINE
# ============================================================
DOCTRINE_VERSION = "1.0.1"
DOCTRINE_DATE = "2026-05-01"
DOCTRINE_AUTEUR = "Équipe produit Cabinet"

# Historique des versions (à compléter à chaque évolution)
DOCTRINE_HISTORIQUE = [
    {
        "version": "1.0.0",
        "date": "2026-01-01",
        "changements": "Version initiale - Phase A complète + B.1 livrée",
    },
    {
        "version": "1.0.1",
        "date": "2026-05-01",
        "changements": (
            "Introduction des limites méthodologiques explicites, principe de "
            "primauté cabinet, et renommage du niveau de précision « Déclaratif » "
            "en « Conformité renforcée ». Ajout de la colonne « Niveau de vigilance » "
            "dans le tableau URSSAF. Section « Ce que l'outil ne fait pas » et "
            "disclaimer AMF Comparateur patrimonial. Harmonisation vocabulaire "
            "(cadre méthodologique, efficience)."
        ),
    },
]


# ============================================================
# NIVEAU DE CONFIANCE PAR MODULE
# ============================================================
class NiveauConfiance(Enum):
    """
    Niveau de confiance affiché à l'utilisateur.

    - CONFORMITE_RENFORCEE : modules calibrés sur les règles fiscales et sociales
      applicables au 01/01/2026 (CEHR, CDHR, plafonnement QF). Précision suffisante
      pour la préparation d'éléments déclaratifs, SOUS VALIDATION CABINET.
    - AVANCE     : modèle complet (consolidation des modules détaillés)
    - CADRAGE    : modèle simplifié pour comparaison rapide
    - INDICATIF  : projection avec hypothèses externes (rendements, fiscalité future)

    Note : l'ancien nom "DECLARATIF" est conservé comme alias transitoire pour
    rétro-compatibilité. Il ne doit plus être affiché côté utilisateur.
    """
    CONFORMITE_RENFORCEE = "Conformité renforcée"
    AVANCE = "Avancé"
    CADRAGE = "Cadrage"
    INDICATIF = "Indicatif"


# Alias transitoire pour rétro-compatibilité code (ne PAS afficher utilisateur)
NiveauConfiance.DECLARATIF = NiveauConfiance.CONFORMITE_RENFORCEE


# Niveau par module
NIVEAU_PAR_MODULE = {
    "TNS": NiveauConfiance.CONFORMITE_RENFORCEE,
    "Libéral": NiveauConfiance.CONFORMITE_RENFORCEE,
    "Salarié": NiveauConfiance.CONFORMITE_RENFORCEE,
    "Assimilé salarié": NiveauConfiance.CONFORMITE_RENFORCEE,
    "Comparateur dispositifs": NiveauConfiance.AVANCE,
    "Synthèse dirigeant": NiveauConfiance.AVANCE,
    "Scénarios A vs B": NiveauConfiance.CADRAGE,
    "Comparateur patrimonial": NiveauConfiance.INDICATIF,
    "Projection 5 ans": NiveauConfiance.INDICATIF,
}

# Description longue par niveau (affichage utilisateur)
DESCRIPTION_NIVEAU = {
    NiveauConfiance.CONFORMITE_RENFORCEE: (
        "Modules calibrés sur les règles fiscales et sociales applicables au "
        "01/01/2026. Inclut CEHR, CDHR, plafonnement QF et quatre cas particuliers. "
        "Précision suffisante pour la préparation des obligations fiscales, sous "
        "validation cabinet."
    ),
    NiveauConfiance.AVANCE: (
        "Modèle complet consolidant les modules détaillés. Lecture consolidée "
        "prudente des plafonds sociaux. Adapté à l'arbitrage stratégique et à la "
        "formalisation de la mission cabinet."
    ),
    NiveauConfiance.CADRAGE: (
        "Outil de cadrage stratégique. Modèle simplifié (sans CEHR, CDHR ni "
        "plafonnement QF) destiné à comparer rapidement plusieurs équilibres. "
        "Pour les calculs destinés aux obligations fiscales, utiliser les "
        "modules de conformité renforcée."
    ),
    NiveauConfiance.INDICATIF: (
        "Projection indicative. Reposant sur des hypothèses externes (rendements, "
        "fiscalité future, durée de placement), à ajuster selon le contexte du "
        "dossier. Ne constitue pas un engagement de performance."
    ),
}


# ============================================================
# DOCTRINE MÉTIER — Sujets transverses
# ============================================================
@dataclass
class RefDoctrine:
    """Référence documentaire d'une règle métier."""
    regle: str
    source_legale: str
    valeur: str
    note: str = ""


DOCTRINE_PERO = [
    RefDoctrine(
        "Forfait social PERO obligatoire",
        "Loi PACTE 2019, CSS L137-15-1",
        "8 %",
        "Taux retenu pour les versements employeur sur PERO. "
        "Paramètre expert modifiable dans le moteur si évolution.",
    ),
    RefDoctrine(
        "Plafond cumul abondements (PEE + PERECO + PERO)",
        "Lecture consolidée prudente URSSAF 2024",
        "16 % PASS = 7 689,60 €",
        "Lecture la plus prudente — sécurise les simulations face à un "
        "contrôle URSSAF. À documenter en cabinet selon doctrine choisie.",
    ),
    RefDoctrine(
        "Catégorie objective éligible",
        "CSS L911-1, Décret 2012-25",
        "Toggle utilisateur",
        "Le PERO doit s'appliquer à une catégorie homogène (cadres ou "
        "équivalent). L'utilisateur certifie l'éligibilité du dirigeant.",
    ),
    RefDoctrine(
        "CSG/CRDS sur cotisation PERO",
        "CSS L136-1",
        "9,7 % sur le brut",
        "À la charge du bénéficiaire, sur le montant brut versé.",
    ),
    RefDoctrine(
        "Incompatibilité PERO + régime TNS",
        "Article 83 CGI",
        "PERO réservé aux salariés et assimilés salariés",
        "Le moteur désactive automatiquement le PERO en régime TNS.",
    ),
]


DOCTRINE_DIVIDENDES = [
    RefDoctrine(
        "PFU global (Flat Tax)",
        "CGI 200 A",
        "31,40 % (12,80 % IR + 17,20 % PS)",
        "Régime de droit commun pour les dividendes.",
    ),
    RefDoctrine(
        "Seuil dividendes TNS soumis cotisations",
        "Art. L131-6 CSS",
        "10 % du capital social + primes + CCA",
        "Au-delà du seuil, fraction soumise aux cotisations TNS (45 %).",
    ),
    RefDoctrine(
        "IR sur fraction TNS-imposée",
        "Convention v19 reproduite",
        "Approximation au TMI marginal",
        "Le moteur reproduit la simplification v19. Limite : ne capte pas "
        "le passage de tranche induit par les dividendes additionnels.",
    ),
]


DOCTRINE_CHARGES = [
    RefDoctrine(
        "Taux patronal moyen",
        "Indicatif PME 2026",
        "42 %",
        "Moyenne indicative. À ajuster par bulletin de paie en cabinet.",
    ),
    RefDoctrine(
        "Taux salarial moyen",
        "Indicatif PME 2026",
        "12 %",
        "Moyenne indicative. À ajuster par bulletin de paie en cabinet.",
    ),
    RefDoctrine(
        "CSG/CRDS revenus d'activité",
        "CSS L136-1, L136-8",
        "9,7 % (sur assiette 98,25 % du brut)",
        "Taux 2026.",
    ),
    RefDoctrine(
        "Forfait social participation < 50 salariés",
        "Loi PACTE 2019",
        "0 %",
        "Exonération totale.",
    ),
    RefDoctrine(
        "Forfait social PERECO",
        "Loi PACTE 2019",
        "0 %",
        "Universellement exonéré jusqu'à fin 2027. Vérifier prorogation 2028.",
    ),
]


DOCTRINE_RETRAITE = [
    RefDoctrine(
        "PERIN - plafond déduction",
        "CGI 163 quatervicies",
        "10 % rev. pro. N-1 (min 10 % PASS, max 8 PASS)",
        "Mutualisable entre conjoints — non modélisé en v1 (cible bénéficiaire-type).",
    ),
    RefDoctrine(
        "PEE - durée de blocage",
        "CSS L3332-25",
        "5 ans",
        "Sortie anticipée possible sur cas limitatifs (mariage, naissance, achat RP...).",
    ),
    RefDoctrine(
        "PERECO - durée de blocage",
        "CSS L3334-1 (ex-PERCO)",
        "Jusqu'à la retraite",
        "Sortie en capital ou rente. Cas de déblocage anticipé encadrés.",
    ),
    RefDoctrine(
        "Article 83 historique",
        "Non modélisé",
        "Encours non traités",
        "Seuls les FLUX PERO post-2019 sont modélisés. Les contrats art. 83 "
        "antérieurs (transférés ou en sommeil) ne sont pas modélisés en v1.",
    ),
]


DOCTRINE_URSSAF = [
    RefDoctrine(
        "Plafond annuel exonération CESU",
        "CSS L7233-4",
        "2 540 € par an et par salarié",
        "Préfinancé par l'employeur, services à la personne.",
    ),
    RefDoctrine(
        "Tickets restaurant - part employeur exonérée",
        "Arrêté 31/12/2023",
        "7,26 €/titre, dans la limite de 60 % de la valeur faciale",
        "Valeur 2026 indicative.",
    ),
    RefDoctrine(
        "Chèques cadeaux & vacances - tolérance URSSAF",
        "Tolérance administrative",
        "Plafond 5 % PASS = 2 403 €",
        "Tolérance URSSAF par événement (Noël, naissance, etc.).",
    ),
    RefDoctrine(
        "Cashback corporate",
        "Position cabinet à documenter",
        "Flux pouvoir d'achat hors lien de subordination",
        "Mode 'Conforme' = souscription nominative + documentation. "
        "Mode 'Standard' = provision URSSAF 30 % recommandée.",
    ),
]


DOCTRINE_PATRIMONIAL = [
    RefDoctrine(
        "Rendement cash défensif",
        "Hypothèse projection",
        "2 % par an",
        "Pour la fraction non capitalisable du gain. Modifiable côté UI.",
    ),
    RefDoctrine(
        "Rendement épargne salariale & PER",
        "Hypothèse projection",
        "4 % par an",
        "Pour la fraction capitalisable. Modifiable côté UI.",
    ),
    RefDoctrine(
        "Rendement comparateur patrimonial",
        "Hypothèse projection",
        "5 % par an par défaut (ajustable)",
        "Appliqué uniformément aux 4 enveloppes pour comparaison fiscale pure.",
    ),
    RefDoctrine(
        "Capitalisation",
        "Convention de calcul",
        "Annuelle composée, versement en début d'année",
        "Formule : Capital × ((1+r)^n - 1) / r × (1+r).",
    ),
    RefDoctrine(
        "Abattement assurance-vie après 8 ans",
        "CGI 125-0 A",
        "4 600 € (célib) / 9 200 € (couple)",
        "Sur les produits, par an et par foyer fiscal.",
    ),
]


# ============================================================
# DOCTRINE COMPLÈTE — Vue agrégée
# ============================================================
DOCTRINE_COMPLETE = {
    "PERO et architecture de réceptacle": DOCTRINE_PERO,
    "Dividendes et fiscalité distributive": DOCTRINE_DIVIDENDES,
    "Charges sociales et forfaits": DOCTRINE_CHARGES,
    "Retraite et épargne longue": DOCTRINE_RETRAITE,
    "URSSAF et avantages exonérés": DOCTRINE_URSSAF,
    "Projection patrimoniale": DOCTRINE_PATRIMONIAL,
}


def afficher_doctrine() -> str:
    """Génère un texte structuré de toute la doctrine pour affichage UI."""
    lignes = [
        f"DOCTRINE MÉTIER — Version {DOCTRINE_VERSION} (mise à jour {DOCTRINE_DATE})",
        "",
        "Référentiel centralisé de toutes les hypothèses métier appliquées par le moteur.",
        "",
    ]
    for theme, refs in DOCTRINE_COMPLETE.items():
        lignes.append(f"━━━ {theme.upper()} ━━━")
        for r in refs:
            lignes.append(f"  • {r.regle}")
            lignes.append(f"      Valeur : {r.valeur}")
            lignes.append(f"      Source : {r.source_legale}")
            if r.note:
                lignes.append(f"      Note   : {r.note}")
            lignes.append("")
    return "\n".join(lignes)


# ============================================================
# REGISTRE DES CAS TESTS (gouvernance QA)
# ============================================================
REGISTRE_CAS_TESTS = {
    "TNS": {
        "Cas 1 - défaut v19": "rém 70k, marié 2 parts, capital 100k, div 50k",
        "Cas 2 - célibataire TMI 30%": "rém 60k, capital 50k, div 10k",
        "Cas 3 - marié 4 parts revenu élevé": "rém 150k, capital 200k, div 30k",
        "Cas 4 - foyer riche CEHR potentielle": "rém 400k, div hors env. 50k",
        "Cas 5 - CDHR plancher 20%": "rém 180k, div hors env. 200k",
        "Cas 6 - dividendes sous seuil 10%": "rém 80k, capital 300k, div 20k",
    },
    "Libéral": {
        "Cas 1 - défaut v19": "BNC 150k, frais 30k, marié 2 parts",
        "Cas 2 - BNC faible revenu": "BNC 80k célibataire 1 part",
        "Cas 3 - BNC marié 3 parts": "BNC 200k, autres rev 30k",
        "Cas 4 - haut revenu CEHR": "BNC 600k, div hors env. 100k",
        "Cas 5 - célibataire CDHR": "BNC 500k, div hors env. 250k",
        "Cas 6 - SEL double couche": "Bénéfice 500k, rém 120k",
    },
    "Salarié": {
        "Cas 1 - défaut v19": "brut 60k marié 2 parts",
        "Cas 2 - bas salaire célibataire": "brut 35k célibataire",
        "Cas 3 - marié 4 parts": "brut 80k autres rev 25k",
        "Cas 4 - cadre supérieur": "brut 200k abattement plafonné",
        "Cas 5 - très haut CEHR": "brut 350k célibataire + div 150k",
        "Cas 6 - couple CDHR": "brut 150k + div hors env. 400k",
    },
    "Comparateur Option 2": {
        "Test 1 - parité v19 stricte": "PEE seul sans PERO",
        "Test 2 - PERECO extension PACTE": "Substitution forfait social",
        "Test 3 - PERO Option 2": "Dirigeant éligible",
    },
    "Synthèse dirigeant": {
        "Test 1 - Stratégie C": "Cas par défaut, validations radar",
        "Test 2 - Stratégie A": "Référence pure, aucun dispositif",
        "Test 3 - Stratégie D + PERO": "Avec forfaits personnalisés",
    },
    "Scénarios A vs B": {
        "Cas 1 - stabilité": "2 scénarios identiques",
        "Cas 2 - arbitrage dividendes": "Avant/après distribution",
        "Cas 3 - inter-régimes": "Assimilé vs TNS",
        "Cas 4 - sensibilité enveloppe": "Variation salaire 100k vs 150k",
    },
}


def afficher_registre_qa() -> str:
    """Génère un texte structuré du registre QA pour affichage UI."""
    lignes = [
        f"REGISTRE DES CAS TESTS — Version {DOCTRINE_VERSION}",
        "",
        f"Total : {sum(len(v) for v in REGISTRE_CAS_TESTS.values())} cas tests"
        f" sur {len(REGISTRE_CAS_TESTS)} modules.",
        "",
    ]
    for module, cas in REGISTRE_CAS_TESTS.items():
        lignes.append(f"━━━ {module.upper()} ━━━")
        for nom, descr in cas.items():
            lignes.append(f"  • {nom} : {descr}")
        lignes.append("")
    return "\n".join(lignes)
