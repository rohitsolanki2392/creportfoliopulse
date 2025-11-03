from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
from typing import Optional
from app.models.models import User, OTP, Building, StandaloneFile, UserLogin



async def create_user(db: AsyncSession, email: str, name: str, number: str, hashed_password: str, role: str) -> User:
    user = User(
        email=email,
        name=name,
        number=number,
        hashed_password=hashed_password,
        role=role,
        is_verified=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_existing_otps(db: AsyncSession, email: str):
    await db.execute(delete(OTP).where(OTP.email.ilike(email)))
    await db.commit()


async def create_otp(db: AsyncSession, email: str, otp_code: str) -> OTP:
    db_otp = OTP(email=email, otp_code=otp_code)
    db.add(db_otp)
    await db.commit()
    await db.refresh(db_otp)
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


async def update_user_password(db: AsyncSession, user: User, hashed_password: str):
    user.hashed_password = hashed_password
    db.add(user)
    await db.commit()


async def verify_user_account(db: AsyncSession, user: User):
    user.is_verified = True
    db.add(user)
    await db.commit()


async def get_all_users(db: AsyncSession):
    result = await db.execute(select(User))
    return result.scalars().all()


async def delete_buildings_by_owner_id(db: AsyncSession, user_id: int):
    await db.execute(delete(Building).where(Building.owner_id == user_id))
    await db.commit()


async def delete_standalone_files_by_user_id(db: AsyncSession, user_id: int):
    await db.execute(delete(StandaloneFile).where(StandaloneFile.user_id == user_id))
    await db.commit()


async def delete_user_logins_by_user_id(db: AsyncSession, user_id: int):
    await db.execute(delete(UserLogin).where(UserLogin.user_id == user_id))
    await db.commit()
