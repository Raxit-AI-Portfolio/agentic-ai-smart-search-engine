-- CustomerDb — sample seed data (demo/portfolio realism only)
-- Run as postgres (superuser) after customerdb_schema.sql — customer/worker/
-- manager have no direct grants on dbo, only on ss.
--
-- One profile, one primary address, and one payment method per customer,
-- inserted in the same order so customer_id / customer_address_id /
-- payment_method_id all line up 1:1 (relied on by operationsdb_seed.sql's
-- cross-database references, which Postgres cannot enforce as real FKs).

INSERT INTO dbo.profile (first_name, last_name, email, contact_number) VALUES
    ('Priya',     'Sharma',   'priya.sharma@gmail.com',    '+91-9821345671'),
    ('Rohan',     'Mehta',    'rohan.mehta@yahoo.com',     '+91-9833456782'),
    ('Ananya',    'Iyer',     'ananya.iyer@outlook.com',   '+91-9845567893'),
    ('Vikram',    'Nair',     'vikram.nair@gmail.com',     '+91-9856678904'),
    ('Sneha',     'Patel',    'sneha.patel@gmail.com',     '+91-9867789015'),
    ('Arjun',     'Reddy',    'arjun.reddy@gmail.com',     '+91-9878890126'),
    ('Kavya',     'Menon',    'kavya.menon@gmail.com',     '+91-9889901237'),
    ('Aditya',    'Kapoor',   'aditya.kapoor@gmail.com',   '+91-9891012348'),
    ('Ishita',    'Verma',    'ishita.verma@gmail.com',    '+91-9802123459'),
    ('Karan',     'Malhotra', 'karan.malhotra@gmail.com',  '+91-9813234560'),
    ('Neha',      'Joshi',    'neha.joshi@gmail.com',      '+91-9824345671'),
    ('Siddharth', 'Rao',      'siddharth.rao@gmail.com',   '+91-9835456782');

INSERT INTO dbo.address (customer_id, street_line_1, street_line_2, city, state, country, postal_code, is_primary) VALUES
    (1,  '14 Marine Drive',  'Apt 302',        'Mumbai',     'Maharashtra',     'India', '400020', TRUE),
    (2,  '27 MG Road',       NULL,             'Bengaluru',  'Karnataka',       'India', '560001', TRUE),
    (3,  '9 Anna Salai',     'Flat 5B',        'Chennai',    'Tamil Nadu',      'India', '600002', TRUE),
    (4,  '55 MG Road',       NULL,             'Kochi',      'Kerala',          'India', '682016', TRUE),
    (5,  '3 CG Road',        'Near Law Garden','Ahmedabad',  'Gujarat',         'India', '380009', TRUE),
    (6,  '21 Banjara Hills', NULL,             'Hyderabad',  'Telangana',       'India', '500034', TRUE),
    (7,  '8 FC Road',        'Flat 12',        'Pune',       'Maharashtra',     'India', '411004', TRUE),
    (8,  '41 Connaught Place', NULL,           'Delhi',      'Delhi',           'India', '110001', TRUE),
    (9,  '17 MI Road',       NULL,             'Jaipur',     'Rajasthan',       'India', '302001', TRUE),
    (10, '5 Sector 17',      'House 22',       'Chandigarh', 'Punjab',          'India', '160017', TRUE),
    (11, '30 Civil Lines',   NULL,             'Nagpur',     'Maharashtra',     'India', '440001', TRUE),
    (12, '12 Arera Colony',  NULL,             'Bhopal',     'Madhya Pradesh',  'India', '462016', TRUE);

INSERT INTO dbo.payment_method (customer_id, payment_type, card_last_four, billing_address) VALUES
    (1,  'Credit Card', '4821', '14 Marine Drive, Apt 302, Mumbai, Maharashtra, India'),
    (2,  'Debit Card',  '3390', '27 MG Road, Bengaluru, Karnataka, India'),
    (3,  'Credit Card', '7712', '9 Anna Salai, Flat 5B, Chennai, Tamil Nadu, India'),
    (4,  'Debit Card',  '2245', '55 MG Road, Kochi, Kerala, India'),
    (5,  'Credit Card', '9081', '3 CG Road, Near Law Garden, Ahmedabad, Gujarat, India'),
    (6,  'Debit Card',  '6634', '21 Banjara Hills, Hyderabad, Telangana, India'),
    (7,  'Credit Card', '1123', '8 FC Road, Flat 12, Pune, Maharashtra, India'),
    (8,  'Debit Card',  '8850', '41 Connaught Place, Delhi, Delhi, India'),
    (9,  'Credit Card', '4409', '17 MI Road, Jaipur, Rajasthan, India'),
    (10, 'Debit Card',  '5567', '5 Sector 17, House 22, Chandigarh, Punjab, India'),
    (11, 'Credit Card', '3312', '30 Civil Lines, Nagpur, Maharashtra, India'),
    (12, 'Debit Card',  '7790', '12 Arera Colony, Bhopal, Madhya Pradesh, India');
