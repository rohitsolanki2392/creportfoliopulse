from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from sqlalchemy.future import select
from app.crud.feedback_crud import create_feedback, get_company_feedback, get_user_feedback
from app.models.models import UserFeedback
from app.schema.feedback_schema import FeedbackCreate, FeedbackResponse
from fastapi import HTTPException
from app.utils.email import send_email
import logging
logger = logging.getLogger(__name__)
# async def submit_feedback_service(db: AsyncSession, current_user, feedback_data: FeedbackCreate):
#     if not current_user.company_id:
#         raise HTTPException(status_code=400, detail="User is not linked to any company")

#     feedback = await create_feedback(
#         db=db,
#         user_id=current_user.id,
#         company_id=current_user.company_id,
#         feedback_data=feedback_data
#     )

#     return FeedbackResponse(
#         id=feedback.id,
#         feedback=feedback.feedback,
#         rating=feedback.rating,
#         created_at=feedback.created_at,
#         user_email=current_user.email
#     )



async def submit_feedback_service(db: AsyncSession, current_user, feedback_data: FeedbackCreate):
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User is not linked to any company")

    # Create feedback
    feedback = await create_feedback(
        db=db,
        user_id=current_user.id,
        company_id=current_user.company_id,
        feedback_data=feedback_data
    )

    # Send thank-you email
    try:
        send_email(
            to_email=current_user.email,
            subject="Thank You for Your Feedback",
            body="Thank you for sharing your information with Portfolio Pulse!"
        )
    except Exception as e:
        logger.info(f"Failed to send email: {str(e)}")

    # Return response
    return FeedbackResponse(
        id=feedback.id,
        feedback=feedback.feedback,
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

    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="Admin not associated with a company")

    feedbacks = await get_company_feedback(db=db, company_id=current_user.company_id)

    # Filter out current user's feedback
    other_users_feedback = [
        f for f in feedbacks 
        if f.UserFeedback.user_id != current_user.id
    ]

    return [
        FeedbackResponse(
            id=f.UserFeedback.id,
            feedback=f.UserFeedback.feedback,
            rating=f.UserFeedback.rating,
            created_at=f.UserFeedback.created_at,
            user_email=f.user_email
        )
        for f in other_users_feedback
    ]




async def delete_user_feedback_service(db: AsyncSession, current_user, feedback_id: int) -> bool:


    result = await db.execute(
        select(UserFeedback).where(UserFeedback.id == feedback_id)
    )
    feedback = result.scalar_one_or_none()

    if feedback is None or feedback.user_id != current_user.id:
        return False 

  
    await db.execute(delete(UserFeedback).where(UserFeedback.id == feedback_id))
    await db.commit()
    return True
