from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.models import UserFeedback, User
from app.schema.feedback_schema import FeedbackCreate


async def create_feedback(db: AsyncSession, user_id: int, company_id: int, feedback_data: FeedbackCreate) -> UserFeedback:
    feedback = UserFeedback(
        user_id=user_id,
        company_id=company_id,
        feedback=feedback_data.feedback,
        rating=feedback_data.rating
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


async def get_user_feedback(db: AsyncSession, user_id: int) -> List[UserFeedback]:
    result = await db.execute(
        select(UserFeedback)
        .where(UserFeedback.user_id == user_id)
        .order_by(UserFeedback.created_at.desc())
    )
    return result.scalars().all()


async def get_company_feedback(db: AsyncSession, company_id: int) -> List[UserFeedback]:
    result = await db.execute(
        select(UserFeedback, User.email.label("user_email"))
        .join(User, User.id == UserFeedback.user_id)
        .where(UserFeedback.company_id == company_id)
        .order_by(UserFeedback.created_at.desc())
    )
    return result.all() 
