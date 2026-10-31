"""Requirement: with thousands of subscriptions, every page responds in under two seconds."""
import time
from datetime import date, timedelta

import pytest

from app.database import SessionLocal
from app.models import Invoice, InvoiceLine, Payment, Plan, Product, Subscription, SubscriptionLine, User

N_CUSTOMERS, N_SUBS = 200, 5000
TODAY = date.today()
LIMIT_SECONDS = 2.0
PLAN_ID = [0]  # filled by the fixture so a plan-filtered report is timed too


@pytest.fixture(scope="module", autouse=True)
def big_dataset(client, admin):
    plan_id = client.post("/plans", json={"name": "Perf plan", "price": 50, "billing_period": "monthly"}, headers=admin).json()["id"]
    prod_id = client.post("/products", json={"name": "Perf product", "type": "software", "sales_price": 100}, headers=admin).json()["id"]
    PLAN_ID[0] = plan_id
    with SessionLocal() as db:
        db.bulk_insert_mappings(User, [
            dict(email=f"perf{i}@example.test", name=f"Perf Customer {i}", hashed_password="x", role="customer", is_active=True)
            for i in range(N_CUSTOMERS)])
        db.commit()
        cust_ids = [r[0] for r in db.query(User.id).filter(User.email.like("perf%@example.test")).order_by(User.id)]

        db.bulk_insert_mappings(Subscription, [
            dict(number=f"PERF-{i:06d}", customer_id=cust_ids[i % N_CUSTOMERS], plan_id=plan_id,
                 start_date=TODAY - timedelta(days=60), expiry_date=TODAY + timedelta(days=300),
                 payment_terms_days=15, status="active" if i % 10 else "closed",
                 billing_anchor=TODAY - timedelta(days=60), cycles_billed=2,
                 next_invoice_date=TODAY + timedelta(days=(i % 28) + 1) if i % 10 else None)
            for i in range(N_SUBS)])
        db.commit()
        subs = db.query(Subscription.id, Subscription.customer_id, Subscription.number) \
            .filter(Subscription.number.like("PERF-%")).order_by(Subscription.id).all()

        db.bulk_insert_mappings(SubscriptionLine, [
            dict(subscription_id=s.id, product_id=prod_id, quantity=3, unit_price=100, amount=300) for s in subs])
        invoices, k = [], 0
        for n, s in enumerate(subs):
            for back in (45, 15):  # two invoices per subscription; the older one is often unpaid -> overdue
                status = ("paid", "confirmed", "confirmed", "draft", "cancelled")[(n + back) % 5]
                issue = TODAY - timedelta(days=back)
                invoices.append(dict(
                    number=f"PERFINV-{k:07d}", subscription_id=s.id, customer_id=s.customer_id,
                    period_start=issue, period_end=issue + timedelta(days=29), issue_date=issue,
                    due_date=issue + timedelta(days=15), status=status, subtotal=300, discount_total=0,
                    tax_total=54, total=354, amount_paid=354 if status == "paid" else 0))
                k += 1
        db.bulk_insert_mappings(Invoice, invoices)
        db.commit()
        paid = db.query(Invoice.id, Invoice.issue_date).filter(Invoice.number.like("PERFINV-%"), Invoice.status == "paid").all()
        db.bulk_insert_mappings(Payment, [
            dict(invoice_id=i.id, method=("card", "upi", "bank_transfer", "cash")[i.id % 4], amount=354, payment_date=i.issue_date)
            for i in paid])
        db.commit()
    yield


def timed(client, path, headers):
    t0 = time.perf_counter()
    r = client.get(path, headers=headers)
    elapsed = time.perf_counter() - t0
    assert r.status_code == 200, (path, r.text[:200])
    return elapsed, r.json()


PAGES = [
    "/reports/summary",
    "/reports/summary?date_from=2026-01-01&plan_id={plan}",
    "/reports/overdue?limit=50",
    "/reports/monthly?months=12",
    "/subscriptions?limit=50",
    "/subscriptions?status=active&limit=200",
    "/invoices?limit=50",
    "/invoices?overdue=true&limit=200",
    "/invoices?outstanding=true&limit=200",
    "/payments?limit=200",
    "/users?role=customer&limit=200",
]


@pytest.mark.parametrize("path", PAGES)
def test_page_under_two_seconds(client, admin, path):
    path = path.format(plan=PLAN_ID[0])
    worst = max(timed(client, path, admin)[0] for _ in range(3))
    print(f"{worst * 1000:7.0f} ms  {path}")
    assert worst < LIMIT_SECONDS, f"{path} took {worst:.2f}s"


def test_customer_portal_is_fast_too(client):
    from .conftest import login
    client.post("/auth/register", json={"email": "perf-portal@example.com", "password": "Str0ng!Pass", "name": "Portal"})
    head = login(client, "perf-portal@example.com", "Str0ng!Pass")
    for path in ("/subscriptions", "/invoices", "/payments"):
        assert timed(client, path, head)[0] < LIMIT_SECONDS


def test_billing_run_over_thousands_of_subscriptions(client, admin):
    """Everything due in the next 30 days across ~4,500 active subscriptions."""
    t0 = time.perf_counter()
    r = client.post("/billing/run", json={"as_of": str(TODAY + timedelta(days=30))}, headers=admin)
    elapsed = time.perf_counter() - t0
    assert r.status_code == 200
    run = r.json()
    print(f"billing run created {run['created']} invoices in {elapsed:.1f}s")
    assert run["created"] > 4000
    again = client.post("/billing/run", json={"as_of": str(TODAY + timedelta(days=30))}, headers=admin).json()
    assert again["created"] == 0  # nothing is billed twice
