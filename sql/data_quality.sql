-- Persisted rule outcomes by severity and action.
SELECT dataset, issue_type, severity, action, COUNT(*) AS exception_count
FROM data_quality_exception
GROUP BY dataset, issue_type, severity, action
ORDER BY exception_count DESC, dataset, issue_type;

-- Warehouse referential-integrity audit (each query should return zero).
SELECT 'ORDER_CUSTOMER_FK' AS control_name, COUNT(*) AS issue_count
FROM fact_order o LEFT JOIN dim_customer c ON c.customer_id=o.customer_id
WHERE c.customer_id IS NULL
UNION ALL
SELECT 'ORDER_PRODUCT_FK', COUNT(*)
FROM fact_order o LEFT JOIN dim_product p ON p.product_id=o.product_id
WHERE p.product_id IS NULL
UNION ALL
SELECT 'FINANCE_ORDER_FK', COUNT(*)
FROM fact_finance_transaction f LEFT JOIN fact_order o ON o.order_id=f.order_id
WHERE o.order_id IS NULL;

-- Financial/range checks expected to return zero loaded violations.
SELECT
    SUM(CASE WHEN quantity <= 0 THEN 1 ELSE 0 END) AS invalid_quantity,
    SUM(CASE WHEN order_amount_cents < 0 THEN 1 ELSE 0 END) AS negative_order_amount,
    SUM(CASE WHEN discount_basis_points NOT BETWEEN 0 AND 10000 THEN 1 ELSE 0 END) AS invalid_discount
FROM fact_order;

-- Quarantine inventory supports audit and source-owner remediation.
SELECT 'orders' AS dataset, COUNT(*) AS quarantined FROM order_quarantine
UNION ALL SELECT 'support_tickets', COUNT(*) FROM support_ticket_quarantine
UNION ALL SELECT 'finance_transactions', COUNT(*) FROM finance_transaction_quarantine;

-- Critical source-to-target controls must all be PASS.
SELECT control_name, dataset, unit, source_value, target_value, difference, status
FROM etl_control
ORDER BY control_name;
