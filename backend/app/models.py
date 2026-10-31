"""Database models. Added scene by scene, following 'A Month at Brightloop'."""
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

Money = Numeric(12, 2)


def utcnow() -> datetime:
    """Naive UTC timestamp (works the same on SQLite and PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---- Scene 1: a new customer signs up (accounts, roles, password reset) ----
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)  # one account per email
    name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True)  # admin | staff | customer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # only the hash is stored
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


# ---- Scene 2: launching a new plan (products, variants, plans) ----
class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    type: Mapped[str] = mapped_column(String(40))  # e.g. software, add-on, service
    sales_price: Mapped[float] = mapped_column(Money)
    cost_price: Mapped[float] = mapped_column(Money, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductVariant.id"
    )


class ProductVariant(Base):
    """e.g. attribute='Brand', value='Odoo', extra_price=560 -> price becomes sales_price + 560."""

    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    attribute: Mapped[str] = mapped_column(String(80))
    value: Mapped[str] = mapped_column(String(80))
    extra_price: Mapped[float] = mapped_column(Money, default=0)

    product: Mapped[Product] = relationship(back_populates="variants")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    price: Mapped[float] = mapped_column(Money)
    billing_period: Mapped[str] = mapped_column(String(10))  # daily | weekly | monthly | yearly
    min_quantity: Mapped[int] = mapped_column(Integer, default=1)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # availability window
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # The admin decides, plan by plan, what can happen to a subscription on this plan:
    auto_close: Mapped[bool] = mapped_column(Boolean, default=False)  # closes by itself when it ends
    allow_early_close: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_pause: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ---- Scene 3: turning a quote into a subscription ----
class Tax(Base):
    __tablename__ = "taxes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    rate_percent: Mapped[float] = mapped_column(Numeric(5, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class QuotationTemplate(Base):
    """A reusable offer: a plan + product lines, valid for a set number of days."""

    __tablename__ = "quotation_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    validity_days: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    plan: Mapped[Plan] = relationship()
    lines: Mapped[list["TemplateLine"]] = relationship(
        cascade="all, delete-orphan", order_by="TemplateLine.id"
    )


class TemplateLine(Base):
    __tablename__ = "template_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("quotation_templates.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    tax_id: Mapped[int | None] = mapped_column(ForeignKey("taxes.id"), nullable=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_sub_status_next", "status", "next_invoice_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str | None] = mapped_column(String(20), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("quotation_templates.id"), nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30)  # invoice due N days after issue
    # draft -> quotation -> confirmed -> active -> closed   (active <-> paused when the plan allows)
    status: Mapped[str] = mapped_column(String(12), default="draft", index=True)
    quotation_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    # billing cursor, used by the billing run (scene 4)
    billing_anchor: Mapped[date | None] = mapped_column(Date, nullable=True)
    cycles_billed: Mapped[int] = mapped_column(Integer, default=0)
    next_invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    plan: Mapped[Plan] = relationship()
    lines: Mapped[list["SubscriptionLine"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan", order_by="SubscriptionLine.id"
    )


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Money)
    tax_id: Mapped[int | None] = mapped_column(ForeignKey("taxes.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Money)  # quantity x unit_price, before tax

    subscription: Mapped[Subscription] = relationship(back_populates="lines")
    product: Mapped[Product] = relationship()
    variant: Mapped[ProductVariant | None] = relationship()
    tax: Mapped[Tax | None] = relationship()

    @property
    def product_name(self) -> str:
        return self.product.name

    @property
    def variant_label(self) -> str | None:
        return f"{self.variant.attribute}: {self.variant.value}" if self.variant else None

    @property
    def tax_rate(self) -> float:
        return float(self.tax.rate_percent) if self.tax else 0.0


# ---- Scene 4: billing day (invoices) ----
class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        # The database itself refuses to bill the same subscription period twice.
        UniqueConstraint("subscription_id", "period_start", name="uq_invoice_period"),
        Index("ix_invoice_status_due", "status", "due_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str | None] = mapped_column(String(20), unique=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    issue_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="draft")  # draft|confirmed|paid|cancelled
    subtotal: Mapped[float] = mapped_column(Money, default=0)
    discount_total: Mapped[float] = mapped_column(Money, default=0)
    tax_total: Mapped[float] = mapped_column(Money, default=0)
    total: Mapped[float] = mapped_column(Money, default=0)
    amount_paid: Mapped[float] = mapped_column(Money, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    subscription: Mapped[Subscription] = relationship()
    customer: Mapped[User] = relationship(foreign_keys=[customer_id])
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceLine.id"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice", order_by="Payment.id")

    @property
    def amount_due(self):
        return self.total - self.amount_paid

    @property
    def is_overdue(self) -> bool:
        return self.status == "confirmed" and self.due_date < date.today()


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Money)
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    tax_amount: Mapped[float] = mapped_column(Money, default=0)
    amount: Mapped[float] = mapped_column(Money)  # before tax; negative for discount lines
    discount_id: Mapped[int | None] = mapped_column(ForeignKey("discounts.id"), nullable=True)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")


# ---- Scene 5: a customer asks for a better price (discount rules) ----
class Discount(Base):
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(10))  # fixed | percent
    value: Mapped[float] = mapped_column(Money)
    min_purchase: Mapped[float] = mapped_column(Money, default=0)  # minimum amount the discount applies to
    min_quantity: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = unlimited
    times_used: Mapped[int] = mapped_column(Integer, default=0)
    # Scope: a product, one subscription, or neither (= every subscription).
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---- Scene 6: the money comes in (payments) ----
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    method: Mapped[str] = mapped_column(String(20))  # cash | card | bank_transfer | upi | cheque | other
    amount: Mapped[float] = mapped_column(Money)
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    invoice: Mapped[Invoice] = relationship(back_populates="payments")
