import asyncio
import time
from typing import Dict

import google.generativeai as gen
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.user_chatbot_crud import (
    get_or_create_chat_session,
    list_user_files,
    save_chat_history,
)
from app.schema.user_chat import AskSimpleQuestionRequest
from app.config import  google_api_key
from app.services.prompts import CLASSIFICATION_PROMPT
from app.utils.process_file import get_embedding, get_pinecone_index



# async def handle_gemini_chat(
#     req: AskSimpleQuestionRequest, current_user, db: AsyncSession
# ) -> Dict:
#     if not google_api_key:
#         raise HTTPException(status_code=500, detail="Google API key missing")
#     if not req.question.strip():
#         raise HTTPException(status_code=400, detail="Question cannot be empty")

#     if current_user.role != "user":
#         raise HTTPException(status_code=403, detail="Only users with 'user' role can access Gemini Chat")

#     start_time = time.time()
#     model = gen.GenerativeModel("gemini-2.0-flash")
#     prompt="""You are Portfolio Pulse Utility A.I., an advanced, highly professional, and discreet strategic assistant for commercial real estate and asset managers. Your role is to process and manipulate the text provided by the user for drafting, summarization, and strategic brainstorming. You MUST operate strictly within the context of commercial real estate, leasing, asset management, and corporate finance. You may also provide general, publicly available market context, news summaries, and company contact information. CRITICAL SECURITY MANDATE: You DO NOT have access to the company's proprietary database, RAG indices, or internal documents. Data Accuracy Warning: All external information, news, and generalized contact details provided are drawn from the model's public training data and are not guaranteed to be current, complete, or factually accurate. Users must independently verify all facts. If the user asks a data-specific question that requires private company data, politely inform them that you can only process the information they paste into the chat window. DO NOT provide legal or tax advice; include a professional disclaimer if necessary. 

#     Proprietary Data: Any information stored in the systems private RAG indices, such as the Square Footage of a specific lease comp, the LXD of a client's lease, or contents of a private meeting note. This is explicitly blocked by the instruction: 'You DO NOT have access to the company's proprietary database, RAG indices, or internal documents'.
    
#     Sensitive User Data: The model must not ask for or store sensitive user inputs (e.g., specific financial figures or confidential deal terms), as it is not protected by the RAG system's security.

#     Unauthorized System Actions: It cannot orchestrate complex actions in other enterprise applications."""

#     resp = model.generate_content(prompt + "\n\nUser Input: " + req.question)

#     answer = (resp.text or "").strip()
#     response_time = round(time.time() - start_time, 3)

#     session = await get_or_create_chat_session(
#         db, req.session_id, current_user.id, req.category, current_user.company_id
#     )

#     confidence_score = 1.0
#     classification = "general"
#     sources = []
#     extracted_metadata = {}

#     await save_chat_history(
#         db=db,
#         session_id=session.id,
#         user_id=current_user.id,
#         file_id=None,
#         question=req.question,
#         answer=answer,
#         company_id=current_user.company_id,
#         response_time=response_time,
#         confidence=confidence_score,
#         response_json={
#             "answer": answer,
#             "confidence": confidence_score,
#             "classification": classification,
#             "sources": sources,
#             "extracted_metadata": extracted_metadata,
#         },
#     )

#     return {
#         "session_id": req.session_id,
#         "question": req.question,
#         "answer": answer,
#         "confidence": round(confidence_score, 3),
#         "classification": classification,
#         "response_time": response_time,
#         "sources": sources,
#         "extracted_metadata": extracted_metadata,
#     }

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


    SYSTEM_SECURITY_PROMPT = """
You are Portfolio Pulse Utility A.I., an advanced, highly professional, and discreet strategic assistant for commercial real estate and asset managers.

Your role is to process and manipulate the text provided by the user for drafting, summarization, and strategic brainstorming.

You MUST operate strictly within the context of commercial real estate, leasing, asset management, and corporate finance.

You may also provide general, publicly available market context, news summaries, and company contact information.

CRITICAL SECURITY MANDATE:
- You DO NOT have access to the company's proprietary database, RAG indices, or internal documents.
- You can only use text explicitly provided by the user OR from uploaded files (non-proprietary user documents).
- Data Accuracy Warning: All external information is from public training data and may not be current.

If a question requires internal data, reply:
"I can only work with the information you paste into the chat or upload as documents."

Do not provide legal or tax advice.
"""


    classification = "general"
    try:
        cls = await asyncio.to_thread(
            model.generate_content,
            CLASSIFICATION_PROMPT.format(query=req.question),
            generation_config={"temperature": 0.0, "max_output_tokens": 10}
        )
        ctext = cls.text.strip().lower()
        if ctext in ["general", "retrieval"]:
            classification = ctext
    except:
        pass

    # -----------------------------
    # 2. GET USER FILES FOR RAG (FILTER BY CATEGORY)
    # -----------------------------
    user_files = await list_user_files(db, user_id=current_user.id, is_admin=False)

    # Filter by category from request
    filtered_files = [f for f in user_files if f.category == req.category]
    user_file_ids = {f.file_id for f in filtered_files}

    # -----------------------------
    # 3. GENERAL MODE (NO FILES OR GENERAL CLASSIFICATION)
    # -----------------------------
    if classification == "general" or not user_file_ids:
        final_prompt = SYSTEM_SECURITY_PROMPT + "\n\nUser Input: " + req.question

        resp = await asyncio.to_thread(model.generate_content, final_prompt)
        answer = resp.text.strip()

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

    # -----------------------------
    # 4. RAG MODE (USER HAS FILES IN CATEGORY)
    # -----------------------------
    query_emb = await get_embedding(req.question, google_api_key)
    index = await get_pinecone_index()

    # Filter only user files in this category
    filter_metadata = {
        "company_id": str(current_user.company_id),
        "file_id": {"$in": list(user_file_ids)},
        "category": req.category
    }

    # Optional metadata filters
    optional_fields = ["building_id", "doc_type", "primary_entity_value"]
    for field in optional_fields:
        val = getattr(req, field, None)
        if val and str(val).strip():
            filter_metadata[field] = str(val).strip()

    results = index.query(
        vector=query_emb,
        top_k=50,
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

    # -----------------------------
    # 5. BUILD CONTEXT FROM TOP CHUNKS
    # -----------------------------
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

    # -----------------------------
    # 6. GENERATE FINAL RESPONSE
    # -----------------------------
    final_prompt = (
        SYSTEM_SECURITY_PROMPT
        + "\n\nContext from user-uploaded documents:\n"
        + final_context
        + "\n\nUser Question: "
        + req.question
    )

    resp = await asyncio.to_thread(model.generate_content, final_prompt)

    return {
        "session_id": req.session_id,
        "question": req.question,
        "answer": resp.text.strip(),
        "classification": "retrieval",
        "confidence": 1.0,
        "response_time": round(time.time() - start_time, 3),
        "sources_used": len(top_sources),
    }