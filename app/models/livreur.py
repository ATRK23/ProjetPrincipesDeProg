from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Livreur(Base):
    __tablename__ = "livreurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    telephone = Column(String(30), nullable=True)
    moyen_transport = Column(String(50), nullable=True)
    note_moyenne = Column(Float, default=0.0, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    user = relationship("User", back_populates="livreur")
    commandes = relationship("Commande", back_populates="livreur")