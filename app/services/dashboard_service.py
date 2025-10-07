from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse

from app.crud.dashborad import get_activity_summary_data, get_analytics_data, get_rag_metrics_data, get_recent_questions_data, get_stats_data, get_usage_trends_data
import json
import re

from dotenv import load_dotenv
from app.utils.llm_client import llm
from app.services.prompts import get_ai_insights_prompt, get_recent_questions_prompt, get_usage_trends_prompt


load_dotenv()


def get_stats_service(db: Session, company_id: int):
    last_24h = datetime.utcnow() - timedelta(hours=24)
    return get_stats_data(db, company_id, last_24h)

def get_analytics_service(db: Session, company_id: int, days: int):
    start_date = datetime.utcnow() - timedelta(days=days)
    return get_analytics_data(db, company_id, start_date)

def get_activity_summary_service(db: Session, company_id: int, days: int):
    start_date = datetime.utcnow().date() - timedelta(days=days - 1)
    summary, result = get_activity_summary_data(db, company_id, start_date, days)
    return JSONResponse(content={
        "daily_activity_summary": summary,
        "session_activity_trend": result
    })

async def get_rag_metrics_service(db: Session, company_id: int):
    return await get_rag_metrics_data(db, company_id)

def get_recent_questions_service(db: Session, company_id: int):
    return get_recent_questions_data(db, company_id)




def get_ai_insights_service(db, company_id: int):
    analytics_data = get_analytics_data(db, company_id, datetime.utcnow() - timedelta(days=7))
    prompt = get_ai_insights_prompt(analytics_data)
    response = None
    try:
        response = llm.invoke(prompt)
        insights = json.loads(response.content)
    except Exception as e:
        print(f"AI Insights error: {e}")
        insights = {"insight": getattr(response, "content", "No response") if response else "No response"}
    return insights


def get_usage_trends_service(db, company_id: int, days: int):
    start_date = datetime.utcnow().date() - timedelta(days=days - 1)
    daily_login_activity = get_usage_trends_data(db, company_id, start_date, days)
    analytics_data = get_analytics_data(db, company_id, datetime.utcnow() - timedelta(days=days))
    activity_categories = {
        "chat_sessions": analytics_data["chat_sessions"],
        "active_users": analytics_data["active_users"],
        "total_logins": analytics_data["total_logins"],
        "platform_users": analytics_data["platform_users"]
    }
    prompt = get_usage_trends_prompt(daily_login_activity, activity_categories)
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

def get_recent_questions_ai_service(db, company_id: int):
    question_texts = get_recent_questions_data(db, company_id)
    prompt = get_recent_questions_prompt(question_texts)
    try:
        response = llm.invoke(prompt)
        response_text = getattr(response, "content", "").strip()
        response_text = re.sub(r"^```json|```$", "", response_text, flags=re.MULTILINE).strip()
        summary = json.loads(response_text)
    except:
        summary = {"summary": "AI parsing failed", "questions": question_texts}
    return JSONResponse(content={"recent_questions": summary})