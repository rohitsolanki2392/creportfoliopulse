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
from app.services.prompts import CLASSIFICATION_PROMPT
from app.utils.process_file import get_embedding, get_pinecone_index
from app.utils.llm_client import client
from fastapi import HTTPException


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


    classification = "general"
    try:
        cls = await asyncio.to_thread(
            model.generate_content,
            CLASSIFICATION_PROMPT.format(query=req.question),
            generation_config={"temperature": 0.0, "max_output_tokens": 10}
        )
        if cls and hasattr(cls, "text"):
            ctext = cls.text.strip().lower()
            if ctext in ["general", "retrieval"]:
                classification = ctext
    except Exception as e:
        print(f"Classification error: {e}")


    system_instruction = """You are Portfolio Pulse Utility A.I., an advanced, highly professional, and discreet strategic assistant for commercial real estate and asset managers. Your role is solely to process and manipulate the text provided by the user for drafting, summarization, and strategic brainstorming. You MUST operate strictly within the context of commercial real estate, leasing, asset management, and corporate finance. 

You may use Google Search to find public information, news summaries, and company contact details to fulfill the user's request.

CRITICAL: You DO NOT have access to the company's proprietary database, RAG indices, or internal documents. If the user asks a data-specific question, politely inform them that you can only process the information they paste into the chat window. 

DO NOT provide legal or tax advice; include a professional disclaimer if necessary."""


    user_files = await list_user_files(db, user_id=current_user.id, is_admin=False)
    filtered_files = [f for f in user_files if f.category == req.category]
    user_file_ids = {f.file_id for f in filtered_files}


    if classification == "general" or not user_file_ids:
        final_prompt = system_instruction + "\n\nUser Input: " + req.question
        try:
            resp = await asyncio.to_thread(model.generate_content, final_prompt)
            answer = resp.text.strip() if resp and hasattr(resp, "text") else "No answer generated."
        except Exception as e:
            answer = f"Error generating response: {e}"

        response_time = round(time.time() - start_time, 3)

        session = await get_or_create_chat_session(
            db, req.session_id, current_user.id, req.category, current_user.company_id
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
            confidence=1.0,
            response_json={"classification": "general"}
        )

        return {
            "session_id": req.session_id,
            "question": req.question,
            "answer": answer,
            "classification": "general",
            "confidence": 1.0,
            "response_time": response_time,
            "sources_used": 0,
        }


    query_emb = await get_embedding(req.question, google_api_key)
    index = await get_pinecone_index()

    filter_metadata = {
        "company_id": str(current_user.company_id),
        "file_id": {"$in": list(user_file_ids)},
        "category": req.category
    }

    optional_fields = ["building_id", "doc_type", "primary_entity_value"]
    for field in optional_fields:
        val = getattr(req, field, None)
        if val and str(val).strip():
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
        response_time = round(time.time() - start_time, 3)

        session = await get_or_create_chat_session(
            db, req.session_id, current_user.id, req.category, current_user.company_id
        )

        await save_chat_history(
            db=db,
            session_id=session.id,
            user_id=current_user.id,
            question=req.question,
            answer=answer,
            response_time=response_time,
            confidence=0.0,
            company_id=current_user.company_id,
            response_json={"classification": "retrieval"}
        )

        return {
            "session_id": req.session_id,
            "question": req.question,
            "answer": answer,
            "classification": "retrieval",
            "confidence": 0.0,
            "response_time": response_time,
            "sources_used": 0
        }


    matches.sort(key=lambda m: m.get("score", 0), reverse=True)
    context_chunks = []
    top_sources = set()
    selected = []

    for m in matches:
        md = m.get("metadata", {})
        text = md.get("text", "")
        if text and len(text.strip()) > 50:
            context_chunks.append(text.strip())
            selected.append(m)
            top_sources.add(md.get("chunk_title", "Document Section"))
        if len(context_chunks) >= 8:
            break

    final_context = "\n\n".join(context_chunks)
    if len(final_context) > 28000:
        final_context = final_context[:28000] + "\n\n... (truncated)"

    final_prompt = (
        system_instruction
        + "\n\nContext from user-uploaded documents:\n"
        + final_context
        + "\n\nUser Question: "
        + req.question
    )


    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=final_prompt,
            config=GenerateContentConfig(
                system_instruction=final_prompt,
                tools=[Tool(google_search=GoogleSearch())]
            )
        )
        answer = resp.text.strip() if resp and hasattr(resp, "text") else "No answer generated."
    except Exception as e:
        answer = f"Error generating RAG response: {e}"

    response_time = round(time.time() - start_time, 3)

    return {
        "session_id": req.session_id,
        "question": req.question,
        "answer": answer,
        "classification": "retrieval",
        "confidence": 1.0,
        "response_time": response_time,
        "sources_used": len(top_sources),
    }

