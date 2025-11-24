from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TourBase(BaseModel):
    date: datetime
    building: str
    floor_suite: Optional[str] = None
    tenant: Optional[str] = None
    broker: Optional[str] = None
    notes: Optional[str] = None

class TourCreate(TourBase):
    pass

class TourResponse(TourBase):
    id: int
    user_email: str  
    company_id: int
    created_at: datetime

    class Config:
        from_attributes = True
