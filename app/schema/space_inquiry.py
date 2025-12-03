from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class SpaceInquiryOut(BaseModel):
    id: int
    company_id: int
    sender_name: Optional[str]
    sender_email: Optional[str]
    sender_phone: Optional[str]
    broker_company: Optional[str]
    building_address: Optional[str]
    inquiry_text: Optional[str]
    email_subject: Optional[str]
    email_date: Optional[datetime]
    matched_rule: str
    ingestion_status: str
    created_at: datetime

    class Config:
        from_attributes = True
