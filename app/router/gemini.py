from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.db import get_db
from app.models.models import User
from app.schema.user_chat import AskSimpleQuestionRequest
from app.utils.gemini_service import handle_gemini_chat
from app.utils.auth_utils import get_current_user

router = APIRouter()

@router.post("/chat")
async def gemini_chat(
    request: AskSimpleQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):  

    if not current_user.gemini_chat_enabled:
        raise HTTPException(
            status_code=403,
            detail="Gemini chat feature is disabled for your account."
        )
    try:
        return await handle_gemini_chat(request, current_user, db)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.patch("/gemini-toggle")
async def toggle_gemini_chat(
    email: str,
    enable: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
   
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can toggle Gemini chat")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.gemini_chat_enabled = enable
    await db.commit()
    await db.refresh(user)

    return {"message": f"Gemini chat {'enabled' if enable else 'disabled'} for {user.email}"}
