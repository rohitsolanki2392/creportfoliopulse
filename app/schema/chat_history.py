from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatHistorySchema(BaseModel):
    id: int
    user_id: int
    question: str
    answer: str
    response_json: Optional[dict]
    timestamp: datetime

    class Config:
        from_attributes = True