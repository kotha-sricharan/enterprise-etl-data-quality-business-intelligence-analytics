"""Central paths, reproducibility settings, and governed domain values."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
SQL_DIR = PROJECT_ROOT / "sql"
DATABASE_PATH = PROCESSED_DIR / "enterprise_analytics.db"

RANDOM_SEED = 20260827
CUSTOMER_COUNT = 1_200
PRODUCT_COUNT = 120
ORDER_COUNT = 8_000
TICKET_COUNT = 2_500

CUSTOMER_SEGMENTS = ("SMB", "MID_MARKET", "ENTERPRISE")
REGIONS = ("NORTH", "SOUTH", "EAST", "WEST")
PRODUCT_CATEGORIES = ("SOFTWARE", "HARDWARE", "SERVICES", "SECURITY", "CLOUD", "DATA")
ORDER_STATUSES = ("COMPLETED", "SHIPPED", "CANCELLED", "RETURNED")
TICKET_PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
TICKET_STATUSES = ("OPEN", "RESOLVED", "CLOSED")
FINANCE_TYPES = ("SALE", "REFUND", "ADJUSTMENT")


def ensure_directories() -> None:
    """Create project-owned runtime directories without touching external paths."""
    for directory in (RAW_DIR, PROCESSED_DIR, OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
