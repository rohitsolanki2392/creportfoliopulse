from fastapi import APIRouter, Depends, BackgroundTasks,Request, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.models.models import User
from app.schema.auth_schema import ForgotPassword, OTPVerify, ResetPassword, UserLogin, UserProfile, UserRegister
from app.services.invite_service import invite_service
from app.utils.auth_utils import get_current_user
from app.services import auth_service

router = APIRouter()


@router.patch("/user/profile/update", response_model=UserProfile, tags=["Auth"])
async def update_user_profile(
    name: str = Form(None),
    number: str = Form(None),
    photo: UploadFile = File(None),
    bg_photo: UploadFile = File(None),  
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    updated_user, photo_base64, bg_photo_base64 = await auth_service.update_user_profile_service(
        db=db,
        current_user=current_user,
        name=name,
        number=number,
        photo=photo,
        bg_photo=bg_photo,   
        request=request
    )

    return {
        **UserProfile.from_orm(updated_user).dict(),
        "photo_base64": photo_base64,
        "bg_photo_base64": bg_photo_base64, 
    }


@router.get("/user/profile", tags=["Auth"])
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    return await auth_service.get_user_profile_service(current_user)

@router.post("/register", tags=["Auth"])
async def register_user(user: UserRegister,db: AsyncSession = Depends(get_db)):
    return await auth_service.register_user_service(user,db)


@router.post("/login", tags=["Auth"])
async def login_user(
    form_data: UserLogin,  
    db: AsyncSession = Depends(get_db)
):
    login_data = UserLogin(email=form_data.email, password=form_data.password)
    result = await auth_service.login_user_service(login_data, db)  
    return {
        "message": result["message"],
        "access_token": result["access_token"],
        "role": result["role"]
    }


@router.post("/forgot_password", tags=["Auth"])
async def forgot_password(forgot_data: ForgotPassword, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    return await auth_service.forgot_password_service(forgot_data, db, background_tasks)

@router.post("/reset_password", tags=["Auth"])
async def reset_password(reset_data: ResetPassword, db: AsyncSession = Depends(get_db)):
    return await auth_service.reset_password_service(reset_data, db)

@router.post("/verify_otp", tags=["Auth"])
async def verify_otp(otp_data: OTPVerify, db: AsyncSession = Depends(get_db)):
    return await auth_service.verify_otp_service(otp_data, db)

@router.delete("/user/", tags=["Super user api"])
async def delete_user(email: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    return await auth_service.delete_user_service(db, current_user, email)


@router.post("/invite-admin", tags=["Super user api"])
async def invite_admin(data: dict, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await invite_service(
        email=data["email"],
        role="admin",
        current_user=current_user,
        db=db,
        company_name=data["company_name"],
        admin_name=data["admin_name"]
    )
