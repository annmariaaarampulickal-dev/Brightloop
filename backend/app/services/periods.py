from datetime import date, timedelta

from dateutil.relativedelta import relativedelta


def add_period(anchor: date, period: str, n: int = 1) -> date:
    """The date n billing periods after `anchor`.

    Always computed from the anchor (not from the previous date) so a subscription that
    starts on the 31st bills on the 30th/28th in short months and returns to the 31st."""
    if period == "daily":
        return anchor + timedelta(days=n)
    if period == "weekly":
        return anchor + timedelta(weeks=n)
    if period == "monthly":
        return anchor + relativedelta(months=n)
    if period == "yearly":
        return anchor + relativedelta(years=n)
    raise ValueError(f"Unknown billing period: {period}")
