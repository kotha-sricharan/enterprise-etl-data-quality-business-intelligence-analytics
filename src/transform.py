"""Pure, testable standardization and type-conversion functions."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


def amount_to_cents(value: str | Decimal | float) -> int:
    """Convert currency to exact integer cents using commercial rounding."""
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def rate_to_basis_points(value: str | Decimal | float) -> int:
    """Convert a decimal rate such as 0.125 to integer basis points."""
    return int((Decimal(str(value)) * 10_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _token(value: str) -> str:
    return "_".join(value.strip().upper().replace("-", " ").split())


def standardize_customer_segment(value: str) -> str:
    aliases = {"SMALL_BUSINESS": "SMB", "MID_MARKET": "MID_MARKET", "ENTERPRISE": "ENTERPRISE", "SMB": "SMB"}
    return aliases.get(_token(value), _token(value))


def standardize_product_category(value: str) -> str:
    aliases = {
        "SOFTWARE": "SOFTWARE", "HARDWARE": "HARDWARE", "PROFESSIONAL_SERVICES": "SERVICES",
        "SERVICES": "SERVICES", "CYBERSECURITY": "SECURITY", "SECURITY": "SECURITY",
        "CLOUD_SERVICES": "CLOUD", "CLOUD": "CLOUD", "DATA_ANALYTICS": "DATA", "DATA": "DATA",
    }
    return aliases.get(_token(value), _token(value))


def standardize_order_status(value: str) -> str:
    aliases = {
        "COMPLETE": "COMPLETED", "COMPLETED": "COMPLETED", "SHIPPED": "SHIPPED",
        "CANCELED": "CANCELLED", "CANCELLED": "CANCELLED", "RETURN": "RETURNED", "RETURNED": "RETURNED",
    }
    return aliases.get(_token(value), _token(value))


def standardize_priority(value: str) -> str:
    aliases = {
        "LOW": "LOW", "MED": "MEDIUM", "MEDIUM": "MEDIUM", "HIGH_PRIORITY": "HIGH",
        "HIGH": "HIGH", "URGENT": "CRITICAL", "CRITICAL": "CRITICAL",
    }
    return aliases.get(_token(value), _token(value))


def standardize_finance_type(value: str) -> str:
    aliases = {
        "SALE": "SALE", "CREDIT": "REFUND", "REFUND": "REFUND", "ADJUSTMENT": "ADJUSTMENT",
    }
    return aliases.get(_token(value), _token(value))


def transform_customer(row: dict, quality_flags: list[str] | None = None) -> dict:
    return {
        "customer_id": row["customer_id"],
        "customer_name": row["customer_name"].strip(),
        "customer_segment": standardize_customer_segment(row["customer_segment"]),
        "region": row.get("region", "").strip().upper() or "UNKNOWN",
        "created_date": row["created_date"],
        "crm_status": row["crm_status"].strip().upper(),
        "quality_flag": "|".join(sorted(quality_flags or [])) or "PASS",
    }


def transform_product(row: dict, quality_flags: list[str] | None = None) -> dict:
    return {
        "product_id": row["product_id"],
        "product_name": row["product_name"].strip(),
        "product_category": standardize_product_category(row["product_category"]),
        "unit_price_cents": amount_to_cents(row["unit_price"]),
        "unit_cost_cents": amount_to_cents(row["unit_cost"]),
        "active_flag": row["active_flag"].strip().upper(),
        "quality_flag": "|".join(sorted(quality_flags or [])) or "PASS",
    }


def transform_order(row: dict, quality_flags: list[str] | None = None) -> dict:
    return {
        "order_id": row["order_id"],
        "customer_id": row["customer_id"],
        "product_id": row["product_id"],
        "order_date": row["order_date"],
        "order_month": row["order_date"][:7],
        "quantity": int(row["quantity"]),
        "unit_price_cents": amount_to_cents(row["unit_price"]),
        "discount_basis_points": rate_to_basis_points(row["discount_rate"]),
        "order_amount_cents": amount_to_cents(row["order_amount"]),
        "order_status": standardize_order_status(row["order_status"]),
        "channel": row["channel"].strip().upper(),
        "quality_flag": "|".join(sorted(quality_flags or [])) or "PASS",
    }


def transform_ticket(row: dict, quality_flags: list[str] | None = None) -> dict:
    opened = datetime.fromisoformat(row["opened_at"])
    resolved = datetime.fromisoformat(row["resolved_at"]) if row.get("resolved_at") else None
    resolution_hours = round((resolved - opened).total_seconds() / 3600, 2) if resolved else None
    return {
        "ticket_id": row["ticket_id"],
        "customer_id": row["customer_id"],
        "opened_at": row["opened_at"],
        "opened_month": row["opened_at"][:7],
        "resolved_at": row.get("resolved_at") or None,
        "ticket_status": row["ticket_status"].strip().upper(),
        "priority": standardize_priority(row["priority"]),
        "issue_category": row["issue_category"].strip().upper(),
        "resolution_hours": resolution_hours,
        "satisfaction_score": int(row["satisfaction_score"]) if row.get("satisfaction_score") else None,
        "quality_flag": "|".join(sorted(quality_flags or [])) or "PASS",
    }


def transform_finance(row: dict, quality_flags: list[str] | None = None) -> dict:
    return {
        "finance_transaction_id": row["finance_transaction_id"],
        "order_id": row["order_id"],
        "posted_date": row["posted_date"],
        "posted_month": row["posted_date"][:7],
        "transaction_type": standardize_finance_type(row["transaction_type"]),
        "transaction_amount_cents": amount_to_cents(row["transaction_amount"]),
        "currency": row["currency"].strip().upper(),
        "posting_status": row["posting_status"].strip().upper(),
        "quality_flag": "|".join(sorted(quality_flags or [])) or "PASS",
    }
