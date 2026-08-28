"""Enterprise KPI, trend, segmentation, and dashboard analytics."""
from __future__ import annotations

import sqlite3
from statistics import mean, pstdev

from src.config import DATABASE_PATH


def _money(cents: int | float | None) -> float:
    return round((cents or 0) / 100, 2)


def compute_quality_score(total_records: int, issues: list[dict], quarantine_count: int) -> float:
    """Calculate a transparent issue-weighted score on a zero-to-100 scale."""
    if total_records <= 0:
        return 0.0
    critical = sum(issue.get("severity") == "CRITICAL" for issue in issues)
    review_or_remediation = sum(issue.get("action") in {"REVIEW", "STANDARDIZE", "DEFAULT_UNKNOWN", "DEDUPLICATE"} for issue in issues)
    weighted_defects = critical * 5 + quarantine_count * 1.5 + review_or_remediation * 0.25
    return round(max(0.0, 100 * (1 - weighted_defects / total_records)), 2)


def calculate_analytics(etl: dict, database_path=DATABASE_PATH) -> dict:
    """Calculate company, monthly, product, customer, and exception measures."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    overall = connection.execute(
        """SELECT COUNT(*) AS order_count,
                  COUNT(DISTINCT customer_id) AS ordering_customers,
                  SUM(CASE WHEN order_status IN ('COMPLETED','SHIPPED') THEN order_amount_cents ELSE 0 END) AS fulfilled_value_cents,
                  AVG(CASE WHEN order_status IN ('COMPLETED','SHIPPED') THEN order_amount_cents END) AS average_order_cents,
                  SUM(CASE WHEN order_status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders
           FROM fact_order"""
    ).fetchone()
    finance = connection.execute(
        """SELECT SUM(CASE WHEN posting_status='POSTED' THEN transaction_amount_cents ELSE 0 END) AS net_revenue_cents,
                  SUM(CASE WHEN posting_status='PENDING' THEN 1 ELSE 0 END) AS pending_transactions
           FROM fact_finance_transaction"""
    ).fetchone()
    support = connection.execute(
        """SELECT COUNT(*) AS ticket_count,
                  SUM(CASE WHEN ticket_status IN ('RESOLVED','CLOSED') THEN 1 ELSE 0 END) AS resolved_count,
                  AVG(CASE WHEN resolution_hours IS NOT NULL THEN resolution_hours END) AS average_resolution_hours,
                  SUM(CASE WHEN resolution_hours IS NOT NULL AND resolution_hours <=
                      CASE priority WHEN 'CRITICAL' THEN 24 WHEN 'HIGH' THEN 48 WHEN 'MEDIUM' THEN 72 ELSE 120 END
                      THEN 1 ELSE 0 END) AS within_sla,
                  SUM(CASE WHEN resolution_hours IS NOT NULL THEN 1 ELSE 0 END) AS eligible_sla
           FROM fact_support_ticket"""
    ).fetchone()

    monthly_order_rows = connection.execute(
        """SELECT order_month,
                  COUNT(*) AS order_count,
                  COUNT(DISTINCT customer_id) AS unique_customers,
                  SUM(quantity) AS units,
                  SUM(CASE WHEN order_status IN ('COMPLETED','SHIPPED') THEN order_amount_cents ELSE 0 END) AS fulfilled_value_cents,
                  AVG(CASE WHEN order_status IN ('COMPLETED','SHIPPED') THEN order_amount_cents END) AS average_order_cents,
                  SUM(CASE WHEN order_status='CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders
           FROM fact_order GROUP BY order_month ORDER BY order_month"""
    ).fetchall()
    monthly_finance = {
        row["posted_month"]: row
        for row in connection.execute(
            """SELECT posted_month,
                      SUM(CASE WHEN posting_status='POSTED' THEN transaction_amount_cents ELSE 0 END) AS net_revenue_cents,
                      SUM(CASE WHEN posting_status='PENDING' THEN 1 ELSE 0 END) AS pending_transactions
               FROM fact_finance_transaction GROUP BY posted_month"""
        ).fetchall()
    }
    monthly_support = {
        row["opened_month"]: row
        for row in connection.execute(
            """SELECT opened_month, COUNT(*) AS ticket_volume,
                      SUM(CASE WHEN ticket_status IN ('RESOLVED','CLOSED') THEN 1 ELSE 0 END) AS resolved_count,
                      AVG(CASE WHEN resolution_hours IS NOT NULL THEN resolution_hours END) AS average_resolution_hours,
                      SUM(CASE WHEN resolution_hours IS NOT NULL AND resolution_hours <=
                          CASE priority WHEN 'CRITICAL' THEN 24 WHEN 'HIGH' THEN 48 WHEN 'MEDIUM' THEN 72 ELSE 120 END
                          THEN 1 ELSE 0 END) AS within_sla,
                      SUM(CASE WHEN resolution_hours IS NOT NULL THEN 1 ELSE 0 END) AS eligible_sla
               FROM fact_support_ticket GROUP BY opened_month"""
        ).fetchall()
    }
    category_rows = connection.execute(
        """SELECT p.product_category, COUNT(*) AS order_count, COUNT(DISTINCT o.customer_id) AS customers,
                  SUM(o.quantity) AS units,
                  SUM(CASE WHEN o.order_status IN ('COMPLETED','SHIPPED') THEN o.order_amount_cents ELSE 0 END) AS fulfilled_value_cents,
                  SUM(COALESCE(CASE WHEN f.posting_status='POSTED' THEN f.transaction_amount_cents END,0)) AS net_revenue_cents
           FROM fact_order o JOIN dim_product p ON p.product_id=o.product_id
           LEFT JOIN fact_finance_transaction f ON f.order_id=o.order_id
           GROUP BY p.product_category ORDER BY net_revenue_cents DESC"""
    ).fetchall()
    segment_rows = connection.execute(
        """WITH order_metrics AS (
               SELECT c.customer_segment, COUNT(o.order_id) AS order_count,
                      COUNT(DISTINCT o.customer_id) AS customers,
                      SUM(CASE WHEN o.order_status IN ('COMPLETED','SHIPPED') THEN o.order_amount_cents ELSE 0 END) AS fulfilled_value_cents,
                      AVG(CASE WHEN o.order_status IN ('COMPLETED','SHIPPED') THEN o.order_amount_cents END) AS average_order_cents
               FROM dim_customer c LEFT JOIN fact_order o ON o.customer_id=c.customer_id
               GROUP BY c.customer_segment
           ), ticket_metrics AS (
               SELECT c.customer_segment, COUNT(DISTINCT t.customer_id) AS customers_with_tickets
               FROM dim_customer c LEFT JOIN fact_support_ticket t ON t.customer_id=c.customer_id
               GROUP BY c.customer_segment
           )
           SELECT o.*, t.customers_with_tickets FROM order_metrics o
           JOIN ticket_metrics t ON t.customer_segment=o.customer_segment
           ORDER BY o.fulfilled_value_cents DESC"""
    ).fetchall()
    dashboard_rows = connection.execute(
        """SELECT o.order_month AS reporting_month, p.product_category,
                  COUNT(*) AS order_count, COUNT(DISTINCT o.customer_id) AS unique_customers,
                  SUM(o.quantity) AS units_sold,
                  SUM(CASE WHEN o.order_status IN ('COMPLETED','SHIPPED') THEN o.order_amount_cents ELSE 0 END) AS fulfilled_value_cents,
                  SUM(COALESCE(CASE WHEN f.posting_status='POSTED' THEN f.transaction_amount_cents END,0)) AS net_revenue_cents,
                  AVG(CASE WHEN o.order_status IN ('COMPLETED','SHIPPED') THEN o.order_amount_cents END) AS average_order_cents,
                  SUM(CASE WHEN o.order_status='CANCELLED' THEN 1 ELSE 0 END) AS cancelled_orders
           FROM fact_order o JOIN dim_product p ON p.product_id=o.product_id
           LEFT JOIN fact_finance_transaction f ON f.order_id=o.order_id
           GROUP BY o.order_month,p.product_category ORDER BY o.order_month,p.product_category"""
    ).fetchall()
    connection.close()

    total_unique = sum(etl["unique_counts"].values())
    quarantined = sum(etl["quarantine_counts"].values())
    quality_score = compute_quality_score(total_unique, etl["quality_issues"], quarantined)
    overall_result = {
        "net_revenue": _money(finance["net_revenue_cents"]),
        "fulfilled_order_value": _money(overall["fulfilled_value_cents"]),
        "order_count": overall["order_count"],
        "average_order_value": _money(overall["average_order_cents"]),
        "ordering_customer_count": overall["ordering_customers"],
        "ticket_volume": support["ticket_count"],
        "ticket_resolution_rate": round(100 * support["resolved_count"] / support["ticket_count"], 2) if support["ticket_count"] else 0,
        "average_resolution_hours": round(support["average_resolution_hours"] or 0, 2),
        "ticket_sla_rate": round(100 * support["within_sla"] / support["eligible_sla"], 2) if support["eligible_sla"] else 0,
        "cancellation_rate": round(100 * overall["cancelled_orders"] / overall["order_count"], 2) if overall["order_count"] else 0,
        "pending_finance_transactions": finance["pending_transactions"],
        "exception_count": len(etl["quality_issues"]),
        "quarantined_record_count": quarantined,
        "data_quality_score": quality_score,
    }

    monthly = []
    prior_revenue = None
    for row in monthly_order_rows:
        month = row["order_month"]
        finance_row = monthly_finance.get(month)
        support_row = monthly_support.get(month)
        revenue = _money(finance_row["net_revenue_cents"] if finance_row else 0)
        growth = round(100 * (revenue - prior_revenue) / abs(prior_revenue), 2) if prior_revenue not in (None, 0) else None
        monthly.append({
            "reporting_month": month,
            "order_count": row["order_count"],
            "unique_customers": row["unique_customers"],
            "units_sold": row["units"],
            "fulfilled_order_value": _money(row["fulfilled_value_cents"]),
            "net_revenue": revenue,
            "revenue_mom_growth_pct": growth,
            "average_order_value": _money(row["average_order_cents"]),
            "cancellation_rate": round(100 * row["cancelled_orders"] / row["order_count"], 2),
            "ticket_volume": support_row["ticket_volume"] if support_row else 0,
            "ticket_resolution_rate": round(100 * support_row["resolved_count"] / support_row["ticket_volume"], 2) if support_row and support_row["ticket_volume"] else 0,
            "ticket_sla_rate": round(100 * support_row["within_sla"] / support_row["eligible_sla"], 2) if support_row and support_row["eligible_sla"] else 0,
            "average_resolution_hours": round(support_row["average_resolution_hours"] or 0, 2) if support_row else 0,
        })
        prior_revenue = revenue
    revenue_values = [row["net_revenue"] for row in monthly]
    revenue_mean, revenue_std = mean(revenue_values), pstdev(revenue_values) or 1
    for row in monthly:
        zscore = (row["net_revenue"] - revenue_mean) / revenue_std
        row["revenue_zscore"] = round(zscore, 2)
        row["revenue_anomaly_flag"] = "Y" if abs(zscore) >= 2 else "N"

    categories = [{
        "product_category": row["product_category"], "order_count": row["order_count"],
        "customers": row["customers"], "units_sold": row["units"],
        "fulfilled_order_value": _money(row["fulfilled_value_cents"]),
        "net_revenue": _money(row["net_revenue_cents"]),
    } for row in category_rows]
    segments = [{
        "customer_segment": row["customer_segment"], "order_count": row["order_count"],
        "customers": row["customers"], "fulfilled_order_value": _money(row["fulfilled_value_cents"]),
        "average_order_value": _money(row["average_order_cents"]),
        "customers_with_tickets": row["customers_with_tickets"],
    } for row in segment_rows]
    dashboard = [{
        "reporting_month": row["reporting_month"], "product_category": row["product_category"],
        "order_count": row["order_count"], "unique_customers": row["unique_customers"],
        "units_sold": row["units_sold"], "fulfilled_order_value": _money(row["fulfilled_value_cents"]),
        "net_revenue": _money(row["net_revenue_cents"]), "average_order_value": _money(row["average_order_cents"]),
        "cancellation_rate": round(100 * row["cancelled_orders"] / row["order_count"], 2),
    } for row in dashboard_rows]
    return {
        "overall": overall_result,
        "monthly": monthly,
        "categories": categories,
        "segments": segments,
        "dashboard": dashboard,
        "top_category": max(categories, key=lambda item: item["net_revenue"]),
        "top_segment": max(segments, key=lambda item: item["fulfilled_order_value"]),
        "highest_revenue_month": max(monthly, key=lambda item: item["net_revenue"]),
        "lowest_sla_month": min(monthly, key=lambda item: item["ticket_sla_rate"]),
    }
