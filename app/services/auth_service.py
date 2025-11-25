import os
import uuid
import base64
import secrets
from typing import List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Tour, User
from fastapi import HTTPException, status, BackgroundTasks, UploadFile, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from app.crud import auth_crud
from app.models.models import User
from app.schema.invite_schema import UserListResponse
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from app.utils.auth_utils import verify_password, get_password_hash, create_bearer_token
from app.services.email_service import cleanup_expired_otps, generate_otp, send_otp_email
import aiofiles


async def register_user_service(user, db: AsyncSession):
    await cleanup_expired_otps(db)

    if user.role not in ["superuser", "admin", "user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'superuser', 'admin' or 'user'"
        )

    existing_user = await auth_crud.get_user_by_email(db, user.email)
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered and verified"
            )
        else:
            await auth_crud.delete_existing_otps(db, user.email)
            otp_code = generate_otp()
            await auth_crud.create_otp(db, user.email, otp_code)
            await send_otp_email(user.email, otp_code)
            return {"message": "OTP resent. Please verify with the OTP sent to your email."}

    if user.password != user.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    hashed_password = get_password_hash(user.password)
    db_user = await auth_crud.create_user(
        db, user.email, user.name, user.number, hashed_password, user.role
    )

    await auth_crud.delete_existing_otps(db, user.email)
    otp_code = generate_otp()
    await auth_crud.create_otp(db, user.email, otp_code)
    await send_otp_email(user.email, otp_code)

    return {"message": "OTP sent. Please verify with the OTP sent to your email."}


async def login_user_service(login_data, db: AsyncSession):
    db_user = await auth_crud.get_user_by_email(db, login_data.email)
    if not db_user or not await verify_password(login_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Account not verified. Please verify your email first.")

    token = await create_bearer_token(db, db_user.id)
    return {
        "message": "Login successful",
        "role": db_user.role,
        "access_token": token,
        "token_type": "bearer"
    }



async def forgot_password_service(data, db: AsyncSession, background_tasks: BackgroundTasks):
    await cleanup_expired_otps(db)
    user = await auth_crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(404, "User not found")
    await auth_crud.delete_existing_otps(db, data.email)
    otp_code = generate_otp()
    await auth_crud.create_otp(db, data.email, otp_code)
    background_tasks.add_task(send_otp_email, data.email, otp_code)
    return {"message": "Password reset OTP sent to your email."}


async def reset_password_service(data, db: AsyncSession):
    if data.new_password != data.confirm_password:
        raise HTTPException(400, "New password and confirm password do not match")

    user = await auth_crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(404, "User not found")

    hashed_password = await get_password_hash(data.new_password)
    await auth_crud.update_user_password(db, user, hashed_password)
    return {"message": "Password reset successfully"}



async def verify_otp_service(data, db: AsyncSession):
    """Service to verify OTP and activate user account."""
    await cleanup_expired_otps(db)

    otp_record = await auth_crud.get_valid_otp(db, data.email, data.otp)
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user = await auth_crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")


    if not user.is_verified:
        await auth_crud.verify_user_account(db, user)
        await auth_crud.delete_otp(db, otp_record)
        return {"message": "Account verified! You can now login."}

    return {"message": "OTP verified successfully."}


async def save_file(upload_file: UploadFile, prefix: str = "") -> Tuple[str, str]:
    ext = os.path.splitext(upload_file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    file_bytes = await upload_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    



    new_filename = f"{prefix}{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_bytes)

    base64_preview = f"data:image/{ext[1:]};base64,{base64.b64encode(file_bytes).decode()}"
    return file_path, base64_preview



async def update_user_profile_service(
    db: AsyncSession,
    current_user: User,
    name: Optional[str] = None,
    number: Optional[str] = None,
    photo: Optional[UploadFile] = None,
    bg_photo: Optional[UploadFile] = None,
    request: Request = None
) -> Tuple[User, Optional[str], Optional[str]]:

    updated = False
    image_preview = None
    bg_image_preview = None


    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")


    if name and name.strip():
        user.name = name.strip()
        updated = True

    if number and number.strip():
        user.number = number.strip()
        updated = True

    if photo:
        file_path, image_preview = await save_file(photo)
        user.photo_url = f"/uploads/profile_photos/{os.path.basename(file_path)}"
        updated = True

    if bg_photo:
        file_path, bg_image_preview = await save_file(bg_photo, prefix="bg_")
        user.bg_photo_url = f"/uploads/profile_photos/{os.path.basename(file_path)}"
        updated = True

    if not updated:
        raise HTTPException(status_code=400, detail="No valid data provided for update")


    await db.commit()
    await db.refresh(user)

    return user, image_preview, bg_image_preview

async def list_all_users_service(current_user: User, db: AsyncSession) -> List[UserListResponse]:
    if current_user.role not in ["superuser", "admin"]:
        raise HTTPException(status_code=403, detail="Superuser or admin access required")

    if current_user.role == "superuser":
        users = (await db.execute(select(User).filter(User.role == "admin"))).scalars().all()
    else:  
        users = (await db.execute(select(User).filter(
            User.company_id == current_user.company_id,
            User.role == "user"
        ))).scalars().all()

    user_list = [
        UserListResponse(
            email=u.email,
            status="Verified" if u.is_verified else "Not Verified",
            display=f"{u.name} ({u.role.capitalize()})",
            name=u.name,
            created=u.created_at,
            actions=["edit", "delete"],
            gemini_status=u.gemini_chat_enabled

        ) for u in users
    ]
    return user_list



async def delete_user_service(db: AsyncSession, current_user: User, email: str):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

   
    await db.execute(delete(Tour).where(Tour.user_id == user.id))


    await db.delete(user)
    await db.commit()

    return {"message": f"User {user.email} deleted successfully"}

async def invite_admin_service(invite_data, db: AsyncSession, background_tasks: BackgroundTasks, current_user: User):
    if current_user.role != "superuser":
        raise HTTPException(status_code=403, detail="Superuser access required")

    existing_company = await auth_crud.get_company_by_name(db, invite_data.company_name)
    if existing_company:
        raise HTTPException(status_code=400, detail="Company name already exists")

    existing_user = await auth_crud.get_user_by_email(db, invite_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    raw_password = secrets.token_hex(8)
    hashed_password = await get_password_hash(raw_password)


    new_company = await auth_crud.create_company(db, invite_data.company_name, invite_data.admin_name)
    new_admin = await auth_crud.create_user(
        db=db,
        email=invite_data.email,
        name=invite_data.admin_name,
        number="placeholder",
        hashed_password=hashed_password,
        role="admin",
        is_verified=True
    )

    new_admin.company_id = new_company.id
    new_company.owner_id = new_admin.id
    db.add(new_admin)
    db.add(new_company)
    await db.commit()
    await db.refresh(new_admin)
    await db.refresh(new_company)

    token = await create_bearer_token(db, new_admin.id)
    email_body = f"Your admin credentials:\nEmail: {invite_data.email}\nPassword: {raw_password}\nCompany: {invite_data.company_name}\nToken: {token}\nPlease login and change your password."
    background_tasks.add_task(send_otp_email, invite_data.email, email_body)
    return {"message": "Admin invited successfully"}



async def get_user_profile_service(current_user):
    response = {
        "id": current_user.id,
        "name": current_user.name,
        "number": current_user.number,
        "email": current_user.email,
        "role": current_user.role,
        "photo_url": current_user.photo_url,
        "bg_photo_url": current_user.bg_photo_url, 
        "gemini_status": current_user.gemini_chat_enabled,
        "photo_base64": None,
        "bg_photo_base64": None  
    }


    if current_user.photo_url:
        file_path = current_user.photo_url.replace("/uploads", "uploads")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            file_ext = os.path.splitext(file_path)[1].lower()
            mime_type = (
                "image/jpeg" if file_ext in [".jpg", ".jpeg"]
                else "image/png" if file_ext == ".png"
                else "image/gif"
            )
            response["photo_base64"] = (
                f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode('utf-8')}"
            )

    if current_user.bg_photo_url:
        file_path = current_user.bg_photo_url.replace("/uploads", "uploads")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            file_ext = os.path.splitext(file_path)[1].lower()
            mime_type = (
                "image/jpeg" if file_ext in [".jpg", ".jpeg"]
                else "image/png" if file_ext == ".png"
                else "image/gif"
            )
            response["bg_photo_base64"] = (
                f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode('utf-8')}"
            )

    return response
