import os
import uuid
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.database.db import get_db
from app.models.models import StandaloneFile, User
from app.services.gen_lease_services import extract_structured_metadata_with_llm, generate_lease_text, save_lease_file
from app.utils.auth_utils import get_current_user


logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "uploads"


# ========== 1️⃣ Upload File (Template or LOI) ==========
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form(...),  # e.g. "template" or "loi"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if category not in {"template", "loi"}:
        raise HTTPException(status_code=400, detail="Invalid category. Use 'template' or 'loi'.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx"]:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed.")

    user_folder = os.path.join(UPLOAD_DIR, f"user_{current_user.id}", category)
    os.makedirs(user_folder, exist_ok=True)

    file_id = str(uuid.uuid4())
    save_path = os.path.join(user_folder, f"{file_id}{ext}")

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    db_file = StandaloneFile(
        file_id=file_id,
        original_file_name=file.filename,
        user_id=current_user.id,
        category=category,
        gcs_path=save_path,  # local path stored here
        uploaded_at=datetime.utcnow(),
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return {"file_id": file_id, "file_name": file.filename, "category": category}


# ========== 2️⃣ List Files ==========
@router.get("/list")
def list_files(
    category: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(StandaloneFile).filter(StandaloneFile.user_id == current_user.id)
    if category:
        query = query.filter(StandaloneFile.category == category)
    files = query.all()
    return [
        {
            "file_id": f.file_id,
            "file_name": f.original_file_name,
            "category": f.category,
            "uploaded_at": f.uploaded_at.isoformat(),
        }
        for f in files
    ]


# ========== 3️⃣ Delete File ==========
@router.delete("/{file_id}")
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_file = db.query(StandaloneFile).filter(
        StandaloneFile.file_id == file_id,
        StandaloneFile.user_id == current_user.id
    ).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="File not found.")

    if os.path.exists(db_file.gcs_path):
        os.remove(db_file.gcs_path)

    db.delete(db_file)
    db.commit()
    return {"message": f"File {file_id} deleted successfully."}


# ========== 4️⃣ Process LOI + Template → Generate Lease ==========
@router.post("/generate-lease")
async def generate_lease_from_template(
    template_file_id: str = Form(...),
    loi_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User selects a template file_id and uploads LOI to auto-generate lease."""
    # Fetch selected template
    template_file = db.query(StandaloneFile).filter(
        StandaloneFile.file_id == template_file_id,
        StandaloneFile.user_id == current_user.id,
        StandaloneFile.category == "template"
    ).first()

    if not template_file:
        raise HTTPException(status_code=404, detail="Template file not found.")

    # Save uploaded LOI locally
    loi_folder = os.path.join(UPLOAD_DIR, f"user_{current_user.id}", "loi")
    os.makedirs(loi_folder, exist_ok=True)
    loi_file_id = str(uuid.uuid4())
    loi_ext = os.path.splitext(loi_file.filename)[1]
    loi_path = os.path.join(loi_folder, f"{loi_file_id}{loi_ext}")

    with open(loi_path, "wb") as buffer:
        shutil.copyfileobj(loi_file.file, buffer)

    # ====== Extract metadata from LOI =====
    extracted_text = "..."  # ← extract text from LOI using pymupdf or docx
    metadata = extract_structured_metadata_with_llm(extracted_text)

    # ====== Generate final lease ======
    lease_text = generate_lease_text(metadata)
    lease_path = save_lease_file(lease_text, f"user_{current_user.id}", "leases", loi_file_id)

    return {
        "message": "Lease generated successfully.",
        "lease_path": lease_path,
        "metadata": metadata
    }
