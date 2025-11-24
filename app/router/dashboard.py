from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.dashboard import get_stats_data
from app.database.db import get_db
from app.models.models import User
from app.services.dashboard_service import (
    get_activity_summary_service,
    get_ai_insights_service,
    get_analytics_service,
    get_rag_metrics_service,
    get_recent_questions_ai_service,
    get_usage_trends_service,
)
from app.utils.auth_utils import get_current_user

router = APIRouter()


def check_admin_permission(current_user: User):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from datetime import datetime, timedelta
    last_24h = datetime.utcnow() - timedelta(days=1)

    stats = await get_stats_data(db, current_user.company_id, last_24h)
    return stats


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(7, description="Filter by last X days (7, 30, 90)"),
):
    check_admin_permission(current_user)
    if days not in [7, 30, 90]:
        raise HTTPException(status_code=400, detail="Days must be 7, 30, or 90")
    return await get_analytics_service(db, current_user.company_id, days)


@router.get("/ai_insights")
async def get_ai_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_admin_permission(current_user)
    return await get_ai_insights_service(db, current_user.company_id)


@router.get("/usage_trends")
async def get_usage_trends(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 7,
):
    check_admin_permission(current_user)
    if days not in [7, 30, 90]:
        days = 7
    return await get_usage_trends_service(db, current_user.company_id, days)


@router.get("/recent_questions")
async def get_recent_questions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_admin_permission(current_user)
    return await get_recent_questions_ai_service(db, current_user.company_id)


@router.get("/activity_summary")
async def get_activity_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 7,
):
    check_admin_permission(current_user)
    if days not in [7, 30, 90]:
        raise HTTPException(status_code=400, detail="Days must be 7, 30, or 90")
    return await get_activity_summary_service(db, current_user.company_id, days)


@router.get("/system_tracing")
async def get_rag_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_admin_permission(current_user)
    return await get_rag_metrics_service(db, current_user.company_id)
