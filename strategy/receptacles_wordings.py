"""
strategy/receptacles_wordings.py — Wordings centralisés du module réceptacles v1.1.

Implémente la décision **D-R3** de `ARCHITECTURE_RECEPTACLES.md` §5 :

    Tous les wordings d'hypothèses ≥ 80 chars (SEUIL_HYPOTHESE_LONGUE)
    utilisés par les modules `strategy/receptacles_*.py` sont définis
    exclusivement ici. Zéro wording inline dans les modules métier.

Convention de nommage (§5.2) :

    WORDING_<ENVELOPPE>_<CONCEPT>      pour les wordings spécifiques à une enveloppe
    WORDING_REC_<CONCEPT>              pour les wordings transverses

Justifications de l'approche centralisée :

    1. **Stabilité des goldens PDF** (SP11) : modifier un wording change
       directement les snapshots `golden_receptacles.json`. Centraliser
       garantit que la mise à jour est consciente et localisée.
    2. **Versionnement** : chaque wording est implicitement versionné par
       la version du module v1.1.0. Toute évolution rédactionnelle suit
       le rituel `--update` du script goldens.
    3. **Mutualisation** : les modules PERIN / PEE / PERECO partagent
       certaines mentions (convention rendement, primauté cabinet).
    4. **Audit** : un seul fichier à relire pour valider tous les wordings
       cabinet du module réceptacles.

Périmètre SP14 : ce fichier est créé en SP14 avec **uniquement** le
wording transverse `WORDING_REC_CONVENTION_RENDEMENT` figé (cf.
`ARCHITECTURE_RECEPTACLES.md` §7.2). Les wordings spécifiques à chaque
enveloppe (`WORDING_PERIN_*`, `WORDING_PEE_*`, `WORDING_PERECO_*`)
seront ajoutés progressivement par les sous-passes SP15-SP17.

Référence doctrinale : `ARCHITECTURE_RECEPTACLES.md` §3 (vocabulaire
verrouillé) et §5 (wordings centralisés).
"""

# ============================================================
# CONSTANTES TRANSVERSES (figées SP14)
# ============================================================

# Hypothèse de rendement conventionnelle (D-R8).
# Toute modification de ce wording change le golden réceptacles —
# acte conscient via `--update`.
WORDING_REC_CONVENTION_RENDEMENT = (
    "Les projections présentées reposent sur une hypothèse "
    "conventionnelle de rendement nominal annuel de 2 %, capitalisé "
    "annuellement et identique pour toutes les enveloppes comparées. "
    "Cette convention permet une comparaison directionnelle entre "
    "enveloppes sur des bases homogènes. Elle n'a pas vocation à "
    "représenter un rendement attendu ni à constituer une projection "
    "patrimoniale. La performance réelle dépendra des supports "
    "sélectionnés, des frais effectifs et du contexte de marché. Le "
    "cabinet apprécie la pertinence des hypothèses au cas par cas."
)

# Disclaimer de comparabilité inter-enveloppes (cadrage v1.1).
# Présent systématiquement dans la trace racine du module réceptacles
# pour rappeler que les 3 enveloppes ont des logiques fiscales et
# sociales différentes ; la comparaison se fait sur des bases
# homogénéisées par convention, pas par équivalence stricte.
WORDING_REC_DISCLAIMER_COMPARABILITE = (
    "Les 3 enveloppes comparées (PERIN, PEE, PERECO) ont des logiques "
    "fiscales et sociales différentes : conditions d'accès, plafonds, "
    "déductibilité à l'entrée, fiscalité à la sortie, conditions de "
    "déblocage. La comparaison est effectuée sur des bases "
    "homogénéisées par convention afin d'éclairer le cabinet sur les "
    "ordres de grandeur. Elle n'a pas vocation à se substituer à "
    "l'analyse cabinet, qui apprécie au cas par cas la pertinence "
    "réelle de chaque enveloppe pour le profil considéré."
)

# Disclaimer absence de dimensionnement (D-R12).
# Rappelle que le module est un comparateur et non un dimensionneur ;
# le flux à allouer est fourni en input, pas calculé.
WORDING_REC_DISCLAIMER_PERIMETRE = (
    "Le module v1.1 effectue une comparaison entre enveloppes pour un "
    "flux donné en input. Il ne dimensionne pas le flux à verser et "
    "ne propose pas d'allocation cabinet. Les questions de "
    "dimensionnement du versement, de stratégie patrimoniale globale "
    "et d'arbitrage cross-enveloppes appartiennent au cabinet, qui "
    "intègre des paramètres hors périmètre du présent calcul."
)


# ============================================================
# PLACEHOLDERS POUR SOUS-PASSES SP15-SP17
# ============================================================
# Les sections suivantes seront complétées progressivement.
# Chaque ajout suit la convention WORDING_<ENVELOPPE>_<CONCEPT> et
# devient automatiquement disponible aux modules métier qui
# l'importent explicitement.

# --- PERIN (SP15) -------------------------------------------
# 4 wordings figés SP15. Le wording sortie en rente est hors périmètre
# SP15 (Q1=b : sortie capital uniquement). Sera ajouté en SP18 ou v1.2
# si le périmètre est étendu.

WORDING_PERIN_REGLE_PLAFOND = (
    "Le plafond annuel PERIN est égal au plus élevé des deux montants "
    "suivants : 10 % des revenus professionnels nets de l'année N-1 "
    "dans la limite de 8 PASS, ou 10 % du PASS de l'année N-1. "
    "Référence : CGI art. 154 bis. Le plafond peut être augmenté par "
    "rattrapage des plafonds non utilisés des 3 années précédentes, "
    "hors périmètre v1.1."
)

WORDING_PERIN_DEDUCTIBILITE_IR_ENTREE = (
    "Les versements volontaires sur un PERIN sont déductibles du "
    "revenu net global imposable à l'IR, dans la limite du plafond "
    "annuel applicable. L'économie fiscale immédiate dépend de la "
    "tranche marginale d'imposition (TMI) du foyer fiscal. Plus la "
    "TMI est élevée, plus l'effort réel est faible — le PERIN est "
    "donc particulièrement adapté aux TMI élevées. Référence : CGI "
    "art. 163 quatervicies."
)

WORDING_PERIN_FISCALITE_SORTIE_CAPITAL = (
    "À la sortie en capital, les sommes correspondant aux versements "
    "déduits à l'entrée sont soumises à l'IR au barème progressif "
    "(reprises dans le revenu global) ; les gains sont soumis au "
    "prélèvement forfaitaire unique (PFU) au taux global de 30 % "
    "(12,8 % IR + 17,2 % prélèvements sociaux). Aucun abattement "
    "spécifique ne s'applique. Pour une sortie partielle, le "
    "traitement est appliqué proratisé. Référence : CGI art. 158."
)

WORDING_PERIN_DISPONIBILITE_RETRAITE = (
    "Le PERIN est un produit retraite : les sommes versées sont "
    "bloquées jusqu'à la date de liquidation effective de la retraite "
    "du titulaire. Cas de déblocage anticipé limitativement énumérés "
    "par la loi : invalidité 2e/3e catégorie du titulaire ou conjoint, "
    "décès du conjoint, surendettement, expiration des droits chômage, "
    "cessation d'activité non salariée suite à liquidation judiciaire, "
    "acquisition de la résidence principale. Référence : C. monétaire "
    "et financier art. L224-4."
)


# --- PEE (SP16) ---------------------------------------------
# 4 wordings figés SP16. Le wording cas de déblocage anticipé reste
# hors périmètre v1.1 (Q7=a : on suppose tous les horizons ≥ 5 ans,
# pas de simulation de déblocage anticipé).

WORDING_PEE_ABONDEMENT_EMPLOYEUR = (
    "Le PEE permet à l'employeur d'abonder les versements volontaires "
    "du salarié, dans la limite légale de 8 % du PASS (3 844,80 € en "
    "2026), avec un plafond complémentaire fixé à 3 fois le versement "
    "individuel. L'abondement constitue un avantage économique direct "
    "du salarié : il augmente le capital reçu sans contrepartie de "
    "versement. Côté employeur, l'abondement est exonéré de "
    "cotisations sociales patronales (hors forfait social) et "
    "déductible du bénéfice imposable. Référence : Code du travail "
    "art. L3332-11."
)

WORDING_PEE_CSG_CRDS_ABONDEMENT = (
    "L'abondement employeur versé sur le PEE est assujetti à la CSG et "
    "à la CRDS au taux global de 9,7 % (CSG 9,2 % + CRDS 0,5 %), "
    "prélevées à la source par l'employeur. Cette retenue diminue le "
    "montant effectivement crédité sur le PEE par rapport à "
    "l'abondement brut. C'est un frottement social explicite que le "
    "présent calcul retient dans le flux entrant net. Référence : Code "
    "de la sécurité sociale art. L136-1 et L136-2."
)

WORDING_PEE_DISPONIBILITE_5ANS = (
    "Les sommes versées sur le PEE (versement salarié + abondement) "
    "sont indisponibles pendant 5 ans à compter de chaque versement. "
    "Passé ce délai, la sortie est libre, sans condition d'âge ni de "
    "situation. Avant 5 ans, des cas légaux de déblocage anticipé "
    "existent (mariage/PACS, naissance 3e enfant, divorce, invalidité, "
    "décès, surendettement, acquisition résidence principale, "
    "cessation contrat de travail, etc.) mais leur traitement détaillé "
    "est hors périmètre v1.1. Référence : Code du travail art. R3324-22."
)

WORDING_PEE_EXONERATION_PV_SORTIE = (
    "À la sortie au-delà de 5 ans, les sommes correspondant aux "
    "versements et à l'abondement sont disponibles en franchise d'IR "
    "(elles ont déjà supporté les prélèvements sociaux à l'entrée pour "
    "l'abondement ; les versements salariés provenaient de revenus "
    "déjà nets d'IR). Les gains acquis pendant la phase d'épargne "
    "sont soumis aux prélèvements sociaux au taux de 17,2 %, sans IR "
    "complémentaire. C'est cette exonération d'IR sur les gains qui "
    "constitue le principal avantage fiscal du PEE à la sortie. "
    "Référence : CGI art. 81 bis."
)


# --- PERECO (SP17) ------------------------------------------
# 4 wordings figés SP17. Le PERECO est hybride : il combine la
# déductibilité IR du PERIN (versements volontaires) et l'abondement
# employeur du PEE. Les wordings reflètent cette double logique.

WORDING_PERECO_DEDUCTIBILITE_IR_ENTREE = (
    "Les versements volontaires du salarié sur le PERECO sont "
    "déductibles du revenu net global imposable à l'IR, dans la "
    "limite du plafond annuel du titulaire (identique au plafond "
    "PERIN, art. 154 bis du CGI). L'économie fiscale immédiate "
    "dépend de la tranche marginale d'imposition (TMI) du foyer. "
    "Cette déductibilité distingue le PERECO du PEE classique. "
    "Référence : CGI art. 163 quatervicies (titre 3 du PER)."
)

WORDING_PERECO_ABONDEMENT_EMPLOYEUR = (
    "L'employeur peut abonder les versements volontaires du salarié "
    "sur le PERECO, dans la limite légale de 16 % du PASS pour le "
    "PERECO (soit 7 689,60 € en 2026, plafond plus élevé que celui "
    "du PEE), avec un plafond complémentaire fixé à 3 fois le "
    "versement individuel. v1.1 retient le plafond simple de 8 % "
    "PASS (3 844,80 €) par cohérence avec le PEE — le plafond 16 % "
    "PASS spécifique PERECO sera modélisé en v1.2 si validé. Côté "
    "employeur, l'abondement est déductible du bénéfice imposable "
    "et exonéré de cotisations patronales (hors forfait social). "
    "Référence : Code monétaire et financier art. L224-13."
)

WORDING_PERECO_CSG_CRDS_ABONDEMENT = (
    "Comme pour le PEE, l'abondement employeur versé sur le PERECO "
    "est assujetti à la CSG et à la CRDS au taux global de 9,7 %, "
    "prélevées à la source par l'employeur. Cette retenue diminue le "
    "montant effectivement crédité par rapport à l'abondement brut. "
    "Référence : Code de la sécurité sociale art. L136-1 et L136-2."
)

WORDING_PERECO_FISCALITE_SORTIE_CAPITAL = (
    "À la sortie en capital, les sommes correspondant aux versements "
    "déduits à l'entrée sont reprises dans le revenu global et "
    "imposées à l'IR au barème progressif (logique identique au "
    "PERIN). Les gains sont soumis au prélèvement forfaitaire unique "
    "(PFU) au taux global de 30 % (12,8 % IR + 17,2 % PS). "
    "L'abondement employeur, déjà fiscalisé à l'entrée (CSG-CRDS), "
    "suit le même régime que les versements pour la part principale, "
    "et les gains attachés au PFU. Référence : CGI art. 158."
)

WORDING_PERECO_DISPONIBILITE_RETRAITE = (
    "Comme le PERIN, le PERECO est un produit retraite : les sommes "
    "(versement salarié + abondement) sont bloquées jusqu'à la "
    "liquidation effective de la retraite. Cas de déblocage anticipé "
    "limitativement énumérés par la loi : invalidité 2e/3e catégorie, "
    "décès du conjoint, surendettement, expiration droits chômage, "
    "cessation activité non salariée suite à liquidation judiciaire, "
    "acquisition résidence principale. Référence : Code monétaire et "
    "financier art. L224-4."
)


# === Wordings PERO (SP24) ===
# Ajoutés par SP24 sans modification des 16 wordings existants
# (cf. directive R2 « aucune réouverture SP1→SP23-bis »).
# 5 wordings réglementaires + 1 wording de simplification de
# simulation (B-Q1=β : simplification capital doctrinalement marquée).

WORDING_PERO_REGLE_COTISATION = (
    "Le PERO est financé par une cotisation employeur exprimée en "
    "pourcentage du salaire brut du salarié-dirigeant assimilé. "
    "Cette cotisation est due au titre d'une catégorie objective "
    "de salariés définie par accord d'entreprise, décision "
    "unilatérale de l'employeur ou convention collective. "
    "L'éligibilité du dirigeant assimilé salarié dépend de son "
    "appartenance à cette catégorie objective. "
    "Référence : Code monétaire et financier art. L224-23."
)

WORDING_PERO_CSG_CRDS_COTISATION = (
    "La cotisation employeur PERO est assujettie à la CSG et à la "
    "CRDS au taux global de 9,7 %, prélevées sur le salarié (et non "
    "sur l'employeur). Cette retenue constitue le seul flux sortant "
    "immédiat du salarié au titre du PERO : le salarié ne réalise "
    "pas de versement volontaire dans le périmètre v1.3 retenu. "
    "Référence : Code de la sécurité sociale art. L136-1 et L136-2."
)

WORDING_PERO_FORFAIT_SOCIAL_EMPLOYEUR = (
    "Côté employeur, la cotisation PERO est soumise au forfait social "
    "au taux applicable aux régimes de retraite supplémentaire "
    "obligatoires d'entreprise. v1.3 retient le taux conventionnel "
    "de 16 % (valeur doctrinale France 2026, à confirmer selon "
    "réglementation en vigueur). Le coût entreprise total est donc "
    "la cotisation majorée du forfait social. "
    "Référence : Code de la sécurité sociale art. L137-15."
)

WORDING_PERO_ECONOMIE_FISCALE_ENTREE = (
    "La cotisation employeur PERO n'entre pas dans le revenu "
    "imposable du salarié (exonération à l'entrée dans la limite "
    "globale PEE/PERECO/PERO de 8 % de la rémunération brute "
    "annuelle, plafonnée à 8 PASS). L'économie fiscale immédiate "
    "du salarié est calculée comme partie exonérée × TMI. Cette "
    "économie est conceptuellement distincte de celle du PERIN "
    "(qui repose sur une déduction du revenu imposable du "
    "versement individuel). "
    "Référence : CGI art. 83 2°."
)

WORDING_PERO_DISPONIBILITE_RETRAITE = (
    "Le PERO est un produit retraite : les sommes capitalisées sont "
    "bloquées jusqu'à la liquidation effective de la retraite, hors "
    "cas légaux de déblocage anticipé. Cas légaux génériques PER : "
    "invalidité 2e/3e catégorie, décès du conjoint, surendettement, "
    "expiration droits chômage, cessation activité non salariée "
    "suite à liquidation judiciaire. Le cas « acquisition résidence "
    "principale » est typiquement exclu pour la fraction issue de "
    "cotisations obligatoires. Référence : Code monétaire et "
    "financier art. L224-4 et L224-23."
)

WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL = (
    "Note de simulation : la valeur nette projetée du PERO est "
    "calculée en sortie capital, par cohérence et comparabilité "
    "avec les autres enveloppes du périmètre (PERIN, PEE, PERECO). "
    "Le PERO est en réalité servi principalement en rente viagère. "
    "La fiscalité de rente (imposition au barème progressif sur "
    "les arrérages) n'est pas modélisée v1.3. La projection capital "
    "présentée doit donc être lue comme une simulation comparative, "
    "non comme une restitution du flux de rente réel."
)


__all__ = [
    # Transverses (SP14)
    "WORDING_REC_CONVENTION_RENDEMENT",
    "WORDING_REC_DISCLAIMER_COMPARABILITE",
    "WORDING_REC_DISCLAIMER_PERIMETRE",
    # PERIN (SP15)
    "WORDING_PERIN_REGLE_PLAFOND",
    "WORDING_PERIN_DEDUCTIBILITE_IR_ENTREE",
    "WORDING_PERIN_FISCALITE_SORTIE_CAPITAL",
    "WORDING_PERIN_DISPONIBILITE_RETRAITE",
    # PEE (SP16)
    "WORDING_PEE_ABONDEMENT_EMPLOYEUR",
    "WORDING_PEE_CSG_CRDS_ABONDEMENT",
    "WORDING_PEE_DISPONIBILITE_5ANS",
    "WORDING_PEE_EXONERATION_PV_SORTIE",
    # PERECO (SP17)
    "WORDING_PERECO_DEDUCTIBILITE_IR_ENTREE",
    "WORDING_PERECO_ABONDEMENT_EMPLOYEUR",
    "WORDING_PERECO_CSG_CRDS_ABONDEMENT",
    "WORDING_PERECO_FISCALITE_SORTIE_CAPITAL",
    "WORDING_PERECO_DISPONIBILITE_RETRAITE",
    # PERO (SP24)
    "WORDING_PERO_REGLE_COTISATION",
    "WORDING_PERO_CSG_CRDS_COTISATION",
    "WORDING_PERO_FORFAIT_SOCIAL_EMPLOYEUR",
    "WORDING_PERO_ECONOMIE_FISCALE_ENTREE",
    "WORDING_PERO_DISPONIBILITE_RETRAITE",
    "WORDING_PERO_SIMPLIFICATION_SORTIE_CAPITAL",
]
