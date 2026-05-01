from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.command import CommandeCreate, CommandeUpdate, CommandeResponse
from app.crud import command as commande_crud
from app.crud import user as user_crud
from app.crud import restaurant as restaurant_crud


router = APIRouter(
    prefix="/commandes",
    tags=["Commandes"]
)


def format_commande_response(commande):
    return CommandeResponse(
        id=commande.id,
        user_id=commande.user_id,
        restaurant_id=commande.restaurant_id,
        statut=commande.statut,
        prix_total=commande.prix_total,
        created_at=commande.created_at,
        plat_ids=[plat.id for plat in commande.plats]
    )


def validate_commande_data(
    db: Session,
    user_id: int,
    restaurant_id: int,
    plat_ids: List[int]
):
    user = user_crud.get_user(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    restaurant = restaurant_crud.get_restaurant(db, restaurant_id)

    if restaurant is None:
        raise HTTPException(
            status_code=404,
            detail="Restaurant introuvable"
        )

    plats = commande_crud.get_plats_by_ids(db, plat_ids)

    if len(plats) != len(set(plat_ids)):
        raise HTTPException(
            status_code=404,
            detail="Un ou plusieurs plats sont introuvables"
        )

    for plat in plats:
        if plat.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=400,
                detail="Tous les plats doivent appartenir au restaurant de la commande"
            )

    return plats


@router.post("/", response_model=CommandeResponse, status_code=status.HTTP_201_CREATED)
def create_commande(
    commande: CommandeCreate,
    db: Session = Depends(get_db)
):
    validate_commande_data(
        db,
        commande.user_id,
        commande.restaurant_id,
        commande.plat_ids
    )

    db_commande = commande_crud.create_commande(db, commande)

    return format_commande_response(db_commande)


@router.get("/", response_model=List[CommandeResponse])
def get_commandes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    commandes = commande_crud.get_commandes(db, skip=skip, limit=limit)

    return [format_commande_response(commande) for commande in commandes]


@router.get("/user/{user_id}", response_model=List[CommandeResponse])
def get_commandes_by_user(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    user = user_crud.get_user(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    commandes = commande_crud.get_commandes_by_user(
        db,
        user_id,
        skip=skip,
        limit=limit
    )

    return [format_commande_response(commande) for commande in commandes]


@router.get("/restaurant/{restaurant_id}", response_model=List[CommandeResponse])
def get_commandes_by_restaurant(
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

    commandes = commande_crud.get_commandes_by_restaurant(
        db,
        restaurant_id,
        skip=skip,
        limit=limit
    )

    return [format_commande_response(commande) for commande in commandes]


@router.get("/{commande_id}", response_model=CommandeResponse)
def get_commande(
    commande_id: int,
    db: Session = Depends(get_db)
):
    db_commande = commande_crud.get_commande(db, commande_id)

    if db_commande is None:
        raise HTTPException(
            status_code=404,
            detail="Commande introuvable"
        )

    return format_commande_response(db_commande)


@router.patch("/{commande_id}", response_model=CommandeResponse)
def update_commande(
    commande_id: int,
    commande_update: CommandeUpdate,
    db: Session = Depends(get_db)
):
    db_commande = commande_crud.get_commande(db, commande_id)

    if db_commande is None:
        raise HTTPException(
            status_code=404,
            detail="Commande introuvable"
        )

    if commande_update.plat_ids is not None:
        validate_commande_data(
            db,
            db_commande.user_id,
            db_commande.restaurant_id,
            commande_update.plat_ids
        )

    updated_commande = commande_crud.update_commande(
        db,
        db_commande,
        commande_update
    )

    return format_commande_response(updated_commande)


@router.delete("/{commande_id}", response_model=CommandeResponse)
def delete_commande(
    commande_id: int,
    db: Session = Depends(get_db)
):
    db_commande = commande_crud.get_commande(db, commande_id)

    if db_commande is None:
        raise HTTPException(
            status_code=404,
            detail="Commande introuvable"
        )

    response = format_commande_response(db_commande)

    commande_crud.delete_commande(db, db_commande)

    return response