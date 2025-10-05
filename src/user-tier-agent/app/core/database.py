"""
Database connection classes for user-tier-agent
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Float, DateTime, Integer
from sqlalchemy.exc import SQLAlchemyError
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class LedgerDb:
    """Database connection for ledger-db"""
    
    def __init__(self):
        self.engine = None
        self.logger = logger
        self.metadata = MetaData()
        self.transactions_table = None
    
    def _ensure_engine(self):
        """Ensure engine is created (lazy initialization)"""
        if self.engine is None:
            self.engine = create_engine(settings.LEDGER_DB_URI)
            # Define transactions table structure
            self.transactions_table = Table(
                'transactions',
                self.metadata,
                Column('transaction_id', String, primary_key=True),
                Column('from_acct', String),
                Column('to_acct', String),
                Column('from_route', String),
                Column('to_route', String),
                Column('amount', Float),
                Column('timestamp', DateTime)
            )
    
    def get_transactions(self, accountid: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get transaction history for an account"""
        try:
            self._ensure_engine()
            query = text("""
                SELECT transaction_id, from_acct, to_acct, from_route, to_route, amount, timestamp
                FROM transactions 
                WHERE from_acct = :accountid OR to_acct = :accountid
                ORDER BY timestamp DESC
                LIMIT :limit
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {"accountid": accountid, "limit": limit})
                transactions = []
                for row in result:
                    transactions.append({
                        "transaction_id": row[0],
                        "from_acct": row[1],
                        "to_acct": row[2],
                        "from_route": row[3],
                        "to_route": row[4],
                        "amount": float(row[5]) if row[5] else 0.0,
                        "timestamp": row[6].isoformat() if row[6] else ""
                    })
                
                self.logger.info("Retrieved transactions", count=len(transactions), accountid=accountid)
                return transactions
                
        except SQLAlchemyError as e:
            self.logger.error("Database error getting transactions", error=str(e), accountid=accountid)
            return []


class QueueDb:
    """Database connection for queue-db"""
    
    def __init__(self):
        self.engine = None
        self.logger = logger
        self.metadata = MetaData()
        self.allocations_table = None
    
    def _ensure_engine(self):
        """Ensure engine is created (lazy initialization)"""
        if self.engine is None:
            self.engine = create_engine(settings.QUEUE_DB_URI)
            # Define allocations table structure
            self.allocations_table = Table(
                'allocations',
                self.metadata,
                Column('id', Integer, primary_key=True),
                Column('uuid', String),
                Column('accountid', String),
                Column('tier1', Float),
                Column('tier2', Float),
                Column('tier3', Float),
                Column('purpose', String),
                Column('created_at', DateTime)
            )
    
    def publish_allocation(self, uuid: str, accountid: str, tier1: float, tier2: float, tier3: float, purpose: str) -> Dict[str, Any]:
        """Publish allocation to queue database"""
        try:
            self._ensure_engine()
            query = text("""
                INSERT INTO allocations (uuid, accountid, tier1, tier2, tier3, purpose, created_at)
                VALUES (:uuid, :accountid, :tier1, :tier2, :tier3, :purpose, NOW())
                RETURNING id
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {
                    "uuid": uuid,
                    "accountid": accountid,
                    "tier1": tier1,
                    "tier2": tier2,
                    "tier3": tier3,
                    "purpose": purpose
                })
                conn.commit()
                
                allocation_id = result.fetchone()[0]
                
                self.logger.info("Allocation published to queue", uuid=uuid, allocation_id=allocation_id)
                return {"success": True, "allocation_id": allocation_id, "uuid": uuid}
                
        except SQLAlchemyError as e:
            self.logger.error("Database error publishing allocation", error=str(e), uuid=uuid)
            return {"success": False, "error": str(e)}


class PortfolioDb:
    """Database connection for user-portfolio-db"""
    
    def __init__(self):
        self.engine = None
        self.logger = logger
        self.metadata = MetaData()
        self.portfolio_transactions_table = None
    
    def _ensure_engine(self):
        """Ensure engine is created (lazy initialization)"""
        if self.engine is None:
            self.engine = create_engine(settings.PORTFOLIO_DB_URI)
            # Define portfolio transactions table structure
            self.portfolio_transactions_table = Table(
                'portfolio_transactions',
                self.metadata,
                Column('id', Integer, primary_key=True),
                Column('uuid', String),
                Column('accountid', String),
                Column('tier1', Float),
                Column('tier2', Float),
                Column('tier3', Float),
                Column('purpose', String),
                Column('table_name', String),
                Column('created_at', DateTime)
            )
    
    def add_transaction(self, uuid: str, accountid: str, tier1: float, tier2: float, tier3: float, purpose: str, table: str = "portfolio-transactions-tb") -> Dict[str, Any]:
        """Add transaction to portfolio database"""
        try:
            self._ensure_engine()
            query = text("""
                INSERT INTO portfolio_transactions (uuid, accountid, tier1, tier2, tier3, purpose, table_name, created_at)
                VALUES (:uuid, :accountid, :tier1, :tier2, :tier3, :purpose, :table_name, NOW())
                RETURNING id
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {
                    "uuid": uuid,
                    "accountid": accountid,
                    "tier1": tier1,
                    "tier2": tier2,
                    "tier3": tier3,
                    "purpose": purpose,
                    "table_name": table
                })
                conn.commit()
                
                transaction_id = result.fetchone()[0]
                
                self.logger.info("Transaction added to portfolio DB", uuid=uuid, transaction_id=transaction_id)
                return {"success": True, "transaction_id": transaction_id, "uuid": uuid}
                
        except SQLAlchemyError as e:
            self.logger.error("Database error adding portfolio transaction", error=str(e), uuid=uuid)
            return {"success": False, "error": str(e)}


# Global database instances (lazy-loaded)
_ledger_db = None
_queue_db = None
_portfolio_db = None

def get_ledger_db():
    """Get ledger database instance (lazy-loaded)"""
    global _ledger_db
    if _ledger_db is None:
        _ledger_db = LedgerDb()
    return _ledger_db

def get_queue_db():
    """Get queue database instance (lazy-loaded)"""
    global _queue_db
    if _queue_db is None:
        _queue_db = QueueDb()
    return _queue_db

def get_portfolio_db():
    """Get portfolio database instance (lazy-loaded)"""
    global _portfolio_db
    if _portfolio_db is None:
        _portfolio_db = PortfolioDb()
    return _portfolio_db

# Global database instances (lazy-loaded)
ledger_db = None
queue_db = None
portfolio_db = None

def get_ledger_db_instance():
    """Get or create global ledger database instance"""
    global ledger_db
    if ledger_db is None:
        ledger_db = get_ledger_db()
    return ledger_db

def get_queue_db_instance():
    """Get or create global queue database instance"""
    global queue_db
    if queue_db is None:
        queue_db = get_queue_db()
    return queue_db

def get_portfolio_db_instance():
    """Get or create global portfolio database instance"""
    global portfolio_db
    if portfolio_db is None:
        portfolio_db = get_portfolio_db()
    return portfolio_db
