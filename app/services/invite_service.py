
import os
import random
import secrets
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.models import User
from app.utils.email import send_email
from app.utils.security import get_password_hash
from app.crud.auth_crud import create_user, get_user_by_email, create_company

async def invite_service(
    email: str,
    role: str,
    current_user: User,
    db: Session,
    company_name: str = None,
    admin_name: str = None
):
    if role == "admin" and current_user.role != "superuser":
        raise HTTPException(status_code=403, detail="Superuser access required")
    if role == "user" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    existing_user = get_user_by_email(db, email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    raw_password = secrets.token_hex(8) if role == "admin" else ''.join(random.choices('0123456789', k=8))
    hashed_password = get_password_hash(raw_password)

    if role == "admin":
        if not company_name or not admin_name:
            raise HTTPException(status_code=400, detail="Company name and admin name required")
        new_company = create_company(db, company_name, admin_name)
        new_user = create_user(
            db,
            email=email,
            name=admin_name,
            number="placeholder",
            hashed_password=hashed_password,
            role="admin",
            is_verified=True
        )
        new_user.company_id = new_company.id
        new_company.owner_id = new_user.id
        db.commit()
        db.refresh(new_user)
        db.refresh(new_company)
        invite_link = f"Your admin credentials:\nEmail: {email}\nPassword: {raw_password}\nCompany: {company_name}"
    else:
        name = email.split("@")[0]
        number = "1234567890"
        company_id = current_user.company_id
        new_user = create_user(
            db,
            email=email,
            name=name,
            number=number,
            hashed_password=hashed_password,
            role="user",
            company_id=company_id,
            is_verified=True
        )
        db.commit()
        db.refresh(new_user)
        invite_link = f"Dear {name},\nYour username: {email}\nPassword: {raw_password}\nInvite Link: {os.getenv('INVITE_LINK')}"

    subject = f"Invitation to join as {role.capitalize()}"
    send_email(email, subject, invite_link)

    return {"message": f"{role.capitalize()} invited successfully", "email": email, "user_id": new_user.id}
