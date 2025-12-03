from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.schema.feedback_schema import FeedbackCreate, FeedbackResponse
from app.services.feedback_service import (
    delete_user_feedback_service,
    submit_feedback_service,
    view_user_feedback_service,
    view_company_feedback_service,
)
from fastapi import HTTPException, status
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.post("/submit", response_model=FeedbackResponse)
async def submit_feedback(
    feedback_data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await submit_feedback_service(db, current_user, feedback_data)

from typing import Optional
from fastapi import Query

@router.get("/my-feedback", response_model=list[FeedbackResponse])
async def view_my_feedback(
    category: Optional[str] = Query(None, description="Filter by feedback category (e.g., bug, feature, ui)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await view_user_feedback_service(db, current_user, category)


@router.get("/company-feedback", response_model=list[FeedbackResponse])
async def view_company_feedback(
    category: Optional[str] = Query(None, description="Filter by feedback category"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await view_company_feedback_service(db, current_user, category)

@router.delete("/")
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):

    deleted = await delete_user_feedback_service(db, current_user, feedback_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found or you are not authorized to delete it."
        )
    return {"message": "Feedback deleted successfully."}