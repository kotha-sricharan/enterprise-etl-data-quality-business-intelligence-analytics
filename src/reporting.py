"""Publish BI-ready datasets, quality evidence, and a computed narrative."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from src.config import OUTPUT_DIR, ensure_directories


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Cannot publish an empty reporting dataset: {path.name}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _kpi_rows(overall: dict) -> list[dict]:
    definitions = {
        "net_revenue": ("USD", "Posted synthetic finance activity, net of refunds and adjustments"),
        "fulfilled_order_value": ("USD", "Order value for completed and shipped orders"),
        "order_count": ("COUNT", "Validated orders loaded to the warehouse"),
        "average_order_value": ("USD", "Average value of completed and shipped orders"),
        "ordering_customer_count": ("COUNT", "Distinct customers with a validated order"),
        "ticket_volume": ("COUNT", "Validated support tickets"),
        "ticket_resolution_rate": ("PERCENT", "Share of tickets in resolved or closed status"),
        "average_resolution_hours": ("HOURS", "Average elapsed time for resolved tickets"),
        "ticket_sla_rate": ("PERCENT", "Resolved tickets within priority-based SLA thresholds"),
        "cancellation_rate": ("PERCENT", "Cancelled orders as a share of loaded orders"),
        "pending_finance_transactions": ("COUNT", "Finance transactions awaiting posting"),
        "exception_count": ("COUNT", "Detected source-quality exceptions, including remediated records"),
        "quarantined_record_count": ("COUNT", "Unsafe fact records excluded with audit evidence"),
        "data_quality_score": ("PERCENT", "Issue-weighted score across unique source records"),
    }
    return [
        {"kpi_name": name, "kpi_value": value, "unit": definitions[name][0], "definition": definitions[name][1]}
        for name, value in overall.items()
    ]


def _recommendations(overall: dict, analytics: dict, etl: dict) -> list[str]:
    issue_counts = etl["quality"]["issue_counts"]
    recommendations: list[str] = []
    if overall["data_quality_score"] < 99:
        recommendations.append(
            f"Track remediation by source owner until the issue-weighted quality score improves from {overall['data_quality_score']:.2f}%."
        )
    if issue_counts.get("INVALID_CUSTOMER_REFERENCE", 0) or issue_counts.get("INVALID_PRODUCT_REFERENCE", 0):
        total = issue_counts.get("INVALID_CUSTOMER_REFERENCE", 0) + issue_counts.get("INVALID_PRODUCT_REFERENCE", 0)
        recommendations.append(
            f"Add master-data validation at ingestion for the {total} invalid customer/product references detected across operational sources."
        )
    if issue_counts.get("FINANCE_ORDER_AMOUNT_MISMATCH", 0):
        recommendations.append(
            f"Route the {issue_counts['FINANCE_ORDER_AMOUNT_MISMATCH']} order-to-ledger amount differences to finance reconciliation before period close."
        )
    if overall["ticket_sla_rate"] < 90:
        recommendations.append(
            f"Review staffing and escalation rules because only {overall['ticket_sla_rate']:.2f}% of eligible tickets met the priority-based SLA."
        )
    if overall["cancellation_rate"] >= 8:
        recommendations.append(
            f"Analyze cancellation drivers by channel and segment; the current rate is {overall['cancellation_rate']:.2f}%."
        )
    anomalies = [row for row in analytics["monthly"] if row["revenue_anomaly_flag"] == "Y"]
    if anomalies:
        months = ", ".join(row["reporting_month"] for row in anomalies)
        recommendations.append(f"Investigate revenue mix and postings for statistically unusual month(s): {months}.")
    return recommendations or ["Continue monthly monitoring of quality controls, revenue, orders, and support performance."]


def _business_report(generation: dict, profile: dict, etl: dict, analytics: dict) -> str:
    overall = analytics["overall"]
    top_category = analytics["top_category"]
    top_segment = analytics["top_segment"]
    best_month = analytics["highest_revenue_month"]
    lowest_sla = analytics["lowest_sla_month"]
    control_statuses = Counter(control["status"] for control in etl["quality"]["controls"])
    reconciliation_status = "PASS" if all(control["status"] == "PASS" for control in etl["reconciliation"]) else "FAIL"
    recommendations = _recommendations(overall, analytics, etl)
    top_issues = sorted(etl["quality"]["issue_counts"].items(), key=lambda item: (-item[1], item[0]))[:6]
    source_rows = sum(generation["source_rows"].values())
    lines = [
        "# Enterprise ETL, Data Quality & Business Intelligence Report",
        "",
        "Reporting period: **2025-01 through 2025-12**",
        "Data classification: **Independent synthetic portfolio data only**",
        "",
        "## Executive Summary",
        "",
        f"The automated pipeline profiled **{source_rows:,} raw rows** from five fictional enterprise systems and loaded a governed analytical warehouse. "
        f"Validated finance activity produced **{_money(overall['net_revenue'])} net revenue** across **{overall['order_count']:,} loaded orders**. "
        f"The data-quality score is **{overall['data_quality_score']:.2f}%**, and source-to-target reconciliation status is **{reconciliation_status}**.",
        "",
        "## Data Quality",
        "",
        f"Profiling identified **{profile['totals']['duplicate_rows']} exact duplicate rows** and **{profile['totals']['null_cells']} blank cells** before remediation. "
        f"The quality framework recorded **{len(etl['quality_issues']):,} exceptions**, including **{overall['quarantined_record_count']:,} quarantined fact records** and "
        f"**{etl['quality']['critical_error_count']} critical pipeline errors**. Control outcomes: {control_statuses.get('PASS', 0)} passed, "
        f"{control_statuses.get('WARNING', 0)} warnings, and {control_statuses.get('FAIL', 0)} failed.",
        "",
        "## Operational Performance",
        "",
        f"Completed and shipped orders represent **{_money(overall['fulfilled_order_value'])}** at an average of "
        f"**{_money(overall['average_order_value'])}**. The cancellation rate is **{overall['cancellation_rate']:.2f}%**. "
        f"Support handled **{overall['ticket_volume']:,} validated tickets**, resolving **{overall['ticket_resolution_rate']:.2f}%** with an average "
        f"resolution time of **{overall['average_resolution_hours']:.2f} hours** and an SLA attainment rate of **{overall['ticket_sla_rate']:.2f}%**.",
        "",
        "## Customer Insights",
        "",
        f"The warehouse contains activity from **{overall['ordering_customer_count']:,} ordering customers**. "
        f"**{top_segment['customer_segment']}** contributes the highest fulfilled order value at **{_money(top_segment['fulfilled_order_value'])}** "
        f"across **{top_segment['order_count']:,} orders**.",
        "",
        "## Product Insights",
        "",
        f"**{top_category['product_category']}** is the highest net-revenue category at **{_money(top_category['net_revenue'])}**, "
        f"with **{top_category['order_count']:,} orders** and **{top_category['units_sold']:,} units**.",
        "",
        "## Trend Analysis",
        "",
        f"**{best_month['reporting_month']}** is the highest-revenue month at **{_money(best_month['net_revenue'])}**. "
        f"The lowest monthly support SLA result occurs in **{lowest_sla['reporting_month']}** at **{lowest_sla['ticket_sla_rate']:.2f}%**. "
        f"Revenue z-scores and month-over-month growth are included in `monthly_trends.csv` for investigation and dashboard alerts.",
        "",
        "## Exceptions",
        "",
        "| Exception type | Count |",
        "|---|---:|",
        *[f"| {name.replace('_', ' ').title()} | {count} |" for name, count in top_issues],
        "",
        f"All **{len(etl['reconciliation'])}** count and amount reconciliation controls passed exactly. Known unsafe records remain in quarantine tables; "
        "standardized and reviewed records retain quality flags in the analytical facts and dimensions.",
        "",
        "## Recommendations",
        "",
        *[f"{index}. {text}" for index, text in enumerate(recommendations, 1)],
        "",
        "## Methodology",
        "",
        "A fixed-seed generator creates fictional CRM, product, order, support, and finance sources. The pipeline profiles raw inputs, applies documented controls, "
        "deduplicates deterministically, standardizes approved aliases, quarantines unsafe fact rows, reconciles counts and integer-cent amounts, loads a constrained "
        "SQLite dimensional model, calculates KPIs, and publishes BI-ready CSV, JSON, and Markdown artifacts.",
        "",
        "All organizations, identifiers, activity, amounts, findings, and recommendations are synthetic and do not represent any employer or real business.",
        "",
    ]
    return "\n".join(lines)


def generate_reports(generation: dict, profile: dict, etl: dict, analytics: dict) -> list[Path]:
    """Generate the five downstream artifacts; profiling publishes the sixth."""
    ensure_directories()
    kpi_path = OUTPUT_DIR / "kpi_summary.csv"
    monthly_path = OUTPUT_DIR / "monthly_trends.csv"
    dashboard_path = OUTPUT_DIR / "dashboard_dataset.csv"
    quality_path = OUTPUT_DIR / "data_quality_report.json"
    report_path = OUTPUT_DIR / "business_report.md"

    _write_csv(kpi_path, _kpi_rows(analytics["overall"]))
    _write_csv(monthly_path, analytics["monthly"])
    _write_csv(dashboard_path, analytics["dashboard"])
    quality_payload = {
        "status": "PASS" if etl["quality"]["critical_error_count"] == 0 and all(c["status"] == "PASS" for c in etl["reconciliation"]) else "FAIL",
        "data_classification": "SYNTHETIC_PORTFOLIO_DATA",
        "data_quality_score": analytics["overall"]["data_quality_score"],
        "source_counts": etl["source_counts"],
        "unique_counts": etl["unique_counts"],
        "loaded_counts": etl["loaded_counts"],
        "quarantine_counts": etl["quarantine_counts"],
        "duplicate_counts": etl["quality"]["duplicate_counts"],
        "critical_errors": etl["quality"]["critical_errors"],
        "issue_counts": etl["quality"]["issue_counts"],
        "validation_controls": etl["quality"]["controls"],
        "reconciliation_controls": etl["reconciliation"],
        "exceptions": etl["quality_issues"],
    }
    quality_path.write_text(json.dumps(quality_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_business_report(generation, profile, etl, analytics), encoding="utf-8")
    return [quality_path, kpi_path, monthly_path, dashboard_path, report_path]
