# Outil d'arbitrage rémunération dirigeant — Prototype Streamlit

Transposition Python/Streamlit de l'outil Excel v19. Objectif : test EC sans exposer les formules.

## Statut prototype

- **Onglet couvert** : Arbitrage (4 stratégies à enveloppe constante)
- **Régime** : Assimilé salarié uniquement (SAS/SASU, SARL gérance min., SELAS)
- **Parité numérique vs v19** : 0,00 € d'écart sur le cas de référence (120 k€, marié, 2 parts, 11-49 salariés)

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

L'app s'ouvre sur http://localhost:8501.

## Déploiement Streamlit Community Cloud (production test)

1. Pousser ce dossier sur un repo GitHub privé (`outil-arbitrage-proto`)
2. Aller sur https://share.streamlit.io → New app → connecter le repo
3. Renseigner : main file = `app.py`, branche = `main`
4. Déploiement automatique en 30 secondes, URL publique : `https://<nom-app>.streamlit.app`
5. Pour restreindre l'accès aux EC du panel : Settings → Sharing → "Only specific people" → ajouter les emails Google des testeurs

Le moteur (`moteur.py`) et les paramètres fiscaux ne sont **jamais** envoyés au navigateur. Seuls les résultats (chiffres calculés) transitent vers l'interface.

## Architecture

```
proto/
├── app.py            # Interface Streamlit (sidebar + onglets + graphiques)
├── moteur.py         # Logique de calcul (référentiel + formules)
└── requirements.txt
```

`moteur.py` est conçu pour être testé indépendamment :
```bash
python moteur.py
```
exécute les tests de parité vs valeurs Excel v19.

## Prochaines étapes (si proto validé)

- v2 : ajout modules TNS / Libéral / Salarié (transposition modules 8/9/10)
- v3 : Comparateur de dispositifs (matrice scorée + podium top 3)
- v4 : Synthèse client + export PDF
- v5 : Authentification nominative EC + journal des scénarios joués
