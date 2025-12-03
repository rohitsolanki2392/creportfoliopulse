from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FeedbackCreate(BaseModel):
    feedback: str
    category: Optional[str]=None


class FeedbackResponse(BaseModel):
    id: int
    feedback: str
    category: Optional[str]=None
    created_at: datetime
    user_email: str
    user_name:str

    class Config:
        from_attributes = True
