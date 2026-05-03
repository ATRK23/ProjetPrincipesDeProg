from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.livreur import LivreurCreate, LivreurUpdate, LivreurResponse
from app.crud import livreur as livreur_crud
from app.crud import user as user_crud
from app.security import ROLE_ADMIN, ROLE_LIVREUR, check_user_is_self_or_admin, get_current_user, require_roles


router = APIRouter(
    prefix="/livreurs",
    tags=["Livreurs"]
)


@router.post("/", response_model=LivreurResponse, status_code=status.HTTP_201_CREATED)
def create_livreur(livreur: LivreurCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    check_user_is_self_or_admin(livreur.user_id, current_user)

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

    db_livreur = livreur_crud.create_livreur(db, livreur)

    user.role = ROLE_LIVREUR
    db.commit()
    db.refresh(user)

    return db_livreur


@router.get("/", response_model=List[LivreurResponse])
def get_livreurs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(require_roles(ROLE_ADMIN))):
    return livreur_crud.get_livreurs(db, skip=skip, limit=limit)


@router.get("/user/{user_id}", response_model=LivreurResponse)
def get_livreur_by_user(user_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    check_user_is_self_or_admin(user_id, current_user)

    livreur = livreur_crud.get_livreur_by_user(db, user_id)

    if livreur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livreur introuvable pour cet utilisateur"
        )

    return livreur


@router.get("/{livreur_id}", response_model=LivreurResponse)
def get_livreur(livreur_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    livreur = livreur_crud.get_livreur(db, livreur_id)

    if livreur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livreur introuvable"
        )

    check_user_is_self_or_admin(livreur.user_id, current_user)

    return livreur


@router.patch("/{livreur_id}", response_model=LivreurResponse)
def update_livreur(livreur_id: int, livreur_update: LivreurUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    livreur = livreur_crud.get_livreur(db, livreur_id)

    if livreur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livreur introuvable"
        )

    check_user_is_self_or_admin(livreur.user_id, current_user)

    return livreur_crud.update_livreur(db, livreur, livreur_update)


@router.delete("/{livreur_id}", response_model=LivreurResponse)
def delete_livreur(livreur_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    livreur = livreur_crud.get_livreur(db, livreur_id)

    if livreur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livreur introuvable"
        )

    check_user_is_self_or_admin(livreur.user_id, current_user)

    return livreur_crud.delete_livreur(db, livreur)