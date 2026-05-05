from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

UserRole = Literal["user", "admin", "livreur", "restaurant_owner"]

class UserBase(BaseModel):
    username: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, email: str) -> str:
        value = email.strip().lower()
        local, separator, domain = value.partition("@")

        if not separator or not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("Adresse email invalide")

        return value
    
class UserCreate(UserBase):
    password: str
    
class UserUpdate(UserBase):
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    password: Optional[str] = None
    
class UserResponse(UserBase):
    id: int
    role: UserRole
    
    model_config = ConfigDict(from_attributes=True)