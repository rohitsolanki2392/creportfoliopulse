
import uuid
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from app.models.models import User, OTP, Company, Token
import secrets

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email.ilike(email)).first()

def create_user(db, email, name, number, hashed_password, role="user", company_id=None, is_verified=False):
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
    db.commit()
    db.refresh(new_user)
    return new_user



def delete_existing_otps(db: Session, email: str):
    db.query(OTP).filter(OTP.email.ilike(email)).delete()
    db.commit()

def create_otp(db: Session, email: str, otp_code: str):
    db_otp = OTP(email=email, otp_code=otp_code)
    db.add(db_otp)
    db.commit()
    return db_otp

def get_valid_otp(db: Session, email: str, otp_code: str) -> Optional[OTP]:
    return db.query(OTP).filter(
        OTP.email.ilike(email),
        OTP.otp_code == otp_code,
        OTP.expires_at > datetime.utcnow()
    ).first()

def delete_otp(db: Session, otp_record: OTP):
    db.delete(otp_record)
    db.commit()

def update_user_password(db: Session, user: User, hashed_password: str):
    user.hashed_password = hashed_password
    db.add(user)
    db.commit()

def verify_user_account(db: Session, user: User):
    user.is_verified = True
    db.add(user)
    db.commit()

def get_all_users(db: Session):
    return db.query(User).filter(User.role != "superuser").all()

def get_company_by_name(db: Session, name: str) -> Optional[Company]:
    return db.query(Company).filter(Company.name.ilike(name)).first()

def create_company(db: Session, name: str, owner_name: str) -> Company:
    company = Company(
        name=name,
        owner_name=owner_name
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

def create_bearer_token(db: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db_token = Token(
        token=token,
        user_id=user_id
    )
    db.add(db_token)
    db.commit()
    return token

def get_user_by_token(db: Session, token: str) -> Optional[User]:
    db_token = db.query(Token).filter(
        Token.token == token,
        Token.expires_at > datetime.utcnow()
    ).first()
    if db_token:
        return db_token.user
    return None

def delete_token(db: Session, token: str):
    db.query(Token).filter(Token.token == token).delete()
    db.commit()

