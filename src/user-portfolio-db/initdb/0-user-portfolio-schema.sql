/*
 * Copyright 2020, Google LLC.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create users table (if not exists, as it might be created by accounts-db)
CREATE TABLE IF NOT EXISTS users (
  accountid CHAR(10) PRIMARY KEY,
  username VARCHAR(64) UNIQUE NOT NULL,
  passhash BYTEA NOT NULL,
  firstname VARCHAR(64) NOT NULL,
  lastname VARCHAR(64) NOT NULL,
  birthday DATE NOT NULL,
  timezone VARCHAR(8) NOT NULL,
  address VARCHAR(64) NOT NULL,
  state CHAR(2) NOT NULL,
  zip VARCHAR(5) NOT NULL,
  ssn CHAR(11) NOT NULL
);

-- Create user_portfolios table for tier-based fund allocation
CREATE TABLE IF NOT EXISTS user_portfolios (
  accountid VARCHAR(10) NOT NULL,
  currency TEXT NOT NULL DEFAULT 'USD',
  tier1_allocation NUMERIC(15,2) NOT NULL DEFAULT 0,
  tier2_allocation NUMERIC(15,2) NOT NULL DEFAULT 0,
  tier3_allocation NUMERIC(15,2) NOT NULL DEFAULT 0,
  total_allocation NUMERIC(15,2) NOT NULL DEFAULT 0,
  tier1_value NUMERIC(15,2) NOT NULL DEFAULT 0,
  tier2_value NUMERIC(15,2) NOT NULL DEFAULT 0,
  tier3_value NUMERIC(15,2) NOT NULL DEFAULT 0, 
  total_value NUMERIC(15,2) NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT check_tier_allocation CHECK (tier1_allocation + tier2_allocation + tier3_allocation = total_allocation),
  CONSTRAINT check_tier_value CHECK (tier1_value + tier2_value + tier3_value = total_value)
);

-- Create indexes for user_portfolios table
CREATE INDEX IF NOT EXISTS idx_user_portfolios_accountid ON user_portfolios (accountid);
CREATE INDEX IF NOT EXISTS idx_user_portfolios_created_at ON user_portfolios (created_at);


-- Create portfolio_transactions table for fund allocation changes
CREATE TABLE IF NOT EXISTS portfolio_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  accountid VARCHAR(10) NOT NULL REFERENCES user_portfolios(accountid) ON DELETE CASCADE,
  transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('INVEST', 'WITHDRAWAL')),
  tier1_change NUMERIC(5,2) DEFAULT 0,
  tier2_change NUMERIC(5,2) DEFAULT 0,
  tier3_change NUMERIC(5,2) DEFAULT 0,
  total_amount NUMERIC(15,2) NOT NULL,
  fees NUMERIC(10,2) DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'COMPLETED', 'FAILED', 'CANCELLED')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT check_tier_change CHECK (tier1_change + tier2_change + tier3_change = total_amount)
);

-- Create indexes for portfolio_transactions table
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_accountid ON portfolio_transactions (accountid);
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_type ON portfolio_transactions (transaction_type);
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_status ON portfolio_transactions (status);
CREATE INDEX IF NOT EXISTS idx_portfolio_transactions_created_at ON portfolio_transactions (created_at);

-- Create portfolio_analytics table for storing calculated metrics
CREATE TABLE IF NOT EXISTS portfolio_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  accountid VARCHAR(10) NOT NULL REFERENCES user_portfolios(accountid) ON DELETE CASCADE,
  total_value NUMERIC(15,2) NOT NULL DEFAULT 0,
  total_invested NUMERIC(15,2) NOT NULL DEFAULT 0,
  total_gain_loss NUMERIC(15,2) NOT NULL DEFAULT 0,
  gain_loss_percentage NUMERIC(8,4) NOT NULL DEFAULT 0,
  risk_score NUMERIC(5,4) DEFAULT 0,
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for portfolio_analytics table
CREATE INDEX IF NOT EXISTS idx_portfolio_analytics_accountid ON portfolio_analytics (accountid);
CREATE INDEX IF NOT EXISTS idx_portfolio_analytics_calculated_at ON portfolio_analytics (calculated_at);

-- Create functions for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_user_portfolios_updated_at BEFORE UPDATE ON user_portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portfolio_transactions_updated_at BEFORE UPDATE ON portfolio_transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create a view for portfolio summary
CREATE OR REPLACE VIEW portfolio_summary AS
SELECT 
    up.accountid,
    up.total_value,
    up.currency,
    up.tier1_allocation,
    up.tier2_allocation,
    up.tier3_allocation,
    up.tier1_value,
    up.tier2_value,
    up.tier3_value,
    up.created_at,
    up.updated_at
FROM user_portfolios up;
