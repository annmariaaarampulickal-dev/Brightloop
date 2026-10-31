from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import joinedload, selectinload

from ..deps import DB, CurrentUser, Staff
from ..emailer import send_email
from ..models import Discount, Invoice, InvoiceLine, Subscription, SubscriptionLine, User, utcnow
from ..schemas import BillingRunIn, BillingRunOut, InvoiceOut
from ..services.billing import bill_subscription, run_billing

billing = APIRouter(prefix="/billing", tags=["billing"])
invoices = APIRouter(prefix="/invoices", tags=["invoices"])


@billing.post("/run", response_model=BillingRunOut)
def billing_run(db: DB, _: Staff, data: BillingRunIn | None = None):
    """Billing day: creates the invoice for every active subscription that is due.
    Safe to run twice - a period that already has an invoice is skipped, never billed again."""
    data = data or BillingRunIn()
    return run_billing(db, data.as_of or date.today(), data.auto_confirm)


def _get_invoice(db, invoice_id: int, user: User | None = None) -> Invoice:
    inv = (
        db.query(Invoice)
        .options(selectinload(Invoice.lines), joinedload(Invoice.customer))
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if not inv or (user and user.role == "customer" and inv.customer_id != user.id):
        raise HTTPException(404, "Invoice not found")
    return inv


@invoices.post("/generate/{subscription_id}", response_model=list[InvoiceOut], status_code=201)
def generate_for_subscription(subscription_id: int, db: DB, _: Staff):
    """Create the due invoice(s) for a single subscription."""
    sub = (
        db.query(Subscription)
        .options(
            joinedload(Subscription.plan),
            selectinload(Subscription.lines).options(
                joinedload(SubscriptionLine.product), joinedload(SubscriptionLine.variant),
                joinedload(SubscriptionLine.tax)),
        )
        .filter(Subscription.id == subscription_id)
        .first()
    )
    if not sub:
        raise HTTPException(404, "Subscription not found")
    if sub.status != "active":
        raise HTTPException(409, "Only active subscriptions are billed")
    created, _skipped = bill_subscription(db, sub, date.today(), auto_confirm=False)
    if not created:
        raise HTTPException(409, "Nothing is due for this subscription yet")
    db.commit()
    return created


@invoices.get("", response_model=list[InvoiceOut])
def list_invoices(
    db: DB,
    user: CurrentUser,
    status: str | None = None,
    customer_id: int | None = None,
    subscription_id: int | None = None,
    overdue: bool | None = None,
    outstanding: bool | None = Query(None, description="Confirmed but not yet fully paid"),
    issued_from: date | None = None,
    issued_to: date | None = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    query = db.query(Invoice).options(selectinload(Invoice.lines))
    if user.role == "customer":
        query = query.filter(Invoice.customer_id == user.id)
    elif customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if status:
        query = query.filter(Invoice.status == status)
    if subscription_id:
        query = query.filter(Invoice.subscription_id == subscription_id)
    if outstanding is True:
        query = query.filter(Invoice.status == "confirmed")
    if overdue is True:
        query = query.filter(Invoice.status == "confirmed", Invoice.due_date < date.today())
    if issued_from:
        query = query.filter(Invoice.issue_date >= issued_from)
    if issued_to:
        query = query.filter(Invoice.issue_date <= issued_to)
    return query.order_by(Invoice.id.desc()).offset(skip).limit(limit).all()


@invoices.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: DB, user: CurrentUser):
    return _get_invoice(db, invoice_id, user)


@invoices.post("/{invoice_id}/confirm", response_model=InvoiceOut)
def confirm_invoice(invoice_id: int, db: DB, _: Staff):
    inv = _get_invoice(db, invoice_id)
    if inv.status != "draft":
        raise HTTPException(409, f"Only draft invoices can be confirmed (this one is {inv.status})")
    inv.status = "paid" if inv.total <= 0 else "confirmed"  # nothing to collect on a fully discounted invoice
    db.commit()
    return inv


@invoices.post("/{invoice_id}/cancel", response_model=InvoiceOut)
def cancel_invoice(invoice_id: int, db: DB, _: Staff):
    inv = _get_invoice(db, invoice_id)
    if inv.status not in ("draft", "confirmed"):
        raise HTTPException(409, f"A {inv.status} invoice cannot be cancelled")
    if inv.amount_paid > 0:
        raise HTTPException(409, "This invoice already has payments recorded")
    inv.status = "cancelled"
    for ln in inv.lines:  # a cancelled invoice gives its discount uses back
        if ln.discount_id:
            d = db.get(Discount, ln.discount_id)
            if d and d.times_used > 0:
                d.times_used -= 1
    db.commit()
    return inv


@invoices.post("/{invoice_id}/send", response_model=InvoiceOut)
def send_invoice(invoice_id: int, db: DB, _: Staff):
    inv = _get_invoice(db, invoice_id)
    if inv.status not in ("confirmed", "paid"):
        raise HTTPException(409, "Confirm the invoice before sending it")
    send_email(
        inv.customer.email,
        f"Invoice {inv.number} from Brightloop",
        f"Hi {inv.customer.name},\n\nInvoice {inv.number} for {inv.total:.2f} is due on {inv.due_date}.\n"
        f"Period: {inv.period_start} to {inv.period_end}.\n\nThank you,\nBrightloop Billing",
    )
    inv.sent_at = utcnow()
    db.commit()
    return inv


@invoices.get("/{invoice_id}/print", response_class=HTMLResponse)
def print_invoice(invoice_id: int, db: DB, user: CurrentUser):
    """A clean printable page - use the browser's Print / Save as PDF."""
    inv = _get_invoice(db, invoice_id, user)
    rows = "".join(
        f"<tr><td>{l.description}</td><td class=n>{l.quantity}</td><td class=n>{l.unit_price:.2f}</td>"
        f"<td class=n>{l.tax_rate:.0f}%</td><td class=n>{l.amount:.2f}</td></tr>"
        for l in inv.lines
    )
    return f"""<!doctype html><html><head><meta charset=utf-8><title>{inv.number}</title><style>
body{{font-family:system-ui,sans-serif;max-width:760px;margin:32px auto;color:#222}}
table{{width:100%;border-collapse:collapse;margin:24px 0}}th,td{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}
.n{{text-align:right}}.tot td{{border:0}}h1{{margin:0}}.muted{{color:#666}}</style></head><body>
<h1>Invoice {inv.number}</h1><p class=muted>Status: {inv.status} &middot; Issued {inv.issue_date} &middot; Due {inv.due_date}</p>
<p><b>Bill to:</b> {inv.customer.name} ({inv.customer.email})<br>
<b>Period:</b> {inv.period_start} to {inv.period_end}</p>
<table><tr><th>Description</th><th class=n>Qty</th><th class=n>Unit</th><th class=n>Tax</th><th class=n>Amount</th></tr>{rows}
<tr class=tot><td colspan=4 class=n>Subtotal</td><td class=n>{inv.subtotal:.2f}</td></tr>
<tr class=tot><td colspan=4 class=n>Discounts</td><td class=n>-{inv.discount_total:.2f}</td></tr>
<tr class=tot><td colspan=4 class=n>Tax</td><td class=n>{inv.tax_total:.2f}</td></tr>
<tr class=tot><td colspan=4 class=n><b>Total</b></td><td class=n><b>{inv.total:.2f}</b></td></tr>
<tr class=tot><td colspan=4 class=n>Paid</td><td class=n>{inv.amount_paid:.2f}</td></tr>
<tr class=tot><td colspan=4 class=n><b>Amount due</b></td><td class=n><b>{inv.amount_due:.2f}</b></td></tr></table>
</body></html>"""
