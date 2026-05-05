from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class CommandePlat(Base):
    __tablename__ = "commande_plat"

    commande_id = Column(Integer, ForeignKey("commandes.id"), primary_key=True)
    plat_id = Column(Integer, ForeignKey("plats.id"), primary_key=True)
    quantite = Column(Integer, nullable=False, default=1)

    commande = relationship("Commande", back_populates="items")
    plat = relationship("Plat", back_populates="commande_items")


commande_plat = CommandePlat.__table__


class Commande(Base):
    __tablename__ = "commandes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    livreur_id = Column(Integer, ForeignKey("livreurs.id"), nullable=True)

    statut = Column(String(50), default="en_attente", nullable=False)
    statut_livraison = Column(String(50), default="non_assignee", nullable=False)
    prix_total = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="commandes")
    restaurant = relationship("Restaurant", back_populates="commandes")
    livreur = relationship("Livreur", back_populates="commandes")
    items = relationship(
        "CommandePlat",
        back_populates="commande",
        cascade="all, delete-orphan",
    )
    plats = relationship(
        "Plat",
        secondary="commande_plat",
        back_populates="commandes",
        viewonly=True,
    )
