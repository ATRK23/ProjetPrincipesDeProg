from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.livreur import LivreurCreate, LivreurUpdate, LivreurResponse
from app.crud import livreur as livreur_crud
from app.crud import user as user_crud


router = APIRouter(
    prefix="/livreurs",
    tags=["Livreurs"]
)


@router.post("/", response_model=LivreurResponse, status_code=status.HTTP_201_CREATED)
def create_livreur(livreur: LivreurCreate, db: Session = Depends(get_db)):
    user = user_crud.get_user(db, livreur.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable"
        )

    existing_livreur = livreur_crud.get_livreur_by_user(db, livreur.user_id)

    if existing_livreur:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet utilisateur est déjà livreur"
        )

    return livreur_crud.create_livreur(db, livreur)


@router.get("/", response_model=List[LivreurResponse])
def get_livreurs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return livreur_crud.get_livreurs(db, skip=skip, limit=limit)


@router.get("/user/{user_id}", response_model=LivreurResponse)
def get_livreur_by_user(user_id: int, db: Session = Depends(get_db)):
    livreur = livreur_crud.get_livreur_by_user(db, user_id)

    if livreur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livreur introuvable pour cet utilisateur"
        )

    return livreur


@router.get("/{livreur_id}", response_model=LivreurResponse)
def get_livreur(livreur_id: int, db: Session = Depends(get_db)):
    livreur = livreur_crud.get_livreur(db, livreur_id)

    if livreur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livreur introuvable"
        )

    return livreur


@router.patch("/{livreur_id}", response_model=LivreurResponse)
def update_livreur(
    livreur_id: int,
    livreur_update: LivreurUpdate,
    db: Session = Depends(get_db)
):
    livreur = livreur_crud.get_livreur(db, livreur_id)

    if livreur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livreur introuvable"
        )

    return livreur_crud.update_livreur(db, livreur, livreur_update)


@router.delete("/{livreur_id}", response_model=LivreurResponse)
def delete_livreur(livreur_id: int, db: Session = Depends(get_db)):
    livreur = livreur_crud.get_livreur(db, livreur_id)

    if livreur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livreur introuvable"
        )

    return livreur_crud.delete_livreur(db, livreur)