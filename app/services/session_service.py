from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.crud.user_chatbot_crud import delete_user_chat_session
from app.models.models import ChatSession, ChatHistory
from sqlalchemy.future import select


async def list_chat_sessions_service(
    current_user,
    db: AsyncSession,
    category: Optional[str] = None
):
    """Lists chat sessions for the user, optionally filtered by category."""


    query = select(ChatSession).where(ChatSession.user_id == current_user.id)


    if category:
        query = query.where(ChatSession.category == category)

    query = query.order_by(ChatSession.created_at.desc())

    result = await db.execute(query)
    sessions = result.scalars().all()

   
    if not sessions:
        return []  
    session_list = []

    for s in sessions:

        msg_result = await db.execute(
            select(ChatHistory)
            .where(ChatHistory.chat_session_id == s.id)
            .where(ChatHistory.user_id == current_user.id)
            .order_by(ChatHistory.timestamp.asc())
        )
        messages = msg_result.scalars().all()


        title = s.title
        if not title:
            if messages:

                title = messages[1].question if len(messages) > 1 else messages[0].question
                s.title = title
                db.add(s)
                await db.commit()
                await db.refresh(s)
            else:
                title = "Untitled Session"

        session_list.append({
            "session_id": s.id,
            "title": title,
            "category": s.category,
            "created_at": s.created_at,
            "building_id": s.building_id
        })

    return session_list


async def get_session_history_service(session_id: str, current_user, db: AsyncSession):
    stmt = select(ChatHistory).where(
        ChatHistory.chat_session_id == session_id,
        ChatHistory.user_id == current_user.id
    ).order_by(ChatHistory.timestamp.asc())

    result = await db.execute(stmt)
    history = result.scalars().all()
    
    if not history:
        return []

    return [{"question": h.question, "answer": h.answer} for h in history]

async def delete_session_service(session_id: str, current_user, db: AsyncSession):
    """Delete a chat session."""
    session = await delete_user_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found or you do not have access")
    
    return {"message": "Session successfully deleted"}
