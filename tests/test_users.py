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


def user_payload(
    username="arthur",
    email="arthur@example.com",
    password="testpass123",
    phone="0600000000",
    address="Paris",
):
    return {
        "username": username,
        "email": email,
        "password": password,
        "phone": phone,
        "address": address,
    }


def create_user(client, **overrides):
    payload = user_payload(**overrides)
    response = client.post("/users/", json=payload)
    assert response.status_code == 201
    return response.json(), payload


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


def create_admin(db_session):
    admin = User(
        username="admin",
        email="admin@example.com",
        role="admin",
        hashed_password=hash_password("adminpass123"),
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def test_create_user_returns_public_fields_and_default_role(client, db_session):
    data, payload = create_user(client)

    assert data["id"] > 0
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]
    assert data["phone"] == payload["phone"]
    assert data["address"] == payload["address"]
    assert data["role"] == "user"
    assert "password" not in data
    assert "hashed_password" not in data

    db_user = db_session.query(User).filter(User.email == payload["email"]).one()
    assert db_user.hashed_password != payload["password"]


def test_create_user_rejects_duplicate_email(client):
    create_user(client)

    response = client.post(
        "/users/",
        json=user_payload(username="arthur-2", email="arthur@example.com"),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Un utilisateur avec cet email existe déjà."


def test_create_user_rejects_invalid_email(client):
    response = client.post(
        "/users/",
        json=user_payload(email="not-an-email"),
    )

    assert response.status_code == 422


def test_login_accepts_valid_credentials_and_rejects_invalid_password(client):
    _, payload = create_user(client)

    valid_response = login(client, payload["email"], payload["password"])
    assert valid_response.status_code == 200
    assert valid_response.json()["token_type"] == "bearer"
    assert valid_response.json()["access_token"]

    invalid_response = login(client, payload["email"], "wrong-password")
    assert invalid_response.status_code == 401


def test_get_current_user_requires_authentication(client):
    data, _ = create_user(client)

    response = client.get(f"/users/{data['id']}")

    assert response.status_code == 401


def test_user_can_get_own_profile(client):
    data, payload = create_user(client)
    headers = auth_headers(client, payload["email"], payload["password"])

    response = client.get(f"/users/{data['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == payload["email"]


def test_user_cannot_get_another_user_profile(client):
    _, first_payload = create_user(
        client,
        username="first",
        email="first@example.com",
    )
    second_user, _ = create_user(
        client,
        username="second",
        email="second@example.com",
    )
    headers = auth_headers(client, first_payload["email"], first_payload["password"])

    response = client.get(f"/users/{second_user['id']}", headers=headers)

    assert response.status_code == 403


def test_admin_can_list_users(client, db_session):
    create_admin(db_session)
    create_user(client, username="client", email="client@example.com")

    headers = auth_headers(client, "admin@example.com", "adminpass123")
    response = client.get("/users/", headers=headers)

    assert response.status_code == 200
    emails = {user["email"] for user in response.json()}
    assert {"admin@example.com", "client@example.com"} <= emails


def test_regular_user_cannot_list_users(client):
    _, payload = create_user(client)
    headers = auth_headers(client, payload["email"], payload["password"])

    response = client.get("/users/", headers=headers)

    assert response.status_code == 403


def test_user_can_update_own_profile_and_password(client):
    data, payload = create_user(client)
    headers = auth_headers(client, payload["email"], payload["password"])

    response = client.patch(
        f"/users/{data['id']}",
        json={
            "username": "arthur-updated",
            "phone": "0611111111",
            "password": "newpass123",
        },
        headers=headers,
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["username"] == "arthur-updated"
    assert updated["phone"] == "0611111111"

    assert login(client, payload["email"], payload["password"]).status_code == 401
    assert login(client, payload["email"], "newpass123").status_code == 200


def test_user_cannot_update_another_user(client):
    _, first_payload = create_user(
        client,
        username="first",
        email="first@example.com",
    )
    second_user, _ = create_user(
        client,
        username="second",
        email="second@example.com",
    )
    headers = auth_headers(client, first_payload["email"], first_payload["password"])

    response = client.patch(
        f"/users/{second_user['id']}",
        json={"username": "hacked"},
        headers=headers,
    )

    assert response.status_code == 403


def test_admin_can_access_missing_user_and_get_404(client, db_session):
    create_admin(db_session)
    headers = auth_headers(client, "admin@example.com", "adminpass123")

    response = client.get("/users/9999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Utilisateur introuvable"


def test_user_can_delete_own_account(client, db_session):
    data, payload = create_user(client)
    headers = auth_headers(client, payload["email"], payload["password"])

    response = client.delete(f"/users/{data['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == payload["email"]
    assert db_session.query(User).filter(User.id == data["id"]).first() is None
