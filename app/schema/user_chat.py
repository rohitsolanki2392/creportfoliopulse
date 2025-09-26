from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

class AskSimpleQuestionRequest(BaseModel):
    session_id: str
    question: str
    category: str

class StandaloneFileResponse(BaseModel):
    file_id: str
    original_file_name: str
    url: str
    user_id: int
    uploaded_at: datetime
    size: str
    category: str
    gcs_path: str

    class Config:
        from_attributes = True

class ChatSessionResponse(BaseModel):
    title: Optional[str]
    session_id: str
    created_at: datetime
    category: str

    class Config:
        from_attributes = True

class ChatHistoryResponse(BaseModel):
    question: str
    answer: Optional[str]
    timestamp: datetime
    file_id: Optional[str]

    class Config:
        from_attributes = True

class FileResponse(BaseModel):
    file_id: str
    original_file_name: str
    url: str
    user_id: str
    uploaded_at: datetime
    size: str
    category: Optional[str]
    gcs_path: str
    building_id: Optional[int]


