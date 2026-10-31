from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .database import Base, SessionLocal, engine
from .models import User
from .routers import auth, billing, catalog, discounts, payments, reports, subscriptions, users
from .security import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:  # make sure there is always an admin to start from
        if not db.query(User).filter(User.role == "admin").first():
            db.add(
                User(
                    email=config.ADMIN_EMAIL.lower(),
                    name="Admin",
                    hashed_password=hash_password(config.ADMIN_PASSWORD),
                    role="admin",
                )
            )
            db.commit()
    yield


app = FastAPI(title="Brightloop Subscription Management", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(catalog.products)
app.include_router(catalog.plans)
app.include_router(catalog.taxes)
app.include_router(catalog.templates)
app.include_router(subscriptions.router)
app.include_router(discounts.router)
app.include_router(billing.billing)
app.include_router(billing.invoices)
app.include_router(payments.router)
app.include_router(reports.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
