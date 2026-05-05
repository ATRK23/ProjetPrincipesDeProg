from sqlalchemy.orm import Session

from app.models.command import Commande, CommandePlat
from app.models.plat import Plat
from app.schemas.command import CommandeCreate, CommandeItem, CommandeUpdate


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


def get_commandes_available_for_delivery(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(Commande)
        .filter(Commande.statut.in_(["en_preparation", "prete"]))
        .filter(Commande.statut_livraison == "non_assignee")
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_plats_by_ids(db: Session, plat_ids: list[int]):
    return db.query(Plat).filter(Plat.id.in_(plat_ids)).all()


def calculate_total(plats_by_id: dict[int, Plat], items: list[CommandeItem]):
    return sum(plats_by_id[item.plat_id].prix * item.quantite for item in items)


def build_commande_items(items: list[CommandeItem]):
    return [
        CommandePlat(plat_id=item.plat_id, quantite=item.quantite)
        for item in items
    ]


def get_plats_by_items(db: Session, items: list[CommandeItem]):
    return get_plats_by_ids(db, [item.plat_id for item in items])


def create_commande(db: Session, commande: CommandeCreate):
    plats = get_plats_by_items(db, commande.items)
    plats_by_id = {plat.id: plat for plat in plats}

    prix_total = calculate_total(plats_by_id, commande.items)

    db_commande = Commande(
        user_id=commande.user_id,
        restaurant_id=commande.restaurant_id,
        livreur_id=None,
        statut_livraison="non_assignee",
        prix_total=prix_total,
        items=build_commande_items(commande.items),
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

    if "items" in update_data:
        items = [CommandeItem(**item) for item in update_data.pop("items")]
        plats = get_plats_by_items(db, items)
        plats_by_id = {plat.id: plat for plat in plats}
        db_commande.items = build_commande_items(items)
        db_commande.prix_total = calculate_total(plats_by_id, items)

    for key, value in update_data.items():
        setattr(db_commande, key, value)

    db.commit()
    db.refresh(db_commande)

    return db_commande


def claim_commande_delivery(db: Session, db_commande: Commande, livreur_id: int):
    db_commande.livreur_id = livreur_id
    db_commande.statut_livraison = "assignee"

    db.commit()
    db.refresh(db_commande)

    return db_commande


def update_commande_status(db: Session, db_commande: Commande, statut: str):
    db_commande.statut = statut

    db.commit()
    db.refresh(db_commande)

    return db_commande


def update_livraison_status(db: Session, db_commande: Commande, statut_livraison: str):
    db_commande.statut_livraison = statut_livraison

    if statut_livraison == "livree":
        db_commande.statut = "terminee"

    db.commit()
    db.refresh(db_commande)

    return db_commande


def delete_commande(db: Session, db_commande: Commande):
    db.delete(db_commande)
    db.commit()

    return db_commande
