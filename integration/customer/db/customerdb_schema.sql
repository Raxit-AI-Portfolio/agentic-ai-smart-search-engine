-- CustomerDb — PostgreSQL setup script
-- Two schemas: `dbo` holds the base tables, `ss` holds the views/functions
-- that customer/worker/manager roles are actually granted access to.
-- Direct table access in `dbo` is NOT granted to any of the three roles —
-- all reads go through ss objects, giving a real access boundary.

-- Single password for all three login roles below — override with
-- `psql -v db_password='...'` rather than editing this literal, and keep the
-- real value only in .env / a secrets manager.
\set db_password 'Abc123'

CREATE SCHEMA IF NOT EXISTS dbo;
CREATE SCHEMA IF NOT EXISTS ss;

-- ============================================================
-- Tables (dbo schema)
-- ============================================================

CREATE TABLE dbo.profile (
    customer_id     SERIAL PRIMARY KEY,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    contact_number  VARCHAR(30)
);

CREATE TABLE dbo.address (
    customer_address_id  SERIAL PRIMARY KEY,
    customer_id          INTEGER NOT NULL REFERENCES dbo.profile(customer_id) ON DELETE CASCADE,
    street_line_1        VARCHAR(255) NOT NULL,
    street_line_2        VARCHAR(255),
    city                 VARCHAR(100) NOT NULL,
    state                VARCHAR(100),
    country              VARCHAR(100) NOT NULL,
    postal_code          VARCHAR(20),
    is_primary           BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_address_customer_id ON dbo.address(customer_id);
CREATE INDEX idx_address_city_state_country ON dbo.address(city, state, country);

-- At most one primary address per customer.
CREATE UNIQUE INDEX uq_address_one_primary_per_customer
    ON dbo.address(customer_id) WHERE is_primary;

CREATE TYPE dbo.payment_type AS ENUM ('Debit Card', 'Credit Card');

CREATE TABLE dbo.payment_method (
    payment_method_id  SERIAL PRIMARY KEY,
    customer_id        INTEGER NOT NULL REFERENCES dbo.profile(customer_id) ON DELETE CASCADE,
    payment_type        dbo.payment_type NOT NULL,
    card_last_four      CHAR(4) NOT NULL,
    billing_address      TEXT
);

CREATE INDEX idx_payment_method_customer_id ON dbo.payment_method(customer_id);

-- ============================================================
-- Views (ss schema)
-- ============================================================

CREATE VIEW ss.customer_name AS
    SELECT customer_id, first_name, last_name
    FROM dbo.profile;
COMMENT ON VIEW ss.customer_name IS
    'All customers'' id and name (no filter — returns every row in dbo.profile). Use get_customer_name(id) instead if you only need one customer.';

CREATE VIEW ss.customer_contact AS
    SELECT customer_id, email, contact_number
    FROM dbo.profile;
COMMENT ON VIEW ss.customer_contact IS
    'All customers'' id, email, and phone number (no filter). Use get_customer_email/get_customer_contact_number instead if you only need one customer.';

CREATE VIEW ss.customer_address AS
    SELECT customer_address_id, customer_id, street_line_1, street_line_2,
           city, state, country, postal_code, is_primary
    FROM dbo.address;
COMMENT ON VIEW ss.customer_address IS
    'Every address row for every customer (no filter), including is_primary. Use get_customer_addresses(id)/get_customer_primary_address(id) instead if you only need one customer.';

CREATE VIEW ss.customer_payment AS
    SELECT payment_method_id, customer_id, payment_type, card_last_four, billing_address
    FROM dbo.payment_method;
COMMENT ON VIEW ss.customer_payment IS
    'Every payment method row for every customer (no filter). Use get_customer_payment_methods(id) instead if you only need one customer.';

-- Distinct city/state/country combos, used by the caching-worker to warm the
-- Redis location lookup at startup (see integration/caching_worker).
CREATE VIEW ss.address_locations AS
    SELECT DISTINCT city, state, country
    FROM dbo.address;
COMMENT ON VIEW ss.address_locations IS
    'Distinct (city, state, country) combinations that appear in any customer address. Not customer-specific — a location lookup list, not an address list.';

-- Combined profile row for the customer-api's User resource (no single
-- existing view/function returns first/last name + email + contact together).
CREATE VIEW ss.customer_profile AS
    SELECT customer_id, first_name, last_name, email, contact_number
    FROM dbo.profile;
COMMENT ON VIEW ss.customer_profile IS
    'Every customer''s full profile: name, email, and phone in one row (no filter). Covers everything customer_name + customer_contact do together.';

-- ============================================================
-- Functions (ss schema) — Postgres has no read-only "stored procedure"
-- distinct from a function, so these are SQL functions returning result sets.
-- SECURITY DEFINER + a locked-down search_path: these run with the owner's
-- (not the caller's) privileges, since customer/worker/manager are never
-- granted access to `dbo` directly — only via functions/views in `ss`.
-- ============================================================

CREATE FUNCTION ss.get_customer_name(p_customer_id INTEGER)
RETURNS TABLE (first_name VARCHAR, last_name VARCHAR)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT first_name, last_name
    FROM dbo.profile
    WHERE customer_id = p_customer_id;
$$;
COMMENT ON FUNCTION ss.get_customer_name(INTEGER) IS
    'First and last name of ONE customer, given their known customer_id.';

CREATE FUNCTION ss.get_customer_primary_address(p_customer_id INTEGER)
RETURNS TABLE (
    customer_address_id INTEGER, street_line_1 VARCHAR, street_line_2 VARCHAR,
    city VARCHAR, state VARCHAR, country VARCHAR, postal_code VARCHAR, is_primary BOOLEAN
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT customer_address_id, street_line_1, street_line_2, city, state, country, postal_code, is_primary
    FROM dbo.address
    WHERE customer_id = p_customer_id AND is_primary;
$$;
COMMENT ON FUNCTION ss.get_customer_primary_address(INTEGER) IS
    'The single address flagged is_primary for ONE customer, given their known customer_id. Empty if none is flagged primary.';

CREATE FUNCTION ss.get_customer_addresses(p_customer_id INTEGER)
RETURNS TABLE (
    customer_address_id INTEGER, street_line_1 VARCHAR, street_line_2 VARCHAR,
    city VARCHAR, state VARCHAR, country VARCHAR, postal_code VARCHAR, is_primary BOOLEAN
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT customer_address_id, street_line_1, street_line_2, city, state, country, postal_code, is_primary
    FROM dbo.address
    WHERE customer_id = p_customer_id;
$$;
COMMENT ON FUNCTION ss.get_customer_addresses(INTEGER) IS
    'ALL address rows for ONE customer, given their known customer_id.';

CREATE FUNCTION ss.get_customer_payment_methods(p_customer_id INTEGER)
RETURNS TABLE (
    payment_method_id INTEGER, payment_type dbo.payment_type,
    card_last_four CHAR(4), billing_address TEXT
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT payment_method_id, payment_type, card_last_four, billing_address
    FROM dbo.payment_method
    WHERE customer_id = p_customer_id;
$$;
COMMENT ON FUNCTION ss.get_customer_payment_methods(INTEGER) IS
    'ALL payment method rows for ONE customer, given their known customer_id.';

CREATE FUNCTION ss.get_customer_email(p_customer_id INTEGER)
RETURNS VARCHAR
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT email FROM dbo.profile WHERE customer_id = p_customer_id;
$$;
COMMENT ON FUNCTION ss.get_customer_email(INTEGER) IS
    'The email address of ONE customer, given their known customer_id.';

CREATE FUNCTION ss.get_customer_contact_number(p_customer_id INTEGER)
RETURNS VARCHAR
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT contact_number FROM dbo.profile WHERE customer_id = p_customer_id;
$$;
COMMENT ON FUNCTION ss.get_customer_contact_number(INTEGER) IS
    'The phone number of ONE customer, given their known customer_id.';

CREATE FUNCTION ss.find_customer_by_email(p_email VARCHAR)
RETURNS TABLE (customer_id INTEGER, first_name VARCHAR, last_name VARCHAR, email VARCHAR, contact_number VARCHAR)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT customer_id, first_name, last_name, email, contact_number
    FROM dbo.profile
    WHERE email = p_email;
$$;
COMMENT ON FUNCTION ss.find_customer_by_email(VARCHAR) IS
    'Looks up a customer''s id/name/contact info by their exact email address — use this to resolve an email to a customer_id.';

CREATE FUNCTION ss.find_customers_by_address(p_city VARCHAR, p_state VARCHAR, p_country VARCHAR)
RETURNS TABLE (customer_id INTEGER, first_name VARCHAR, last_name VARCHAR)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT DISTINCT p.customer_id, p.first_name, p.last_name
    FROM dbo.profile p
    JOIN dbo.address a ON a.customer_id = p.customer_id
    WHERE a.city = p_city AND a.state = p_state AND a.country = p_country;
$$;
COMMENT ON FUNCTION ss.find_customers_by_address(VARCHAR, VARCHAR, VARCHAR) IS
    'Customers who have an address exactly matching the given city, state, and country (all three required — no partial match).';

-- ============================================================
-- Roles & grants
-- customer / worker / manager get access to ss (views + functions) only —
-- no direct access to dbo tables. They now have LOGIN so the FastAPI apps
-- can connect directly as the role matching the caller's JWT role claim.
-- NOTE: rotate db_password (see \set above) before any real deployment.
-- psql doesn't interpolate :'vars' inside a dollar-quoted DO $$ body, so each
-- statement is built as text and run via \gexec instead. Roles are cluster-
-- wide and survive `DROP DATABASE`/recreation, so this ALTERs an existing
-- role's password to match db_password rather than silently keeping
-- whatever password it already had from a previous run.
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
GRANT SELECT ON ALL TABLES IN SCHEMA ss TO customer, worker, manager;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ss TO customer, worker, manager;

-- Keep future ss objects covered automatically.
ALTER DEFAULT PRIVILEGES IN SCHEMA ss GRANT SELECT ON TABLES TO customer, worker, manager;
ALTER DEFAULT PRIVILEGES IN SCHEMA ss GRANT EXECUTE ON FUNCTIONS TO customer, worker, manager;
