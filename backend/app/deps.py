from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_access_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token")

DB = Annotated[Session, Depends(get_db)]


def current_user(token: Annotated[str, Depends(oauth2)], db: DB) -> User:
    uid = decode_access_token(token)
    user = db.get(User, uid) if uid else None
    if not user or not user.is_active:
        raise HTTPException(401, "Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require(*roles: str):
    def dep(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(403, "You do not have access to this action")
        return user

    return dep


# Admin controls the whole system; staff do day-to-day work; customers use the portal.
Admin = Annotated[User, Depends(require("admin"))]
Staff = Annotated[User, Depends(require("admin", "staff"))]
