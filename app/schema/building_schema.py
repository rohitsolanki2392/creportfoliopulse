from typing import Optional
from pydantic import BaseModel
class BuildingCreate(BaseModel):
    address: str
   
class BuildingUpdate(BaseModel):
    building_id: int
    address: Optional[str] = None

class BuildingPermissionCreate(BaseModel):
    building_id: int
    user_id: int