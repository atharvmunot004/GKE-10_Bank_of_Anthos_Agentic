"""
Unit tests for database module
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime
import asyncpg

from database import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager functionality"""
    
    def setup_method(self):
        """Setup test database manager"""
        self.db_manager = DatabaseManager()
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful database initialization"""
        mock_pool = MagicMock()
        
        with patch('asyncpg.create_pool', new_callable=AsyncMock, return_value=mock_pool):
            await self.db_manager.initialize()
            
            assert self.db_manager.pool == mock_pool
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test database initialization failure"""
        with patch('asyncpg.create_pool', new_callable=AsyncMock, 
                  side_effect=asyncpg.ConnectionDoesNotExistError("Connection failed")):
            
            with pytest.raises(asyncpg.ConnectionDoesNotExistError):
                await self.db_manager.initialize()
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test database connection close"""
        mock_pool = AsyncMock()
        self.db_manager.pool = mock_pool
        
        await self.db_manager.close()
        
        mock_pool.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_is_connected_success(self):
        """Test successful connection check"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=1)
        
        # Use proper async context manager mock
        with patch.object(self.db_manager.pool, 'acquire') as mock_acquire:
            mock_acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await self.db_manager.is_connected()
            
            assert result is True
            mock_conn.fetchval.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_is_connected_no_pool(self):
        """Test connection check with no pool"""
        self.db_manager.pool = None
        
        result = await self.db_manager.is_connected()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_connected_failure(self):
        """Test connection check failure"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=asyncpg.ConnectionDoesNotExistError("Connection failed"))
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        result = await self.db_manager.is_connected()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_count_pending_requests_success(self):
        """Test successful pending requests count"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=15)
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        result = await self.db_manager.count_pending_requests()
        
        assert result == 15
        mock_conn.fetchval.assert_called_once_with(
            "SELECT COUNT(*) FROM investment_withdrawal_queue WHERE status = 'PENDING'"
        )
    
    @pytest.mark.asyncio
    async def test_count_pending_requests_none_result(self):
        """Test pending requests count with None result"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=None)
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        result = await self.db_manager.count_pending_requests()
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_count_pending_requests_failure(self):
        """Test pending requests count failure"""
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(side_effect=asyncpg.PostgresError("Query failed"))
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        with pytest.raises(asyncpg.PostgresError):
            await self.db_manager.count_pending_requests()
    
    @pytest.mark.asyncio
    async def test_fetch_batch_success(self):
        """Test successful batch fetch"""
        mock_rows = [
            {
                'uuid': 'uuid-1',
                'accountid': '12345678901234567890',
                'tier_1': Decimal('1000.00'),
                'tier_2': Decimal('2000.00'),
                'tier_3': Decimal('500.00'),
                'transaction_type': 'INVEST',
                'status': 'PENDING',
                'created_at': datetime.utcnow(),
                'updated_at': None,
                'processed_at': None
            },
            {
                'uuid': 'uuid-2',
                'accountid': '12345678901234567890',
                'tier_1': Decimal('500.00'),
                'tier_2': Decimal('1000.00'),
                'tier_3': Decimal('250.00'),
                'transaction_type': 'WITHDRAW',
                'status': 'PENDING',
                'created_at': datetime.utcnow(),
                'updated_at': None,
                'processed_at': None
            }
        ]
        
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=mock_rows)
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        result = await self.db_manager.fetch_batch(10)
        
        assert len(result) == 2
        assert result[0]['uuid'] == 'uuid-1'
        assert result[0]['tier1'] == Decimal('1000.00')
        assert result[0]['purpose'] == 'INVEST'
        assert result[1]['uuid'] == 'uuid-2'
        assert result[1]['purpose'] == 'WITHDRAW'
    
    @pytest.mark.asyncio
    async def test_fetch_batch_empty(self):
        """Test fetch batch with empty result"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        result = await self.db_manager.fetch_batch(10)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_batch_failure(self):
        """Test fetch batch failure"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=asyncpg.PostgresError("Query failed"))
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        with pytest.raises(asyncpg.PostgresError):
            await self.db_manager.fetch_batch(10)
    
    @pytest.mark.asyncio
    async def test_update_batch_status_success(self):
        """Test successful batch status update"""
        uuids = ['uuid-1', 'uuid-2', 'uuid-3']
        status = 'COMPLETED'
        
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        mock_conn.execute = AsyncMock(return_value="UPDATE 3")
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        result = await self.db_manager.update_batch_status(uuids, status)
        
        assert result is True
        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args[0]
        assert status in call_args
        assert uuids in call_args
    
    @pytest.mark.asyncio
    async def test_update_batch_status_failure(self):
        """Test batch status update failure"""
        uuids = ['uuid-1', 'uuid-2']
        status = 'FAILED'
        
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        mock_conn.execute = AsyncMock(side_effect=asyncpg.PostgresError("Update failed"))
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        with pytest.raises(asyncpg.PostgresError):
            await self.db_manager.update_batch_status(uuids, status)
    
    @pytest.mark.asyncio
    async def test_get_transaction_by_uuid_found(self):
        """Test get transaction by UUID - found"""
        mock_row = {
            'uuid': 'uuid-1',
            'accountid': '12345678901234567890',
            'tier_1': Decimal('1000.00'),
            'tier_2': Decimal('2000.00'),
            'tier_3': Decimal('500.00'),
            'transaction_type': 'INVEST',
            'status': 'PENDING',
            'created_at': datetime.utcnow(),
            'updated_at': None,
            'processed_at': None
        }
        
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        result = await self.db_manager.get_transaction_by_uuid('uuid-1')
        
        assert result is not None
        assert result['uuid'] == 'uuid-1'
        assert result['tier1'] == Decimal('1000.00')
        assert result['purpose'] == 'INVEST'
    
    @pytest.mark.asyncio
    async def test_get_transaction_by_uuid_not_found(self):
        """Test get transaction by UUID - not found"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        result = await self.db_manager.get_transaction_by_uuid('nonexistent-uuid')
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_transaction_by_uuid_failure(self):
        """Test get transaction by UUID failure"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(side_effect=asyncpg.PostgresError("Query failed"))
        
        mock_pool = AsyncMock()
        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire.return_value = mock_context_manager
        
        self.db_manager.pool = mock_pool
        
        with pytest.raises(asyncpg.PostgresError):
            await self.db_manager.get_transaction_by_uuid('uuid-1')
