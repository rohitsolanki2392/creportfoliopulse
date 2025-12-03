from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NoteBase(BaseModel):
    title: Optional[str] = None
    content: str = ""

class NoteCreate(NoteBase):
    pass

class NoteUpdate(NoteBase):
    pass

class NoteInDB(NoteBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True