# Enterprise ETL, Data Quality & Business Intelligence Analytics

An end-to-end Data Analyst / Analytics Engineer portfolio project that integrates five fictional enterprise systems, profiles and governs source data, loads a constrained SQLite warehouse, and publishes audit-ready and BI-ready reporting datasets.

> **This repository is an independent synthetic-data portfolio project and does not contain confidential employer data.** Every organization, identifier, transaction, issue, KPI, and finding is fictional. The project does not reuse employer code, schemas, branding, or production data.

## Business Problem

A fictional operations company receives customer, product, order, support, and finance data from separate platforms. The sources disagree on categories, contain incomplete or duplicate records, and include broken references and financial differences. Business teams need one trusted layer that answers:

- Can every published record be traced to a governed source outcome?
- Which records were standardized, reviewed, or quarantined—and why?
- Do source counts and financial amounts reconcile to the warehouse?
- What are revenue, order, customer, product, support, and trend results?
- Can the same outputs be refreshed reliably for Power BI or Tableau?

## Architecture and Data Flow

```text
Fixed-seed synthetic sources
 CRM │ products │ orders │ support │ finance
                    │
                    ▼
       raw profiling and rule validation
                    │
       ┌────────────┴────────────┐
       ▼                         ▼
 approved remediation       quarantine evidence
 aliases/defaults           unsafe fact records
       └────────────┬────────────┘
                    ▼
      count + integer-cent reconciliation
                    ▼
      constrained SQLite dimensional model
                    ▼
  KPIs │ trends │ segments │ exceptions │ BI extracts
                    ▼
       CSV │ JSON │ automated Markdown report
```

Pipeline sequence:

```text
extract → profile → validate → transform → reconcile → load → analyze → report
```

## Repository Structure

```text
data/raw/          reproducible generated CSV sources (gitignored)
data/processed/    reproducible SQLite warehouse (gitignored)
src/               generation, profiling, quality, ETL, analytics, reporting
sql/               schema and business-focused analytical SQL
tests/             standard-library unit tests
outputs/           versioned BI, profile, quality, and narrative artifacts
docs/              requirements, dictionary, and test scenarios
```

## Data Sources

The fixed seed `20260827` generates 19,848 raw rows:

| Source | Raw rows | Purpose |
|---|---:|---|
| `customers.csv` | 1,205 | CRM customer, segment, region, and status attributes |
| `products.csv` | 123 | Product master, categories, prices, and costs |
| `orders.csv` | 8,008 | Order activity, quantities, discounts, amounts, and channels |
| `support_tickets.csv` | 2,506 | Ticket priority, lifecycle, category, and satisfaction |
| `finance_transactions.csv` | 8,006 | Order-linked postings, refunds, adjustments, and status |

Controlled conditions include 28 duplicate rows, missing values, category aliases, bad foreign keys, malformed dates, invalid quantities/amounts, high-value observations, and 18 order-to-ledger amount differences. Defects are not silently removed: deterministic duplicates are logged, approved aliases/defaults retain flags, review observations remain visible, and unsafe fact rows are stored in quarantine tables.

## Data Model

SQLite implements a compact dimensional warehouse:

- `dim_customer` and `dim_product` provide governed descriptive attributes.
- `fact_order`, `fact_support_ticket`, and `fact_finance_transaction` preserve operational grains.
- Three quarantine tables retain unsafe records without violating warehouse constraints.
- `data_quality_exception` records rule, severity, action, and explanatory evidence.
- `etl_control` stores source/target counts, integer-cent totals, differences, and status.

Primary keys, foreign keys, domain/range `CHECK` constraints, and analytical indexes enforce the model. Currency is stored as integer cents and discount rates as integer basis points. See [`sql/schema.sql`](sql/schema.sql) and the [data dictionary](docs/data_dictionary.md).

## Profiling

[`src/profile_data.py`](src/profile_data.py) calculates raw row/column counts, exact duplicate counts, primary-key duplicate counts, null counts, unique counts, duplicate-value counts, lexical ranges, numeric count/min/max/mean/sum, and top categorical distributions. The complete pre-remediation evidence is published to `outputs/data_profile.json`.

## Data Quality Controls

[`src/quality.py`](src/quality.py) validates required fields, uniqueness, parent references, numeric and rate ranges, governed categories, ISO dates/timestamps, date sequences, and order-to-ledger expectations. Results distinguish:

- **Critical / fail pipeline:** structural dimension, primary-key, parsing, or domain failures that make reporting unsafe.
- **High / quarantine:** bad fact references, malformed dates, invalid quantities/amounts, or lifecycle conflicts.
- **Medium / review:** unusual values and finance variances requiring analyst follow-up.
- **Low / standardize:** approved source aliases mapped to canonical values.

The deterministic run has zero critical errors. It quarantines 60 orders, 36 support tickets, and 78 finance transactions. Five count/amount controls reconcile exactly:

```text
8,000 unique orders = 7,940 loaded + 60 quarantined
2,500 unique tickets = 2,464 loaded + 36 quarantined
8,000 unique finance rows = 7,922 loaded + 78 quarantined
```

Order and finance amounts also reconcile exactly in integer cents. The issue-weighted data-quality score is **98.22%**.

## ETL

Python modules keep extraction, profiling, validation, transformation, loading, analytics, and reporting independently testable. The workflow:

1. Recreates every source from a fixed seed.
2. Profiles raw data before remediation.
3. Fails on critical integrity defects.
4. Deduplicates by keeping the first deterministic business-key row.
5. Standardizes documented aliases and missing regions.
6. Quarantines unsafe fact rows with reasons.
7. Cascades finance quarantine when its order was not loaded.
8. Proves count and amount conservation.
9. Loads SQLite in one transaction with foreign keys enabled.
10. Calculates and publishes business outputs.

## SQL Analysis

The SQL is designed around real analytical questions:

- [`transformations.sql`](sql/transformations.sql): enriched dimensional joins and deterministic order/finance matching with `ROW_NUMBER`.
- [`data_quality.sql`](sql/data_quality.sql): exception summaries, range checks, foreign-key audits, quarantine inventory, and persisted reconciliations.
- [`kpi_queries.sql`](sql/kpi_queries.sql): executive KPIs, conditional aggregation, category contribution, customer segmentation with `HAVING`, and support SLA performance.
- [`trend_analysis.sql`](sql/trend_analysis.sql): `LAG` month-over-month analysis, `RANK`, `DENSE_RANK`, top-customer segmentation, and exception ranking.

## KPIs and Reporting

The deterministic run calculates:

- **$119.79M** posted net revenue;
- **7,940** validated orders and **$19,964.55** average fulfilled order value;
- **1,199** ordering customers;
- **2,464** validated support tickets and **88.27%** resolution rate;
- **43.26%** priority-based support SLA attainment;
- **9.02%** order cancellation rate;
- **HARDWARE** as the highest net-revenue category at **$41.72M**;
- **October 2025** as the highest-revenue month at **$11.27M**.

Generated artifacts:

| Output | Intended use |
|---|---|
| `data_profile.json` | Machine-readable raw profiling evidence |
| `data_quality_report.json` | Controls, exceptions, quarantine, reconciliation, and score |
| `kpi_summary.csv` | Executive KPI cards and definitions |
| `monthly_trends.csv` | Monthly growth, support performance, z-scores, and anomaly flags |
| `dashboard_dataset.csv` | Power BI/Tableau-ready month-category analytical grain |
| `business_report.md` | Automated findings and rule-based recommendations |

All narrative values and recommendations are generated from calculated results.

## Testing and Documentation

Twelve `unittest` tests cover duplicate and missing-value detection, foreign-key validation, quarantine decisions, alias and integer-cent transformations, reconciliation success/failure, KPI calculation, quality scoring, and report generation from calculated facts.

- [`docs/requirements.md`](docs/requirements.md) defines business and control requirements.
- [`docs/data_dictionary.md`](docs/data_dictionary.md) documents source and warehouse fields/grains.
- [`docs/test_scenarios.md`](docs/test_scenarios.md) records analyst-friendly validation and UAT scenarios.

## How to Run

Requires Python 3.11 or later. The main workflow is API-free and uses only the Python standard library and SQLite.

```bash
git clone https://github.com/kotha-sricharan/enterprise-etl-data-quality-business-intelligence-analytics.git
cd enterprise-etl-data-quality-business-intelligence-analytics

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python -m src.run_pipeline
python -m unittest discover -s tests -v
```

Or run the complete verification target:

```bash
make verify
```

## Findings and Recommendations

The synthetic run shows that count reconciliation can pass while operational exceptions still require action. The largest opportunities are stronger master-data validation, finance variance review before close, improved priority-based support performance, and cancellation analysis by channel and customer segment. The generated report quantifies each recommendation from the current run rather than hard-coding conclusions.

## Limitations and Production Extensions

- The data and business rules are fictional and intentionally simplified.
- Revenue is illustrative finance activity, not GAAP reporting, forecasting, or a regulatory filing.
- One product is modeled per order; line-item, tax, payment allocation, and multi-currency complexity are excluded.
- SQLite and local files demonstrate architecture, not production scale or security controls.

Production extensions would include governed connectors, incremental loads, slowly changing dimensions, orchestration, lineage, role-based access, encryption, alert routing, CI/CD quality gates, semantic-model measures, and scheduled BI refreshes.
