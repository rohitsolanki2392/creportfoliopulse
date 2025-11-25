import secrets
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import asyncio
from dotenv import load_dotenv
from app.crud import auth_crud
from app.database.db import get_db
from app.models.models import Token, User
from app.config import pwd_context, oauth2_scheme

load_dotenv()


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(pwd_context.verify, plain_password, hashed_password)


async def get_password_hash(password: str) -> str:
    try:
        hashed = await asyncio.to_thread(pwd_context.hash, password)
        return hashed
    except Exception as e:
        raise



async def create_bearer_token(db: AsyncSession, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db_token = Token(token=token, user_id=user_id)
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return token


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),

) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )



    token_to_use = token

    if not token_to_use:
        raise credentials_exception

    user = await auth_crud.get_user_by_token(db, token_to_use)
    if not user:
        raise credentials_exception

    return user

async def authenticate_user(email: str, password: str, role: str, db: AsyncSession) -> Optional[User]:
    try:
        result = await db.execute(select(User).where(User.email.ilike(email)))
        user: User = result.scalars().first()

        if not user:
            return None
        if not await verify_password(password, user.hashed_password):
            return None
        if user.role != role:
            return None
        return user
    except Exception:
        return None
