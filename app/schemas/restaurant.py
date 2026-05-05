from typing import Optional

from pydantic import BaseModel, ConfigDict



class RestaurantBase(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_open: bool = True
    

class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_open: Optional[bool] = None
    

class RestaurantResponse(RestaurantBase):
    id: int
    owner_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)