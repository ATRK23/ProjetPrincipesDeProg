# Restaurant API - SAE Developpement et Deploiement d'une API RESTful

API REST de gestion de restaurants, plats, utilisateurs, commandes et livraisons. Le projet repond a l'enonce de SAE : backend REST, persistance relationnelle, ORM, relations entre entites, conteneurisation Docker, orchestration Docker Compose, migrations, documentation et tests automatises.

## Sommaire

- [Contexte du projet](#contexte-du-projet)
- [Fonctionnalites](#fonctionnalites)
- [Stack technique](#stack-technique)
- [Respect de l'enonce](#respect-de-lenonce)
- [Architecture](#architecture)
- [Modele de donnees](#modele-de-donnees)
- [Installation avec Docker Compose](#installation-avec-docker-compose)
- [Jeu de donnees de test](#jeu-de-donnees-de-test)
- [Lancement local sans conteneur API](#lancement-local-sans-conteneur-api)
- [Documentation Swagger](#documentation-swagger)
- [Authentification et roles](#authentification-et-roles)
- [Routes principales](#routes-principales)
- [Exemples d'utilisation](#exemples-dutilisation)
- [Tests automatises](#tests-automatises)
- [Image Docker](#image-docker)
- [Variables d'environnement](#variables-denvironnement)

## Contexte du projet

L'application simule une plateforme de commande de repas. Elle permet a des clients de creer un compte, consulter des restaurants et leurs plats, passer une commande, puis suivre son traitement jusqu'a la livraison.

Le projet couvre aussi les besoins des restaurateurs et des livreurs :

- un restaurateur possede un ou plusieurs restaurants ;
- un restaurateur gere les plats de ses restaurants ;
- un client passe des commandes contenant un ou plusieurs plats ;
- un livreur peut recuperer une commande disponible et faire evoluer son statut de livraison ;
- un administrateur peut consulter les ressources globales protegees.

## Fonctionnalites

- Gestion des utilisateurs avec mot de passe hashe.
- Connexion par JWT via `/auth/login`.
- Roles applicatifs : `user`, `admin`, `restaurant_owner`, `livreur`.
- CRUD restaurants avec controle du proprietaire.
- CRUD plats rattaches a un restaurant.
- Creation et consultation des commandes.
- Calcul automatique du `prix_total` a partir des plats commandes.
- Workflow de commande : `en_attente`, `acceptee`, `en_preparation`, `prete`, `annulee`, `terminee`.
- Workflow de livraison : `non_assignee`, `assignee`, `recuperee`, `en_route`, `livree`.
- Assignation d'une commande a un livreur.
- Gestion des erreurs HTTP : `400`, `401`, `403`, `404`, `422`.
- Migrations de schema avec Alembic.
- Tests automatises avec pytest.
- Conteneurisation de l'API et de PostgreSQL avec Docker Compose.

## Stack technique

| Besoin | Choix du projet |
| --- | --- |
| Langage | Python 3.12 |
| Framework API | FastAPI |
| Serveur ASGI | Uvicorn |
| Base relationnelle | PostgreSQL 16 en Docker |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Validation | Pydantic |
| Authentification | JWT avec `python-jose`, hash avec `passlib`/bcrypt |
| Tests | pytest, FastAPI TestClient, SQLite en memoire pour les tests |
| Conteneurisation | Docker et Docker Compose |

## Respect de l'enonce

| Demande de l'enonce | Implementation dans ce depot |
| --- | --- |
| API REST avec routes HTTP | Routes FastAPI en `GET`, `POST`, `PATCH`, `DELETE` |
| Backend au choix | Backend Python/FastAPI |
| Base de donnees relationnelle | PostgreSQL via le service Docker `db` |
| ORM obligatoire | Modeles SQLAlchemy dans `app/models` |
| Relations 1-1, 1-n, n-n | Voir [Modele de donnees](#modele-de-donnees) |
| API conteneurisee | `Dockerfile` pour le service `api` |
| Base conteneurisee | Image officielle `postgres:16` |
| Orchestration Docker Compose | `docker-compose.yml` |
| Migrations / schema | Alembic dans `alembic/versions` |
| Donnees minimales de test | Script `scripts/seed.py` |
| Documentation du lancement | Present README |
| Documentation des routes | Swagger FastAPI + exemples ci-dessous |
| Tests automatises | Dossier `tests` avec pytest |

## Architecture

```text
.
+-- app
|   +-- crud          # Acces aux donnees SQLAlchemy
|   +-- models        # Modeles ORM et relations
|   +-- routers       # Routes FastAPI
|   +-- schemas       # Schemas Pydantic
|   +-- database.py   # Connexion SQLAlchemy
|   +-- main.py       # Application FastAPI
|   +-- security.py   # JWT, roles, hash mot de passe
+-- alembic
|   +-- versions      # Migrations SQL
+-- scripts
|   +-- seed.py       # Jeu de donnees de demonstration
+-- tests             # Tests unitaires et API
+-- Dockerfile
+-- docker-compose.yml
+-- requirements.txt
+-- README.md
```

Flux general :

```text
Client HTTP
   |
   v
FastAPI routers -> schemas Pydantic -> couche CRUD -> modeles SQLAlchemy -> PostgreSQL
   |
   v
Reponse JSON + code HTTP
```

## Modele de donnees

Entites principales :

- `User` : utilisateur de la plateforme.
- `Restaurant` : restaurant cree par un utilisateur proprietaire.
- `Plat` : plat vendu par un restaurant.
- `Commande` : commande passee par un utilisateur dans un restaurant.
- `Livreur` : profil de livraison rattache a un utilisateur.
- `commande_plat` : table d'association entre commandes et plats.

Relations implementees :

```text
User 1 -> 0..1 Livreur
User 1 -> 0..n Restaurant
User 1 -> 0..n Commande
Restaurant 1 -> 0..n Plat
Restaurant 1 -> 0..n Commande
Livreur 1 -> 0..n Commande
Commande n -> n Plat
```

Correspondance avec les contraintes de relations :

- Relation 1-1 : `User` -> `Livreur`, grace a `livreurs.user_id` unique.
- Relations 1-n : `Restaurant` -> `Plat`, `User` -> `Commande`, `Restaurant` -> `Commande`, `Livreur` -> `Commande`.
- Relation n-n : `Commande` <-> `Plat`, via la table d'association `commande_plat`.

## Installation avec Docker Compose

Prerequis :

- Docker ;
- Docker Compose ;
- un port `8000` disponible pour l'API ;
- un port `5433` disponible pour PostgreSQL cote machine hote.

Creer le fichier d'environnement :

```bash
cp .env_example .env
```

Demarrer l'API et la base de donnees :

```bash
docker compose up --build -d
```

Verifier les services :

```bash
docker compose ps
```

Consulter les logs de l'API :

```bash
docker compose logs -f api
```

L'API est disponible ici :

- API : http://127.0.0.1:8000
- Swagger : http://127.0.0.1:8000/docs
- OpenAPI JSON : http://127.0.0.1:8000/openapi.json

Au demarrage du conteneur `api`, les migrations Alembic sont appliquees automatiquement par la commande du `Dockerfile` :

```bash
alembic upgrade head
```

Arreter les conteneurs :

```bash
docker compose down
```

Arreter les conteneurs et supprimer le volume PostgreSQL :

```bash
docker compose down -v
```

## Jeu de donnees de test

Le script `scripts/seed.py` insere des utilisateurs, restaurants, plats, livreurs et commandes de demonstration.

Installer les dependances Python cote machine hote si ce n'est pas deja fait :

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Avec la base Docker lancee, executer le seed depuis l'hote :

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/restaurant_db python3 scripts/seed.py --reset
```

Comptes crees par defaut :

| Role | Email | Mot de passe |
| --- | --- | --- |
| Administrateur | `admin@example.com` | `password123` |
| Client | `arthur@example.com` | `password123` |
| Client | `marie@example.com` | `password123` |
| Restaurateur | `bistro@example.com` | `password123` |
| Restaurateur | `pizza@example.com` | `password123` |
| Livreur | `leo@example.com` | `password123` |
| Livreur | `sara@example.com` | `password123` |

Le seed cree notamment :

- 3 restaurants : `Le Bistro du Code`, `Pizza Algo`, `Sushi Recursion` ;
- 7 plats ;
- 2 profils livreurs ;
- 4 commandes avec differents statuts.

## Lancement local sans conteneur API

Il est aussi possible de lancer seulement PostgreSQL avec Docker, puis l'API directement avec Uvicorn.

Demarrer uniquement la base :

```bash
docker compose up -d db
```

Creer l'environnement Python :

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Appliquer les migrations :

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/restaurant_db alembic upgrade head
```

Lancer l'API :

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/restaurant_db python3 -m uvicorn app.main:app --reload
```

Tester la racine :

```bash
curl http://127.0.0.1:8000/
```

Reponse attendue :

```json
{"message":"API restaurant OK"}
```

## Documentation Swagger

FastAPI genere automatiquement la documentation interactive :

- Swagger UI : http://127.0.0.1:8000/docs
- ReDoc : http://127.0.0.1:8000/redoc

Swagger permet de tester les routes directement dans le navigateur. Pour les routes protegees, il faut d'abord recuperer un token via `/auth/login`, puis cliquer sur `Authorize` et renseigner :

```text
Bearer <token>
```

## Authentification et roles

L'authentification utilise un token JWT.

Connexion :

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=<email>&password=<mot_de_passe>
```

Reponse :

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

Roles :

| Role | Droits principaux |
| --- | --- |
| `user` | Consulter les restaurants/plats, gerer son compte, passer ses commandes |
| `restaurant_owner` | Gerer ses restaurants, ses plats et les commandes de ses restaurants |
| `livreur` | Voir les commandes livrables, prendre une livraison, mettre a jour son statut |
| `admin` | Acces global aux listes protegees et aux ressources |

## Routes principales

### Auth

| Methode | Route | Description | Auth |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | Connexion et recuperation d'un JWT | Non |

### Utilisateurs

| Methode | Route | Description | Auth |
| --- | --- | --- | --- |
| `POST` | `/users/` | Creer un utilisateur | Non |
| `GET` | `/users/` | Lister les utilisateurs | Admin |
| `GET` | `/users/{user_id}` | Voir un utilisateur | Soi-meme ou admin |
| `PATCH` | `/users/{user_id}` | Modifier un utilisateur | Soi-meme ou admin |
| `DELETE` | `/users/{user_id}` | Supprimer un utilisateur | Soi-meme ou admin |

### Restaurants

| Methode | Route | Description | Auth |
| --- | --- | --- | --- |
| `POST` | `/restaurants/` | Creer un restaurant | Connecte |
| `GET` | `/restaurants/` | Lister les restaurants | Non |
| `GET` | `/restaurants/{restaurant_id}` | Voir un restaurant | Non |
| `PATCH` | `/restaurants/{restaurant_id}` | Modifier un restaurant | Proprietaire ou admin |
| `DELETE` | `/restaurants/{restaurant_id}` | Supprimer un restaurant | Proprietaire ou admin |

### Plats

| Methode | Route | Description | Auth |
| --- | --- | --- | --- |
| `POST` | `/plats/` | Creer un plat | Proprietaire du restaurant ou admin |
| `GET` | `/plats/` | Lister les plats | Non |
| `GET` | `/plats/restaurant/{restaurant_id}` | Lister les plats d'un restaurant | Non |
| `GET` | `/plats/{plat_id}` | Voir un plat | Non |
| `PATCH` | `/plats/{plat_id}` | Modifier un plat | Proprietaire du restaurant ou admin |
| `DELETE` | `/plats/{plat_id}` | Supprimer un plat | Proprietaire du restaurant ou admin |

### Commandes

| Methode | Route | Description | Auth |
| --- | --- | --- | --- |
| `POST` | `/commandes/` | Creer une commande | Client concerne ou admin |
| `GET` | `/commandes/` | Lister toutes les commandes | Admin |
| `GET` | `/commandes/{commande_id}` | Voir une commande | Client, proprietaire, livreur assigne ou admin |
| `GET` | `/commandes/user/{user_id}` | Lister les commandes d'un client | Client concerne ou admin |
| `GET` | `/commandes/restaurant/{restaurant_id}` | Lister les commandes d'un restaurant | Proprietaire ou admin |
| `PATCH` | `/commandes/{commande_id}` | Modifier statut ou plats | Proprietaire du restaurant ou admin |
| `DELETE` | `/commandes/{commande_id}` | Supprimer selon statut et role | Controle specifique |
| `GET` | `/commandes/available-for-delivery` | Voir les commandes livrables | Livreur |
| `PATCH` | `/commandes/{commande_id}/claim-delivery` | Prendre une livraison | Livreur |
| `PATCH` | `/commandes/{commande_id}/livraison-status` | Changer le statut de livraison | Livreur assigne ou admin |
| `GET` | `/commandes/{commande_id}/livreur` | Voir le livreur assigne | Acteur autorise |

### Livreurs

| Methode | Route | Description | Auth |
| --- | --- | --- | --- |
| `POST` | `/livreurs/` | Creer un profil livreur | Utilisateur concerne ou admin |
| `GET` | `/livreurs/` | Lister les livreurs | Admin |
| `GET` | `/livreurs/user/{user_id}` | Voir le livreur d'un utilisateur | Utilisateur concerne ou admin |
| `GET` | `/livreurs/{livreur_id}` | Voir un livreur | Utilisateur concerne ou admin |
| `PATCH` | `/livreurs/{livreur_id}` | Modifier un livreur | Utilisateur concerne ou admin |
| `DELETE` | `/livreurs/{livreur_id}` | Supprimer un livreur | Utilisateur concerne ou admin |

## Exemples d'utilisation

### Creer un utilisateur

```bash
curl -X POST http://127.0.0.1:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "client_demo",
    "email": "client.demo@example.com",
    "phone": "0600000000",
    "address": "10 rue de Paris",
    "password": "password123"
  }'
```

### Se connecter

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=password123"
```

Stocker ensuite le token dans une variable :

```bash
TOKEN="coller_le_token_ici"
```

### Creer un restaurant

```bash
curl -X POST http://127.0.0.1:8000/restaurants/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Le Bon Plat",
    "address": "12 rue de Paris",
    "phone": "0102030405",
    "description": "Cuisine maison",
    "is_open": true
  }'
```

### Creer un plat

```bash
curl -X POST http://127.0.0.1:8000/plats/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Burger maison",
    "prix": 12.5,
    "description": "Pain artisanal, steak et cheddar",
    "ingredients": "Pain, boeuf, cheddar, salade",
    "allergenes": "gluten, lactose",
    "is_available": true,
    "restaurant_id": 1
  }'
```

### Creer une commande

```bash
curl -X POST http://127.0.0.1:8000/commandes/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "restaurant_id": 1,
    "plat_ids": [1, 2]
  }'
```

Reponse type :

```json
{
  "id": 1,
  "user_id": 2,
  "restaurant_id": 1,
  "livreur_id": null,
  "statut": "en_attente",
  "statut_livraison": "non_assignee",
  "prix_total": 22.5,
  "created_at": "2026-05-04T10:00:00Z",
  "plat_ids": [1, 2]
}
```

### Faire avancer une commande cote restaurant

```bash
curl -X PATCH http://127.0.0.1:8000/commandes/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"statut": "en_preparation"}'
```

Transitions de commande autorisees :

```text
en_attente -> acceptee | en_preparation | annulee
acceptee -> en_preparation | annulee
en_preparation -> prete | annulee
prete -> annulee
```

### Prendre une commande en livraison

Avec un token de livreur :

```bash
curl -X GET http://127.0.0.1:8000/commandes/available-for-delivery \
  -H "Authorization: Bearer $TOKEN"
```

```bash
curl -X PATCH http://127.0.0.1:8000/commandes/1/claim-delivery \
  -H "Authorization: Bearer $TOKEN"
```

Transitions de livraison autorisees :

```text
assignee -> recuperee
recuperee -> en_route
en_route -> livree
```

Quand une livraison passe a `livree`, la commande passe automatiquement a `terminee`.

## Tests automatises

Les tests utilisent SQLite en memoire et ne dependent pas de PostgreSQL.

Installer les dependances :

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Executer la suite :

```bash
pytest
```

Les tests couvrent notamment :

- authentification JWT ;
- permissions par role ;
- CRUD utilisateurs, restaurants, plats, livreurs ;
- creation et workflow des commandes ;
- transitions invalides ;
- erreurs HTTP ;
- relations ORM 1-1, 1-n, n-n ;
- cascades de suppression.

## Image Docker

### Publication Docker Hub

https://hub.docker.com/r/atrk23/restaurant-api

Commande pour lancer l'image publiee avec une base PostgreSQL sur le meme reseau Docker :

```bash
docker network create restaurant_network
docker run -d --name restaurant_db --network restaurant_network \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=restaurant_db \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:16
docker run --rm --name restaurant_api --network restaurant_network \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://postgres:postgres@restaurant_db:5432/restaurant_db \
  -e SECRET_KEY=change_me_in_env_file \
  <compte-dockerhub>/restaurant-api:latest
```

Volume utilise :

```text
postgres_data:/var/lib/postgresql/data
```

## Variables d'environnement

Les valeurs par defaut sont definies dans `.env_example`.

| Variable | Description | Valeur par defaut |
| --- | --- | --- |
| `POSTGRES_USER` | Utilisateur PostgreSQL | `postgres` |
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL | `postgres` |
| `POSTGRES_DB` | Nom de la base | `restaurant_db` |
| `POSTGRES_PORT` | Port PostgreSQL expose sur l'hote | `5433` |
| `API_PORT` | Port API expose sur l'hote | `8000` |
| `DATABASE_URL` | URL SQLAlchemy de connexion a la base | `postgresql://postgres:postgres@db:5432/restaurant_db` |
| `SECRET_KEY` | Cle de signature JWT | `change_me_in_env_file` |
| `ALGORITHM` | Algorithme JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duree de validite du token | `60` |

En production ou pour une soutenance publique, remplacer `SECRET_KEY` par une valeur longue et non partagee.

## Commandes utiles

Voir les conteneurs :

```bash
docker compose ps
```

Voir les logs API :

```bash
docker compose logs -f api
```

Relancer les migrations manuellement depuis l'hote :

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/restaurant_db alembic upgrade head
```

Creer une nouvelle migration apres modification des modeles :

```bash
alembic revision --autogenerate -m "description de la migration"
```

Reinitialiser completement la base Docker :

```bash
docker compose down -v
docker compose up --build -d
```

## Depannage

Si l'API ne demarre pas, verifier les logs :

```bash
docker compose logs api
```

Si le port PostgreSQL est deja utilise, modifier `POSTGRES_PORT` dans `.env`.

Si le port API est deja utilise, modifier `API_PORT` dans `.env`.

Si une route protegee repond `401`, le token est absent, mal forme ou expire.

Si une route protegee repond `403`, l'utilisateur authentifie n'a pas le role attendu ou n'est pas proprietaire de la ressource.
