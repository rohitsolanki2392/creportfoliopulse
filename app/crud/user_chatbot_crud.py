from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import ChatHistory, ChatSession, StandaloneFile
from typing import Dict
async def save_standalone_file(
    db: AsyncSession,
    file_id: str,
    file_name: str,
    user_id: int,
    category: str,
    gcs_path: str,
    file_size: str,
    company_id: int,
    building_id: Optional[int] = None

    
) -> StandaloneFile:
    new_file = StandaloneFile(
        file_id=file_id,
        original_file_name=file_name,
        user_id=user_id,
        building_id=building_id,
        category=category,
        gcs_path=gcs_path,
        file_size=file_size,
        uploaded_at=datetime.utcnow(),
        company_id=company_id
    )
    db.add(new_file)
    await db.commit()
    await db.refresh(new_file)
    return new_file


async def list_user_files(db: AsyncSession, user_id: int, is_admin: bool) -> List[StandaloneFile]:
    stmt = select(StandaloneFile)
    if not is_admin:
        stmt = stmt.where(StandaloneFile.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_standalone_file(db: AsyncSession, file_id: str) -> Optional[StandaloneFile]:
    result = await db.execute(select(StandaloneFile).where(StandaloneFile.file_id == file_id))
    return result.scalars().first()


async def delete_standalone_file(db: AsyncSession, file_id: str) -> Optional[StandaloneFile]:
    file_obj = await get_standalone_file(db, file_id)
    if file_obj:
        await db.delete(file_obj)
        await db.commit()
    return file_obj


async def get_or_create_chat_session(
    db: AsyncSession,
    session_id: Optional[str],
    user_id: int,
    category: Optional[str] = None,
    company_id: Optional[int] = None,
    title: Optional[str] = None,
    building_id: Optional[int] = None
) -> ChatSession:
    session = None
    if session_id:
        result = await db.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        session = result.scalars().first()

    if not session:
        session = ChatSession(
            id=session_id,
            user_id=user_id,
            category=category,
            title=title,
            company_id=company_id,
            building_id=building_id,
            created_at=datetime.utcnow(),
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
    return session


async def list_user_chat_sessions(db: AsyncSession, user_id: int) -> List[ChatSession]:
    result = await db.execute(
        select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc())
    )
    return result.scalars().all()


async def delete_user_chat_session(db: AsyncSession, session_id: str, user_id: int) -> Optional[ChatSession]:
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    session = result.scalars().first()
    if session:
        await db.delete(session)
        await db.commit()
    return session




async def save_chat_history(
    db: AsyncSession,
    session_id: str,
    user_id: int,
    question: str,
    answer: str,
    file_id: Optional[str] = None,
    response_json: Optional[dict] = None,
    company_id: Optional[int] = None,
    response_time: Optional[float] = None,
    confidence: Optional[float] = None
) -> ChatHistory:
    chat_history = ChatHistory(
        chat_session_id=session_id,
        user_id=user_id,
        file_id=file_id,
        question=question,
        answer=answer,
        response_json=response_json,
        company_id=company_id,
        timestamp=datetime.utcnow(),
        response_time=response_time,
        confidence=confidence
    )
    db.add(chat_history)
    await db.commit()
    await db.refresh(chat_history)
    return chat_history


async def get_user_chat_history(db: AsyncSession, session_id: str, user_id: int) -> List[ChatHistory]:
    result = await db.execute(
        select(ChatHistory)
        .where(ChatHistory.chat_session_id == session_id, ChatHistory.user_id == user_id)
        .order_by(ChatHistory.timestamp.asc())
    )
    return result.scalars().all()





