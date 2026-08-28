# Enterprise ETL, Data Quality & Business Intelligence Report

Reporting period: **2025-01 through 2025-12**
Data classification: **Independent synthetic portfolio data only**

## Executive Summary

The automated pipeline profiled **19,848 raw rows** from five fictional enterprise systems and loaded a governed analytical warehouse. Validated finance activity produced **$119,792,439.77 net revenue** across **7,940 loaded orders**. The data-quality score is **98.22%**, and source-to-target reconciliation status is **PASS**.

## Data Quality

Profiling identified **28 exact duplicate rows** and **622 blank cells** before remediation. The quality framework recorded **543 exceptions**, including **174 quarantined fact records** and **0 critical pipeline errors**. Control outcomes: 5 passed, 27 warnings, and 0 failed.

## Operational Performance

Completed and shipped orders represent **$134,301,497.03** at an average of **$19,964.55**. The cancellation rate is **9.02%**. Support handled **2,464 validated tickets**, resolving **88.27%** with an average resolution time of **86.97 hours** and an SLA attainment rate of **43.26%**.

## Customer Insights

The warehouse contains activity from **1,199 ordering customers**. **SMB** contributes the highest fulfilled order value at **$76,308,759.27** across **4,366 orders**.

## Product Insights

**HARDWARE** is the highest net-revenue category at **$41,722,403.65**, with **1,663 orders** and **11,293 units**.

## Trend Analysis

**2025-10** is the highest-revenue month at **$11,273,174.53**. The lowest monthly support SLA result occurs in **2025-01** at **34.18%**. Revenue z-scores and month-over-month growth are included in `monthly_trends.csv` for investigation and dashboard alerts.

## Exceptions

| Exception type | Count |
|---|---:|
| Unusual Numeric Value | 219 |
| Category Standardized | 92 |
| Order Not Loaded | 60 |
| Duplicate Business Key | 28 |
| Invalid Customer Reference | 24 |
| Malformed Date | 22 |

All **5** count and amount reconciliation controls passed exactly. Known unsafe records remain in quarantine tables; standardized and reviewed records retain quality flags in the analytical facts and dimensions.

## Recommendations

1. Track remediation by source owner until the issue-weighted quality score improves from 98.22%.
2. Add master-data validation at ingestion for the 36 invalid customer/product references detected across operational sources.
3. Route the 18 order-to-ledger amount differences to finance reconciliation before period close.
4. Review staffing and escalation rules because only 43.26% of eligible tickets met the priority-based SLA.
5. Analyze cancellation drivers by channel and segment; the current rate is 9.02%.

## Methodology

A fixed-seed generator creates fictional CRM, product, order, support, and finance sources. The pipeline profiles raw inputs, applies documented controls, deduplicates deterministically, standardizes approved aliases, quarantines unsafe fact rows, reconciles counts and integer-cent amounts, loads a constrained SQLite dimensional model, calculates KPIs, and publishes BI-ready CSV, JSON, and Markdown artifacts.

All organizations, identifiers, activity, amounts, findings, and recommendations are synthetic and do not represent any employer or real business.
