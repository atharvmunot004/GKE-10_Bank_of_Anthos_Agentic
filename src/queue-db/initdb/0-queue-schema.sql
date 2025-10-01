-- Copyright 2024 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     https://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

-- Create the investment and withdrawal queue table
CREATE TABLE IF NOT EXISTS investment_withdrawal_queue (
    queue_id SERIAL PRIMARY KEY,
    accountid VARCHAR(20) NOT NULL,
    tier_1 DECIMAL(20, 8) NOT NULL CHECK (tier_1 >= 0),
    tier_2 DECIMAL(20, 8) NOT NULL CHECK (tier_2 >= 0),
    tier_3 DECIMAL(20, 8) NOT NULL CHECK (tier_3 >= 0),
    uuid VARCHAR(36) UNIQUE NOT NULL,
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('INVEST', 'WITHDRAW')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_queue_uuid ON investment_withdrawal_queue(uuid);
CREATE INDEX IF NOT EXISTS idx_queue_accountid ON investment_withdrawal_queue(accountid);
CREATE INDEX IF NOT EXISTS idx_queue_status ON investment_withdrawal_queue(status);
CREATE INDEX IF NOT EXISTS idx_queue_created_at ON investment_withdrawal_queue(created_at);
CREATE INDEX IF NOT EXISTS idx_queue_transaction_type ON investment_withdrawal_queue(transaction_type);
CREATE INDEX IF NOT EXISTS idx_queue_status_type ON investment_withdrawal_queue(status, transaction_type);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at on row updates
CREATE TRIGGER update_investment_withdrawal_queue_updated_at
    BEFORE UPDATE ON investment_withdrawal_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to set processed_at when status changes to COMPLETED or FAILED
CREATE OR REPLACE FUNCTION set_processed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('COMPLETED', 'FAILED') AND OLD.status NOT IN ('COMPLETED', 'FAILED') THEN
        NEW.processed_at = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to set processed_at timestamp
CREATE TRIGGER set_investment_withdrawal_queue_processed_at
    BEFORE UPDATE ON investment_withdrawal_queue
    FOR EACH ROW
    EXECUTE FUNCTION set_processed_at();

-- Create view for queue statistics
CREATE OR REPLACE VIEW queue_statistics AS
SELECT 
    status,
    transaction_type,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (COALESCE(processed_at, CURRENT_TIMESTAMP) - created_at))) as avg_processing_time_seconds
FROM investment_withdrawal_queue
GROUP BY status, transaction_type;

-- Create view for account queue summary
CREATE OR REPLACE VIEW account_queue_summary AS
SELECT 
    accountid,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending_requests,
    COUNT(CASE WHEN status = 'PROCESSING' THEN 1 END) as processing_requests,
    COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_requests,
    COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_requests,
    COUNT(CASE WHEN status = 'CANCELLED' THEN 1 END) as cancelled_requests,
    SUM(CASE WHEN transaction_type = 'INVEST' THEN tier_1 + tier_2 + tier_3 ELSE 0 END) as total_investment_amount,
    SUM(CASE WHEN transaction_type = 'WITHDRAW' THEN tier_1 + tier_2 + tier_3 ELSE 0 END) as total_withdrawal_amount
FROM investment_withdrawal_queue
GROUP BY accountid;

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE investment_withdrawal_queue TO queue-admin;
GRANT ALL PRIVILEGES ON SEQUENCE investment_withdrawal_queue_queue_id_seq TO queue-admin;
GRANT SELECT ON VIEW queue_statistics TO queue-admin;
GRANT SELECT ON VIEW account_queue_summary TO queue-admin;
