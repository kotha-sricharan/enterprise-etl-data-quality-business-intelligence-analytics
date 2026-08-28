# Data Dictionary

All data is fictional. Identifiers use synthetic prefixes and do not map to real people, customers, products, or transactions.

## Raw Sources

### `customers.csv` — CRM customer grain

| Field | Meaning |
|---|---|
| `customer_id` | Synthetic business key (`CUS######`) |
| `customer_name` | Fictional organization label |
| `customer_segment` | SMB, mid-market, or enterprise; raw aliases are injected |
| `region` | North, south, east, west, or blank controlled condition |
| `created_date` | CRM creation date |
| `crm_status` | Active/inactive domain |
| `source_system` | Fictional source lineage label |

### `products.csv` — product master grain

| Field | Meaning |
|---|---|
| `product_id` | Synthetic product key (`PRD####`) |
| `product_name` | Fictional offering name |
| `product_category` | Governed category with controlled raw aliases |
| `unit_price` / `unit_cost` | Synthetic USD decimals |
| `active_flag` | Product master activity indicator |
| `source_system` | Fictional source lineage label |

### `orders.csv` — one product per order

| Field | Meaning |
|---|---|
| `order_id` | Synthetic order key (`ORD#######`) |
| `customer_id` / `product_id` | Parent references |
| `order_date` | Raw order date |
| `quantity` | Ordered units |
| `unit_price` | Synthetic USD unit price |
| `discount_rate` | Decimal discount rate |
| `order_amount` | Synthetic extended order amount |
| `order_status` | Completed, shipped, cancelled, returned, or controlled alias |
| `channel` | Direct, partner, or online |
| `source_system` | Fictional source lineage label |

### `support_tickets.csv` — one support case

| Field | Meaning |
|---|---|
| `ticket_id` | Synthetic ticket key (`TKT#######`) |
| `customer_id` | CRM customer reference |
| `opened_at` / `resolved_at` | ISO lifecycle timestamps when valid |
| `ticket_status` | Open, resolved, or closed |
| `priority` | Low, medium, high, critical, or controlled alias |
| `issue_category` | Billing, product, access, integration, or service |
| `satisfaction_score` | Optional integer from 1 to 5 |
| `source_system` | Fictional source lineage label |

### `finance_transactions.csv` — one synthetic ledger event

| Field | Meaning |
|---|---|
| `finance_transaction_id` | Synthetic finance key (`FIN#######`) |
| `order_id` | Order reference |
| `posted_date` | Ledger posting date |
| `transaction_type` | Sale, refund, adjustment, or controlled alias |
| `transaction_amount` | Signed synthetic USD amount |
| `currency` | USD in this implementation |
| `posting_status` | Posted or pending |
| `source_system` | Fictional source lineage label |

## Warehouse Model

| Table | Grain and key measures |
|---|---|
| `dim_customer` | One governed customer; canonical segment/region and quality flag |
| `dim_product` | One governed product; category, integer-cent price/cost, quality flag |
| `fact_order` | One validated unique order; month, units, basis-point discount, integer-cent amount |
| `fact_support_ticket` | One validated ticket; lifecycle, priority, resolution hours, satisfaction |
| `fact_finance_transaction` | One validated ledger event; order link, signed integer cents, posting status |
| `order_quarantine` | One unsafe order and its combined reason(s) |
| `support_ticket_quarantine` | One unsafe ticket and its combined reason(s) |
| `finance_transaction_quarantine` | One unsafe finance row and its combined reason(s) |
| `data_quality_exception` | One detected rule exception; dataset, record, severity, action, message |
| `etl_control` | One source-target control; unit, source, target, difference, status |

## Reporting Outputs

- `kpi_summary.csv`: one row per KPI.
- `monthly_trends.csv`: one row per reporting month.
- `dashboard_dataset.csv`: one row per reporting month and product category; numeric measures are additive only within that declared grain.
- `data_profile.json`: raw profiling metadata.
- `data_quality_report.json`: validation, exception, quarantine, and reconciliation evidence.
- `business_report.md`: automated management narrative.
