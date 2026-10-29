-- OperationsDb — sample seed data (demo/portfolio realism only)
-- Run as postgres (superuser) after operationsdb_schema.sql AND after
-- customerdb_seed.sql (this data assumes customer_id 1-12 exist there, and
-- that CustomerDb's payment_method_id / customer_address_id are also 1-12,
-- one each per customer — cross-database references Postgres cannot
-- enforce as real FKs, see the comment at the top of operationsdb_schema.sql).

INSERT INTO dbo.product (category, sub_category, product_name, quantity, price) VALUES
    ('Electronics',        'Laptops',            'Dell Inspiron 15',                25, 42999.00),
    ('Electronics',        'Laptops',            'HP Pavilion x360',                18, 54999.00),
    ('Electronics',        'Laptops',            'Lenovo ThinkPad E14',             12, 61999.00),
    ('Electronics',        'Laptops',            'Apple MacBook Air M2',             8, 99999.00),
    ('Electronics',        'Mobiles',            'Samsung Galaxy S23',              30, 74999.00),
    ('Electronics',        'Mobiles',            'OnePlus Nord CE 3',               40, 26999.00),
    ('Electronics',        'Mobiles',            'Apple iPhone 14',                 15, 69999.00),
    ('Electronics',        'Mobiles',            'Xiaomi Redmi Note 12',            50, 18999.00),
    ('Home & Kitchen',     'Cookware',           'Prestige Non-Stick Tawa',         60,   899.00),
    ('Home & Kitchen',     'Cookware',           'Milton Insulated Casserole',      45,  1299.00),
    ('Home & Kitchen',     'Cookware',           'Pigeon Induction Pressure Cooker',35,  1899.00),
    ('Home & Kitchen',     'Cookware',           'Borosil Glass Storage Set',       55,  1099.00),
    ('Fashion',            'Men''s Clothing',    'Levi''s Slim Fit Jeans',          70,  2199.00),
    ('Fashion',            'Men''s Clothing',    'Allen Solly Formal Shirt',        65,  1499.00),
    ('Fashion',            'Men''s Clothing',    'Puma Running Shoes',              40,  3499.00),
    ('Fashion',            'Men''s Clothing',    'Wildcraft Travel Backpack',       30,  1799.00),
    ('Grocery',            'Snacks & Beverages', 'Tata Tea Gold 1kg',              100,   549.00),
    ('Grocery',            'Snacks & Beverages', 'Amul Butter 500g',                90,   269.00),
    ('Grocery',            'Snacks & Beverages', 'Haldiram''s Namkeen Mix',        120,   199.00),
    ('Grocery',            'Snacks & Beverages', 'Nescafe Classic Coffee 200g',     80,   399.00),
    ('Books & Stationery', 'Books',              'Atomic Habits - James Clear',     50,   499.00),
    ('Books & Stationery', 'Books',              'The Alchemist - Paulo Coelho',    45,   399.00),
    ('Books & Stationery', 'Books',              'Rich Dad Poor Dad',               40,   349.00),
    ('Books & Stationery', 'Books',              'Classmate Notebook Pack',        200,   249.00);

-- All dates below are relative to v_today (= CURRENT_DATE at seed time) so
-- this data stays "recent" no matter when the script runs, instead of
-- drifting into the past. v_today - 18 days anchors the most recent event
-- (order 18 / delivery of order 16); every other date keeps its original
-- offset from that anchor.
DO $$
DECLARE
    v_today date := CURRENT_DATE;
BEGIN

-- customer_id references CustomerDb.dbo.profile (1-12, from customerdb_seed.sql).
INSERT INTO dbo.orders (customer_id, order_date, order_status) VALUES
    (1,  (v_today - 58) + TIME '10:15:00', 'Delivered'),
    (2,  (v_today - 56) + TIME '11:05:00', 'Delivered'),
    (3,  (v_today - 53) + TIME '09:40:00', 'Shipped'),
    (4,  (v_today - 46) + TIME '14:20:00', 'Processing'),
    (5,  (v_today - 44) + TIME '16:10:00', 'Paid'),
    (6,  (v_today - 42) + TIME '12:00:00', 'Pending'),
    (7,  (v_today - 41) + TIME '17:30:00', 'Cancelled'),
    (8,  (v_today - 39) + TIME '08:50:00', 'Refunded'),
    (9,  (v_today - 37) + TIME '13:15:00', 'Returned'),
    (10, (v_today - 35) + TIME '10:00:00', 'Delivered'),
    (11, (v_today - 33) + TIME '15:45:00', 'Shipped'),
    (12, (v_today - 31) + TIME '09:20:00', 'Paid'),
    (1,  (v_today - 29) + TIME '11:30:00', 'Pending'),
    (3,  (v_today - 27) + TIME '14:00:00', 'Delivered'),
    (5,  (v_today - 25) + TIME '16:40:00', 'Processing'),
    (7,  (v_today - 23) + TIME '10:10:00', 'Delivered'),
    (9,  (v_today - 21) + TIME '12:50:00', 'Shipped'),
    (11, (v_today - 19) + TIME '09:05:00', 'Paid');

-- uom is assigned per product category: Electronics/Fashion/Books & Stationery
-- sell by the piece ('pcs'), Home & Kitchen cookware by the 'set', and
-- Grocery by the packaged 'pack'.
INSERT INTO dbo.order_product (order_id, product_id, special_priced, quantity, uom) VALUES
    (1, 1, TRUE, 1, 'pcs'), (1, 5, FALSE, 1, 'pcs'),
    (2, 9, FALSE, 2, 'set'), (2, 10, FALSE, 1, 'set'),
    (3, 13, FALSE, 2, 'pcs'),
    (4, 17, FALSE, 3, 'pack'),
    (5, 21, FALSE, 1, 'pcs'), (5, 22, FALSE, 1, 'pcs'),
    (6, 2, FALSE, 1, 'pcs'),
    (7, 6, FALSE, 1, 'pcs'),
    (8, 14, FALSE, 2, 'pcs'),
    (9, 18, FALSE, 4, 'pack'),
    (10, 1, FALSE, 1, 'pcs'), (10, 9, FALSE, 3, 'set'), (10, 13, FALSE, 1, 'pcs'),
    (11, 5, FALSE, 1, 'pcs'), (11, 17, FALSE, 2, 'pack'),
    (12, 21, FALSE, 2, 'pcs'),
    (13, 3, FALSE, 1, 'pcs'),
    (14, 7, FALSE, 1, 'pcs'), (14, 15, FALSE, 1, 'pcs'),
    (15, 19, FALSE, 5, 'pack'),
    (16, 23, FALSE, 1, 'pcs'), (16, 24, FALSE, 3, 'pcs'),
    (17, 10, FALSE, 1, 'set'),
    (18, 2, FALSE, 1, 'pcs'), (18, 6, FALSE, 1, 'pcs');

-- Discounted price for order 1's laptop (special_priced = TRUE above).
INSERT INTO dbo.special_price (order_id, product_id, price) VALUES
    (1, 1, 39999.00);

-- payment_method_id references CustomerDb.dbo.payment_method (= customer_id, 1:1).
-- Skips orders 6/7/13 (Pending/Cancelled — never paid).
-- payment_amount is kept in sync with the invoice total (order_amount +
-- tax_amount, 4% tax) for each order — see dbo.invoice below.
INSERT INTO dbo.payment (order_id, payment_method_id, payment_date, payment_amount) VALUES
    (1,  1,  (v_today - 58) + TIME '10:20:00', 119597.92),
    (2,  2,  (v_today - 56) + TIME '11:10:00',   3220.88),
    (3,  3,  (v_today - 53) + TIME '09:45:00',   4573.92),
    (4,  4,  (v_today - 46) + TIME '14:25:00',   1712.88),
    (5,  5,  (v_today - 44) + TIME '16:15:00',    933.92),
    (8,  8,  (v_today - 39) + TIME '08:55:00',   3117.92),
    (9,  9,  (v_today - 37) + TIME '13:20:00',   1119.04),
    (10, 10, (v_today - 35) + TIME '10:05:00',  49810.80),
    (11, 11, (v_today - 33) + TIME '15:50:00',  79140.88),
    (12, 12, (v_today - 31) + TIME '09:25:00',   1037.92),
    (14, 3,  (v_today - 27) + TIME '14:05:00',  76437.92),
    (15, 5,  (v_today - 25) + TIME '16:45:00',   1034.80),
    (16, 7,  (v_today - 23) + TIME '10:15:00',   1139.84),
    (17, 9,  (v_today - 21) + TIME '12:55:00',   1350.96),
    (18, 11, (v_today - 19) + TIME '09:10:00',  85277.92);

-- payment_id assigned in the same order as the INSERT above (1-15).
-- order_amount = SUM(order_product.quantity * unit price, special-price-aware);
-- tax_amount = order_amount * 0.04 (4% tax).
INSERT INTO dbo.invoice (order_id, payment_id, invoice_date, order_amount, tax_amount) VALUES
    (1,  1,  (v_today - 58) + TIME '10:25:00', 114998.00, 4599.92),
    (2,  2,  (v_today - 56) + TIME '11:15:00',   3097.00,  123.88),
    (3,  3,  (v_today - 53) + TIME '09:50:00',   4398.00,  175.92),
    (4,  4,  (v_today - 46) + TIME '14:30:00',   1647.00,   65.88),
    (5,  5,  (v_today - 44) + TIME '16:20:00',    898.00,   35.92),
    (8,  6,  (v_today - 39) + TIME '09:00:00',   2998.00,  119.92),
    (9,  7,  (v_today - 37) + TIME '13:25:00',   1076.00,   43.04),
    (10, 8,  (v_today - 35) + TIME '10:10:00',  47895.00, 1915.80),
    (11, 9,  (v_today - 33) + TIME '15:55:00',  76097.00, 3043.88),
    (12, 10, (v_today - 31) + TIME '09:30:00',    998.00,   39.92),
    (14, 11, (v_today - 27) + TIME '14:10:00',  73498.00, 2939.92),
    (15, 12, (v_today - 25) + TIME '16:50:00',    995.00,   39.80),
    (16, 13, (v_today - 23) + TIME '10:20:00',   1096.00,   43.84),
    (17, 14, (v_today - 21) + TIME '13:00:00',   1299.00,   51.96),
    (18, 15, (v_today - 19) + TIME '09:15:00',  81998.00, 3279.92);

-- invoice_id assigned in the same order as the INSERT above (1-15).
-- Only Shipped/Delivered/Refunded/Returned orders have a delivery record
-- (Refunded/Returned are modeled as having been delivered first).
-- customer_address_id references CustomerDb.dbo.address (= customer_id, 1:1).
INSERT INTO dbo.delivery (order_id, invoice_id, customer_address_id, delivery_date, delivery_status) VALUES
    (1,  1,  1,  (v_today - 53) + TIME '12:00:00', 'Delivered'),
    (2,  2,  2,  (v_today - 51) + TIME '13:30:00', 'Delivered'),
    (3,  3,  3,  NULL,                              'InTransit'),
    (8,  6,  8,  (v_today - 34) + TIME '10:00:00', 'Delivered'),
    (9,  7,  9,  (v_today - 32) + TIME '11:20:00', 'Delivered'),
    (10, 8,  10, (v_today - 30) + TIME '09:45:00', 'Delivered'),
    (11, 9,  11, NULL,                              'Shipped'),
    (14, 11, 3,  (v_today - 22) + TIME '10:30:00', 'Delivered'),
    (16, 13, 7,  (v_today - 18) + TIME '14:00:00', 'Delivered'),
    (17, 14, 9,  NULL,                              'InTransit');

END $$;
