# Validation and UAT Test Scenarios

These scenarios describe how an analyst, data steward, or reviewer can validate the project beyond the automated unit tests.

| ID | Scenario | Test action | Expected result |
|---|---|---|---|
| DQ-01 | Duplicate business keys | Add a second identical order row | Duplicate is logged once, first row is kept, unique count is unchanged |
| DQ-02 | Missing required order parent | Blank an order customer ID | Order is quarantined with `MISSING_REQUIRED_FIELD` |
| DQ-03 | Invalid reference | Replace a product/customer ID with an unknown key | Fact is quarantined and no broken warehouse FK is loaded |
| DQ-04 | Malformed date | Set an order date to an invalid ISO value | Order is quarantined with `MALFORMED_DATE` |
| DQ-05 | Invalid numeric range | Set quantity to zero or order amount negative | Order is quarantined and range constraints remain clean |
| DQ-06 | Controlled alias | Change `COMPLETED` to `complete` | Row loads as `COMPLETED` with a standardization quality flag |
| DQ-07 | Missing region | Blank a customer region | Customer loads as `UNKNOWN` with an explicit default flag |
| FIN-01 | Order-ledger variance | Change a finance amount without changing its order | Difference appears in exceptions and SQL reconciliation analysis |
| FIN-02 | Count conservation | Compare unique source facts with loaded plus quarantine | Every count difference equals zero |
| FIN-03 | Amount conservation | Sum source, loaded, and quarantined integer cents | Order and finance amount differences equal zero |
| ETL-01 | Critical failure | Remove a dimension business key | Pipeline raises `DataQualityError` and does not publish a new warehouse |
| ETL-02 | Fact cascade | Quarantine an order referenced by finance | Related finance row is also quarantined as `ORDER_NOT_LOADED` |
| SQL-01 | Warehouse integrity | Run `PRAGMA integrity_check` and `PRAGMA foreign_key_check` | Integrity returns `ok`; foreign-key query returns no rows |
| BI-01 | Monthly reconciliation | Sum monthly order counts | Total equals `fact_order` count |
| BI-02 | Dashboard grain | Check month/category uniqueness | Every month-category pair occurs once |
| RPT-01 | Calculated report | Change controlled KPI inputs in a unit test | Markdown report contains the changed calculated values |
| REP-01 | Deterministic rerun | Run the pipeline twice and compare artifact hashes | Generated raw/database/reporting files are byte-identical |

## Automated Test Mapping

- `test_quality.py`: DQ-01 through DQ-03.
- `test_etl.py`: DQ-06, FIN-02, FIN-03, and failure behavior.
- `test_analytics.py`: BI calculation and score behavior.
- `test_reporting.py`: RPT-01 and output creation.

The end-to-end verification additionally executes every SQL file, database integrity checks, artifact schema checks, a secrets/confidentiality scan, and a fresh-clone run.
