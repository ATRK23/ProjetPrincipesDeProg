from typing import Optional

from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone: Optional[str] = None
    adress: Optional[str] = None
    
class UserCreate(UserBase):
    password: str
    
class UserUpdate(UserBase):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    adress: Optional[str] = None
    password: Optional[str] = None
    
class UserResponse(UserBase):
    id: int
    
    class Config:
        from_attributes = True