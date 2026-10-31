# Brightloop

### Intelligent Subscription and Revenue Management Platform

Brightloop is a web-based platform for managing subscriptions, customers, products, plans, invoices, payments, and revenue reports.

It helps businesses organize subscription operations in one place. It provides separate access for administrators, staff, and customers.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [User Roles](#user-roles)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration)
- [Running the Application](#running-the-application)
- [Demo Accounts](#demo-accounts)
- [API Overview](#api-overview)
- [Database](#database)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## Overview

Managing subscriptions involves several tasks, including tracking customers, handling renewals, creating invoices, recording payments, and monitoring revenue.

Brightloop brings these tasks together in a single application.

The frontend provides the user interface, while the backend handles API requests, application rules, authentication, and data operations.

## Features

### Authentication
- User login and registration.
- Retrieve the current user's information.
- Forgot-password and password-reset workflows.
- Role-based access to application features.

### Customer Management
- View customer accounts.
- Retrieve customer records from the backend.
- Connect customer information with subscription and billing operations.

### Product and Plan Management
- Manage products and subscription plans.
- Manage discounts.
- Restrict management operations according to user permissions.

### Subscription Management
- View and manage subscriptions.
- Create subscriptions from templates.
- Renew subscriptions.
- Pause, resume, or close subscriptions when allowed by the plan.

### Invoice Management
- View invoices.
- Filter invoices by date.
- View outstanding and overdue invoices.
- Confirm, cancel, send, and print invoices.
- Run billing operations.

### Payment Management
- View payment records.
- Track outstanding invoices.
- Access payment information through the backend API.

### Dashboard and Reports
- View summary reports.
- Monitor overdue invoices.
- View monthly reports.
- Access subscription and revenue information.

### Administrative Settings
- Manage staff accounts.
- Manage tax settings.
- Control access to administrative features.

## User Roles

| Role | Responsibilities |
|---|---|
| Admin | Manage staff, settings, products, plans, discounts, subscriptions, and billing operations. |
| Staff | Access permitted customer, product, plan, subscription, invoice, and payment information. |
| Customer | Access permitted account and subscription features. |

The backend enforces the application's business rules and permissions.

## Technology Stack

### Frontend
- React 18
- Vite 5
- JavaScript
- React Router
- Axios
- CSS

### Backend
- Python
- FastAPI
- Uvicorn

### Database
- PostgreSQL 16
- SQLAlchemy-compatible PostgreSQL connection

### Development and Deployment
- Node.js
- npm
- Docker
- Docker Compose
- Git
- GitHub

## Architecture

Brightloop uses a frontend-backend architecture.

```text
                 User
                   |
                   v
          React + Vite Frontend
                   |
                   | HTTP Requests
                   v
             FastAPI Backend
                   |
                   v
              SQLAlchemy
                   |
                   v
              PostgreSQL
```

### How It Works

1. The user interacts with the React frontend.
2. Axios sends HTTP requests to the FastAPI backend.
3. The backend validates requests and applies business rules.
4. The backend accesses the PostgreSQL database.
5. The API returns responses to the frontend.
6. The frontend displays the results.

## Project Structure

```text
Brightloop/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── seed.py
│   ├── Dockerfile
│   └── docker-compose.yml
├── src/
│   ├── components/
│   ├── hooks/
│   ├── pages/
│   ├── services/
│   └── utils/
├── .gitignore
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
└── README.md
```

This is a simplified overview. The backend and frontend may contain additional files and folders.

| File or Folder | Purpose |
|---|---|
| `backend/` | Backend application and deployment configuration. |
| `backend/app/main.py` | FastAPI application entry point. |
| `backend/app/seed.py` | Script for creating demo data. |
| `backend/Dockerfile` | Instructions for building the backend container. |
| `backend/docker-compose.yml` | Configuration for running the backend and PostgreSQL. |
| `src/components/` | Reusable React components. |
| `src/hooks/` | Custom React hooks. |
| `src/pages/` | Application pages. |
| `src/services/` | API communication and service logic. |
| `src/utils/` | Shared utility functions. |
| `package.json` | Frontend dependencies and commands. |
| `vite.config.js` | Vite development server configuration. |

## Prerequisites

Install the following tools:

- Git
- Node.js and npm
- Docker Desktop with Docker Compose

If you do not use Docker, you will also need Python, pip, and a compatible PostgreSQL database.

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/annmariaaarampulickal-dev/Brightloop.git
cd Brightloop
```

### 2. Start the Backend and Database

Open a terminal in the project root, then run:

```bash
cd backend
docker compose up --build
```

This starts the PostgreSQL database and FastAPI backend using the provided Docker Compose configuration.

The backend is exposed at:

```text
http://localhost:8000
```

Keep this terminal running.

### 3. Install Frontend Dependencies

Open a second terminal in the project root:

```bash
npm install
```

### 4. Configure the Frontend

Create a `.env` file in the project root if one does not already exist.

Add:

```env
VITE_API_URL=http://localhost:8000
```

This sets the base URL used by the frontend to contact the backend.

### 5. Start the Frontend

Run:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

Port `3000` is configured in `vite.config.js` to match the backend's frontend URL setting.

## Environment Configuration

### Frontend Environment Variables

| Variable | Purpose |
|---|---|
| `VITE_API_URL` | Base URL of the backend API. |

Example:

```env
VITE_API_URL=http://localhost:8000
```

### Backend Environment Variables

The Docker Compose configuration includes settings for the database connection and administrator account.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string. |
| `SECRET_KEY` | Secret used by the backend for security-related operations. |
| `ADMIN_EMAIL` | Administrator account email. |
| `ADMIN_PASSWORD` | Initial administrator password. |

**Important:** The credentials in the Docker Compose file are for local development. Change them before deploying the application. Use a strong, private secret key and do not commit production secrets to GitHub.

## Running the Application

Start the backend and database first:

```bash
cd backend
docker compose up --build
```

Then, in a separate terminal at the project root:

```bash
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

### Production Frontend Build

To create a production build of the frontend, run this from the project root:

```bash
npm run build
```

To preview the generated build locally:

```bash
npm run preview
```

## Demo Accounts

The project documentation provides the following accounts for local development after the demo data has been initialized.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@brightloop.com` | `Admin@12345` |
| Staff | `staff@brightloop.com` | `Demo@12345` |
| Customer | `acme@example.com` | `Demo@12345` |

If an account does not work, initialize the demo data using the instructions below.

These credentials are for development only. Never use them in a public production deployment.

## API Overview

The frontend communicates with the FastAPI backend through HTTP endpoints.

| Module | Endpoints | Purpose |
|---|---|---|
| Authentication | `/auth/login`, `/auth/me`, `/auth/register` | Login, registration, and current-user information. |
| Password Reset | `/auth/forgot-password`, `/auth/reset-password` | Password-reset workflows. |
| Customers | `/users?role=customer` | Retrieve customer accounts. |
| Staff | `/users?role=staff`, `/users/staff` | Retrieve and create staff accounts. |
| Tax Settings | `/taxes` | Manage tax settings. |
| Products | `/products` | Manage products. |
| Plans | `/plans` | Manage subscription plans. |
| Discounts | `/discounts` | Manage discounts. |
| Subscriptions | `/subscriptions` | Manage subscriptions. |
| Templates | `/quotation-templates` | Access subscription or quotation templates. |
| Invoices | `/invoices` | Retrieve and manage invoices. |
| Billing | `/billing/run` | Run billing operations. |
| Payments | `/payments` | Retrieve payment records. |
| Reports | `/reports/summary`, `/reports/overdue`, `/reports/monthly` | Retrieve reporting data. |

Some operations use additional paths, query parameters, or HTTP methods.

For full API details, open the interactive FastAPI documentation while the backend is running:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database

Brightloop uses PostgreSQL to store application data.

The Docker Compose configuration creates a PostgreSQL 16 service and stores database files in a Docker-managed volume.

### Initialize Demo Data

After starting the backend, open another terminal and run:

```bash
cd backend
docker compose exec api python -m app.seed
```

This runs the backend's seed script inside the API container.

Use this command when you need the demo accounts and sample data. Check the seed script before running it against data you need to preserve.

## Security

Follow these practices when developing or deploying Brightloop:

- Use strong passwords and secret keys.
- Never publish production credentials.
- Enforce access permissions in the backend.
- Validate incoming API requests.
- Use HTTPS in production.
- Keep dependencies updated.
- Protect customer and billing information.
- Configure allowed frontend origins correctly.
- Use secure password storage and authentication practices.

Frontend restrictions alone are not enough to protect sensitive operations. The backend must enforce authorization.

## Troubleshooting

### Frontend Cannot Connect to the Backend

- Check that the backend container is running.
- Confirm that the API is available at `http://localhost:8000`.
- Verify `VITE_API_URL` in the frontend `.env` file.
- Check the browser's Network and Console tabs.
- Review the backend logs.

### Login Does Not Work

- Confirm that the demo data has been initialized.
- Verify the email and password.
- Check the backend logs for authentication errors.
- Confirm that the frontend is using the correct API URL.

### Frontend Shows a Blank Page

- Check the browser console for JavaScript errors.
- Check the terminal running Vite.
- Confirm that `npm install` completed successfully.
- Check for failed API requests.

### Backend Does Not Start

- Confirm that Docker Desktop is running.
- Check whether ports `8000` and `5432` are already in use.
- Review the container logs.
- Verify the database configuration.

To view container logs:

```bash
cd backend
docker compose logs
```

### Password Reset Does Not Send an Email

Without SMTP configuration, the backend logs password-reset email information instead of sending an actual email.

For local testing, inspect the API logs and use the reset link printed there.

To send real emails, configure the required SMTP settings in the backend.
