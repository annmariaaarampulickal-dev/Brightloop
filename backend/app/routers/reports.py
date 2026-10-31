"""The finance lead's view: active subscriptions, revenue, payments and overdue invoices."""
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import extract, func

from ..deps import DB, Staff
from ..models import Invoice, Payment, Plan, Subscription, SubscriptionLine, User

router = APIRouter(prefix="/reports", tags=["reports"])

# Months per billing period, used to turn every plan into a comparable monthly figure.
MONTHLY_FACTOR = {"daily": 30.0, "weekly": 52 / 12, "monthly": 1.0, "yearly": 1 / 12}


def f(x) -> float:
    return round(float(x or 0), 2)


def _invoice_scope(query, customer_id, plan_id):
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if plan_id:
        query = query.join(Subscription, Subscription.id == Invoice.subscription_id).filter(
            Subscription.plan_id == plan_id
        )
    return query


def _sub_scope(query, customer_id, plan_id):
    if customer_id:
        query = query.filter(Subscription.customer_id == customer_id)
    if plan_id:
        query = query.filter(Subscription.plan_id == plan_id)
    return query


@router.get("/summary")
def summary(
    db: DB,
    _: Staff,
    date_from: date | None = Query(None, description="Start of the period for invoiced / collected figures"),
    date_to: date | None = None,
    customer_id: int | None = None,
    plan_id: int | None = None,
):
    """One page for the month-end questions. `invoiced` and `payments` follow the date range;
    subscription counts, MRR and receivables (outstanding / overdue) are as of today."""
    today = date.today()

    # --- subscriptions ---
    by_status = dict(
        _sub_scope(db.query(Subscription.status, func.count(Subscription.id)), customer_id, plan_id)
        .group_by(Subscription.status).all()
    )
    fees = _sub_scope(
        db.query(Plan.billing_period, func.coalesce(func.sum(Plan.price), 0))
        .select_from(Subscription).join(Plan, Plan.id == Subscription.plan_id)
        .filter(Subscription.status == "active"), customer_id, plan_id,
    ).group_by(Plan.billing_period).all()
    lines = _sub_scope(
        db.query(Plan.billing_period, func.coalesce(func.sum(SubscriptionLine.amount), 0))
        .select_from(SubscriptionLine)
        .join(Subscription, Subscription.id == SubscriptionLine.subscription_id)
        .join(Plan, Plan.id == Subscription.plan_id)
        .filter(Subscription.status == "active"), customer_id, plan_id,
    ).group_by(Plan.billing_period).all()
    mrr = sum(float(v) * MONTHLY_FACTOR[p] for p, v in [*fees, *lines])

    # --- invoices & payments in the period ---
    inv_q = db.query(func.coalesce(func.sum(Invoice.total), 0)).filter(Invoice.status.in_(("confirmed", "paid")))
    if date_from:
        inv_q = inv_q.filter(Invoice.issue_date >= date_from)
    if date_to:
        inv_q = inv_q.filter(Invoice.issue_date <= date_to)
    invoiced = _invoice_scope(inv_q, customer_id, plan_id).scalar()

    inv_counts = dict(
        _invoice_scope(db.query(Invoice.status, func.count(Invoice.id)), customer_id, plan_id)
        .group_by(Invoice.status).all()
    )

    pay_q = db.query(Payment.method, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)) \
        .select_from(Payment).join(Invoice, Invoice.id == Payment.invoice_id)
    if date_from:
        pay_q = pay_q.filter(Payment.payment_date >= date_from)
    if date_to:
        pay_q = pay_q.filter(Payment.payment_date <= date_to)
    methods = _invoice_scope(pay_q, customer_id, plan_id).group_by(Payment.method).all()

    # --- receivables (what is still owed) ---
    owed = func.coalesce(func.sum(Invoice.total - Invoice.amount_paid), 0)
    outstanding = _invoice_scope(db.query(owed).filter(Invoice.status == "confirmed"), customer_id, plan_id).scalar()
    overdue_count, overdue_amount = _invoice_scope(
        db.query(func.count(Invoice.id), owed).filter(Invoice.status == "confirmed", Invoice.due_date < today),
        customer_id, plan_id,
    ).one()

    return {
        "as_of": today,
        "filters": {"date_from": date_from, "date_to": date_to, "customer_id": customer_id, "plan_id": plan_id},
        "subscriptions": {"active": by_status.get("active", 0), "by_status": by_status, "mrr": f(mrr)},
        "invoices": {"by_status": inv_counts, "invoiced_total": f(invoiced)},
        "payments": {
            "collected": f(sum(float(a) for _, _, a in methods)),
            "count": sum(c for _, c, _ in methods),
            "by_method": {m: f(a) for m, _, a in methods},
        },
        "receivables": {"outstanding": f(outstanding), "overdue_count": overdue_count, "overdue_amount": f(overdue_amount)},
    }


@router.get("/overdue")
def overdue_invoices(
    db: DB,
    _: Staff,
    customer_id: int | None = None,
    min_days_overdue: int = Query(0, ge=0),
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    """The chase list: confirmed invoices past their due date, oldest first."""
    today = date.today()
    query = (
        db.query(Invoice, User.name, User.email)
        .join(User, User.id == Invoice.customer_id)
        .filter(Invoice.status == "confirmed", Invoice.due_date < today)
    )
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if min_days_overdue:
        query = query.filter(Invoice.due_date <= date.fromordinal(today.toordinal() - min_days_overdue))
    rows = query.order_by(Invoice.due_date, Invoice.id).offset(skip).limit(limit).all()
    return [
        {
            "invoice_id": i.id, "number": i.number, "customer_id": i.customer_id,
            "customer_name": name, "customer_email": email, "subscription_id": i.subscription_id,
            "due_date": i.due_date, "days_overdue": (today - i.due_date).days,
            "total": f(i.total), "amount_due": f(i.total - i.amount_paid),
        }
        for i, name, email in rows
    ]


@router.get("/monthly")
def monthly(db: DB, _: Staff, months: int = Query(12, ge=1, le=36)):
    """Invoiced vs collected per month - ready to plot."""
    today = date.today()
    first = date(today.year, today.month, 1)
    start_ord = (first.year * 12 + first.month - 1) - (months - 1)
    start = date(start_ord // 12, start_ord % 12 + 1, 1)

    rows: dict[str, dict] = defaultdict(lambda: {"invoiced": 0.0, "collected": 0.0})
    inv = (
        db.query(extract("year", Invoice.issue_date), extract("month", Invoice.issue_date), func.sum(Invoice.total))
        .filter(Invoice.status.in_(("confirmed", "paid")), Invoice.issue_date >= start)
        .group_by(extract("year", Invoice.issue_date), extract("month", Invoice.issue_date)).all()
    )
    for y, m, total in inv:
        rows[f"{int(y):04d}-{int(m):02d}"]["invoiced"] = f(total)
    pay = (
        db.query(extract("year", Payment.payment_date), extract("month", Payment.payment_date), func.sum(Payment.amount))
        .filter(Payment.payment_date >= start)
        .group_by(extract("year", Payment.payment_date), extract("month", Payment.payment_date)).all()
    )
    for y, m, total in pay:
        rows[f"{int(y):04d}-{int(m):02d}"]["collected"] = f(total)

    out = []
    for n in range(months):
        idx = start_ord + n
        key = f"{idx // 12:04d}-{idx % 12 + 1:02d}"
        out.append({"month": key, **rows.get(key, {"invoiced": 0.0, "collected": 0.0})})
    return out
