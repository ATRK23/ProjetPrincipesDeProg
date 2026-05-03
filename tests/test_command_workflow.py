import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_user_in_db(
    db_session,
    username,
    email,
    password="testpass123",
    role="user",
):
    user = User(
        username=username,
        email=email,
        role=role,
        hashed_password=hash_password(password),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user, password


def login(client, email, password):
    return client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )


def auth_headers(client, email, password):
    response = login(client, email, password)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_restaurant(client, headers):
    response = client.post(
        "/restaurants/",
        json={
            "name": "Le Bon Plat",
            "address": "12 rue de Paris",
            "phone": "0102030405",
            "description": "Cuisine maison",
            "is_open": True,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def create_plat(client, restaurant_id, headers, nom, prix):
    response = client.post(
        "/plats/",
        json={
            "nom": nom,
            "prix": prix,
            "description": f"{nom} prepare sur place",
            "ingredients": "ingredients frais",
            "allergenes": None,
            "is_available": True,
            "restaurant_id": restaurant_id,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def create_livreur_profile(client, user_id, headers):
    response = client.post(
        "/livreurs/",
        json={
            "nom": "Livreur Express",
            "telephone": "0600000000",
            "moyen_transport": "velo",
            "note_moyenne": 4.7,
            "user_id": user_id,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def update_commande_status(client, commande_id, statut, headers):
    response = client.patch(
        f"/commandes/{commande_id}",
        json={"statut": statut},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def update_livraison_status(client, commande_id, statut_livraison, headers):
    response = client.patch(
        f"/commandes/{commande_id}/livraison-status",
        json={"statut_livraison": statut_livraison},
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()


def test_complete_command_workflow_from_order_to_delivery(client, db_session):
    customer, customer_password = create_user_in_db(
        db_session,
        username="customer",
        email="customer@example.com",
    )
    owner, owner_password = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
    )
    livreur_user, livreur_password = create_user_in_db(
        db_session,
        username="livreur",
        email="livreur@example.com",
    )

    customer_headers = auth_headers(client, customer.email, customer_password)
    owner_headers = auth_headers(client, owner.email, owner_password)
    livreur_headers = auth_headers(client, livreur_user.email, livreur_password)

    restaurant = create_restaurant(client, owner_headers)
    db_session.refresh(owner)
    assert owner.role == "restaurant_owner"

    burger = create_plat(
        client,
        restaurant["id"],
        owner_headers,
        nom="Burger maison",
        prix=12.5,
    )
    fries = create_plat(
        client,
        restaurant["id"],
        owner_headers,
        nom="Frites",
        prix=4.0,
    )

    livreur = create_livreur_profile(client, livreur_user.id, livreur_headers)
    db_session.refresh(livreur_user)
    assert livreur_user.role == "livreur"

    create_response = client.post(
        "/commandes/",
        json={
            "user_id": customer.id,
            "restaurant_id": restaurant["id"],
            "plat_ids": [burger["id"], fries["id"]],
        },
        headers=customer_headers,
    )
    assert create_response.status_code == 201
    commande = create_response.json()
    assert commande["statut"] == "en_attente"
    assert commande["statut_livraison"] == "non_assignee"
    assert commande["prix_total"] == 16.5
    assert set(commande["plat_ids"]) == {burger["id"], fries["id"]}

    customer_view = client.get(f"/commandes/{commande['id']}", headers=customer_headers)
    assert customer_view.status_code == 200
    assert customer_view.json()["id"] == commande["id"]

    restaurant_orders = client.get(
        f"/commandes/restaurant/{restaurant['id']}",
        headers=owner_headers,
    )
    assert restaurant_orders.status_code == 200
    assert [item["id"] for item in restaurant_orders.json()] == [commande["id"]]

    accepted = update_commande_status(
        client,
        commande["id"],
        "acceptee",
        owner_headers,
    )
    assert accepted["statut"] == "acceptee"

    preparing = update_commande_status(
        client,
        commande["id"],
        "en_preparation",
        owner_headers,
    )
    assert preparing["statut"] == "en_preparation"

    available_response = client.get(
        "/commandes/available-for-delivery",
        headers=livreur_headers,
    )
    assert available_response.status_code == 200
    assert [item["id"] for item in available_response.json()] == [commande["id"]]

    claim_response = client.patch(
        f"/commandes/{commande['id']}/claim-delivery",
        headers=livreur_headers,
    )
    assert claim_response.status_code == 200
    assert claim_response.json()["livreur_id"] == livreur["id"]
    assert claim_response.json()["statut_livraison"] == "assignee"

    assigned_livreur = client.get(
        f"/commandes/{commande['id']}/livreur",
        headers=customer_headers,
    )
    assert assigned_livreur.status_code == 200
    assert assigned_livreur.json()["id"] == livreur["id"]

    picked_up = update_livraison_status(
        client,
        commande["id"],
        "recuperee",
        livreur_headers,
    )
    assert picked_up["statut_livraison"] == "recuperee"

    on_the_way = update_livraison_status(
        client,
        commande["id"],
        "en_route",
        livreur_headers,
    )
    assert on_the_way["statut_livraison"] == "en_route"

    delivered = update_livraison_status(
        client,
        commande["id"],
        "livree",
        livreur_headers,
    )
    assert delivered["statut_livraison"] == "livree"
    assert delivered["statut"] == "terminee"

    final_customer_view = client.get(
        f"/commandes/{commande['id']}",
        headers=customer_headers,
    )
    assert final_customer_view.status_code == 200
    assert final_customer_view.json()["statut"] == "terminee"
    assert final_customer_view.json()["statut_livraison"] == "livree"


def test_command_workflow_blocks_livreur_before_order_is_in_preparation(client, db_session):
    customer, customer_password = create_user_in_db(
        db_session,
        username="customer",
        email="customer@example.com",
    )
    owner, owner_password = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
    )
    livreur_user, livreur_password = create_user_in_db(
        db_session,
        username="livreur",
        email="livreur@example.com",
    )

    customer_headers = auth_headers(client, customer.email, customer_password)
    owner_headers = auth_headers(client, owner.email, owner_password)
    livreur_headers = auth_headers(client, livreur_user.email, livreur_password)

    restaurant = create_restaurant(client, owner_headers)
    plat = create_plat(
        client,
        restaurant["id"],
        owner_headers,
        nom="Burger maison",
        prix=12.5,
    )
    create_livreur_profile(client, livreur_user.id, livreur_headers)

    create_response = client.post(
        "/commandes/",
        json={
            "user_id": customer.id,
            "restaurant_id": restaurant["id"],
            "plat_ids": [plat["id"]],
        },
        headers=customer_headers,
    )
    assert create_response.status_code == 201
    commande = create_response.json()

    claim_response = client.patch(
        f"/commandes/{commande['id']}/claim-delivery",
        headers=livreur_headers,
    )

    assert claim_response.status_code == 400
    assert claim_response.json()["detail"] == "Commande non disponible pour livraison"
