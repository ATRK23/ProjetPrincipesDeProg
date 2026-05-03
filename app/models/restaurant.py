from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

class Restaurant(Base):
    __tablename__ = "restaurants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    description = Column(String(500), nullable=True)
    is_open = Column(Boolean, default=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="restaurants")
    
    plats = relationship(
        "Plat",
        back_populates="restaurant",
        cascade="all, delete-orphan"
    )
    
    commandes = relationship(
        "Commande",
        back_populates="restaurant",
        cascade="all, delete-orphan"
    )