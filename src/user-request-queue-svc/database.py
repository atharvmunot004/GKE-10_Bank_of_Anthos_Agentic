"""
Database connection and query management for user-request-queue-svc
"""
import asyncio
import asyncpg
from typing import List, Optional
from decimal import Decimal
import structlog
from config import settings

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Database connection and query manager"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.queue_db_host,
                port=settings.queue_db_port,
                database=settings.queue_db_name,
                user=settings.queue_db_user,
                password=settings.queue_db_password,
                min_size=1,
                max_size=settings.connection_pool_size,
                command_timeout=60
            )
            logger.info("Database connection pool initialized", 
                       host=settings.queue_db_host, 
                       port=settings.queue_db_port)
        except Exception as e:
            logger.error("Failed to initialize database connection pool", error=str(e))
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def is_connected(self) -> bool:
        """Check if database is connected"""
        try:
            if not self.pool:
                return False
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True
        except Exception as e:
            logger.error("Database connection check failed", error=str(e))
            return False
    
    async def count_pending_requests(self) -> int:
        """Count pending requests in the queue"""
        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM investment_withdrawal_queue WHERE status = 'PENDING'"
                )
                return count or 0
        except Exception as e:
            logger.error("Failed to count pending requests", error=str(e))
            raise
    
    async def fetch_batch(self, limit: int = 10) -> List[dict]:
        """Fetch a batch of pending transactions"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT uuid, accountid, tier_1, tier_2, tier_3, 
                           transaction_type, status, created_at, updated_at, processed_at
                    FROM investment_withdrawal_queue 
                    WHERE status = 'PENDING' 
                    ORDER BY created_at ASC 
                    LIMIT $1
                    """,
                    limit
                )
                
                transactions = []
                for row in rows:
                    transactions.append({
                        'uuid': row['uuid'],
                        'accountid': row['accountid'],
                        'tier1': row['tier_1'],
                        'tier2': row['tier_2'],
                        'tier3': row['tier_3'],
                        'purpose': row['transaction_type'],
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'processed_at': row['processed_at']
                    })
                
                logger.info("Fetched batch of transactions", count=len(transactions))
                return transactions
        except Exception as e:
            logger.error("Failed to fetch batch", error=str(e))
            raise
    
    async def update_batch_status(self, uuids: List[str], status: str) -> bool:
        """Update status for a batch of transactions"""
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.execute(
                        """
                        UPDATE investment_withdrawal_queue 
                        SET status = $1, updated_at = NOW(), processed_at = NOW()
                        WHERE uuid = ANY($2)
                        """,
                        status,
                        uuids
                    )
                    
                    logger.info("Updated batch status", 
                               status=status, 
                               count=len(uuids),
                               affected_rows=result.split()[-1])
                    return True
        except Exception as e:
            logger.error("Failed to update batch status", 
                        error=str(e), 
                        status=status, 
                        uuids=uuids)
            raise
    
    async def get_transaction_by_uuid(self, uuid: str) -> Optional[dict]:
        """Get a specific transaction by UUID"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT uuid, accountid, tier_1, tier_2, tier_3, 
                           transaction_type, status, created_at, updated_at, processed_at
                    FROM investment_withdrawal_queue 
                    WHERE uuid = $1
                    """,
                    uuid
                )
                
                if row:
                    return {
                        'uuid': row['uuid'],
                        'accountid': row['accountid'],
                        'tier1': row['tier_1'],
                        'tier2': row['tier_2'],
                        'tier3': row['tier_3'],
                        'purpose': row['transaction_type'],
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at'],
                        'processed_at': row['processed_at']
                    }
                return None
        except Exception as e:
            logger.error("Failed to get transaction by UUID", error=str(e), uuid=uuid)
            raise


# Global database manager instance
db_manager = DatabaseManager()
