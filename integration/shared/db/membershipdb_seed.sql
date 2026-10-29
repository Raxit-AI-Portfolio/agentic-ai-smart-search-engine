-- MembershipDb — sample seed data (demo/portfolio realism only)
-- Run as postgres (superuser) after membershipdb_schema.sql.
-- crypt()/gen_salt('bf') is pgcrypto's bcrypt hashing.

-- One demo account per role, for the Streamlit login dropdown.
INSERT INTO dbo.user_account (username, password_hash, email, role, customer_id) VALUES
    ('alice', crypt('customer123', gen_salt('bf')), 'alice@ekart.com', 'customer', 1),
    ('bob',   crypt('worker123',   gen_salt('bf')), 'bob@ekart.com',   'worker',   NULL),
    ('carol', crypt('manager123',  gen_salt('bf')), 'carol@ekart.com', 'manager',  NULL);

-- Two more customer logins, matching CustomerDb's sample profiles (see
-- customerdb_seed.sql), so more than one customer account is available.
INSERT INTO dbo.user_account (username, password_hash, email, role, customer_id) VALUES
    ('rohan.mehta', crypt('customer123', gen_salt('bf')), 'rohan.mehta@yahoo.com', 'customer', 2),
    ('ananya.iyer', crypt('customer123', gen_salt('bf')), 'ananya.iyer@outlook.com', 'customer', 3);
