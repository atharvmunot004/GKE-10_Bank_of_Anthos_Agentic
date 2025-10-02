import psycopg2
import psycopg2.extras

def test_database_connection():
    """Test basic database connection and table existence."""
    try:
        # Connect to database
        conn = psycopg2.connect("postgresql://queue-admin:queue-pwd@localhost:5432/queue-db")
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Test 1: Check if we can connect
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchone()
        assert result['test'] == 1
        print("✅ Test 1 PASSED: Database connection works")
        
        # Test 2: Check if table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'investment_withdrawal_queue'
        """)
        result = cursor.fetchone()
        if result:
            print("✅ Test 2 PASSED: investment_withdrawal_queue table exists")
        else:
            print("❌ Test 2 FAILED: investment_withdrawal_queue table does not exist")
        
        # Test 3: Check table structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'investment_withdrawal_queue'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        expected_columns = ['queue_id', 'accountid', 'tier_1', 'tier_2', 'tier_3', 'uuid', 'transaction_type', 'status', 'created_at', 'updated_at', 'processed_at']
        
        actual_columns = [col['column_name'] for col in columns]
        if all(col in actual_columns for col in expected_columns):
            print("✅ Test 3 PASSED: All expected columns exist")
        else:
            print(f"❌ Test 3 FAILED: Missing columns. Expected: {expected_columns}, Got: {actual_columns}")
        
        # Test 4: Test basic insert
        cursor.execute("""
            INSERT INTO investment_withdrawal_queue 
            (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING queue_id
        """, ('TEST123', 100.50, 200.75, 50.25, 'test-uuid-12345', 'INVEST', 'PENDING'))
        
        result = cursor.fetchone()
        if result and result['queue_id']:
            print("✅ Test 4 PASSED: Can insert data into table")
            
            # Clean up test data
            cursor.execute("DELETE FROM investment_withdrawal_queue WHERE uuid = %s", ('test-uuid-12345',))
            conn.commit()
            print("✅ Test cleanup completed")
        else:
            print("❌ Test 4 FAILED: Cannot insert data into table")
        
        cursor.close()
        conn.close()
        print("\n🎉 All basic tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    test_database_connection()
