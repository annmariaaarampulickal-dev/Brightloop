from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import joinedload, selectinload

from ..deps import DB, CurrentUser, Staff
from ..models import (
    Plan,
    Product,
    QuotationTemplate,
    Subscription,
    SubscriptionLine,
    Tax,
    User,
)
from ..schemas import (
    FromTemplateIn,
    LineIn,
    SubscriptionIn,
    SubscriptionLineOut,
    SubscriptionOut,
    TransitionIn,
)
from ..services.periods import add_period

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# Draft -> Quotation -> Confirmed -> Active -> Closed. Paused is a side-step from Active.
TRANSITIONS = {
    "draft": {"quotation", "closed"},
    "quotation": {"draft", "confirmed", "closed"},
    "confirmed": {"active", "closed"},
    "active": {"paused", "closed"},
    "paused": {"active", "closed"},
    "closed": set(),
}
# What a customer may do themselves from the portal.
CUSTOMER_MOVES = {("active", "paused"), ("paused", "active"), ("active", "closed")}


def _load(db, sub_id: int) -> Subscription:
    sub = (
        db.query(Subscription)
        .options(selectinload(Subscription.lines), joinedload(Subscription.plan))
        .filter(Subscription.id == sub_id)
        .first()
    )
    if not sub:
        raise HTTPException(404, "Subscription not found")
    return sub


def _load_visible(db, sub_id: int, user: User) -> Subscription:
    sub = _load(db, sub_id)
    if user.role == "customer" and sub.customer_id != user.id:
        raise HTTPException(404, "Subscription not found")  # customers only see their own
    return sub


def _build_line(db, plan: Plan, ln: LineIn) -> SubscriptionLine:
    product = db.get(Product, ln.product_id)
    if not product or not product.is_active:
        raise HTTPException(422, f"Product {ln.product_id} not found or inactive")
    variant = None
    if ln.variant_id:
        variant = next((v for v in product.variants if v.id == ln.variant_id), None)
        if not variant:
            raise HTTPException(422, "Variant does not belong to that product")
    if ln.tax_id and not db.get(Tax, ln.tax_id):
        raise HTTPException(422, f"Tax {ln.tax_id} not found")
    if ln.quantity < plan.min_quantity:
        raise HTTPException(422, f"This plan needs a minimum quantity of {plan.min_quantity}")
    price = ln.unit_price if ln.unit_price is not None else product.sales_price + (variant.extra_price if variant else 0)
    return SubscriptionLine(
        product_id=product.id,
        variant_id=variant.id if variant else None,
        quantity=ln.quantity,
        unit_price=price,
        tax_id=ln.tax_id,
        amount=round(price * ln.quantity, 2),
    )


def _check_customer(db, customer_id: int) -> None:
    c = db.get(User, customer_id)
    if not c or c.role != "customer":
        raise HTTPException(422, "customer_id must be an existing customer account")


def _create(db, staff: User, *, customer_id, plan: Plan, start_date, expiry_date, terms, lines, template_id=None, valid_until=None):
    _check_customer(db, customer_id)
    if not plan.is_active:
        raise HTTPException(422, "This plan is no longer offered")
    if (plan.start_date and start_date < plan.start_date) or (plan.end_date and start_date > plan.end_date):
        raise HTTPException(422, "The plan is not available on that start date")
    expiry = expiry_date or plan.end_date or add_period(start_date, "yearly")
    if expiry < start_date:
        raise HTTPException(422, "expiry_date cannot be before start_date")
    sub = Subscription(
        customer_id=customer_id,
        plan_id=plan.id,
        template_id=template_id,
        start_date=start_date,
        expiry_date=expiry,
        payment_terms_days=terms,
        quotation_valid_until=valid_until,
        created_by=staff.id,
    )
    sub.lines = [_build_line(db, plan, ln) for ln in lines]
    db.add(sub)
    db.flush()
    sub.number = f"SUB-{sub.id:06d}"
    db.commit()
    return _load(db, sub.id)


@router.post("", response_model=SubscriptionOut, status_code=201)
def create_subscription(data: SubscriptionIn, db: DB, staff: Staff):
    plan = db.get(Plan, data.plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return _create(
        db, staff, customer_id=data.customer_id, plan=plan, start_date=data.start_date,
        expiry_date=data.expiry_date, terms=data.payment_terms_days, lines=data.lines,
    )


@router.post("/from-template/{template_id}", response_model=SubscriptionOut, status_code=201)
def create_from_template(template_id: int, data: FromTemplateIn, db: DB, staff: Staff):
    """Start from a quotation template instead of building the offer from scratch."""
    t = db.get(QuotationTemplate, template_id)
    if not t or not t.is_active:
        raise HTTPException(404, "Template not found")
    lines = [
        LineIn(product_id=l.product_id, variant_id=l.variant_id, quantity=l.quantity, tax_id=l.tax_id)
        for l in t.lines
    ]
    return _create(
        db, staff, customer_id=data.customer_id, plan=t.plan, start_date=data.start_date,
        expiry_date=data.expiry_date, terms=data.payment_terms_days, lines=lines,
        template_id=t.id, valid_until=date.today() + timedelta(days=t.validity_days),
    )


@router.get("", response_model=list[SubscriptionOut])
def list_subscriptions(
    db: DB,
    user: CurrentUser,
    status: str | None = None,
    customer_id: int | None = None,
    plan_id: int | None = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    query = db.query(Subscription).options(selectinload(Subscription.lines))
    if user.role == "customer":
        query = query.filter(Subscription.customer_id == user.id)  # portal: only their own
    elif customer_id:
        query = query.filter(Subscription.customer_id == customer_id)
    if status:
        query = query.filter(Subscription.status == status)
    if plan_id:
        query = query.filter(Subscription.plan_id == plan_id)
    return query.order_by(Subscription.id.desc()).offset(skip).limit(limit).all()


@router.get("/{sub_id}", response_model=SubscriptionOut)
def get_subscription(sub_id: int, db: DB, user: CurrentUser):
    return _load_visible(db, sub_id, user)


@router.post("/{sub_id}/lines", response_model=SubscriptionLineOut, status_code=201)
def add_line(sub_id: int, data: LineIn, db: DB, _: Staff):
    sub = _load(db, sub_id)
    if sub.status not in ("draft", "quotation"):
        raise HTTPException(409, "Lines can only be changed while the subscription is a draft or quotation")
    line = _build_line(db, sub.plan, data)
    sub.lines.append(line)
    db.commit()
    return line


@router.delete("/{sub_id}/lines/{line_id}", status_code=204)
def remove_line(sub_id: int, line_id: int, db: DB, _: Staff):
    sub = _load(db, sub_id)
    if sub.status not in ("draft", "quotation"):
        raise HTTPException(409, "Lines can only be changed while the subscription is a draft or quotation")
    line = next((l for l in sub.lines if l.id == line_id), None)
    if not line:
        raise HTTPException(404, "Line not found")
    if len(sub.lines) == 1:
        raise HTTPException(409, "A subscription needs at least one line")
    sub.lines.remove(line)
    db.commit()


@router.post("/{sub_id}/transition", response_model=SubscriptionOut)
def transition(sub_id: int, data: TransitionIn, db: DB, user: CurrentUser):
    sub = _load_visible(db, sub_id, user)
    frm, to, plan, today = sub.status, data.to, sub.plan, date.today()

    if to not in TRANSITIONS[frm]:
        raise HTTPException(409, f"Cannot move from {frm} to {to}")
    if user.role == "customer" and (frm, to) not in CUSTOMER_MOVES:
        raise HTTPException(403, "You can only pause, resume or close your own active subscription")

    # Rules the admin sets plan by plan
    if to == "paused" and not plan.allow_pause:
        raise HTTPException(409, "This plan cannot be paused")
    ending_early = to == "closed" and frm in ("active", "paused") and sub.expiry_date and sub.expiry_date > today
    if ending_early and not plan.allow_early_close and user.role != "admin":
        raise HTTPException(409, "This plan cannot be closed before its expiry date")

    if frm == "quotation" and to == "confirmed" and sub.quotation_valid_until and sub.quotation_valid_until < today:
        raise HTTPException(409, "This quotation has expired")

    if to == "active":
        if frm == "confirmed":
            sub.billing_anchor = sub.start_date
            sub.cycles_billed = 0
            sub.next_invoice_date = sub.start_date
        else:  # resuming from pause: don't bill for the time it was paused
            sub.billing_anchor = max(today, sub.start_date)
            sub.cycles_billed = 0
            sub.next_invoice_date = sub.billing_anchor
    if to in ("paused", "closed"):
        sub.next_invoice_date = None if to == "closed" else sub.next_invoice_date

    sub.status = to
    db.commit()
    return sub


@router.post("/{sub_id}/renew", response_model=SubscriptionOut)
def renew(sub_id: int, db: DB, user: CurrentUser):
    """Extend an active subscription by one more billing period (when the plan allows it)."""
    sub = _load_visible(db, sub_id, user)
    if not sub.plan.allow_renew:
        raise HTTPException(409, "This plan cannot be renewed")
    if sub.status != "active":
        raise HTTPException(409, "Only active subscriptions can be renewed")
    base = max(sub.expiry_date or date.today(), date.today())
    sub.expiry_date = add_period(base, sub.plan.billing_period)
    db.commit()
    return sub
