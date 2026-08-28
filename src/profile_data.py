"""Reusable raw-data profiling for counts, completeness, ranges, and distributions."""
from __future__ import annotations

import csv
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.config import OUTPUT_DIR, RAW_DIR, ensure_directories

PRIMARY_KEYS = {
    "customers": "customer_id",
    "products": "product_id",
    "orders": "order_id",
    "support_tickets": "ticket_id",
    "finance_transactions": "finance_transaction_id",
}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _numeric_summary(values: list[str]) -> dict | None:
    parsed: list[Decimal] = []
    try:
        parsed = [Decimal(value) for value in values]
    except (InvalidOperation, TypeError):
        return None
    if not parsed:
        return None
    return {
        "count": len(parsed),
        "min": float(min(parsed)),
        "max": float(max(parsed)),
        "mean": round(float(sum(parsed) / len(parsed)), 4),
        "sum": round(float(sum(parsed)), 2),
    }


def profile_rows(rows: list[dict], primary_key: str) -> dict:
    """Profile one in-memory table without mutating its source rows."""
    if not rows:
        return {"row_count": 0, "column_count": 0, "duplicate_row_count": 0, "columns": {}}
    row_signatures = [tuple(sorted(row.items())) for row in rows]
    key_counts = Counter(row.get(primary_key, "") for row in rows if row.get(primary_key, ""))
    columns: dict[str, dict] = {}
    for column in rows[0]:
        raw_values = [row.get(column, "") for row in rows]
        populated = [str(value) for value in raw_values if value not in (None, "")]
        counts = Counter(populated)
        numeric = _numeric_summary(populated)
        profile = {
            "null_count": len(raw_values) - len(populated),
            "unique_count": len(counts),
            "duplicate_value_count": sum(count - 1 for count in counts.values() if count > 1),
            "min": min(populated) if populated else None,
            "max": max(populated) if populated else None,
            "numeric_summary": numeric,
            "top_values": [
                {"value": value, "count": count}
                for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
            ],
        }
        columns[column] = profile
    return {
        "row_count": len(rows),
        "column_count": len(rows[0]),
        "duplicate_row_count": len(row_signatures) - len(set(row_signatures)),
        "duplicate_primary_key_count": sum(1 for count in key_counts.values() if count > 1),
        "primary_key": primary_key,
        "columns": columns,
    }


def profile_sources(output_path: Path | None = None) -> dict:
    """Profile all generated CSVs and persist machine-readable evidence."""
    ensure_directories()
    datasets = {}
    for dataset, primary_key in PRIMARY_KEYS.items():
        datasets[dataset] = profile_rows(read_csv(RAW_DIR / f"{dataset}.csv"), primary_key)
    payload = {
        "profile_version": "1.0",
        "scope": "raw synthetic source files before remediation",
        "datasets": datasets,
        "totals": {
            "rows_profiled": sum(item["row_count"] for item in datasets.values()),
            "duplicate_rows": sum(item["duplicate_row_count"] for item in datasets.values()),
            "null_cells": sum(
                column["null_count"]
                for item in datasets.values()
                for column in item["columns"].values()
            ),
        },
    }
    target = output_path or OUTPUT_DIR / "data_profile.json"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
