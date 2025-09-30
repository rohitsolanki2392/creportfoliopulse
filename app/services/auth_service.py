
import base64
import os
from typing import List
from sqlalchemy.orm import Session
from app.models.models import User, Company
import uuid
from fastapi import  HTTPException, Request, status, BackgroundTasks, UploadFile
from fastapi.responses import JSONResponse
from app.crud import auth_crud
from app.schema.invite_schema import UserListResponse
from app.utils.auth_utils import verify_password, get_password_hash, create_bearer_token
from app.services.email_service import cleanup_expired_otps, generate_otp, send_otp_email
import secrets

UPLOAD_DIR = "uploads/profile_photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}

async def register_user_service(user, db: Session):
    cleanup_expired_otps()

    if user.role not in ["superuser", "admin", "user"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Invalid role. Must be 'superuser', 'admin' or 'user'"}
        )

    existing_user = auth_crud.get_user_by_email(db, user.email)
    if existing_user:
        if existing_user.is_verified:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Email already registered and verified"}
            )
        else:
            auth_crud.delete_existing_otps(db, user.email)
            otp_code = generate_otp()
            auth_crud.create_otp(db, user.email, otp_code)
            otp= send_otp_email (user.email, otp_code)
            
            return {"message": "OTP resent. Please verify with the OTP sent to your email."}

    if user.password != user.confirm_password:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Passwords do not match"}
        )

    hashed_password = get_password_hash(user.password)
    db_user = auth_crud.create_user(db, user.email, user.name, user.number, hashed_password, user.role)

    auth_crud.delete_existing_otps(db, user.email)
    otp_code = generate_otp()
    auth_crud.create_otp(db, user.email, otp_code)
    send_otp_email(user.email, otp_code)
    return {"message": "OTP sent. Please verify with the OTP sent to your email."}


def login_user_service(login_data, db: Session):
    db_user = auth_crud.get_user_by_email(db, login_data.email)

    if not db_user or not verify_password(login_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not db_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified. Please verify your email first."
        )

    token = create_bearer_token(db, db_user.id)

    return {
        "message": "Login successful",
        "role": db_user.role.value if hasattr(db_user.role, "value") else db_user.role,
        "access_token": token,
    }

async def forgot_password_service(data, db: Session, background_tasks: BackgroundTasks):
    cleanup_expired_otps()
    user = auth_crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(404, "User not found")

    if not user.is_verified:
        raise HTTPException(400, "Email not verified")

    auth_crud.delete_existing_otps(db, data.email)
    otp_code = generate_otp()
    auth_crud.create_otp(db, data.email, otp_code)
    background_tasks.add_task(send_otp_email, data.email, otp_code)
    return {"message": "Password reset OTP sent to your email."}


def reset_password_service(data, db: Session):
    if data.new_password != data.confirm_password:
        raise HTTPException(400, "New password and confirm password do not match")

    user = auth_crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(404, "User not found")

    hashed_password = get_password_hash(data.new_password)
    auth_crud.update_user_password(db, user, hashed_password)
    return {"message": "Password reset successfully"}


def verify_otp_service(data, db: Session):
    cleanup_expired_otps()
    otp_record = auth_crud.get_valid_otp(db, data.email, data.otp)
    if not otp_record:
        raise HTTPException(400, "Invalid or expired OTP")

    user = auth_crud.get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(404, "User not found")

    if not user.is_verified:
        auth_crud.verify_user_account(db, user)
        auth_crud.delete_otp(db, otp_record)
        return {"message": "Account verified! You can now login."}
    return {"message": "OTP verified"}

async def update_user_profile_service(db: Session, current_user, name: str = None, number: str = None, photo: UploadFile = None, request: Request = None):
    updated = False
    image_preview = None
    if name:
        current_user.name = name
        updated = True
    if number:
        current_user.number = number
        updated = True
    if photo:
        file_ext = os.path.splitext(photo.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG, PNG, GIF allowed.")
        
        file_bytes = await photo.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        new_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, new_filename)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        
        
        current_user.photo_url = f"/uploads/profile_photos/{new_filename}"  

        image_preview = f"data:{'image/jpeg' if file_ext in ['.jpg','.jpeg'] else f'image/{file_ext[1:]}' };base64,{base64.b64encode(file_bytes).decode('utf-8')}"
        updated = True


    if not updated:
        raise HTTPException(status_code=400, detail="No data provided for update")
    
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user, image_preview

def get_user_profile_service(current_user):
    response = {
        "id": current_user.id,
        "name": current_user.name,
        "number": current_user.number,
        "photo_url": current_user.photo_url,
        "photo_base64": None
    }

    if current_user.photo_url:
        file_path = current_user.photo_url.replace("/uploads", "uploads")
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            file_ext = os.path.splitext(file_path)[1].lower()
            mime_type = "image/jpeg" if file_ext in [".jpg", ".jpeg"] else "image/png" if file_ext == ".png" else "image/gif"
            response["photo_base64"] = f"data:{mime_type};base64,{base64.b64encode(file_bytes).decode('utf-8')}"
        else:
            response["photo_base64"] = None
    
    return response

async def list_all_users_service(current_user: User, db: Session) -> List[UserListResponse]:
    if current_user.role not in ["superuser", "admin"]:
        raise HTTPException(status_code=403, detail="Superuser or admin access required")

    users = []

    if current_user.role == "superuser":
        users = db.query(User).filter(User.role == "admin").all()

    elif current_user.role == "admin":
        users = db.query(User).filter(
            User.company_id == current_user.company_id,
            User.role == "user"
        ).all()

    user_list = []
    for user in users:
        user_list.append(UserListResponse(
            email=user.email,
            status="Verified" if user.is_verified else "Not Verified",
            display=f"{user.name} ({user.role.capitalize()})",
            name=user.name,
            created=user.created_at,
            actions=["edit", "delete"]
        ))

    return user_list

def delete_user_service(db: Session, current_user: User, email: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role not in ["superuser", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers or admins can delete users"
        )
        
    if current_user.role == "admin" and user.company_id != current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins can only delete users within their company"
        )


    if user.role=="superuser":
        admin_company = db.query(User).filter(User.company_id == user.company_id).all()
        for u in admin_company:
            db.delete(u)
        db.commit()
    if user.role == "admin":
        users_in_company = db.query(User).filter(User.company_id == user.company_id).all()
        for u in users_in_company:
            db.delete(u)
        db.commit() 
        company = db.query(Company).filter(Company.id == user.company_id).first()
        if company:
            db.delete(company)
        db.commit()   

        return {"message": f"Admin {user.email}, all company users, and the company deleted successfully"}

    else:
        db.delete(user)
        db.commit()
        return {"message": f"User {user.email} deleted successfully"}


async def invite_admin_service(invite_data, db: Session, background_tasks: BackgroundTasks, current_user: User):
    if current_user.role != "superuser":
        raise HTTPException(status_code=403, detail="Superuser access required")

    existing_company = auth_crud.get_company_by_name(db, invite_data.company_name)
    if existing_company:
        raise HTTPException(status_code=400, detail="Company name already exists")

    existing_user = auth_crud.get_user_by_email(db, invite_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    raw_password = secrets.token_hex(8)
    hashed_password = get_password_hash(raw_password)

    new_company = auth_crud.create_company(db, invite_data.company_name, invite_data.admin_name)
    new_admin = auth_crud.create_user(
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
    db.commit()
    db.refresh(new_admin)
    db.refresh(new_company)

    token = create_bearer_token(db, new_admin.id)
    email_body = f"Your admin credentials:\nEmail: {invite_data.email}\nPassword: {raw_password}\nCompany: {invite_data.company_name}\nToken: {token}\nPlease login and change your password."
    send_otp_email(invite_data.email, email_body)
    return {"message": "Admin invited successfully"}



