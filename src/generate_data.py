"""Generate deterministic fictional enterprise sources with controlled defects."""
from __future__ import annotations

import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from src.config import (
    CUSTOMER_COUNT,
    CUSTOMER_SEGMENTS,
    ORDER_COUNT,
    PRODUCT_CATEGORIES,
    PRODUCT_COUNT,
    RANDOM_SEED,
    RAW_DIR,
    REGIONS,
    TICKET_COUNT,
    ensure_directories,
)


def _write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    """Write a stable UTF-8 CSV using an explicit column order."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _random_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _generate_customers(rng: random.Random) -> tuple[list[dict], dict[str, int]]:
    rows: list[dict] = []
    segment_aliases = {"SMB": "small business", "MID_MARKET": "Mid Market", "ENTERPRISE": "enterprise "}
    alias_indexes = set(rng.sample(range(CUSTOMER_COUNT), 24))
    missing_region_indexes = set(rng.sample([i for i in range(CUSTOMER_COUNT) if i not in alias_indexes], 12))
    for index in range(CUSTOMER_COUNT):
        segment = rng.choices(CUSTOMER_SEGMENTS, weights=(55, 30, 15))[0]
        rows.append({
            "customer_id": f"CUS{index + 1:06d}",
            "customer_name": f"Synthetic Customer Organization {index + 1:04d}",
            "customer_segment": segment_aliases[segment] if index in alias_indexes else segment,
            "region": "" if index in missing_region_indexes else rng.choice(REGIONS),
            "created_date": _random_date(rng, date(2022, 1, 1), date(2025, 6, 30)).isoformat(),
            "crm_status": rng.choices(("ACTIVE", "INACTIVE"), weights=(93, 7))[0],
            "source_system": "SYNTHETIC_CRM",
        })
    for duplicate_index in sorted(rng.sample(range(CUSTOMER_COUNT), 5)):
        rows.append(dict(rows[duplicate_index]))
    return rows, {
        "customer_duplicate_rows": 5,
        "customer_segment_aliases": len(alias_indexes),
        "customer_missing_regions": len(missing_region_indexes),
    }


def _generate_products(rng: random.Random) -> tuple[list[dict], dict[str, int]]:
    rows: list[dict] = []
    aliases = {
        "SOFTWARE": "Software", "HARDWARE": "hardware ", "SERVICES": "Professional Services",
        "SECURITY": "Cybersecurity", "CLOUD": "Cloud Services", "DATA": "data analytics",
    }
    alias_indexes = set(rng.sample(range(PRODUCT_COUNT), 18))
    unusual_price_indexes = set(rng.sample([i for i in range(PRODUCT_COUNT) if i not in alias_indexes], 4))
    for index in range(PRODUCT_COUNT):
        category = rng.choice(PRODUCT_CATEGORIES)
        unit_price = round(rng.uniform(45, 4_500), 2)
        if index in unusual_price_indexes:
            unit_price = round(rng.uniform(25_000, 45_000), 2)
        unit_cost = round(unit_price * rng.uniform(0.28, 0.72), 2)
        rows.append({
            "product_id": f"PRD{index + 1:04d}",
            "product_name": f"Synthetic {category.title()} Offering {index + 1:03d}",
            "product_category": aliases[category] if index in alias_indexes else category,
            "unit_price": f"{unit_price:.2f}",
            "unit_cost": f"{unit_cost:.2f}",
            "active_flag": "Y" if rng.random() > 0.05 else "N",
            "source_system": "SYNTHETIC_PRODUCT_MASTER",
        })
    for duplicate_index in sorted(rng.sample(range(PRODUCT_COUNT), 3)):
        rows.append(dict(rows[duplicate_index]))
    return rows, {
        "product_duplicate_rows": 3,
        "product_category_aliases": len(alias_indexes),
        "unusual_product_prices": len(unusual_price_indexes),
    }


def _generate_orders(
    rng: random.Random, customers: list[dict], products: list[dict]
) -> tuple[list[dict], dict[str, int]]:
    indexes = list(range(ORDER_COUNT))
    rng.shuffle(indexes)
    invalid_customer = set(indexes[0:14])
    missing_customer = set(indexes[14:24])
    invalid_product = set(indexes[24:36])
    malformed_date = set(indexes[36:45])
    invalid_quantity = set(indexes[45:53])
    invalid_amount = set(indexes[53:60])
    status_alias = set(indexes[60:80])
    high_value = set(indexes[80:98])
    canonical_statuses = ("COMPLETED", "SHIPPED", "CANCELLED", "RETURNED")
    alias_by_status = {"COMPLETED": "complete", "SHIPPED": "shipped ", "CANCELLED": "canceled", "RETURNED": "Return"}

    rows: list[dict] = []
    for index in range(ORDER_COUNT):
        customer = rng.choice(customers[:CUSTOMER_COUNT])
        product = rng.choice(products[:PRODUCT_COUNT])
        quantity = rng.randint(1, 12)
        if index in high_value:
            quantity = rng.randint(80, 140)
        if index in invalid_quantity:
            quantity = 0
        unit_price = float(product["unit_price"])
        discount = rng.uniform(0, 0.22)
        amount = round(quantity * unit_price * (1 - discount), 2)
        if index in invalid_amount:
            amount = round(-rng.uniform(50, 700), 2)
        status = rng.choices(canonical_statuses, weights=(71, 14, 9, 6))[0]
        rows.append({
            "order_id": f"ORD{index + 1:07d}",
            "customer_id": "" if index in missing_customer else (
                f"CUS_UNKNOWN_{index + 1:04d}" if index in invalid_customer else customer["customer_id"]
            ),
            "product_id": f"PRD_UNKNOWN_{index + 1:04d}" if index in invalid_product else product["product_id"],
            "order_date": "2025-13-40" if index in malformed_date else _random_date(rng, date(2025, 1, 1), date(2025, 12, 31)).isoformat(),
            "quantity": str(quantity),
            "unit_price": f"{unit_price:.2f}",
            "discount_rate": f"{discount:.4f}",
            "order_amount": f"{amount:.2f}",
            "order_status": alias_by_status[status] if index in status_alias else status,
            "channel": rng.choice(("DIRECT", "PARTNER", "ONLINE")),
            "source_system": "SYNTHETIC_ORDER_PLATFORM",
        })
    for duplicate_index in sorted(rng.sample(range(ORDER_COUNT), 8)):
        rows.append(dict(rows[duplicate_index]))
    return rows, {
        "order_duplicate_rows": 8,
        "orders_invalid_customer": len(invalid_customer),
        "orders_missing_customer": len(missing_customer),
        "orders_invalid_product": len(invalid_product),
        "orders_malformed_date": len(malformed_date),
        "orders_invalid_quantity": len(invalid_quantity),
        "orders_invalid_amount": len(invalid_amount),
        "order_status_aliases": len(status_alias),
        "high_value_orders": len(high_value),
    }


def _generate_tickets(rng: random.Random, customers: list[dict]) -> tuple[list[dict], dict[str, int]]:
    indexes = list(range(TICKET_COUNT))
    rng.shuffle(indexes)
    invalid_customer = set(indexes[0:10])
    malformed_open = set(indexes[10:16])
    reverse_resolution = set(indexes[16:24])
    missing_issue = set(indexes[24:36])
    priority_alias = set(indexes[36:51])
    alias_by_priority = {"LOW": "low ", "MEDIUM": "Med", "HIGH": "high-priority", "CRITICAL": "urgent"}
    rows: list[dict] = []
    for index in range(TICKET_COUNT):
        customer = rng.choice(customers[:CUSTOMER_COUNT])
        opened = datetime.combine(_random_date(rng, date(2025, 1, 1), date(2025, 12, 31)), datetime.min.time())
        opened += timedelta(hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        status = rng.choices(("OPEN", "RESOLVED", "CLOSED"), weights=(12, 43, 45))[0]
        resolution_hours = rng.randint(2, 168)
        resolved = "" if status == "OPEN" else (opened + timedelta(hours=resolution_hours)).isoformat(timespec="minutes")
        if index in reverse_resolution:
            resolved = (opened - timedelta(hours=rng.randint(1, 24))).isoformat(timespec="minutes")
            status = "RESOLVED"
        priority = rng.choices(("LOW", "MEDIUM", "HIGH", "CRITICAL"), weights=(28, 42, 23, 7))[0]
        rows.append({
            "ticket_id": f"TKT{index + 1:07d}",
            "customer_id": f"CUS_UNKNOWN_{index + 1:04d}" if index in invalid_customer else customer["customer_id"],
            "opened_at": "not-a-date" if index in malformed_open else opened.isoformat(timespec="minutes"),
            "resolved_at": resolved,
            "ticket_status": status,
            "priority": alias_by_priority[priority] if index in priority_alias else priority,
            "issue_category": "" if index in missing_issue else rng.choice(("BILLING", "PRODUCT", "ACCESS", "INTEGRATION", "SERVICE")),
            "satisfaction_score": "" if status == "OPEN" else str(rng.randint(1, 5)),
            "source_system": "SYNTHETIC_SUPPORT_DESK",
        })
    for duplicate_index in sorted(rng.sample(range(TICKET_COUNT), 6)):
        rows.append(dict(rows[duplicate_index]))
    return rows, {
        "ticket_duplicate_rows": 6,
        "tickets_invalid_customer": len(invalid_customer),
        "tickets_malformed_date": len(malformed_open),
        "tickets_reverse_resolution": len(reverse_resolution),
        "tickets_missing_issue": len(missing_issue),
        "ticket_priority_aliases": len(priority_alias),
    }


def _canonical_order_status(value: str) -> str:
    return {
        "complete": "COMPLETED", "shipped ": "SHIPPED", "canceled": "CANCELLED", "Return": "RETURNED",
    }.get(value, value)


def _generate_finance(rng: random.Random, orders: list[dict]) -> tuple[list[dict], dict[str, int]]:
    indexes = list(range(ORDER_COUNT))
    rng.shuffle(indexes)
    invalid_order = set(indexes[0:11])
    malformed_date = set(indexes[11:18])
    amount_mismatch = set(indexes[18:36])
    type_alias = set(indexes[36:51])
    rows: list[dict] = []
    for index, order in enumerate(orders[:ORDER_COUNT]):
        status = _canonical_order_status(order["order_status"])
        order_amount = float(order["order_amount"])
        if status in {"COMPLETED", "SHIPPED"}:
            amount = order_amount
            transaction_type = "SALE"
        elif status == "RETURNED":
            amount = -abs(order_amount)
            transaction_type = "REFUND"
        else:
            amount = 0.0
            transaction_type = "ADJUSTMENT"
        if index in amount_mismatch:
            amount = round(amount + rng.uniform(25, 500), 2)
        raw_type = {"SALE": "sale ", "REFUND": "Credit", "ADJUSTMENT": "adjustment"}[transaction_type] if index in type_alias else transaction_type
        order_date = order["order_date"] if order["order_date"] != "2025-13-40" else "2025-06-15"
        posted_date = date.fromisoformat(order_date) + timedelta(days=rng.randint(0, 5))
        rows.append({
            "finance_transaction_id": f"FIN{index + 1:07d}",
            "order_id": f"ORD_UNKNOWN_{index + 1:04d}" if index in invalid_order else order["order_id"],
            "posted_date": "31/31/2025" if index in malformed_date else posted_date.isoformat(),
            "transaction_type": raw_type,
            "transaction_amount": f"{amount:.2f}",
            "currency": "USD",
            "posting_status": rng.choices(("POSTED", "PENDING"), weights=(97, 3))[0],
            "source_system": "SYNTHETIC_FINANCE_LEDGER",
        })
    for duplicate_index in sorted(rng.sample(range(ORDER_COUNT), 6)):
        rows.append(dict(rows[duplicate_index]))
    return rows, {
        "finance_duplicate_rows": 6,
        "finance_invalid_order": len(invalid_order),
        "finance_malformed_date": len(malformed_date),
        "finance_amount_mismatches": len(amount_mismatch),
        "finance_type_aliases": len(type_alias),
    }


def generate_synthetic_data() -> dict:
    """Generate every raw source and return counts/control metadata."""
    ensure_directories()
    rng = random.Random(RANDOM_SEED)
    customers, customer_issues = _generate_customers(rng)
    products, product_issues = _generate_products(rng)
    orders, order_issues = _generate_orders(rng, customers, products)
    tickets, ticket_issues = _generate_tickets(rng, customers)
    finance, finance_issues = _generate_finance(rng, orders)

    datasets = {
        "customers.csv": customers,
        "products.csv": products,
        "orders.csv": orders,
        "support_tickets.csv": tickets,
        "finance_transactions.csv": finance,
    }
    for filename, rows in datasets.items():
        _write_csv(RAW_DIR / filename, rows, list(rows[0]))

    return {
        "seed": RANDOM_SEED,
        "source_rows": {name.removesuffix(".csv"): len(rows) for name, rows in datasets.items()},
        "unique_business_records": {
            "customers": CUSTOMER_COUNT,
            "products": PRODUCT_COUNT,
            "orders": ORDER_COUNT,
            "support_tickets": TICKET_COUNT,
            "finance_transactions": ORDER_COUNT,
        },
        "controlled_issues": {
            **customer_issues, **product_issues, **order_issues, **ticket_issues, **finance_issues,
        },
    }


if __name__ == "__main__":
    print(generate_synthetic_data())
