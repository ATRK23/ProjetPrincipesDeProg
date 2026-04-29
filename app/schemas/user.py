from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict

class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    
class UserCreate(UserBase):
    password: str
    
class UserUpdate(UserBase):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    password: Optional[str] = None
    
class UserResponse(UserBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)