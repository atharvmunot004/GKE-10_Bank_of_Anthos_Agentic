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

-- Load test data for queue-db
-- This script loads sample investment and withdrawal requests for testing

-- Insert sample investment requests
INSERT INTO investment_withdrawal_queue (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status, created_at) VALUES
('1011226111', 1000.50, 2000.75, 500.25, '550e8400-e29b-41d4-a716-446655440001', 'INVEST', 'PENDING', CURRENT_TIMESTAMP - INTERVAL '1 hour'),
('1011226111', 2000.00, 3000.00, 1000.00, '550e8400-e29b-41d4-a716-446655440002', 'INVEST', 'PROCESSING', CURRENT_TIMESTAMP - INTERVAL '30 minutes'),
('1011226111', 500.00, 750.00, 250.00, '550e8400-e29b-41d4-a716-446655440003', 'INVEST', 'COMPLETED', CURRENT_TIMESTAMP - INTERVAL '2 hours'),
('1011226112', 1500.25, 2500.50, 750.75, '550e8400-e29b-41d4-a716-446655440004', 'INVEST', 'PENDING', CURRENT_TIMESTAMP - INTERVAL '45 minutes'),
('1011226112', 3000.00, 4000.00, 1500.00, '550e8400-e29b-41d4-a716-446655440005', 'INVEST', 'FAILED', CURRENT_TIMESTAMP - INTERVAL '1 day'),
('1011226113', 800.00, 1200.00, 400.00, '550e8400-e29b-41d4-a716-446655440006', 'INVEST', 'COMPLETED', CURRENT_TIMESTAMP - INTERVAL '3 hours');

-- Insert sample withdrawal requests
INSERT INTO investment_withdrawal_queue (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status, created_at) VALUES
('1011226111', 500.00, 1000.00, 250.00, '550e8400-e29b-41d4-a716-446655440007', 'WITHDRAW', 'PENDING', CURRENT_TIMESTAMP - INTERVAL '20 minutes'),
('1011226111', 1000.00, 1500.00, 500.00, '550e8400-e29b-41d4-a716-446655440008', 'WITHDRAW', 'PROCESSING', CURRENT_TIMESTAMP - INTERVAL '10 minutes'),
('1011226112', 750.00, 1250.00, 375.00, '550e8400-e29b-41d4-a716-446655440009', 'WITHDRAW', 'COMPLETED', CURRENT_TIMESTAMP - INTERVAL '4 hours'),
('1011226112', 2000.00, 3000.00, 1000.00, '550e8400-e29b-41d4-a716-446655440010', 'WITHDRAW', 'CANCELLED', CURRENT_TIMESTAMP - INTERVAL '1 day'),
('1011226113', 600.00, 900.00, 300.00, '550e8400-e29b-41d4-a716-446655440011', 'WITHDRAW', 'PENDING', CURRENT_TIMESTAMP - INTERVAL '5 minutes'),
('1011226114', 1200.00, 1800.00, 600.00, '550e8400-e29b-41d4-a716-446655440012', 'WITHDRAW', 'FAILED', CURRENT_TIMESTAMP - INTERVAL '2 days');

-- Update some records to have processed_at timestamps
UPDATE investment_withdrawal_queue 
SET processed_at = created_at + INTERVAL '15 minutes'
WHERE status IN ('COMPLETED', 'FAILED') AND processed_at IS NULL;

-- Update some records to have updated_at timestamps different from created_at
UPDATE investment_withdrawal_queue 
SET updated_at = created_at + INTERVAL '5 minutes'
WHERE status IN ('PROCESSING', 'FAILED', 'CANCELLED');

-- Display summary of loaded data
SELECT 
    'Investment Requests' as request_type,
    status,
    COUNT(*) as count
FROM investment_withdrawal_queue 
WHERE transaction_type = 'INVEST'
GROUP BY status
UNION ALL
SELECT 
    'Withdrawal Requests' as request_type,
    status,
    COUNT(*) as count
FROM investment_withdrawal_queue 
WHERE transaction_type = 'WITHDRAW'
GROUP BY status
ORDER BY request_type, status;
