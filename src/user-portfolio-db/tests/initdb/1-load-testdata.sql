/*
 * Test data for user-portfolio-db
 * Copyright 2024 Google LLC
 */

-- Insert test users (if users table exists)
INSERT INTO users (accountid, username, passhash, firstname, lastname, birthday, timezone, address, state, zip, ssn)
VALUES 
    ('1000000001', 'testuser1', E'\\x1234', 'Test', 'User1', '1990-01-01', 'UTC', '123 Main St', 'CA', '90210', '123-45-6789'),
    ('1000000002', 'testuser2', E'\\x1234', 'Test', 'User2', '1990-01-01', 'UTC', '123 Main St', 'CA', '90210', '123-45-6790'),
    ('1000000003', 'testuser3', E'\\x1234', 'Test', 'User3', '1990-01-01', 'UTC', '123 Main St', 'CA', '90210', '123-45-6791')
ON CONFLICT (accountid) DO NOTHING;

-- Insert test portfolios
INSERT INTO user_portfolios (accountid, currency, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation,
                           tier1_value, tier2_value, tier3_value, total_value)
VALUES 
    ('1000000001', 'USD', 40.00, 30.00, 30.00, 100.00, 4000.00, 3000.00, 3000.00, 10000.00),
    ('1000000002', 'USD', 50.00, 25.00, 25.00, 100.00, 5000.00, 2500.00, 2500.00, 10000.00),
    ('1000000003', 'USD', 60.00, 20.00, 20.00, 100.00, 6000.00, 2000.00, 2000.00, 10000.00)
ON CONFLICT (accountid) DO NOTHING;

-- Insert test transactions
INSERT INTO portfolio_transactions (accountid, transaction_type, tier1_change, tier2_change, tier3_change, total_amount, fees, status)
VALUES 
    ('1000000001', 'INVEST', 40.00, 30.00, 30.00, 100.00, 0.00, 'COMPLETED'),
    ('1000000002', 'INVEST', 50.00, 25.00, 25.00, 100.00, 0.00, 'COMPLETED'),
    ('1000000003', 'INVEST', 60.00, 20.00, 20.00, 100.00, 0.00, 'COMPLETED'),
    ('1000000001', 'WITHDRAWAL', -10.00, -5.00, -5.00, -20.00, 1.00, 'COMPLETED')
ON CONFLICT DO NOTHING;

-- Insert test analytics
INSERT INTO portfolio_analytics (accountid, total_value, total_invested, total_gain_loss, gain_loss_percentage, risk_score)
VALUES 
    ('1000000001', 10000.00, 10000.00, 0.00, 0.0000, 0.5000),
    ('1000000002', 10000.00, 10000.00, 0.00, 0.0000, 0.4000),
    ('1000000003', 10000.00, 10000.00, 0.00, 0.0000, 0.6000)
ON CONFLICT (id) DO NOTHING;
