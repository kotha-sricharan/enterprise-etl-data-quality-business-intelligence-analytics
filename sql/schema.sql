PRAGMA foreign_keys = ON;

CREATE TABLE dim_customer (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    customer_segment TEXT NOT NULL CHECK (customer_segment IN ('SMB','MID_MARKET','ENTERPRISE')),
    region TEXT NOT NULL,
    created_date TEXT NOT NULL,
    crm_status TEXT NOT NULL CHECK (crm_status IN ('ACTIVE','INACTIVE')),
    quality_flag TEXT NOT NULL
);

CREATE TABLE dim_product (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    product_category TEXT NOT NULL CHECK (product_category IN ('SOFTWARE','HARDWARE','SERVICES','SECURITY','CLOUD','DATA')),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents > 0),
    unit_cost_cents INTEGER NOT NULL CHECK (unit_cost_cents BETWEEN 0 AND unit_price_cents),
    active_flag TEXT NOT NULL CHECK (active_flag IN ('Y','N')),
    quality_flag TEXT NOT NULL
);

CREATE TABLE fact_order (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES dim_customer(customer_id),
    product_id TEXT NOT NULL REFERENCES dim_product(product_id),
    order_date TEXT NOT NULL,
    order_month TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents > 0),
    discount_basis_points INTEGER NOT NULL CHECK (discount_basis_points BETWEEN 0 AND 10000),
    order_amount_cents INTEGER NOT NULL CHECK (order_amount_cents >= 0),
    order_status TEXT NOT NULL CHECK (order_status IN ('COMPLETED','SHIPPED','CANCELLED','RETURNED')),
    channel TEXT NOT NULL CHECK (channel IN ('DIRECT','PARTNER','ONLINE')),
    quality_flag TEXT NOT NULL
);

CREATE TABLE fact_support_ticket (
    ticket_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES dim_customer(customer_id),
    opened_at TEXT NOT NULL,
    opened_month TEXT NOT NULL,
    resolved_at TEXT,
    ticket_status TEXT NOT NULL CHECK (ticket_status IN ('OPEN','RESOLVED','CLOSED')),
    priority TEXT NOT NULL CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    issue_category TEXT NOT NULL,
    resolution_hours REAL CHECK (resolution_hours IS NULL OR resolution_hours >= 0),
    satisfaction_score INTEGER CHECK (satisfaction_score IS NULL OR satisfaction_score BETWEEN 1 AND 5),
    quality_flag TEXT NOT NULL
);

CREATE TABLE fact_finance_transaction (
    finance_transaction_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES fact_order(order_id),
    posted_date TEXT NOT NULL,
    posted_month TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('SALE','REFUND','ADJUSTMENT')),
    transaction_amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL CHECK (currency = 'USD'),
    posting_status TEXT NOT NULL CHECK (posting_status IN ('POSTED','PENDING')),
    quality_flag TEXT NOT NULL
);

CREATE TABLE order_quarantine (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    product_id TEXT,
    order_date TEXT,
    order_amount_cents INTEGER,
    quarantine_reason TEXT NOT NULL
);

CREATE TABLE support_ticket_quarantine (
    ticket_id TEXT PRIMARY KEY,
    customer_id TEXT,
    opened_at TEXT,
    quarantine_reason TEXT NOT NULL
);

CREATE TABLE finance_transaction_quarantine (
    finance_transaction_id TEXT PRIMARY KEY,
    order_id TEXT,
    posted_date TEXT,
    transaction_amount_cents INTEGER,
    quarantine_reason TEXT NOT NULL
);

CREATE TABLE data_quality_exception (
    exception_id TEXT PRIMARY KEY,
    dataset TEXT NOT NULL,
    record_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    action TEXT NOT NULL CHECK (action IN ('DEDUPLICATE','STANDARDIZE','DEFAULT_UNKNOWN','REVIEW','QUARANTINE','FAIL_PIPELINE')),
    message TEXT NOT NULL
);

CREATE TABLE etl_control (
    control_name TEXT PRIMARY KEY,
    dataset TEXT NOT NULL,
    unit TEXT NOT NULL CHECK (unit IN ('COUNT','CENTS')),
    source_value INTEGER NOT NULL,
    target_value INTEGER NOT NULL,
    difference INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS','FAIL'))
);

CREATE INDEX idx_order_month ON fact_order(order_month);
CREATE INDEX idx_order_customer_month ON fact_order(customer_id, order_month);
CREATE INDEX idx_order_product_month ON fact_order(product_id, order_month);
CREATE INDEX idx_ticket_customer_month ON fact_support_ticket(customer_id, opened_month);
CREATE INDEX idx_ticket_priority_status ON fact_support_ticket(priority, ticket_status);
CREATE INDEX idx_finance_order ON fact_finance_transaction(order_id);
CREATE INDEX idx_finance_month ON fact_finance_transaction(posted_month);
CREATE INDEX idx_dq_dataset_issue ON data_quality_exception(dataset, issue_type);
