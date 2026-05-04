import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Commande, Livreur, Plat, Restaurant, User
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
    username="client",
    email="client@example.com",
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


def create_restaurant_in_db(db_session, owner_id=None, name="Le Bon Plat"):
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


def create_livreur_in_db(db_session, user_id, nom="Livreur Test"):
    livreur = Livreur(
        nom=nom,
        telephone="0600000000",
        moyen_transport="velo",
        note_moyenne=4.5,
        user_id=user_id,
    )
    db_session.add(livreur)
    db_session.commit()
    db_session.refresh(livreur)
    return livreur


def create_commande_in_db(
    db_session,
    user_id,
    restaurant_id,
    plats,
    statut="en_attente",
    statut_livraison="non_assignee",
    livreur_id=None,
):
    commande = Commande(
        user_id=user_id,
        restaurant_id=restaurant_id,
        livreur_id=livreur_id,
        statut=statut,
        statut_livraison=statut_livraison,
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


def commande_payload(user_id, restaurant_id, plat_ids):
    return {
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "plat_ids": plat_ids,
    }


def seed_order_context(db_session):
    client_user, client_password = create_user_in_db(db_session)
    owner, owner_password = create_user_in_db(
        db_session,
        username="owner",
        email="owner@example.com",
        role="restaurant_owner",
    )
    restaurant = create_restaurant_in_db(db_session, owner_id=owner.id)
    first_plat = create_plat_in_db(
        db_session,
        restaurant.id,
        nom="Burger maison",
        prix=12.5,
    )
    second_plat = create_plat_in_db(
        db_session,
        restaurant.id,
        nom="Frites",
        prix=4.0,
    )
    return {
        "client": client_user,
        "client_password": client_password,
        "owner": owner,
        "owner_password": owner_password,
        "restaurant": restaurant,
        "plats": [first_plat, second_plat],
    }


def test_create_commande_requires_authentication(client, db_session):
    context = seed_order_context(db_session)

    response = client.post(
        "/commandes/",
        json=commande_payload(
            context["client"].id,
            context["restaurant"].id,
            [context["plats"][0].id],
        ),
    )

    assert response.status_code == 401


def test_user_can_create_own_commande_and_total_is_calculated(client, db_session):
    context = seed_order_context(db_session)
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.post(
        "/commandes/",
        json=commande_payload(
            context["client"].id,
            context["restaurant"].id,
            [plat.id for plat in context["plats"]],
        ),
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == context["client"].id
    assert data["restaurant_id"] == context["restaurant"].id
    assert data["livreur_id"] is None
    assert data["statut"] == "en_attente"
    assert data["statut_livraison"] == "non_assignee"
    assert data["prix_total"] == 16.5
    assert set(data["plat_ids"]) == {plat.id for plat in context["plats"]}
    assert data["created_at"]


def test_user_cannot_create_commande_for_another_user(client, db_session):
    context = seed_order_context(db_session)
    other_user, _ = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.post(
        "/commandes/",
        json=commande_payload(
            other_user.id,
            context["restaurant"].id,
            [context["plats"][0].id],
        ),
        headers=headers,
    )

    assert response.status_code == 403


def test_create_commande_returns_404_when_user_does_not_exist(client, db_session):
    context = seed_order_context(db_session)
    admin, admin_password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    headers = auth_headers(client, admin.email, admin_password)

    response = client.post(
        "/commandes/",
        json=commande_payload(
            9999,
            context["restaurant"].id,
            [context["plats"][0].id],
        ),
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Utilisateur introuvable"


def test_create_commande_returns_404_when_restaurant_does_not_exist(client, db_session):
    context = seed_order_context(db_session)
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.post(
        "/commandes/",
        json=commande_payload(context["client"].id, 9999, [context["plats"][0].id]),
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant introuvable"


def test_create_commande_returns_404_when_plat_does_not_exist(client, db_session):
    context = seed_order_context(db_session)
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.post(
        "/commandes/",
        json=commande_payload(context["client"].id, context["restaurant"].id, [9999]),
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Un ou plusieurs plats sont introuvables"


def test_create_commande_rejects_plat_from_another_restaurant(client, db_session):
    context = seed_order_context(db_session)
    other_restaurant = create_restaurant_in_db(db_session, name="Autre restaurant")
    other_plat = create_plat_in_db(db_session, other_restaurant.id, nom="Pizza")
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.post(
        "/commandes/",
        json=commande_payload(
            context["client"].id,
            context["restaurant"].id,
            [context["plats"][0].id, other_plat.id],
        ),
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Tous les plats doivent appartenir au restaurant de la commande"


def test_admin_can_list_all_commandes(client, db_session):
    context = seed_order_context(db_session)
    create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
    )
    admin, admin_password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    headers = auth_headers(client, admin.email, admin_password)

    response = client.get("/commandes/", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_regular_user_cannot_list_all_commandes(client, db_session):
    context = seed_order_context(db_session)
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.get("/commandes/", headers=headers)

    assert response.status_code == 403


def test_user_can_get_own_commandes(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
    )
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.get(f"/commandes/user/{context['client'].id}", headers=headers)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [commande.id]


def test_user_cannot_get_another_users_commandes(client, db_session):
    context = seed_order_context(db_session)
    other_user, _ = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.get(f"/commandes/user/{other_user.id}", headers=headers)

    assert response.status_code == 403


def test_restaurant_owner_can_get_commandes_by_restaurant(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
    )
    headers = auth_headers(client, context["owner"].email, context["owner_password"])

    response = client.get(
        f"/commandes/restaurant/{context['restaurant'].id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [commande.id]


def test_non_owner_cannot_get_commandes_by_restaurant(client, db_session):
    context = seed_order_context(db_session)
    other_user, password = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    headers = auth_headers(client, other_user.email, password)

    response = client.get(
        f"/commandes/restaurant/{context['restaurant'].id}",
        headers=headers,
    )

    assert response.status_code == 403


def test_allowed_user_can_get_commande_by_id(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
    )
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.get(f"/commandes/{commande.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == commande.id


def test_unrelated_user_cannot_get_commande_by_id(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
    )
    other_user, password = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    headers = auth_headers(client, other_user.email, password)

    response = client.get(f"/commandes/{commande.id}", headers=headers)

    assert response.status_code == 403


def test_get_missing_commande_returns_404_for_authenticated_user(client, db_session):
    context = seed_order_context(db_session)
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.get("/commandes/9999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Commande introuvable"


def test_get_livreur_by_commande_returns_assigned_livreur(client, db_session):
    context = seed_order_context(db_session)
    livreur_user, _ = create_user_in_db(
        db_session,
        username="livreur",
        email="livreur@example.com",
        role="livreur",
    )
    livreur = create_livreur_in_db(db_session, livreur_user.id)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
        statut="prete",
        statut_livraison="assignee",
        livreur_id=livreur.id,
    )
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.get(f"/commandes/{commande.id}/livreur", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == livreur.id
    assert response.json()["user_id"] == livreur_user.id


def test_get_livreur_by_commande_returns_404_when_unassigned(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
    )
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.get(f"/commandes/{commande.id}/livreur", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Aucun livreur assigné à cette commande"


def test_available_for_delivery_requires_livreur_profile(client, db_session):
    context = seed_order_context(db_session)
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.get("/commandes/available-for-delivery", headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Profil livreur requis"


def test_livreur_can_list_available_commandes_and_claim_one(client, db_session):
    context = seed_order_context(db_session)
    livreur_user, livreur_password = create_user_in_db(
        db_session,
        username="livreur",
        email="livreur@example.com",
        role="livreur",
    )
    livreur = create_livreur_in_db(db_session, livreur_user.id)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
        statut="prete",
    )
    headers = auth_headers(client, livreur_user.email, livreur_password)

    list_response = client.get("/commandes/available-for-delivery", headers=headers)
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [commande.id]

    claim_response = client.patch(
        f"/commandes/{commande.id}/claim-delivery",
        headers=headers,
    )
    assert claim_response.status_code == 200
    assert claim_response.json()["livreur_id"] == livreur.id
    assert claim_response.json()["statut_livraison"] == "assignee"


def test_livreur_cannot_claim_unavailable_commande(client, db_session):
    context = seed_order_context(db_session)
    livreur_user, livreur_password = create_user_in_db(
        db_session,
        username="livreur",
        email="livreur@example.com",
        role="livreur",
    )
    create_livreur_in_db(db_session, livreur_user.id)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
        statut="en_attente",
    )
    headers = auth_headers(client, livreur_user.email, livreur_password)

    response = client.patch(f"/commandes/{commande.id}/claim-delivery", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Commande non disponible pour livraison"


def test_assigned_livreur_can_progress_livraison_until_delivered(client, db_session):
    context = seed_order_context(db_session)
    livreur_user, livreur_password = create_user_in_db(
        db_session,
        username="livreur",
        email="livreur@example.com",
        role="livreur",
    )
    livreur = create_livreur_in_db(db_session, livreur_user.id)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
        statut="prete",
        statut_livraison="assignee",
        livreur_id=livreur.id,
    )
    headers = auth_headers(client, livreur_user.email, livreur_password)

    first_response = client.patch(
        f"/commandes/{commande.id}/livraison-status",
        json={"statut_livraison": "recuperee"},
        headers=headers,
    )
    second_response = client.patch(
        f"/commandes/{commande.id}/livraison-status",
        json={"statut_livraison": "en_route"},
        headers=headers,
    )
    third_response = client.patch(
        f"/commandes/{commande.id}/livraison-status",
        json={"statut_livraison": "livree"},
        headers=headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert third_response.status_code == 200
    assert third_response.json()["statut_livraison"] == "livree"
    assert third_response.json()["statut"] == "terminee"


def test_livraison_status_rejects_invalid_transition(client, db_session):
    context = seed_order_context(db_session)
    livreur_user, livreur_password = create_user_in_db(
        db_session,
        username="livreur",
        email="livreur@example.com",
        role="livreur",
    )
    livreur = create_livreur_in_db(db_session, livreur_user.id)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
        statut="prete",
        statut_livraison="assignee",
        livreur_id=livreur.id,
    )
    headers = auth_headers(client, livreur_user.email, livreur_password)

    response = client.patch(
        f"/commandes/{commande.id}/livraison-status",
        json={"statut_livraison": "livree"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Transition de livraison invalide"


def test_unassigned_livreur_cannot_update_livraison_status(client, db_session):
    context = seed_order_context(db_session)
    livreur_user, livreur_password = create_user_in_db(
        db_session,
        username="livreur",
        email="livreur@example.com",
        role="livreur",
    )
    create_livreur_in_db(db_session, livreur_user.id)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
        statut="prete",
        statut_livraison="assignee",
    )
    headers = auth_headers(client, livreur_user.email, livreur_password)

    response = client.patch(
        f"/commandes/{commande.id}/livraison-status",
        json={"statut_livraison": "recuperee"},
        headers=headers,
    )

    assert response.status_code == 403


def test_restaurant_owner_can_update_commande_status_and_plats(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        [context["plats"][0]],
    )
    headers = auth_headers(client, context["owner"].email, context["owner_password"])

    response = client.patch(
        f"/commandes/{commande.id}",
        json={
            "statut": "acceptee",
            "plat_ids": [plat.id for plat in context["plats"]],
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["statut"] == "acceptee"
    assert data["prix_total"] == 16.5
    assert set(data["plat_ids"]) == {plat.id for plat in context["plats"]}


def test_update_commande_rejects_invalid_status_transition(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
    )
    headers = auth_headers(client, context["owner"].email, context["owner_password"])

    response = client.patch(
        f"/commandes/{commande.id}",
        json={"statut": "prete"},
        headers=headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Transition de commande invalide"


def test_non_owner_cannot_update_commande(client, db_session):
    context = seed_order_context(db_session)
    other_user, password = create_user_in_db(
        db_session,
        username="other",
        email="other@example.com",
    )
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
    )
    headers = auth_headers(client, other_user.email, password)

    response = client.patch(
        f"/commandes/{commande.id}",
        json={"statut": "acceptee"},
        headers=headers,
    )

    assert response.status_code == 403


def test_user_can_delete_own_pending_commande(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
    )
    commande_id = commande.id
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.delete(f"/commandes/{commande_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == commande_id
    assert db_session.query(Commande).filter(Commande.id == commande_id).first() is None


def test_user_cannot_delete_accepted_commande(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
        statut="acceptee",
    )
    headers = auth_headers(client, context["client"].email, context["client_password"])

    response = client.delete(f"/commandes/{commande.id}", headers=headers)

    assert response.status_code == 403
    assert db_session.query(Commande).filter(Commande.id == commande.id).first() is not None


def test_restaurant_owner_can_delete_preparation_commande(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
        statut="en_preparation",
    )
    commande_id = commande.id
    headers = auth_headers(client, context["owner"].email, context["owner_password"])

    response = client.delete(f"/commandes/{commande_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == commande_id
    assert db_session.query(Commande).filter(Commande.id == commande_id).first() is None


def test_admin_can_delete_any_commande(client, db_session):
    context = seed_order_context(db_session)
    commande = create_commande_in_db(
        db_session,
        context["client"].id,
        context["restaurant"].id,
        context["plats"],
        statut="terminee",
    )
    commande_id = commande.id
    admin, admin_password = create_user_in_db(
        db_session,
        username="admin",
        email="admin@example.com",
        role="admin",
    )
    headers = auth_headers(client, admin.email, admin_password)

    response = client.delete(f"/commandes/{commande_id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == commande_id
    assert db_session.query(Commande).filter(Commande.id == commande_id).first() is None
