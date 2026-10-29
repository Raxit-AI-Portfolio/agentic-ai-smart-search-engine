-- MembershipDb — PostgreSQL setup script
-- Shared identity store for both the Customer API and Operations API.
-- Holds login accounts only (username/password/role/customer_id) — no
-- business data. `role` matches a login role name in CustomerDb/OperationsDb
-- (customer/worker/manager); both APIs use it, after authenticating here, to
-- pick which of their own DB connection pools to use.

-- Password for the auth_service login role below — override with
-- `psql -v db_password='...'` rather than editing this literal.
\set db_password 'Abc123'

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS dbo;
CREATE SCHEMA IF NOT EXISTS ss;

CREATE TYPE dbo.user_role AS ENUM ('customer', 'worker', 'manager');

CREATE TABLE dbo.user_account (
    user_id        SERIAL PRIMARY KEY,
    username       VARCHAR(100) NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    email          VARCHAR(255) NOT NULL,
    role           dbo.user_role NOT NULL,
    customer_id    INTEGER,  -- CustomerDb.dbo.profile.customer_id when role = 'customer' (cross-db, not enforced)
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMP NOT NULL DEFAULT now()
);

-- Demo accounts are seeded separately — see membershipdb_seed.sql.

-- SECURITY DEFINER + locked-down search_path: auth_service is only ever
-- granted EXECUTE on this function, never SELECT on dbo.user_account itself,
-- so a compromised API can authenticate callers but can't dump the table.
CREATE FUNCTION ss.authenticate(p_username VARCHAR, p_password TEXT)
RETURNS TABLE (username VARCHAR, email VARCHAR, role dbo.user_role, customer_id INTEGER)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT username, email, role, customer_id
    FROM dbo.user_account
    WHERE username = p_username
      AND is_active
      AND password_hash = public.crypt(p_password, password_hash);
$$;

-- Logout revocation list. This lives in the DB (rather than in-process
-- memory) because the JWT is now verified independently by the Shared API,
-- the Customer API, and the Operations API — three separate processes that
-- all need to see the same "this token was logged out" fact.
CREATE TABLE dbo.revoked_token (
    jti         UUID PRIMARY KEY,
    revoked_at  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE FUNCTION ss.revoke_token(p_jti UUID)
RETURNS VOID
LANGUAGE sql SECURITY DEFINER SET search_path = '' AS $$
    INSERT INTO dbo.revoked_token (jti) VALUES (p_jti)
    ON CONFLICT (jti) DO NOTHING;
$$;

CREATE FUNCTION ss.is_token_revoked(p_jti UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT EXISTS (SELECT 1 FROM dbo.revoked_token WHERE jti = p_jti);
$$;

-- psql doesn't interpolate :'vars' inside a dollar-quoted DO $$ body, so the
-- statement is built as text and run via \gexec instead. auth_service is a
-- cluster-wide role that survives DROP DATABASE/recreation, so this ALTERs
-- an existing role's password to match db_password rather than silently
-- keeping whatever password it already had from a previous run.
SELECT format(
    CASE WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'auth_service')
         THEN 'ALTER ROLE auth_service WITH PASSWORD %L'
         ELSE 'CREATE ROLE auth_service LOGIN PASSWORD %L'
    END, :'db_password')
\gexec

GRANT USAGE ON SCHEMA ss TO auth_service;
GRANT EXECUTE ON FUNCTION
    ss.authenticate(VARCHAR, TEXT),
    ss.revoke_token(UUID),
    ss.is_token_revoked(UUID)
    TO auth_service;
