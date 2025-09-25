from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from app.models.models import User, OTP, Building, StandaloneFile, UserLogin

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email.ilike(email)).first()

def create_user(db: Session, email: str, name: str, number: str, hashed_password: str, role: str) -> User:
    user = User(
        email=email,
        name=name,
        number=number,
        hashed_password=hashed_password,
        role=role,
        is_verified=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

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
    return db.query(User).all()

def delete_buildings_by_owner_id(db: Session, user_id: int):
    """
    Delete all building records where the user is the owner.
    """
    db.query(Building).filter(Building.owner_id == user_id).delete()
    db.commit()


def delete_standalone_files_by_user_id(db: Session, user_id: int):
    """
    Delete all standalone_file records associated with a user.
    """
    db.query(StandaloneFile).filter(StandaloneFile.user_id == user_id).delete()
    db.commit()

def delete_user_logins_by_user_id(db: Session, user_id: int):
    """
    Delete all user_login records associated with a user.
    """
    db.query(UserLogin).filter(UserLogin.user_id == user_id).delete()
    db.commit()