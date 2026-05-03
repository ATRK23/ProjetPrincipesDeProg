import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Commande, Plat, Restaurant, User
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
    username="arthur",
    email="arthur@example.com",
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


def create_restaurant_in_db(db_session, owner_id=None):
    restaurant = Restaurant(
        name="Le Bon Plat",
        address="12 rue de Paris",
        phone="0102030405",
        description="Cuisine maison",
        is_open=True,
        owner_id=owner_id,
    )
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)
    return restaurant


def create_plat_in_db(db_session, restaurant_id, nom="Burger maison", prix=12.5):
    plat = Plat(
        nom=nom,
        prix=prix,
        description="Pain artisanal et sauce maison",
        ingredients="Pain, steak, cheddar",
        allergenes="gluten, lactose",
        is_available=True,
        restaurant_id=restaurant_id,
    )
    db_session.add(plat)
    db_session.commit()
    db_session.refresh(plat)
    return plat


def create_commande_in_db(db_session, user_id, restaurant_id, plats):
    commande = Commande(
        user_id=user_id,
        restaurant_id=restaurant_id,
        livreur_id=None,
        statut="en_attente",
        statut_livraison="non_assignee",
        prix_total=sum(plat.prix for plat in plats),
        plats=plats,
    )
    db_session.add(commande)
    db_session.commit()
    db_session.refresh(commande)
    return commande


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


def assert_error(response, status_code, detail):
    assert response.status_code == status_code
    assert response.json()["detail"] == detail


def test_401_not_authenticated_on_protected_user_route(client):
    response = client.get("/users/1")

    assert_error(response, 401, "Not authenticated")


def test_401_invalid_token_on_protected_route(client):
    response = client.get(
        "/users/1",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert_error(response, 401, "Token invalide")


def test_401_wrong_login_credentials(client, db_session):
    user, _ = create_user_in_db(db_session)

    response = login(client, user.email, "wrong-password")

    assert_error(response, 401, "Email ou mot de passe incorrect")


def test_403_admin_only_users_list_for_regular_user(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.get("/users/", headers=headers)

    assert_error(response, 403, "Accès interdit")


def test_403_user_profile_access_for_other_user(client, db_session):
    user, password = create_user_in_db(db_session)
    other_user, _ = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    headers = auth_headers(client, user.email, password)

    response = client.get(f"/users/{other_user.id}", headers=headers)

    assert_error(response, 403, "Accès interdit")


def test_403_restaurant_update_for_non_owner(client, db_session):
    owner, _ = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
        role="restaurant_owner",
    )
    other_user, password = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    headers = auth_headers(client, other_user.email, password)

    response = client.patch(
        f"/restaurants/{restaurant.id}",
        json={"name": "Interdit"},
        headers=headers,
    )

    assert_error(response, 403, "Accès interdit")


def test_404_missing_user_for_admin(client, db_session):
    admin, password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    headers = auth_headers(client, admin.email, password)

    response = client.get("/users/9999", headers=headers)

    assert_error(response, 404, "Utilisateur introuvable")


def test_404_missing_restaurant_public_route(client):
    response = client.get("/restaurants/9999")

    assert_error(response, 404, "Restaurant introuvable")


def test_404_missing_plat_public_route(client):
    response = client.get("/plats/9999")

    assert_error(response, 404, "Plat introuvable")


def test_404_missing_commande_for_authenticated_user(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.get("/commandes/9999", headers=headers)

    assert_error(response, 404, "Commande introuvable")


def test_404_missing_livreur_for_authenticated_user(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.get("/livreurs/9999", headers=headers)

    assert_error(response, 404, "Livreur introuvable")


def test_400_duplicate_user_email(client):
    payload = {
        "username": "arthur",
        "email": "arthur@example.com",
        "password": "testpass123",
        "phone": "0600000000",
        "address": "Paris",
    }
    first_response = client.post("/users/", json=payload)
    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/users/",
        json={**payload, "username": "arthur-2"},
    )

    assert_error(
        duplicate_response,
        400,
        "Un utilisateur avec cet email existe déjà.",
    )


def test_400_commande_with_plat_from_another_restaurant(client, db_session):
    user, password = create_user_in_db(db_session)
    restaurant = create_restaurant_in_db(db_session)
    other_restaurant = create_restaurant_in_db(db_session)
    valid_plat = create_plat_in_db(db_session, restaurant.id, nom="Burger")
    invalid_plat = create_plat_in_db(db_session, other_restaurant.id, nom="Pizza")
    headers = auth_headers(client, user.email, password)

    response = client.post(
        "/commandes/",
        json={
            "user_id": user.id,
            "restaurant_id": restaurant.id,
            "plat_ids": [valid_plat.id, invalid_plat.id],
        },
        headers=headers,
    )

    assert_error(
        response,
        400,
        "Tous les plats doivent appartenir au restaurant de la commande",
    )


def test_400_invalid_commande_status_transition(client, db_session):
    user, _ = create_user_in_db(db_session)
    owner, owner_password = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
        role="restaurant_owner",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    plat = create_plat_in_db(db_session, restaurant.id)
    commande = create_commande_in_db(db_session, user.id, restaurant.id, [plat])
    headers = auth_headers(client, owner.email, owner_password)

    response = client.patch(
        f"/commandes/{commande.id}",
        json={"statut": "prete"},
        headers=headers,
    )

    assert_error(response, 400, "Transition de commande invalide")


def test_422_invalid_user_payload(client):
    response = client.post(
        "/users/",
        json={
            "username": "arthur",
            "email": "not-an-email",
            "password": "testpass123",
        },
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_422_invalid_restaurant_payload(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.post(
        "/restaurants/",
        json={"phone": "0102030405"},
        headers=headers,
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_422_invalid_commande_status_literal(client, db_session):
    user, _ = create_user_in_db(db_session)
    owner, owner_password = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
        role="restaurant_owner",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    plat = create_plat_in_db(db_session, restaurant.id)
    commande = create_commande_in_db(db_session, user.id, restaurant.id, [plat])
    headers = auth_headers(client, owner.email, owner_password)

    response = client.patch(
        f"/commandes/{commande.id}",
        json={"statut": "statut_invalide"},
        headers=headers,
    )

    assert response.status_code == 422
    assert "detail" in response.json()
