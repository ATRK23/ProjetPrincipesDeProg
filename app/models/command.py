from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


commande_plat = Table(
    "commande_plat",
    Base.metadata,
    Column("commande_id", Integer, ForeignKey("commandes.id"), primary_key=True),
    Column("plat_id", Integer, ForeignKey("plats.id"), primary_key=True),
)


class Commande(Base):
    __tablename__ = "commandes"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)

    statut = Column(String(50), default="en_attente", nullable=False)
    prix_total = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="commandes")
    restaurant = relationship("Restaurant", back_populates="commandes")
    plats = relationship("Plat", secondary=commande_plat, back_populates="commandes")