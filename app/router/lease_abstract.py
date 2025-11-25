from datetime import datetime
import os
import uuid
import io
import google.generativeai as genai
from app.services.prompts import PROMPT
from app.config import MODEL,google_api_key
from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import StandaloneFile, User
from app.database.db import get_db
from app.utils.auth_utils import get_current_user
from app.services.lease_abs_services import  delete_file_service, list_category_files_service, process_lease_abstract
from app.utils.process_file import process_uploaded_file
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.params import Form
from app.models.models import User
import logging
logger = logging.getLogger(__name__)

router = APIRouter()


genai.configure(api_key=google_api_key)


@router.post("/upload/summarize")
async def summarize(
    file: UploadFile = File(...),
    category: str = Form("lease"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    content = await file.read()
    if len(content) > 32 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 32 MB")

    pdf_file = genai.upload_file(io.BytesIO(content), mime_type="application/pdf")
    model = genai.GenerativeModel(MODEL)

    try:
        response = model.generate_content([PROMPT, pdf_file], generation_config={"temperature": 0.1})
        output = response.text
        logger.info(f"Gemini response: {output}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {e}")
    finally:
        try:
            genai.delete_file(pdf_file.name)
        except:
            pass


    file_id = str(uuid.uuid4())


    new_file = StandaloneFile(
        file_id=file_id,
        original_file_name=file.filename,
        user_id=current_user.id,
        company_id=current_user.company_id,
        category=category,
        uploaded_at=datetime.utcnow(),
        gcs_path=None,      # No local file stored
        file_size=str(len(content)),
    )

    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)

    TEMP_SUMMARY_DIR = "temp_summary"
    os.makedirs(TEMP_SUMMARY_DIR, exist_ok=True)

    temp_summary_path = os.path.join(TEMP_SUMMARY_DIR, f"{file_id}.txt")

    with open(temp_summary_path, "w", encoding="utf-8") as f:
        f.write(output)

    try:
        await process_uploaded_file(
            file_path=temp_summary_path,
            filename=file.filename,
            file_id=file_id,
            category=category,
            company_id=current_user.company_id,
            building_id=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing error: {e}")
    finally:
        if os.path.exists(temp_summary_path):
            os.remove(temp_summary_path)

    return {
        "message": "Summary generated, saved, and indexed successfully.",
        "file_id": new_file.file_id,
         "file_name": file.filename,    
    }


@router.post("/upload/simple")
async def upload_lease_abstract(
    file: UploadFile = File(...),
    category: str = Form("lease"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    output_path = await process_lease_abstract(file, current_user, category, db)
    return {"file_path": output_path}




@router.get("/list_category_files/")
async def list_category_files(category: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await list_category_files_service(current_user.id, category, db)

@router.delete("/delete_file/")
async def delete_file(file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await delete_file_service(file_id, current_user.id, db)