import os
import random
import secrets
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User
from app.utils.email import send_email
from app.utils.auth_utils import get_password_hash
from app.crud.auth_crud import create_user, get_user_by_email, create_company

async def invite_service(
    email: str,
    role: str,
    current_user: User,
    db: AsyncSession,
    company_name: str = None,
    admin_name: str = None
):

    # Role permissions
    if role == "admin" and current_user.role != "superuser":
        raise HTTPException(status_code=403, detail="Superuser access required")
    if role == "user" and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if already registered
    existing_user = await get_user_by_email(db, email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    # Placeholder password (not used)
    hashed_password = await get_password_hash("TEMP_UNUSED_PASSWORD")


    # ------------------------------------------------------
    # SUPERUSER INVITES ADMIN
    # ------------------------------------------------------
    if role == "admin":

        if not company_name or not admin_name:
            raise HTTPException(status_code=400, detail="Company name and admin name required")

        # Create company
        new_company = await create_company(db, company_name, admin_name)

        # Create admin
        new_user = await create_user(
            db,
            email=email,
            name=admin_name,
            number="0000000000",
            hashed_password=hashed_password,
            role="admin",
            company_id=new_company.id,
            is_verified=False       # Admin will verify after Reset Password
        )

        new_company.owner_id = new_user.id

        await db.commit()
        await db.refresh(new_user)
        await db.refresh(new_company)

        name_for_email = admin_name


    # ------------------------------------------------------
    # ADMIN INVITES NORMAL USER
    # ------------------------------------------------------
    else:
        name_for_email = email.split("@")[0]
        company_id = current_user.company_id

        new_user = await create_user(
            db=db,
            email=email,
            name=name_for_email,
            number="0000000000",
            hashed_password=hashed_password,
            role="user",
            company_id=company_id,
            is_verified=False       # User also must verify after Reset Password
        )

        await db.commit()
        await db.refresh(new_user)


    # ------------------------------------------------------
    # SAME EMAIL FORMAT FOR BOTH ADMIN + USER
    # ------------------------------------------------------
    invite_msg = (
        f"Hello {name_for_email},\n\n"
        f"You have been invited to join the platform as a {role}.\n"
        f"Please login using your email: {email}\n"
        f"Then click 'Forgot Password' to set your password and activate your account.\n\n"
        f"Platform Link: {os.getenv('INVITE_LINK')}\n"
        f"Welcome aboard!\n"
    )

    send_email(email, f"Invitation to join as {role.capitalize()}", invite_msg)

    return {
        "message": f"{role.capitalize()} invited successfully",
        "email": email,
        "user_id": new_user.id
    }
