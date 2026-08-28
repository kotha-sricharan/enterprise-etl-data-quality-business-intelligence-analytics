"""Unit tests for transformations and reconciliation failure behavior."""
import unittest

from src.etl import reconcile_partition
from src.quality import DataQualityError
from src.transform import amount_to_cents, standardize_order_status, transform_order


class EtlTests(unittest.TestCase):
    def test_currency_conversion_uses_integer_cents(self):
        self.assertEqual(amount_to_cents("10.235"), 1024)

    def test_alias_standardization(self):
        self.assertEqual(standardize_order_status("canceled"), "CANCELLED")

    def test_transform_order_creates_typed_fact(self):
        row = {
            "order_id": "O1", "customer_id": "C1", "product_id": "P1", "order_date": "2025-02-01",
            "quantity": "3", "unit_price": "20.00", "discount_rate": "0.0500", "order_amount": "57.00",
            "order_status": "complete", "channel": "online",
        }
        transformed = transform_order(row, ["CATEGORY_STANDARDIZED"])
        self.assertEqual(transformed["order_amount_cents"], 5700)
        self.assertEqual(transformed["quantity"], 3)
        self.assertEqual(transformed["order_status"], "COMPLETED")

    def test_reconciliation_count_and_amount_match(self):
        source = [{"order_id": "O1", "amount": "10.00"}, {"order_id": "O2", "amount": "5.00"}]
        loaded = [{"amount_cents": 1000}]
        quarantine = [{"amount_cents": 500}]
        controls = reconcile_partition("test", source, loaded, quarantine, "amount", "amount_cents")
        self.assertTrue(all(control["status"] == "PASS" for control in controls))

    def test_reconciliation_fails_loudly(self):
        with self.assertRaises(DataQualityError):
            reconcile_partition("test", [{"order_id": "O1"}], [], [])


if __name__ == "__main__":
    unittest.main()
