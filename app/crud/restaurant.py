from sqlalchemy.orm import Session

from app.models.restaurant import Restaurant
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate


# Getters

def get_restaurant(db: Session, restaurant_id: int):
    return db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()

def get_restaurants(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Restaurant).offset(skip).limit(limit).all()


# Setters

def create_restaurant(db: Session, restaurant: RestaurantCreate):
    
    db_restaurant = Restaurant(
        name=restaurant.username,
        adress=restaurant.adress,
        phone=restaurant.phone,
        description=restaurant.description,
        is_open=restaurant.is_open
    )
    
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    
    return db_restaurant

def update_restaurant(db: Session, db_restaurant: Restaurant, restaurant_update: RestaurantUpdate):
    update_data = restaurant_update.model_dump(exclude_unset=True)
        
    for key, value in update_data.items():
        setattr(db_restaurant, key, value)
        
    db.commit()
    db.refresh(db_restaurant)
    
    return db_restaurant

def delete_restaurant(db: Session, db_restaurant: Restaurant):
    db.delete(db_restaurant)
    db.commit()
    
    return db_restaurant