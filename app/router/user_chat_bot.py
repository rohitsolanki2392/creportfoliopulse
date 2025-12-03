from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.params import Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database.db import get_db
from app.models.models import User
from app.schema.chat_bot_schema import ListFilesResponse
from app.schema.user_chat import (
    AskSimpleQuestionRequest,
    AskSummaryChatRequest,
    StandaloneFileResponse,
)

from app.utils.auth_utils import get_current_user
from app.services.user_chatbot_service import (
    ask_summary_chat_service,
    upload_standalone_files_service,
    ask_simple_service,
    list_simple_files_service,
    delete_simple_file_service,
)

router = APIRouter()

@router.post("/standalone/upload", response_model=List[StandaloneFileResponse])
async def upload_standalone_files(
    files: List[UploadFile] = File(...),
    category: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await upload_standalone_files_service(files, category, current_user, db,building_id=None)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")




@router.post("/ask_summary_chat/", response_model=dict)
async def ask_summary_chat(
    req: AskSummaryChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ask_summary_chat_service(req, current_user, db)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")


@router.post("/ask_simple/", response_model=dict)
async def ask_simple(
    req: AskSimpleQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await ask_simple_service(req, current_user, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")



@router.get("/list_simple_files/", response_model=ListFilesResponse)
async def list_simple_files(
    building_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_simple_files_service(building_id, category, current_user, db)

@router.delete("/delete_simple_file/")
async def delete_simple_file(
    building_id: Optional[int] = Query(None),
    file_id: str = Query(...),
    category: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await delete_simple_file_service(building_id, file_id, category, current_user, db)

