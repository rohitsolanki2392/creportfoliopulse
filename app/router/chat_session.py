
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import  Optional
from app.database.db import get_db
from app.services.session_service import delete_session_service, get_session_history_service, list_chat_sessions_service
from app.utils.auth_utils import get_current_user
import secrets
router = APIRouter()



def generate_session_id(num_bytes: int = 32) -> str:
    """Return a URL-safe base64-like session ID (~43 chars for 32 bytes)."""
    return secrets.token_urlsafe(num_bytes)

@router.post("/session_id_create")
async def create_session_id(
):
    session_id = generate_session_id()
    return {"session_id": session_id}


@router.get("/sessions/")
async def list_chat_sessions(
    category: Optional[str] = Query(None, description="Filter chat sessions by category"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all chat sessions for the current user, optionally filtered by category."""
    return await list_chat_sessions_service(current_user, db, category)


@router.get("/history/")
async def get_session_history(
    session_id: str = Query(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_session_history_service(session_id, current_user, db)

@router.delete("/delete/")
async def delete_session(
    session_id: str = Query(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await delete_session_service(session_id, current_user, db)

