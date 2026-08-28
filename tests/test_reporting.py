"""Unit tests that prove reports use calculated inputs."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.reporting import generate_reports


class ReportingTests(unittest.TestCase):
    def test_business_report_uses_calculated_data(self):
        overall = {
            "net_revenue": 123.45, "fulfilled_order_value": 150.0, "order_count": 2,
            "average_order_value": 75.0, "ordering_customer_count": 1, "ticket_volume": 1,
            "ticket_resolution_rate": 100.0, "average_resolution_hours": 2.0, "ticket_sla_rate": 100.0,
            "cancellation_rate": 0.0, "pending_finance_transactions": 0, "exception_count": 0,
            "quarantined_record_count": 0, "data_quality_score": 100.0,
        }
        monthly = [{
            "reporting_month": "2025-01", "order_count": 2, "unique_customers": 1, "units_sold": 2,
            "fulfilled_order_value": 150.0, "net_revenue": 123.45, "revenue_mom_growth_pct": None,
            "average_order_value": 75.0, "cancellation_rate": 0.0, "ticket_volume": 1,
            "ticket_resolution_rate": 100.0, "ticket_sla_rate": 100.0, "average_resolution_hours": 2.0,
            "revenue_zscore": 0.0, "revenue_anomaly_flag": "N",
        }]
        category = {"product_category": "SOFTWARE", "order_count": 2, "customers": 1, "units_sold": 2, "fulfilled_order_value": 150.0, "net_revenue": 123.45}
        segment = {"customer_segment": "SMB", "order_count": 2, "customers": 1, "fulfilled_order_value": 150.0, "average_order_value": 75.0, "customers_with_tickets": 1}
        analytics = {
            "overall": overall, "monthly": monthly, "categories": [category], "segments": [segment],
            "dashboard": [{"reporting_month": "2025-01", "product_category": "SOFTWARE", "order_count": 2}],
            "top_category": category, "top_segment": segment, "highest_revenue_month": monthly[0], "lowest_sla_month": monthly[0],
        }
        etl = {
            "source_counts": {}, "unique_counts": {}, "loaded_counts": {},
            "quarantine_counts": {"orders": 0, "support_tickets": 0, "finance_transactions": 0},
            "quality": {"critical_error_count": 0, "critical_errors": [], "duplicate_counts": {}, "issue_counts": {}, "controls": []},
            "quality_issues": [],
            "reconciliation": [{"control_name": "test", "dataset": "test", "unit": "COUNT", "source_value": 1, "target_value": 1, "difference": 0, "status": "PASS"}],
        }
        with tempfile.TemporaryDirectory() as directory, patch("src.reporting.OUTPUT_DIR", Path(directory)):
            paths = generate_reports(
                {"source_rows": {"test": 2}}, {"totals": {"duplicate_rows": 0, "null_cells": 0}}, etl, analytics,
            )
            report = (Path(directory) / "business_report.md").read_text(encoding="utf-8")
            self.assertEqual(len(paths), 5)
            self.assertIn("$123.45", report)
            self.assertIn("2 loaded orders", report)


if __name__ == "__main__":
    unittest.main()
