from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError

from .. import config
from ..deps import DB, CurrentUser
from ..emailer import send_email
from ..models import PasswordReset, User, utcnow
from ..schemas import ForgotIn, LoginIn, RegisterIn, ResetIn, TokenOut, UserOut
from ..security import (
    create_access_token,
    hash_password,
    hash_token,
    new_reset_token,
    verify_password,
)
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])


def create_user(db, email: str, name: str, password: str, role: str) -> User:
    user = User(email=email.lower(), name=name, hashed_password=hash_password(password), role=role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # the unique index also protects against two simultaneous signups
        db.rollback()
        raise HTTPException(409, "An account with this email already exists")
    return user


def _login(db, email: str, password: str) -> TokenOut:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not user.is_active or not verify_password(password, user.hashed_password):
        raise HTTPException(401, "Incorrect email or password")
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/register", response_model=UserOut, status_code=201)
def register(data: RegisterIn, db: DB):
    """Public sign-up. Always creates a *customer*; staff are added only by the admin."""
    return create_user(db, data.email, data.name, data.password, "customer")


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: DB):
    return _login(db, data.email, data.password)


@router.post("/token", response_model=TokenOut, include_in_schema=False)
def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    """Form-based login so the Swagger 'Authorize' button works (username = email)."""
    return _login(db, form.username, form.password)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/forgot-password")
def forgot_password(data: ForgotIn, db: DB):
    """Sends a reset link to the registered email. The response is identical whether or
    not the email exists, so the endpoint can't be used to discover accounts."""
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if user and user.is_active:
        raw, hashed = new_reset_token()
        db.add(
            PasswordReset(
                user_id=user.id,
                token_hash=hashed,
                expires_at=utcnow() + timedelta(minutes=config.RESET_TOKEN_EXPIRE_MINUTES),
            )
        )
        db.commit()
        send_email(
            user.email,
            "Reset your Brightloop password",
            f"Hi {user.name},\n\nUse this link to reset your password "
            f"(valid {config.RESET_TOKEN_EXPIRE_MINUTES} minutes):\n"
            f"{config.FRONTEND_URL}/reset-password?token={raw}\n\n"
            "If you didn't ask for this, you can ignore this email.",
        )
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(data: ResetIn, db: DB):
    row = db.query(PasswordReset).filter(PasswordReset.token_hash == hash_token(data.token)).first()
    if not row or row.used or row.expires_at < utcnow():
        raise HTTPException(400, "This reset link is invalid or has expired")
    user = db.get(User, row.user_id)
    user.hashed_password = hash_password(data.new_password)
    row.used = True  # single use
    db.commit()
    return {"message": "Password updated. You can now log in."}
