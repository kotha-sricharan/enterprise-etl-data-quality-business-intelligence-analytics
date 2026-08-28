-- Enriched order grain used by BI datasets without changing warehouse facts.
WITH enriched_orders AS (
    SELECT o.order_id, o.order_month, o.customer_id, c.customer_segment, c.region,
           o.product_id, p.product_category, o.quantity, o.order_amount_cents,
           o.order_status, o.channel,
           CASE WHEN o.order_status IN ('COMPLETED','SHIPPED') THEN o.order_amount_cents ELSE 0 END AS fulfilled_value_cents
    FROM fact_order o
    JOIN dim_customer c ON c.customer_id = o.customer_id
    JOIN dim_product p ON p.product_id = o.product_id
)
SELECT order_month, product_category, customer_segment,
       COUNT(*) AS order_count, COUNT(DISTINCT customer_id) AS customers,
       SUM(quantity) AS units, SUM(fulfilled_value_cents) / 100.0 AS fulfilled_value
FROM enriched_orders
GROUP BY order_month, product_category, customer_segment
ORDER BY order_month, product_category, customer_segment;

-- One deterministic finance record per order and its status-based expectation.
WITH expected AS (
    SELECT order_id,
           CASE WHEN order_status IN ('COMPLETED','SHIPPED') THEN order_amount_cents
                WHEN order_status='RETURNED' THEN -order_amount_cents ELSE 0 END AS expected_cents
    FROM fact_order
), ranked_finance AS (
    SELECT f.*, ROW_NUMBER() OVER (
        PARTITION BY f.order_id ORDER BY f.posted_date, f.finance_transaction_id
    ) AS row_number
    FROM fact_finance_transaction f
)
SELECT r.finance_transaction_id, r.order_id, e.expected_cents,
       r.transaction_amount_cents, r.transaction_amount_cents - e.expected_cents AS variance_cents
FROM ranked_finance r
JOIN expected e ON e.order_id = r.order_id
WHERE r.row_number = 1 AND r.transaction_amount_cents <> e.expected_cents
ORDER BY ABS(r.transaction_amount_cents - e.expected_cents) DESC;
