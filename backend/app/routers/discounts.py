from fastapi import APIRouter, HTTPException, Query

from ..deps import DB, Admin, Staff
from ..models import Discount, Product, Subscription
from ..schemas import DiscountIn, DiscountOut, DiscountUpdate

router = APIRouter(prefix="/discounts", tags=["discounts"])


@router.post("", response_model=DiscountOut, status_code=201)
def create_discount(data: DiscountIn, db: DB, _: Admin):
    """Only the admin can create discount rules. Once active, a rule shows up on the next
    invoice on its own and stops when it expires or its usage limit is reached."""
    if data.product_id and not db.get(Product, data.product_id):
        raise HTTPException(422, "Product not found")
    if data.subscription_id and not db.get(Subscription, data.subscription_id):
        raise HTTPException(422, "Subscription not found")
    d = Discount(**data.model_dump())
    db.add(d)
    db.commit()
    return d


@router.get("", response_model=list[DiscountOut])
def list_discounts(
    db: DB,
    _: Staff,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    query = db.query(Discount)
    if not include_inactive:
        query = query.filter(Discount.is_active.is_(True))
    return query.order_by(Discount.id.desc()).offset(skip).limit(limit).all()


@router.get("/{discount_id}", response_model=DiscountOut)
def get_discount(discount_id: int, db: DB, _: Staff):
    d = db.get(Discount, discount_id)
    if not d:
        raise HTTPException(404, "Discount not found")
    return d


@router.patch("/{discount_id}", response_model=DiscountOut)
def update_discount(discount_id: int, data: DiscountUpdate, db: DB, _: Admin):
    d = db.get(Discount, discount_id)
    if not d:
        raise HTTPException(404, "Discount not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    return d
