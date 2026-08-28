"""Unit tests for reusable data-quality controls."""
import unittest

from src.quality import find_duplicates, invalid_foreign_keys, missing_required_fields, validate_sources


def valid_sources():
    customers = [{
        "customer_id": "C1", "customer_name": "Synthetic Customer", "customer_segment": "SMB",
        "region": "NORTH", "created_date": "2025-01-01", "crm_status": "ACTIVE",
    }]
    products = [{
        "product_id": "P1", "product_name": "Synthetic Product", "product_category": "SOFTWARE",
        "unit_price": "100.00", "unit_cost": "40.00", "active_flag": "Y",
    }]
    orders = [{
        "order_id": "O1", "customer_id": "C1", "product_id": "P1", "order_date": "2025-01-15",
        "quantity": "2", "unit_price": "100.00", "discount_rate": "0.10", "order_amount": "180.00",
        "order_status": "COMPLETED", "channel": "DIRECT",
    }]
    tickets = [{
        "ticket_id": "T1", "customer_id": "C1", "opened_at": "2025-01-01T10:00",
        "resolved_at": "2025-01-01T14:00", "ticket_status": "RESOLVED", "priority": "HIGH",
        "issue_category": "ACCESS", "satisfaction_score": "5",
    }]
    finance = [{
        "finance_transaction_id": "F1", "order_id": "O1", "posted_date": "2025-01-16",
        "transaction_type": "SALE", "transaction_amount": "180.00", "currency": "USD", "posting_status": "POSTED",
    }]
    return customers, products, orders, tickets, finance


class QualityTests(unittest.TestCase):
    def test_duplicate_detection(self):
        rows = [{"id": "A"}, {"id": "A"}, {"id": "B"}]
        self.assertEqual(find_duplicates(rows, "id"), ["A"])

    def test_missing_required_field_logic(self):
        rows = [{"id": "A", "name": ""}, {"id": "B", "name": "Present"}]
        self.assertEqual(missing_required_fields(rows, ("id", "name"), "id"), [{"record_id": "A", "fields": ["name"]}])

    def test_foreign_key_validation(self):
        rows = [{"id": "1", "customer_id": "C1"}, {"id": "2", "customer_id": "BAD"}]
        self.assertEqual(invalid_foreign_keys(rows, "customer_id", {"C1"}, "id"), ["2"])

    def test_invalid_order_customer_is_quarantined(self):
        customers, products, orders, tickets, finance = valid_sources()
        orders[0]["customer_id"] = "UNKNOWN"
        result = validate_sources(customers, products, orders, tickets, finance)
        self.assertIn("O1", result["quarantine_ids"]["orders"])
        self.assertEqual(result["critical_error_count"], 0)


if __name__ == "__main__":
    unittest.main()
