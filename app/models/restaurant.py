from sqlalchemy import Column, Integer, String, Boolean

from app.database import Base

class Restaurant(Base):
    __tablename__ = "restaurants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    adress = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    description = Column(String(500), nullable=True)
    is_open = Column(Boolean, default=True, nullable=False)