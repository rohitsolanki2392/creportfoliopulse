from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.schema.invite_schema import InviteUserCreate, UserListResponse
from app.services.auth_service import list_all_users_service
from app.services.invite_service import invite_service
from app.models.models import Company, User
from app.utils.auth_utils import get_current_user

router = APIRouter()




@router.post("/admin")
async def invite_user(invite: InviteUserCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await invite_service(invite.email, "user", current_user, db)

@router.get("/list", response_model=List[UserListResponse])
async def list_all_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await list_all_users_service(current_user, db)


@router.get("/admin/invited-users")
def list_invited_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
   
    company = db.query(Company).filter(Company.owner_id == current_user.id).first()
    if not company:
        raise HTTPException(status_code=403, detail="You are not an admin")

   
    users = db.query(User).filter(
        User.company_id == company.id,
        User.id != current_user.id
    ).all()

    user_list = []
    for user in users:
        user_list.append({
            "email": user.email,
            "status": "Verified" if user.is_verified else "Not Verified",
            "display": f"{user.name} ({user.role.capitalize()})",
            "name": user.name,
            "created": user.created_at,
            "actions": ["edit", "delete"]
        })

    return user_list
