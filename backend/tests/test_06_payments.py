"""Scene 6: the money comes in."""
from datetime import date, timedelta

import pytest

from .conftest import login

PW = "Str0ng!Pass"
TODAY = date.today()


def mv(client, sid, head):
    for to in ("quotation", "confirmed", "active"):
        assert client.post(f"/subscriptions/{sid}/transition", json={"to": to}, headers=head).status_code == 200


@pytest.fixture(scope="module")
def w(client, admin):
    client.post("/users/staff", json={"email": "pay-rep@example.com", "password": PW, "name": "Pat"}, headers=admin)
    client.post("/auth/register", json={"email": "payer@example.com", "password": PW, "name": "Payer"})
    cust = login(client, "payer@example.com", PW)
    cid = client.get("/auth/me", headers=cust).json()["id"]
    tax = client.post("/taxes", json={"name": "GST 18%", "rate_percent": 18}, headers=admin).json()
    plan = client.post("/plans", json={"name": "Pay plan", "price": 100, "billing_period": "monthly"}, headers=admin).json()
    prod = client.post("/products", json={"name": "Pay Prod", "type": "software", "sales_price": 1560}, headers=admin).json()
    return {"admin": admin, "cust": cust, "cid": cid, "tax": tax, "plan": plan, "prod": prod,
            "staff": login(client, "pay-rep@example.com", PW)}


def billed_invoice(client, w, start=None, as_of=None, confirm=True):
    body = {"customer_id": w["cid"], "plan_id": w["plan"]["id"], "start_date": str(start or TODAY), "payment_terms_days": 15,
            "lines": [{"product_id": w["prod"]["id"], "quantity": 5, "tax_id": w["tax"]["id"]}]}
    sub = client.post("/subscriptions", json=body, headers=w["staff"]).json()
    mv(client, sub["id"], w["staff"])
    client.post("/billing/run", json={"as_of": str(as_of or TODAY)}, headers=w["staff"])
    inv = client.get(f"/invoices?subscription_id={sub['id']}", headers=w["staff"]).json()[0]
    if confirm:
        inv = client.post(f"/invoices/{inv['id']}/confirm", headers=w["staff"]).json()
    return inv


def pay(client, w, inv, amount, method="cash", head=None, **kw):
    return client.post("/payments", json={"invoice_id": inv["id"], "method": method, "amount": amount, **kw},
                       headers=head or w["staff"])


def test_partial_then_full_payment_marks_invoice_paid(client, w):
    inv = billed_invoice(client, w)
    assert inv["total"] == 9304 and inv["amount_due"] == 9304
    r = pay(client, w, inv, 4000, "cash", note="Deposit at the counter", payment_date=str(TODAY))
    assert r.status_code == 201 and r.json()["note"] == "Deposit at the counter"
    mid = client.get(f"/invoices/{inv['id']}", headers=w["staff"]).json()
    assert mid["status"] == "confirmed" and mid["amount_paid"] == 4000 and mid["amount_due"] == 5304
    # shows up while outstanding, gone once paid
    out_ids = [i["id"] for i in client.get("/invoices?outstanding=true&limit=200", headers=w["staff"]).json()]
    assert inv["id"] in out_ids

    assert pay(client, w, inv, 5304, "upi").status_code == 201
    done = client.get(f"/invoices/{inv['id']}", headers=w["staff"]).json()
    assert done["status"] == "paid" and done["amount_due"] == 0
    out_ids = [i["id"] for i in client.get("/invoices?outstanding=true&limit=200", headers=w["staff"]).json()]
    assert inv["id"] not in out_ids
    methods = {p["method"] for p in client.get(f"/payments?invoice_id={inv['id']}", headers=w["staff"]).json()}
    assert methods == {"cash", "upi"}


def test_payment_guards(client, w):
    draft = billed_invoice(client, w, confirm=False)
    assert pay(client, w, draft, 10).status_code == 409                       # confirm first
    inv = client.post(f"/invoices/{draft['id']}/confirm", headers=w["staff"]).json()
    assert pay(client, w, inv, 99999).status_code == 422                      # more than owed
    assert pay(client, w, inv, 0).status_code == 422
    assert pay(client, w, inv, -5).status_code == 422
    assert client.post("/payments", json={"invoice_id": inv["id"], "method": "bitcoin", "amount": 5}, headers=w["staff"]).status_code == 422
    assert pay(client, w, inv, 10, head=w["cust"]).status_code == 403          # customers can't record payments
    assert pay(client, w, {"id": 999999}, 10).status_code == 404
    assert pay(client, w, inv, inv["total"]).status_code == 201
    assert pay(client, w, inv, 1).status_code == 409                          # already paid
    cancelled = billed_invoice(client, w)
    client.post(f"/invoices/{cancelled['id']}/cancel", headers=w["staff"])
    assert pay(client, w, cancelled, 1).status_code == 409
    paid_one = billed_invoice(client, w)
    pay(client, w, paid_one, 10)
    assert client.post(f"/invoices/{paid_one['id']}/cancel", headers=w["staff"]).status_code == 409  # has payments


def test_overdue_invoices_can_be_chased(client, w):
    # billed 30 days ago with 15-day terms -> due 15 days ago
    old = billed_invoice(client, w, start=TODAY - timedelta(days=30), as_of=TODAY - timedelta(days=30))
    fresh = billed_invoice(client, w)
    overdue = {i["id"]: i for i in client.get("/invoices?overdue=true&limit=200", headers=w["staff"]).json()}
    assert old["id"] in overdue and overdue[old["id"]]["is_overdue"] is True
    assert fresh["id"] not in overdue
    pay(client, w, old, old["total"])
    assert old["id"] not in [i["id"] for i in client.get("/invoices?overdue=true&limit=200", headers=w["staff"]).json()]


def test_customer_sees_only_own_payments(client, w):
    client.post("/auth/register", json={"email": "snoop@example.com", "password": PW, "name": "Snoop"})
    snoop = login(client, "snoop@example.com", PW)
    assert client.get("/payments", headers=snoop).json() == []
    mine = {p["id"] for p in client.get("/payments?limit=200", headers=w["cust"]).json()}
    staff_view = {p["id"] for p in client.get(f"/payments?customer_id={w['cid']}&limit=200", headers=w["staff"]).json()}
    assert mine and mine == staff_view
    upi = client.get("/payments?method=upi", headers=w["staff"]).json()
    assert upi and all(p["method"] == "upi" for p in upi)


def test_fully_discounted_invoice_is_settled_on_confirmation(client, w):
    body = {"customer_id": w["cid"], "plan_id": w["plan"]["id"], "start_date": str(TODAY),
            "lines": [{"product_id": w["prod"]["id"], "quantity": 5}]}
    sub = client.post("/subscriptions", json=body, headers=w["staff"]).json()
    mv(client, sub["id"], w["staff"])
    client.post("/discounts", json={"name": "Free month", "kind": "percent", "value": 100, "subscription_id": sub["id"]}, headers=w["admin"])
    client.post("/billing/run", json={}, headers=w["staff"])
    inv = client.get(f"/invoices?subscription_id={sub['id']}", headers=w["staff"]).json()[0]
    assert inv["total"] == 0
    assert client.post(f"/invoices/{inv['id']}/confirm", headers=w["staff"]).json()["status"] == "paid"
