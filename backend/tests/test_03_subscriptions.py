"""Scene 3: turning a quote into a subscription."""
from datetime import date, timedelta

import pytest

from .conftest import login

PW = "Str0ng!Pass"
TODAY = date.today()


def make_customer(client, email):
    r = client.post("/auth/register", json={"email": email, "password": PW, "name": email.split("@")[0]})
    return r.json()["id"], login(client, email, PW)


@pytest.fixture(scope="module")
def world(client, admin):
    tax = client.post("/taxes", json={"name": "GST 18%", "rate_percent": 18}, headers=admin).json()
    prod = client.post("/products", json={
        "name": "Seat License", "type": "software", "sales_price": 1000, "cost_price": 300,
        "variants": [{"attribute": "Brand", "value": "Odoo", "extra_price": 560}],
    }, headers=admin).json()
    plan = client.post("/plans", json={
        "name": "Team Monthly", "price": 100, "billing_period": "monthly", "min_quantity": 5,
    }, headers=admin).json()
    tpl = client.post("/quotation-templates", json={
        "name": "Standard 5-seat offer", "plan_id": plan["id"], "validity_days": 14,
        "lines": [{"product_id": prod["id"], "variant_id": prod["variants"][0]["id"], "quantity": 5, "tax_id": tax["id"]}],
    }, headers=admin)
    assert tpl.status_code == 201, tpl.text
    cid, chead = make_customer(client, "bigco@example.com")
    client.post("/users/staff", json={"email": "rep@example.com", "password": PW, "name": "Rep"}, headers=admin)
    return {"tax": tax, "prod": prod, "plan": plan, "tpl": tpl.json(), "cid": cid, "chead": chead,
            "staff": login(client, "rep@example.com", PW)}


def from_template(client, w, head=None, **extra):
    body = {"customer_id": w["cid"], "start_date": str(TODAY), **extra}
    return client.post(f"/subscriptions/from-template/{w['tpl']['id']}", json=body, headers=head or w["staff"])


def move(client, sub_id, to, head):
    return client.post(f"/subscriptions/{sub_id}/transition", json={"to": to}, headers=head)


def test_template_gives_priced_lines_and_validity(client, world):
    r = from_template(client, world)
    assert r.status_code == 201, r.text
    sub = r.json()
    assert sub["number"].startswith("SUB-") and sub["status"] == "draft"
    assert sub["quotation_valid_until"] == str(TODAY + timedelta(days=14))
    line = sub["lines"][0]
    assert line["unit_price"] == 1560  # 1000 + 560 for the Odoo variant
    assert line["amount"] == 7800 and line["quantity"] == 5 and line["tax_rate"] == 18
    assert line["variant_label"] == "Brand: Odoo"


def test_unique_numbers_and_minimum_quantity(client, world):
    a, b = from_template(client, world).json(), from_template(client, world).json()
    assert a["number"] != b["number"]
    body = {"customer_id": world["cid"], "plan_id": world["plan"]["id"], "start_date": str(TODAY),
            "lines": [{"product_id": world["prod"]["id"], "quantity": 2}]}
    r = client.post("/subscriptions", json=body, headers=world["staff"])
    assert r.status_code == 422 and "minimum quantity" in r.text


def test_lifecycle_order_is_enforced(client, world):
    sub = from_template(client, world).json()
    s = world["staff"]
    assert move(client, sub["id"], "active", s).status_code == 409      # can't skip steps
    assert move(client, sub["id"], "quotation", s).json()["status"] == "quotation"
    assert move(client, sub["id"], "confirmed", s).json()["status"] == "confirmed"
    active = move(client, sub["id"], "active", s).json()
    assert active["status"] == "active" and active["next_invoice_date"] == str(TODAY)
    assert move(client, sub["id"], "closed", s).json()["status"] == "closed"
    assert move(client, sub["id"], "active", s).status_code == 409      # closed is final


def test_lines_editable_only_before_confirmation(client, world):
    sub = from_template(client, world).json()
    add = {"product_id": world["prod"]["id"], "quantity": 5}
    assert client.post(f"/subscriptions/{sub['id']}/lines", json=add, headers=world["staff"]).status_code == 201
    move(client, sub["id"], "quotation", world["staff"])
    move(client, sub["id"], "confirmed", world["staff"])
    assert client.post(f"/subscriptions/{sub['id']}/lines", json=add, headers=world["staff"]).status_code == 409


def test_customer_sees_only_their_own(client, world):
    sub = from_template(client, world).json()
    _, other = make_customer(client, "other-co@example.com")
    assert client.get(f"/subscriptions/{sub['id']}", headers=world["chead"]).status_code == 200
    assert client.get(f"/subscriptions/{sub['id']}", headers=other).status_code == 404
    assert client.get("/subscriptions", headers=other).json() == []
    assert all(s["customer_id"] == world["cid"] for s in client.get("/subscriptions", headers=world["chead"]).json())
    # customers can't create subscriptions or use templates
    assert from_template(client, world, head=world["chead"]).status_code == 403
    assert client.get("/quotation-templates", headers=world["chead"]).status_code == 403


def test_customer_self_service_follows_plan_rules(client, admin, world):
    def active_sub(plan_body):
        plan = client.post("/plans", json=plan_body, headers=admin).json()
        body = {"customer_id": world["cid"], "plan_id": plan["id"], "start_date": str(TODAY),
                "expiry_date": str(TODAY + timedelta(days=365)),
                "lines": [{"product_id": world["prod"]["id"], "quantity": 1}]}
        sub = client.post("/subscriptions", json=body, headers=world["staff"]).json()
        for to in ("quotation", "confirmed", "active"):
            move(client, sub["id"], to, world["staff"])
        return sub

    locked = active_sub({"name": "Locked", "price": 10, "billing_period": "monthly",
                         "allow_pause": False, "allow_early_close": False})
    assert move(client, locked["id"], "paused", world["chead"]).status_code == 409
    assert move(client, locked["id"], "closed", world["chead"]).status_code == 409
    assert client.post(f"/subscriptions/{locked['id']}/renew", headers=world["chead"]).status_code == 200

    flexible = active_sub({"name": "Flexible", "price": 10, "billing_period": "monthly"})
    assert move(client, flexible["id"], "paused", world["chead"]).json()["status"] == "paused"
    assert move(client, flexible["id"], "active", world["chead"]).json()["status"] == "active"
    # customers may not drive the sales steps
    assert move(client, flexible["id"], "confirmed", world["chead"]).status_code in (403, 409)

    no_renew = active_sub({"name": "Fixed", "price": 10, "billing_period": "monthly", "allow_renew": False})
    assert client.post(f"/subscriptions/{no_renew['id']}/renew", headers=world["chead"]).status_code == 409


def test_plan_availability_window(client, admin, world):
    plan = client.post("/plans", json={"name": "Past", "price": 1, "billing_period": "monthly",
                                       "start_date": "2020-01-01", "end_date": "2020-12-31"}, headers=admin).json()
    body = {"customer_id": world["cid"], "plan_id": plan["id"], "start_date": str(TODAY),
            "lines": [{"product_id": world["prod"]["id"], "quantity": 1}]}
    r = client.post("/subscriptions", json=body, headers=world["staff"])
    assert r.status_code == 422 and "not available" in r.text
