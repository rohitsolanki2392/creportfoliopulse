from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple
from app.models.models import UserFeedback, User
from app.schema.feedback_schema import FeedbackCreate


async def create_feedback(db: AsyncSession, user_id: int, company_id: int, feedback_data: FeedbackCreate) -> UserFeedback:
    feedback = UserFeedback(
        user_id=user_id,
        company_id=company_id,
        feedback=feedback_data.feedback,
        feedback_category=feedback_data.category,   
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback

from typing import Optional

async def get_user_feedback(db: AsyncSession, user_id: int, category: Optional[str] = None) -> List[UserFeedback]:
    query = select(UserFeedback).where(UserFeedback.user_id == user_id)

    if category:
        query = query.where(UserFeedback.feedback_category.ilike(category.strip()))

    query = query.order_by(UserFeedback.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_company_feedback(db: AsyncSession, company_id: int, category: Optional[str] = None):
    query = (
        select(UserFeedback, User.email, User.name)
        .join(User, User.id == UserFeedback.user_id)
        .where(UserFeedback.company_id == company_id)
    )

    if category:
        query = query.where(UserFeedback.feedback_category.ilike(category.strip()))

    query = query.order_by(UserFeedback.created_at.desc())

    result = await db.execute(query)
    return result.all()