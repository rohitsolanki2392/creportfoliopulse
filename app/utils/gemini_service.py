import asyncio
import time
from typing import Dict
import google.generativeai as gen
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool
from app.crud.user_chatbot_crud import (
    get_or_create_chat_session,
    list_user_files,
    save_chat_history,
)
from app.schema.user_chat import AskSimpleQuestionRequest
from app.config import  google_api_key
from app.services.prompts import CLASSIFICATION_PROMPT, SYSTEM_INSTRUCTION
from app.utils.process_file import get_embedding, get_pinecone_index
from app.utils.llm_client import client
async def handle_gemini_chat(
    req: AskSimpleQuestionRequest, current_user, db: AsyncSession
) -> Dict:

    if not google_api_key:
        raise HTTPException(status_code=500, detail="Google API key missing")

    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if current_user.role != "user":
        raise HTTPException(status_code=403, detail="Only users with 'user' role can access Gemini Chat")

    start_time = time.time()
    model = gen.GenerativeModel("gemini-2.0-flash")  


    session = await get_or_create_chat_session(
        db=db,
        session_id=req.session_id,
        user_id=current_user.id,
        category=req.category,
        company_id=current_user.company_id,
        building_id=getattr(req, "building_id", None),
        title=None
    )

    # 2. Load user files for retrieval
    user_files = await list_user_files(db, user_id=current_user.id, is_admin=False)
    filtered_files = [f for f in user_files if f.category == req.category]
    user_file_ids = {f.file_id for f in filtered_files}

    # 3. Classify question
    classification = "general"
    try:
        cls = await asyncio.to_thread(
            model.generate_content,
            CLASSIFICATION_PROMPT.format(query=req.question),
            generation_config={"temperature": 0.0, "max_output_tokens": 10}
        )
        if cls and hasattr(cls, "text"):
            label = cls.text.strip().lower()
            if label in ["general", "retrieval", "google"]:
                classification = label
    except Exception:
        pass  # fallback to general

    # Default response values
    answer = ""
    sources_used = 0
    confidence = 1.0

    # 4. Handle each classification
    if classification == "general":
        final_prompt = SYSTEM_INSTRUCTION + "\n\nUser Question:\n" + req.question
        try:
            resp = await asyncio.to_thread(model.generate_content, final_prompt)
            answer = resp.text.strip() if resp.text else "No response generated."
        except Exception as e:
            answer = f"Sorry, something went wrong: {str(e)}"

    elif classification == "google":
        try:
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=req.question,
                config=GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=[Tool(google_search=GoogleSearch())]
                )
            )
            answer = resp.text.strip() if resp.text else "No response from search."
            sources_used = "google"
        except Exception as e:
            answer = f"Search failed: {str(e)}"
            classification = "general"  # fallback

    elif classification == "retrieval":
        try:
            query_emb = await get_embedding(req.question, google_api_key)
            index = await get_pinecone_index()

            filter_metadata = {
                "company_id": str(current_user.company_id),
                "file_id": {"$in": list(user_file_ids)},
                "category": req.category
            }
            for field in ["building_id", "doc_type", "primary_entity_value"]:
                val = getattr(req, field, None)
                if val is not None:
                    filter_metadata[field] = str(val).strip()

            results = index.query(
                vector=query_emb,
                top_k=10,
                include_metadata=True,
                filter=filter_metadata
            )

            matches = results.get("matches", [])
            if not matches:
                answer = "I couldn't find relevant information in your uploaded documents."
                confidence = 0.0
            else:
                context_chunks = []
                for m in matches:
                    txt = m.get("metadata", {}).get("text", "")
                    if txt and len(txt.strip()) > 50:
                        context_chunks.append(txt.strip())
                    if len(context_chunks) >= 8:
                        break

                final_context = "\n\n".join(context_chunks)[:28000]
                final_prompt = (
                    SYSTEM_INSTRUCTION
                    + "\n\nContext from documents:\n"
                    + final_context
                    + "\n\nUser Question:\n"
                    + req.question
                )

                resp = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=final_prompt,
                    config=GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
                )
                answer = resp.text.strip() if resp.text else "No answer generated."
                sources_used = len(context_chunks)

        except Exception as e:
            answer = f"Retrieval error: {str(e)}"
            confidence = 0.0

    # 5. Finalize timing
    response_time = round(time.time() - start_time, 3)

    # 6. Save chat history (MOST IMPORTANT — now runs in ALL cases)
    response_metadata = {
        "classification": classification,
        "confidence": confidence,
        "response_time": response_time,
        "sources_used": sources_used,
    }

    await save_chat_history(
        db=db,
        session_id=session.id,
        user_id=current_user.id,
        question=req.question,
        answer=answer,
        response_json=response_metadata,
        company_id=current_user.company_id,
        response_time=response_time,
        confidence=confidence,
    )

    # 7. Return consistent response
    return {
        "session_id": str(session.id),       
        "question": req.question,
        "answer": answer,
        "classification": classification,
        "confidence": confidence,
        "response_time": response_time,
        "sources_used": sources_used,
    }