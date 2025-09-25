


from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User
from app.crud.auth_crud import get_user_by_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    user = get_user_by_token(db, token)
    if not user:
        raise credentials_exception
    return user
