"""Unit tests for KPI calculations against a controlled SQLite model."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.analytics import calculate_analytics, compute_quality_score
from src.config import SQL_DIR


class AnalyticsTests(unittest.TestCase):
    def test_quality_score_penalizes_quarantine(self):
        clean = compute_quality_score(100, [], 0)
        affected = compute_quality_score(100, [{"severity": "MEDIUM", "action": "REVIEW"}], 2)
        self.assertEqual(clean, 100.0)
        self.assertLess(affected, clean)

    def test_calculated_kpis_use_warehouse_facts(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.db"
            connection = sqlite3.connect(database)
            connection.executescript((SQL_DIR / "schema.sql").read_text(encoding="utf-8"))
            connection.execute("INSERT INTO dim_customer VALUES ('C1','Synthetic','SMB','NORTH','2025-01-01','ACTIVE','PASS')")
            connection.execute("INSERT INTO dim_product VALUES ('P1','Synthetic','SOFTWARE',10000,4000,'Y','PASS')")
            connection.executemany(
                "INSERT INTO fact_order VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    ("O1","C1","P1","2025-01-02","2025-01",1,10000,0,10000,"COMPLETED","DIRECT","PASS"),
                    ("O2","C1","P1","2025-01-03","2025-01",1,5000,0,5000,"CANCELLED","ONLINE","PASS"),
                ],
            )
            connection.executemany(
                "INSERT INTO fact_finance_transaction VALUES (?,?,?,?,?,?,?,?,?)",
                [
                    ("F1","O1","2025-01-03","2025-01","SALE",10000,"USD","POSTED","PASS"),
                    ("F2","O2","2025-01-04","2025-01","ADJUSTMENT",0,"USD","POSTED","PASS"),
                ],
            )
            connection.execute(
                "INSERT INTO fact_support_ticket VALUES ('T1','C1','2025-01-01T10:00','2025-01','2025-01-01T20:00','RESOLVED','HIGH','ACCESS',10,5,'PASS')"
            )
            connection.commit()
            connection.close()
            etl = {
                "unique_counts": {"customers": 1, "products": 1, "orders": 2, "support_tickets": 1, "finance_transactions": 2},
                "quarantine_counts": {"orders": 0, "support_tickets": 0, "finance_transactions": 0},
                "quality_issues": [],
            }
            result = calculate_analytics(etl, database)
            self.assertEqual(result["overall"]["net_revenue"], 100.0)
            self.assertEqual(result["overall"]["order_count"], 2)
            self.assertEqual(result["overall"]["average_order_value"], 100.0)
            self.assertEqual(result["overall"]["cancellation_rate"], 50.0)
            self.assertEqual(result["overall"]["ticket_sla_rate"], 100.0)


if __name__ == "__main__":
    unittest.main()
