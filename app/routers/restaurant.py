from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate, RestaurantResponse
from app.crud import restaurant as restaurant_crud

router = APIRouter(
    prefix="/restaurants",
    tags=["Restaurants"]
)


# POST

@router.post("/", response_model=RestaurantResponse, status_code=status.HTTP_201_CREATED)
def create_restaurant(restaurant: RestaurantCreate, db: Session = Depends(get_db)):
    return restaurant_crud.create_restaurant(db, restaurant)


# GET

@router.get("/", response_model=List[RestaurantResponse])
def get_restaurants(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return restaurant_crud.get_restaurants(db, skip=skip, limit=limit)

@router.get("/{restaurant_id}", response_model=RestaurantResponse)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    db_restaurant = restaurant_crud.get_restaurant(db, restaurant_id)

    if db_restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant introuvable"
        )

    return db_restaurant


# PATCH

@router.patch("/{restaurant_id}", response_model=RestaurantResponse)
def update_restaurant(restaurant_id: int, restaurant_update: RestaurantUpdate, db: Session = Depends(get_db)):
    db_restaurant = restaurant_crud.get_restaurant(db, restaurant_id)

    if db_restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant introuvable"
        )

    return restaurant_crud.update_restaurant(db, db_restaurant, restaurant_update)


# DELETE

@router.delete("/{restaurant_id}", response_model=RestaurantResponse)
def delete_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    db_restaurant = restaurant_crud.get_restaurant(db, restaurant_id)

    if db_restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant introuvable"
        )

    return restaurant_crud.delete_restaurant(db, db_restaurant)