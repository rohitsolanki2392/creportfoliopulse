from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database.db import get_db
from app.models.models import User
from app.schema.chat_bot_schema import AskQuestionRequest, ListFilesResponse
from app.utils.auth_utils import get_current_user

from app.services.user_chatbot_service import ask_simple_service, delete_simple_file_service, list_simple_files_service, update_standalone_file_service, upload_standalone_files_service

router = APIRouter()

@router.post("/upload_building_doc/", summary="Upload building documents")
async def upload_lease_doc(
    files: List[UploadFile] = File(...),
    building_id: int = Form(...),
    category: str = Form(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
        return await upload_standalone_files_service(
        files, category, current_user, db, building_id=building_id
    )

@router.get("/files/", response_model=ListFilesResponse)
async def list_files(
    building_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_simple_files_service(building_id, category, current_user, db)

@router.post("/ask_question/")
async def ask_question(
    req: AskQuestionRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):  
    return await ask_simple_service(req, current_user, db)


@router.patch("/update_files/")
async def update_file(
    file_id: str = Form(...),
    new_file: UploadFile = File(...),
    building_id: Optional[int] = Form(None),
    category: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await update_standalone_file_service(file_id, new_file, current_user, db, building_id, category)


@router.delete("/delete_files/", summary="Delete a specific file for a building")
async def delete_file(
    building_id: Optional[int] = Query(None),
    file_id: str = Query(...),
    category: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await delete_simple_file_service(building_id, file_id,category, current_user, db)