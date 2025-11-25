import asyncio
import time
from typing import  Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.user_chatbot_crud import get_or_create_chat_session, save_chat_history, save_standalone_file
from app.models.models import  StandaloneFile, User
from app.schema.chat_bot_schema import FileItem, ListFilesResponse
from app.schema.user_chat import AskSummaryChatRequest, StandaloneFileResponse
from app.utils.process_file import get_embedding, get_pinecone_index, save_to_temp, process_uploaded_file
from datetime import datetime
import logging
from uuid import uuid4
import os
import logging
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.models.models import StandaloneFile
from app.config import google_api_key
from app.utils.process_file import get_pinecone_index, process_uploaded_file, save_to_temp
from app.services.prompts import  CLASSIFICATION_PROMPT, GENERAL_PROMPT_TEMPLATE, SYSTEM_PROMPT,summary_system_prompt
from app.config import SUPPORTED_EXT
from sqlalchemy.future import select
import google.generativeai as gen



gen.configure(api_key=google_api_key)


logger = logging.getLogger(__name__)

def human_readable_size(size_in_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} PB"




async def upload_standalone_files_service(
    files, 
    category, 
    current_user, 
    db: AsyncSession,
    building_id: Optional[int] = None 
):
    if not (
        current_user.role == "admin" or
        (current_user.role == "user" and category == "Gemini")
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to upload files for this category."
        )

    uploaded_files = []

    for file in files:
        temp_path = None
        try:
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in SUPPORTED_EXT:
                logger.warning(f"Unsupported file type for {file.filename}: {file_ext}")
                continue

            file_id = str(uuid4())
            temp_path = await save_to_temp(file, file_id, current_user, category)
            file_size = os.path.getsize(temp_path)
            if file_size == 0:
                logger.warning(f"Empty file: {file.filename}")
                os.remove(temp_path)
                continue
            unique_filename = f"standalone_files/{file_id}{file_ext}"


            await process_uploaded_file(
    file_path=temp_path,
    filename=file.filename,
    file_id=file_id,
    category=category,
    company_id=current_user.company_id,
    building_id=building_id
)

            saved_file = await save_standalone_file(
                db=db,
                file_id=file_id,
                file_name=file.filename,
                user_id=current_user.id,
                category=category,
                gcs_path=unique_filename, 
                file_size=str(file_size),
                company_id=current_user.company_id,
                building_id=building_id
            )

            uploaded_files.append({
                "file_id": saved_file.file_id,
                "original_file_name": saved_file.original_file_name,
                "category": saved_file.category,
                "url": "", 
                "user_id": current_user.id,
                "uploaded_at": saved_file.uploaded_at or datetime.utcnow(),
                "size": human_readable_size(file_size),
                "gcs_path": unique_filename,  
                "building_id": str(building_id) if building_id is not None else "",
            })
            logger.info(f"Successfully processed {file.filename}")
        
        except Exception as e:
            logger.error(f"Failed to process file {file.filename}: {str(e)}")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    if not uploaded_files:
        raise HTTPException(status_code=400, detail="Upload failed. No valid files were provided. Please check once.")
    
    return uploaded_files


async def ask_simple_service(req, current_user, db):
    if not req.question or not req.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    logger.info(f"Question from user {current_user.id}: {req.question}")
    start_time = time.time()

    model = gen.GenerativeModel("gemini-2.0-flash")

    try:
        
        classification = "retrieval"  
        try:
            resp = await asyncio.to_thread(
                model.generate_content,
                CLASSIFICATION_PROMPT.format(query=req.question),
                generation_config={"temperature": 0.0, "max_output_tokens": 10}
            )
            text = resp.text.strip().lower()
            if text in ["general", "retrieval"]:
                classification = text
        except Exception as e:
            logger.warning(f"Classification failed: {e}")

        logger.info(f"Query classified as: {classification}")


        if classification == "general":
            prompt = GENERAL_PROMPT_TEMPLATE.format(query=req.question)
            response = await asyncio.to_thread(model.generate_content, prompt)
            answer = response.text.strip() or "I'm here to help with your real estate documents!"
            confidence = 1.0
            sources_used = 0

  
        else:
           
            query_emb = await get_embedding(req.question, google_api_key)
            index = await get_pinecone_index()

           
            filter_metadata = {"company_id": str(current_user.company_id)}
            optional_fields = ["category", "building_id", "doc_type", "primary_entity_value"]
            for field in optional_fields:
                val = getattr(req, field, None)
                if val and str(val).strip():
                    filter_metadata[field] = str(val).strip()

            logger.info(f"Pinecone filter: {filter_metadata}")

           
            results = index.query(
                vector=query_emb,
                top_k=50, 
                include_metadata=True,
                filter=filter_metadata,
            )

            matches = results.get("matches", [])
            if not matches:
                answer = "I couldn't find relevant information in your uploaded documents."
                confidence = 0.0
                sources_used = 0
            else:
                
                matches.sort(key=lambda m: m.get("score", 0), reverse=True)

                relevant_chunks = []
                contexts = []
                source_titles = set()
                for match in matches:
                    metadata = match.get("metadata", {})
                    full_text = metadata.get("text", "")
                    title = metadata.get("chunk_title", "Document Section")

                    if full_text and len(full_text.strip()) > 50:
                        contexts.append(full_text.strip())
                        relevant_chunks.append(match)
                        source_titles.add(title)

                    if len(relevant_chunks) >= 8:
                        break

                combined_context = "\n\n".join(contexts)
                if len(combined_context) > 28_000:
                    combined_context = combined_context[:28_000] + "\n\n... (truncated)"

            
                final_prompt = SYSTEM_PROMPT.format(context=combined_context, query=req.question)
                response = await asyncio.to_thread(model.generate_content, final_prompt)
                answer = response.text.strip()

                confidence = max(m.get("score", 0) for m in relevant_chunks) if relevant_chunks else 0.0
                sources_used = len(relevant_chunks)

                if source_titles and len(source_titles) <= 4:
                    answer += "\n\nSources:\n" + "\n".join(f"• {t}" for t in source_titles)

     
        end_time = time.time()
        response_time = round(end_time - start_time, 3)

        session = await get_or_create_chat_session(
            db, req.session_id, current_user.id, req.category or "general", current_user.company_id
        )

        await save_chat_history(
            db=db,
            session_id=session.id,
            user_id=current_user.id,
            file_id=None,
            question=req.question,
            answer=answer,
            company_id=current_user.company_id,
            response_time=response_time,
            confidence=confidence,
            response_json={
                "classification": classification,
                "sources_used": sources_used,
                "confidence": round(confidence, 3),
            },
        )

        return {
            "session_id": req.session_id,
            "question": req.question,
            "answer": answer,
            "confidence": round(confidence, 3),
            "classification": classification,
            "response_time": response_time,
            "sources_used": sources_used,
        }

    except Exception as e:
        logger.error(f"RAG Error: {str(e)}", exc_info=True)
        raise HTTPException(500, "Sorry, I couldn't process your request right now.")



async def ask_summary_chat_service(req, current_user,db):
    if not google_api_key:
        logger.error("Google API key missing")
        raise HTTPException(500, "Google API key missing")
    if not req.question or not req.question.strip():
        logger.warning("Empty question received")
        raise HTTPException(400, "Question cannot be empty")

    logger.info(f"Processing summary chat | Question: '{req.question}' | file_id: {req.file_id}")
    start_time = time.time()
    model = gen.GenerativeModel("gemini-2.0-flash")  

    try:
    
        classification = "retrieval"
        try:
            resp = await asyncio.to_thread(
                model.generate_content,
                CLASSIFICATION_PROMPT.format(query=req.question),
                generation_config={"temperature": 0.0, "max_output_tokens": 10}
            )
            text = resp.text.strip().lower()
            if text in ["general", "retrieval"]:
                classification = text
        except Exception as e:
            logger.warning(f"Classification failed for '{req.question}': {e}")

        logger.info(f"Query classified as: {classification}")

        answer = ""
        confidence = 0.0
        combined_context = ""

        if classification == "general":

            prompt = GENERAL_PROMPT_TEMPLATE.format(query=req.question)
            response = await asyncio.to_thread(model.generate_content, prompt)
            answer = response.text.strip() or "No answer generated."
            confidence = 1.0

        else:

            query_emb = await get_embedding(req.question, google_api_key)
            index = await get_pinecone_index()


            filter_metadata = {"company_id": str(current_user.company_id)}

            if req.category and str(req.category).strip():
                filter_metadata["category"] = str(req.category).strip()
            if req.file_id and str(req.file_id).strip():
                filter_metadata["file_id"] = str(req.file_id).strip()


            filter_metadata = {k: v for k, v in filter_metadata.items() if v is not None}

            logger.info(f"Pinecone filter applied: {filter_metadata}")

            results = index.query(
                vector=query_emb,
                top_k=50,
                include_metadata=True,
                filter=filter_metadata,
            )

            matches = results.get("matches", [])
            logger.info(f"Pinecone returned {len(matches)} matching chunks")

            if not matches:
                answer = "No relevant information found in the summary."
                confidence = 0.0
            else:
                matches.sort(key=lambda m: m.get("score", 0), reverse=True)
                contexts = []
                relevant_matches = []
                source_titles = set()

                for match in matches:
                    metadata = match.get("metadata", {})
       
                    chunk_text = metadata.get("text", "").strip()
                    title = metadata.get("chunk_title", "Document Section")

                    if chunk_text and len(chunk_text) > 50:
                        contexts.append(chunk_text)
                        relevant_matches.append(match)
                        source_titles.add(title)

                    if len(relevant_matches) >= 8:
                        break

                combined_context = "\n\n".join(contexts)
                if len(combined_context) > 28_000:
                    combined_context = combined_context[:28_000] + "\n\n... (truncated)"

                logger.info(f"Combined context length: {len(combined_context)} characters")

                final_prompt = summary_system_prompt.format(context=combined_context, query=req.question)
                response = await asyncio.to_thread(model.generate_content, final_prompt)
                answer = response.text.strip() or "No answer generated."
                confidence = max(m.get("score", 0) for m in relevant_matches) if relevant_matches else 0.0

                if source_titles and len(source_titles) <= 4:
                    answer += "\n\nSources:\n" + "\n".join(f"• {t}" for t in source_titles)


        response_time = round(time.time() - start_time, 3)
        logger.info(f"Summary chat processed in {response_time}s | Confidence: {confidence:.3f}")

        session = await get_or_create_chat_session(
            db=db,
            session_id=req.session_id,
            user_id=current_user.id,
            category=req.category or "general",
            company_id=current_user.company_id
        )

        await save_chat_history(
            db=db,
            session_id=session.id,
            user_id=current_user.id,
            file_id=req.file_id,
            question=req.question,
            answer=answer,
            company_id=current_user.company_id,
            response_time=response_time,
            confidence=confidence,
            response_json={
                "answer": answer,
                "confidence": round(confidence, 3),
                "file_id": req.file_id,
                "context_length": len(combined_context)
            },
        )

        return {
            "session_id": session.id,
            "file_id": req.file_id,
            "question": req.question,
            "answer": answer,
            "confidence": round(confidence, 3),
            "response_time": response_time,
        }

    except Exception as e:
        logger.error(f"Error during summary chat: {e}", exc_info=True)
        raise HTTPException(500, "Error processing summary chat")

async def list_simple_files_service(
    building_id: Optional[int],
    category: Optional[str],
    current_user,
    db: AsyncSession
) -> ListFilesResponse:


    stmt = select(StandaloneFile).where(
        StandaloneFile.company_id == current_user.company_id
    )
    if building_id is not None:
        stmt = stmt.where(StandaloneFile.building_id == building_id)
    if category:
        stmt = stmt.where(StandaloneFile.category == category)

    result = await db.execute(stmt)               
    files = result.scalars().all()

    result: list[FileItem] = []
    total_size_bytes = 0

    for file in files:
        try:
            size = int(file.file_size) if file.file_size else 0
        except Exception:
            size = 0

        total_size_bytes += size

        result.append(FileItem(
            file_id=file.file_id,
            original_file_name=file.original_file_name,
            url="",  
            user_id=file.user_id,
            uploaded_at=file.uploaded_at,
            size=human_readable_size(size),
            category=file.category,
            gcs_path=file.gcs_path,  
            building_id=file.building_id,
        ))

    return ListFilesResponse(
        files=result,
        total_files=len(result),
        total_size=human_readable_size(total_size_bytes),
        user_email=current_user.email,
        building_id=building_id,
        category=category,
    )


async def update_standalone_file_service(
    file_id: str,
    new_file: UploadFile,
    current_user,
    db: AsyncSession,
    building_id: Optional[int] = None,
    category: Optional[str] = None
):



    if not google_api_key:
        raise HTTPException(status_code=500, detail="Configuration missing: GOOGLE_API_KEY")

    stmt = select(StandaloneFile).where(StandaloneFile.file_id == file_id)
    existing_file = (await db.execute(stmt)).scalar_one_or_none()
    if not existing_file:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")

    category_to_use = category or existing_file.category
    temp_path = None

    try:
        temp_path = await save_to_temp(new_file, file_id, current_user, category_to_use)

        file_ext = os.path.splitext(new_file.filename)[1].lower()
        unique_filename = f"standalone_files/{file_id}{file_ext}"


        index =await get_pinecone_index()
        index.delete(filter={"file_id": file_id})

        await process_uploaded_file(
            temp_path, new_file.filename, file_id, google_api_key, category_to_use, current_user.company_id, building_id=building_id
        )


        existing_file.original_file_name = new_file.filename
        existing_file.building_id = building_id
        existing_file.file_size = str(os.path.getsize(temp_path))
        existing_file.gcs_path = unique_filename
        existing_file.category = category_to_use
        existing_file.uploaded_at = datetime.utcnow()
        await db.commit()                              
        await db.refresh(existing_file)

        return {
            "file_id": existing_file.file_id,
            "original_file_name": existing_file.original_file_name,
            "category": existing_file.category,
            "url": "",  
            "user_id": current_user.id,
            "uploaded_at": existing_file.uploaded_at,
            "size": human_readable_size(os.path.getsize(temp_path)),
            "gcs_path": unique_filename,
            "building_id": str(building_id) if building_id else ""
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update file: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


async def delete_simple_file_service(
    building_id: Optional[int],
    file_id: str,
    category: Optional[str],
    current_user,
    db: AsyncSession
):
    stmt = select(StandaloneFile).where(StandaloneFile.file_id == file_id)
    if building_id:
        stmt = stmt.where(StandaloneFile.building_id == building_id)
    if category:
        stmt = stmt.where(StandaloneFile.category == category)

    file_record = (await db.execute(stmt)).scalar_one_or_none()  

    if not file_record:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")

    if current_user.role != "admin" and file_record.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this file")
    try:
        index =await get_pinecone_index()
        index.delete(filter={"file_id": file_id})
        logger.info(f"Deleted vectors for file_id {file_id} from Pinecone")
    except Exception as e:
        logger.error(f"Failed to delete Pinecone vectors for file_id {file_id}: {e}")
    try:
        if file_record.gcs_path:  
            local_path = os.path.join("standalone_files", os.path.basename(file_record.gcs_path))
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"Deleted local file {local_path}")
    except Exception as e:
        logger.error(f"Failed to delete local file {file_record.gcs_path}: {e}")

    try:
        await db.delete(file_record)                   
        await db.commit()
        logger.info(f"Deleted file record {file_id} from database")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete file record {file_id} from DB: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file from DB: {str(e)}")


    return StandaloneFileResponse(
        file_id=file_record.file_id,
        original_file_name=file_record.original_file_name,
        category=file_record.category,
        url="", 
        user_id=file_record.user_id,
        uploaded_at=file_record.uploaded_at,
        size=file_record.file_size,
        gcs_path=file_record.gcs_path, 
        building_id=str(file_record.building_id) if file_record.building_id else ""
    )
