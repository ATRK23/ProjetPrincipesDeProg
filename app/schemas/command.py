from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

CommandeStatus = Literal["en_attente", "acceptee", "en_preparation", "prete", "annulee", "terminee"]
LivraisonStatus = Literal["non_assignee", "assignee", "recuperee", "en_route", "livree"]


class CommandeItem(BaseModel):
    plat_id: int
    quantite: int = Field(gt=0)


class CommandeBase(BaseModel):
    user_id: int
    restaurant_id: int
    items: List[CommandeItem] = Field(min_length=1)


class CommandeCreate(CommandeBase):
    pass


class CommandeUpdate(BaseModel):
    statut: Optional[CommandeStatus] = None
    items: Optional[List[CommandeItem]] = Field(default=None, min_length=1)


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
    items: List[CommandeItem]

    model_config = ConfigDict(from_attributes=True)
