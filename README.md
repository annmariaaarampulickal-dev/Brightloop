# Brightloop frontend (React + Vite)

Built against the Brightloop FastAPI backend (`brightloop.zip`).

## Run

```bash
# 1. backend (from the brightloop/ folder)
docker compose up --build            # or: uvicorn app.main:app --reload
python -m app.seed                   # optional demo data (docker: docker compose exec api python -m app.seed)

# 2. frontend (this folder)
npm install
npm run dev                          # http://localhost:3000
```

Port **3000** is deliberate: the backend's `FRONTEND_URL` defaults to `http://localhost:3000`, so the
password-reset email links straight to `/reset-password?token=...` in this app.
Without `SMTP_HOST` the backend only logs the email; copy the link from the API log.

API address is in `.env` (`VITE_API_URL=http://localhost:8000`).

## Logins (after seeding)

| Role | Email | Password |
|---|---|---|
| Admin | admin@brightloop.com | Admin@12345 |
| Staff | staff@brightloop.com | Demo@12345 |
| Customer | acme@example.com | Demo@12345 |

## How the UI maps to the API

| Screen | Endpoints |
|---|---|
| Login / Register / Reset | `POST /auth/login` + `GET /auth/me`, `/auth/register`, `/auth/forgot-password`, `/auth/reset-password` |
| Customers | `GET /users?role=customer` (customers are users; they sign up themselves) |
| Settings (admin) | `/taxes`, `POST /users/staff`, `GET /users?role=staff` |
| Products & Plans | `/products`, `/plans`, `/discounts` (admin creates, staff read-only) |
| Subscriptions | `/subscriptions`, `/subscriptions/from-template/{id}`, `/{id}/transition`, `/{id}/renew`, `/quotation-templates` |
| Invoices | `/invoices` (+ `outstanding`, `overdue`, date filters), `/confirm`, `/cancel`, `/send`, `/print`, `POST /billing/run` |
| Payments | `/payments`, `/invoices?outstanding=true` |
| Dashboard / Analytics | `/reports/summary`, `/reports/overdue`, `/reports/monthly` |

Notes
- Lists use server paging (`skip`/`limit`); the API returns ids only, so names are looked up via `hooks/useLookups.js`.
- Dropdowns for customers/plans/products load up to 200 rows. Beyond that, swap them for search-as-you-type.
- Customers can pause/resume/close/renew only where the plan allows it; the backend enforces it and the UI shows its message.
