#!/usr/bin/env python3
"""Seed the application database with demo restaurant data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import Base, SessionLocal, engine
from app.models import Commande, Livreur, Plat, Restaurant, User
from app.models.command import commande_plat
from app.security import hash_password


DEFAULT_PASSWORD = "password123"


USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "phone": "0100000000",
        "address": "1 rue Admin, Paris",
    },
    {
        "username": "client_arthur",
        "email": "arthur@example.com",
        "role": "user",
        "phone": "0600000001",
        "address": "12 rue des Lilas, Paris",
    },
    {
        "username": "client_marie",
        "email": "marie@example.com",
        "role": "user",
        "phone": "0600000002",
        "address": "24 avenue Victor Hugo, Paris",
    },
    {
        "username": "owner_bistro",
        "email": "bistro@example.com",
        "role": "restaurant_owner",
        "phone": "0142000001",
        "address": "8 rue Montorgueil, Paris",
    },
    {
        "username": "owner_pizza",
        "email": "pizza@example.com",
        "role": "restaurant_owner",
        "phone": "0142000002",
        "address": "15 rue Oberkampf, Paris",
    },
    {
        "username": "livreur_leo",
        "email": "leo@example.com",
        "role": "livreur",
        "phone": "0611111111",
        "address": "5 rue de Lyon, Paris",
    },
    {
        "username": "livreur_sara",
        "email": "sara@example.com",
        "role": "livreur",
        "phone": "0622222222",
        "address": "9 rue Nationale, Paris",
    },
]


RESTAURANTS = [
    {
        "key": "bistro",
        "name": "Le Bistro du Code",
        "address": "8 rue Montorgueil, Paris",
        "phone": "0142000001",
        "description": "Cuisine francaise maison et plats du jour.",
        "is_open": True,
        "owner_email": "bistro@example.com",
    },
    {
        "key": "pizza",
        "name": "Pizza Algo",
        "address": "15 rue Oberkampf, Paris",
        "phone": "0142000002",
        "description": "Pizzas artisanales, pates fraiches et desserts italiens.",
        "is_open": True,
        "owner_email": "pizza@example.com",
    },
    {
        "key": "closed",
        "name": "Sushi Recursion",
        "address": "3 quai de Seine, Paris",
        "phone": "0142000003",
        "description": "Sushis, makis et bentos.",
        "is_open": False,
        "owner_email": "bistro@example.com",
    },
]


PLATS = [
    {
        "restaurant_key": "bistro",
        "nom": "Burger maison",
        "prix": 12.5,
        "description": "Pain artisanal, steak, cheddar et sauce maison.",
        "ingredients": "Pain, boeuf, cheddar, salade, tomate",
        "allergenes": "gluten, lactose",
        "is_available": True,
    },
    {
        "restaurant_key": "bistro",
        "nom": "Salade Cesar",
        "prix": 10.0,
        "description": "Salade romaine, poulet grille, parmesan et croutons.",
        "ingredients": "Salade, poulet, parmesan, croutons",
        "allergenes": "gluten, lactose, oeuf",
        "is_available": True,
    },
    {
        "restaurant_key": "bistro",
        "nom": "Tarte du jour",
        "prix": 6.5,
        "description": "Dessert maison selon la saison.",
        "ingredients": "Farine, beurre, fruits",
        "allergenes": "gluten, lactose",
        "is_available": False,
    },
    {
        "restaurant_key": "pizza",
        "nom": "Pizza Margherita",
        "prix": 11.0,
        "description": "Tomate, mozzarella et basilic frais.",
        "ingredients": "Pate, tomate, mozzarella, basilic",
        "allergenes": "gluten, lactose",
        "is_available": True,
    },
    {
        "restaurant_key": "pizza",
        "nom": "Pizza Regina",
        "prix": 13.5,
        "description": "Tomate, mozzarella, jambon et champignons.",
        "ingredients": "Pate, tomate, mozzarella, jambon, champignons",
        "allergenes": "gluten, lactose",
        "is_available": True,
    },
    {
        "restaurant_key": "pizza",
        "nom": "Tiramisu",
        "prix": 5.5,
        "description": "Dessert italien au cafe.",
        "ingredients": "Mascarpone, cafe, biscuit, cacao",
        "allergenes": "gluten, lactose, oeuf",
        "is_available": True,
    },
    {
        "restaurant_key": "closed",
        "nom": "Menu Bento",
        "prix": 15.0,
        "description": "Assortiment de riz, poisson et legumes.",
        "ingredients": "Riz, saumon, avocat, concombre",
        "allergenes": "poisson, sesame",
        "is_available": False,
    },
]


LIVREURS = [
    {
        "user_email": "leo@example.com",
        "nom": "Leo Martin",
        "telephone": "0611111111",
        "moyen_transport": "velo",
        "note_moyenne": 4.7,
    },
    {
        "user_email": "sara@example.com",
        "nom": "Sara Dupont",
        "telephone": "0622222222",
        "moyen_transport": "scooter",
        "note_moyenne": 4.9,
    },
]


COMMANDES = [
    {
        "user_email": "arthur@example.com",
        "restaurant_key": "bistro",
        "plat_names": ["Burger maison", "Salade Cesar"],
        "statut": "en_attente",
        "statut_livraison": "non_assignee",
        "livreur_email": None,
    },
    {
        "user_email": "marie@example.com",
        "restaurant_key": "pizza",
        "plat_names": ["Pizza Margherita", "Tiramisu"],
        "statut": "en_preparation",
        "statut_livraison": "non_assignee",
        "livreur_email": None,
    },
    {
        "user_email": "arthur@example.com",
        "restaurant_key": "pizza",
        "plat_names": ["Pizza Regina"],
        "statut": "prete",
        "statut_livraison": "assignee",
        "livreur_email": "leo@example.com",
    },
    {
        "user_email": "marie@example.com",
        "restaurant_key": "bistro",
        "plat_names": ["Burger maison", "Tarte du jour"],
        "statut": "terminee",
        "statut_livraison": "livree",
        "livreur_email": "sara@example.com",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the restaurant API database with demo data."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing application data before inserting the seed data.",
    )
    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="Create missing tables from SQLAlchemy models before seeding.",
    )
    return parser.parse_args()


def reset_database(db) -> None:
    db.execute(commande_plat.delete())
    db.query(Commande).delete()
    db.query(Plat).delete()
    db.query(Restaurant).delete()
    db.query(Livreur).delete()
    db.query(User).delete()
    db.commit()


def get_or_create_user(db, data: dict) -> User:
    user = db.query(User).filter(User.email == data["email"]).first()
    if user is None:
        user = User(
            username=data["username"],
            email=data["email"],
            phone=data["phone"],
            address=data["address"],
            role=data["role"],
            hashed_password=hash_password(DEFAULT_PASSWORD),
        )
        db.add(user)
    else:
        user.username = data["username"]
        user.phone = data["phone"]
        user.address = data["address"]
        user.role = data["role"]
    return user


def get_or_create_restaurant(db, data: dict, users_by_email: dict[str, User]) -> Restaurant:
    restaurant = db.query(Restaurant).filter(Restaurant.name == data["name"]).first()
    owner = users_by_email[data["owner_email"]]
    if restaurant is None:
        restaurant = Restaurant(name=data["name"])
        db.add(restaurant)

    restaurant.address = data["address"]
    restaurant.phone = data["phone"]
    restaurant.description = data["description"]
    restaurant.is_open = data["is_open"]
    restaurant.owner = owner
    return restaurant


def get_or_create_plat(db, data: dict, restaurants_by_key: dict[str, Restaurant]) -> Plat:
    restaurant = restaurants_by_key[data["restaurant_key"]]
    plat = (
        db.query(Plat)
        .filter(Plat.restaurant_id == restaurant.id, Plat.nom == data["nom"])
        .first()
    )
    if plat is None:
        plat = Plat(nom=data["nom"], restaurant=restaurant)
        db.add(plat)

    plat.prix = data["prix"]
    plat.description = data["description"]
    plat.ingredients = data["ingredients"]
    plat.allergenes = data["allergenes"]
    plat.is_available = data["is_available"]
    return plat


def get_or_create_livreur(db, data: dict, users_by_email: dict[str, User]) -> Livreur:
    user = users_by_email[data["user_email"]]
    livreur = db.query(Livreur).filter(Livreur.user_id == user.id).first()
    if livreur is None:
        livreur = Livreur(user=user)
        db.add(livreur)

    livreur.nom = data["nom"]
    livreur.telephone = data["telephone"]
    livreur.moyen_transport = data["moyen_transport"]
    livreur.note_moyenne = data["note_moyenne"]
    return livreur


def create_commandes(
    db,
    users_by_email: dict[str, User],
    restaurants_by_key: dict[str, Restaurant],
    livreurs_by_email: dict[str, Livreur],
) -> list[Commande]:
    created_commandes = []

    for data in COMMANDES:
        restaurant = restaurants_by_key[data["restaurant_key"]]
        user = users_by_email[data["user_email"]]
        plats = [
            plat
            for plat in restaurant.plats
            if plat.nom in set(data["plat_names"])
        ]
        livreur = (
            livreurs_by_email[data["livreur_email"]]
            if data["livreur_email"] is not None
            else None
        )

        existing = (
            db.query(Commande)
            .filter(
                Commande.user_id == user.id,
                Commande.restaurant_id == restaurant.id,
                Commande.statut == data["statut"],
                Commande.statut_livraison == data["statut_livraison"],
            )
            .first()
        )
        if existing is not None:
            created_commandes.append(existing)
            continue

        commande = Commande(
            user=user,
            restaurant=restaurant,
            livreur=livreur,
            statut=data["statut"],
            statut_livraison=data["statut_livraison"],
            prix_total=sum(plat.prix for plat in plats),
            plats=plats,
        )
        db.add(commande)
        created_commandes.append(commande)

    return created_commandes


def seed_database(reset: bool = False, create_tables: bool = False) -> None:
    if create_tables:
        Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if reset:
            reset_database(db)

        users_by_email = {}
        for user_data in USERS:
            user = get_or_create_user(db, user_data)
            users_by_email[user_data["email"]] = user
        db.commit()

        restaurants_by_key = {}
        for restaurant_data in RESTAURANTS:
            restaurant = get_or_create_restaurant(db, restaurant_data, users_by_email)
            restaurants_by_key[restaurant_data["key"]] = restaurant
        db.commit()

        plats = []
        for plat_data in PLATS:
            plats.append(get_or_create_plat(db, plat_data, restaurants_by_key))
        db.commit()

        livreurs_by_email = {}
        for livreur_data in LIVREURS:
            livreur = get_or_create_livreur(db, livreur_data, users_by_email)
            livreurs_by_email[livreur_data["user_email"]] = livreur
        db.commit()

        commandes = create_commandes(
            db,
            users_by_email,
            restaurants_by_key,
            livreurs_by_email,
        )
        db.commit()

        print("Seed complete.")
        print(f"Users: {len(users_by_email)}")
        print(f"Restaurants: {len(restaurants_by_key)}")
        print(f"Plats: {len(plats)}")
        print(f"Livreurs: {len(livreurs_by_email)}")
        print(f"Commandes: {len(commandes)}")
        print(f"Default password for all seeded users: {DEFAULT_PASSWORD}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    args = parse_args()
    seed_database(reset=args.reset, create_tables=args.create_tables)


if __name__ == "__main__":
    main()
