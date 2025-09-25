from pydantic import BaseModel, EmailStr

class InviteUserCreate(BaseModel):
    email: EmailStr


from pydantic import BaseModel
from datetime import datetime
from typing import List

class UserListResponse(BaseModel):
    email: str
    status: str
    display: str
    name: str
    created: datetime
    actions: List[str]