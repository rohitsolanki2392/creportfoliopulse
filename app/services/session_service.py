from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.crud.user_chatbot_crud import delete_user_chat_session, get_user_chat_history, list_user_chat_sessions
from app.models.models import ChatSession, ChatHistory

async def list_chat_sessions_service(current_user, db: AsyncSession):
    """Lists chat sessions for the user."""
    sessions = list_user_chat_sessions(db, current_user.id)

    session_list = []
    for s in sessions:
        messages = (db.query(ChatHistory).filter_by(chat_session_id=s.id, user_id=current_user.id).order_by(ChatHistory.timestamp.asc()).all())

        title = s.title if s.title else "Untitled Session"

        if not s.title and messages:
            title = messages[1].question if len(messages) >= 2 else messages[0].question
            s.title = title
            db.add(s)
            await db.commit()
            db.refresh(s)

        session_list.append({
            "session_id": s.id,
            "title": title,
            "category": s.category,
            "created_at": s.created_at,
            "building_id": s.building_id
        })

    return session_list


async def get_session_history_service(session_id: str, current_user, db: AsyncSession):
    """Fetch chat history for a session."""
    session = db.query(ChatSession).filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found or you do not have access")

    messages = get_user_chat_history(db, session_id, current_user.id)
    return [
        {
            "question": m.question,
            "answer": m.answer,
            "timestamp": m.timestamp,
            "file_id": m.file_id
        }
        for m in messages
    ]


async def delete_session_service(session_id: str, current_user, db: AsyncSession):
    """Delete a chat session."""
    session = delete_user_chat_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found or you do not have access")
    return {"message": "Session successfully deleted"}
