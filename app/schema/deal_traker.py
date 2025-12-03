from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class DealStageBase(BaseModel):
    stage_name: str
    order_index: int
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None

class DealStageCreate(DealStageBase):
    pass

class DealStageOut(DealStageBase):
    id: int

    class Config:
        from_attributes = True

class DealCreate(BaseModel):
    tenant_name: str
    building_address_interest: str
    current_building_address: Optional[str] = None
    floor_suite_interest: Optional[str] = None
    floor_suite_current: Optional[str] = None
    broker_of_record: Optional[str] = None
    landlord_lead_of_record: Optional[str] = None
    current_lease_expiration: Optional[datetime] = None
    stages: List[DealStageCreate] = []



class DealOut(BaseModel):
    id: int
    tenant_name: str
    building_address_interest: str
    current_building_address: Optional[str] = None
    floor_suite_interest: Optional[str] = None
    floor_suite_current: Optional[str] = None
    broker_of_record: Optional[str] = None
    landlord_lead_of_record: Optional[str] = None
    current_lease_expiration: Optional[datetime] = None

    status: str = "Not Started"
    last_updated: datetime
    last_edited_by: str

    stages: List[DealStageOut] = []

    class Config:
        from_attributes = True   