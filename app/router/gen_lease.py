import os

from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session
from app.models.models import User
from app.database.db import get_db
from app.utils.auth_utils import get_current_user
from app.services.gen_lease_services import  delete_file_service, list_category_files_service, process_lease_abstract

router = APIRouter()

@router.post("/upload/simple")
async def upload_lease_abstract(
    file: UploadFile = File(...),
    category: str = Form("lease"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    output_path = await process_lease_abstract(file, current_user, category, db)
    return {"file_path": output_path}


@router.get("/list_category_files/")
async def list_category_files(category: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await list_category_files_service(current_user.id, category, db)

@router.delete("/delete_file/")
async def delete_file(file_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await delete_file_service(file_id, current_user.id, db)