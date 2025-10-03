
import re
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from langchain_core.prompts import ChatPromptTemplate
from app.crud.user_chatbot_crud import get_or_create_chat_session, save_chat_history, save_standalone_file
from app.models.models import  StandaloneFile
from app.schema.chat_bot_schema import FileItem, ListFilesResponse
from app.schema.user_chat import StandaloneFileResponse
from app.utils.process_file import get_embedding, get_pinecone_index, save_to_temp, process_uploaded_file
from datetime import datetime
import json
import logging
from uuid import uuid4
import os
import logging
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.models import StandaloneFile
from app.config import google_api_key
from app.utils.process_file import get_pinecone_index, process_uploaded_file, save_to_temp
from app.utils.llm_client import llm

SUPPORTED_EXT = ['.pdf', '.docx', '.txt', '.xlsx','.csv']


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
    db: Session,
    building_id: Optional[int] = None 
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can upload categorized files")
        
    # google_api_key = os.getenv("GOOGLE_API_KEY")

    company_id = current_user.company_id


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
                temp_path, file.filename, file_id, google_api_key, category, company_id, building_id=building_id
            )

            saved_file = save_standalone_file(
                db=db,
                file_id=file_id,
                file_name=file.filename,
                user_id=current_user.id,
                category=category,
                gcs_path=unique_filename, 
                file_size=str(file_size),
                company_id=company_id,
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

async def ask_simple_service(req, current_user, db: Session):
    # google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise HTTPException(500, "Google API key missing")

    if not req.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    logger.info(f"Received question: '{req.question}'")

    question_lower = req.question.lower().strip()

    # llm = ChatGoogleGenerativeAI(
    #     model="gemini-2.0-flash", google_api_key=google_api_key, temperature=0.2
    # )

    classification_prompt = """
    You are a helpful assistant that classifies user queries into two categories: 'general' or 'specific'.
    - 'general' queries include greetings(e.g., "Hello", "How are you?").
    - 'specific' queries are related to categorized files, inquiries about documents, or specific information (e.g., "What is in the lease agreement?", "Find details about the tenant contract").
    Based on the query, return a JSON object with a single key 'query_type' and a value of either 'general' or 'specific'.
    Do not assume or infer beyond the query provided.

    Query: {query}
    """
    prompt = ChatPromptTemplate.from_messages([("system", classification_prompt), ("human", question_lower)])

    try:
        response = await llm.ainvoke(prompt.format_messages(query=question_lower))
        content = response.content.strip()
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)

        classification = json.loads(content)
        query_type = classification.get("query_type")

        if query_type not in ["general", "specific"]:
            logger.error(f"Invalid query type returned: {query_type}")
            raise HTTPException(status_code=500, detail="Failed to classify query type")
    except Exception as e:
        logger.error(f"Failed to classify query: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to classify query type")
    if query_type == "general":
        general_prompt = """
        You are a friendly assistant responding to general questions or greetings.
        Provide a concise, conversational response appropriate to the user's query.
        Query: {query}
        """
        prompt = ChatPromptTemplate.from_messages([("system", general_prompt), ("human", req.question)])
        try:
            response = await llm.ainvoke(prompt.format_messages(query=req.question))
            answer = response.content.strip()
        except Exception as e:
            logger.error(f"Failed to generate response for general query: {str(e)}")
            answer = "Hello! How can I assist you today?"

    else:
        try:
            query_emb = await get_embedding(req.question, google_api_key)
            index = get_pinecone_index()

            filter_metadata = {"category": req.category, "company_id": str(current_user.company_id)}
            if getattr(req, "building_id", None) and str(req.building_id).strip():
                filter_metadata["building_id"] = str(req.building_id)

            logger.info(f"Using Pinecone filter: {filter_metadata}")

            result = index.query(
                vector=query_emb,
                top_k=5,
                include_metadata=True,
                filter=filter_metadata
            )

            if not result["matches"]:
                logger.warning("No Pinecone matches found")
                answer = "Information not available in documents"
                return {
                    "session_id": req.session_id,
                    "question": req.question,
                    "answer": answer,
                    "source_file": None,
                    "all_answers": [],
                }
            else:
                for m in result["matches"]:
                    logger.info(f"Match score: {m['score']}, Chunk: {m['metadata']['chunk'][:2000]}")

                contexts = [match["metadata"]["chunk"] for match in result["matches"]]
                combined_context = "\n\n".join(contexts) 

                system_prompt = """
                You are an expert analyst specializing in lease agreements and property management.
                Use the provided context to answer questions accurately and concisely.
                - Reply politely if user greets you like hii, hello
                - Focus on key details like dates, clauses, obligations, and financial terms
                - Use bullet points for structured responses when appropriate
                - If the question involves calculations, show your work
                - Reference specific document sections when relevant
                - Do not add information beyond the context
                - Use the context to answer as best as you can.
                - Maintain professional, neutral tone
                Context: {context}
                """
                prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", req.question)])
                response = await llm.ainvoke(prompt.format_messages(context=combined_context))
                answer = response.content.strip()

        except Exception as e:
            logger.error(f"Failed to search results: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve information from files")

        if not answer:
            answer = "I'm sorry, I couldn't find relevant information in your files."
     
    session = get_or_create_chat_session(db, req.session_id, current_user.id, req.category, current_user.company_id)

    save_chat_history(
        db=db,
        session_id=session.id,
        user_id=current_user.id,
        file_id=None,
        question=req.question,
        answer=answer,
        company_id=current_user.company_id,
        response_json={"query_type": query_type, "answer": answer}
    )

    return {
        "session_id": req.session_id,
        "question": req.question,
        "answer": answer,
        "source_file": None,
        "all_answers": [],
    }


async def list_simple_files_service(
    building_id: Optional[int],
    category: Optional[str],
    current_user,
    db: Session
) -> ListFilesResponse:

    query = db.query(StandaloneFile).filter(
        StandaloneFile.company_id == current_user.company_id
    )

    if building_id is not None:
        query = query.filter(StandaloneFile.building_id == building_id)

    if category:
        query = query.filter(StandaloneFile.category == category)

    files = query.all()

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
    db: Session,
    building_id: Optional[int] = None,
    category: Optional[str] = None
):
    # google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise HTTPException(status_code=500, detail="Configuration missing: GOOGLE_API_KEY")

    existing_file = db.query(StandaloneFile).filter(StandaloneFile.file_id == file_id).first()
    if not existing_file:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")

    category_to_use = category or existing_file.category
    temp_path = None

    try:
        temp_path = await save_to_temp(new_file, file_id, current_user, category_to_use)

        file_ext = os.path.splitext(new_file.filename)[1].lower()
        unique_filename = f"standalone_files/{file_id}{file_ext}"


        index = get_pinecone_index()
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
        db.commit()
        db.refresh(existing_file)

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
    db: Session
):
    """
    Delete a standalone file from DB, Pinecone, and optionally local storage
    based on file_id (+ optional building_id, category).
    Checks if the current user has permission to delete the file.
    """

    query = db.query(StandaloneFile).filter(StandaloneFile.file_id == file_id)

    if building_id:
        query = query.filter(StandaloneFile.building_id == building_id)

    if category:
        query = query.filter(StandaloneFile.category == category)

    file_record = query.first()

    if not file_record:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")

    if current_user.role != "admin" and file_record.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this file")
    try:
        index = get_pinecone_index()
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
        db.delete(file_record)
        db.commit()
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
