import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
import json
import re

from app.crud.dashborad import (
    get_activity_summary_data,
    get_analytics_data,
    get_rag_metrics_data,
    get_recent_questions_data,
    get_stats_data,
    get_usage_trends_data
)
from app.utils.llm_client import llm
from app.services.prompts import (
    get_ai_insights_prompt,
    get_recent_questions_prompt,
    get_usage_trends_prompt
)




async def get_stats_service(db: AsyncSession, company_id: int):
    last_24h = datetime.utcnow() - timedelta(hours=24)
    return await get_stats_data(db, company_id, last_24h)


async def get_analytics_service(db: AsyncSession, company_id: int, days: int):
    start_date = datetime.utcnow() - timedelta(days=days)
    return await get_analytics_data(db, company_id, start_date)


async def get_activity_summary_service(db: AsyncSession, company_id: int, days: int):
    start_date = datetime.utcnow().date() - timedelta(days=days - 1)
    summary, result = await get_activity_summary_data(db, company_id, start_date, days)
    return JSONResponse(content={
        "daily_activity_summary": summary,
        "session_activity_trend": result
    })


async def get_rag_metrics_service(db: AsyncSession, company_id: int):
    return await get_rag_metrics_data(db, company_id)


async def get_recent_questions_service(db: AsyncSession, company_id: int):
    return await get_recent_questions_data(db, company_id)




async def get_ai_insights_service(db: AsyncSession, company_id: int):
    analytics_data = await get_analytics_data(db, company_id, datetime.utcnow() - timedelta(days=7))
    prompt = await get_ai_insights_prompt(analytics_data)

    response = None
    try:
        response = llm.invoke(prompt)
        try:
            insights = json.loads(response.content)
        except json.JSONDecodeError:
            insights = {"insight": response.content}
    except Exception as e:

        insights = {"insight": getattr(response, "content", "No response") if response else "No response"}
    return insights


async def get_usage_trends_service(db: AsyncSession, company_id: int, days: int):
    start_date = datetime.utcnow().date() - timedelta(days=days - 1)
    daily_login_activity = await get_usage_trends_data(db, company_id, start_date, days)
    analytics_data = await get_analytics_service(db, company_id, days)
    activity_categories = {
        "chat_sessions": analytics_data["chat_sessions"],
        "active_users": analytics_data["active_users"],
        "total_logins": analytics_data["total_logins"],
        "platform_users": analytics_data["platform_users"]
    }
    prompt = await get_usage_trends_prompt(daily_login_activity, activity_categories)

    try:
        response = await asyncio.to_thread(llm.invoke, prompt)
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


async def get_recent_questions_ai_service(db: AsyncSession, company_id: int):
    question_texts = await get_recent_questions_data(db, company_id)
    prompt =await get_recent_questions_prompt(question_texts)

    try:
        response = await asyncio.to_thread(llm.invoke, prompt)
        response_text = getattr(response, "content", "").strip()
        response_text = re.sub(r"^```json|```$", "", response_text, flags=re.MULTILINE).strip()
        summary = json.loads(response_text)
    except Exception as e:
        summary = {"summary": "AI parsing failed", "questions": question_texts}

    return JSONResponse(content={"recent_questions": summary})
