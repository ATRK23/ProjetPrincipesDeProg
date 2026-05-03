from typing import Optional

from pydantic import BaseModel


class LivreurBase(BaseModel):
    nom: str
    telephone: Optional[str] = None
    moyen_transport: Optional[str] = None
    note_moyenne: float = 0.0


class LivreurCreate(LivreurBase):
    user_id: int


class LivreurUpdate(BaseModel):
    nom: Optional[str] = None
    telephone: Optional[str] = None
    moyen_transport: Optional[str] = None
    note_moyenne: Optional[float] = None


class LivreurResponse(LivreurBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True