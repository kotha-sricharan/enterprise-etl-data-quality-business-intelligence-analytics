# Business and Analytical Requirements

## Purpose

The fictional operations company needs a repeatable analytical layer that reconciles CRM, product, order, support, and finance activity. This document translates user needs into testable portfolio requirements.

## Stakeholders and User Needs

| Stakeholder | User need | Acceptance measure |
|---|---|---|
| Operations leadership | Monitor orders, customers, cancellations, and monthly performance | Monthly and executive KPI outputs refresh from source data |
| Finance analyst | Reconcile order activity to ledger postings | Source counts/amounts are conserved; variances are separately identified |
| Support manager | Monitor volume, resolution, and priority-based SLA attainment | Ticket KPIs use documented status and SLA rules |
| Product manager | Compare category volume, value, and customer reach | Month-category dashboard extract has a declared additive grain |
| Data steward | Identify, explain, and route quality exceptions | Every issue has a rule, severity, action, record ID, and message |
| BI developer | Consume stable, typed datasets | CSV schemas and dimensional keys remain consistent across reruns |
| Auditor/reviewer | Reproduce counts and remediation decisions | Fixed seed, exact reconciliations, rule documentation, and tests are available |

## Functional Requirements

1. Generate deterministic fictional inputs for five source systems.
2. Profile source row counts, completeness, uniqueness, ranges, numeric measures, and categorical distributions before remediation.
3. Validate required fields, business keys, domains, references, dates, numeric ranges, and cross-system finance expectations.
4. Distinguish critical failures, quarantines, review warnings, and approved standardizations.
5. Stop publication when a critical source or reconciliation control fails.
6. Preserve unsafe records in explicit quarantine tables.
7. Store currency as integer cents and discount rates as integer basis points.
8. Load constrained customer/product dimensions and order/support/finance facts into SQLite.
9. Calculate revenue, order, customer, product, support, quality, monthly growth, and anomaly measures.
10. Produce six stable, nonempty reporting artifacts suitable for BI ingestion or audit review.
11. Create a business report whose facts and recommendations derive from the current calculation results.
12. Run without paid services, private credentials, or confidential data.

## Nonfunctional Requirements

- Python 3.11+ and standard-library runtime only.
- Deterministic output for the same source seed and code version.
- Transactional database load with foreign-key enforcement.
- Modular functions that can be unit tested independently.
- UTF-8, documented paths, professional comments/docstrings, and no unfinished sections.
- A fresh clone must run using the README commands.

## KPI Definitions

- **Net revenue:** sum of posted finance transaction amounts, including negative refunds.
- **Fulfilled order value:** order amount for completed and shipped orders.
- **Average order value:** average fulfilled order amount.
- **Ordering customers:** distinct customers with a validated loaded order.
- **Ticket resolution rate:** resolved or closed tickets divided by loaded tickets.
- **SLA attainment:** resolved tickets within 24/48/72/120 hours for critical/high/medium/low priority.
- **Cancellation rate:** cancelled loaded orders divided by all loaded orders.
- **Data-quality score:** issue-weighted measure across unique source records, with greater penalties for critical and quarantined outcomes.

## Out of Scope

Real organizations or people, employer systems, production deployment, accounting certification, multi-currency conversion, tax, revenue recognition policy, predictive modeling, and live dashboard hosting are outside this portfolio implementation.
