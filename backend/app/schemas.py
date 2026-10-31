from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

from .security import validate_password

# Money is stored as Decimal and sent to clients as a plain JSON number.
Money = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]


# ---- Scene 1: accounts ----
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str = Field(min_length=1, max_length=120)

    @field_validator("password")
    @classmethod
    def _password_rules(cls, v: str) -> str:
        return validate_password(v)


class StaffIn(RegisterIn):
    pass


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password_rules(cls, v: str) -> str:
        return validate_password(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: str
    role: str
    is_active: bool


# ---- Scene 2: products, variants, plans ----
class VariantIn(BaseModel):
    attribute: str = Field(min_length=1, max_length=80)  # e.g. Brand
    value: str = Field(min_length=1, max_length=80)  # e.g. Odoo
    extra_price: Money = Decimal("0")  # added to the product's sales price


class VariantOut(VariantIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: str = Field(min_length=1, max_length=40)
    sales_price: Money = Field(ge=0)
    cost_price: Money = Field(default=Decimal("0"), ge=0)
    notes: str | None = None
    variants: list[VariantIn] = []


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=160)
    type: str | None = Field(None, min_length=1, max_length=40)
    sales_price: Money | None = Field(None, ge=0)
    cost_price: Money | None = Field(None, ge=0)
    notes: str | None = None
    is_active: bool | None = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    type: str
    sales_price: Money
    cost_price: Money
    notes: str | None
    is_active: bool
    variants: list[VariantOut]


BillingPeriod = Literal["daily", "weekly", "monthly", "yearly"]


class PlanIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    price: Money = Field(ge=0)
    billing_period: BillingPeriod
    min_quantity: int = Field(1, ge=1)
    start_date: date | None = None  # dates the plan is available
    end_date: date | None = None
    auto_close: bool = False
    allow_early_close: bool = True
    allow_pause: bool = True
    allow_renew: bool = True

    @model_validator(mode="after")
    def _dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class PlanUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=160)
    price: Money | None = Field(None, ge=0)
    billing_period: BillingPeriod | None = None
    min_quantity: int | None = Field(None, ge=1)
    start_date: date | None = None
    end_date: date | None = None
    auto_close: bool | None = None
    allow_early_close: bool | None = None
    allow_pause: bool | None = None
    allow_renew: bool | None = None
    is_active: bool | None = None


class PlanOut(PlanIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool


# ---- Scene 3: taxes, quotation templates, subscriptions ----
class TaxIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    rate_percent: Money = Field(ge=0, le=100)


class TaxOut(TaxIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool


class LineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(1, ge=1)
    unit_price: Money | None = Field(None, ge=0)  # defaults to product price + variant extra
    tax_id: int | None = None


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    plan_id: int
    validity_days: int = Field(30, ge=1)
    lines: list[LineIn] = Field(min_length=1)


class TemplateLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    variant_id: int | None
    quantity: int
    tax_id: int | None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    plan_id: int
    validity_days: int
    is_active: bool
    lines: list[TemplateLineOut]


class SubscriptionIn(BaseModel):
    customer_id: int
    plan_id: int
    start_date: date
    expiry_date: date | None = None  # defaults to the plan's end date, else 1 year
    payment_terms_days: int = Field(30, ge=0)
    lines: list[LineIn] = Field(min_length=1)


class FromTemplateIn(BaseModel):
    customer_id: int
    start_date: date
    expiry_date: date | None = None
    payment_terms_days: int = Field(30, ge=0)


class SubscriptionLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product_name: str
    variant_id: int | None
    variant_label: str | None
    quantity: int
    unit_price: Money
    tax_id: int | None
    tax_rate: float
    amount: Money


SubStatus = Literal["draft", "quotation", "confirmed", "active", "paused", "closed"]


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    customer_id: int
    plan_id: int
    template_id: int | None
    start_date: date
    expiry_date: date | None
    payment_terms_days: int
    status: SubStatus
    quotation_valid_until: date | None
    next_invoice_date: date | None
    lines: list[SubscriptionLineOut]


class TransitionIn(BaseModel):
    to: SubStatus


# ---- Scene 4: invoices ----
class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: str
    quantity: int
    unit_price: Money
    tax_rate: Money
    tax_amount: Money
    amount: Money


InvoiceStatus = Literal["draft", "confirmed", "paid", "cancelled"]


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: str
    subscription_id: int
    customer_id: int
    period_start: date
    period_end: date
    issue_date: date
    due_date: date
    status: InvoiceStatus
    subtotal: Money
    discount_total: Money
    tax_total: Money
    total: Money
    amount_paid: Money
    amount_due: Money
    is_overdue: bool
    lines: list[InvoiceLineOut]


class BillingRunIn(BaseModel):
    as_of: date | None = None  # bill everything due up to this date (default: today)
    auto_confirm: bool = False  # confirm the invoices straight away instead of leaving drafts


class BillingRunOut(BaseModel):
    as_of: date
    created: int
    skipped_already_billed: int
    closed_subscriptions: int
    invoice_ids: list[int]


# ---- Scene 5: discounts ----
class DiscountIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["fixed", "percent"]
    value: Money = Field(gt=0)
    min_purchase: Money = Field(default=Decimal("0"), ge=0)
    min_quantity: int = Field(0, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    usage_limit: int | None = Field(None, ge=1)
    product_id: int | None = None  # leave empty to apply to whole subscriptions
    subscription_id: int | None = None  # leave empty to apply to every subscription

    @model_validator(mode="after")
    def _check(self):
        if self.kind == "percent" and self.value > 100:
            raise ValueError("A percentage discount cannot be more than 100")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class DiscountUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    end_date: date | None = None
    usage_limit: int | None = Field(None, ge=1)
    is_active: bool | None = None


class DiscountOut(DiscountIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    times_used: int
    is_active: bool


# ---- Scene 6: payments ----
PaymentMethod = Literal["cash", "card", "bank_transfer", "upi", "cheque", "other"]


class PaymentIn(BaseModel):
    invoice_id: int
    method: PaymentMethod
    amount: Money = Field(gt=0)
    payment_date: date | None = None  # defaults to today
    note: str | None = Field(None, max_length=500)


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    method: PaymentMethod
    amount: Money
    payment_date: date
    note: str | None
