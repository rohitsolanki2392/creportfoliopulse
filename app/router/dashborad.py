
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User
from app.services.dashboard_service import get_activity_summary_service, get_ai_insights_service, get_analytics_service, get_rag_metrics_service, get_recent_questions_ai_service, get_stats_service, get_usage_trends_service
from app.utils.auth_utils import get_current_user

router = APIRouter()

def check_admin_permission(current_user: User):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_admin_permission(current_user)
    return get_stats_service(db, current_user.company_id)

@router.get("/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(7, description="Filter by last X days (7, 30, 90)")
):
    check_admin_permission(current_user)
    if days not in [7, 30, 90]:
        raise HTTPException(status_code=400, detail="Days must be 7, 30, or 90")
    return get_analytics_service(db, current_user.company_id, days)

@router.get("/ai_insights")
def get_ai_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_admin_permission(current_user)
    return get_ai_insights_service(db, current_user.company_id)

@router.get("/usage_trends")
def get_usage_trends(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 7
):
    check_admin_permission(current_user)
    if days not in [7, 30, 90]:
        days = 7
    return get_usage_trends_service(db, current_user.company_id, days)

@router.get("/recent_questions")
def get_recent_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    check_admin_permission(current_user)
    return get_recent_questions_ai_service(db, current_user.company_id)

@router.get("/activity_summary")
def get_activity_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = 7
):
    check_admin_permission(current_user)
    if days not in [7, 30, 90]:
        raise HTTPException(status_code=400, detail="Days must be 7, 30, or 90")
    return get_activity_summary_service(db, current_user.company_id, days)

@router.get("/system_tracing")
def get_rag_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_admin_permission(current_user)
    return get_rag_metrics_service(db, current_user.company_id)