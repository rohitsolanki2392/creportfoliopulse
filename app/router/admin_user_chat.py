from fastapi import APIRouter, Depends,UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.db import get_db
from app.models.models import  User
from app.schema.user_chat import StandaloneFileResponse
from app.services.session_service import get_session_history_service
from app.utils.auth_utils import get_current_user
from app.services.user_chatbot_service import delete_simple_file_service, list_simple_files_service, update_standalone_file_service, upload_standalone_files_service
router = APIRouter()

@router.post("/upload", response_model=List[StandaloneFileResponse])
async def upload_categorized_files(
    files: List[UploadFile] = File(...),
    category: str = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    return await upload_standalone_files_service(files, category, current_user, db)
   

@router.patch("/update", response_model=StandaloneFileResponse)
async def update_file(
    file_id: str = Query(...),                     
    category: Optional[str] = Query(None),         
    file: UploadFile = File(...),               
    building_id: Optional[int] = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    
    return await update_standalone_file_service(
        file_id=file_id,
        new_file=file,   
        current_user=current_user,
        db=db,
        building_id=building_id,
        category=category
    )


@router.get("/list", response_model=List[dict])
async def list_categorized_files(
    building_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
   
    response = await list_simple_files_service(building_id, category, current_user, db)
    
   
    files_list = []
    for file_item in response.files:
        files_list.append({
            "file_id": file_item.file_id,
            "original_file_name": file_item.original_file_name,
            "url": file_item.url,
            "user_id": file_item.user_id,
            "uploaded_at": file_item.uploaded_at,
            "category": file_item.category,
        })
    
    return files_list

@router.delete("/delete", response_model=StandaloneFileResponse)
async def delete_categorized_file(
    building_id: Optional[int] = Query(None),
    file_id: str = Query(...),
    category: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await delete_simple_file_service(building_id, file_id, category, current_user, db)




@router.get("/admin/chat/history/", response_model=List[dict])
async def get_chat_history(
    session_id: str = Query(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch chat history for admin using existing service function.
    """
    return await get_session_history_service(session_id, current_user, db)  
