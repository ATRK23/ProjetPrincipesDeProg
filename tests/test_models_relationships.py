import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Commande, CommandePlat, Livreur, Plat, Restaurant, User
from app.models.command import commande_plat
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


def create_user(
    db_session,
    username="arthur",
    email="arthur@example.com",
    role="user",
):
    user = User(
        username=username,
        email=email,
        role=role,
        hashed_password=hash_password("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def create_restaurant(db_session, owner_id=None, name="Le Bon Plat"):
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


def create_plat(db_session, restaurant_id, nom="Burger maison", prix=12.5):
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


def create_livreur(db_session, user_id):
    livreur = Livreur(
        nom="Arthur Livreur",
        telephone="0600000000",
        moyen_transport="velo",
        note_moyenne=4.5,
        user_id=user_id,
    )
    db_session.add(livreur)
    db_session.commit()
    db_session.refresh(livreur)
    return livreur


def create_commande(
    db_session,
    user_id,
    restaurant_id,
    plats,
    livreur_id=None,
):
    commande = Commande(
        user_id=user_id,
        restaurant_id=restaurant_id,
        livreur_id=livreur_id,
        statut="en_attente",
        statut_livraison="non_assignee",
        prix_total=sum(plat.prix for plat in plats),
        items=[CommandePlat(plat=plat, quantite=1) for plat in plats],
    )
    db_session.add(commande)
    db_session.commit()
    db_session.refresh(commande)
    return commande


def test_user_livreur_is_one_to_one_relationship(db_session):
    user = create_user(db_session, role="livreur")
    livreur = create_livreur(db_session, user.id)

    db_session.refresh(user)
    db_session.refresh(livreur)

    assert user.livreur.id == livreur.id
    assert livreur.user.id == user.id
    assert livreur.user_id == user.id


def test_user_livreur_foreign_key_is_unique(db_session):
    user = create_user(db_session, role="livreur")
    first_livreur = create_livreur(db_session, user.id)
    duplicate_livreur = Livreur(
        nom="Duplicate",
        telephone="0611111111",
        moyen_transport="scooter",
        note_moyenne=4.0,
        user_id=user.id,
    )

    db_session.add(duplicate_livreur)

    with pytest.raises(Exception):
        db_session.commit()

    db_session.rollback()
    assert db_session.query(Livreur).filter(Livreur.user_id == user.id).one().id == first_livreur.id


def test_user_restaurants_is_one_to_many_relationship(db_session):
    owner = create_user(
        db_session,
        username="owner",
        email="owner@example.com",
        role="restaurant_owner",
    )
    first_restaurant = create_restaurant(db_session, owner_id=owner.id, name="Premier")
    second_restaurant = create_restaurant(db_session, owner_id=owner.id, name="Second")

    db_session.refresh(owner)

    assert {restaurant.id for restaurant in owner.restaurants} == {
        first_restaurant.id,
        second_restaurant.id,
    }
    assert first_restaurant.owner.id == owner.id
    assert second_restaurant.owner.id == owner.id


def test_restaurant_plats_is_one_to_many_relationship(db_session):
    restaurant = create_restaurant(db_session)
    first_plat = create_plat(db_session, restaurant.id, nom="Burger")
    second_plat = create_plat(db_session, restaurant.id, nom="Frites")

    db_session.refresh(restaurant)

    assert {plat.id for plat in restaurant.plats} == {first_plat.id, second_plat.id}
    assert first_plat.restaurant.id == restaurant.id
    assert second_plat.restaurant.id == restaurant.id


def test_user_commandes_is_one_to_many_relationship(db_session):
    user = create_user(db_session)
    restaurant = create_restaurant(db_session)
    plat = create_plat(db_session, restaurant.id)
    first_commande = create_commande(db_session, user.id, restaurant.id, [plat])
    second_commande = create_commande(db_session, user.id, restaurant.id, [plat])

    db_session.refresh(user)

    assert {commande.id for commande in user.commandes} == {
        first_commande.id,
        second_commande.id,
    }
    assert first_commande.user.id == user.id
    assert second_commande.user.id == user.id


def test_restaurant_commandes_is_one_to_many_relationship(db_session):
    user = create_user(db_session)
    restaurant = create_restaurant(db_session)
    plat = create_plat(db_session, restaurant.id)
    first_commande = create_commande(db_session, user.id, restaurant.id, [plat])
    second_commande = create_commande(db_session, user.id, restaurant.id, [plat])

    db_session.refresh(restaurant)

    assert {commande.id for commande in restaurant.commandes} == {
        first_commande.id,
        second_commande.id,
    }
    assert first_commande.restaurant.id == restaurant.id
    assert second_commande.restaurant.id == restaurant.id


def test_livreur_commandes_is_one_to_many_relationship(db_session):
    user = create_user(db_session)
    livreur_user = create_user(
        db_session,
        username="livreur",
        email="livreur@example.com",
        role="livreur",
    )
    livreur = create_livreur(db_session, livreur_user.id)
    restaurant = create_restaurant(db_session)
    plat = create_plat(db_session, restaurant.id)
    first_commande = create_commande(
        db_session,
        user.id,
        restaurant.id,
        [plat],
        livreur_id=livreur.id,
    )
    second_commande = create_commande(
        db_session,
        user.id,
        restaurant.id,
        [plat],
        livreur_id=livreur.id,
    )

    db_session.refresh(livreur)

    assert {commande.id for commande in livreur.commandes} == {
        first_commande.id,
        second_commande.id,
    }
    assert first_commande.livreur.id == livreur.id
    assert second_commande.livreur.id == livreur.id


def test_commande_plats_is_many_to_many_relationship(db_session):
    user = create_user(db_session)
    restaurant = create_restaurant(db_session)
    burger = create_plat(db_session, restaurant.id, nom="Burger", prix=12.5)
    fries = create_plat(db_session, restaurant.id, nom="Frites", prix=4.0)

    commande = create_commande(db_session, user.id, restaurant.id, [burger, fries])

    db_session.refresh(commande)
    db_session.refresh(burger)
    db_session.refresh(fries)

    assert {plat.id for plat in commande.plats} == {burger.id, fries.id}
    assert commande.id in {commande.id for commande in burger.commandes}
    assert commande.id in {commande.id for commande in fries.commandes}


def test_commande_plat_association_table_contains_pairs(db_session):
    user = create_user(db_session)
    restaurant = create_restaurant(db_session)
    burger = create_plat(db_session, restaurant.id, nom="Burger")
    fries = create_plat(db_session, restaurant.id, nom="Frites")
    commande = create_commande(db_session, user.id, restaurant.id, [burger, fries])

    rows = db_session.execute(commande_plat.select()).all()

    assert {(row.commande_id, row.plat_id, row.quantite) for row in rows} == {
        (commande.id, burger.id, 1),
        (commande.id, fries.id, 1),
    }


def test_deleting_user_cascades_to_livreur_and_commandes(db_session):
    user = create_user(db_session, role="livreur")
    livreur = create_livreur(db_session, user.id)
    restaurant = create_restaurant(db_session)
    plat = create_plat(db_session, restaurant.id)
    commande = create_commande(
        db_session,
        user.id,
        restaurant.id,
        [plat],
        livreur_id=livreur.id,
    )
    user_id = user.id
    livreur_id = livreur.id
    commande_id = commande.id

    db_session.delete(user)
    db_session.commit()

    assert db_session.query(User).filter(User.id == user_id).first() is None
    assert db_session.query(Livreur).filter(Livreur.id == livreur_id).first() is None
    assert db_session.query(Commande).filter(Commande.id == commande_id).first() is None


def test_deleting_restaurant_cascades_to_plats_and_commandes(db_session):
    user = create_user(db_session)
    restaurant = create_restaurant(db_session)
    plat = create_plat(db_session, restaurant.id)
    commande = create_commande(db_session, user.id, restaurant.id, [plat])
    restaurant_id = restaurant.id
    plat_id = plat.id
    commande_id = commande.id

    db_session.delete(restaurant)
    db_session.commit()

    assert db_session.query(Restaurant).filter(Restaurant.id == restaurant_id).first() is None
    assert db_session.query(Plat).filter(Plat.id == plat_id).first() is None
    assert db_session.query(Commande).filter(Commande.id == commande_id).first() is None
