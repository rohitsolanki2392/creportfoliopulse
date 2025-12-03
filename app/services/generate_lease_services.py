import asyncio
import os
import json
import re
import logging
from typing import Dict, Any
from datetime import datetime
import aiofiles
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.user_chatbot_crud import get_standalone_file
from app.models.models import StandaloneFile, User
from app.config import client

from sqlalchemy.future import select
logger = logging.getLogger(__name__)


with open("app/services/templates/lease_template.txt", "r", encoding="utf-8") as f:
    LEASE_TEMPLATE = f.read()


async def save_lease_file(content: str, company_id: str, category: str, file_id: str) -> str:
    file_path = f"uploads/{company_id}/{category}/{file_id}.txt"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
        await f.write(content)

    return file_path

async def generate_lease_text(metadata: Dict[str, Any]) -> str:
    try:
        prompt = f"""
        You are an expert in lease-document automation.
        Using the provided metadata, fill all placeholders in the lease template exactly as instructed.

        Template:
        {LEASE_TEMPLATE}

        Metadata:
        {metadata}

        Instructions:
        - Output only the completed template with all placeholders filled using the metadata.
        - Do not add explanations, comments, or extra text.
        - Preserve all formatting from the template.

        Response:
        Only the fully populated template.
        """

        response = await asyncio.to_thread(
            lambda: client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )
        )

        lease_text = response.text.strip()

        return lease_text

    except Exception as e:
        logger.error(f"Error in generate_lease_text: {e}")
        return f"Error processing lease template: {e}"
    
async def save_file_metadata(
    db: AsyncSession,
    file,
    file_path: str,
    category: str,
    current_user: User,
    structured_metadata: str
) -> StandaloneFile:
    from uuid import uuid4
    new_file = StandaloneFile(
        file_id=str(uuid4()),
        original_file_name=file.filename,
        user_id=current_user.id,
        category=category,
        file_path=file_path,
        company_id=current_user.company_id,
        uploaded_at=datetime.utcnow(),
        structured_metadata=structured_metadata
    )
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)
    return new_file


async def list_category_files_service(current_user: User, db: AsyncSession, category: str):
    result = await db.execute(
        select(StandaloneFile).filter(
            StandaloneFile.user_id == current_user.id,
            StandaloneFile.category == category
        )
    )

    files = result.scalars().all()
    return {
        "category": category,
        "files": [
            {
                "file_id": f.file_id,
                "original_file_name": f.original_file_name,
                "uploaded_at": f.uploaded_at.isoformat(),
                "category": f.category,
            }
            for f in files
        ],
        "total_files": len(files),
    }


async def extract_structured_metadata_with_llm(extracted_text: str) -> dict:
    try:
        from google.generativeai import GenerativeModel
        model = GenerativeModel("gemini-2.0-flash")

        prompt = f"""
        Extract key lease metadata as JSON from the following document text:
        {extracted_text}
        """

        response = await model.generate_content_async(prompt)
        text = response.text.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}
    except Exception as e:
        logger.error(f"Metadata extraction failed: {e}")
        return {}


async def get_file_info_service(db: AsyncSession, file_id: str) -> dict:
    db_file = await get_standalone_file(db, file_id)
    if not db_file:
        return {"success": False}
    return {
        "file_id": db_file.file_id,
        "original_file_name": db_file.original_file_name,
        "category": db_file.category,
        "uploaded_at": db_file.uploaded_at,
        "structured_metadata": json.loads(db_file.structured_metadata or "{}"),
        "success": True
    }