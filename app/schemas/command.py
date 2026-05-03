from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CommandeBase(BaseModel):
    user_id: int
    restaurant_id: int
    plat_ids: List[int]


class CommandeCreate(CommandeBase):
    pass


class CommandeUpdate(BaseModel):
    statut: Optional[str] = None
    livreur_id: Optional[int] = None
    plat_ids: Optional[List[int]] = None


class CommandeLivraisonStatusUpdate(BaseModel):
    statut: str


class CommandeResponse(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    livreur_id: Optional[int] = None
    statut: str
    prix_total: float
    created_at: datetime
    plat_ids: List[int]

    model_config = ConfigDict(from_attributes=True)
