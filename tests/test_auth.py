from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import ALGORITHM, SECRET_KEY, hash_password


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


def login(client, email, password):
    return client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def encode_token(payload):
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_login_returns_bearer_token_for_valid_credentials(client, db_session):
    user, password = create_user_in_db(db_session)

    response = login(client, user.email, password)

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]

    decoded = jwt.decode(data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == user.email
    assert "exp" in decoded


def test_login_rejects_unknown_email(client):
    response = login(client, "missing@example.com", "testpass123")

    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou mot de passe incorrect"


def test_login_rejects_invalid_password(client, db_session):
    user, _ = create_user_in_db(db_session)

    response = login(client, user.email, "wrong-password")

    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou mot de passe incorrect"


def test_login_requires_form_username_and_password(client):
    response = client.post("/auth/login", json={"username": "a", "password": "b"})

    assert response.status_code == 422


def test_valid_token_allows_access_to_protected_route(client, db_session):
    user, password = create_user_in_db(db_session)
    login_response = login(client, user.email, password)
    token = login_response.json()["access_token"]

    response = client.get(f"/users/{user.id}", headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["email"] == user.email


def test_protected_route_rejects_missing_token(client, db_session):
    user, _ = create_user_in_db(db_session)

    response = client.get(f"/users/{user.id}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_protected_route_rejects_malformed_token(client, db_session):
    user, _ = create_user_in_db(db_session)

    response = client.get(f"/users/{user.id}", headers=bearer("not-a-jwt"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token invalide"


def test_protected_route_rejects_token_without_subject(client, db_session):
    user, _ = create_user_in_db(db_session)
    token = encode_token(
        {
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        }
    )

    response = client.get(f"/users/{user.id}", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token invalide"


def test_protected_route_rejects_expired_token(client, db_session):
    user, _ = create_user_in_db(db_session)
    token = encode_token(
        {
            "sub": user.email,
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        }
    )

    response = client.get(f"/users/{user.id}", headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token invalide"


def test_protected_route_returns_404_when_token_user_no_longer_exists(client, db_session):
    user, password = create_user_in_db(db_session)
    token = login(client, user.email, password).json()["access_token"]

    db_session.delete(user)
    db_session.commit()

    response = client.get(f"/users/{user.id}", headers=bearer(token))

    assert response.status_code == 404
    assert response.json()["detail"] == "Utilisateur introuvable"
