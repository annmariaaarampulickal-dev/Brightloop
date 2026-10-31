from datetime import date

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.orm import selectinload

from ..deps import DB, Admin, CurrentUser
from ..models import Plan, Product, ProductVariant, QuotationTemplate, TemplateLine, Tax
from ..schemas import (
    PlanIn,
    PlanOut,
    PlanUpdate,
    ProductIn,
    ProductOut,
    ProductUpdate,
    TaxIn,
    TaxOut,
    TemplateIn,
    TemplateOut,
    VariantIn,
    VariantOut,
)

products = APIRouter(prefix="/products", tags=["products"])
plans = APIRouter(prefix="/plans", tags=["plans"])
taxes = APIRouter(prefix="/taxes", tags=["taxes"])
templates = APIRouter(prefix="/quotation-templates", tags=["quotation templates"])


def _get(db, model, id_: int, label: str):
    obj = db.get(model, id_)
    if not obj:
        raise HTTPException(404, f"{label} not found")
    return obj


# ---------------- Products & variants ----------------
@products.post("", response_model=ProductOut, status_code=201)
def create_product(data: ProductIn, db: DB, _: Admin):
    p = Product(**data.model_dump(exclude={"variants"}))
    p.variants = [ProductVariant(**v.model_dump()) for v in data.variants]
    db.add(p)
    db.commit()
    return p


@products.get("", response_model=list[ProductOut])
def list_products(
    db: DB,
    _: CurrentUser,
    q: str | None = None,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    query = db.query(Product).options(selectinload(Product.variants))
    if not include_inactive:
        query = query.filter(Product.is_active.is_(True))
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    return query.order_by(Product.id).offset(skip).limit(limit).all()


@products.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: DB, _: CurrentUser):
    return _get(db, Product, product_id, "Product")


@products.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, db: DB, _: Admin):
    p = _get(db, Product, product_id, "Product")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return p


@products.post("/{product_id}/variants", response_model=VariantOut, status_code=201)
def add_variant(product_id: int, data: VariantIn, db: DB, _: Admin):
    _get(db, Product, product_id, "Product")
    v = ProductVariant(product_id=product_id, **data.model_dump())
    db.add(v)
    db.commit()
    return v


@products.delete("/{product_id}/variants/{variant_id}", status_code=204)
def delete_variant(product_id: int, variant_id: int, db: DB, _: Admin):
    v = db.get(ProductVariant, variant_id)
    if not v or v.product_id != product_id:
        raise HTTPException(404, "Variant not found")
    db.delete(v)
    db.commit()


# ---------------- Plans ----------------
@plans.post("", response_model=PlanOut, status_code=201)
def create_plan(data: PlanIn, db: DB, _: Admin):
    plan = Plan(**data.model_dump())
    db.add(plan)
    db.commit()
    return plan


@plans.get("", response_model=list[PlanOut])
def list_plans(
    db: DB,
    _: CurrentUser,
    available_on: date | None = Query(None, description="Only plans on sale on this date"),
    billing_period: str | None = None,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = Query(50, le=200),
):
    query = db.query(Plan)
    if not include_inactive:
        query = query.filter(Plan.is_active.is_(True))
    if billing_period:
        query = query.filter(Plan.billing_period == billing_period)
    if available_on:
        query = query.filter(
            (Plan.start_date.is_(None)) | (Plan.start_date <= available_on),
            (Plan.end_date.is_(None)) | (Plan.end_date >= available_on),
        )
    return query.order_by(Plan.id).offset(skip).limit(limit).all()


@plans.get("/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, db: DB, _: CurrentUser):
    return _get(db, Plan, plan_id, "Plan")


@plans.patch("/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, data: PlanUpdate, db: DB, _: Admin):
    plan = _get(db, Plan, plan_id, "Plan")
    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(plan, k, v)
    if plan.start_date and plan.end_date and plan.end_date < plan.start_date:
        db.rollback()
        raise HTTPException(422, "end_date cannot be before start_date")
    db.commit()
    return plan


# ---------------- Taxes (rules set by the admin) ----------------
@taxes.post("", response_model=TaxOut, status_code=201)
def create_tax(data: TaxIn, db: DB, _: Admin):
    t = Tax(**data.model_dump())
    db.add(t)
    db.commit()
    return t


@taxes.get("", response_model=list[TaxOut])
def list_taxes(db: DB, _: CurrentUser):
    return db.query(Tax).filter(Tax.is_active.is_(True)).order_by(Tax.id).all()


@taxes.delete("/{tax_id}", status_code=204)
def deactivate_tax(tax_id: int, db: DB, _: Admin):
    """Taxes are deactivated, never deleted, so old invoices keep their history."""
    _get(db, Tax, tax_id, "Tax").is_active = False
    db.commit()


# ---------------- Quotation templates ----------------
@templates.post("", response_model=TemplateOut, status_code=201)
def create_template(data: TemplateIn, db: DB, _: Admin):
    _get(db, Plan, data.plan_id, "Plan")
    t = QuotationTemplate(name=data.name, plan_id=data.plan_id, validity_days=data.validity_days)
    for ln in data.lines:
        prod = _get(db, Product, ln.product_id, "Product")
        if ln.variant_id and not any(v.id == ln.variant_id for v in prod.variants):
            raise HTTPException(422, "Variant does not belong to that product")
        if ln.tax_id:
            _get(db, Tax, ln.tax_id, "Tax")
        t.lines.append(
            TemplateLine(product_id=ln.product_id, variant_id=ln.variant_id, quantity=ln.quantity, tax_id=ln.tax_id)
        )
    db.add(t)
    db.commit()
    return t


@templates.get("", response_model=list[TemplateOut])
def list_templates(db: DB, user: CurrentUser):
    if user.role == "customer":
        raise HTTPException(403, "You do not have access to this action")
    return db.query(QuotationTemplate).filter(QuotationTemplate.is_active.is_(True)).order_by(QuotationTemplate.id).all()
