from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CommandeBase(BaseModel):
    user_id: int
    restaurant_id: int
    plat_ids: List[int]


class CommandeCreate(CommandeBase):
    pass


class CommandeUpdate(BaseModel):
    statut: Optional[str] = None
    plat_ids: Optional[List[int]] = None


class CommandeResponse(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    statut: str
    prix_total: float
    created_at: datetime
    plat_ids: List[int]

    class Config:
        from_attributes = True