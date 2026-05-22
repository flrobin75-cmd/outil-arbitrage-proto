# baseline_audit_G3f_pre/ — snapshot rétroactif avant G3f

Contient les versions originales (non instrumentées) de `strategy/perin.py`
et `strategy/receptacles.py` extraites du snapshot v1.5 du 19/05/2026.

Snapshot reconstitué *après* l'instrumentation G3f-perin.1 et G3f-receptacles.1
pour préserver la cohérence de la séquence baseline_audit_*_pre/ (un snapshot
par jalon, du jalon précédent au jalon courant).

Fichiers :
- `perin.py.original` : version v1.5, avant G3f-perin
- `receptacles.py.original` : version v1.5, avant G3f-receptacles

Différentiel : voir `git diff` entre ces fichiers et `strategy/perin.py` /
`strategy/receptacles.py` actuels.
