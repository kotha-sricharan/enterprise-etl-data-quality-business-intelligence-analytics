-- Month-over-month revenue and order growth using window functions.
WITH order_months AS (
    SELECT order_month AS reporting_month, COUNT(*) AS order_count,
           SUM(CASE WHEN order_status IN ('COMPLETED','SHIPPED') THEN order_amount_cents ELSE 0 END) AS fulfilled_cents
    FROM fact_order GROUP BY order_month
), finance_months AS (
    SELECT posted_month AS reporting_month,
           SUM(CASE WHEN posting_status='POSTED' THEN transaction_amount_cents ELSE 0 END) AS net_revenue_cents
    FROM fact_finance_transaction GROUP BY posted_month
), monthly AS (
    SELECT o.reporting_month, o.order_count, o.fulfilled_cents,
           COALESCE(f.net_revenue_cents,0) AS net_revenue_cents
    FROM order_months o LEFT JOIN finance_months f USING (reporting_month)
), prior AS (
    SELECT *, LAG(order_count) OVER (ORDER BY reporting_month) AS prior_orders,
           LAG(net_revenue_cents) OVER (ORDER BY reporting_month) AS prior_revenue
    FROM monthly
)
SELECT reporting_month, order_count, fulfilled_cents / 100.0 AS fulfilled_value,
       net_revenue_cents / 100.0 AS net_revenue,
       ROUND(100.0 * (order_count-prior_orders) / NULLIF(prior_orders,0),2) AS order_growth_pct,
       ROUND(100.0 * (net_revenue_cents-prior_revenue) / NULLIF(ABS(prior_revenue),0),2) AS revenue_growth_pct
FROM prior ORDER BY reporting_month;

-- Top customers in each segment using RANK and deterministic ROW_NUMBER.
WITH customer_value AS (
    SELECT c.customer_segment, c.customer_id, c.customer_name,
           SUM(CASE WHEN o.order_status IN ('COMPLETED','SHIPPED') THEN o.order_amount_cents ELSE 0 END) AS value_cents
    FROM dim_customer c JOIN fact_order o ON o.customer_id=c.customer_id
    GROUP BY c.customer_segment,c.customer_id,c.customer_name
), ranked AS (
    SELECT *, RANK() OVER (PARTITION BY customer_segment ORDER BY value_cents DESC) AS value_rank,
           ROW_NUMBER() OVER (PARTITION BY customer_segment ORDER BY value_cents DESC,customer_id) AS row_number
    FROM customer_value
)
SELECT customer_segment,customer_id,customer_name,value_cents/100.0 AS fulfilled_value,value_rank,row_number
FROM ranked WHERE row_number <= 5 ORDER BY customer_segment,row_number;

-- Monthly exception volume highlights recurring source-control themes.
WITH exception_counts AS (
    SELECT dataset, issue_type, COUNT(*) AS exception_count
    FROM data_quality_exception GROUP BY dataset,issue_type
)
SELECT dataset,issue_type,exception_count,
       DENSE_RANK() OVER (PARTITION BY dataset ORDER BY exception_count DESC) AS issue_rank
FROM exception_counts ORDER BY dataset,issue_rank,issue_type;
