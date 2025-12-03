from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database.db import get_db
from app.schema.invite_schema import InviteUserCreate, UserListResponse
from app.services.auth_service import list_all_users_service
from app.services.invite_service import invite_service
from app.models.models import Company, User
from app.utils.auth_utils import get_current_user

router = APIRouter(prefix="/invite_user", tags=["Invite User"])


@router.post("/admin")
async def invite_user(
    invite: InviteUserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await invite_service(invite.email, "user", current_user, db)


@router.get("/list", response_model=List[UserListResponse])
async def list_all_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await list_all_users_service(current_user, db)


@router.get("/admin/invited-users", response_model=List[dict])
async def list_invited_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    stmt = select(Company).where(Company.owner_id == current_user.id)
    result = await db.execute(stmt)
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=403, detail="You are not an admin")

    stmt = select(User).where(
        User.company_id == company.id,
        User.id != current_user.id
    )
    result = await db.execute(stmt)
    users = result.scalars().all()


    user_list = []
    for user in users:
        user_list.append({
            "email": user.email,
            "status": "Verified" if user.is_verified else "Not Verified",
            "display": f"{user.name} ({user.role.capitalize()})",
            "name": user.name,
            "created": user.created_at,
            "actions": ["edit", "delete"],
            "gemini_status": user.gemini_chat_enabled,
            "forum_status": user.forum_enabled

            
        })

    return user_list
