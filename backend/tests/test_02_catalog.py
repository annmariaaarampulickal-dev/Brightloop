"""Scene 2: launching a new plan."""
from .conftest import login

PW = "Str0ng!Pass"


def customer_headers(client, email="catalog-cust@example.com"):
    client.post("/auth/register", json={"email": email, "password": PW, "name": "C"})
    return login(client, email, PW)


def test_admin_creates_product_with_variants(client, admin):
    body = {
        "name": "Brightloop CRM",
        "type": "software",
        "sales_price": 1000,
        "cost_price": 400,
        "notes": "Flagship product",
        "variants": [
            {"attribute": "Brand", "value": "Odoo", "extra_price": 560},
            {"attribute": "Brand", "value": "Custom", "extra_price": 0},
        ],
    }
    r = client.post("/products", json=body, headers=admin)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["sales_price"] == 1000 and len(p["variants"]) == 2
    assert p["variants"][0]["extra_price"] == 560  # choosing Odoo adds 560

    # add and remove a variant later
    v = client.post(f"/products/{p['id']}/variants", json={"attribute": "Size", "value": "XL", "extra_price": 25}, headers=admin)
    assert v.status_code == 201
    assert client.delete(f"/products/{p['id']}/variants/{v.json()['id']}", headers=admin).status_code == 204
    assert len(client.get(f"/products/{p['id']}", headers=admin).json()["variants"]) == 2


def test_only_admin_writes_catalog(client, admin):
    cust = customer_headers(client)
    body = {"name": "X", "type": "software", "sales_price": 1}
    assert client.post("/products", json=body, headers=cust).status_code == 403
    assert client.post("/plans", json={"name": "P", "price": 1, "billing_period": "monthly"}, headers=cust).status_code == 403
    # but any logged-in user can browse
    assert client.get("/products", headers=cust).status_code == 200
    assert client.get("/plans", headers=cust).status_code == 200


def test_plan_periods_and_validation(client, admin):
    for period in ["daily", "weekly", "monthly", "yearly"]:
        r = client.post("/plans", json={"name": f"{period} plan", "price": 99, "billing_period": period}, headers=admin)
        assert r.status_code == 201, r.text
    assert client.post("/plans", json={"name": "bad", "price": 1, "billing_period": "hourly"}, headers=admin).status_code == 422
    assert client.post("/plans", json={"name": "bad", "price": 1, "billing_period": "monthly", "min_quantity": 0}, headers=admin).status_code == 422
    bad_dates = {"name": "bad", "price": 1, "billing_period": "monthly", "start_date": "2026-12-01", "end_date": "2026-01-01"}
    assert client.post("/plans", json=bad_dates, headers=admin).status_code == 422


def test_plan_lifecycle_options_and_availability(client, admin):
    body = {
        "name": "Seasonal Yearly",
        "price": 5000,
        "billing_period": "yearly",
        "min_quantity": 5,
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "auto_close": True,
        "allow_early_close": False,
        "allow_pause": False,
        "allow_renew": True,
    }
    plan = client.post("/plans", json=body, headers=admin).json()
    assert plan["auto_close"] is True and plan["allow_pause"] is False and plan["allow_early_close"] is False

    names = lambda d: [p["name"] for p in client.get(f"/plans?available_on={d}", headers=admin).json()]
    assert "Seasonal Yearly" in names("2026-06-01")
    assert "Seasonal Yearly" not in names("2027-02-01")

    upd = client.patch(f"/plans/{plan['id']}", json={"allow_pause": True, "price": 4500}, headers=admin)
    assert upd.status_code == 200 and upd.json()["allow_pause"] is True and upd.json()["price"] == 4500
