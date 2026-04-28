from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse
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