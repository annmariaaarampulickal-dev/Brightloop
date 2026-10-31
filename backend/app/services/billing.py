"""The billing engine: turns due subscriptions into invoices, safely and exactly once."""
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from ..models import Discount, Invoice, InvoiceLine, Plan, Subscription, SubscriptionLine
from .periods import add_period

CENT = Decimal("0.01")
MAX_CATCH_UP = 12  # never create more than this many periods for one subscription in one run


def D(x) -> Decimal:
    return Decimal(str(x))


def q(x) -> Decimal:
    return D(x).quantize(CENT, ROUND_HALF_UP)


def load_discounts(db) -> list[Discount]:
    return db.query(Discount).filter(Discount.is_active.is_(True)).order_by(Discount.id).all()


def discount_is_live(d: Discount, sub: Subscription, today: date) -> bool:
    """Active, inside its dates, not used up, and meant for this subscription."""
    if not d.is_active:
        return False
    if (d.start_date and today < d.start_date) or (d.end_date and today > d.end_date):
        return False
    if d.usage_limit is not None and d.times_used >= d.usage_limit:
        return False
    return d.subscription_id in (None, sub.id)


def _apply_discounts(inv: Invoice, entries: list[tuple], subtotal: Decimal, sub, today, discounts) -> list[InvoiceLine]:
    """entries = (invoice line, product_id or None, quantity). Returns the discount lines to add."""
    out: list[InvoiceLine] = []
    given = Decimal(0)
    for d in discounts:
        if not discount_is_live(d, sub, today):
            continue
        scope = [e for e in entries if d.product_id is None or e[1] == d.product_id]
        if d.product_id is None:
            qty = sum(e[2] for e in entries if e[1] is not None)  # seats, not the plan fee
        else:
            qty = sum(e[2] for e in scope)
        base = sum((D(e[0].amount) for e in scope), Decimal(0))
        if not scope or base <= 0:
            continue
        if base < D(d.min_purchase) or qty < d.min_quantity:
            continue
        amount = q(base * D(d.value) / 100) if d.kind == "percent" else min(q(d.value), base)
        amount = min(amount, subtotal - given)  # stacked discounts can never push the price below zero
        if amount <= 0:
            continue
        tax_base = sum((D(e[0].tax_amount) for e in scope), Decimal(0))
        tax_back = q(amount * tax_base / base)  # the tax on the discounted part is not charged
        out.append(InvoiceLine(description=f"Discount - {d.name}", quantity=1, unit_price=-amount,
                               tax_rate=0, tax_amount=-tax_back, amount=-amount, discount_id=d.id))
        given += amount
        d.times_used += 1
    return out


def build_invoice(db, sub: Subscription, period_start: date, today: date, discounts: list[Discount]) -> Invoice | None:
    """Create the draft invoice for one subscription period, or None if it already exists."""
    already = db.query(Invoice.id).filter(
        Invoice.subscription_id == sub.id, Invoice.period_start == period_start
    ).first()
    if already:
        return None

    plan = sub.plan
    period_end = add_period(period_start, plan.billing_period) - timedelta(days=1)
    inv = Invoice(
        subscription_id=sub.id,
        customer_id=sub.customer_id,
        period_start=period_start,
        period_end=period_end,
        issue_date=today,
        due_date=today + timedelta(days=sub.payment_terms_days),
        status="draft",
    )

    entries: list[tuple] = []
    if q(plan.price) > 0:  # the plan's own recurring fee (untaxed)
        fee = q(plan.price)
        entries.append((InvoiceLine(description=f"Plan fee - {plan.name}", quantity=1, unit_price=fee,
                                    tax_rate=0, tax_amount=Decimal(0), amount=fee), None, 1))
    for sl in sub.lines:
        rate = D(sl.tax.rate_percent) if sl.tax else Decimal(0)
        amount = q(D(sl.unit_price) * sl.quantity)
        label = sl.product.name + (f" ({sl.variant.attribute}: {sl.variant.value})" if sl.variant else "")
        entries.append((InvoiceLine(description=label, quantity=sl.quantity, unit_price=q(sl.unit_price),
                                    tax_rate=rate, tax_amount=q(amount * rate / 100), amount=amount),
                        sl.product_id, sl.quantity))

    lines = [e[0] for e in entries]
    subtotal = sum((D(l.amount) for l in lines), Decimal(0))
    discount_lines = _apply_discounts(inv, entries, subtotal, sub, today, discounts)
    lines += discount_lines

    inv.lines = lines
    inv.subtotal = subtotal
    inv.discount_total = -sum((D(l.amount) for l in discount_lines), Decimal(0))
    inv.tax_total = sum((D(l.tax_amount) for l in lines), Decimal(0))
    inv.total = inv.subtotal - inv.discount_total + inv.tax_total
    db.add(inv)
    db.flush()
    inv.number = f"INV-{inv.id:06d}"
    return inv


def _next_due(sub: Subscription) -> date:
    return add_period(sub.billing_anchor, sub.plan.billing_period, sub.cycles_billed)


def bill_subscription(db, sub: Subscription, as_of: date, auto_confirm: bool,
                      discounts: list[Discount] | None = None) -> tuple[list[Invoice], int]:
    """Bill every period of `sub` that is due up to `as_of`. Returns (new invoices, skipped)."""
    if discounts is None:
        discounts = load_discounts(db)
    created, skipped = [], 0
    while sub.next_invoice_date and sub.next_invoice_date <= as_of and len(created) + skipped < MAX_CATCH_UP:
        period_start = sub.next_invoice_date
        if sub.expiry_date and period_start > sub.expiry_date:
            sub.next_invoice_date = None  # nothing left to bill
            break
        try:
            with db.begin_nested():  # a savepoint: a race on the unique index only loses this one
                inv = build_invoice(db, sub, period_start, as_of, discounts)
        except IntegrityError:
            inv = None
        if inv is None:
            skipped += 1
        else:
            if auto_confirm:
                inv.status = "paid" if inv.total <= 0 else "confirmed"
            created.append(inv)
        sub.cycles_billed += 1
        sub.next_invoice_date = _next_due(sub)
    return created, skipped


def close_expired(db, as_of: date) -> int:
    """Close subscriptions on plans that close on their own once they (or the plan) end."""
    subs = (
        db.query(Subscription)
        .join(Plan, Subscription.plan_id == Plan.id)
        .filter(Subscription.status.in_(("active", "paused")), Plan.auto_close.is_(True))
        .filter(
            (Subscription.expiry_date < as_of) | (Plan.end_date.isnot(None) & (Plan.end_date < as_of))
        )
        .all()
    )
    for s in subs:
        s.status = "closed"
        s.next_invoice_date = None
    return len(subs)


def run_billing(db, as_of: date, auto_confirm: bool = False) -> dict:
    subs = (
        db.query(Subscription)
        .options(
            joinedload(Subscription.plan),
            selectinload(Subscription.lines).options(
                joinedload(SubscriptionLine.product),
                joinedload(SubscriptionLine.variant),
                joinedload(SubscriptionLine.tax),
            ),
        )
        .filter(Subscription.status == "active", Subscription.next_invoice_date <= as_of)
        .order_by(Subscription.id)
        .all()
    )
    discounts = load_discounts(db)  # loaded once; usage counts update as invoices are created
    ids, skipped = [], 0
    for sub in subs:
        created, sk = bill_subscription(db, sub, as_of, auto_confirm, discounts)
        ids += [i.id for i in created]
        skipped += sk
    closed = close_expired(db, as_of)  # after billing, so a final period is never lost
    db.commit()
    return {"as_of": as_of, "created": len(ids), "skipped_already_billed": skipped,
            "closed_subscriptions": closed, "invoice_ids": ids}
