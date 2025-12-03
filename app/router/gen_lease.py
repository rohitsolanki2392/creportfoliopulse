import logging
import os
import json
import asyncio
import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    File,
    UploadFile,
    Form,
    Body,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.db import get_db
from app.models.models import StandaloneFile, User
from app.schema.gen_lease import UpdateMetadataRequest
from app.services.generate_lease_services import (
    save_file_metadata,
    extract_structured_metadata_with_llm,
    get_file_info_service,
    generate_lease_text,
    list_category_files_service,
    save_lease_file,
)
from app.utils.auth_utils import get_current_user
from app.crud.user_chatbot_crud import (
    get_standalone_file,
    delete_standalone_file,
)
from app.utils.process_file import (
    save_to_temp,
    extract_text_from_file_using_llm,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

router = APIRouter()



@router.post("/upload/simple")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a lease file, extract text, metadata and store it.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Only PDF files are allowed."
        )

    temp_path = None
    try:
        logger.info(f"Uploading file {file.filename} for user {current_user.id}")

        temp_path = await save_to_temp(file, current_user.id, current_user, category)

        extracted_text = extract_text_from_file_using_llm(temp_path)
        if not extracted_text:
            raise ValueError("No text extracted from file")

        structured_metadata = await extract_structured_metadata_with_llm(extracted_text) or {}


        saved_file = await save_file_metadata(
            db,
            file,
            file_path="",
            category=category,
            current_user=current_user,
            structured_metadata=json.dumps(structured_metadata),
        )

        os.remove(temp_path)

        return {
            "file_id": saved_file.file_id,
            "original_file_name": saved_file.original_file_name,
            "category": saved_file.category,
            "user_id": saved_file.user_id,
            "uploaded_at": saved_file.uploaded_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to upload file {file.filename}: {str(e)}")
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")




@router.get("/files/structured_metadata")
async def get_structured_metadata(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get structured metadata from uploaded file
    """
    try:
        result = await db.execute(
            select(StandaloneFile).filter(
                StandaloneFile.file_id == file_id,
                StandaloneFile.user_id == current_user.id,
            )
        )
        file_record = result.scalars().first()

        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "file_id": file_record.file_id,
            "structured_metadata": json.loads(file_record.structured_metadata or "{}"),
        }
    except Exception as e:
        logger.error(f"Failed to fetch structured metadata for file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metadata: {str(e)}")




@router.get("/files/lease-agreement-text", response_class=PlainTextResponse)
async def generate_lease_agreement_text(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate lease text from structured metadata
    """
    try:
        file_info = await get_file_info_service(db, file_id)
        if not file_info or not file_info.get("success"):
            raise HTTPException(status_code=404, detail="File not found or extraction failed")

        lease_text = await generate_lease_text(file_info["structured_metadata"])

        await save_lease_file(
            content=lease_text,
            company_id=current_user.company_id,
            category="lease_gen",
            file_id=file_id,
        )

        db_file = await get_standalone_file(db, file_id)
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")

        return PlainTextResponse(content=lease_text)

    except Exception as e:
        logger.error(f"Error generating lease text for file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate lease text: {str(e)}")



@router.get("/files/view_generated_lease/text", response_class=PlainTextResponse)
async def view_file_text(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    View generated lease text file
    """
    result = await db.execute(
        select(StandaloneFile).filter(
            StandaloneFile.file_id == file_id,
            StandaloneFile.user_id == current_user.id,
        )
    )
    db_file = result.scalars().first()

    if not db_file:
        raise HTTPException(status_code=404, detail="File not found or not authorized")

    file_path = os.path.join(
        "uploads", str(current_user.company_id), "lease_gen", f"{file_id}.txt"
    )

    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="No lease text file found")


    async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
        content = await f.read()


    return PlainTextResponse(content=content)



@router.patch("/files/text")
async def update_file_text(
    file_id: str,
    new_text: str = Body(..., media_type="text/plain"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(StandaloneFile).filter(
            StandaloneFile.file_id == file_id,
            StandaloneFile.user_id == current_user.id,
        )
    )
         
    db_file =  result.scalars().first()

    if not db_file:
        raise HTTPException(status_code=404, detail="File not found or not authorized")

    file_path = os.path.join(
        "uploads", str(current_user.company_id), "lease_gen", f"{file_id}.txt"
    )

    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="No lease text file found to update")

    await save_lease_file(
        content=new_text,
        company_id=current_user.company_id,
        category="lease_gen",
        file_id=file_id,
    )

    return {"message": "Text updated successfully."}



@router.patch("/files/update-metadata")
async def update_metadata(
    request: UpdateMetadataRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        file_id = request.file_id
        db_file = await get_standalone_file(db, file_id)
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        if db_file.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this file")

        structured_metadata = request.structured_metadata
        db_file.structured_metadata = json.dumps(structured_metadata)
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)

        lease_text =await generate_lease_text(structured_metadata)

        file_path = await save_lease_file(
            content=lease_text,
            company_id=current_user.company_id,
            category="lease_gen",
            file_id=file_id,
        )
        logger.info(
            f"Lease text saved to {file_path} with updated metadata for file_id {file_id}"
        )

        return {
            "file_id": db_file.file_id,
            "structured_metadata": structured_metadata,
            "file_path": file_path,
        }
    except Exception as e:
        logger.error(f"Error updating metadata for file_id {file_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while updating metadata: {str(e)}",
        )



@router.get("/list_category_files/")
async def list_category_files(
    category: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await list_category_files_service(current_user, db, category)
    except Exception as e:
        logger.error(f"Error listing files in category {category}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")




@router.delete("/delete_file/")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        logger.info(f"Deleting file {file_id} for user {current_user.id}")
        db_file = await get_standalone_file(db, file_id)
        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        if db_file.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this file")

        file_path = f"uploads/{current_user.company_id}/lease_gen/{file_id}.txt"
        if os.path.exists(file_path):
            await asyncio.to_thread(os.remove, file_path)
            logger.info(f"Deleted lease text file {file_path}")

        await delete_standalone_file(db, file_id)
        return {"message": f"File with id {file_id} deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
