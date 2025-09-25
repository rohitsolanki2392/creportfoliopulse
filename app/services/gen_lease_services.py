# # gen_lease_services.py (updated with lease generation, removed duplicates, used Gemini, template import)

# import logging
# import os
# import re
# import json
# from io import BytesIO
# from typing import Dict, Any
# from fastapi import HTTPException, UploadFile
# import fitz  # Should print a version like '1.24.0'
# import pytesseract
# from pdf2image import convert_from_bytes
# from PIL import Image
# from sqlalchemy.orm import Session
# from app.crud.user_chatbot_crud import get_standalone_file
# from app.models.models import StandaloneFile, User
# from google.cloud import storage
# from google.oauth2 import service_account
# from datetime import datetime, timedelta
# from uuid import uuid4
# from docx import Document
# from docx.enum.text import WD_PARAGRAPH_ALIGNMENT

# from app.utils.gcp_utils import get_secret

# from vertexai.generative_models import GenerativeModel
# import logging
# import os
# import re
# import json
# from io import BytesIO
# from typing import Dict, Any
# from fastapi import HTTPException, UploadFile
# import pytesseract
# from pdf2image import convert_from_bytes
# from PIL import Image
# from sqlalchemy.orm import Session
# from app.crud.user_chatbot_crud import get_standalone_file
# from app.models.models import StandaloneFile, User
# from google.cloud import storage
# from google.oauth2 import service_account
# from datetime import datetime, timedelta
# from uuid import uuid4
# from docx import Document
# from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
# from app.utils.gcp_utils import get_secret
# import os
# from docx import Document
# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# # TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'app/utils/lease_template.docx')  # Assume .doc converted to .docx
# TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'lease_template.docx')




# def replace_placeholders(doc: Document, metadata: Dict[str, Any]):
#     placeholders = {
#         '_________________________________________________________________': metadata.get('tenant_name', '[TENANT NAME TO BE FILLED]'),
#         '_____ Main Street, Suite ____': metadata.get('property_address', '[PROPERTY ADDRESS TO BE FILLED]'),
#         'Dated:  ______________________': f"Dated: {datetime.now().strftime('%B %d, %Y')}",
#         'containing approximately ______________ square feet': f"containing approximately {metadata.get('square_footage', '[SQUARE FOOTAGE TO BE FILLED]')} square feet",
#         'as and for a ________________________________________________________________': f"as and for a {metadata.get('use_clause', '[PERMITTED USE TO BE FILLED]')}",
#         'commence on __________________ (“Commencement Date”)': f"commence on {metadata.get('commencement_date', '[COMMENCEMENT DATE TO BE FILLED]')} (“Commencement Date”)",
#         'end on _______________________________ (“Expiration Date”)': f"end on {metadata.get('expiration_date', '[EXPIRATION DATE TO BE FILLED]')} (“Expiration Date”)",
#         'a base annual rent of __________________ (“Base Annual Rent”)': f"a base annual rent of {metadata.get('rent_amount', '[MONTHLY RENT TO BE FILLED]')} (“Base Annual Rent”)",
#         'monthly installments of ______________________ per month (“Base Monthly Rent”)': f"monthly installments of {metadata.get('rent_amount', '[MONTHLY RENT TO BE FILLED]')} per month (“Base Monthly Rent”)",
#         '$________________': metadata.get('security_deposit', '[SECURITY DEPOSIT TO BE FILLED]'),
#         # Add more for other placeholders in the .doc template, e.g., for addenda
#     }
#     for paragraph in doc.paragraphs:
#         for placeholder, value in placeholders.items():
#             if placeholder in paragraph.text:
#                 paragraph.text = paragraph.text.replace(placeholder, str(value))
#     # Handle tables for rent escalations
#     if 'rent_amount' in metadata:
#         base_monthly = float(metadata['rent_amount'].replace('$', '').replace(',', ''))
#         base_annual = base_monthly * 12
#         base_psf = base_annual / int(metadata['square_footage']) if 'square_footage' in metadata else 0
#         for table in doc.tables:
#             if 'Year 2' in table.rows[1].cells[0].text:  # Assume the escalation table structure
#                 for year in range(2, 11):  # For 10-year term
#                     escalated_monthly = base_monthly * (1.02 ** (year - 1))
#                     escalated_annual = escalated_monthly * 12
#                     row = table.rows[year - 1]
#                     row.cells[0].text = f'Year {year}'
#                     row.cells[1].text = f'${escalated_monthly:.2f}'
#                     row.cells[2].text = f'${escalated_annual:.2f}'
#     # Additional replacements for TI, use, etc.
#     # For example, for use clause
#     for paragraph in doc.paragraphs:
#         if 'as and for a ________________________________________________________________' in paragraph.text:
#             paragraph.text = paragraph.text.replace('as and for a ________________________________________________________________', f"as and for a {metadata.get('use_clause', '[USE]')}")

# def create_lease_document_service(db: Session, file_id: str) -> BytesIO:
#     file_info = get_file_info_service(db, file_id)
#     if not file_info or not file_info.get('success'):
#         raise HTTPException(status_code=404, detail="File not found or extraction failed")
#     metadata = file_info.get('structured_metadata', {})
#     doc = Document(TEMPLATE_PATH)  # Load the sample .docx template
#     replace_placeholders(doc, metadata)
#     doc_stream = BytesIO()
#     doc.save(doc_stream)
#     doc_stream.seek(0)
#     return doc_stream

# # Optional: generate_lease_text if needed for plain text version
# def generate_lease_text(metadata: Dict[str, Any]) -> str:
#     # If needed, extract text from docx template and replace, but since focus is docx, optional
#     doc = Document(TEMPLATE_PATH)
#     text = '\n'.join(p.text for p in doc.paragraphs)
#     for placeholder, value in placeholders.items():  # Use same placeholders dict
#         text = text.replace(placeholder, str(value))
#     return text

# async def upload_to_gcs(file: UploadFile) -> dict:
#     bucket_name = os.getenv("GCS_BUCKET_NAME")
#     if not bucket_name:
#         raise HTTPException(status_code=500, detail="Missing GCS bucket configuration")
#     credentials_path = os.getenv("GOOGLE_CLOUD_CREDENTIALS_PATH")
#     if credentials_path:
#         credentials = service_account.Credentials.from_service_account_file(credentials_path)
#     else:
#         credentials_json = get_secret("gcp-credentials")
#         if not credentials_json:
#             raise HTTPException(status_code=500, detail="Missing GCP credentials")
#         credentials = service_account.Credentials.from_service_account_info(json.loads(credentials_json))
#     storage_client = storage.Client(credentials=credentials)
#     bucket = storage_client.bucket(bucket_name)
#     content = await file.read()
#     if not content:
#         raise HTTPException(status_code=400, detail="Uploaded file is empty")
#     file_ext = os.path.splitext(file.filename)[1].lower()
#     unique_filename = f"standalone_files/{uuid4()}{file_ext}"
#     blob = bucket.blob(unique_filename)
#     blob.upload_from_string(content)
#     signed_url = blob.generate_signed_url(expiration=timedelta(days=365*10))
#     return {
#         "unique_filename": unique_filename,
#         "signed_url": signed_url,
#         "file_size": len(content),
#     }

# def save_file_metadata(db: Session, file: UploadFile, gcs_path: str, category: str, current_user: User) -> StandaloneFile:
#     saved_file = StandaloneFile(
#         file_id=str(uuid4()),
#         original_file_name=file.filename,
#         user_id=current_user.id,
#         category=category,
#         gcs_path=gcs_path,
#         company_id=current_user.company_id,
#         uploaded_at=datetime.utcnow()
#     )
#     db.add(saved_file)
#     db.commit()
#     db.refresh(saved_file)
#     return saved_file

# async def list_category_files_service(current_user: User, db: Session, category: str):
#     bucket_name = os.getenv("GCS_BUCKET_NAME")
#     if not bucket_name:
#         raise HTTPException(status_code=500, detail="Configuration missing")
#     files = db.query(StandaloneFile).filter(
#         StandaloneFile.user_id == current_user.id,
#         StandaloneFile.category == category,
#     ).all()
#     credentials_path = os.getenv("GOOGLE_CLOUD_CREDENTIALS_PATH")
#     if credentials_path:
#         credentials = service_account.Credentials.from_service_account_file(credentials_path)
#     else:
#         credentials_json = get_secret("gcp-credentials")
#         if not credentials_json:
#             raise HTTPException(status_code=500, detail="Missing GCP credentials")
#         credentials = service_account.Credentials.from_service_account_info(json.loads(credentials_json))
#     storage_client = storage.Client(credentials=credentials)
#     bucket = storage_client.bucket(bucket_name)
#     result = []
#     for file in files:
#         blob = bucket.get_blob(file.gcs_path)
#         if not blob:
#             continue
#         signed_url = blob.generate_signed_url(expiration=timedelta(days=365*10))
#         result.append({
#             "file_id": file.file_id,
#             "original_file_name": file.original_file_name,
#             "url": signed_url,
#             "user_id": file.user_id,
#             "uploaded_at": file.uploaded_at.isoformat(),
#             "category": file.category,
#             "gcs_path": file.gcs_path,
#         })
#     return {
#         "category": category,
#         "files": result,
#         "total_files": len(result),
#     }

# class PDFTextExtractor:
#     def extract_text_pymupdf(self, pdf_bytes: bytes) -> str:
#         try:
#             doc = fitz.open(stream=pdf_bytes, filetype="pdf")
#             text = "".join(page.get_text() + "\n" for page in doc)
#             doc.close()
#             return text.strip()
#         except Exception as e:
#             logger.error(f"PyMuPDF extraction failed: {str(e)}")
#             return ""

#     def extract_text_ocr(self, pdf_bytes: bytes) -> str:
#         try:
#             images = convert_from_bytes(pdf_bytes, dpi=300)
#             text = "".join(f"--- Page {i+1} ---\n" + pytesseract.image_to_string(image, config='--psm 6 -l eng') + "\n" for i, image in enumerate(images))
#             return text.strip()
#         except Exception as e:
#             logger.error(f"OCR extraction failed: {str(e)}")
#             return ""

#     def extract_text_with_fallback(self, pdf_bytes: bytes) -> tuple[str, str]:
#         text = self.extract_text_pymupdf(pdf_bytes)
#         method = "text_extraction"
#         if not text or len(text.strip()) < 50:
#             text = self.extract_text_ocr(pdf_bytes)
#             method = "ocr"
#         return text, method

# def extract_structured_metadata_regex(text: str) -> dict:
#     metadata = {}
#     patterns = {
#         'tenant_name': [r'tenant[:\s]+(.+?)(?:\n|$)', r'lessee[:\s]+(.+?)(?:\n|$)', r'company[:\s]+(.+?)(?:\n|$)'],
#         'landlord_name': [r'landlord[:\s]+(.+?)(?:\n|$)', r'lessor[:\s]+(.+?)(?:\n|$)', r'owner[:\s]+(.+?)(?:\n|$)'],
#         'property_address': [r'property[:\s]+(.+?)(?:\n|$)', r'premises[:\s]+(.+?)(?:\n|$)', r'address[:\s]+(.+?)(?:\n|$)', r'location[:\s]+(.+?)(?:\n|$)'],
#         'lease_term': [r'term[:\s]+(.+?)(?:\n|$)', r'lease term[:\s]+(.+?)(?:\n|$)', r'duration[:\s]+(.+?)(?:\n|$)'],
#         'rent_amount': [r'rent[:\s]*\$?([\d,]+\.?\d*)(?:\s|$)', r'monthly rent[:\s]*\$?([\d,]+\.?\d*)(?:\s|$)', r'base rent[:\s]*\$?([\d,]+\.?\d*)(?:\s|$)'],
#         'square_footage': [r'square feet[:\s]*([\d,]+)', r'sq\.?\s*ft\.?[:\s]*([\d,]+)', r'sf[:\s]*([\d,]+)', r'rsf[:\s]*([\d,]+)'],
#         'commencement_date': [r'commencement[:\s]+(.+?)(?:\n|$)', r'start date[:\s]+(.+?)(?:\n|$)', r'lease start[:\s]+(.+?)(?:\n|$)'],
#         'expiration_date': [r'expiration[:\s]+(.+?)(?:\n|$)', r'end date[:\s]+(.+?)(?:\n|$)', r'lease end[:\s]+(.+?)(?:\n|$)'],
#         'security_deposit': [r'security deposit[:\s]+(.+?)(?:\n|$)', r'deposit[:\s]+(.+?)(?:\n|$)'],
#         'use_clause': [r'use clause[:\s]+(.+?)(?:\n|$)', r'permitted use[:\s]+(.+?)(?:\n|$)', r'use[:\s]+(.+?)(?:\n|$)'],
#         'tenant_improvements': [r'tenant improvements[:\s]+(.+?)(?:\n|$)', r'improvements[:\s]+(.+?)(?:\n|$)', r'ti[:\s]+(.+?)(?:\n|$)']
#     }
#     text_lower = text.lower()
#     for field, pattern_list in patterns.items():
#         for pattern in pattern_list:
#             match = re.search(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
#             if match:
#                 value = match.group(1).strip()
#                 if value and len(value) > 2:
#                     metadata[field] = value
#                     break
#         if field not in metadata:
#             metadata[field] = None
#     metadata['additional_terms'] = ''  # Extract or leave blank
#     metadata['extraction_timestamp'] = datetime.now().isoformat()
#     metadata['text_length'] = len(text)
#     return metadata

# def extract_structured_metadata_with_llm(structured_metadata: str) -> dict:
#     try:
#         project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
#         if not project_id:
#             raise HTTPException(status_code=500, detail="Missing Google Cloud project configuration")
#         model = GenerativeModel("gemini-1.5-pro")
#         prompt = f"""
#         Extract the following information from this Letter of Intent (LOI) text and return it as a JSON object:
#         - tenant_name: Name of the tenant/lessee
#         - landlord_name: Name of the landlord/lessor
#         - property_address: Full address of the property
#         - lease_term: Duration of the lease
#         - rent_amount: Monthly rent amount
#         - square_footage: Size of the space in square feet
#         - commencement_date: Lease start date
#         - expiration_date: Lease end date
#         - security_deposit: Security deposit amount
#         - use_clause: Permitted use of the property
#         - tenant_improvements: Information about tenant improvements
#         - additional_terms: Any other important terms or conditions
#         Text: {structured_metadata}
#         Return only valid JSON. Use null if not found.
#         """
#         response = model.generate_content(prompt)
#         return json.loads(response.text)
#     except Exception as e:
#         logger.error(f"LLM extraction failed: {str(e)}")
#         return extract_structured_metadata_regex(structured_metadata)

# def extract_metadata_from_gcs_enhanced(gcs_path: str, bucket_name: str, credentials) -> dict:
#     client = storage.Client(credentials=credentials)
#     bucket = client.bucket(bucket_name)
#     blob = bucket.blob(gcs_path)
#     if not blob.exists():
#         return {"error": "File not found in GCS", "success": False}
#     content = blob.download_as_bytes()
#     extractor = PDFTextExtractor()
#     structured_metadata, extraction_method = extractor.extract_text_with_fallback(content)
#     if not structured_metadata:
#         return {"error": "Could not extract text from PDF", "success": False}
#     structured_metadata = extract_structured_metadata_with_llm(structured_metadata)
#     return {
#         "extraction_method": extraction_method,
#         "structured_metadata": structured_metadata,
#         "structured_metadata": structured_metadata,
#         "success": True
#     }

# def get_file_info_service(db: Session, file_id: str) -> dict:
#     db_file = get_standalone_file(db, file_id)
#     if not db_file:
#         return None
#     if db_file.structured_metadata:
#         return {
#             "file_id": db_file.file_id,
#             "original_file_name": db_file.original_file_name,
#             "category": db_file.category,
#             "uploaded_at": db_file.uploaded_at,
#             "structured_metadata": db_file.structured_metadata,
#             "structured_metadata": json.loads(db_file.structured_metadata),
#             "success": True
#         }
#     credentials_path = os.getenv("GOOGLE_CLOUD_CREDENTIALS_PATH")
#     if credentials_path:
#         credentials = service_account.Credentials.from_service_account_file(credentials_path)
#     else:
#         credentials_json = get_secret("gcp-credentials")
#         if not credentials_json:
#             raise HTTPException(status_code=500, detail="Missing GCP credentials")
#         credentials = service_account.Credentials.from_service_account_info(json.loads(credentials_json))
#     bucket_name = os.getenv("GCS_BUCKET_NAME")
#     if not bucket_name:
#         raise HTTPException(status_code=500, detail="Missing GCS bucket configuration")
#     extraction_result = extract_metadata_from_gcs_enhanced(db_file.gcs_path, bucket_name, credentials)
#     if extraction_result.get("success"):
#         db_file.structured_metadata = extraction_result["structured_metadata"]
#         db_file.structured_metadata = json.dumps(extraction_result["structured_metadata"])
#         db.commit()
#         db.refresh(db_file)
#     return {
#         "file_id": db_file.file_id,
#         "original_file_name": db_file.original_file_name,
#         "category": db_file.category,
#         "uploaded_at": db_file.uploaded_at,
#         **extraction_result
#     }


# from datetime import datetime
# from typing import Dict, Any

# with open("app/services/templates/lease_template.txt", "r", encoding="utf-8") as f:
#     LEASE_TEMPLATE = f.read()
# def generate_lease_text(metadata: Dict[str, Any]) -> str:
#     # Simple string replacement for placeholders in template
#     lease_text = LEASE_TEMPLATE
#     lease_text = lease_text.replace("_________________________________________________________________", metadata.get('tenant_name', '[TENANT NAME]'))
#     lease_text = lease_text.replace("_____ Main Street, Suite ____", metadata.get('property_address', '[PROPERTY ADDRESS]').split(',')[0])
#     lease_text = lease_text.replace("Dated:  ______________________", f"Dated: {datetime.now().strftime('%B %d, %Y')}")
#     lease_text = lease_text.replace("containing approximately ______________ square feet", f"containing approximately {metadata.get('square_footage', '[SQUARE FOOTAGE]')} square feet")
#     lease_text = lease_text.replace("as and for a ________________________________________________________________", f"as and for a {metadata.get('use_clause', '[USE]')}")
#     lease_text = lease_text.replace("commence on __________________ (“Commencement Date”)", f"commence on {metadata.get('commencement_date', '[COMMENCEMENT DATE]')} (“Commencement Date”)")
#     lease_text = lease_text.replace("end on _______________________________ (“Expiration Date”)", f"end on {metadata.get('expiration_date', '[EXPIRATION DATE]')} (“Expiration Date”)")
#     lease_text = lease_text.replace("a base annual rent of __________________ (“Base Annual Rent”)", f"a base annual rent of {metadata.get('rent_amount', '[RENT AMOUNT]')} (“Base Annual Rent”)")
#     lease_text = lease_text.replace("monthly installments of ______________________ per month (“Base Monthly Rent”)", f"monthly installments of {metadata.get('rent_amount', '[MONTHLY RENT]')} per month (“Base Monthly Rent”)")
#     lease_text = lease_text.replace("$________________", metadata.get('security_deposit', '[SECURITY DEPOSIT]'))
#     # Add more replacements as needed for escalations, TI, etc. For complex, use better templating like jinja
#     # For escalations, calculate if needed
#     return lease_text

# def create_lease_document_service(db: Session, file_id: str) -> BytesIO:
#     file_info = get_file_info_service(db, file_id)
#     if not file_info or not file_info.get('success'):
#         raise HTTPException(status_code=404, detail="File not found or extraction failed")
#     metadata = file_info.get('structured_metadata', {})
#     doc = Document()
#     doc.add_heading('DEED OF LEASE', 0).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
#     # Build full lease structure using metadata, similar to previous but for lease
#     doc.add_paragraph(f"between {metadata.get('landlord_name', '[LANDLORD]')}, as Landlord and {metadata.get('tenant_name', '[TENANT]')}, as Tenant")
#     doc.add_paragraph(f"for {metadata.get('property_address', '[ADDRESS]')}")
#     doc.add_paragraph(f"Dated: {datetime.now().strftime('%B %d, %Y')}")
#     # Add sections 1-38, filling blanks
#     doc.add_heading('1. PREMISES', level=1)
#     doc.add_paragraph(f"Landlord leases to Tenant the space at {metadata.get('property_address', '[ADDRESS]')} containing approximately {metadata.get('square_footage', '[SF]')} square feet.")
#     # Continue adding all sections with filled data...
#     # For brevity, assume full build; in practice, parse template and fill
#     doc_stream = BytesIO()
#     doc.save(doc_stream)
#     doc_stream.seek(0)
#     return doc_stream