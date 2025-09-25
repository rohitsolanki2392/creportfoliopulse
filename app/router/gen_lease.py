# # gen_lease.py (unchanged, as generation is handled in services)

# import logging
# import os
# from typing import Dict, Any
# from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query, Body
# from fastapi.responses import PlainTextResponse, StreamingResponse
# from sqlalchemy.orm import Session
# from app.database.db import get_db
# from app.models.models import User
# from app.services.gen_lease_services import ( list_category_files_service, save_file_metadata, upload_to_gcs, PDFTextExtractor,
#     extract_structured_metadata_with_llm, get_file_info_service, create_lease_document_service,generate_lease_text
# )
# from app.utils.auth_utils import get_current_user
# from app.crud.user_chatbot_crud import get_standalone_file, delete_standalone_file
# from google.cloud import storage
# from google.oauth2 import service_account
# from app.utils.gcp_utils import get_secret
# import json
# from datetime import datetime
# from pydantic import BaseModel

# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# router = APIRouter()

# class UpdateTextRequest(BaseModel):
#     file_id: str
#     structured_metadata: str

# class UpdateMetadataRequest(BaseModel):
#     file_id: str
#     structured_metadata: Dict[str, Any]

# @router.post("/upload/simple")
# async def upload_file_to_gcs_and_db(
#     file: UploadFile = File(...),
#     category: str = Form(...),
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     try:
#         logger.info(f"Uploading file {file.filename} for user {current_user.id}")
#         gcs_result = await upload_to_gcs(file)
#         saved_file = save_file_metadata(db, file, gcs_result["unique_filename"], category, current_user)
#         return {
#             "file_id": saved_file.file_id,
#             "original_file_name": saved_file.original_file_name,
#             "category": saved_file.category,
#             "user_id": saved_file.user_id,
#             "uploaded_at": saved_file.uploaded_at.isoformat(),
#             "gcs_path": saved_file.gcs_path,
#             "url": gcs_result["signed_url"],
#         }
#     except Exception as e:
#         logger.error(f"Failed to upload file {file.filename}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

# @router.delete("/delete_file/")
# async def delete_file(
#     file_id: str,
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     try:
#         logger.info(f"Deleting file {file_id} for user {current_user.id}")
#         db_file = get_standalone_file(db, file_id)
#         if not db_file:
#             raise HTTPException(status_code=404, detail="File not found")
#         if db_file.user_id != current_user.id:
#             raise HTTPException(status_code=403, detail="Not authorized to delete this file")
#         bucket_name = os.getenv("GCS_BUCKET_NAME")
#         if not bucket_name:
#             raise HTTPException(status_code=500, detail="Missing GCS bucket configuration")
#         credentials_path = os.getenv("GOOGLE_CLOUD_CREDENTIALS_PATH")
#         if credentials_path:
#             credentials = service_account.Credentials.from_service_account_file(credentials_path)
#         else:
#             credentials_json = get_secret("gcp-credentials")
#             if not credentials_json:
#                 raise HTTPException(status_code=500, detail="Missing GCP credentials")
#             credentials = service_account.Credentials.from_service_account_info(json.loads(credentials_json))
#         storage_client = storage.Client(credentials=credentials)
#         bucket = storage_client.bucket(bucket_name)
#         blob = bucket.blob(db_file.gcs_path)
#         if blob.exists():
#             blob.delete()
#             logger.info(f"Deleted file from GCS: {db_file.gcs_path}")
#         delete_standalone_file(db, file_id)
#         return {"message": f"File with id {file_id} deleted successfully from database and GCS"}
#     except Exception as e:
#         logger.error(f"Error deleting file {file_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



# @router.get("/files/extract-metadata")
# async def extract_metadata(
#     file_id: str = Query(...),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         db_file = get_standalone_file(db, file_id)
#         if not db_file:
#             raise HTTPException(status_code=404, detail="File not found")
#         if db_file.user_id != current_user.id:
#             raise HTTPException(status_code=403, detail="Not authorized")
#         bucket_name = os.getenv("GCS_BUCKET_NAME")
#         if not bucket_name:
#             raise HTTPException(status_code=500, detail="Missing GCS bucket configuration")
#         credentials_path = os.getenv("GOOGLE_CLOUD_CREDENTIALS_PATH")
#         if credentials_path:
#             credentials = service_account.Credentials.from_service_account_file(credentials_path)
#         else:
#             credentials_json = get_secret("gcp-credentials")
#             if not credentials_json:
#                 raise HTTPException(status_code=500, detail="Missing GCP credentials")
#             credentials = service_account.Credentials.from_service_account_info(json.loads(credentials_json))
#         client = storage.Client(credentials=credentials)
#         bucket = client.bucket(bucket_name)
#         blob = bucket.blob(db_file.gcs_path)
#         if not blob.exists():
#             raise HTTPException(status_code=404, detail="File not found in GCS")
#         content = blob.download_as_bytes()
#         extractor = PDFTextExtractor()
#         structured_metadata, extraction_method = extractor.extract_text_with_fallback(content)
#         if not structured_metadata:
#             raise HTTPException(status_code=422, detail="Could not extract text from file")
#         structured_metadata = extract_structured_metadata_with_llm(structured_metadata)
#         db_file.structured_metadata = structured_metadata
#         db_file.structured_metadata = json.dumps(structured_metadata)
#         db.commit()
#         db.refresh(db_file)
#         return {
#             "file_id": db_file.file_id,
#             "original_file_name": db_file.original_file_name,
#             "category": db_file.category,
#             "uploaded_at": db_file.uploaded_at.isoformat(),
#             "extraction_method": extraction_method,
#             "structured_metadata": structured_metadata,
#             "structured_metadata_preview": structured_metadata[:500] + "..." if len(structured_metadata) > 500 else structured_metadata
#         }
#     except Exception as e:
#         logger.error(f"Error extracting metadata for file_id {file_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error while extracting metadata")

# @router.get("/files/lease-agreement-text", response_class=PlainTextResponse)
# async def generate_lease_agreement_text(
#     file_id: str = Query(...),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         file_info = get_file_info_service(db, file_id)
#         if not file_info or not file_info.get("success"):
#             raise HTTPException(status_code=404, detail="File not found or extraction failed")
        
#         lease_text = generate_lease_text(file_info["structured_metadata"])
#         return PlainTextResponse(content=lease_text)

#     except Exception as e:
#         logger.error(f"Error generating lease agreement text for file {file_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error while generating lease agreement")

# @router.get("/files/lease-agreement-docx")
# async def generate_lease_agreement_docx(
#     file_id: str = Query(...),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         doc_stream = create_lease_document_service(db, file_id)
#         file_info = get_file_info_service(db, file_id)
#         original_name = file_info.get("original_file_name", "lease_agreement.docx")
#         base_name = original_name.rsplit('.', 1)[0] if '.' in original_name else original_name
#         return StreamingResponse(
#             doc_stream,
#             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#             headers={"Content-Disposition": f"attachment; filename={base_name}_lease_agreement.docx"}
#         )
#     except Exception as e:
#         logger.error(f"Error generating lease agreement DOCX for file {file_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error while generating lease agreement DOCX")

# @router.patch("/files/update-extracted-text")
# async def update_extracted_text(
#     request: UpdateTextRequest = Body(...),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         file_id = request.file_id
#         db_file = get_standalone_file(db, file_id)
#         if not db_file:
#             raise HTTPException(status_code=404, detail="File not found")
#         if db_file.user_id != current_user.id:
#             raise HTTPException(status_code=403, detail="Not authorized to update this file")
#         new_structured_metadata = request.structured_metadata.strip()
#         if not new_structured_metadata:
#             raise HTTPException(status_code=400, detail="Provided text cannot be empty")
#         structured_metadata = extract_structured_metadata_with_llm(new_structured_metadata)
#         db_file.structured_metadata = new_structured_metadata
#         db_file.structured_metadata = json.dumps(structured_metadata)
#         db.commit()
#         db.refresh(db_file)
#         return {
#             "file_id": db_file.file_id,
#             "original_file_name": db_file.original_file_name,
#             "category": db_file.category,
#             "extraction_method": "manual_update",
#             "structured_metadata": structured_metadata,
#             "structured_metadata_preview": new_structured_metadata[:500] + "..." if len(new_structured_metadata) > 500 else new_structured_metadata
#         }
#     except Exception as e:
#         logger.error(f"Error updating extracted text for file_id {file_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error while updating extracted text")

# @router.get("/list_category_files/")
# async def list_category_files(
#     category: str = Query(...),
#     current_user: User = Depends(get_current_user),
#     db: Session = Depends(get_db),
# ):
#     try:
#         return await list_category_files_service(current_user, db, category)
#     except Exception as e:
#         logger.error(f"Error listing files in category {category}: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# @router.patch("/files/update-metadata")
# async def update_metadata(
#     request: UpdateMetadataRequest = Body(...),
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     try:
#         file_id = request.file_id
#         db_file = get_standalone_file(db, file_id)
#         if not db_file:
#             raise HTTPException(status_code=404, detail="File not found")
#         if db_file.user_id != current_user.id:
#             raise HTTPException(status_code=403, detail="Not authorized to update this file")
#         structured_metadata = request.structured_metadata
#         db_file.structured_metadata = json.dumps(structured_metadata)
#         db.commit()
#         db.refresh(db_file)
#         return {
#             "file_id": db_file.file_id,
#             "structured_metadata": structured_metadata
#         }
#     except Exception as e:
#         logger.error(f"Error updating metadata for file_id {file_id}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error while updating metadata")

