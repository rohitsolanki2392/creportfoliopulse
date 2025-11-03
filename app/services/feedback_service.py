from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.feedback_crud import create_feedback, get_company_feedback, get_user_feedback
from app.schema.feedback_schema import FeedbackCreate, FeedbackResponse


async def submit_feedback_service(db: AsyncSession, current_user, feedback_data: FeedbackCreate):
    """
    Async service for user feedback submission.
    Automatically links feedback with the user's company.
    """
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User is not linked to any company")

    feedback = await create_feedback(
        db=db,
        user_id=current_user.id,
        company_id=current_user.company_id,
        feedback_data=feedback_data
    )

    return FeedbackResponse(
        id=feedback.id,
        feedback=feedback.feedback,
        rating=feedback.rating,
        created_at=feedback.created_at,
        user_email=current_user.email
    )


async def view_user_feedback_service(db: AsyncSession, current_user):
    """
    Async service for fetching the logged-in user's feedback history.
    """
    feedbacks = await get_user_feedback(db=db, user_id=current_user.id)

    return [
        FeedbackResponse(
            id=f.id,
            feedback=f.feedback,
            rating=f.rating,
            created_at=f.created_at,
            user_email=current_user.email
        )
        for f in feedbacks
    ]


async def view_company_feedback_service(db: AsyncSession, current_user):
    """
    Async service for admins to view feedback for their own company.
    """
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )

    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="Admin not associated with a company")

    feedbacks = await get_company_feedback(db=db, company_id=current_user.company_id)

    return [
        FeedbackResponse(
            id=f.UserFeedback.id,
            feedback=f.UserFeedback.feedback,
            rating=f.UserFeedback.rating,
            created_at=f.UserFeedback.created_at,
            user_email=f.user_email
        )
        for f in feedbacks
    ]
