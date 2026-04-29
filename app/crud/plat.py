from sqlalchemy.orm import Session

from app.models.plat import Plat
from app.schemas.plat import PlatCreate, PlatUpdate


# GETTERS

def get_plat(db: Session, plat_id: int):
    return db.query(Plat).filter(Plat.id == plat_id).first()

def get_plats(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Plat).offset(skip).limit(limit).all()

def get_plats_by_restaurant(db: Session, restaurant_id: int, skip: int = 0, limit: int = 100):
    return (
        db.query(Plat)
        .filter(Plat.restaurant_id == restaurant_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    
# SETTERS

def create_plat(db: Session, plat: PlatCreate):
    db_plat = Plat(
        nom=plat.nom,
        prix=plat.prix,
        description=plat.description,
        ingredients=plat.ingredients,
        allergenes=plat.allergenes,
        is_available=plat.is_available,
        restaurant_id=plat.restaurant_id
    )

    db.add(db_plat)
    db.commit()
    db.refresh(db_plat)

    return db_plat

def update_plat(db: Session, db_plat: Plat, plat_update: PlatUpdate):
    update_data = plat_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_plat, key, value)

    db.commit()
    db.refresh(db_plat)

    return db_plat

def delete_plat(db: Session, db_plat: Plat):
    db.delete(db_plat)
    db.commit()

    return db_plat