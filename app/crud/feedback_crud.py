from sqlalchemy.orm import Session
from app.models.models import UserFeedback, User
from app.schema.feedback_schema import FeedbackCreate



def create_feedback(db: Session, user_id: int, company_id: int, feedback_data: FeedbackCreate):
    feedback = UserFeedback(
        user_id=user_id,
        company_id=company_id,
        feedback=feedback_data.feedback,
        rating=feedback_data.rating
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_user_feedback(db: Session, user_id: int):
    return (
        db.query(UserFeedback)
        .filter(UserFeedback.user_id == user_id)
        .order_by(UserFeedback.created_at.desc())
        .all()
    )


def get_company_feedback(db: Session, company_id: int):
    return (
        db.query(UserFeedback, User.email.label("user_email"))
        .join(User, User.id == UserFeedback.user_id)
        .filter(UserFeedback.company_id == company_id)
        .order_by(UserFeedback.created_at.desc())
        .all()
    )
