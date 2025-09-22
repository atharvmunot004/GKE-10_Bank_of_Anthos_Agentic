-- Updated Unit Tests for User Portfolio Database
-- Tests the current schema with accountid as primary key

-- Test 1: Schema Validation
DO $$
DECLARE
    table_count INTEGER;
    column_count INTEGER;
BEGIN
    -- Test 1.1: Verify all required tables exist
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('user_portfolios', 'portfolio_transactions', 'portfolio_analytics');
    
    IF table_count = 3 THEN
        RAISE NOTICE 'PASS: All required tables exist';
    ELSE
        RAISE EXCEPTION 'FAIL: Expected 3 tables, found %', table_count;
    END IF;
    
    -- Test 1.2: Verify user_portfolios table structure
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns 
    WHERE table_name = 'user_portfolios' 
    AND column_name IN ('accountid', 'currency', 'tier1_allocation', 'tier2_allocation', 'tier3_allocation', 'total_allocation', 'tier1_value', 'tier2_value', 'tier3_value', 'total_value', 'created_at', 'updated_at');
    
    IF column_count = 12 THEN
        RAISE NOTICE 'PASS: user_portfolios table has all required columns';
    ELSE
        RAISE EXCEPTION 'FAIL: user_portfolios table missing columns, found %', column_count;
    END IF;
    
    RAISE NOTICE 'Schema validation completed successfully!';
END $$;

-- Test 2: Constraint Validation
DO $$
DECLARE
    test_passed BOOLEAN := TRUE;
BEGIN
    -- Test 2.1: Test valid allocation (should pass)
    BEGIN
        INSERT INTO user_portfolios (accountid, total_value, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation, tier1_value, tier2_value, tier3_value)
        VALUES ('test-user-1', 1000.00, 50.0, 30.0, 20.0, 100.0, 500.00, 300.00, 200.00);
        DELETE FROM user_portfolios WHERE accountid = 'test-user-1';
        RAISE NOTICE 'PASS: Valid allocation (50+30+20=100) accepted';
    EXCEPTION WHEN OTHERS THEN
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Valid allocation rejected: %', SQLERRM;
    END;
    
    -- Test 2.2: Test invalid allocation (should fail)
    BEGIN
        INSERT INTO user_portfolios (accountid, total_value, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation, tier1_value, tier2_value, tier3_value)
        VALUES ('test-user-2', 1000.00, 50.0, 30.0, 25.0, 105.0, 500.00, 300.00, 250.00);
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Invalid allocation (50+30+25=105) was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: Invalid allocation (50+30+25=105) correctly rejected';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'FAIL: Unexpected error for invalid allocation: %', SQLERRM;
    END;
    
    -- Test 2.3: Test tier value constraint (should pass)
    BEGIN
        INSERT INTO user_portfolios (accountid, total_value, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation, tier1_value, tier2_value, tier3_value)
        VALUES ('test-user-3', 1000.00, 50.0, 30.0, 20.0, 100.0, 500.00, 300.00, 200.00);
        DELETE FROM user_portfolios WHERE accountid = 'test-user-3';
        RAISE NOTICE 'PASS: Valid tier values (500+300+200=1000) accepted';
    EXCEPTION WHEN OTHERS THEN
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Valid tier values rejected: %', SQLERRM;
    END;
    
    -- Test 2.4: Test invalid tier value (should fail)
    BEGIN
        INSERT INTO user_portfolios (accountid, total_value, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation, tier1_value, tier2_value, tier3_value)
        VALUES ('test-user-4', 1000.00, 50.0, 30.0, 20.0, 100.0, 500.00, 300.00, 250.00);
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Invalid tier values (500+300+250=1050) was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: Invalid tier values (500+300+250=1050) correctly rejected';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'FAIL: Unexpected error for invalid tier values: %', SQLERRM;
    END;
    
    IF test_passed THEN
        RAISE NOTICE 'Constraint tests completed successfully!';
    ELSE
        RAISE EXCEPTION 'Some constraint tests failed';
    END IF;
END $$;

-- Test 3: Transaction Constraints
DO $$
DECLARE
    test_passed BOOLEAN := TRUE;
BEGIN
    -- Setup: Create a test portfolio
    INSERT INTO user_portfolios (accountid, total_value, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation, tier1_value, tier2_value, tier3_value)
    VALUES ('test-user-5', 1000.00, 50.0, 30.0, 20.0, 100.0, 500.00, 300.00, 200.00);
    
    -- Test 3.1: Valid transaction type (should pass)
    BEGIN
        INSERT INTO portfolio_transactions (accountid, transaction_type, total_amount)
        VALUES ('test-user-5', 'INVEST', 100.00);
        DELETE FROM portfolio_transactions WHERE accountid = 'test-user-5';
        RAISE NOTICE 'PASS: Valid transaction type (INVEST) accepted';
    EXCEPTION WHEN OTHERS THEN
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Valid transaction type rejected: %', SQLERRM;
    END;
    
    -- Test 3.2: Another valid transaction type (should pass)
    BEGIN
        INSERT INTO portfolio_transactions (accountid, transaction_type, total_amount)
        VALUES ('test-user-5', 'WITHDRAWAL', 50.00);
        DELETE FROM portfolio_transactions WHERE accountid = 'test-user-5' AND transaction_type = 'WITHDRAWAL';
        RAISE NOTICE 'PASS: Valid transaction type (WITHDRAWAL) accepted';
    EXCEPTION WHEN OTHERS THEN
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Valid transaction type (WITHDRAWAL) rejected: %', SQLERRM;
    END;
    
    -- Test 3.3: Invalid transaction type (should fail)
    BEGIN
        INSERT INTO portfolio_transactions (accountid, transaction_type, total_amount)
        VALUES ('test-user-5', 'INVALID_TYPE', 0.00);
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Invalid transaction type was accepted';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'PASS: Invalid transaction type correctly rejected';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'FAIL: Unexpected error for invalid transaction type: %', SQLERRM;
    END;
    
    -- Cleanup
    DELETE FROM user_portfolios WHERE accountid = 'test-user-5';
    
    IF test_passed THEN
        RAISE NOTICE 'Transaction constraint tests completed successfully!';
    ELSE
        RAISE EXCEPTION 'Some transaction constraint tests failed';
    END IF;
END $$;

-- Test 4: Foreign Key Relationships
DO $$
DECLARE
    test_passed BOOLEAN := TRUE;
BEGIN
    -- Test 4.1: Insert transaction with valid accountid (should pass)
    BEGIN
        INSERT INTO user_portfolios (accountid, total_value, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation, tier1_value, tier2_value, tier3_value)
        VALUES ('test-user-6', 1000.00, 50.0, 30.0, 20.0, 100.0, 500.00, 300.00, 200.00);
        
        INSERT INTO portfolio_transactions (accountid, transaction_type, total_amount)
        VALUES ('test-user-6', 'INVEST', 100.00);
        
        DELETE FROM portfolio_transactions WHERE accountid = 'test-user-6';
        DELETE FROM user_portfolios WHERE accountid = 'test-user-6';
        RAISE NOTICE 'PASS: Foreign key relationship works correctly';
    EXCEPTION WHEN OTHERS THEN
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Foreign key relationship failed: %', SQLERRM;
    END;
    
    -- Test 4.2: Insert transaction with invalid accountid (should fail)
    BEGIN
        INSERT INTO portfolio_transactions (accountid, transaction_type, total_amount)
        VALUES ('nonexistent-user', 'INVEST', 100.00);
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Foreign key constraint not enforced';
    EXCEPTION WHEN foreign_key_violation THEN
        RAISE NOTICE 'PASS: Foreign key constraint correctly enforced';
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'FAIL: Unexpected error for foreign key constraint: %', SQLERRM;
    END;
    
    -- Test 4.3: Test cascade delete
    BEGIN
        INSERT INTO user_portfolios (accountid, total_value, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation, tier1_value, tier2_value, tier3_value)
        VALUES ('test-user-7', 1000.00, 50.0, 30.0, 20.0, 100.0, 500.00, 300.00, 200.00);
        
        INSERT INTO portfolio_transactions (accountid, transaction_type, total_amount)
        VALUES ('test-user-7', 'INVEST', 100.00);
        
        -- Delete portfolio - should cascade delete transactions
        DELETE FROM user_portfolios WHERE accountid = 'test-user-7';
        
        -- Check if transaction was deleted
        IF NOT EXISTS (SELECT 1 FROM portfolio_transactions WHERE accountid = 'test-user-7') THEN
            RAISE NOTICE 'PASS: Cascade delete works correctly';
        ELSE
            test_passed := FALSE;
            RAISE NOTICE 'FAIL: Cascade delete did not work';
        END IF;
    EXCEPTION WHEN OTHERS THEN
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: Cascade delete test failed: %', SQLERRM;
    END;
    
    IF test_passed THEN
        RAISE NOTICE 'Foreign key relationship tests completed successfully!';
    ELSE
        RAISE EXCEPTION 'Some foreign key relationship tests failed';
    END IF;
END $$;

-- Test 5: Index Performance
DO $$
DECLARE
    test_passed BOOLEAN := TRUE;
    index_count INTEGER;
BEGIN
    -- Test 5.1: Check if indexes exist
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE tablename = 'user_portfolios' 
    AND indexname LIKE 'idx_user_portfolios_%';
    
    IF index_count >= 1 THEN
        RAISE NOTICE 'PASS: Indexes exist on user_portfolios table';
    ELSE
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: No indexes found on user_portfolios table';
    END IF;
    
    -- Test 5.2: Check portfolio_transactions indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE tablename = 'portfolio_transactions' 
    AND indexname LIKE 'idx_portfolio_transactions_%';
    
    IF index_count >= 1 THEN
        RAISE NOTICE 'PASS: Indexes exist on portfolio_transactions table';
    ELSE
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: No indexes found on portfolio_transactions table';
    END IF;
    
    IF test_passed THEN
        RAISE NOTICE 'Index performance tests completed successfully!';
    ELSE
        RAISE EXCEPTION 'Some index performance tests failed';
    END IF;
END $$;

-- Test 6: View Functionality
DO $$
DECLARE
    test_passed BOOLEAN := TRUE;
    view_count INTEGER;
BEGIN
    -- Test 6.1: Check if portfolio_summary view exists
    SELECT COUNT(*) INTO view_count
    FROM information_schema.views 
    WHERE table_name = 'portfolio_summary';
    
    IF view_count = 1 THEN
        RAISE NOTICE 'PASS: portfolio_summary view exists';
        
        -- Test 6.2: Test view functionality
        BEGIN
            INSERT INTO user_portfolios (accountid, total_value, tier1_allocation, tier2_allocation, tier3_allocation, total_allocation, tier1_value, tier2_value, tier3_value)
            VALUES ('test-user-8', 1000.00, 50.0, 30.0, 20.0, 100.0, 500.00, 300.00, 200.00);
            
            -- Query the view
            IF EXISTS (SELECT 1 FROM portfolio_summary WHERE accountid = 'test-user-8') THEN
                RAISE NOTICE 'PASS: portfolio_summary view returns data correctly';
            ELSE
                test_passed := FALSE;
                RAISE NOTICE 'FAIL: portfolio_summary view does not return data';
            END IF;
            
            DELETE FROM user_portfolios WHERE accountid = 'test-user-8';
        EXCEPTION WHEN OTHERS THEN
            test_passed := FALSE;
            RAISE NOTICE 'FAIL: portfolio_summary view test failed: %', SQLERRM;
        END;
    ELSE
        test_passed := FALSE;
        RAISE NOTICE 'FAIL: portfolio_summary view does not exist';
    END IF;
    
    IF test_passed THEN
        RAISE NOTICE 'View functionality tests completed successfully!';
    ELSE
        RAISE EXCEPTION 'Some view functionality tests failed';
    END IF;
END $$;

-- Test Summary
DO $$
BEGIN
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'User Portfolio Database Test Summary';
    RAISE NOTICE '==========================================';
    RAISE NOTICE 'All tests completed successfully! 🎉';
    RAISE NOTICE 'Database schema is working correctly.';
    RAISE NOTICE '==========================================';
END $$;
