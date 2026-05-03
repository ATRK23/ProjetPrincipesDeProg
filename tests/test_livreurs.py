import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Livreur, User
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


def create_livreur_in_db(
    db_session,
    user_id,
    nom="Arthur Livreur",
    telephone="0600000000",
    moyen_transport="velo",
    note_moyenne=4.5,
):
    livreur = Livreur(
        nom=nom,
        telephone=telephone,
        moyen_transport=moyen_transport,
        note_moyenne=note_moyenne,
        user_id=user_id,
    )
    db_session.add(livreur)
    db_session.commit()
    db_session.refresh(livreur)
    return livreur


def livreur_payload(
    user_id,
    nom="Arthur Livreur",
    telephone="0600000000",
    moyen_transport="velo",
    note_moyenne=4.5,
):
    return {
        "nom": nom,
        "telephone": telephone,
        "moyen_transport": moyen_transport,
        "note_moyenne": note_moyenne,
        "user_id": user_id,
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


def test_create_livreur_requires_authentication(client, db_session):
    user, _ = create_user_in_db(db_session)

    response = client.post("/livreurs/", json=livreur_payload(user.id))

    assert response.status_code == 401


def test_user_can_create_own_livreur_profile_and_role_is_updated(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.post(
        "/livreurs/",
        json=livreur_payload(user.id),
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["nom"] == "Arthur Livreur"
    assert data["telephone"] == "0600000000"
    assert data["moyen_transport"] == "velo"
    assert data["note_moyenne"] == 4.5
    assert data["user_id"] == user.id

    db_session.refresh(user)
    assert user.role == "livreur"


def test_create_livreur_rejects_missing_required_fields(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.post(
        "/livreurs/",
        json={"telephone": "0600000000", "user_id": user.id},
        headers=headers,
    )

    assert response.status_code == 422


def test_user_cannot_create_livreur_profile_for_another_user(client, db_session):
    user, password = create_user_in_db(db_session)
    other_user, _ = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    headers = auth_headers(client, user.email, password)

    response = client.post(
        "/livreurs/",
        json=livreur_payload(other_user.id),
        headers=headers,
    )

    assert response.status_code == 403


def test_admin_can_create_livreur_profile_for_any_user(client, db_session):
    target_user, _ = create_user_in_db(db_session)
    admin, admin_password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    headers = auth_headers(client, admin.email, admin_password)

    response = client.post(
        "/livreurs/",
        json=livreur_payload(target_user.id, nom="Livreur Admin"),
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["nom"] == "Livreur Admin"
    assert response.json()["user_id"] == target_user.id

    db_session.refresh(target_user)
    assert target_user.role == "livreur"


def test_create_livreur_returns_404_when_user_does_not_exist(client, db_session):
    admin, admin_password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    headers = auth_headers(client, admin.email, admin_password)

    response = client.post(
        "/livreurs/",
        json=livreur_payload(user_id=9999),
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Utilisateur introuvable"


def test_create_livreur_rejects_duplicate_profile(client, db_session):
    user, password = create_user_in_db(db_session)
    create_livreur_in_db(db_session, user.id)
    headers = auth_headers(client, user.email, password)

    response = client.post(
        "/livreurs/",
        json=livreur_payload(user.id, nom="Deuxieme profil"),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cet utilisateur est déjà livreur"


def test_admin_can_list_livreurs_with_pagination(client, db_session):
    first_user, _ = create_user_in_db(
        db_session,
        username="first",
        email="first@example.com",
        role="livreur",
    )
    second_user, _ = create_user_in_db(
        db_session,
        username="second",
        email="second@example.com",
        role="livreur",
    )
    create_livreur_in_db(db_session, first_user.id, nom="Premier")
    create_livreur_in_db(db_session, second_user.id, nom="Second")
    admin, admin_password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    headers = auth_headers(client, admin.email, admin_password)

    response = client.get("/livreurs/?skip=1&limit=1", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["nom"] == "Second"


def test_regular_user_cannot_list_livreurs(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.get("/livreurs/", headers=headers)

    assert response.status_code == 403


def test_user_can_get_own_livreur_profile_by_user_id(client, db_session):
    user, password = create_user_in_db(db_session, role="livreur")
    livreur = create_livreur_in_db(db_session, user.id)
    headers = auth_headers(client, user.email, password)

    response = client.get(f"/livreurs/user/{user.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == livreur.id
    assert response.json()["user_id"] == user.id


def test_user_cannot_get_another_users_livreur_profile_by_user_id(client, db_session):
    user, password = create_user_in_db(db_session)
    other_user, _ = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
        role="livreur",
    )
    create_livreur_in_db(db_session, other_user.id)
    headers = auth_headers(client, user.email, password)

    response = client.get(f"/livreurs/user/{other_user.id}", headers=headers)

    assert response.status_code == 403


def test_get_livreur_by_user_returns_404_when_profile_missing(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.get(f"/livreurs/user/{user.id}", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Livreur introuvable pour cet utilisateur"


def test_user_can_get_own_livreur_profile_by_livreur_id(client, db_session):
    user, password = create_user_in_db(db_session, role="livreur")
    livreur = create_livreur_in_db(db_session, user.id)
    headers = auth_headers(client, user.email, password)

    response = client.get(f"/livreurs/{livreur.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == livreur.id


def test_admin_can_get_any_livreur_profile_by_livreur_id(client, db_session):
    user, _ = create_user_in_db(db_session, role="livreur")
    livreur = create_livreur_in_db(db_session, user.id)
    admin, admin_password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    headers = auth_headers(client, admin.email, admin_password)

    response = client.get(f"/livreurs/{livreur.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == livreur.id


def test_get_missing_livreur_returns_404_for_authenticated_user(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.get("/livreurs/9999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Livreur introuvable"


def test_user_can_update_own_livreur_profile(client, db_session):
    user, password = create_user_in_db(db_session, role="livreur")
    livreur = create_livreur_in_db(db_session, user.id)
    headers = auth_headers(client, user.email, password)

    response = client.patch(
        f"/livreurs/{livreur.id}",
        json={
            "nom": "Arthur Express",
            "telephone": "0611111111",
            "moyen_transport": "scooter",
            "note_moyenne": 4.8,
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["nom"] == "Arthur Express"
    assert data["telephone"] == "0611111111"
    assert data["moyen_transport"] == "scooter"
    assert data["note_moyenne"] == 4.8


def test_user_cannot_update_another_users_livreur_profile(client, db_session):
    user, password = create_user_in_db(db_session)
    other_user, _ = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
        role="livreur",
    )
    livreur = create_livreur_in_db(db_session, other_user.id)
    headers = auth_headers(client, user.email, password)

    response = client.patch(
        f"/livreurs/{livreur.id}",
        json={"nom": "Tentative interdite"},
        headers=headers,
    )

    assert response.status_code == 403


def test_update_missing_livreur_returns_404_for_authenticated_user(client, db_session):
    user, password = create_user_in_db(db_session)
    headers = auth_headers(client, user.email, password)

    response = client.patch(
        "/livreurs/9999",
        json={"nom": "Introuvable"},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Livreur introuvable"


def test_user_can_delete_own_livreur_profile(client, db_session):
    user, password = create_user_in_db(db_session, role="livreur")
    livreur = create_livreur_in_db(db_session, user.id)
    livreur_id = livreur.id
    headers = auth_headers(client, user.email, password)

    response = client.delete(f"/livreurs/{livreur_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == livreur_id
    assert db_session.query(Livreur).filter(Livreur.id == livreur_id).first() is None


def test_user_cannot_delete_another_users_livreur_profile(client, db_session):
    user, password = create_user_in_db(db_session)
    other_user, _ = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
        role="livreur",
    )
    livreur = create_livreur_in_db(db_session, other_user.id)
    headers = auth_headers(client, user.email, password)

    response = client.delete(f"/livreurs/{livreur.id}", headers=headers)

    assert response.status_code == 403
    assert db_session.query(Livreur).filter(Livreur.id == livreur.id).first() is not None


def test_admin_can_delete_any_livreur_profile(client, db_session):
    user, _ = create_user_in_db(db_session, role="livreur")
    livreur = create_livreur_in_db(db_session, user.id)
    livreur_id = livreur.id
    admin, admin_password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    headers = auth_headers(client, admin.email, admin_password)

    response = client.delete(f"/livreurs/{livreur_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == livreur_id
    assert db_session.query(Livreur).filter(Livreur.id == livreur_id).first() is None
