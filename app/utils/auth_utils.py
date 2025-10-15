
import secrets
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from dotenv import load_dotenv
from app.crud import auth_crud
from app.database.db import get_db
from app.models.models import Token, User
from app.crud.auth_crud import get_user_by_token
from app.config import pwd_context,oauth2_scheme
load_dotenv()



def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    try:
        hashed = pwd_context.hash(password)
        print(f"[DEBUG] Password hashed successfully")
        return hashed
    except Exception as e:
        print(f"[DEBUG] Password hashing error: {str(e)}")
        raise

def create_bearer_token(db: Session, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    db_token = Token(token=token, user_id=user_id)
    db.add(db_token)
    db.commit()
    return token

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
