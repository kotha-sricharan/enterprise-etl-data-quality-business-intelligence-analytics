-- Executive KPIs across orders, finance, customers, and support.
WITH order_kpis AS (
    SELECT COUNT(*) AS order_count, COUNT(DISTINCT customer_id) AS ordering_customers,
           SUM(CASE WHEN order_status IN ('COMPLETED','SHIPPED') THEN order_amount_cents ELSE 0 END) AS fulfilled_value_cents,
           AVG(CASE WHEN order_status IN ('COMPLETED','SHIPPED') THEN order_amount_cents END) AS average_order_cents,
           AVG(CASE WHEN order_status='CANCELLED' THEN 1.0 ELSE 0 END) AS cancellation_rate
    FROM fact_order
), finance_kpis AS (
    SELECT SUM(CASE WHEN posting_status='POSTED' THEN transaction_amount_cents ELSE 0 END) AS net_revenue_cents
    FROM fact_finance_transaction
), support_kpis AS (
    SELECT COUNT(*) AS ticket_volume,
           AVG(CASE WHEN ticket_status IN ('RESOLVED','CLOSED') THEN 1.0 ELSE 0 END) AS resolution_rate,
           AVG(resolution_hours) AS average_resolution_hours
    FROM fact_support_ticket
)
SELECT o.order_count, o.ordering_customers, o.fulfilled_value_cents / 100.0 AS fulfilled_order_value,
       o.average_order_cents / 100.0 AS average_order_value, ROUND(100*o.cancellation_rate,2) AS cancellation_rate,
       f.net_revenue_cents / 100.0 AS net_revenue, s.ticket_volume,
       ROUND(100*s.resolution_rate,2) AS ticket_resolution_rate, ROUND(s.average_resolution_hours,2) AS average_resolution_hours
FROM order_kpis o CROSS JOIN finance_kpis f CROSS JOIN support_kpis s;

-- Product/category performance with rank and contribution.
WITH category_performance AS (
    SELECT p.product_category, COUNT(*) AS order_count, SUM(o.quantity) AS units,
           SUM(CASE WHEN o.order_status IN ('COMPLETED','SHIPPED') THEN o.order_amount_cents ELSE 0 END) AS fulfilled_cents
    FROM fact_order o JOIN dim_product p ON p.product_id=o.product_id
    GROUP BY p.product_category
), ranked AS (
    SELECT *, DENSE_RANK() OVER (ORDER BY fulfilled_cents DESC) AS revenue_rank,
           100.0 * fulfilled_cents / SUM(fulfilled_cents) OVER () AS revenue_share
    FROM category_performance
)
SELECT product_category, order_count, units, fulfilled_cents / 100.0 AS fulfilled_value,
       revenue_rank, ROUND(revenue_share,2) AS revenue_share_pct
FROM ranked ORDER BY revenue_rank;

-- Customer segmentation with a real HAVING threshold.
SELECT c.customer_segment, COUNT(o.order_id) AS order_count,
       COUNT(DISTINCT o.customer_id) AS ordering_customers,
       SUM(CASE WHEN o.order_status IN ('COMPLETED','SHIPPED') THEN o.order_amount_cents ELSE 0 END) / 100.0 AS fulfilled_value
FROM dim_customer c JOIN fact_order o ON o.customer_id=c.customer_id
GROUP BY c.customer_segment
HAVING COUNT(o.order_id) >= 100
ORDER BY fulfilled_value DESC;

-- SLA performance by governed ticket priority.
SELECT priority, COUNT(*) AS ticket_volume,
       SUM(CASE WHEN ticket_status IN ('RESOLVED','CLOSED') THEN 1 ELSE 0 END) AS resolved_tickets,
       ROUND(AVG(resolution_hours),2) AS average_resolution_hours,
       ROUND(100.0 * SUM(CASE WHEN resolution_hours IS NOT NULL AND resolution_hours <=
           CASE priority WHEN 'CRITICAL' THEN 24 WHEN 'HIGH' THEN 48 WHEN 'MEDIUM' THEN 72 ELSE 120 END
           THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN resolution_hours IS NOT NULL THEN 1 ELSE 0 END),0),2) AS sla_rate
FROM fact_support_ticket
GROUP BY priority
ORDER BY CASE priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END;
