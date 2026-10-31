"""Scene 1: a new customer signs up."""
from app.emailer import OUTBOX

from .conftest import auth, login

GOOD = "Str0ng!Pass"


def register(client, email="shop@example.com", password=GOOD):
    return client.post("/auth/register", json={"email": email, "password": password, "name": "Shop"})


def test_signup_creates_customer(client):
    r = register(client)
    assert r.status_code == 201
    assert r.json()["role"] == "customer"


def test_email_must_be_unique_case_insensitive(client):
    assert register(client, "dupe@example.com").status_code == 201
    assert register(client, "DUPE@example.com").status_code == 409


def test_password_rules(client):
    cases = {
        "Sh0rt!aA": "more than 8",   # exactly 8 chars is not enough
        "nouppercase!1": "uppercase",
        "NOLOWERCASE!1": "lowercase",
        "NoSpecial123": "special",
    }
    for pw, expected in cases.items():
        r = register(client, f"pw{abs(hash(pw))}@example.com", pw)
        assert r.status_code == 422, pw
        assert expected in r.text, (pw, r.text)
    # 9 chars with all three kinds is accepted
    assert register(client, "nine@example.com", "Abcdefg!h").status_code == 201


def test_login_and_wrong_password(client):
    register(client, "login@example.com")
    assert client.post("/auth/login", json={"email": "login@example.com", "password": "Wrong!Pass1"}).status_code == 401
    h = login(client, "login@example.com", GOOD)
    assert client.get("/auth/me", headers=h).json()["email"] == "login@example.com"


def test_roles_and_staff_creation(client, admin):
    register(client, "cust@example.com")
    cust = login(client, "cust@example.com", GOOD)
    staff_body = {"email": "staff@example.com", "password": GOOD, "name": "Sam"}

    # customers and anonymous users cannot add staff; the public sign-up never makes staff
    assert client.post("/users/staff", json=staff_body, headers=cust).status_code == 403
    assert client.post("/users/staff", json=staff_body).status_code == 401

    r = client.post("/users/staff", json=staff_body, headers=admin)
    assert r.status_code == 201 and r.json()["role"] == "staff"

    staff = login(client, "staff@example.com", GOOD)
    # staff cannot add staff, but can list customers; customers cannot list users
    assert client.post("/users/staff", json={**staff_body, "email": "s2@example.com"}, headers=staff).status_code == 403
    assert client.get("/users?role=customer", headers=staff).status_code == 200
    assert client.get("/users", headers=cust).status_code == 403


def test_forgot_and_reset_password(client):
    register(client, "forgot@example.com")
    OUTBOX.clear()

    # unknown email: same response, nothing sent
    r = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200 and not OUTBOX

    r2 = client.post("/auth/forgot-password", json={"email": "forgot@example.com"})
    assert r2.json() == r.json()  # no account enumeration
    assert len(OUTBOX) == 1 and OUTBOX[0]["to"] == "forgot@example.com"
    token = OUTBOX[0]["body"].split("token=")[1].split()[0]

    assert client.post("/auth/reset-password", json={"token": token, "new_password": "weak"}).status_code == 422
    ok = client.post("/auth/reset-password", json={"token": token, "new_password": "N3w!Passw0rd"})
    assert ok.status_code == 200
    # link is single-use
    assert client.post("/auth/reset-password", json={"token": token, "new_password": "An0ther!Pass"}).status_code == 400
    # old password no longer works, new one does
    assert client.post("/auth/login", json={"email": "forgot@example.com", "password": GOOD}).status_code == 401
    login(client, "forgot@example.com", "N3w!Passw0rd")
