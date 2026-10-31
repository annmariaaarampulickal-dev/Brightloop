"""Scene 5: a customer asks for a better price."""
from datetime import date, timedelta

import pytest

from .conftest import login

PW = "Str0ng!Pass"
TODAY = date.today()


def mv(client, sid, head):
    for to in ("quotation", "confirmed", "active"):
        assert client.post(f"/subscriptions/{sid}/transition", json={"to": to}, headers=head).status_code == 200


def register(client, email):
    client.post("/auth/register", json={"email": email, "password": PW, "name": email.split("@")[0]})
    return client.get("/auth/me", headers=login(client, email, PW)).json()["id"]


@pytest.fixture(scope="module")
def w(client, admin):
    client.post("/users/staff", json={"email": "disc-rep@example.com", "password": PW, "name": "Dee"}, headers=admin)
    tax = client.post("/taxes", json={"name": "GST 18%", "rate_percent": 18}, headers=admin).json()
    free_plan = client.post("/plans", json={"name": "Disc plan", "price": 0, "billing_period": "monthly"}, headers=admin).json()
    fee_plan = client.post("/plans", json={"name": "Disc fee plan", "price": 100, "billing_period": "monthly"}, headers=admin).json()
    pa = client.post("/products", json={"name": "Disc Prod A", "type": "software", "sales_price": 1000,
                                        "variants": [{"attribute": "Brand", "value": "Odoo", "extra_price": 560}]}, headers=admin).json()
    pb = client.post("/products", json={"name": "Disc Prod B", "type": "add-on", "sales_price": 500}, headers=admin).json()
    return {"tax": tax, "free": free_plan, "fee": fee_plan, "pa": pa, "pb": pb, "admin": admin,
            "staff": login(client, "disc-rep@example.com", PW)}


def make_sub(client, w, email, plan, lines):
    cid = register(client, email)
    body = {"customer_id": cid, "plan_id": plan["id"], "start_date": str(TODAY),
            "lines": [{**l, "tax_id": w["tax"]["id"]} for l in lines]}
    sub = client.post("/subscriptions", json=body, headers=w["staff"]).json()
    mv(client, sub["id"], w["staff"])
    return sub


def invoices_of(client, w, sub):
    return sorted(client.get(f"/invoices?subscription_id={sub['id']}&limit=50", headers=w["staff"]).json(),
                  key=lambda i: i["period_start"])


def bill(client, w, offset_days=0):
    return client.post("/billing/run", json={"as_of": str(TODAY + timedelta(days=offset_days))}, headers=w["staff"]).json()


def discount(client, w, **kw):
    body = {"name": "Test", "kind": "percent", "value": 10, **kw}
    r = client.post("/discounts", json=body, headers=w["admin"])
    assert r.status_code == 201, r.text
    return r.json()


def test_only_admin_creates_discounts(client, w):
    body = {"name": "Nope", "kind": "percent", "value": 5}
    assert client.post("/discounts", json=body, headers=w["staff"]).status_code == 403
    cust = login(client, "disc-rep@example.com", PW)  # staff can read the list, not write
    assert client.get("/discounts", headers=cust).status_code == 200
    assert client.post("/discounts", json={**body, "kind": "percent", "value": 150}, headers=w["admin"]).status_code == 422
    bad = {**body, "start_date": "2026-05-01", "end_date": "2026-01-01"}
    assert client.post("/discounts", json=bad, headers=w["admin"]).status_code == 422


def test_whole_subscription_percent_discount_appears_on_next_invoice_then_runs_out(client, w):
    sub = make_sub(client, w, "d1@example.com", w["fee"], [{"product_id": w["pa"]["id"], "variant_id": w["pa"]["variants"][0]["id"], "quantity": 5}])
    d = discount(client, w, name="Volume 10%", kind="percent", value=10, min_quantity=5, usage_limit=1, subscription_id=sub["id"])
    bill(client, w)
    first = invoices_of(client, w, sub)[0]
    # base 100 + 7800 = 7900; 10% = 790; tax 1404 less 10% share (140.40) = 1263.60
    assert (first["subtotal"], first["discount_total"], first["tax_total"], first["total"]) == (7900, 790, 1263.6, 8373.6)
    assert first["lines"][-1]["description"] == "Discount - Volume 10%" and first["lines"][-1]["amount"] == -790
    # usage limit of 1: the next period is billed at full price
    bill(client, w, 40)
    second = invoices_of(client, w, sub)[1]
    assert second["discount_total"] == 0 and second["total"] == 9304
    assert client.get(f"/discounts/{d['id']}", headers=w["staff"]).json()["times_used"] == 1


def test_product_specific_fixed_discount_adjusts_tax(client, w):
    sub = make_sub(client, w, "d2@example.com", w["free"], [
        {"product_id": w["pa"]["id"], "quantity": 2}, {"product_id": w["pb"]["id"], "quantity": 3}])
    discount(client, w, name="Add-on deal", kind="fixed", value=200, product_id=w["pb"]["id"], subscription_id=sub["id"])
    bill(client, w)
    inv = invoices_of(client, w, sub)[0]
    # A: 2000 (+360 tax), B: 1500 (+270 tax); 200 off B also removes 36 tax
    assert (inv["subtotal"], inv["discount_total"], inv["tax_total"], inv["total"]) == (3500, 200, 594, 3894)


def test_conditions_and_dates_are_respected(client, w):
    sub = make_sub(client, w, "d3@example.com", w["free"], [{"product_id": w["pa"]["id"], "quantity": 2}])
    discount(client, w, name="Needs 10 seats", min_quantity=10, subscription_id=sub["id"])
    discount(client, w, name="Needs 5000 spend", min_purchase=5000, subscription_id=sub["id"])
    discount(client, w, name="Expired", end_date=str(TODAY - timedelta(days=1)), subscription_id=sub["id"])
    discount(client, w, name="Starts later", start_date=str(TODAY + timedelta(days=5)), subscription_id=sub["id"])
    bill(client, w)
    inv = invoices_of(client, w, sub)[0]
    assert inv["discount_total"] == 0 and inv["total"] == 2360


def test_usage_limit_is_shared_across_customers(client, w):
    prod = client.post("/products", json={"name": "Limited Prod", "type": "software", "sales_price": 100}, headers=w["admin"]).json()
    subs = [make_sub(client, w, f"lim{i}@example.com", w["free"], [{"product_id": prod["id"], "quantity": 1}]) for i in range(3)]
    d = discount(client, w, name="First two only", kind="percent", value=50, product_id=prod["id"], usage_limit=2)
    bill(client, w)
    totals = sorted(invoices_of(client, w, s)[0]["discount_total"] for s in subs)
    assert totals == [0, 50, 50]  # exactly two uses, then it stops by itself
    assert client.get(f"/discounts/{d['id']}", headers=w["staff"]).json()["times_used"] == 2


def test_cancelling_an_invoice_returns_the_use_and_deactivating_stops_it(client, w):
    sub = make_sub(client, w, "d5@example.com", w["free"], [{"product_id": w["pa"]["id"], "quantity": 1}])
    d = discount(client, w, name="Once", usage_limit=1, subscription_id=sub["id"])
    bill(client, w)
    inv = invoices_of(client, w, sub)[0]
    assert inv["discount_total"] == 100
    client.post(f"/invoices/{inv['id']}/cancel", headers=w["staff"])
    assert client.get(f"/discounts/{d['id']}", headers=w["staff"]).json()["times_used"] == 0

    d2 = discount(client, w, name="Switched off", subscription_id=sub["id"])
    assert client.patch(f"/discounts/{d2['id']}", json={"is_active": False}, headers=w["admin"]).status_code == 200
    bill(client, w, 40)
    later = invoices_of(client, w, sub)[-1]
    assert later["lines"][-1]["description"] != "Discount - Switched off"
