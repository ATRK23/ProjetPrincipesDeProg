from sqlalchemy.orm import Session

from app.models.livreur import Livreur
from app.schemas.livreur import LivreurCreate, LivreurUpdate


def get_livreur(db: Session, livreur_id: int):
    return db.query(Livreur).filter(Livreur.id == livreur_id).first()


def get_livreur_by_user(db: Session, user_id: int):
    return db.query(Livreur).filter(Livreur.user_id == user_id).first()


def get_livreurs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Livreur).offset(skip).limit(limit).all()


def create_livreur(db: Session, livreur: LivreurCreate):
    db_livreur = Livreur(
        nom=livreur.nom,
        telephone=livreur.telephone,
        moyen_transport=livreur.moyen_transport,
        note_moyenne=livreur.note_moyenne,
        user_id=livreur.user_id
    )

    db.add(db_livreur)
    db.commit()
    db.refresh(db_livreur)

    return db_livreur


def update_livreur(
    db: Session,
    db_livreur: Livreur,
    livreur_update: LivreurUpdate
):
    update_data = livreur_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_livreur, key, value)

    db.commit()
    db.refresh(db_livreur)

    return db_livreur


def delete_livreur(db: Session, db_livreur: Livreur):
    db.delete(db_livreur)
    db.commit()

    return db_livreur