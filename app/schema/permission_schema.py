from pydantic import BaseModel
from datetime import datetime

from app.models.models import Status


class BuildingAccessRequestCreate(BaseModel):
    building_id: int

class BuildingAccessRequestResponse(BaseModel):
    message: str
    request_id: int
    user_id: int
    user_email: str
    building_id: int
    status: Status
    created_at: datetime
    updated_at: datetime

class BuildingAccessRequestAction(BaseModel):
    request_id: int
    action: str  # "approve" or "deny"
