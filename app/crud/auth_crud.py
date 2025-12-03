from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from datetime import datetime
from typing import Optional
from app.models.models import User, OTP, Company, Token
import secrets


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email.ilike(email)))
    return result.scalars().first()

async def create_user(
    db: AsyncSession,
    email: str,
    name: str,
    number: str,
    hashed_password: str,
    role: str = "user",
    company_id: Optional[int] = None,
    is_verified: bool = False
) -> User:
    new_user = User(
        email=email,
        name=name,
        number=number,
        hashed_password=hashed_password,
        role=role,
        company_id=company_id,
        is_verified=is_verified
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def update_user_password(db: AsyncSession, user: User, hashed_password: str):
    user.hashed_password = hashed_password
    db.add(user)
    await db.commit()

async def verify_user_account(db: AsyncSession, user: User):
    user.is_verified = True
    db.add(user)
    await db.commit()


async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User).where(User.role != "superuser"))
    return result.scalars().all()



async def delete_existing_otps(db: AsyncSession, email: str):
    await db.execute(delete(OTP).where(OTP.email.ilike(email)))
    await db.commit()


async def create_otp(db: AsyncSession, email: str, otp_code: str) -> OTP:
    db_otp = OTP(email=email, otp_code=otp_code)
    db.add(db_otp)
    await db.commit()
    return db_otp

async def get_valid_otp(db: AsyncSession, email: str, otp_code: str) -> Optional[OTP]:
    result = await db.execute(
        select(OTP).where(
            OTP.email.ilike(email),
            OTP.otp_code == otp_code,
            OTP.expires_at > datetime.utcnow()
        )
    )
    return result.scalars().first()


async def delete_otp(db: AsyncSession, otp_record: OTP):
    await db.delete(otp_record)
    await db.commit()




async def get_company_by_name(db: AsyncSession, name: str) -> Optional[Company]:
    result = await db.execute(select(Company).where(Company.name.ilike(name)))
    return result.scalars().first()


async def create_company(db: AsyncSession, name: str, owner_name: str) -> Company:
    company = Company(name=name, owner_name=owner_name)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company



async def create_bearer_token(db: AsyncSession, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db_token = Token(token=token, user_id=user_id)
    db.add(db_token)
    await db.commit()
    return token


from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

async def get_user_by_token(db: AsyncSession, token: str):
    stmt = select(Token).options(selectinload(Token.user)).where(Token.token == token)
    result = await db.execute(stmt)
    db_token = result.scalars().first()
    if not db_token:
        return None
    return db_token.user 


async def delete_token(db: AsyncSession, token: str):
    await db.execute(delete(Token).where(Token.token == token))
    await db.commit()
