


from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.models import ChatHistory, ChatSession, StandaloneFile

def save_standalone_file(
    db: Session,
    file_id: str,
    file_name: str,
    user_id: int,
    category: str,
    gcs_path: str,
    file_size: str,
    company_id: int,
    building_id: Optional[int] = None
):
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
    db.commit()
    db.refresh(new_file)
    return new_file

def list_user_files(db: Session, user_id: int, is_admin: bool):
    query = db.query(StandaloneFile)
    if not is_admin:
        query = query.filter_by(user_id=user_id)
    return query.all()

def get_standalone_file(db: Session, file_id: str):
    return db.query(StandaloneFile).filter_by(file_id=file_id).first()

def delete_standalone_file(db: Session, file_id: str):
    db_file = get_standalone_file(db, file_id)
    if db_file:
        db.delete(db_file)
        db.commit()
    return db_file



def get_or_create_chat_session(
    db: Session,
    session_id: Optional[str],
    user_id: int,
    category: Optional[str] = None,
    company_id: Optional[int] = None,
    title: Optional[str] = None,
    building_id: Optional[int] = None
):
    session = db.query(ChatSession).filter_by(id=session_id, user_id=user_id).first() if session_id else None
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
        db.commit()
        db.refresh(session)
    return session

def list_user_chat_sessions(db: Session, user_id: int):
    return db.query(ChatSession).filter_by(user_id=user_id).order_by(ChatSession.created_at.desc()).all()

def delete_user_chat_session(db: Session, session_id: str, user_id: int):
    session = db.query(ChatSession).filter_by(id=session_id, user_id=user_id).first()
    if session:
        db.delete(session)
        db.commit()
    return session


def save_chat_history(
    db: Session,
    session_id: str,
    user_id: int,
    question: str,
    answer: str,
    file_id: Optional[str] = None,
    response_json: Optional[dict] = None,
    company_id: Optional[int] = None
):
    chat_history = ChatHistory(
        chat_session_id=session_id,
        user_id=user_id,
        file_id=file_id,
        question=question,
        answer=answer,
        response_json=response_json,
        company_id=company_id,
        timestamp=datetime.utcnow()
    )
    db.add(chat_history)
    db.commit()
    db.refresh(chat_history)
    return chat_history

def get_user_chat_history(db: Session, session_id: str, user_id: int):
    return db.query(ChatHistory).filter_by(
        chat_session_id=session_id,
        user_id=user_id
    ).order_by(ChatHistory.timestamp.asc()).all()
