from typing import Optional

from pydantic import BaseModel, ConfigDict


class PlatBase(BaseModel):
    nom: str
    prix: float
    description: Optional[str] = None
    ingredients: Optional[str] = None
    allergenes: Optional[str] = None
    is_available: bool = True
    
class PlatCreate(PlatBase):
    restaurant_id: int
    
class PlatUpdate(BaseModel):
    nom: Optional[str] = None
    prix: Optional[float] = None
    description: Optional[str] = None
    ingredients: Optional[str] = None
    allergenes: Optional[str] = None
    is_available: Optional[bool] = None
    restaurant_id: Optional[int] = None
    
class PlatResponse(PlatBase):
    id: int
    restaurant_id: int
    
    model_config = ConfigDict(from_attributes=True)