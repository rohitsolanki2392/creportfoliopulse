from sqlalchemy import func, union_all, select
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.models.models import OTP, Building, StandaloneFile, User, ChatSession, ChatHistory, UserLogin

def get_stats_data(db: Session, company_id: int, last_24h: datetime):
    total_standalone = db.query(StandaloneFile).filter(StandaloneFile.company_id == company_id).count()
    total_building_files = (
        db.query(StandaloneFile)
        .join(Building, StandaloneFile.building_id == Building.id)
        .filter(Building.company_id == company_id)
        .count()
    )
    total_documents = total_standalone + total_building_files
    total_chat_history = db.query(ChatHistory).filter(ChatHistory.company_id == company_id).count()
    total_buildings = db.query(Building).filter(Building.company_id == company_id).count()
    recent_uploads = (
        db.query(StandaloneFile)
        .filter(StandaloneFile.company_id == company_id, StandaloneFile.uploaded_at >= last_24h)
        .count()
    )
    return {
        "total_documents": total_documents,
        "buildings": total_buildings,
        "recent_uploads": recent_uploads,
        "AI_queries": total_chat_history,
    }

def get_analytics_data(db: Session, company_id: int, start_date: datetime):
    platform_users = db.query(User).filter(User.company_id == company_id).count()
    active_users = db.query(User).filter(User.company_id == company_id, User.is_verified == True).count()
    chat_sessions = (
        db.query(ChatSession)
        .filter(ChatSession.company_id == company_id, ChatSession.created_at >= start_date)
        .count()
    )
    total_logins = db.query(User).filter(User.company_id == company_id).count()
    return {
        "chat_sessions": chat_sessions,
        "active_users": active_users,
        "total_logins": total_logins,
        "platform_users": platform_users,
    }

def get_usage_trends_data(db: Session, company_id: int, start_date: datetime, days: int):
    login_counts = (
        db.query(func.date(OTP.created_at).label("date"), func.count().label("count"))
        .filter(
            OTP.created_at >= start_date,
            OTP.email.in_(db.query(User.email).filter(User.company_id == company_id))
        )
        .group_by(func.date(OTP.created_at))
        .order_by(func.date(OTP.created_at))
        .all()
    )
    daily_login_activity = []
    for i in range(days):
        day = (start_date + timedelta(days=i)).isoformat()
        count = next((c for d, c in login_counts if d.isoformat() == day), 0)
        daily_login_activity.append({"date": day, "logins": count})
    return daily_login_activity

def get_recent_questions_data(db: Session, company_id: int):
    chat_history_query = (
        select(ChatHistory.question, ChatHistory.timestamp)
        .where(ChatHistory.company_id == company_id)
    )
    union_query = union_all(chat_history_query).alias("questions")
    recent_questions = (
        db.query(union_query.c.question, union_query.c.timestamp)
        .order_by(union_query.c.timestamp.desc())
        .limit(10)
        .all()
    )
    return [row[0] for row in recent_questions]

def get_activity_summary_data(db: Session, company_id: int, start_date: datetime, days: int):
    chat_sessions = (
        db.query(func.date(ChatSession.created_at).label("date"), func.count().label("count"))
        .filter(ChatSession.company_id == company_id, ChatSession.created_at >= start_date)
        .group_by(func.date(ChatSession.created_at))
        .order_by(func.date(ChatSession.created_at))
        .all()
    )
    logins = (
        db.query(func.date(OTP.created_at).label("date"), func.count().label("count"))
        .filter(
            OTP.created_at >= start_date,
            OTP.email.in_(db.query(User.email).filter(User.company_id == company_id))
        )
        .group_by(func.date(OTP.created_at))
        .all()
    )
    active_users = (
        db.query(func.date(ChatSession.created_at).label("date"),
                 func.count(func.distinct(ChatSession.user_id)).label("count"))
        .filter(ChatSession.company_id == company_id, ChatSession.created_at >= start_date)
        .group_by(func.date(ChatSession.created_at))
        .all()
    )
    summary = []
    for i in range(days):
        day = (start_date + timedelta(days=i)).isoformat()
        summary.append({"date": day, "chat_sessions": 0, "logins": 0, "active_users": 0})

    for date, count in chat_sessions:
        for entry in summary:
            if entry["date"] == date.isoformat():
                entry["chat_sessions"] = count

    for date, count in logins:
        for entry in summary:
            if entry["date"] == date.isoformat():
                entry["logins"] = count

    for date, count in active_users:
        for entry in summary:
            if entry["date"] == date.isoformat():
                entry["active_users"] = count

    result = [
        {"date": entry["date"], "chat_sessions": entry["chat_sessions"], "active_users": entry["active_users"]}
        for entry in summary
    ]
    return summary, result

def get_rag_metrics_data(db: Session, company_id: int):
    query = (
        db.query(ChatHistory)
        .join(User, ChatHistory.user_id == User.id)
        .filter(User.company_id == company_id)
    )
    total_queries = query.count() or 0
    avg_response_time = query.with_entities(func.avg(ChatHistory.response_time)).scalar() or 0.0
    avg_confidence = query.with_entities(func.avg(ChatHistory.confidence)).scalar() or 0.0
    positive_feedback_count = query.filter(ChatHistory.feedback == "positive").count() or 0
    positive_feedback_percent = (positive_feedback_count / total_queries * 100) if total_queries > 0 else 0
    chat_sessions = query.with_entities(func.count(func.distinct(ChatHistory.chat_session_id))).scalar() or 0
    active_users = query.with_entities(func.count(func.distinct(ChatHistory.user_id))).scalar() or 0
    total_logins = (
        db.query(func.count(UserLogin.id))
        .join(User, UserLogin.user_id == User.id)
        .filter(User.company_id == company_id)
        .scalar()
        or 0
    )
    platform_users = db.query(func.count(User.id)).filter(User.company_id == company_id).scalar() or 0
    return {
        "dashboard_metrics": {
            "chat_sessions": chat_sessions,
            "active_users": active_users,
            "total_logins": total_logins,
            "platform_users": platform_users,
        },
        "avg_response_time_ms": round(avg_response_time, 2),
        "avg_confidence": round(avg_confidence, 2),
        "positive_feedback_percent": round(positive_feedback_percent, 2),
        "total_queries": total_queries
    }