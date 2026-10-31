# Brightloop Subscription Management

One system for the whole life of a subscription business: products and plans, quotations,
subscriptions, automatic invoicing, discounts, payments and revenue reporting.
FastAPI + SQLAlchemy, PostgreSQL in Docker (SQLite for quick local runs and tests).

## Run it

**Docker (PostgreSQL):**

```bash
docker compose up --build
docker compose exec api python -m app.seed      # optional demo data
```

**Local (SQLite, no Docker):**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
python -m app.seed                               # optional demo data
```

Open **http://localhost:8000/docs**, click **Authorize** and log in (username = email).

| Role | Login | Password |
|---|---|---|
| Admin (created on first start) | `admin@brightloop.com` | `Admin@12345` |
| Staff (seed data) | `staff@brightloop.com` | `Demo@12345` |
| Customer (seed data) | `acme@example.com` (also `globex@`, `initech@`) | `Demo@12345` |

Change `ADMIN_EMAIL`, `ADMIN_PASSWORD` and `SECRET_KEY` before any real use (see `app/config.py`).

## Tests

```bash
pytest -q          # 54 tests, ~40 s
pytest -q -s tests/test_08_performance.py    # prints timings
```

Tests are organised in the same order as the story, one file per scene.

## How each scene is covered

| Scene | What it does | Main endpoints |
|---|---|---|
| **1. A new customer signs up** | Sign-up with unique email (case-insensitive) and the password rule (more than 8 chars, upper, lower, special). Reset link by email, single-use, 30 minutes. Roles: admin / staff / customer. Only the admin adds staff. | `POST /auth/register`, `/auth/login`, `/auth/forgot-password`, `/auth/reset-password`, `POST /users/staff` |
| **2. Launching a new plan** | Products (name, type, sales/cost price, notes) with variants that add to the price (Odoo brand = +560). Plans: price, daily/weekly/monthly/yearly, minimum quantity, availability dates, and per-plan switches for auto-close, early close, pause and renew. | `/products`, `/products/{id}/variants`, `/plans` |
| **3. Quote to subscription** | Quotation templates (plan + lines + validity days). Subscriptions get a number (`SUB-000001`), customer, plan, dates, payment terms and priced lines. Status Draft → Quotation → Confirmed → Active → Closed (plus Paused). | `/quotation-templates`, `/subscriptions`, `/subscriptions/from-template/{id}`, `/subscriptions/{id}/transition`, `/renew` |
| **4. Billing day** | One call creates every due invoice with customer, lines, plan fee, tax and totals. Draft → Confirmed → Paid; confirm, cancel, send (email) and print. Nothing is billed twice or skipped. | `POST /billing/run`, `/invoices`, `/invoices/{id}/confirm`, `/cancel`, `/send`, `/print` |
| **5. Better price** | Admin-only discount rules: fixed or percent, minimum purchase/quantity, dates, usage limit, scoped to a product, a subscription or everything. Applied automatically to the next invoice; stops on expiry or when used up. | `/discounts` |
| **6. The money comes in** | Payments with method, amount, date and note against an invoice; partial payments allowed; invoice turns Paid when covered. Filters for outstanding and overdue. | `POST /payments`, `/payments`, `/invoices?outstanding=true`, `?overdue=true` |
| **7. Finance lead** | Active subscriptions, MRR, invoiced, collected (by method), outstanding and overdue, with date/customer/plan filters; a chase list and a monthly series for charts. | `/reports/summary`, `/reports/overdue`, `/reports/monthly` |

### Who can do what

- **Admin**: everything, including products, plans, taxes, templates, discounts and adding staff.
- **Staff**: customers, subscriptions, billing, invoices, payments and reports. Read-only on the catalog and discounts.
- **Customer**: only their own subscriptions, invoices and payments; can pause, resume or close their own active subscription if the plan allows it, and print their invoices.

## Why billing is safe

- A **unique constraint** on `(subscription, period_start)` makes the database itself refuse a second invoice for the same period; the billing run also checks first and uses a savepoint per invoice, so one conflict never stops the rest.
- Each subscription keeps a billing cursor (`billing_anchor` + `cycles_billed`), so periods are never skipped, a missed run catches up (max 12 periods per run), and a monthly subscription started on the 31st bills on the 30th/28th and returns to the 31st.
- Pausing stops billing and resuming restarts the cycle from the day of resuming, so paused time is never billed.
- Payments take a row lock on the invoice and refuse overpayment.

## Money rules and assumptions

Where the brief left room, these are the choices made (all small, isolated changes if you want otherwise):

- **Plan price** is a recurring fee that appears as its own invoice line ("Plan fee"), untaxed. Product lines are billed every period on top. Set the plan price to 0 for product-only billing.
- **Tax** is a per-line choice from the admin's tax list; invoices store the rate used, so later tax changes don't rewrite history.
- **Discounts** reduce the base they apply to and remove the tax on the discounted amount. Several can stack but never push an invoice below zero. A fully discounted invoice settles itself on confirmation. Cancelling an invoice gives its discount uses back.
- **Revenue** in reports means payments received; **invoiced** counts confirmed and paid invoices (drafts and cancelled don't count). MRR is the pre-tax, pre-discount recurring value of active subscriptions, normalised to a month.
- A cancelled invoice's period is **not re-billed automatically**, by design, so "nothing billed twice" holds; create a corrective invoice manually if needed.
- Anyone can sign up as a **customer**; staff and admins can only be created by the admin.
- Reset emails are logged and kept in an in-memory outbox unless `SMTP_HOST` is set.

## Performance

`tests/test_08_performance.py` loads 5,000 subscriptions and about 10,000 invoices and times every list and report endpoint: all respond in well under 100 ms on SQLite (limit: 2 s). All filtered columns are indexed (status + due date, status + next invoice date, customer, subscription, payment date) and reports use SQL aggregates, not Python loops. The billing run over ~4,500 due subscriptions takes about 10 s. It's a batch job, not a page.

## Project layout

```
app/
  main.py            app, startup (tables + first admin)
  models.py          all tables, grouped by scene
  schemas.py         request/response models and validation
  security.py        password rules, hashing, JWT, reset tokens
  deps.py            auth + role guards (Admin, Staff, CurrentUser)
  services/          periods.py (date maths), billing.py (the billing engine)
  routers/           auth, users, catalog, subscriptions, discounts, billing, payments, reports
  seed.py            demo data
tests/               one file per scene + performance
```

## Not included yet (good next steps)

- A React dashboard/portal on top of this API (the Swagger UI works as a demo front end today).
- Alembic migrations (tables are created on start-up).
- A scheduler (cron / Celery beat) calling `POST /billing/run` every night, and a nightly overdue-reminder email.
- Voiding or refunding a recorded payment, and credit notes.
- Rate limiting on login and password-reset endpoints.
- Not run here: the Docker/PostgreSQL path (tests and the demo ran on SQLite). The code uses only portable SQLAlchemy constructs, but give `docker compose up` a try early.
