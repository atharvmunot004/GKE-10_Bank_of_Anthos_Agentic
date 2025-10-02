"""
Integration tests for database operations
"""
import pytest
import asyncio
import asyncpg
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch
import os

from database import DatabaseManager
from models import TransactionType, TransactionStatus


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    """Integration tests for database operations with real database"""
    
    @pytest.fixture(scope="class")
    async def test_db_manager(self):
        """Setup test database manager with test database"""
        # Use test database configuration
        test_db_config = {
            'host': os.getenv('TEST_DB_HOST', 'localhost'),
            'port': int(os.getenv('TEST_DB_PORT', '5432')),
            'database': os.getenv('TEST_DB_NAME', 'test_queue_db'),
            'user': os.getenv('TEST_DB_USER', 'test_user'),
            'password': os.getenv('TEST_DB_PASSWORD', 'test_password')
        }
        
        db_manager = DatabaseManager()
        
        # Override connection settings for test
        with patch.multiple(
            'config.settings',
            queue_db_host=test_db_config['host'],
            queue_db_port=test_db_config['port'],
            queue_db_name=test_db_config['database'],
            queue_db_user=test_db_config['user'],
            queue_db_password=test_db_config['password'],
            connection_pool_size=2
        ):
            try:
                await db_manager.initialize()
                yield db_manager
            finally:
                await db_manager.close()
    
    @pytest.fixture(autouse=True)
    async def setup_test_data(self, test_db_manager):
        """Setup and cleanup test data for each test"""
        # Setup: Create test table and insert test data
        async with test_db_manager.pool.acquire() as conn:
            # Create test table if not exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS investment_withdrawal_queue (
                    queue_id SERIAL PRIMARY KEY,
                    accountid VARCHAR(20) NOT NULL,
                    tier_1 DECIMAL(20, 8) NOT NULL,
                    tier_2 DECIMAL(20, 8) NOT NULL,
                    tier_3 DECIMAL(20, 8) NOT NULL,
                    uuid VARCHAR(36) UNIQUE NOT NULL,
                    transaction_type VARCHAR(20) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    processed_at TIMESTAMP WITH TIME ZONE
                )
            """)
            
            # Insert test data
            await conn.execute("""
                INSERT INTO investment_withdrawal_queue 
                (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                VALUES 
                ($1, $2, $3, $4, $5, $6, $7),
                ($8, $9, $10, $11, $12, $13, $14),
                ($15, $16, $17, $18, $19, $20, $21)
            """, 
                '12345678901234567890', Decimal('1000.00'), Decimal('2000.00'), Decimal('500.00'), 
                'test-uuid-1', 'INVEST', 'PENDING',
                '12345678901234567890', Decimal('500.00'), Decimal('1000.00'), Decimal('250.00'), 
                'test-uuid-2', 'WITHDRAW', 'PENDING',
                '98765432109876543210', Decimal('750.00'), Decimal('1500.00'), Decimal('375.00'), 
                'test-uuid-3', 'INVEST', 'PROCESSING'
            )
        
        yield
        
        # Cleanup: Remove test data
        async with test_db_manager.pool.acquire() as conn:
            await conn.execute("DELETE FROM investment_withdrawal_queue WHERE uuid LIKE 'test-uuid-%'")
    
    @pytest.mark.asyncio
    async def test_database_connection(self, test_db_manager):
        """Test database connection"""
        is_connected = await test_db_manager.is_connected()
        assert is_connected is True
    
    @pytest.mark.asyncio
    async def test_count_pending_requests(self, test_db_manager):
        """Test counting pending requests"""
        count = await test_db_manager.count_pending_requests()
        assert count >= 2  # At least our test data
    
    @pytest.mark.asyncio
    async def test_fetch_batch(self, test_db_manager):
        """Test fetching a batch of transactions"""
        batch = await test_db_manager.fetch_batch(5)
        
        assert isinstance(batch, list)
        assert len(batch) >= 2  # At least our pending test data
        
        # Verify structure of returned data
        for transaction in batch:
            assert 'uuid' in transaction
            assert 'accountid' in transaction
            assert 'tier1' in transaction
            assert 'tier2' in transaction
            assert 'tier3' in transaction
            assert 'purpose' in transaction
            assert 'status' in transaction
            assert transaction['status'] == 'PENDING'
    
    @pytest.mark.asyncio
    async def test_update_batch_status(self, test_db_manager):
        """Test updating batch status"""
        # First, get some pending transactions
        batch = await test_db_manager.fetch_batch(2)
        assert len(batch) >= 1
        
        uuids = [t['uuid'] for t in batch[:1]]  # Take first transaction
        
        # Update status
        result = await test_db_manager.update_batch_status(uuids, 'COMPLETED')
        assert result is True
        
        # Verify the update
        async with test_db_manager.pool.acquire() as conn:
            updated_row = await conn.fetchrow(
                "SELECT status, processed_at FROM investment_withdrawal_queue WHERE uuid = $1",
                uuids[0]
            )
            assert updated_row['status'] == 'COMPLETED'
            assert updated_row['processed_at'] is not None
    
    @pytest.mark.asyncio
    async def test_get_transaction_by_uuid(self, test_db_manager):
        """Test getting transaction by UUID"""
        # Test existing transaction
        transaction = await test_db_manager.get_transaction_by_uuid('test-uuid-1')
        
        assert transaction is not None
        assert transaction['uuid'] == 'test-uuid-1'
        assert transaction['accountid'] == '12345678901234567890'
        assert transaction['tier1'] == Decimal('1000.00')
        assert transaction['purpose'] == 'INVEST'
        
        # Test non-existing transaction
        transaction = await test_db_manager.get_transaction_by_uuid('non-existent-uuid')
        assert transaction is None
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, test_db_manager):
        """Test concurrent database operations"""
        async def count_requests():
            return await test_db_manager.count_pending_requests()
        
        async def fetch_batch():
            return await test_db_manager.fetch_batch(1)
        
        # Run operations concurrently
        results = await asyncio.gather(
            count_requests(),
            fetch_batch(),
            count_requests(),
            fetch_batch()
        )
        
        # Verify all operations completed successfully
        assert isinstance(results[0], int)  # count result
        assert isinstance(results[1], list)  # batch result
        assert isinstance(results[2], int)  # count result
        assert isinstance(results[3], list)  # batch result
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, test_db_manager):
        """Test transaction rollback on error"""
        async with test_db_manager.pool.acquire() as conn:
            try:
                async with conn.transaction():
                    # Insert a valid record
                    await conn.execute("""
                        INSERT INTO investment_withdrawal_queue 
                        (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, '12345678901234567890', Decimal('100.00'), Decimal('200.00'), 
                         Decimal('50.00'), 'rollback-test-1', 'INVEST', 'PENDING')
                    
                    # Try to insert a duplicate UUID (should fail)
                    await conn.execute("""
                        INSERT INTO investment_withdrawal_queue 
                        (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, '12345678901234567890', Decimal('100.00'), Decimal('200.00'), 
                         Decimal('50.00'), 'rollback-test-1', 'INVEST', 'PENDING')
                    
            except asyncpg.UniqueViolationError:
                # Expected error due to duplicate UUID
                pass
            
            # Verify that the transaction was rolled back
            result = await conn.fetchrow(
                "SELECT * FROM investment_withdrawal_queue WHERE uuid = $1",
                'rollback-test-1'
            )
            assert result is None
    
    @pytest.mark.asyncio
    async def test_large_batch_operations(self, test_db_manager):
        """Test operations with large batches"""
        # Insert a larger number of test records
        async with test_db_manager.pool.acquire() as conn:
            # Insert 50 test records
            for i in range(50):
                await conn.execute("""
                    INSERT INTO investment_withdrawal_queue 
                    (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, f'account-{i}', Decimal(f'{i * 10}.00'), Decimal(f'{i * 20}.00'), 
                     Decimal(f'{i * 5}.00'), f'large-batch-{i}', 
                     'INVEST' if i % 2 == 0 else 'WITHDRAW', 'PENDING')
        
        try:
            # Test fetching large batch
            batch = await test_db_manager.fetch_batch(30)
            assert len(batch) >= 30
            
            # Test updating large batch
            uuids = [t['uuid'] for t in batch if t['uuid'].startswith('large-batch-')][:20]
            if uuids:
                result = await test_db_manager.update_batch_status(uuids, 'COMPLETED')
                assert result is True
                
                # Verify updates
                async with test_db_manager.pool.acquire() as conn:
                    completed_count = await conn.fetchval(
                        "SELECT COUNT(*) FROM investment_withdrawal_queue WHERE uuid = ANY($1) AND status = 'COMPLETED'",
                        uuids
                    )
                    assert completed_count == len(uuids)
        
        finally:
            # Cleanup
            async with test_db_manager.pool.acquire() as conn:
                await conn.execute("DELETE FROM investment_withdrawal_queue WHERE uuid LIKE 'large-batch-%'")
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self, test_db_manager):
        """Test behavior when connection pool is exhausted"""
        # Create more concurrent operations than pool size
        async def long_running_operation():
            async with test_db_manager.pool.acquire() as conn:
                await asyncio.sleep(0.1)  # Simulate work
                return await conn.fetchval("SELECT COUNT(*) FROM investment_withdrawal_queue")
        
        # Run more operations than pool size (pool size is 2 in test config)
        tasks = [long_running_operation() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All operations should complete successfully
        assert len(results) == 5
        for result in results:
            assert isinstance(result, int)
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, test_db_manager):
        """Test database error handling"""
        # Test with invalid query
        with pytest.raises(asyncpg.PostgresError):
            async with test_db_manager.pool.acquire() as conn:
                await conn.execute("SELECT * FROM non_existent_table")
        
        # Test with invalid data type
        with pytest.raises(asyncpg.PostgresError):
            async with test_db_manager.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO investment_withdrawal_queue 
                    (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, '12345678901234567890', 'invalid_decimal', Decimal('200.00'), 
                     Decimal('50.00'), 'error-test-1', 'INVEST', 'PENDING')


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.slow
class TestDatabasePerformance:
    """Performance tests for database operations"""
    
    @pytest.mark.asyncio
    async def test_batch_fetch_performance(self, test_db_manager):
        """Test performance of batch fetch operations"""
        import time
        
        # Insert performance test data
        async with test_db_manager.pool.acquire() as conn:
            for i in range(1000):
                await conn.execute("""
                    INSERT INTO investment_withdrawal_queue 
                    (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, f'perf-account-{i % 10}', Decimal(f'{i}.00'), Decimal(f'{i * 2}.00'), 
                     Decimal(f'{i / 2}.00'), f'perf-uuid-{i}', 
                     'INVEST' if i % 2 == 0 else 'WITHDRAW', 'PENDING')
        
        try:
            # Measure fetch performance
            start_time = time.time()
            batch = await test_db_manager.fetch_batch(100)
            end_time = time.time()
            
            fetch_time = end_time - start_time
            
            assert len(batch) == 100
            assert fetch_time < 1.0  # Should complete within 1 second
            
        finally:
            # Cleanup
            async with test_db_manager.pool.acquire() as conn:
                await conn.execute("DELETE FROM investment_withdrawal_queue WHERE uuid LIKE 'perf-uuid-%'")
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_updates_performance(self, test_db_manager):
        """Test performance of concurrent batch updates"""
        import time
        
        # Insert test data
        async with test_db_manager.pool.acquire() as conn:
            for i in range(100):
                await conn.execute("""
                    INSERT INTO investment_withdrawal_queue 
                    (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, f'concurrent-account-{i % 5}', Decimal(f'{i}.00'), Decimal(f'{i * 2}.00'), 
                     Decimal(f'{i / 2}.00'), f'concurrent-uuid-{i}', 
                     'INVEST' if i % 2 == 0 else 'WITHDRAW', 'PENDING')
        
        try:
            # Prepare batches for concurrent updates
            batch1_uuids = [f'concurrent-uuid-{i}' for i in range(0, 25)]
            batch2_uuids = [f'concurrent-uuid-{i}' for i in range(25, 50)]
            batch3_uuids = [f'concurrent-uuid-{i}' for i in range(50, 75)]
            batch4_uuids = [f'concurrent-uuid-{i}' for i in range(75, 100)]
            
            # Measure concurrent update performance
            start_time = time.time()
            
            await asyncio.gather(
                test_db_manager.update_batch_status(batch1_uuids, 'COMPLETED'),
                test_db_manager.update_batch_status(batch2_uuids, 'FAILED'),
                test_db_manager.update_batch_status(batch3_uuids, 'COMPLETED'),
                test_db_manager.update_batch_status(batch4_uuids, 'FAILED')
            )
            
            end_time = time.time()
            update_time = end_time - start_time
            
            assert update_time < 2.0  # Should complete within 2 seconds
            
            # Verify all updates completed
            async with test_db_manager.pool.acquire() as conn:
                completed_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM investment_withdrawal_queue WHERE uuid LIKE 'concurrent-uuid-%' AND status IN ('COMPLETED', 'FAILED')"
                )
                assert completed_count == 100
                
        finally:
            # Cleanup
            async with test_db_manager.pool.acquire() as conn:
                await conn.execute("DELETE FROM investment_withdrawal_queue WHERE uuid LIKE 'concurrent-uuid-%'")
