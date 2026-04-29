from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.plat import PlatCreate, PlatUpdate, PlatResponse
from app.crud import plat as plat_crud
from app.crud import restaurant as restaurant_crud


router = APIRouter(
    prefix="/plats",
    tags=["Plats"]
)


# POST

@router.post("/", response_model=PlatResponse, status_code=status.HTTP_201_CREATED)
def create_plat(plat: PlatCreate, db: Session = Depends(get_db)):
    restaurant = restaurant_crud.get_restaurant(db, plat.restaurant_id)

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant introuvable"
        )

    return plat_crud.create_plat(db, plat)


# GET

@router.get("/", response_model=List[PlatResponse])
def get_plats(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return plat_crud.get_plats(db, skip=skip, limit=limit)


@router.get("/restaurant/{restaurant_id}", response_model=List[PlatResponse])
def get_plats_by_restaurant(
    restaurant_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    restaurant = restaurant_crud.get_restaurant(db, restaurant_id)

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant introuvable"
        )

    return plat_crud.get_plats_by_restaurant(
        db,
        restaurant_id,
        skip=skip,
        limit=limit
    )


@router.get("/{plat_id}", response_model=PlatResponse)
def get_plat(plat_id: int, db: Session = Depends(get_db)):
    db_plat = plat_crud.get_plat(db, plat_id)

    if db_plat is None:
        raise HTTPException(
            status_code=404,
            detail="Plat introuvable"
        )

    return db_plat


# PATCH

@router.patch("/{plat_id}", response_model=PlatResponse)
def update_plat(
    plat_id: int,
    plat_update: PlatUpdate,
    db: Session = Depends(get_db)
):
    db_plat = plat_crud.get_plat(db, plat_id)

    if db_plat is None:
        raise HTTPException(
            status_code=404,
            detail="Plat introuvable"
        )

    if plat_update.restaurant_id is not None:
        restaurant = restaurant_crud.get_restaurant(db, plat_update.restaurant_id)

        if restaurant is None:
            raise HTTPException(
                status_code=404,
                detail="Restaurant introuvable"
            )

    return plat_crud.update_plat(db, db_plat, plat_update)


# DELETE

@router.delete("/{plat_id}", response_model=PlatResponse)
def delete_plat(plat_id: int, db: Session = Depends(get_db)):
    db_plat = plat_crud.get_plat(db, plat_id)

    if db_plat is None:
        raise HTTPException(
            status_code=404,
            detail="Plat introuvable"
        )

    return plat_crud.delete_plat(db, db_plat)