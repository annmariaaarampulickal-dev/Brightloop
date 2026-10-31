import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from . import config

ALGORITHM = "HS256"


def validate_password(p: str) -> str:
    """Brightloop rule: more than 8 characters, with an uppercase letter,
    a lowercase letter and a special character."""
    if len(p) <= 8:
        raise ValueError("Password must be more than 8 characters")
    if len(p.encode()) > 72:
        raise ValueError("Password must be at most 72 bytes")
    if not re.search(r"[A-Z]", p):
        raise ValueError("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", p):
        raise ValueError("Password must contain a lowercase letter")
    if not re.search(r"[^A-Za-z0-9]", p):
        raise ValueError("Password must contain a special character")
    return p


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": exp}, config.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    try:
        return int(jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def new_reset_token() -> tuple[str, str]:
    """Returns (raw token for the email link, sha256 hash to store)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
