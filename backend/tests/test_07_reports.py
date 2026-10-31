"""Scene 7: the finance lead, at the end of the month."""
from datetime import date, timedelta

import pytest

from .conftest import login

PW = "Str0ng!Pass"
TODAY = date.today()


def mv(client, sid, head, steps=("quotation", "confirmed", "active")):
    for to in steps:
        assert client.post(f"/subscriptions/{sid}/transition", json={"to": to}, headers=head).status_code == 200


@pytest.fixture(scope="module")
def w(client, admin):
    client.post("/users/staff", json={"email": "fin-lead@example.com", "password": PW, "name": "Fin"}, headers=admin)
    client.post("/auth/register", json={"email": "fin-cust@example.com", "password": PW, "name": "Fin Customer"})
    cust = login(client, "fin-cust@example.com", PW)
    cid = client.get("/auth/me", headers=cust).json()["id"]
    tax = client.post("/taxes", json={"name": "GST 18%", "rate_percent": 18}, headers=admin).json()
    monthly = client.post("/plans", json={"name": "Rep monthly", "price": 100, "billing_period": "monthly"}, headers=admin).json()
    yearly = client.post("/plans", json={"name": "Rep yearly", "price": 1200, "billing_period": "yearly"}, headers=admin).json()
    p1560 = client.post("/products", json={"name": "Rep Prod", "type": "software", "sales_price": 1560}, headers=admin).json()
    p1200 = client.post("/products", json={"name": "Rep Prod Y", "type": "software", "sales_price": 1200}, headers=admin).json()
    return {"admin": admin, "cust": cust, "cid": cid, "tax": tax, "monthly": monthly, "yearly": yearly,
            "p1560": p1560, "p1200": p1200, "staff": login(client, "fin-lead@example.com", PW)}


def make_sub(client, w, plan, prod, qty, start, activate=True):
    body = {"customer_id": w["cid"], "plan_id": plan["id"], "start_date": str(start), "payment_terms_days": 15,
            "lines": [{"product_id": prod["id"], "quantity": qty, "tax_id": w["tax"]["id"]}]}
    sub = client.post("/subscriptions", json=body, headers=w["staff"]).json()
    if activate:
        mv(client, sub["id"], w["staff"])
    return sub


def inv_of(client, w, sub):
    return client.get(f"/invoices?subscription_id={sub['id']}", headers=w["staff"]).json()[0]


@pytest.fixture(scope="module")
def books(client, w):
    """B is billed 20 days ago (so overdue); A and C today; D is yearly; E is paused."""
    b = make_sub(client, w, w["monthly"], w["p1560"], 5, TODAY - timedelta(days=20))
    client.post("/billing/run", json={"as_of": str(TODAY - timedelta(days=20))}, headers=w["staff"])
    a = make_sub(client, w, w["monthly"], w["p1560"], 5, TODAY)
    c = make_sub(client, w, w["monthly"], w["p1560"], 5, TODAY)
    d = make_sub(client, w, w["yearly"], w["p1200"], 1, TODAY)
    e = make_sub(client, w, w["monthly"], w["p1560"], 5, TODAY)
    mv(client, e["id"], w["staff"], ("paused",))
    client.post("/billing/run", json={}, headers=w["staff"])
    inv = {k: inv_of(client, w, s) for k, s in {"a": a, "b": b, "c": c}.items()}
    for i in inv.values():
        client.post(f"/invoices/{i['id']}/confirm", headers=w["staff"])
    # A: paid in full by card.  B: nothing paid (overdue).  C: confirmed, part-paid by cash.
    client.post("/payments", json={"invoice_id": inv["a"]["id"], "method": "card", "amount": 9304}, headers=w["staff"])
    client.post("/payments", json={"invoice_id": inv["c"]["id"], "method": "cash", "amount": 1000}, headers=w["staff"])
    return inv


def test_summary_answers_the_month_end_questions(client, w, books):
    s = client.get(f"/reports/summary?customer_id={w['cid']}", headers=w["staff"])
    assert s.status_code == 200, s.text
    s = s.json()
    assert s["subscriptions"]["active"] == 4 and s["subscriptions"]["by_status"]["paused"] == 1
    # three monthly subs at 100 + 7800 each, plus the yearly sub (1200 + 1200) / 12 = 200
    assert s["subscriptions"]["mrr"] == 23900
    # only confirmed/paid invoices count as billed: A, B, C (the yearly sub's invoice is still a draft)
    assert s["invoices"]["invoiced_total"] == 9304 * 3
    assert s["invoices"]["by_status"]["draft"] == 1
    assert s["payments"]["collected"] == 10304 and s["payments"]["by_method"] == {"card": 9304, "cash": 1000}
    assert s["receivables"]["outstanding"] == 9304 + 8304  # B in full + the rest of C
    assert s["receivables"]["overdue_count"] == 1 and s["receivables"]["overdue_amount"] == 9304


def test_summary_filters(client, w, books):
    base = f"/reports/summary?customer_id={w['cid']}"
    nothing = client.get(f"{base}&date_from={TODAY + timedelta(days=1)}", headers=w["staff"]).json()
    assert nothing["payments"]["collected"] == 0 and nothing["invoices"]["invoiced_total"] == 0
    monthly_only = client.get(f"{base}&plan_id={w['monthly']['id']}", headers=w["staff"]).json()
    assert monthly_only["subscriptions"]["mrr"] == 23700
    stranger = client.get("/reports/summary?customer_id=999999", headers=w["staff"]).json()
    assert stranger["subscriptions"]["active"] == 0 and stranger["receivables"]["outstanding"] == 0


def test_overdue_chase_list(client, w, books):
    rows = client.get(f"/reports/overdue?customer_id={w['cid']}", headers=w["staff"]).json()
    assert [r["invoice_id"] for r in rows] == [books["b"]["id"]]
    r = rows[0]
    assert r["days_overdue"] == 5 and r["customer_email"] == "fin-cust@example.com" and r["amount_due"] == 9304
    assert client.get(f"/reports/overdue?customer_id={w['cid']}&min_days_overdue=30", headers=w["staff"]).json() == []


def test_monthly_series_for_charts(client, w, books):
    rows = client.get("/reports/monthly?months=3", headers=w["staff"]).json()
    assert len(rows) == 3 and rows[-1]["month"] == TODAY.strftime("%Y-%m")
    assert rows[-1]["collected"] >= 10304 and rows[-1]["invoiced"] > 0


def test_reports_are_staff_only(client, w, books):
    for path in ("/reports/summary", "/reports/overdue", "/reports/monthly"):
        assert client.get(path, headers=w["cust"]).status_code == 403
        assert client.get(path).status_code == 401
