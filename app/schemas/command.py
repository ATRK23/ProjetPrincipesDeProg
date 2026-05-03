from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

CommandeStatus = Literal["en_attente", "acceptee", "en_preparation", "prete", "annulee", "terminee"]
LivraisonStatus = Literal["non_assignee", "assignee", "recuperee", "en_route", "livree"]


class CommandeBase(BaseModel):
    user_id: int
    restaurant_id: int
    plat_ids: List[int]


class CommandeCreate(CommandeBase):
    pass


class CommandeUpdate(BaseModel):
    statut: Optional[CommandeStatus] = None
    plat_ids: Optional[List[int]] = None


class CommandeLivraisonStatusUpdate(BaseModel):
    statut_livraison: LivraisonStatus


class CommandeResponse(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    livreur_id: Optional[int] = None
    statut: CommandeStatus
    statut_livraison: LivraisonStatus
    prix_total: float
    created_at: datetime
    plat_ids: List[int]

    model_config = ConfigDict(from_attributes=True)
