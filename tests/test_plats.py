import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Plat, Restaurant, User
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
    username="owner",
    email="owner@example.com",
    password="testpass123",
    role="restaurant_owner",
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


def create_restaurant_in_db(
    db_session,
    owner_id=None,
    name="Le Bon Plat",
):
    restaurant = Restaurant(
        name=name,
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


def create_plat_in_db(
    db_session,
    restaurant_id,
    nom="Burger maison",
    prix=12.5,
    description="Pain artisanal et sauce maison",
    ingredients="Pain, steak, cheddar",
    allergenes="gluten, lactose",
    is_available=True,
):
    plat = Plat(
        nom=nom,
        prix=prix,
        description=description,
        ingredients=ingredients,
        allergenes=allergenes,
        is_available=is_available,
        restaurant_id=restaurant_id,
    )
    db_session.add(plat)
    db_session.commit()
    db_session.refresh(plat)
    return plat


def plat_payload(
    restaurant_id,
    nom="Burger maison",
    prix=12.5,
    description="Pain artisanal et sauce maison",
    ingredients="Pain, steak, cheddar",
    allergenes="gluten, lactose",
    is_available=True,
):
    return {
        "nom": nom,
        "prix": prix,
        "description": description,
        "ingredients": ingredients,
        "allergenes": allergenes,
        "is_available": is_available,
        "restaurant_id": restaurant_id,
    }


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


def test_create_plat_requires_authentication(client, db_session):
    restaurant = create_restaurant_in_db(db_session)

    response = client.post("/plats/", json=plat_payload(restaurant.id))

    assert response.status_code == 401


def test_owner_can_create_plat_for_own_restaurant(client, db_session):
    owner, password = create_user_in_db(db_session)
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    headers = auth_headers(client, owner.email, password)

    response = client.post(
        "/plats/",
        json=plat_payload(restaurant.id),
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["nom"] == "Burger maison"
    assert data["prix"] == 12.5
    assert data["description"] == "Pain artisanal et sauce maison"
    assert data["ingredients"] == "Pain, steak, cheddar"
    assert data["allergenes"] == "gluten, lactose"
    assert data["is_available"] is True
    assert data["restaurant_id"] == restaurant.id


def test_create_plat_rejects_missing_required_fields(client, db_session):
    owner, password = create_user_in_db(db_session)
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    headers = auth_headers(client, owner.email, password)

    response = client.post(
        "/plats/",
        json={"restaurant_id": restaurant.id, "description": "Incomplet"},
        headers=headers,
    )

    assert response.status_code == 422


def test_create_plat_returns_404_when_restaurant_does_not_exist(client, db_session):
    owner, password = create_user_in_db(db_session)
    headers = auth_headers(client, owner.email, password)

    response = client.post(
        "/plats/",
        json=plat_payload(restaurant_id=9999),
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant introuvable"


def test_non_owner_cannot_create_plat_for_restaurant(client, db_session):
    owner, _ = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
    )
    other_user, password = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    headers = auth_headers(client, other_user.email, password)

    response = client.post(
        "/plats/",
        json=plat_payload(restaurant.id),
        headers=headers,
    )

    assert response.status_code == 403


def test_admin_can_create_plat_for_any_restaurant(client, db_session):
    owner, _ = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
    )
    admin, password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    headers = auth_headers(client, admin.email, password)

    response = client.post(
        "/plats/",
        json=plat_payload(restaurant.id, nom="Plat admin"),
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["nom"] == "Plat admin"


def test_get_plats_is_public_and_supports_pagination(client, db_session):
    restaurant = create_restaurant_in_db(db_session)
    create_plat_in_db(db_session, restaurant.id, nom="Premier")
    create_plat_in_db(db_session, restaurant.id, nom="Second")

    response = client.get("/plats/?skip=1&limit=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nom"] == "Second"


def test_get_plats_by_restaurant_is_public(client, db_session):
    first_restaurant = create_restaurant_in_db(db_session, name="Premier restaurant")
    second_restaurant = create_restaurant_in_db(db_session, name="Second restaurant")
    create_plat_in_db(db_session, first_restaurant.id, nom="Plat A")
    create_plat_in_db(db_session, first_restaurant.id, nom="Plat B")
    create_plat_in_db(db_session, second_restaurant.id, nom="Plat C")

    response = client.get(f"/plats/restaurant/{first_restaurant.id}")

    assert response.status_code == 200
    names = {plat["nom"] for plat in response.json()}
    assert names == {"Plat A", "Plat B"}


def test_get_plats_by_missing_restaurant_returns_404(client):
    response = client.get("/plats/restaurant/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant introuvable"


def test_get_plat_by_id_is_public(client, db_session):
    restaurant = create_restaurant_in_db(db_session)
    plat = create_plat_in_db(db_session, restaurant.id)

    response = client.get(f"/plats/{plat.id}")

    assert response.status_code == 200
    assert response.json()["id"] == plat.id
    assert response.json()["nom"] == plat.nom


def test_get_missing_plat_returns_404(client):
    response = client.get("/plats/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Plat introuvable"


def test_update_plat_requires_authentication(client, db_session):
    restaurant = create_restaurant_in_db(db_session)
    plat = create_plat_in_db(db_session, restaurant.id)

    response = client.patch(
        f"/plats/{plat.id}",
        json={"nom": "Nouveau nom"},
    )

    assert response.status_code == 401


def test_owner_can_update_plat(client, db_session):
    owner, password = create_user_in_db(db_session)
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    plat = create_plat_in_db(db_session, restaurant.id)
    headers = auth_headers(client, owner.email, password)

    response = client.patch(
        f"/plats/{plat.id}",
        json={
            "nom": "Burger vegetarien",
            "prix": 10.0,
            "is_available": False,
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["nom"] == "Burger vegetarien"
    assert data["prix"] == 10.0
    assert data["is_available"] is False


def test_non_owner_cannot_update_plat(client, db_session):
    owner, _ = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
    )
    other_user, password = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    plat = create_plat_in_db(db_session, restaurant.id)
    headers = auth_headers(client, other_user.email, password)

    response = client.patch(
        f"/plats/{plat.id}",
        json={"nom": "Tentative interdite"},
        headers=headers,
    )

    assert response.status_code == 403


def test_owner_can_move_plat_to_another_owned_restaurant(client, db_session):
    owner, password = create_user_in_db(db_session)
    first_restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    second_restaurant = create_restaurant_in_db(
        db_session,
        owner_id=owner.id,
        name="Deuxieme restaurant",
    )
    plat = create_plat_in_db(db_session, first_restaurant.id)
    headers = auth_headers(client, owner.email, password)

    response = client.patch(
        f"/plats/{plat.id}",
        json={"restaurant_id": second_restaurant.id},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["restaurant_id"] == second_restaurant.id


def test_owner_cannot_move_plat_to_restaurant_owned_by_someone_else(client, db_session):
    owner, password = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
    )
    other_owner, _ = create_user_in_db(
        db_session,
        username="other-owner",
        email="other-owner@example.com",
    )
    source_restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    target_restaurant = create_restaurant_in_db(
        db_session,
        owner_id=other_owner.id,
        name="Autre restaurant",
    )
    plat = create_plat_in_db(db_session, source_restaurant.id)
    headers = auth_headers(client, owner.email, password)

    response = client.patch(
        f"/plats/{plat.id}",
        json={"restaurant_id": target_restaurant.id},
        headers=headers,
    )

    assert response.status_code == 403


def test_update_plat_to_missing_restaurant_returns_404(client, db_session):
    owner, password = create_user_in_db(db_session)
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    plat = create_plat_in_db(db_session, restaurant.id)
    headers = auth_headers(client, owner.email, password)

    response = client.patch(
        f"/plats/{plat.id}",
        json={"restaurant_id": 9999},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant introuvable"


def test_update_missing_plat_returns_404_for_authenticated_user(client, db_session):
    owner, password = create_user_in_db(db_session)
    headers = auth_headers(client, owner.email, password)

    response = client.patch(
        "/plats/9999",
        json={"nom": "Introuvable"},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Plat introuvable"


def test_owner_can_delete_plat(client, db_session):
    owner, password = create_user_in_db(db_session)
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    plat = create_plat_in_db(db_session, restaurant.id)
    headers = auth_headers(client, owner.email, password)

    response = client.delete(f"/plats/{plat.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == plat.id
    assert db_session.query(Plat).filter(Plat.id == plat.id).first() is None


def test_non_owner_cannot_delete_plat(client, db_session):
    owner, _ = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
    )
    other_user, password = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    plat = create_plat_in_db(db_session, restaurant.id)
    headers = auth_headers(client, other_user.email, password)

    response = client.delete(f"/plats/{plat.id}", headers=headers)

    assert response.status_code == 403
    assert db_session.query(Plat).filter(Plat.id == plat.id).first() is not None


def test_admin_can_delete_any_plat(client, db_session):
    owner, _ = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
    )
    admin, password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    plat = create_plat_in_db(db_session, restaurant.id)
    headers = auth_headers(client, admin.email, password)

    response = client.delete(f"/plats/{plat.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == plat.id
    assert db_session.query(Plat).filter(Plat.id == plat.id).first() is None
