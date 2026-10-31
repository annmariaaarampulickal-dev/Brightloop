from fastapi import APIRouter, Query

from ..deps import DB, Admin, Staff
from ..models import User
from ..schemas import StaffIn, UserOut
from .auth import create_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/staff", response_model=UserOut, status_code=201)
def add_staff(data: StaffIn, db: DB, _: Admin):
    """Only the admin can add a new member of staff."""
    return create_user(db, data.email, data.name, data.password, "staff")


@router.get("", response_model=list[UserOut])
def list_users(
    db: DB,
    _: Staff,
    role: str | None = None,
    q: str | None = Query(None, description="Search name or email"),
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(User.email.like(like) | User.name.ilike(like))
    return query.order_by(User.id).offset(skip).limit(limit).all()
