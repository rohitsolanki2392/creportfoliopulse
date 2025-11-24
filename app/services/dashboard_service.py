import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.dashboard import (
    get_activity_summary_data,
    get_analytics_data,
    get_rag_metrics_data,
    get_recent_questions_data,
    get_stats_data,
    get_usage_trends_data,
)
from app.services.prompts import (
    get_ai_insights_prompt,
    get_recent_questions_prompt,
    get_usage_trends_prompt,
)


from app.utils.llm_client import invoke_llm_async 


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


async def get_ai_insights_service(db: AsyncSession, company_id: int) -> Dict[str, Any]:
    analytics_data = await get_analytics_data(db, company_id, datetime.utcnow() - timedelta(days=7))
    prompt = await get_ai_insights_prompt(analytics_data)

    insights = await invoke_llm_async(
        prompt=prompt,
        expect_json=True,
        fallback={"insight": "Unable to generate insights at this time."}
    )


    if isinstance(insights, dict) and "error" in insights:
        insights = {"insight": f"AI service temporarily unavailable: {insights.get('error')}"}

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

    ai_insights = await invoke_llm_async(
        prompt=prompt,
        expect_json=True,
        fallback={
            "trend_summary": "Trend analysis unavailable",
            "category_analysis": "Unable to analyze usage patterns at this time."
        }
    )

    return JSONResponse(content={
        "daily_login_activity": daily_login_activity,
        "activity_categories": activity_categories,
        "ai_insights": ai_insights
    })



async def get_recent_questions_ai_service(db: AsyncSession, company_id: int):
    question_texts = await get_recent_questions_data(db, company_id)
    prompt = await get_recent_questions_prompt(question_texts)

    summary = await invoke_llm_async(
        prompt=prompt,
        expect_json=True,
        fallback={
            "summary": "Unable to summarize recent questions",
            "questions": question_texts[:10] 
        }
    )

    return JSONResponse(content={"recent_questions": summary})