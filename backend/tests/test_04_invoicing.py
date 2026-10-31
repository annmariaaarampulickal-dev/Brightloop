"""Scene 4: billing day."""
import time
from datetime import date, timedelta

import pytest

from app.emailer import OUTBOX

from .conftest import login

PW = "Str0ng!Pass"
TODAY = date.today()


def mv(client, sid, steps, head):
    for to in steps:
        assert client.post(f"/subscriptions/{sid}/transition", json={"to": to}, headers=head).status_code == 200


@pytest.fixture(scope="module")
def world(client, admin):
    staff_email = "billing-rep@example.com"
    client.post("/users/staff", json={"email": staff_email, "password": PW, "name": "Bill"}, headers=admin)
    tax = client.post("/taxes", json={"name": "GST 18%", "rate_percent": 18}, headers=admin).json()
    prod = client.post("/products", json={"name": "Seat", "type": "software", "sales_price": 1000,
        "variants": [{"attribute": "Brand", "value": "Odoo", "extra_price": 560}]}, headers=admin).json()
    plan = client.post("/plans", json={"name": "Billing Monthly", "price": 100, "billing_period": "monthly"}, headers=admin).json()
    client.post("/auth/register", json={"email": "inv-cust@example.com", "password": PW, "name": "Inv Customer"})
    cust = login(client, "inv-cust@example.com", PW)
    cid = client.get("/auth/me", headers=cust).json()["id"]
    return {"tax": tax, "prod": prod, "plan": plan, "cid": cid, "cust": cust,
            "staff": login(client, staff_email, PW)}


def new_active_sub(client, w, cid=None, plan=None, qty=5, start=None, expiry=None):
    body = {"customer_id": cid or w["cid"], "plan_id": (plan or w["plan"])["id"],
            "start_date": str(start or TODAY), "payment_terms_days": 15,
            "lines": [{"product_id": w["prod"]["id"], "variant_id": w["prod"]["variants"][0]["id"],
                       "quantity": qty, "tax_id": w["tax"]["id"]}]}
    if expiry:
        body["expiry_date"] = str(expiry)
    sub = client.post("/subscriptions", json=body, headers=w["staff"]).json()
    mv(client, sub["id"], ["quotation", "confirmed", "active"], w["staff"])
    return sub


def test_invoice_is_built_from_subscription_with_tax(client, world):
    sub = new_active_sub(client, world)
    run = client.post("/billing/run", json={}, headers=world["staff"]).json()
    assert run["created"] >= 1
    inv = client.get(f"/invoices?subscription_id={sub['id']}", headers=world["staff"]).json()[0]
    assert inv["number"].startswith("INV-") and inv["status"] == "draft"
    assert inv["customer_id"] == world["cid"]
    assert inv["due_date"] == str(TODAY + timedelta(days=15))  # payment terms
    # plan fee 100 (no tax) + 5 x 1560 = 7800 taxed at 18% = 1404
    assert (inv["subtotal"], inv["tax_total"], inv["total"]) == (7900, 1404, 9304)
    assert [l["description"] for l in inv["lines"]] == ["Plan fee - Billing Monthly", "Seat (Brand: Odoo)"]
    assert inv["lines"][1]["tax_amount"] == 1404


def test_nothing_is_billed_twice(client, world):
    sub = new_active_sub(client, world)
    first = client.post("/billing/run", json={}, headers=world["staff"]).json()
    again = client.post("/billing/run", json={}, headers=world["staff"]).json()
    assert sub["id"] and again["created"] == 0
    assert len(client.get(f"/invoices?subscription_id={sub['id']}", headers=world["staff"]).json()) == 1
    # generating one by hand when nothing is due is refused too
    assert client.post(f"/invoices/generate/{sub['id']}", headers=world["staff"]).status_code == 409


def test_next_periods_are_billed_when_due_and_not_skipped(client, world):
    sub = new_active_sub(client, world)
    client.post("/billing/run", json={}, headers=world["staff"])
    # jump ahead ~2.5 months: both missed periods are created, none skipped, none doubled
    run = client.post("/billing/run", json={"as_of": str(TODAY + timedelta(days=75))}, headers=world["staff"]).json()
    invs = client.get(f"/invoices?subscription_id={sub['id']}&limit=50", headers=world["staff"]).json()
    starts = sorted(i["period_start"] for i in invs)
    assert len(invs) == 3 and len(set(starts)) == 3
    assert starts[0] == str(TODAY)


def test_invoice_workflow_and_permissions(client, world):
    sub = new_active_sub(client, world)
    client.post("/billing/run", json={}, headers=world["staff"])
    inv = client.get(f"/invoices?subscription_id={sub['id']}", headers=world["staff"]).json()[0]
    s, c = world["staff"], world["cust"]

    assert client.post(f"/invoices/{inv['id']}/send", headers=s).status_code == 409   # confirm first
    assert client.post(f"/invoices/{inv['id']}/confirm", headers=c).status_code == 403
    assert client.post(f"/invoices/{inv['id']}/confirm", headers=s).json()["status"] == "confirmed"
    assert client.post(f"/invoices/{inv['id']}/confirm", headers=s).status_code == 409  # not twice

    OUTBOX.clear()
    sent = client.post(f"/invoices/{inv['id']}/send", headers=s)
    assert sent.status_code == 200 and OUTBOX[0]["to"] == "inv-cust@example.com"

    html = client.get(f"/invoices/{inv['id']}/print", headers=c)   # customer can print their own
    assert html.status_code == 200 and inv["number"] in html.text

    assert client.post(f"/invoices/{inv['id']}/cancel", headers=s).json()["status"] == "cancelled"
    assert client.post(f"/invoices/{inv['id']}/cancel", headers=s).status_code == 409


def test_customers_see_only_their_own_invoices(client, world):
    client.post("/auth/register", json={"email": "nosy@example.com", "password": PW, "name": "Nosy"})
    nosy = login(client, "nosy@example.com", PW)
    inv = client.get("/invoices?limit=1", headers=world["staff"]).json()[0]
    assert client.get(f"/invoices/{inv['id']}", headers=nosy).status_code == 404
    assert client.get("/invoices", headers=nosy).json() == []
    assert all(i["customer_id"] == world["cid"] for i in client.get("/invoices", headers=world["cust"]).json())


def test_paused_and_closed_subscriptions_are_not_billed(client, world):
    sub = new_active_sub(client, world)
    mv(client, sub["id"], ["paused"], world["staff"])
    client.post("/billing/run", json={}, headers=world["staff"])
    assert client.get(f"/invoices?subscription_id={sub['id']}", headers=world["staff"]).json() == []


def test_plans_that_end_close_on_their_own(client, admin, world):
    auto = client.post("/plans", json={"name": "Short auto", "price": 10, "billing_period": "weekly", "auto_close": True}, headers=admin).json()
    manual = client.post("/plans", json={"name": "Short manual", "price": 10, "billing_period": "weekly", "auto_close": False}, headers=admin).json()
    expiry = TODAY + timedelta(days=10)
    a = new_active_sub(client, world, plan=auto, expiry=expiry)
    m = new_active_sub(client, world, plan=manual, expiry=expiry)
    later = {"as_of": str(TODAY + timedelta(days=30))}
    run = client.post("/billing/run", json=later, headers=world["staff"]).json()
    assert run["closed_subscriptions"] >= 1
    assert client.get(f"/subscriptions/{a['id']}", headers=world["staff"]).json()["status"] == "closed"
    assert client.get(f"/subscriptions/{m['id']}", headers=world["staff"]).json()["status"] == "active"
    # the final periods up to expiry were still billed before closing, and none after it
    last = max(i["period_start"] for i in client.get(f"/invoices?subscription_id={a['id']}", headers=world["staff"]).json())
    assert last <= str(expiry)


def test_hundreds_due_at_once(client, admin, world):
    plan = client.post("/plans", json={"name": "Bulk", "price": 5, "billing_period": "monthly"}, headers=admin).json()
    client.post("/auth/register", json={"email": "bulk@example.com", "password": PW, "name": "Bulk"})
    bulk_id = client.get("/auth/me", headers=login(client, "bulk@example.com", PW)).json()["id"]
    subs = [new_active_sub(client, world, cid=bulk_id, plan=plan, qty=1) for _ in range(120)]
    t0 = time.perf_counter()
    run = client.post("/billing/run", json={}, headers=world["staff"]).json()
    elapsed = time.perf_counter() - t0
    mine = client.get(f"/invoices?customer_id={bulk_id}&limit=200", headers=world["staff"]).json()
    assert len(mine) == 120 and len({i["subscription_id"] for i in mine}) == 120
    assert run["created"] >= 120 and elapsed < 10, elapsed
    assert client.post("/billing/run", json={}, headers=world["staff"]).json()["created"] == 0
