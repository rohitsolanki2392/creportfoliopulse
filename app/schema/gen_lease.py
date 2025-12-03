from pydantic import BaseModel
from typing import Dict, Any, List

class UpdateMetadataRequest(BaseModel):
    file_id: str
    structured_metadata: Dict[str, Any]


class FindReplaceItem(BaseModel):
    find_text: str
    replace_text: str


class UpdateMultipleTextRequest(BaseModel):
    file_id: str
    updates: List[FindReplaceItem]


class UpdateTextRequest(BaseModel):
    file_id: str
    new_text: str

