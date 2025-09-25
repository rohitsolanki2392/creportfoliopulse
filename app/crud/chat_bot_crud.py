# from typing import Optional
# from sqlalchemy.orm import Session
# from app.models.models import (
#     Building,
#     BuildingPermission, ChatSession,
#     ChatHistory
# )

# def get_building(db: Session, building_id: int):
#     return db.query(Building).filter_by(id=building_id).first()


# def get_building_permission(db: Session, user_id: int, building_id: int):
#     return db.query(BuildingPermission).filter_by(
#         user_id=user_id, building_id=building_id
#     ).first()



# def get_or_create_chatbot_session(db: Session, session_id: Optional[str], user_id: int, category: str,  company_id:int,building_id: Optional[int] = None):
#     if session_id:
#         try:
#             return db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).one()
#         except:
#             pass
#     session = ChatSession(user_id=user_id, category=category, building_id=building_id,company_id=company_id)
#     db.add(session)
#     db.commit()
#     db.refresh(session)
#     return session

# def save_chat_history(db: Session, session_id: str, user_id: int,
#                       file_id: Optional[str], question: str, answer: str, response_json: dict,company_id:int):
#     chat = ChatHistory(
#         chat_session_id=session_id,
#         user_id=user_id,
#         file_id=file_id,
#         question=question,
#         answer=answer,
#         response_json=response_json,
#         company_id= company_id
#     )
#     db.add(chat)
#     db.commit()
#     return chat

# def list_chat_sessions(db: Session, user_id: int):
#     return db.query(ChatSession).filter_by(user_id=user_id).order_by(ChatSession.created_at.desc()).all()

# def get_chat_history(db: Session, session_id: str, user_id: int):
#     return db.query(ChatHistory).filter_by(chat_session_id=session_id, user_id=user_id).order_by(ChatHistory.timestamp.asc()).all()

# def delete_chat_session(db: Session, session_id: str, user_id: int):
#     session = db.query(ChatSession).filter_by(id=session_id, user_id=user_id).first()
#     if session:
#         db.delete(session)
#         db.commit()
#     return session