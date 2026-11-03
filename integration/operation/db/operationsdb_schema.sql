-- OperationsDb — PostgreSQL setup script
-- Two schemas: `dbo` holds the base tables, `ss` holds the views/functions
-- that customer/worker/manager roles are actually granted access to.
-- Direct table access in `dbo` is NOT granted to any of the three roles —
-- all reads go through ss objects (SECURITY DEFINER functions / owner-rights
-- views), giving a real access boundary, same pattern as CustomerDb.
--
-- customer / worker / manager are cluster-wide Postgres roles shared with
-- CustomerDb (see customerdb_schema.sql) — the CREATE ROLE guards below are
-- only so this script can also run standalone. They now have LOGIN so the
-- Operations API can connect directly as the role matching the caller's JWT.
-- NOTE: rotate db_password (see \set below) before any real deployment. When
-- this script runs after customerdb_schema.sql (the normal order), the roles
-- already exist and this file's CREATE ROLE calls are skipped — db_password
-- must match the value customerdb_schema.sql used to create them.
--
\set db_password 'Abc123'
--
-- Cross-database references: Payment.PaymentMethodId -> CustomerDb's
-- core.payment_method, and Delivery.CustomerAddressId -> CustomerDb's
-- core.address. Postgres cannot enforce a FOREIGN KEY across databases, so
-- these are plain INTEGER columns with no physical constraint — integrity
-- across the two databases is an application-layer responsibility.

CREATE SCHEMA IF NOT EXISTS dbo;
CREATE SCHEMA IF NOT EXISTS ss;

-- ============================================================
-- Tables (dbo schema)
-- ============================================================

CREATE TABLE dbo.product (
    product_id      SERIAL PRIMARY KEY,
    category        VARCHAR(100) NOT NULL,
    sub_category    VARCHAR(100),
    product_name    VARCHAR(255) NOT NULL,
    quantity        NUMERIC(10, 3) NOT NULL DEFAULT 0,
    price           NUMERIC(12, 2) NOT NULL
);

CREATE INDEX idx_product_category ON dbo.product(category);
CREATE INDEX idx_product_sub_category ON dbo.product(sub_category);
CREATE INDEX idx_product_name ON dbo.product(product_name);

CREATE TYPE dbo.order_status AS ENUM (
    'Pending', 'Paid', 'Processing', 'Shipped', 'Delivered',
    'Cancelled', 'Refunded', 'Returned'
);

CREATE TABLE dbo.orders (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INTEGER NOT NULL,  -- CustomerDb.core.profile.customer_id (cross-db, not enforced)
    order_date    TIMESTAMP NOT NULL DEFAULT now(),
    order_status  dbo.order_status NOT NULL DEFAULT 'Pending'
);

CREATE INDEX idx_orders_customer_id ON dbo.orders(customer_id);
CREATE INDEX idx_orders_order_date ON dbo.orders(order_date);
CREATE INDEX idx_orders_status ON dbo.orders(order_status);

CREATE TABLE dbo.order_product (
    order_product_id  SERIAL PRIMARY KEY,
    order_id          INTEGER NOT NULL REFERENCES dbo.orders(order_id) ON DELETE CASCADE,
    product_id        INTEGER NOT NULL REFERENCES dbo.product(product_id),
    special_priced    BOOLEAN NOT NULL DEFAULT FALSE,
    quantity          NUMERIC(10, 3) NOT NULL DEFAULT 1,
    uom               VARCHAR(20) NOT NULL DEFAULT 'pcs'
);

CREATE INDEX idx_order_product_order_id ON dbo.order_product(order_id);
CREATE INDEX idx_order_product_product_id ON dbo.order_product(product_id);

CREATE TABLE dbo.payment (
    payment_id         SERIAL PRIMARY KEY,
    order_id           INTEGER NOT NULL REFERENCES dbo.orders(order_id),
    payment_method_id  INTEGER NOT NULL,  -- CustomerDb.core.payment_method.payment_method_id (cross-db, not enforced)
    payment_date       TIMESTAMP NOT NULL DEFAULT now(),
    payment_amount     NUMERIC(12, 2) NOT NULL
);

CREATE INDEX idx_payment_order_id ON dbo.payment(order_id);

CREATE TABLE dbo.invoice (
    invoice_id    SERIAL PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES dbo.orders(order_id),
    payment_id    INTEGER NOT NULL REFERENCES dbo.payment(payment_id),
    invoice_date  TIMESTAMP NOT NULL DEFAULT now(),
    order_amount  NUMERIC(12, 2) NOT NULL,
    tax_amount    NUMERIC(12, 2) NOT NULL
    -- Line items are not duplicated here; an invoice's products are looked up
    -- via dbo.order_product through its order_id. order_amount/tax_amount are
    -- snapshotted at invoice time (not recomputed from order_product/price on
    -- every read) since prices can change after the invoice is issued.
);

CREATE INDEX idx_invoice_order_id ON dbo.invoice(order_id);
CREATE INDEX idx_invoice_payment_id ON dbo.invoice(payment_id);

CREATE TYPE dbo.delivery_status AS ENUM ('Shipped', 'InTransit', 'Delivered');

CREATE TABLE dbo.delivery (
    delivery_id           SERIAL PRIMARY KEY,
    order_id              INTEGER NOT NULL REFERENCES dbo.orders(order_id),
    invoice_id            INTEGER NOT NULL REFERENCES dbo.invoice(invoice_id),
    customer_address_id   INTEGER NOT NULL,  -- CustomerDb.core.address.customer_address_id (cross-db, not enforced)
    delivery_date         TIMESTAMP,
    delivery_status       dbo.delivery_status NOT NULL DEFAULT 'Shipped'
);

CREATE INDEX idx_delivery_order_id ON dbo.delivery(order_id);
CREATE INDEX idx_delivery_invoice_id ON dbo.delivery(invoice_id);

CREATE TABLE dbo.special_price (
    order_id    INTEGER NOT NULL REFERENCES dbo.orders(order_id),
    product_id  INTEGER NOT NULL REFERENCES dbo.product(product_id),
    price       NUMERIC(12, 2) NOT NULL,
    PRIMARY KEY (order_id, product_id)
);

-- ============================================================
-- Functions (ss schema)
-- SECURITY DEFINER + a locked-down search_path: these run with the owner's
-- (not the caller's) privileges, since customer/worker/manager are never
-- granted access to `dbo` directly — only via functions/views in `ss`.
--
-- "Customer can only see their own data" (Orders, OrderProduct, Payment,
-- Invoice, Delivery by-id/by-order lookups) is a business rule Postgres
-- GRANTs cannot enforce on parameter *values* or row contents — it is
-- enforced by the Operations API, which checks the customer_id each of these
-- functions returns against the caller's own JWT customer_id claim.
-- ============================================================

-- Internal helper, not part of the requested SP list: special-price-aware
-- order total, reused by get_invoice_date_and_total and the 3 order views.
CREATE FUNCTION ss.order_amount(p_order_id INTEGER)
RETURNS NUMERIC
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT COALESCE(SUM(
        op.quantity * CASE WHEN op.special_priced THEN COALESCE(sp.price, p.price) ELSE p.price END
    ), 0)
    FROM dbo.order_product op
    JOIN dbo.product p ON p.product_id = op.product_id
    LEFT JOIN dbo.special_price sp ON sp.order_id = op.order_id AND sp.product_id = op.product_id
    WHERE op.order_id = p_order_id;
$$;
COMMENT ON FUNCTION ss.order_amount(INTEGER) IS
    'INTERNAL ONLY — not granted to any role, do not call directly. Special-price-aware total for one order, used inside other functions/views.';
-- Postgres grants EXECUTE to PUBLIC on every new function by default, so
-- without this, "not granted to any role" above would be false — every login
-- role (including customer/worker) could call it despite never being an
-- explicit grantee. The blanket `REVOKE ... FROM PUBLIC` further down (after
-- the roles/grants section header) covers the rest of the ss schema; this one
-- is redundant with it but kept for clarity right next to the function it
-- protects.
REVOKE EXECUTE ON FUNCTION ss.order_amount(INTEGER) FROM PUBLIC;

-- --- Product ---------------------------------------------------------

CREATE FUNCTION ss.get_products()
RETURNS TABLE (product_id INTEGER, category VARCHAR, sub_category VARCHAR, product_name VARCHAR, quantity NUMERIC, price NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT product_id, category, sub_category, product_name, quantity, price
    FROM dbo.product;
$$;
COMMENT ON FUNCTION ss.get_products() IS
    'ALL products in the catalog (no filter, no args).';

CREATE FUNCTION ss.get_product(p_product_id INTEGER)
RETURNS TABLE (product_id INTEGER, category VARCHAR, sub_category VARCHAR, product_name VARCHAR, quantity NUMERIC, price NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT product_id, category, sub_category, product_name, quantity, price
    FROM dbo.product
    WHERE product_id = p_product_id;
$$;
COMMENT ON FUNCTION ss.get_product(INTEGER) IS
    'ONE product, given its known product_id.';

CREATE FUNCTION ss.get_product_by_name(p_product_name VARCHAR)
RETURNS TABLE (product_id INTEGER, category VARCHAR, sub_category VARCHAR, product_name VARCHAR, quantity NUMERIC, price NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT product_id, category, sub_category, product_name, quantity, price
    FROM dbo.product
    WHERE product_name = p_product_name;
$$;
COMMENT ON FUNCTION ss.get_product_by_name(VARCHAR) IS
    'ONE product, given its EXACT product_name (case-sensitive equality — use search_products for a fuzzy match).';

CREATE FUNCTION ss.get_products_by_category(p_category VARCHAR)
RETURNS TABLE (product_id INTEGER, category VARCHAR, sub_category VARCHAR, product_name VARCHAR, quantity NUMERIC, price NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT product_id, category, sub_category, product_name, quantity, price
    FROM dbo.product
    WHERE category = p_category;
$$;
COMMENT ON FUNCTION ss.get_products_by_category(VARCHAR) IS
    'ALL products in ONE exact category (e.g. "Electronics") — use get_categories() first if you don''t know the exact value.';

CREATE FUNCTION ss.get_products_by_sub_category(p_sub_category VARCHAR)
RETURNS TABLE (product_id INTEGER, category VARCHAR, sub_category VARCHAR, product_name VARCHAR, quantity NUMERIC, price NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT product_id, category, sub_category, product_name, quantity, price
    FROM dbo.product
    WHERE sub_category = p_sub_category;
$$;
COMMENT ON FUNCTION ss.get_products_by_sub_category(VARCHAR) IS
    'ALL products in ONE exact sub_category — use get_sub_categories() first if you don''t know the exact value.';

-- Distinct category/sub_category lists, used by the caching-worker to warm
-- the Redis product lookup at startup (see integration/caching_worker).
CREATE FUNCTION ss.get_categories()
RETURNS TABLE (category VARCHAR)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT DISTINCT category FROM dbo.product ORDER BY category;
$$;
COMMENT ON FUNCTION ss.get_categories() IS
    'Every distinct product category value that exists (no args) — use this to discover valid values for get_products_by_category.';

CREATE FUNCTION ss.get_sub_categories()
RETURNS TABLE (sub_category VARCHAR)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT DISTINCT sub_category FROM dbo.product WHERE sub_category IS NOT NULL ORDER BY sub_category;
$$;
COMMENT ON FUNCTION ss.get_sub_categories() IS
    'Every distinct product sub_category value that exists (no args) — use this to discover valid values for get_products_by_sub_category.';

CREATE FUNCTION ss.search_products(p_search_string VARCHAR)
RETURNS TABLE (product_id INTEGER, category VARCHAR, sub_category VARCHAR, product_name VARCHAR, quantity NUMERIC, price NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT product_id, category, sub_category, product_name, quantity, price
    FROM dbo.product
    WHERE product_name ILIKE '%' || p_search_string || '%'
       OR category ILIKE '%' || p_search_string || '%'
       OR sub_category ILIKE '%' || p_search_string || '%';
$$;
COMMENT ON FUNCTION ss.search_products(VARCHAR) IS
    'Fuzzy, case-insensitive substring match for one search term against product_name, category, and sub_category together.';

-- --- Order -----------------------------------------------------------

CREATE FUNCTION ss.get_orders()
RETURNS TABLE (order_id INTEGER, customer_id INTEGER, order_date TIMESTAMP, order_status dbo.order_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT order_id, customer_id, order_date, order_status
    FROM dbo.orders;
$$;
COMMENT ON FUNCTION ss.get_orders() IS
    'ALL orders for ALL customers (no filter, no args) — worker/manager only.';

CREATE FUNCTION ss.get_orders_by_date(p_date DATE)
RETURNS TABLE (order_id INTEGER, customer_id INTEGER, order_date TIMESTAMP, order_status dbo.order_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT order_id, customer_id, order_date, order_status
    FROM dbo.orders
    WHERE order_date::date = p_date;
$$;
COMMENT ON FUNCTION ss.get_orders_by_date(DATE) IS
    'Orders placed on exactly ONE calendar day (not a range) — takes a single p_date. For a date range, call it once per day or use get_order_by_product_and_dates if also filtering by product.';

CREATE FUNCTION ss.get_orders_by_customer(p_customer_id INTEGER)
RETURNS TABLE (order_id INTEGER, customer_id INTEGER, order_date TIMESTAMP, order_status dbo.order_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT order_id, customer_id, order_date, order_status
    FROM dbo.orders
    WHERE customer_id = p_customer_id;
$$;
COMMENT ON FUNCTION ss.get_orders_by_customer(INTEGER) IS
    'ALL orders belonging to ONE customer, given their known customer_id.';

CREATE FUNCTION ss.get_order_by_customer_and_order(p_customer_id INTEGER, p_order_id INTEGER)
RETURNS TABLE (order_id INTEGER, customer_id INTEGER, order_date TIMESTAMP, order_status dbo.order_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT order_id, customer_id, order_date, order_status
    FROM dbo.orders
    WHERE customer_id = p_customer_id AND order_id = p_order_id;
$$;
COMMENT ON FUNCTION ss.get_order_by_customer_and_order(INTEGER, INTEGER) IS
    'ONE order, verifying it belongs to the given customer_id — both customer_id and order_id must already be known.';

CREATE FUNCTION ss.get_order(p_order_id INTEGER)
RETURNS TABLE (order_id INTEGER, customer_id INTEGER, order_date TIMESTAMP, order_status dbo.order_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT order_id, customer_id, order_date, order_status
    FROM dbo.orders
    WHERE order_id = p_order_id;
$$;
COMMENT ON FUNCTION ss.get_order(INTEGER) IS
    'ONE order, given its known order_id.';

CREATE FUNCTION ss.get_order_status(p_order_id INTEGER)
RETURNS TABLE (order_id INTEGER, customer_id INTEGER, order_status dbo.order_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT order_id, customer_id, order_status
    FROM dbo.orders
    WHERE order_id = p_order_id;
$$;
COMMENT ON FUNCTION ss.get_order_status(INTEGER) IS
    'Just the status of ONE order, given its known order_id.';

-- Line items for GetCompleteOrder — special-price-aware unit price per line,
-- reusing the same logic as ss.order_amount but per-row instead of summed.
CREATE FUNCTION ss.get_order_line_items(p_order_id INTEGER)
RETURNS TABLE (
    order_product_id INTEGER, product_id INTEGER, product_name VARCHAR,
    special_priced BOOLEAN, quantity NUMERIC, uom VARCHAR, unit_price NUMERIC
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT op.order_product_id, op.product_id, p.product_name, op.special_priced, op.quantity, op.uom,
           CASE WHEN op.special_priced THEN COALESCE(sp.price, p.price) ELSE p.price END AS unit_price
    FROM dbo.order_product op
    JOIN dbo.product p ON p.product_id = op.product_id
    LEFT JOIN dbo.special_price sp ON sp.order_id = op.order_id AND sp.product_id = op.product_id
    WHERE op.order_id = p_order_id;
$$;
COMMENT ON FUNCTION ss.get_order_line_items(INTEGER) IS
    'Per-product line items (with the actual unit_price charged, special-price-aware) for ONE order, given its known order_id.';

-- Assumes "Product" in the spec means ProductId (functions elsewhere take
-- ProductId, not a name, for exact lookups).
CREATE FUNCTION ss.get_order_by_product_and_dates(p_product_id INTEGER, p_start_date DATE, p_end_date DATE)
RETURNS TABLE (order_id INTEGER, customer_id INTEGER, order_date TIMESTAMP, order_status dbo.order_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT DISTINCT o.order_id, o.customer_id, o.order_date, o.order_status
    FROM dbo.orders o
    JOIN dbo.order_product op ON op.order_id = o.order_id
    WHERE op.product_id = p_product_id
      AND o.order_date::date BETWEEN p_start_date AND p_end_date;
$$;
COMMENT ON FUNCTION ss.get_order_by_product_and_dates(INTEGER, DATE, DATE) IS
    'Orders containing ONE product (by product_id) placed within a date range — takes p_start_date AND p_end_date (inclusive), unlike get_orders_by_date which takes only one day.';

-- --- OrderProduct ------------------------------------------------------

CREATE FUNCTION ss.get_order_products()
RETURNS TABLE (order_product_id INTEGER, order_id INTEGER, customer_id INTEGER, product_id INTEGER, special_priced BOOLEAN, quantity NUMERIC, uom VARCHAR)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT op.order_product_id, op.order_id, o.customer_id, op.product_id, op.special_priced, op.quantity, op.uom
    FROM dbo.order_product op
    JOIN dbo.orders o ON o.order_id = op.order_id;
$$;
COMMENT ON FUNCTION ss.get_order_products() IS
    'ALL order-product line rows for ALL orders (no filter, no args) — worker/manager only.';

CREATE FUNCTION ss.get_order_product(p_order_product_id INTEGER)
RETURNS TABLE (order_product_id INTEGER, order_id INTEGER, customer_id INTEGER, product_id INTEGER, special_priced BOOLEAN, quantity NUMERIC, uom VARCHAR)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT op.order_product_id, op.order_id, o.customer_id, op.product_id, op.special_priced, op.quantity, op.uom
    FROM dbo.order_product op
    JOIN dbo.orders o ON o.order_id = op.order_id
    WHERE op.order_product_id = p_order_product_id;
$$;
COMMENT ON FUNCTION ss.get_order_product(INTEGER) IS
    'ONE order-product line row, given its known order_product_id (not an order_id or product_id).';

CREATE FUNCTION ss.get_order_product_by_order(p_order_id INTEGER)
RETURNS TABLE (order_product_id INTEGER, order_id INTEGER, product_id INTEGER, special_priced BOOLEAN, quantity NUMERIC, uom VARCHAR)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT order_product_id, order_id, product_id, special_priced, quantity, uom
    FROM dbo.order_product
    WHERE order_id = p_order_id;
$$;
COMMENT ON FUNCTION ss.get_order_product_by_order(INTEGER) IS
    'ALL order-product line rows for ONE order, given its known order_id.';

CREATE FUNCTION ss.get_orders_by_product(p_product_id INTEGER)
RETURNS TABLE (order_id INTEGER, customer_id INTEGER, order_date TIMESTAMP, order_status dbo.order_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT DISTINCT o.order_id, o.customer_id, o.order_date, o.order_status
    FROM dbo.orders o
    JOIN dbo.order_product op ON op.order_id = o.order_id
    WHERE op.product_id = p_product_id;
$$;
COMMENT ON FUNCTION ss.get_orders_by_product(INTEGER) IS
    'ALL orders (any customer, any date) that contain ONE product, given its known product_id — worker/manager only.';

-- --- Payment -----------------------------------------------------------

CREATE FUNCTION ss.get_payments()
RETURNS TABLE (payment_id INTEGER, order_id INTEGER, customer_id INTEGER, payment_method_id INTEGER, payment_date TIMESTAMP, payment_amount NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT pay.payment_id, pay.order_id, o.customer_id, pay.payment_method_id, pay.payment_date, pay.payment_amount
    FROM dbo.payment pay
    JOIN dbo.orders o ON o.order_id = pay.order_id;
$$;
COMMENT ON FUNCTION ss.get_payments() IS
    'ALL payments for ALL orders (no filter, no args) — worker/manager only.';

CREATE FUNCTION ss.get_payment(p_payment_id INTEGER)
RETURNS TABLE (payment_id INTEGER, order_id INTEGER, customer_id INTEGER, payment_method_id INTEGER, payment_date TIMESTAMP, payment_amount NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT pay.payment_id, pay.order_id, o.customer_id, pay.payment_method_id, pay.payment_date, pay.payment_amount
    FROM dbo.payment pay
    JOIN dbo.orders o ON o.order_id = pay.order_id
    WHERE pay.payment_id = p_payment_id;
$$;
COMMENT ON FUNCTION ss.get_payment(INTEGER) IS
    'ONE payment, given its known payment_id (not an order_id — there is no get_payment_by_order; go via get_invoice_by_order to find the payment_id for an order, since invoices carry it).';

-- PaymentMethod.PaymentType lives in CustomerDb, not here, so "GetByPaymentType"
-- can't filter in SQL directly. The Operations API resolves the payment type
-- to a set of PaymentMethodIds via the Customer API first, then calls this.
CREATE FUNCTION ss.get_payments_by_method_ids(p_payment_method_ids INTEGER[])
RETURNS TABLE (payment_id INTEGER, order_id INTEGER, customer_id INTEGER, payment_method_id INTEGER, payment_date TIMESTAMP, payment_amount NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT pay.payment_id, pay.order_id, o.customer_id, pay.payment_method_id, pay.payment_date, pay.payment_amount
    FROM dbo.payment pay
    JOIN dbo.orders o ON o.order_id = pay.order_id
    WHERE pay.payment_method_id = ANY (p_payment_method_ids);
$$;
COMMENT ON FUNCTION ss.get_payments_by_method_ids(INTEGER[]) IS
    'Payments matching ANY of a given LIST of payment_method_id values (an array, not a single id) — worker/manager only.';

-- --- Invoice -------------------------------------------------------------

CREATE FUNCTION ss.get_invoices()
RETURNS TABLE (invoice_id INTEGER, order_id INTEGER, customer_id INTEGER, payment_id INTEGER, invoice_date TIMESTAMP, order_amount NUMERIC, tax_amount NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT i.invoice_id, i.order_id, o.customer_id, i.payment_id, i.invoice_date, i.order_amount, i.tax_amount
    FROM dbo.invoice i
    JOIN dbo.orders o ON o.order_id = i.order_id;
$$;
COMMENT ON FUNCTION ss.get_invoices() IS
    'ALL invoices for ALL orders (no filter, no args) — worker/manager only.';

CREATE FUNCTION ss.get_invoice(p_invoice_id INTEGER)
RETURNS TABLE (invoice_id INTEGER, order_id INTEGER, customer_id INTEGER, payment_id INTEGER, invoice_date TIMESTAMP, order_amount NUMERIC, tax_amount NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT i.invoice_id, i.order_id, o.customer_id, i.payment_id, i.invoice_date, i.order_amount, i.tax_amount
    FROM dbo.invoice i
    JOIN dbo.orders o ON o.order_id = i.order_id
    WHERE i.invoice_id = p_invoice_id;
$$;
COMMENT ON FUNCTION ss.get_invoice(INTEGER) IS
    'ONE invoice, given its known invoice_id (not an order_id — use get_invoice_by_order for that).';

CREATE FUNCTION ss.get_invoice_date_and_total(p_invoice_id INTEGER)
RETURNS TABLE (invoice_date TIMESTAMP, total_amount NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT i.invoice_date, i.order_amount + i.tax_amount
    FROM dbo.invoice i
    WHERE i.invoice_id = p_invoice_id;
$$;
COMMENT ON FUNCTION ss.get_invoice_date_and_total(INTEGER) IS
    'Just the date and total_amount (order_amount + tax_amount, revenue) for ONE invoice, given its known invoice_id — worker/manager only. This is the resource to sum for revenue questions, not order_amount (internal-only).';

CREATE FUNCTION ss.get_invoice_by_customer(p_customer_id INTEGER, p_invoice_id INTEGER)
RETURNS TABLE (invoice_id INTEGER, order_id INTEGER, payment_id INTEGER, invoice_date TIMESTAMP, order_amount NUMERIC, tax_amount NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT i.invoice_id, i.order_id, i.payment_id, i.invoice_date, i.order_amount, i.tax_amount
    FROM dbo.invoice i
    JOIN dbo.orders o ON o.order_id = i.order_id
    WHERE o.customer_id = p_customer_id AND i.invoice_id = p_invoice_id;
$$;
COMMENT ON FUNCTION ss.get_invoice_by_customer(INTEGER, INTEGER) IS
    'ONE invoice, verifying it belongs to the given customer_id — both customer_id and invoice_id must already be known.';

CREATE FUNCTION ss.get_invoice_by_order(p_order_id INTEGER)
RETURNS TABLE (invoice_id INTEGER, order_id INTEGER, customer_id INTEGER, payment_id INTEGER, invoice_date TIMESTAMP, order_amount NUMERIC, tax_amount NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT i.invoice_id, i.order_id, o.customer_id, i.payment_id, i.invoice_date, i.order_amount, i.tax_amount
    FROM dbo.invoice i
    JOIN dbo.orders o ON o.order_id = i.order_id
    WHERE i.order_id = p_order_id;
$$;
COMMENT ON FUNCTION ss.get_invoice_by_order(INTEGER) IS
    'The invoice for ONE order, given its known order_id — this is how to find an order''s payment_id (invoice.payment_id), since there is no direct get_payment_by_order.';

CREATE FUNCTION ss.get_invoices_by_date(p_date DATE)
RETURNS TABLE (invoice_id INTEGER, order_id INTEGER, payment_id INTEGER, invoice_date TIMESTAMP, order_amount NUMERIC, tax_amount NUMERIC)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT invoice_id, order_id, payment_id, invoice_date, order_amount, tax_amount
    FROM dbo.invoice
    WHERE invoice_date::date = p_date;
$$;
COMMENT ON FUNCTION ss.get_invoices_by_date(DATE) IS
    'Invoices issued on exactly ONE calendar day (not a range) — takes a single p_date, not a start/end pair. Manager only. To total revenue over a month, this must be called once per day in the range (or via a broader manual query) — there is no start/end-date revenue function.';

-- --- Delivery --------------------------------------------------------------

CREATE FUNCTION ss.get_deliveries()
RETURNS TABLE (delivery_id INTEGER, order_id INTEGER, customer_id INTEGER, invoice_id INTEGER, customer_address_id INTEGER, delivery_date TIMESTAMP, delivery_status dbo.delivery_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT d.delivery_id, d.order_id, o.customer_id, d.invoice_id, d.customer_address_id, d.delivery_date, d.delivery_status
    FROM dbo.delivery d
    JOIN dbo.orders o ON o.order_id = d.order_id;
$$;
COMMENT ON FUNCTION ss.get_deliveries() IS
    'ALL deliveries for ALL orders (no filter, no args) — worker/manager only.';

CREATE FUNCTION ss.get_delivery(p_delivery_id INTEGER)
RETURNS TABLE (delivery_id INTEGER, order_id INTEGER, customer_id INTEGER, invoice_id INTEGER, customer_address_id INTEGER, delivery_date TIMESTAMP, delivery_status dbo.delivery_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT d.delivery_id, d.order_id, o.customer_id, d.invoice_id, d.customer_address_id, d.delivery_date, d.delivery_status
    FROM dbo.delivery d
    JOIN dbo.orders o ON o.order_id = d.order_id
    WHERE d.delivery_id = p_delivery_id;
$$;
COMMENT ON FUNCTION ss.get_delivery(INTEGER) IS
    'ONE delivery, given its known delivery_id (not an order_id — use get_delivery_status_by_order for that).';

-- Enum value lists, used by the caching-worker to warm the Redis status
-- lookups at startup (see integration/caching_worker).
CREATE FUNCTION ss.get_order_statuses()
RETURNS TABLE (order_status dbo.order_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT unnest(enum_range(NULL::dbo.order_status));
$$;
COMMENT ON FUNCTION ss.get_order_statuses() IS
    'Every possible order_status enum value (no args) — a fixed reference list, not data about any specific order.';

CREATE FUNCTION ss.get_delivery_statuses()
RETURNS TABLE (delivery_status dbo.delivery_status)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT unnest(enum_range(NULL::dbo.delivery_status));
$$;
COMMENT ON FUNCTION ss.get_delivery_statuses() IS
    'Every possible delivery_status enum value (no args) — a fixed reference list, not data about any specific delivery.';

CREATE FUNCTION ss.get_delivery_status_by_order(p_order_id INTEGER)
RETURNS TABLE (order_id INTEGER, customer_id INTEGER, delivery_status dbo.delivery_status, delivery_date TIMESTAMP)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT d.order_id, o.customer_id, d.delivery_status, d.delivery_date
    FROM dbo.delivery d
    JOIN dbo.orders o ON o.order_id = d.order_id
    WHERE d.order_id = p_order_id;
$$;
COMMENT ON FUNCTION ss.get_delivery_status_by_order(INTEGER) IS
    'Delivery status and date for ONE order, given its known order_id.';

-- ============================================================
-- Views (ss schema) — views run with the owner's privileges by default in
-- Postgres, so no SECURITY DEFINER equivalent is needed here.
-- ============================================================

CREATE VIEW ss.product_metadata AS
    SELECT product_id, category, sub_category, product_name
    FROM dbo.product;
COMMENT ON VIEW ss.product_metadata IS
    'Every product''s id/category/sub_category/name only (no quantity or price) — no filter, no args.';

-- "Completed" = OrderStatus = 'Delivered'.
CREATE VIEW ss.completed_orders AS
    SELECT o.order_id, pay.payment_id, i.invoice_id, o.order_date, i.invoice_date,
           d.delivery_date, i.order_amount, i.tax_amount
    FROM dbo.orders o
    JOIN dbo.payment pay ON pay.order_id = o.order_id
    JOIN dbo.invoice i ON i.order_id = o.order_id
    JOIN dbo.delivery d ON d.order_id = o.order_id
    WHERE o.order_status = 'Delivered';
COMMENT ON VIEW ss.completed_orders IS
    'ALL orders with status Delivered, across ALL customers, each with its invoiced order_amount and tax_amount — no filter, no args, manager only.';

CREATE VIEW ss.pending_orders AS
    SELECT order_id, order_date, order_status, ss.order_amount(order_id) AS order_amount
    FROM dbo.orders
    WHERE order_status = 'Pending';
COMMENT ON VIEW ss.pending_orders IS
    'ALL orders with status Pending, across ALL customers, each with its order_amount total — no filter, no args, manager only.';

CREATE VIEW ss.rejected_or_refunded_orders AS
    SELECT order_id, order_date, order_status, ss.order_amount(order_id) AS order_amount
    FROM dbo.orders
    WHERE order_status IN ('Cancelled', 'Refunded', 'Returned');
COMMENT ON VIEW ss.rejected_or_refunded_orders IS
    'ALL orders with status Cancelled, Refunded, or Returned, across ALL customers, each with its order_amount total — no filter, no args, manager only.';

-- ============================================================
-- Roles & grants
-- c = customer, w = worker, m = manager, matching the request's cwm shorthand.
-- Where a by-id/by-order lookup is customer+worker+manager, "customer" means
-- "customer, but the API restricts them to rows for their own customer_id" —
-- see the note at the top of the Functions section.
-- ============================================================

SELECT format(
    CASE WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'customer')
         THEN 'ALTER ROLE customer WITH PASSWORD %L'
         ELSE 'CREATE ROLE customer LOGIN PASSWORD %L'
    END, :'db_password')
\gexec

SELECT format(
    CASE WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'worker')
         THEN 'ALTER ROLE worker WITH PASSWORD %L'
         ELSE 'CREATE ROLE worker LOGIN PASSWORD %L'
    END, :'db_password')
\gexec

SELECT format(
    CASE WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'manager')
         THEN 'ALTER ROLE manager WITH PASSWORD %L'
         ELSE 'CREATE ROLE manager LOGIN PASSWORD %L'
    END, :'db_password')
\gexec

GRANT USAGE ON SCHEMA ss TO customer, worker, manager;

-- Postgres grants EXECUTE to PUBLIC by default on every new function, which
-- would undermine the wm-only/m-only restrictions below (ss.order_amount was
-- already handled individually above). Revoke that default here, then the
-- explicit GRANTs below re-assert access per role.
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA ss FROM PUBLIC;

-- cwm: product catalog (not customer-scoped data)
GRANT EXECUTE ON FUNCTION
    ss.get_products(),
    ss.get_product(INTEGER),
    ss.get_product_by_name(VARCHAR),
    ss.get_products_by_category(VARCHAR),
    ss.get_products_by_sub_category(VARCHAR),
    ss.search_products(VARCHAR),
    ss.get_categories(),
    ss.get_sub_categories(),
    ss.get_order_statuses(),
    ss.get_delivery_statuses()
    TO customer, worker, manager;
GRANT SELECT ON ss.product_metadata TO customer, worker, manager;

-- c (own CustomerId only, app-enforced) + wm
GRANT EXECUTE ON FUNCTION
    ss.get_orders_by_customer(INTEGER),
    ss.get_order_by_customer_and_order(INTEGER, INTEGER),
    ss.get_order(INTEGER),
    ss.get_order_status(INTEGER),
    ss.get_order_line_items(INTEGER),
    ss.get_order_product_by_order(INTEGER),
    ss.get_order_product(INTEGER),
    ss.get_invoice_by_customer(INTEGER, INTEGER),
    ss.get_invoice(INTEGER),
    ss.get_invoice_by_order(INTEGER),
    ss.get_payment(INTEGER),
    ss.get_delivery(INTEGER),
    ss.get_delivery_status_by_order(INTEGER)
    TO customer, worker, manager;

-- wm only (cross-customer listings / reporting)
GRANT EXECUTE ON FUNCTION
    ss.get_orders(),
    ss.get_orders_by_date(DATE),
    ss.get_order_by_product_and_dates(INTEGER, DATE, DATE),
    ss.get_order_products(),
    ss.get_orders_by_product(INTEGER),
    ss.get_payments(),
    ss.get_payments_by_method_ids(INTEGER[]),
    ss.get_invoices(),
    ss.get_invoice_date_and_total(INTEGER),
    ss.get_deliveries()
    TO worker, manager;

-- m only
GRANT EXECUTE ON FUNCTION ss.get_invoices_by_date(DATE) TO manager;
GRANT SELECT ON ss.completed_orders, ss.pending_orders, ss.rejected_or_refunded_orders TO manager;

-- NOTE: ss.order_amount is an internal helper (not in the original SP/View
-- list) and is intentionally NOT granted to customer/worker/manager; it only
-- runs as SECURITY DEFINER from inside the views/functions above.
