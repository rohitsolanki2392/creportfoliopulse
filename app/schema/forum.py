from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class ForumThought(BaseModel):
    id: Optional[str] = None
    author_uid: str
    author_name: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    deleted: bool = False

class PortfolioThread(BaseModel):
    id: Optional[str] = None
    client_id: str
    title: str
    author_uid: str
    author_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_thought_at: Optional[datetime] = None
    thought_count: int = 0
    deleted: bool = False

class ThreadWithThoughts(PortfolioThread):
    thoughts: List[ForumThought] = []



class ThreadCreate(BaseModel):
    title: str

class ThoughtCreate(BaseModel):
    content: str

class ThoughtOut(BaseModel):
    id: str
    author_name: str
    author_uid: str
    content: str
    created_at: datetime
    deleted: bool = False

class ThreadOut(BaseModel):
    id: str
    title: str
    author_name: str
    created_at: datetime
    last_thought_at: Optional[datetime] = None
    thought_count: int = 0
    thoughts: List[ThoughtOut] = []