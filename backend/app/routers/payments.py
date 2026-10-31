from datetime import date

from fastapi import APIRouter, HTTPException, Query

from ..deps import DB, CurrentUser, Staff
from ..models import Invoice, Payment
from ..schemas import PaymentIn, PaymentOut

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentOut, status_code=201)
def record_payment(data: PaymentIn, db: DB, staff: Staff):
    """Record a payment (method, amount, date, note) against an invoice. Partial payments are
    fine; the invoice becomes Paid as soon as the payments add up to its total."""
    inv = db.query(Invoice).filter(Invoice.id == data.invoice_id).with_for_update().first()  # row lock
    if not inv:
        raise HTTPException(404, "Invoice not found")
    if inv.status == "draft":
        raise HTTPException(409, "Confirm the invoice before recording payments")
    if inv.status == "paid":
        raise HTTPException(409, "This invoice is already fully paid")
    if inv.status == "cancelled":
        raise HTTPException(409, "This invoice was cancelled")
    if data.amount > inv.amount_due:
        raise HTTPException(422, f"Amount exceeds what is still owed ({inv.amount_due:.2f})")

    payment = Payment(
        invoice_id=inv.id,
        method=data.method,
        amount=data.amount,
        payment_date=data.payment_date or date.today(),
        note=data.note,
        recorded_by=staff.id,
    )
    db.add(payment)
    inv.amount_paid = inv.amount_paid + data.amount
    if inv.amount_paid >= inv.total:
        inv.status = "paid"
    db.commit()
    return payment


@router.get("", response_model=list[PaymentOut])
def list_payments(
    db: DB,
    user: CurrentUser,
    invoice_id: int | None = None,
    customer_id: int | None = None,
    method: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    query = db.query(Payment).join(Invoice, Payment.invoice_id == Invoice.id)
    if user.role == "customer":
        query = query.filter(Invoice.customer_id == user.id)
    elif customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)
    if method:
        query = query.filter(Payment.method == method)
    if date_from:
        query = query.filter(Payment.payment_date >= date_from)
    if date_to:
        query = query.filter(Payment.payment_date <= date_to)
    return query.order_by(Payment.id.desc()).offset(skip).limit(limit).all()
