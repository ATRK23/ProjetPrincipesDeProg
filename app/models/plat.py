from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Plat(Base):
    __tablename__ = "plats"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prix = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    ingredients = Column(Text, nullable=True)
    allergenes = Column(Text, nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)

    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    restaurant = relationship("Restaurant", back_populates="plats")