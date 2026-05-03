# ProjetPrincipesDeProg
Projet Principes de Programmation 


# Installation locale

- Créer un environnement python et installer les dépendances :
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- Créer une copie du fichier ```.env_example``` et l'appeler ```.env```

```
cp .env_example .env
```

- Modifier les variables d'environnement si nécessaire (optionnel)

# Utilisation avec Docker

L'API et la base de données sont conteneurisées séparément :
- `api` : application FastAPI exposée sur http://127.0.0.1:8000
- `db` : base PostgreSQL exposée sur le port local `5433`

Démarrer l'API et la base de données :
```
docker compose up --build -d
```

Les migrations Alembic sont appliquées automatiquement au démarrage du conteneur `api`.

Vérifier les conteneurs :
```
docker compose ps
```

Consulter les logs :
```
docker compose logs -f api
```

Arrêter les conteneurs :
```
docker compose down
```

Arrêter les conteneurs et supprimer les données PostgreSQL :
```
docker compose down -v
```

# Migrations en développement

Appliquer les migrations Alembic manuellement, si l'API est lancée hors Docker :
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/restaurant_db alembic upgrade head
```

Créer une nouvelle migration après modification des modèles SQLAlchemy :
```
alembic revision --autogenerate -m "description de la migration"
```

# Tests avec uvicorn

- S'assurer que le service `db` est lancé
- S'assurer que les migrations sont appliquées
- Lancer uvicorn :
```
python -m uvicorn app.main:app --reload
```
- Se rendre sur http://127.0.0.1:8000 et observer que le message ```{"message":"API restaurant OK"}``` apparaît

- Se rendre sur http://127.0.0.1:8000/docs et tester les différentes routes disponibles

# Tests avec Pytest

- S'assurer que le service `db` est lancé
- S'assurer que les migrations sont appliquées avec ```alembic upgrade head```
- Executer ```pytest``` :
```
pytest
```
- Observer la sortie et vérifier que tous les tests passent correctement
