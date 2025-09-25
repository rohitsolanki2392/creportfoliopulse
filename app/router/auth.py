

# app/routes/auth.py
from fastapi import APIRouter, Depends, BackgroundTasks,Request, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User
from app.schema.auth_schema import ForgotPassword, OTPVerify, ResetPassword, Token, UserLogin, UserProfile, UserRegister, InviteAdminRequest
from app.services.invite_service import invite_service
from app.utils.auth_utils import get_current_user
from app.services import auth_service

router = APIRouter()

@router.patch("/user/profile/update", response_model=UserProfile, tags=["Auth"])
async def update_user_profile(
    name: str = Form(None),
    number: str = Form(None),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    updated_user, photo_base64 = await auth_service.update_user_profile_service(
        db=db,
        current_user=current_user,
        name=name,
        number=number,
        photo=photo,
        request=request
    )
    return {
        **UserProfile.from_orm(updated_user).dict(),
        "photo_base64": photo_base64
    }

@router.get("/user/profile", tags=["Auth"])
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    return auth_service.get_user_profile_service(current_user)

@router.post("/register", status_code=status.HTTP_201_CREATED, tags=["Auth"])
async def register_user(user: UserRegister, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return await auth_service.register_user_service(user, db, background_tasks)

@router.post("/login", response_model=Token, tags=["Auth"])
async def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    return auth_service.login_user_service(login_data, db)

@router.post("/forgot_password", tags=["Auth"])
async def forgot_password(forgot_data: ForgotPassword, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return await auth_service.forgot_password_service(forgot_data, db, background_tasks)

@router.post("/reset_password", tags=["Auth"])
async def reset_password(reset_data: ResetPassword, db: Session = Depends(get_db)):
    return auth_service.reset_password_service(reset_data, db)

@router.post("/verify_otp", tags=["Auth"])
async def verify_otp(otp_data: OTPVerify, db: Session = Depends(get_db)):
    return auth_service.verify_otp_service(otp_data, db)

@router.delete("/user/",  tags=["Super user api"])
def delete_user(email: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return auth_service.delete_user_service(db, current_user, email)



@router.post("/invite-admin", tags=["Super user api"])
async def invite_admin(data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await invite_service(
        email=data["email"],
        role="admin",
        current_user=current_user,
        db=db,
        company_name=data["company_name"],
        admin_name=data["admin_name"]
    )