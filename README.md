# ProjetPrincipesDeProg
Projet Principes de Programmation 


# Installation

- Créer un environnement python et installer les dépendances :
```
python3 -m venv venv
pip install -r requirements.txt
```

- Créer une copie du fichier ```.env_example``` et l'appeler ```.env```

```
cp .env_example .env
```

- Modifier les variables d'environnement si nécessaire (optionnel)

# Utilisation

Démarrer le docker : 
```
docker compose up -d
```

# Tests avec unicorn

- S'assurer que le docker est lancé
- Lancer unicorn : 
```
python -m uvicorn app.main:app --reload
```
- Se rendre sur http://127.0.0.1:8000 et observer que le message ```{"message":"API restaurant OK"}``` apparaît

- Se rendre sur http://127.0.0.1:8000/docs et tester les différentes routes disponibles