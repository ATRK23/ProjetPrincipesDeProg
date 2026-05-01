from sqlalchemy.orm import Session

from app.models.command import Commande
from app.models.plat import Plat
from app.schemas.command import CommandeCreate, CommandeUpdate


def get_commande(db: Session, commande_id: int):
    return db.query(Commande).filter(Commande.id == commande_id).first()


def get_commandes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Commande).offset(skip).limit(limit).all()


def get_commandes_by_user(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100
):
    return (
        db.query(Commande)
        .filter(Commande.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_commandes_by_restaurant(
    db: Session,
    restaurant_id: int,
    skip: int = 0,
    limit: int = 100
):
    return (
        db.query(Commande)
        .filter(Commande.restaurant_id == restaurant_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_plats_by_ids(db: Session, plat_ids: list[int]):
    return db.query(Plat).filter(Plat.id.in_(plat_ids)).all()


def calculate_total(plats: list[Plat]):
    return sum(plat.prix for plat in plats)


def create_commande(db: Session, commande: CommandeCreate):
    plats = get_plats_by_ids(db, commande.plat_ids)

    prix_total = calculate_total(plats)

    db_commande = Commande(
        user_id=commande.user_id,
        restaurant_id=commande.restaurant_id,
        prix_total=prix_total,
        plats=plats
    )

    db.add(db_commande)
    db.commit()
    db.refresh(db_commande)

    return db_commande


def update_commande(
    db: Session,
    db_commande: Commande,
    commande_update: CommandeUpdate
):
    update_data = commande_update.model_dump(exclude_unset=True)

    if "plat_ids" in update_data:
        plats = get_plats_by_ids(db, update_data.pop("plat_ids"))
        db_commande.plats = plats
        db_commande.prix_total = calculate_total(plats)

    for key, value in update_data.items():
        setattr(db_commande, key, value)

    db.commit()
    db.refresh(db_commande)

    return db_commande


def delete_commande(db: Session, db_commande: Commande):
    db.delete(db_commande)
    db.commit()

    return db_commande