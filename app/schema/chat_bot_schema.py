from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
class AskQuestionRequest(BaseModel):
    session_id: str
    question: str
    category: str
    building_id: Optional[int] = None  
    
class ListFilesRequest(BaseModel):
    building_id: int
    category: Optional[str] = None

class FileItem(BaseModel):
    file_id: str
    original_file_name: str
    url: str
    user_id: int
    uploaded_at: datetime
    size: str
    category: Optional[str] = None
    gcs_path: str
    building_id: Optional[int] = None

class ListFilesResponse(BaseModel):
    files: List[FileItem]
    total_files: int
    total_size: str
    user_email: str
    building_id: Optional[int] = None
    category: Optional[str] = None
