from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.models import OTP, Building, StandaloneFile, User, ChatSession, ChatHistory, UserLogin, UserFeedback
from app.services.prompts import build_feedback_classification_prompt
from app.utils.llm_client import invoke_llm_async
from sqlalchemy import func


async def get_stats_data(db: AsyncSession, company_id: int, last_24h: datetime):
    total_standalone = await db.execute(
        select(func.count()).select_from(StandaloneFile).where(StandaloneFile.company_id == company_id)
    )
    total_standalone = total_standalone.scalar() or 0

    total_building_files = await db.execute(
        select(func.count())
        .select_from(StandaloneFile)
        .join(Building, StandaloneFile.building_id == Building.id)
        .where(Building.company_id == company_id)
    )
    total_building_files = total_building_files.scalar() or 0
    total_documents = total_standalone + total_building_files

    total_chat_history = await db.execute(
        select(func.count()).select_from(ChatHistory).where(ChatHistory.company_id == company_id)
    )
    total_chat_history = total_chat_history.scalar() or 0

    total_buildings = await db.execute(
        select(func.count()).select_from(Building).where(Building.company_id == company_id)
    )
    total_buildings = total_buildings.scalar() or 0

    recent_uploads = await db.execute(
        select(func.count()).select_from(StandaloneFile)
        .where(StandaloneFile.company_id == company_id, StandaloneFile.uploaded_at >= last_24h)
    )
    recent_uploads = recent_uploads.scalar() or 0

    return {
        "total_documents": total_documents,
        "buildings": total_buildings,
        "recent_uploads": recent_uploads,
        "AI_queries": total_chat_history,
    }


async def get_analytics_data(db: AsyncSession, company_id: int, start_date: datetime):
    platform_users_res = await db.execute(select(func.count()).select_from(User).where(User.company_id == company_id))
    platform_users = platform_users_res.scalar() or 0

    active_users_res = await db.execute(
        select(func.count()).select_from(User)
        .where(User.company_id == company_id, User.is_verified == True)
    )
    active_users = active_users_res.scalar() or 0

    chat_sessions_res = await db.execute(
        select(func.count()).select_from(ChatSession)
        .where(ChatSession.company_id == company_id, ChatSession.created_at >= start_date)
    )
    chat_sessions = chat_sessions_res.scalar() or 0

    total_logins_res = await db.execute(
        select(func.count()).select_from(User).where(User.company_id == company_id)
    )
    total_logins = total_logins_res.scalar() or 0

    return {
        "chat_sessions": chat_sessions,
        "active_users": active_users,
        "total_logins": total_logins,
        "platform_users": platform_users,
    }


async def get_usage_trends_data(db: AsyncSession, company_id: int, start_date: datetime, days: int):
    login_counts_res = await db.execute(
        select(func.date(OTP.created_at).label("date"), func.count().label("count"))
        .where(
            OTP.created_at >= start_date,
            OTP.email.in_(
                select(User.email).where(User.company_id == company_id)
            )
        )
        .group_by(func.date(OTP.created_at))
        .order_by(func.date(OTP.created_at))
    )
    login_counts = login_counts_res.all()

    daily_login_activity = []
    for i in range(days):
        day = (start_date + timedelta(days=i)).isoformat()
        count = next((c for d, c in login_counts if d.isoformat() == day), 0)
        daily_login_activity.append({"date": day, "logins": count})

    return daily_login_activity


async def get_recent_questions_data(db: AsyncSession, company_id: int):
    result = await db.execute(
        select(ChatHistory.question, ChatHistory.timestamp)
        .where(ChatHistory.company_id == company_id)
        .order_by(ChatHistory.timestamp.desc())
        .limit(10)
    )
    recent_questions = result.all()
    return [row[0] for row in recent_questions]


async def get_activity_summary_data(db: AsyncSession, company_id: int, start_date: datetime, days: int):
    chat_sessions_res = await db.execute(
        select(func.date(ChatSession.created_at).label("date"), func.count().label("count"))
        .where(ChatSession.company_id == company_id, ChatSession.created_at >= start_date)
        .group_by(func.date(ChatSession.created_at))
        .order_by(func.date(ChatSession.created_at))
    )
    chat_sessions = chat_sessions_res.all()

    logins_res = await db.execute(
        select(func.date(OTP.created_at).label("date"), func.count().label("count"))
        .where(
            OTP.created_at >= start_date,
            OTP.email.in_(select(User.email).where(User.company_id == company_id))
        )
        .group_by(func.date(OTP.created_at))
    )
    logins = logins_res.all()

    active_users_res = await db.execute(
        select(func.date(ChatSession.created_at).label("date"), func.count(func.distinct(ChatSession.user_id)).label("count"))
        .where(ChatSession.company_id == company_id, ChatSession.created_at >= start_date)
        .group_by(func.date(ChatSession.created_at))
    )
    active_users = active_users_res.all()

    summary = [{"date": (start_date + timedelta(days=i)).isoformat(), "chat_sessions": 0, "logins": 0, "active_users": 0} for i in range(days)]

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

    result = [{"date": e["date"], "chat_sessions": e["chat_sessions"], "active_users": e["active_users"]} for e in summary]

    return summary, result




async def classify_feedback_with_llm(feedback_list: list[str]):
    if not feedback_list:
        return []

    prompt = await build_feedback_classification_prompt(feedback_list)

    result = await invoke_llm_async(prompt, expect_json=True, fallback={"feedback": ["neutral"] * len(feedback_list)})
    
    feedback_labels = result.get("feedback", [])
    if len(feedback_labels) != len(feedback_list):
        feedback_labels = ["neutral"] * len(feedback_list)
    
    return feedback_labels


async def get_rag_metrics_data(db: AsyncSession, company_id: int):
    query = select(ChatHistory).join(User, ChatHistory.user_id == User.id).where(User.company_id == company_id)
    query_result = await db.execute(query)
    chat_histories = query_result.scalars().all()

    total_queries = len(chat_histories)
    chat_sessions = len(set(ch.chat_session_id for ch in chat_histories))
    active_users = len(set(ch.user_id for ch in chat_histories))

    total_logins_res = await db.execute(
        select(func.count(UserLogin.id)).join(User, UserLogin.user_id == User.id).where(User.company_id == company_id)
    )
    total_logins = total_logins_res.scalar() or 0

    platform_users_res = await db.execute(select(func.count(User.id)).where(User.company_id == company_id))
    platform_users = platform_users_res.scalar() or 0

    feedback_entries_res = await db.execute(select(UserFeedback.feedback).where(UserFeedback.company_id == company_id, UserFeedback.feedback.isnot(None)))
    feedback_texts = [f[0] for f in feedback_entries_res.all() if f[0]]

    positive_feedback_count = 0
    if feedback_texts:
        classifications = await classify_feedback_with_llm(feedback_texts)
        positive_feedback_count = sum(1 for c in classifications if c.lower() == "positive")

    total_feedbacks = len(feedback_texts)
    positive_feedback_percent = (positive_feedback_count / total_feedbacks * 100) if total_feedbacks > 0 else 0

    avg_response_time_sec = sum(ch.response_time or 0 for ch in chat_histories) / len(chat_histories) if chat_histories else 0.0
    avg_confidence_fraction = sum(ch.confidence or 0 for ch in chat_histories) / len(chat_histories) if chat_histories else 0.0

    avg_response_time_ms = round(avg_response_time_sec * 1000, 2)
    avg_confidence_percent = round(avg_confidence_fraction * 100, 2)

    return {
        "dashboard_metrics": {
            "chat_sessions": chat_sessions,
            "active_users": active_users,
            "total_logins": total_logins,
            "platform_users": platform_users,
        },
        "avg_response_time_ms": avg_response_time_ms,
        "avg_confidence": avg_confidence_percent,
        "positive_feedback_percent": round(positive_feedback_percent, 2),
        "total_queries": total_queries,
        "total_feedbacks": total_feedbacks,
        "last_updated": datetime.utcnow().isoformat()
    }
