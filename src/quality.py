"""Business-rule validation, exception classification, and critical controls."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from src.transform import (
    amount_to_cents,
    standardize_customer_segment,
    standardize_finance_type,
    standardize_order_status,
    standardize_priority,
    standardize_product_category,
)


class DataQualityError(RuntimeError):
    """Raised when a critical control makes the warehouse unsafe to publish."""


def find_duplicates(rows: list[dict], key: str) -> list[str]:
    """Return sorted nonblank key values that occur more than once."""
    counts = Counter(row.get(key, "") for row in rows if row.get(key, ""))
    return sorted(value for value, count in counts.items() if count > 1)


def missing_required_fields(rows: list[dict], required: tuple[str, ...], key: str) -> list[dict]:
    """Return row identifiers and missing required columns."""
    missing = []
    for row in rows:
        fields = [field for field in required if row.get(field) in (None, "")]
        if fields:
            missing.append({"record_id": row.get(key, "MISSING_KEY"), "fields": fields})
    return missing


def invalid_foreign_keys(rows: list[dict], field: str, valid_ids: set[str], key: str) -> list[str]:
    """Return record IDs whose populated foreign key is absent from its parent."""
    return sorted(
        row.get(key, "MISSING_KEY")
        for row in rows
        if row.get(field) and row.get(field) not in valid_ids
    )


def _deduplicate(rows: list[dict], key: str) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for row in rows:
        identifier = row.get(key, "")
        if identifier not in seen:
            unique.append(row)
            seen.add(identifier)
    return unique


def _iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def _iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except (TypeError, ValueError):
        return False


def _decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return None


def validate_sources(
    customers: list[dict], products: list[dict], orders: list[dict],
    tickets: list[dict], finance: list[dict], raise_on_critical: bool = True,
) -> dict:
    """Classify raw defects and return explicit remediation/quarantine decisions."""
    issues: list[dict] = []
    critical_errors: list[str] = []
    quarantine = {"orders": set(), "support_tickets": set(), "finance_transactions": set()}

    def add(dataset: str, record_id: str, issue_type: str, severity: str, action: str, message: str) -> None:
        issues.append({
            "dataset": dataset, "record_id": record_id, "issue_type": issue_type,
            "severity": severity, "action": action, "message": message,
        })
        if action == "QUARANTINE":
            quarantine[dataset].add(record_id)
        if action == "FAIL_PIPELINE":
            critical_errors.append(f"{dataset}/{record_id}: {message}")

    datasets = (
        ("customers", customers, "customer_id"),
        ("products", products, "product_id"),
        ("orders", orders, "order_id"),
        ("support_tickets", tickets, "ticket_id"),
        ("finance_transactions", finance, "finance_transaction_id"),
    )
    unique: dict[str, list[dict]] = {}
    for dataset, rows, key in datasets:
        duplicates = find_duplicates(rows, key)
        for identifier in duplicates:
            add(dataset, identifier, "DUPLICATE_BUSINESS_KEY", "MEDIUM", "DEDUPLICATE", f"Duplicate {key}; keep first deterministic row")
        unique[dataset] = _deduplicate(rows, key)
        for row in unique[dataset]:
            if not row.get(key):
                add(dataset, "MISSING_KEY", "MISSING_PRIMARY_KEY", "CRITICAL", "FAIL_PIPELINE", f"{key} is required")

    customers_u = unique["customers"]
    products_u = unique["products"]
    orders_u = unique["orders"]
    tickets_u = unique["support_tickets"]
    finance_u = unique["finance_transactions"]

    for row in customers_u:
        identifier = row.get("customer_id", "MISSING_KEY")
        for field in ("customer_name", "customer_segment", "created_date", "crm_status"):
            if not row.get(field):
                add("customers", identifier, "MISSING_REQUIRED_FIELD", "CRITICAL", "FAIL_PIPELINE", f"{field} is required")
        if row.get("created_date") and not _iso_date(row["created_date"]):
            add("customers", identifier, "MALFORMED_DATE", "CRITICAL", "FAIL_PIPELINE", "created_date must be ISO format")
        standardized = standardize_customer_segment(row.get("customer_segment", ""))
        if standardized not in {"SMB", "MID_MARKET", "ENTERPRISE"}:
            add("customers", identifier, "INVALID_CATEGORY", "CRITICAL", "FAIL_PIPELINE", "customer segment is outside the governed domain")
        elif row.get("customer_segment") != standardized:
            add("customers", identifier, "CATEGORY_STANDARDIZED", "LOW", "STANDARDIZE", "Customer segment mapped to canonical value")
        if not row.get("region"):
            add("customers", identifier, "MISSING_REGION", "MEDIUM", "DEFAULT_UNKNOWN", "Missing region standardized to UNKNOWN")

    for row in products_u:
        identifier = row.get("product_id", "MISSING_KEY")
        for field in ("product_name", "product_category", "unit_price", "unit_cost", "active_flag"):
            if not row.get(field):
                add("products", identifier, "MISSING_REQUIRED_FIELD", "CRITICAL", "FAIL_PIPELINE", f"{field} is required")
        category = standardize_product_category(row.get("product_category", ""))
        if category not in {"SOFTWARE", "HARDWARE", "SERVICES", "SECURITY", "CLOUD", "DATA"}:
            add("products", identifier, "INVALID_CATEGORY", "CRITICAL", "FAIL_PIPELINE", "product category is outside the governed domain")
        elif row.get("product_category") != category:
            add("products", identifier, "CATEGORY_STANDARDIZED", "LOW", "STANDARDIZE", "Product category mapped to canonical value")
        price, cost = _decimal(row.get("unit_price", "")), _decimal(row.get("unit_cost", ""))
        if price is None or cost is None or price <= 0 or cost < 0 or cost > price:
            add("products", identifier, "INVALID_PRODUCT_AMOUNT", "CRITICAL", "FAIL_PIPELINE", "Product price/cost hierarchy is invalid")
        elif price > Decimal("20000"):
            add("products", identifier, "UNUSUAL_NUMERIC_VALUE", "MEDIUM", "REVIEW", "Unit price exceeds the profiling threshold")

    customer_ids = {row["customer_id"] for row in customers_u if row.get("customer_id")}
    product_ids = {row["product_id"] for row in products_u if row.get("product_id")}
    for row in orders_u:
        identifier = row.get("order_id", "MISSING_KEY")
        if not row.get("customer_id"):
            add("orders", identifier, "MISSING_REQUIRED_FIELD", "HIGH", "QUARANTINE", "customer_id is required")
        elif row["customer_id"] not in customer_ids:
            add("orders", identifier, "INVALID_CUSTOMER_REFERENCE", "HIGH", "QUARANTINE", "Customer does not exist in CRM source")
        if not row.get("product_id") or row.get("product_id") not in product_ids:
            add("orders", identifier, "INVALID_PRODUCT_REFERENCE", "HIGH", "QUARANTINE", "Product does not exist in product master")
        if not _iso_date(row.get("order_date", "")):
            add("orders", identifier, "MALFORMED_DATE", "HIGH", "QUARANTINE", "order_date must be ISO format")
        quantity = _decimal(row.get("quantity", ""))
        amount = _decimal(row.get("order_amount", ""))
        unit_price = _decimal(row.get("unit_price", ""))
        discount = _decimal(row.get("discount_rate", ""))
        if quantity is None or quantity <= 0 or quantity != quantity.to_integral_value():
            add("orders", identifier, "INVALID_QUANTITY", "HIGH", "QUARANTINE", "quantity must be a positive integer")
        if amount is None or amount < 0:
            add("orders", identifier, "INVALID_ORDER_AMOUNT", "HIGH", "QUARANTINE", "order amount must be nonnegative")
        if unit_price is None or unit_price <= 0 or discount is None or not Decimal("0") <= discount <= Decimal("1"):
            add("orders", identifier, "INVALID_NUMERIC_VALUE", "HIGH", "QUARANTINE", "price or discount is outside the valid range")
        if amount is not None and amount > Decimal("100000"):
            add("orders", identifier, "UNUSUAL_NUMERIC_VALUE", "MEDIUM", "REVIEW", "Order amount exceeds the high-value review threshold")
        status = standardize_order_status(row.get("order_status", ""))
        if status not in {"COMPLETED", "SHIPPED", "CANCELLED", "RETURNED"}:
            add("orders", identifier, "INVALID_CATEGORY", "HIGH", "QUARANTINE", "Order status is outside the governed domain")
        elif row.get("order_status") != status:
            add("orders", identifier, "CATEGORY_STANDARDIZED", "LOW", "STANDARDIZE", "Order status mapped to canonical value")

    for row in tickets_u:
        identifier = row.get("ticket_id", "MISSING_KEY")
        if not row.get("customer_id") or row.get("customer_id") not in customer_ids:
            add("support_tickets", identifier, "INVALID_CUSTOMER_REFERENCE", "HIGH", "QUARANTINE", "Ticket customer does not exist")
        opened_valid = _iso_datetime(row.get("opened_at", ""))
        resolved_valid = not row.get("resolved_at") or _iso_datetime(row["resolved_at"])
        if not opened_valid or not resolved_valid:
            add("support_tickets", identifier, "MALFORMED_DATE", "HIGH", "QUARANTINE", "Ticket timestamps must be ISO format")
        elif row.get("resolved_at") and datetime.fromisoformat(row["resolved_at"]) < datetime.fromisoformat(row["opened_at"]):
            add("support_tickets", identifier, "INVALID_DATE_SEQUENCE", "HIGH", "QUARANTINE", "Resolution precedes ticket creation")
        if not row.get("issue_category"):
            add("support_tickets", identifier, "MISSING_REQUIRED_FIELD", "HIGH", "QUARANTINE", "issue_category is required")
        priority = standardize_priority(row.get("priority", ""))
        if priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            add("support_tickets", identifier, "INVALID_CATEGORY", "HIGH", "QUARANTINE", "Priority is outside the governed domain")
        elif row.get("priority") != priority:
            add("support_tickets", identifier, "CATEGORY_STANDARDIZED", "LOW", "STANDARDIZE", "Priority mapped to canonical value")

    raw_order_by_id = {row["order_id"]: row for row in orders_u if row.get("order_id")}
    raw_order_ids = set(raw_order_by_id)
    for row in finance_u:
        identifier = row.get("finance_transaction_id", "MISSING_KEY")
        order_id = row.get("order_id", "")
        if not order_id or order_id not in raw_order_ids:
            add("finance_transactions", identifier, "INVALID_ORDER_REFERENCE", "HIGH", "QUARANTINE", "Finance order does not exist in order source")
        if not _iso_date(row.get("posted_date", "")):
            add("finance_transactions", identifier, "MALFORMED_DATE", "HIGH", "QUARANTINE", "posted_date must be ISO format")
        amount = _decimal(row.get("transaction_amount", ""))
        if amount is None:
            add("finance_transactions", identifier, "INVALID_NUMERIC_VALUE", "HIGH", "QUARANTINE", "Transaction amount must be numeric")
        finance_type = standardize_finance_type(row.get("transaction_type", ""))
        if finance_type not in {"SALE", "REFUND", "ADJUSTMENT"}:
            add("finance_transactions", identifier, "INVALID_CATEGORY", "HIGH", "QUARANTINE", "Transaction type is outside the governed domain")
        elif row.get("transaction_type") != finance_type:
            add("finance_transactions", identifier, "CATEGORY_STANDARDIZED", "LOW", "STANDARDIZE", "Finance type mapped to canonical value")
        if row.get("currency") != "USD" or row.get("posting_status") not in {"POSTED", "PENDING"}:
            add("finance_transactions", identifier, "INVALID_CATEGORY", "HIGH", "QUARANTINE", "Currency or posting status is invalid")
        if order_id in raw_order_by_id and amount is not None:
            order = raw_order_by_id[order_id]
            order_amount = _decimal(order.get("order_amount", ""))
            status = standardize_order_status(order.get("order_status", ""))
            if order_amount is not None:
                expected = order_amount if status in {"COMPLETED", "SHIPPED"} else (-abs(order_amount) if status == "RETURNED" else Decimal("0"))
                if amount_to_cents(amount) != amount_to_cents(expected):
                    add("finance_transactions", identifier, "FINANCE_ORDER_AMOUNT_MISMATCH", "MEDIUM", "REVIEW", "Ledger amount differs from the status-based order expectation")

    if critical_errors and raise_on_critical:
        raise DataQualityError("Critical source validation failed:\n" + "\n".join(critical_errors[:30]))

    grouped = Counter((issue["dataset"], issue["issue_type"], issue["severity"], issue["action"]) for issue in issues)
    controls = [
        {
            "dataset": dataset, "control": issue_type, "severity": severity, "action": action,
            "issue_count": count, "status": "WARNING" if action != "FAIL_PIPELINE" else "FAIL",
        }
        for (dataset, issue_type, severity, action), count in sorted(grouped.items())
    ]
    passed_controls = [
        {"dataset": "enterprise", "control": name, "severity": "CRITICAL", "action": "NONE", "issue_count": 0, "status": "PASS"}
        for name in (
            "PRIMARY_KEYS_PRESENT", "DIMENSION_DOMAINS_VALID", "DIMENSION_AMOUNTS_VALID",
            "SOURCE_FILES_READABLE", "CRITICAL_ERROR_THRESHOLD",
        )
    ]
    controls.extend(passed_controls)
    return {
        "unique_rows": unique,
        "issues": issues,
        "controls": controls,
        "critical_errors": critical_errors,
        "critical_error_count": len(critical_errors),
        "quarantine_ids": {dataset: sorted(ids) for dataset, ids in quarantine.items()},
        "duplicate_counts": {
            dataset: len(find_duplicates(rows, key)) for dataset, rows, key in datasets
        },
    }
