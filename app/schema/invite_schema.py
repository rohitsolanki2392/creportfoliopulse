from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List

class InviteUserCreate(BaseModel):
    email: EmailStr


class UserListResponse(BaseModel):
    email: str
    status: str
    display: str
    name: str
    created: datetime
    actions: List[str]
    gemini_status: bool