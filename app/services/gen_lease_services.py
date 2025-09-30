
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
    """
    Preserves the structure of the lease template in plain text.
    - Keeps headings on new lines
    - Ensures index/table of contents spacing
    - Collapses extra blank lines to single blank lines
    """
    text = re.sub(r'\n{3,}', '\n\n', raw_text)
    text = re.sub(r'(\d+\.\s[A-Z][A-Z\s]+)', r'\n\1\n', text)
    text = text.replace('\t', '    ')
    return text.strip()

def generate_lease_text(metadata: Dict[str, Any]) -> str:
    lease_text = LEASE_TEMPLATE
    lease_text = lease_text.replace("_________________________________________________________________", metadata.get('tenant_name', '[TENANT NAME]'))
    lease_text = lease_text.replace("_____ Main Street, Suite ____", metadata.get('property_address', '[PROPERTY ADDRESS]'))
    lease_text = lease_text.replace("Dated:  ______________________", f"Dated: {datetime.now().strftime('%B %d, %Y')}")
    lease_text = lease_text.replace("containing approximately ______________ square feet", f"containing approximately {metadata.get('square_footage', '[SQUARE FOOTAGE]')} square feet")
    lease_text = lease_text.replace("as and for a ________________________________________________________________", f"as and for a {metadata.get('use_clause', '[USE]')}")
    lease_text = lease_text.replace("commence on __________________ (“Commencement Date”)", f"commence on {metadata.get('commencement_date', '[COMMENCEMENT DATE]')} (“Commencement Date”)")
    lease_text = lease_text.replace("end on _______________________________ (“Expiration Date”)", f"end on {metadata.get('expiration_date', '[EXPIRATION DATE]')} (“Expiration Date”)")
    lease_text = lease_text.replace("a base annual rent of __________________ (“Base Annual Rent”)", f"a base annual rent of {metadata.get('rent_amount', '[RENT AMOUNT]')} (“Base Annual Rent”)")
    lease_text = lease_text.replace("monthly installments of ______________________ per month (“Base Monthly Rent”)", f"monthly installments of {metadata.get('rent_amount', '[MONTHLY RENT]')} per month (“Base Monthly Rent”)")
    lease_text = lease_text.replace("$________________", metadata.get('security_deposit', '[SECURITY DEPOSIT]'))
    return format_lease_text(lease_text)

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
        Extract the following information from this Letter of Intent (LOI) text and return it as a JSON object:
        - tenant_name: Name of the tenant/lessee
        - landlord_name: Name of the landlord/lessor
        - property_address: Full address of the property
        - lease_term: Duration of the lease
        - rent_amount: Monthly rent amount
        - square_footage: Size of the space in square feet
        - commencement_date: Lease start date
        - expiration_date: Lease end date
        - security_deposit: Security deposit amount
        - use_clause: Permitted use of the property
        - tenant_improvements: Information about tenant improvements
        - additional_terms: Any other important terms or conditions
        Text: {extracted_text}
        Return only valid JSON. Use null if not found.
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
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