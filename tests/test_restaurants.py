import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Restaurant, User
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


def restaurant_payload(
    name="Le Bon Plat",
    address="12 rue de Paris",
    phone="0102030405",
    description="Cuisine maison",
    image_url="/images/bistro_du_code.jpg",
    is_open=True,
):
    return {
        "name": name,
        "address": address,
        "phone": phone,
        "description": description,
        "image_url": image_url,
        "is_open": is_open,
    }


def create_user_in_db(
    db_session,
    username="owner",
    email="owner@example.com",
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


def create_restaurant_in_db(
    db_session,
    owner_id=None,
    name="Le Bon Plat",
    address="12 rue de Paris",
    phone="0102030405",
    description="Cuisine maison",
    image_url="/images/bistro_du_code.jpg",
    is_open=True,
):
    restaurant = Restaurant(
        name=name,
        address=address,
        phone=phone,
        description=description,
        image_url=image_url,
        is_open=is_open,
        owner_id=owner_id,
    )
    db_session.add(restaurant)
    db_session.commit()
    db_session.refresh(restaurant)
    return restaurant


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


def test_create_restaurant_requires_authentication(client):
    response = client.post("/restaurants/", json=restaurant_payload())

    assert response.status_code == 401


def test_authenticated_user_can_create_restaurant_and_becomes_owner(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.post(
        "/restaurants/",
        json=restaurant_payload(),
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Le Bon Plat"
    assert data["address"] == "12 rue de Paris"
    assert data["phone"] == "0102030405"
    assert data["description"] == "Cuisine maison"
    assert data["image_url"] == "/images/bistro_du_code.jpg"
    assert data["is_open"] is True
    assert data["owner_id"] == user.id

    db_session.refresh(user)
    assert user.role == "restaurant_owner"


def test_create_restaurant_rejects_missing_required_fields(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.post(
        "/restaurants/",
        json={"phone": "0102030405"},
        headers=headers,
    )

    assert response.status_code == 422


def test_get_restaurants_is_public_and_supports_pagination(client, db_session):
    create_restaurant_in_db(db_session, name="Premier")
    create_restaurant_in_db(db_session, name="Second")

    response = client.get("/restaurants/?skip=1&limit=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Second"


def test_get_restaurant_by_id_is_public(client, db_session):
    restaurant = create_restaurant_in_db(db_session)

    response = client.get(f"/restaurants/{restaurant.id}")

    assert response.status_code == 200
    assert response.json()["id"] == restaurant.id
    assert response.json()["name"] == restaurant.name


def test_get_missing_restaurant_returns_404(client):
    response = client.get("/restaurants/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant introuvable"


def test_update_restaurant_requires_authentication(client, db_session):
    restaurant = create_restaurant_in_db(db_session)

    response = client.patch(
        f"/restaurants/{restaurant.id}",
        json={"name": "Nouveau nom"},
    )

    assert response.status_code == 401


def test_owner_can_update_restaurant(client, db_session):
    owner, password = create_user_in_db(db_session)
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    headers = auth_headers(client, owner.email, password)

    response = client.patch(
        f"/restaurants/{restaurant.id}",
        json={
            "name": "Nouveau nom",
            "description": "Nouvelle description",
            "is_open": False,
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Nouveau nom"
    assert data["description"] == "Nouvelle description"
    assert data["is_open"] is False


def test_non_owner_cannot_update_restaurant(client, db_session):
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

    response = client.patch(
        f"/restaurants/{restaurant.id}",
        json={"name": "Tentative interdite"},
        headers=headers,
    )

    assert response.status_code == 403


def test_admin_can_update_any_restaurant(client, db_session):
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

    response = client.patch(
        f"/restaurants/{restaurant.id}",
        json={"name": "Modifie par admin"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Modifie par admin"


def test_update_missing_restaurant_returns_404_for_authenticated_user(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.patch(
        "/restaurants/9999",
        json={"name": "Introuvable"},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant introuvable"


def test_owner_can_delete_restaurant(client, db_session):
    owner, password = create_user_in_db(db_session)
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    headers = auth_headers(client, owner.email, password)

    response = client.delete(f"/restaurants/{restaurant.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == restaurant.id
    assert db_session.query(Restaurant).filter(Restaurant.id == restaurant.id).first() is None


def test_non_owner_cannot_delete_restaurant(client, db_session):
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

    response = client.delete(f"/restaurants/{restaurant.id}", headers=headers)

    assert response.status_code == 403
    assert db_session.query(Restaurant).filter(Restaurant.id == restaurant.id).first() is not None


def test_admin_can_delete_any_restaurant(client, db_session):
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

    response = client.delete(f"/restaurants/{restaurant.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == restaurant.id
    assert db_session.query(Restaurant).filter(Restaurant.id == restaurant.id).first() is None
