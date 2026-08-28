"""Extract, validate, transform, reconcile, and load the SQLite warehouse."""
from __future__ import annotations

import csv
import sqlite3
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.config import DATABASE_PATH, RAW_DIR, SQL_DIR, ensure_directories
from src.quality import DataQualityError, validate_sources
from src.transform import (
    amount_to_cents,
    transform_customer,
    transform_finance,
    transform_order,
    transform_product,
    transform_ticket,
)


def read_csv(path: Path) -> list[dict]:
    """Extract one UTF-8 CSV source into row dictionaries."""
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _source_cents(row: dict, field: str, identifier: str) -> int:
    try:
        return amount_to_cents(row[field])
    except (InvalidOperation, ValueError, TypeError, KeyError) as error:
        raise DataQualityError(f"Cannot reconcile {identifier}: {field} is not numeric") from error


def reconcile_partition(
    control_prefix: str,
    unique_source: list[dict],
    loaded: list[dict],
    quarantined: list[dict],
    source_amount_field: str | None = None,
    target_amount_field: str | None = None,
) -> list[dict]:
    """Prove count and optional amount conservation for one fact source."""
    controls = [{
        "control_name": f"{control_prefix}_count",
        "dataset": control_prefix,
        "unit": "COUNT",
        "source_value": len(unique_source),
        "target_value": len(loaded) + len(quarantined),
    }]
    if source_amount_field and target_amount_field:
        controls.append({
            "control_name": f"{control_prefix}_amount_cents",
            "dataset": control_prefix,
            "unit": "CENTS",
            "source_value": sum(_source_cents(row, source_amount_field, row.get(next(iter(row)), "UNKNOWN")) for row in unique_source),
            "target_value": sum(row[target_amount_field] for row in loaded) + sum((row[target_amount_field] or 0) for row in quarantined),
        })
    for control in controls:
        control["difference"] = control["source_value"] - control["target_value"]
        control["status"] = "PASS" if control["difference"] == 0 else "FAIL"
    if any(control["status"] == "FAIL" for control in controls):
        failed = ", ".join(control["control_name"] for control in controls if control["status"] == "FAIL")
        raise DataQualityError(f"Critical source-to-target reconciliation failed: {failed}")
    return controls


def _safe_cents(value: str) -> int | None:
    try:
        return amount_to_cents(value)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _load_database(
    customers: list[dict], products: list[dict], orders: list[dict], tickets: list[dict],
    finance: list[dict], order_quarantine: list[dict], ticket_quarantine: list[dict],
    finance_quarantine: list[dict], issues: list[dict], controls: list[dict],
) -> None:
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.executescript((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
        connection.executemany(
            "INSERT INTO dim_customer VALUES (:customer_id,:customer_name,:customer_segment,:region,:created_date,:crm_status,:quality_flag)", customers,
        )
        connection.executemany(
            "INSERT INTO dim_product VALUES (:product_id,:product_name,:product_category,:unit_price_cents,:unit_cost_cents,:active_flag,:quality_flag)", products,
        )
        connection.executemany(
            """INSERT INTO fact_order VALUES (
                :order_id,:customer_id,:product_id,:order_date,:order_month,:quantity,:unit_price_cents,
                :discount_basis_points,:order_amount_cents,:order_status,:channel,:quality_flag
            )""", orders,
        )
        connection.executemany(
            """INSERT INTO fact_support_ticket VALUES (
                :ticket_id,:customer_id,:opened_at,:opened_month,:resolved_at,:ticket_status,:priority,
                :issue_category,:resolution_hours,:satisfaction_score,:quality_flag
            )""", tickets,
        )
        connection.executemany(
            """INSERT INTO fact_finance_transaction VALUES (
                :finance_transaction_id,:order_id,:posted_date,:posted_month,:transaction_type,
                :transaction_amount_cents,:currency,:posting_status,:quality_flag
            )""", finance,
        )
        connection.executemany(
            "INSERT INTO order_quarantine VALUES (:order_id,:customer_id,:product_id,:order_date,:order_amount_cents,:quarantine_reason)", order_quarantine,
        )
        connection.executemany(
            "INSERT INTO support_ticket_quarantine VALUES (:ticket_id,:customer_id,:opened_at,:quarantine_reason)", ticket_quarantine,
        )
        connection.executemany(
            "INSERT INTO finance_transaction_quarantine VALUES (:finance_transaction_id,:order_id,:posted_date,:transaction_amount_cents,:quarantine_reason)", finance_quarantine,
        )
        exception_rows = [dict(exception_id=f"DQ{index:06d}", **issue) for index, issue in enumerate(issues, 1)]
        connection.executemany(
            "INSERT INTO data_quality_exception VALUES (:exception_id,:dataset,:record_id,:issue_type,:severity,:action,:message)", exception_rows,
        )
        connection.executemany(
            "INSERT INTO etl_control VALUES (:control_name,:dataset,:unit,:source_value,:target_value,:difference,:status)", controls,
        )
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise DataQualityError(f"Warehouse foreign-key validation failed: {violations[:5]}")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def run_etl() -> dict:
    """Execute the governed ETL workflow and return audit metadata."""
    ensure_directories()
    sources = {
        "customers": read_csv(RAW_DIR / "customers.csv"),
        "products": read_csv(RAW_DIR / "products.csv"),
        "orders": read_csv(RAW_DIR / "orders.csv"),
        "support_tickets": read_csv(RAW_DIR / "support_tickets.csv"),
        "finance_transactions": read_csv(RAW_DIR / "finance_transactions.csv"),
    }
    quality = validate_sources(
        sources["customers"], sources["products"], sources["orders"],
        sources["support_tickets"], sources["finance_transactions"],
    )
    unique = quality["unique_rows"]
    issue_map: dict[tuple[str, str], list[str]] = defaultdict(list)
    for issue in quality["issues"]:
        issue_map[(issue["dataset"], issue["record_id"])].append(issue["issue_type"])

    customers = [transform_customer(row, issue_map[("customers", row["customer_id"])]) for row in unique["customers"]]
    products = [transform_product(row, issue_map[("products", row["product_id"])]) for row in unique["products"]]

    order_q_ids = set(quality["quarantine_ids"]["orders"])
    orders, order_quarantine = [], []
    for row in unique["orders"]:
        identifier = row["order_id"]
        if identifier in order_q_ids:
            order_quarantine.append({
                "order_id": identifier, "customer_id": row.get("customer_id") or None,
                "product_id": row.get("product_id") or None, "order_date": row.get("order_date") or None,
                "order_amount_cents": _safe_cents(row.get("order_amount", "")),
                "quarantine_reason": "|".join(sorted(set(issue_map[("orders", identifier)]))),
            })
        else:
            orders.append(transform_order(row, issue_map[("orders", identifier)]))

    ticket_q_ids = set(quality["quarantine_ids"]["support_tickets"])
    tickets, ticket_quarantine = [], []
    for row in unique["support_tickets"]:
        identifier = row["ticket_id"]
        if identifier in ticket_q_ids:
            ticket_quarantine.append({
                "ticket_id": identifier, "customer_id": row.get("customer_id") or None,
                "opened_at": row.get("opened_at") or None,
                "quarantine_reason": "|".join(sorted(set(issue_map[("support_tickets", identifier)]))),
            })
        else:
            tickets.append(transform_ticket(row, issue_map[("support_tickets", identifier)]))

    loaded_order_ids = {row["order_id"] for row in orders}
    finance_q_ids = set(quality["quarantine_ids"]["finance_transactions"])
    cascade_count = 0
    for row in unique["finance_transactions"]:
        identifier = row["finance_transaction_id"]
        if row.get("order_id") not in loaded_order_ids and identifier not in finance_q_ids:
            cascade_count += 1
            finance_q_ids.add(identifier)
            issue = {
                "dataset": "finance_transactions", "record_id": identifier,
                "issue_type": "ORDER_NOT_LOADED", "severity": "HIGH", "action": "QUARANTINE",
                "message": "Referenced order was quarantined and is unavailable to the warehouse fact",
            }
            quality["issues"].append(issue)
            issue_map[("finance_transactions", identifier)].append("ORDER_NOT_LOADED")
    if cascade_count:
        quality["controls"].append({
            "dataset": "finance_transactions", "control": "ORDER_NOT_LOADED", "severity": "HIGH",
            "action": "QUARANTINE", "issue_count": cascade_count, "status": "WARNING",
        })
    quality["quarantine_ids"]["finance_transactions"] = sorted(finance_q_ids)

    finance, finance_quarantine = [], []
    for row in unique["finance_transactions"]:
        identifier = row["finance_transaction_id"]
        if identifier in finance_q_ids:
            finance_quarantine.append({
                "finance_transaction_id": identifier, "order_id": row.get("order_id") or None,
                "posted_date": row.get("posted_date") or None,
                "transaction_amount_cents": _safe_cents(row.get("transaction_amount", "")),
                "quarantine_reason": "|".join(sorted(set(issue_map[("finance_transactions", identifier)]))),
            })
        else:
            finance.append(transform_finance(row, issue_map[("finance_transactions", identifier)]))

    controls = []
    controls.extend(reconcile_partition("orders", unique["orders"], orders, order_quarantine, "order_amount", "order_amount_cents"))
    controls.extend(reconcile_partition("support_tickets", unique["support_tickets"], tickets, ticket_quarantine))
    controls.extend(reconcile_partition(
        "finance_transactions", unique["finance_transactions"], finance, finance_quarantine,
        "transaction_amount", "transaction_amount_cents",
    ))
    _load_database(
        customers, products, orders, tickets, finance, order_quarantine, ticket_quarantine,
        finance_quarantine, quality["issues"], controls,
    )
    issue_counts = Counter(issue["issue_type"] for issue in quality["issues"])
    return {
        "source_counts": {dataset: len(rows) for dataset, rows in sources.items()},
        "unique_counts": {dataset: len(rows) for dataset, rows in unique.items()},
        "loaded_counts": {
            "customers": len(customers), "products": len(products), "orders": len(orders),
            "support_tickets": len(tickets), "finance_transactions": len(finance),
        },
        "quarantine_counts": {
            "orders": len(order_quarantine), "support_tickets": len(ticket_quarantine),
            "finance_transactions": len(finance_quarantine),
        },
        "quality": {
            "critical_error_count": quality["critical_error_count"],
            "critical_errors": quality["critical_errors"],
            "duplicate_counts": quality["duplicate_counts"],
            "issue_counts": dict(sorted(issue_counts.items())),
            "controls": quality["controls"],
            "quarantine_ids": quality["quarantine_ids"],
        },
        "quality_issues": quality["issues"],
        "reconciliation": controls,
        "database_path": str(DATABASE_PATH),
    }
