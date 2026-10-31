"""Demo data so the dashboard and the portal have something to show.

    python -m app.seed

Safe to run more than once: it stops if the demo customers already exist.
Everything goes through the real API, so the demo data obeys the same rules as real data.
"""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from .main import app

PW = "Demo@12345"
TODAY = date.today()


def main() -> None:
    with TestClient(app) as c:  # starts the app (creates tables + the admin)
        from . import config

        def ok(r):
            assert r.status_code < 300, (r.request.url, r.status_code, r.text)
            return r.json()

        token = ok(c.post("/auth/login", json={"email": config.ADMIN_EMAIL, "password": config.ADMIN_PASSWORD}))
        admin = {"Authorization": f"Bearer {token['access_token']}"}

        if c.get("/users?q=acme", headers=admin).json():
            print("Demo data already present - nothing to do.")
            return

        ok(c.post("/users/staff", json={"email": "staff@brightloop.com", "password": PW, "name": "Sam Staff"}, headers=admin))
        staff = {"Authorization": "Bearer " + ok(c.post("/auth/login", json={"email": "staff@brightloop.com", "password": PW}))["access_token"]}

        customers = {}
        for key, name in (("acme", "Acme Retail"), ("globex", "Globex Corp"), ("initech", "Initech Ltd")):
            customers[key] = ok(c.post("/auth/register", json={"email": f"{key}@example.com", "password": PW, "name": name}))["id"]

        tax = ok(c.post("/taxes", json={"name": "GST 18%", "rate_percent": 18}, headers=admin))
        crm = ok(c.post("/products", json={
            "name": "Brightloop CRM", "type": "software", "sales_price": 1000, "cost_price": 400,
            "notes": "Flagship CRM seat",
            "variants": [{"attribute": "Brand", "value": "Odoo", "extra_price": 560},
                         {"attribute": "Brand", "value": "Standard", "extra_price": 0}]}, headers=admin))
        addon = ok(c.post("/products", json={"name": "Analytics add-on", "type": "add-on", "sales_price": 250, "cost_price": 60}, headers=admin))
        monthly = ok(c.post("/plans", json={"name": "Team Monthly", "price": 100, "billing_period": "monthly", "min_quantity": 1}, headers=admin))
        yearly = ok(c.post("/plans", json={"name": "Business Yearly", "price": 1200, "billing_period": "yearly", "min_quantity": 5,
                                           "auto_close": True, "allow_pause": False}, headers=admin))
        tpl = ok(c.post("/quotation-templates", json={
            "name": "Standard 5-seat offer", "plan_id": monthly["id"], "validity_days": 14,
            "lines": [{"product_id": crm["id"], "variant_id": crm["variants"][0]["id"], "quantity": 5, "tax_id": tax["id"]}]}, headers=admin))
        ok(c.post("/discounts", json={"name": "Volume 10%", "kind": "percent", "value": 10, "min_quantity": 5,
                                      "start_date": str(TODAY - timedelta(days=90)), "end_date": str(TODAY + timedelta(days=90))}, headers=admin))

        def activate(sub_id):
            for to in ("quotation", "confirmed", "active"):
                ok(c.post(f"/subscriptions/{sub_id}/transition", json={"to": to}, headers=staff))

        # An older subscription, billed 20 days ago and never paid -> shows up as overdue.
        old = ok(c.post(f"/subscriptions/from-template/{tpl['id']}", json={
            "customer_id": customers["initech"], "start_date": str(TODAY - timedelta(days=20)), "payment_terms_days": 15}, headers=staff))
        activate(old["id"])
        ok(c.post("/billing/run", json={"as_of": str(TODAY - timedelta(days=20)), "auto_confirm": True}, headers=staff))

        # Current subscriptions.
        s1 = ok(c.post(f"/subscriptions/from-template/{tpl['id']}", json={
            "customer_id": customers["acme"], "start_date": str(TODAY), "payment_terms_days": 30}, headers=staff))
        s2 = ok(c.post("/subscriptions", json={
            "customer_id": customers["globex"], "plan_id": yearly["id"], "start_date": str(TODAY), "payment_terms_days": 30,
            "lines": [{"product_id": crm["id"], "quantity": 10, "tax_id": tax["id"]},
                      {"product_id": addon["id"], "quantity": 10, "tax_id": tax["id"]}]}, headers=staff))
        s3 = ok(c.post("/subscriptions", json={
            "customer_id": customers["acme"], "plan_id": monthly["id"], "start_date": str(TODAY), "payment_terms_days": 30,
            "lines": [{"product_id": addon["id"], "quantity": 3, "tax_id": tax["id"]}]}, headers=staff))
        for s in (s1, s2, s3):
            activate(s["id"])
        ok(c.post(f"/subscriptions/{s3['id']}/transition", json={"to": "paused"}, headers=staff))
        # one more still in the sales pipeline
        ok(c.post(f"/subscriptions/from-template/{tpl['id']}", json={"customer_id": customers["globex"], "start_date": str(TODAY + timedelta(days=7))}, headers=staff))

        ok(c.post("/billing/run", json={"auto_confirm": True}, headers=staff))

        # Payments: Acme pays in full by card, Globex pays half by bank transfer.
        invoices = ok(c.get("/invoices?limit=200", headers=staff))
        for inv in invoices:
            if inv["status"] != "confirmed":
                continue
            if inv["customer_id"] == customers["acme"]:
                ok(c.post("/payments", json={"invoice_id": inv["id"], "method": "card", "amount": inv["total"], "note": "Paid online"}, headers=staff))
            elif inv["customer_id"] == customers["globex"]:
                ok(c.post("/payments", json={"invoice_id": inv["id"], "method": "bank_transfer", "amount": round(inv["total"] / 2, 2),
                                             "note": "First instalment"}, headers=staff))

    print(f"""
Demo data created.

  admin     {config.ADMIN_EMAIL} / {config.ADMIN_PASSWORD}
  staff     staff@brightloop.com / {PW}
  customer  acme@example.com / {PW}      (also globex@ and initech@)

Open http://localhost:8000/docs, click Authorize, and log in with any of the above.
Try GET /reports/summary and GET /reports/overdue as admin or staff.
""")


if __name__ == "__main__":
    main()
