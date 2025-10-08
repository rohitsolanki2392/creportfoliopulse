from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.schema.feedback_schema import FeedbackCreate, FeedbackResponse
from app.services.feedback_service import (
    submit_feedback_service,
    view_user_feedback_service,
    view_company_feedback_service
)
from app.utils.auth_utils import get_current_user

router = APIRouter()

@router.post("/submit", response_model=FeedbackResponse)
def submit_feedback(
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return submit_feedback_service(db, current_user, feedback_data)


@router.get("/my-feedback", response_model=list[FeedbackResponse])
def view_my_feedback(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return view_user_feedback_service(db, current_user)


@router.get("/company-feedback", response_model=list[FeedbackResponse])
def view_company_feedback(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return view_company_feedback_service(db, current_user)
