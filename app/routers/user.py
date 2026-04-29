from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.crud import user as user_crud

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


# POST

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = user_crud.get_user_by_email(db, user.email)
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail = "Un utilisateur avec cet email existe déjà."
        )
        
    return user_crud.create_user(db, user)


# GET

@router.get("/", response_model=List[UserResponse])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user_crud.get_users(db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = user_crud.get_user(db, user_id)
    
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )
        
    return db_user


# Patch

@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    db_user = user_crud.get_user(db, user_id)
    
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur Introuvable"
        )
        
    return user_crud.update_user(db, db_user, user_update)


# Delete

@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = user_crud.get_user(db, user_id)
    
    if db_user is None:
        raise HTTPException(
            status_code=404,
            detail="Utilisateur Introuvable"
        )
        
    return user_crud.delete_user(db, db_user)