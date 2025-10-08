
import logging
import os
import json
import re
from typing import Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.crud.user_chatbot_crud import get_standalone_file
from app.models.models import StandaloneFile, User
from datetime import datetime
from google.generativeai import GenerativeModel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

with open("app/services/templates/lease_template.txt", "r", encoding="utf-8") as f:
    LEASE_TEMPLATE = f.read()

def save_lease_file(content: str, company_id: str, category: str, file_id: str) -> str:
    try:
        file_path = f"uploads/{company_id}/{category}/{file_id}.txt"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path
    except Exception as e:
        logger.error(f"Error saving lease file {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save lease file: {str(e)}")

def format_lease_text(raw_text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', raw_text)
    text = re.sub(r'(\d+\.\s[A-Z][A-Z\s]+)', r'\n\1\n', text)
    text = text.replace('\t', '    ')
    return text.strip()


import json
from typing import Dict, Any
from google import genai

client = genai.Client()

def generate_lease_text(metadata: Dict[str, Any]) -> str:
    lease_text = LEASE_TEMPLATE
    try:
        prompt = f"""
        You are an expert in lease document automation.
        Analyze the following lease template and metadata, and determine which metadata keys should replace which placeholders.
        Use your best judgment based on context (e.g., names, dates, addresses, terms).

        Template:
        {LEASE_TEMPLATE}

        Metadata:
        {metadata}

        Return only a valid JSON mapping of placeholder to value. Example:
        {{
          "[TENANT_NAME]": "John Smith",
          "[LANDLORD_NAME]": "ABC Properties",
          "[PROPERTY_ADDRESS]": "123 Main St, New York"
        }}
        """

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        raw_text = response.text.strip()

        
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            raw_text = raw_text.replace("json", "", 1).strip()

        try:
            replacements = json.loads(raw_text)
        except Exception as json_error:
            print("Raw response from Gemini:", raw_text)
            raise ValueError(f"Gemini returned invalid JSON: {json_error}")

        for placeholder, value in replacements.items():
            lease_text = lease_text.replace(placeholder, str(value or "N/A"))

        return lease_text

    except Exception as e:
        return f"Error processing lease template with metadata: {e}"

def format_lease_text(lease_text: str) -> str:
    """Ensure consistent formatting of the lease text."""
    lines = [line.strip() for line in lease_text.split('\n') if line.strip()]
    return '\n'.join(lines)

def save_file_metadata(
    db: Session,
    file,
    gcs_path: str,
    category: str,
    current_user: User,
    structured_metadata: str
) -> StandaloneFile:
    from uuid import uuid4
    saved_file = StandaloneFile(
        file_id=str(uuid4()),
        original_file_name=file.filename,
        user_id=current_user.id,
        category=category,
        gcs_path=gcs_path,
        company_id=current_user.company_id,
       uploaded_at=datetime.utcnow(),
        structured_metadata=structured_metadata
    )
    db.add(saved_file)
    db.commit()
    db.refresh(saved_file)
    return saved_file

async def list_category_files_service(current_user: User, db: Session, category: str):
    files = db.query(StandaloneFile).filter(
        StandaloneFile.user_id == current_user.id,
        StandaloneFile.category == category,
    ).all()
    result = []
    for file in files:
        result.append({
            "file_id": file.file_id,
            "original_file_name": file.original_file_name,
            "user_id": file.user_id,
            "uploaded_at": file.uploaded_at.isoformat(),
            "category": file.category,
        })
    return {
        "category": category,
        "files": result,
        "total_files": len(result),
    }

def extract_structured_metadata_with_llm(extracted_text: str) -> dict:
    try:
        model = GenerativeModel("gemini-2.0-flash")
        prompt = f"""
                    You are an AI legal document assistant. A user has uploaded a lease-related document 
                    (e.g., Letter of Intent, lease agreement, or rental contract). 
                    Your task is to carefully read and analyze the document,
                    identify all important information, and extract it as key-value pairs in a JSON object.
                Important:
            - The document may vary in structure, wording, and content.
            - Extract all relevant information for the lease, including but not limited to:
                - Tenant and landlord information
                - Property address and details
                - Lease terms (duration, commencement and expiration dates)
                - Financial terms (rent amount, security deposit, payment schedule)
                - Property size, square footage
                - Permitted use, tenant improvements
                - Special clauses, rights, obligations, insurance, maintenance, renewal, penalties
                - Any other important terms or conditions that affect the lease

            Requirements:
            - Return a **valid JSON object** with key-value pairs for all extracted information.
            - Use `null` for any values not present.
            - If you find additional important fields not listed above, include them as new keys.
            - Ensure all extracted information is accurate and reflects the content of the document.

            Document Text: {extracted_text}
            """
          
        response = model.generate_content(prompt)
       
        text = response.text.strip()
        print(text)
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                metadata = json.loads(json_match.group())
                if isinstance(metadata, dict):
                    return metadata
            except json.JSONDecodeError:
                logger.error("LLM returned malformed JSON")
        logger.error(f"LLM did not return valid JSON, response: {text[:500]}")
        return {}
    except Exception as e:
        logger.error(f"LLM extraction failed: {str(e)}")
        return {}

def get_file_info_service(db: Session, file_id: str) -> dict:
    db_file = get_standalone_file(db, file_id)
    if not db_file:
        return {"success": False}
    return {
        "file_id": db_file.file_id,
        "original_file_name": db_file.original_file_name,
        "category": db_file.category,
        "uploaded_at": db_file.uploaded_at,
        "structured_metadata": json.loads(db_file.structured_metadata) if db_file.structured_metadata else {},
        "success": True
    }