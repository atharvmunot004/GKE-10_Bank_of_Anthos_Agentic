# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
import requests
from typing import Dict, List, Optional, Tuple
import uuid
from datetime import datetime, timedelta
import threading
import time
import signal
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration from environment variables
QUEUE_DB_URI = os.getenv('QUEUE_DB_URI', 'postgresql://queue-admin:queue-pwd@queue-db:5432/queue-db')
USER_PORTFOLIO_DB_URI = os.getenv('USER_PORTFOLIO_DB_URI', 'postgresql://portfolio-admin:portfolio-pwd@user-portfolio-db:5432/user-portfolio-db')
PORT = int(os.getenv('PORT', 8080))
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', 30))  # seconds
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 100))

class ConsistencyManager:
    """Service for ensuring UUID consistency between queue-db and portfolio-transaction table."""
    
    def __init__(self):
        self.queue_db_uri = QUEUE_DB_URI
        self.portfolio_db_uri = USER_PORTFOLIO_DB_URI
        self.sync_interval = SYNC_INTERVAL
        self.batch_size = BATCH_SIZE
        self.running = True
        self.sync_thread = None
        
    def get_queue_db_connection(self):
        """Get database connection to queue-db."""
        try:
            conn = psycopg2.connect(self.queue_db_uri)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to queue-db: {e}")
            raise
    
    def get_portfolio_db_connection(self):
        """Get database connection to user-portfolio-db."""
        try:
            conn = psycopg2.connect(self.portfolio_db_uri)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to user-portfolio-db: {e}")
            raise
    
    def get_pending_queue_entries(self) -> List[Dict]:
        """Get pending queue entries that need status updates."""
        try:
            with self.get_queue_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Get entries from both investment and withdrawal queues
                    cursor.execute("""
                        SELECT 
                            'investment' as queue_type,
                            queue_id,
                            account_number,
                            tier_1,
                            tier_2,
                            tier_3,
                            uuid,
                            status,
                            created_at,
                            updated_at,
                            processed_at
                        FROM investment_queue 
                        WHERE status IN ('PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')
                        AND processed_at IS NOT NULL
                        
                        UNION ALL
                        
                        SELECT 
                            'withdrawal' as queue_type,
                            queue_id,
                            account_number,
                            tier_1,
                            tier_2,
                            tier_3,
                            uuid,
                            status,
                            created_at,
                            updated_at,
                            processed_at
                        FROM withdrawal_queue 
                        WHERE status IN ('PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')
                        AND processed_at IS NOT NULL
                        
                        ORDER BY processed_at DESC
                        LIMIT %s
                    """, (self.batch_size,))
                    
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get pending queue entries: {e}")
            return []
    
    def get_user_portfolio_id(self, account_number: str) -> Optional[str]:
        """Get the portfolio ID for a given account number."""
        try:
            with self.get_portfolio_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id FROM user_portfolios 
                        WHERE user_id = %s
                    """, (account_number,))
                    result = cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get user portfolio ID: {e}")
            return None
    
    def find_portfolio_transaction_by_uuid(self, uuid: str) -> Optional[Dict]:
        """Find a portfolio transaction by UUID (stored in a custom way)."""
        try:
            with self.get_portfolio_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Since portfolio_transactions doesn't have uuid field, we'll use a different approach
                    # We'll look for transactions that match the queue entry characteristics
                    cursor.execute("""
                        SELECT pt.*, up.user_id
                        FROM portfolio_transactions pt
                        JOIN user_portfolios up ON pt.portfolio_id = up.id
                        WHERE pt.created_at >= NOW() - INTERVAL '24 hours'
                        ORDER BY pt.created_at DESC
                        LIMIT 100
                    """)
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to find portfolio transaction by UUID: {e}")
            return None
    
    def update_or_create_portfolio_transaction(self, queue_entry: Dict) -> bool:
        """Update existing portfolio transaction or create new one based on queue entry."""
        try:
            portfolio_id = self.get_user_portfolio_id(queue_entry['account_number'])
            if not portfolio_id:
                logger.warning(f"No portfolio found for account {queue_entry['account_number']}")
                return False
            
            with self.get_portfolio_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Determine transaction type and amounts
                    if queue_entry['queue_type'] == 'investment':
                        transaction_type = 'DEPOSIT'
                        total_amount = float(queue_entry['tier_1']) + float(queue_entry['tier_2']) + float(queue_entry['tier_3'])
                        tier1_change = float(queue_entry['tier_1'])
                        tier2_change = float(queue_entry['tier_2'])
                        tier3_change = float(queue_entry['tier_3'])
                    else:  # withdrawal
                        transaction_type = 'WITHDRAWAL'
                        total_amount = -(float(queue_entry['tier_1']) + float(queue_entry['tier_2']) + float(queue_entry['tier_3']))
                        tier1_change = -float(queue_entry['tier_1'])
                        tier2_change = -float(queue_entry['tier_2'])
                        tier3_change = -float(queue_entry['tier_3'])
                    
                    # Map queue status to portfolio transaction status
                    status_mapping = {
                        'PROCESSING': 'PENDING',
                        'COMPLETED': 'COMPLETED',
                        'FAILED': 'FAILED',
                        'CANCELLED': 'CANCELLED'
                    }
                    portfolio_status = status_mapping.get(queue_entry['status'], 'PENDING')
                    
                    # Check if a similar transaction already exists (within last hour)
                    cursor.execute("""
                        SELECT id FROM portfolio_transactions 
                        WHERE portfolio_id = %s 
                        AND transaction_type = %s 
                        AND total_amount = %s
                        AND created_at >= NOW() - INTERVAL '1 hour'
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (portfolio_id, transaction_type, total_amount))
                    
                    existing_transaction = cursor.fetchone()
                    
                    if existing_transaction:
                        # Update existing transaction
                        cursor.execute("""
                            UPDATE portfolio_transactions 
                            SET status = %s, updated_at = NOW()
                            WHERE id = %s
                        """, (portfolio_status, existing_transaction[0]))
                        
                        logger.info(f"Updated portfolio transaction {existing_transaction[0]} for UUID: {queue_entry['uuid']}")
                    else:
                        # Create new transaction
                        cursor.execute("""
                            INSERT INTO portfolio_transactions (
                                portfolio_id,
                                transaction_type,
                                tier1_change,
                                tier2_change,
                                tier3_change,
                                total_amount,
                                status,
                                created_at,
                                updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                        """, (
                            portfolio_id,
                            transaction_type,
                            tier1_change,
                            tier2_change,
                            tier3_change,
                            total_amount,
                            portfolio_status,
                            queue_entry['created_at'],
                            queue_entry['updated_at']
                        ))
                        
                        logger.info(f"Created portfolio transaction for UUID: {queue_entry['uuid']}")
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update/create portfolio transaction: {e}")
            return False
    
    def update_user_portfolio_values(self, queue_entry: Dict) -> bool:
        """Update user portfolio tier values based on queue entry."""
        try:
            portfolio_id = self.get_user_portfolio_id(queue_entry['account_number'])
            if not portfolio_id:
                logger.warning(f"No portfolio found for account {queue_entry['account_number']}")
                return False
            
            with self.get_portfolio_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Get current portfolio values
                    cursor.execute("""
                        SELECT tier1_value, tier2_value, tier3_value, total_value
                        FROM user_portfolios 
                        WHERE id = %s
                    """, (portfolio_id,))
                    
                    current_values = cursor.fetchone()
                    if not current_values:
                        logger.warning(f"No portfolio values found for {portfolio_id}")
                        return False
                    
                    current_tier1, current_tier2, current_tier3, current_total = current_values
                    
                    # Calculate new values based on queue entry
                    if queue_entry['queue_type'] == 'investment':
                        # Add to portfolio
                        new_tier1 = current_tier1 + float(queue_entry['tier_1'])
                        new_tier2 = current_tier2 + float(queue_entry['tier_2'])
                        new_tier3 = current_tier3 + float(queue_entry['tier_3'])
                    else:  # withdrawal
                        # Subtract from portfolio
                        new_tier1 = current_tier1 - float(queue_entry['tier_1'])
                        new_tier2 = current_tier2 - float(queue_entry['tier_2'])
                        new_tier3 = current_tier3 - float(queue_entry['tier_3'])
                    
                    new_total = new_tier1 + new_tier2 + new_tier3
                    
                    # Only update if status is COMPLETED
                    if queue_entry['status'] == 'COMPLETED':
                        cursor.execute("""
                            UPDATE user_portfolios 
                            SET 
                                tier1_value = %s,
                                tier2_value = %s,
                                tier3_value = %s,
                                total_value = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (new_tier1, new_tier2, new_tier3, new_total, portfolio_id))
                        
                        logger.info(f"Updated portfolio values for {portfolio_id}")
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to update user portfolio values: {e}")
            return False
    
    def sync_queue_to_portfolio(self) -> Dict[str, int]:
        """Sync queue entries to portfolio transactions and update portfolio values."""
        stats = {
            'processed': 0,
            'transactions_updated': 0,
            'transactions_created': 0,
            'portfolios_updated': 0,
            'errors': 0
        }
        
        try:
            # Get pending queue entries
            queue_entries = self.get_pending_queue_entries()
            logger.info(f"Found {len(queue_entries)} queue entries to process")
            
            for entry in queue_entries:
                try:
                    stats['processed'] += 1
                    
                    # Update or create portfolio transaction
                    if self.update_or_create_portfolio_transaction(entry):
                        stats['transactions_updated'] += 1
                    else:
                        stats['errors'] += 1
                        continue
                    
                    # Update portfolio values if completed
                    if entry['status'] == 'COMPLETED':
                        if self.update_user_portfolio_values(entry):
                            stats['portfolios_updated'] += 1
                        else:
                            stats['errors'] += 1
                            
                except Exception as e:
                    logger.error(f"Error processing queue entry {entry['uuid']}: {e}")
                    stats['errors'] += 1
            
            logger.info(f"Sync completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to sync queue to portfolio: {e}")
            stats['errors'] += 1
            return stats
    
    def start_sync_thread(self):
        """Start the background sync thread."""
        if self.sync_thread and self.sync_thread.is_alive():
            logger.warning("Sync thread is already running")
            return
        
        self.running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("Started consistency sync thread")
    
    def stop_sync_thread(self):
        """Stop the background sync thread."""
        self.running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        logger.info("Stopped consistency sync thread")
    
    def _sync_loop(self):
        """Background sync loop."""
        while self.running:
            try:
                logger.info("Starting consistency sync cycle")
                stats = self.sync_queue_to_portfolio()
                logger.info(f"Sync cycle completed: {stats}")
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
            
            # Wait for next sync interval
            for _ in range(self.sync_interval):
                if not self.running:
                    break
                time.sleep(1)

# Global consistency manager instance
consistency_manager = ConsistencyManager()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Test database connections
        consistency_manager.get_queue_db_connection().close()
        consistency_manager.get_portfolio_db_connection().close()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'sync_interval': consistency_manager.sync_interval,
            'sync_running': consistency_manager.sync_thread.is_alive() if consistency_manager.sync_thread else False
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check endpoint."""
    try:
        # Test database connections
        consistency_manager.get_queue_db_connection().close()
        consistency_manager.get_portfolio_db_connection().close()
        
        return jsonify({
            'status': 'ready',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503

@app.route('/api/v1/sync', methods=['POST'])
def manual_sync():
    """Manually trigger a sync operation."""
    try:
        stats = consistency_manager.sync_queue_to_portfolio()
        return jsonify({
            'status': 'success',
            'message': 'Sync completed',
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/v1/stats', methods=['GET'])
def get_stats():
    """Get consistency manager statistics."""
    try:
        # Get queue statistics
        with consistency_manager.get_queue_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        'investment' as queue_type,
                        COUNT(*) as total_count,
                        COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending_count,
                        COUNT(CASE WHEN status = 'PROCESSING' THEN 1 END) as processing_count,
                        COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_count,
                        COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_count
                    FROM investment_queue
                    
                    UNION ALL
                    
                    SELECT 
                        'withdrawal' as queue_type,
                        COUNT(*) as total_count,
                        COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending_count,
                        COUNT(CASE WHEN status = 'PROCESSING' THEN 1 END) as processing_count,
                        COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_count,
                        COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_count
                    FROM withdrawal_queue
                """)
                queue_stats = cursor.fetchall()
        
        # Get portfolio transaction statistics
        with consistency_manager.get_portfolio_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_count,
                        COUNT(CASE WHEN transaction_type = 'DEPOSIT' THEN 1 END) as deposit_count,
                        COUNT(CASE WHEN transaction_type = 'WITHDRAWAL' THEN 1 END) as withdrawal_count,
                        COUNT(CASE WHEN status = 'PENDING' THEN 1 END) as pending_count,
                        COUNT(CASE WHEN status = 'COMPLETED' THEN 1 END) as completed_count,
                        COUNT(CASE WHEN status = 'FAILED' THEN 1 END) as failed_count
                    FROM portfolio_transactions
                """)
                portfolio_stats = cursor.fetchone()
        
        return jsonify({
            'queue_stats': queue_stats,
            'portfolio_stats': portfolio_stats,
            'sync_running': consistency_manager.sync_thread.is_alive() if consistency_manager.sync_thread else False,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    consistency_manager.stop_sync_thread()
    sys.exit(0)

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the sync thread
    consistency_manager.start_sync_thread()
    
    try:
        logger.info(f"Starting Consistency Manager Service on port {PORT}")
        app.run(host='0.0.0.0', port=PORT, debug=False)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        consistency_manager.stop_sync_thread()
