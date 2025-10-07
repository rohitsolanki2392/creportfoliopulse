from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FeedbackCreate(BaseModel):
    feedback: str
    rating: Optional[int] = None


class FeedbackResponse(BaseModel):
    id: int
    feedback: str
    rating: Optional[int]
    created_at: datetime
    user_email: str

    class Config:
        orm_mode = True
