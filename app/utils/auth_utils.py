
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from app.crud import auth_crud
from app.database.db import get_db
from app.models.models import User
from app.crud.auth_crud import get_user_by_token

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "x" * 32)
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        print(f"[DEBUG] Password verification: {'SUCCESS' if result else 'FAILED'}")
        return result
    except Exception as e:
        print(f"[DEBUG] Password verification error: {str(e)}")
        return False

def get_password_hash(password: str) -> str:
    try:
        hashed = pwd_context.hash(password)
        print(f"[DEBUG] Password hashed successfully")
        return hashed
    except Exception as e:
        print(f"[DEBUG] Password hashing error: {str(e)}")
        raise

def create_bearer_token(db: Session, user_id: int) -> str:
    return auth_crud.create_bearer_token(db, user_id)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = get_user_by_token(db, token)
    if not user:
        print(f"[DEBUG] Invalid or expired token")
        raise credentials_exception

    print(f"[DEBUG] User authenticated successfully: {user.email}, role: {user.role}")
    return user

def authenticate_user(email: str, password: str, role: str, db: Session) -> Optional[User]:
    try:
        user = db.query(User).filter(User.email.ilike(email)).first()
        if not user:
            print(f"[DEBUG] User not found: {email}")
            return None

        if not verify_password(password, user.hashed_password):
            print(f"[DEBUG] Password verification failed for: {email}")
            return None

        if user.role != role:
            print(f"[DEBUG] Role verification failed for: {email}, expected: {role}, got: {user.role}")
            return None

        print(f"[DEBUG] User authenticated successfully: {email}, role: {role}")
        return user
    except Exception as e:
        print(f"[DEBUG] Authentication error for {email}: {str(e)}")
        return None
