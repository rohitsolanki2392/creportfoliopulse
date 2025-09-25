from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import ChatHistory, User, UserLogin
from app.utils.get_current_user import get_current_user
from datetime import datetime, timedelta
import re
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import union_all, select, func
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from app.database.db import get_db
from app.models.models import (
    OTP, Building,StandaloneFile,
    User, ChatSession, ChatHistory
)
from app.utils.auth_utils import get_current_user

load_dotenv()
router = APIRouter()

google_api_key = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=google_api_key,
)


# ---------------------- 📊 STATS ----------------------
@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access statistics"
        )

    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    company_id = current_user.company_id

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


# ---------------------- 📈 ANALYTICS ----------------------
@router.get("/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(7, description="Filter by last X days (7, 30, 90)")
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if days not in [7, 30, 90]:
        raise HTTPException(status_code=400, detail="Days must be 7, 30, or 90")

    today = datetime.utcnow()
    start_date = today - timedelta(days=days)
    company_id = current_user.company_id

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


# ---------------------- 🤖 AI INSIGHTS ----------------------
@router.get("/ai_insights")
def get_ai_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    analytics_data = get_analytics(db, current_user, days=7)

    prompt = f"""
    You are an expert data analyst. Generate concise AI-driven insights based on the following analytics data:
    - Chat Sessions: {analytics_data['chat_sessions']}
    - Active Users: {analytics_data['active_users']}
    - Total Logins: {analytics_data['total_logins']}
    - Platform Users: {analytics_data['platform_users']}
    Provide insights as well structured text.
    """

    try:
        response = llm.invoke(prompt)
        insights = json.loads(response.content)
    except:
        insights = {"insight": getattr(response, "content", "No response")}

    return insights


# ---------------------- 📊 USAGE TRENDS ----------------------
@router.get("/usage_trends")
def get_usage_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 7
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if days not in [7, 30, 90]:
        days = 7

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days - 1)
    company_id = current_user.company_id

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
    analytics_data = get_analytics(db, current_user, days)

    daily_login_activity = []
    for i in range(days):
        day = (start_date + timedelta(days=i)).isoformat()
        count = next((c for d, c in login_counts if d.isoformat() == day), 0)
        daily_login_activity.append({"date": day, "logins": count})

    activity_categories = {
        "chat_sessions": analytics_data["chat_sessions"],
        "active_users": analytics_data["active_users"],
        "total_logins": analytics_data["total_logins"],
        "platform_users": analytics_data["platform_users"]
    }

    prompt = f"""
    You are an expert data analyst. Analyze the following usage data:
    - Daily Login Activity: {daily_login_activity}
    - Activity Categories: {activity_categories}
    Provide ONLY in text format with keys:
    {{
      "trend_summary": "string",
      "category_analysis": "string"
    }}
    """

    try:
        response = llm.invoke(prompt)
        response_text = getattr(response, "content", "").strip()
        if response_text.startswith("```"):
            response_text = response_text.strip("`")
            if response_text.lower().startswith("json"):
                response_text = response_text[4:].strip()
        ai_insights = json.loads(response_text)
    except Exception as e:
        ai_insights = {"trend_summary": str(e), "category_analysis": ""}

    return JSONResponse(content={
        "daily_login_activity": daily_login_activity,
        "activity_categories": activity_categories,
        "ai_insights": ai_insights
    })


# ---------------------- ❓ RECENT QUESTIONS ----------------------
@router.get("/recent_questions")
def get_recent_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    company_id = current_user.company_id

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

    question_texts = [row[0] for row in recent_questions]

    prompt = f"""
    Summarize the following recent questions from users:
    {', '.join(question_texts) if question_texts else 'No recent questions available.'}
    Provide the answer ONLY in Plain text format:
    {{
        "summary": "short summary text",
        "questions": ["q1", "q2", "q3"]
    }}
    """

    try:
        response = llm.invoke(prompt)
        response_text = getattr(response, "content", "").strip()
        response_text = re.sub(r"^```json|```$", "", response_text, flags=re.MULTILINE).strip()
        summary = json.loads(response_text)
    except:
        summary = {"summary": "AI parsing failed", "questions": question_texts}

    return JSONResponse(content={"recent_questions": summary})


# ---------------------- 📉 ACTIVITY SUMMARY ----------------------
@router.get("/activity_summary")
def get_activity_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 7
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if days not in [7, 30, 90]:
        raise HTTPException(status_code=400, detail="Days must be 7, 30, or 90")

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days - 1)
    company_id = current_user.company_id

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
    return JSONResponse(content={
        "daily_activity_summary": summary,
        "session_activity_trend": result
    })
@router.get("/system_tracing")
def get_rag_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  
):
    company_id = current_user.company_id  
    query = (
        db.query(ChatHistory)
        .join(User, ChatHistory.user_id == User.id)
        .filter(User.company_id == company_id)
    )

    # Total queries
    total_queries = query.count() or 0

    # Avg response time (in ms)
    avg_response_time = query.with_entities(func.avg(ChatHistory.response_time)).scalar() or 0.0

    # Avg confidence
    avg_confidence = query.with_entities(func.avg(ChatHistory.confidence)).scalar() or 0.0

    # Positive feedback %
    positive_feedback_count = query.filter(ChatHistory.feedback == "positive").count() or 0
    positive_feedback_percent = (positive_feedback_count / total_queries * 100) if total_queries > 0 else 0

    # Dashboard Metrics
    chat_sessions = query.with_entities(func.count(func.distinct(ChatHistory.chat_session_id))).scalar() or 0
    active_users = query.with_entities(func.count(func.distinct(ChatHistory.user_id))).scalar() or 0

    # ✅ Company-specific logins & users
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
