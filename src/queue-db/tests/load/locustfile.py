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

"""
Load testing for queue-db microservice using Locust.
Tests database performance under various load conditions.
"""

import random
import uuid
from decimal import Decimal
from locust import HttpUser, task, between
import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool


class QueueDatabaseUser(HttpUser):
    """Locust user class for queue database load testing."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize database connection pool."""
        self.connection_pool = SimpleConnectionPool(
            1, 10,
            host='localhost',
            port=5432,
            database='queue-db',
            user='queue-admin',
            password='queue-pwd'
        )
        
        # Sample account IDs for testing
        self.account_ids = [
            '1011226111', '1011226112', '1011226113',
            '1011226114', '1011226115', '1011226116',
            '1011226117', '1011226118', '1011226119',
            '1011226120'
        ]
    
    def on_stop(self):
        """Clean up database connections."""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()
    
    def get_connection(self):
        """Get database connection from pool."""
        return self.connection_pool.getconn()
    
    def return_connection(self, conn):
        """Return connection to pool."""
        self.connection_pool.putconn(conn)
    
    @task(3)
    def create_investment_request(self):
        """Create an investment request."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = """
                INSERT INTO investment_withdrawal_queue 
                (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING queue_id
                """
                
                data = (
                    random.choice(self.account_ids),
                    Decimal(str(round(random.uniform(100, 5000), 2))),
                    Decimal(str(round(random.uniform(200, 10000), 2))),
                    Decimal(str(round(random.uniform(50, 2500), 2))),
                    str(uuid.uuid4()),
                    'INVEST',
                    'PENDING'
                )
                
                cursor.execute(query, data)
                result = cursor.fetchone()
                conn.commit()
                
                # Simulate API response time
                return result['queue_id']
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.return_connection(conn)
    
    @task(2)
    def create_withdrawal_request(self):
        """Create a withdrawal request."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                query = """
                INSERT INTO investment_withdrawal_queue 
                (accountid, tier_1, tier_2, tier_3, uuid, transaction_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING queue_id
                """
                
                data = (
                    random.choice(self.account_ids),
                    Decimal(str(round(random.uniform(50, 2500), 2))),
                    Decimal(str(round(random.uniform(100, 5000), 2))),
                    Decimal(str(round(random.uniform(25, 1250), 2))),
                    str(uuid.uuid4()),
                    'WITHDRAW',
                    'PENDING'
                )
                
                cursor.execute(query, data)
                result = cursor.fetchone()
                conn.commit()
                
                return result['queue_id']
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.return_connection(conn)
    
    @task(2)
    def get_queue_entry(self):
        """Get a queue entry by UUID."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # First, get a random UUID from existing entries
                cursor.execute("""
                    SELECT uuid FROM investment_withdrawal_queue 
                    ORDER BY RANDOM() LIMIT 1
                """)
                result = cursor.fetchone()
                
                if result:
                    uuid = result['uuid']
                    
                    # Now get the full entry
                    cursor.execute("""
                        SELECT * FROM investment_withdrawal_queue 
                        WHERE uuid = %s
                    """, (uuid,))
                    
                    entry = cursor.fetchone()
                    return dict(entry) if entry else None
                
        except Exception as e:
            raise e
        finally:
            self.return_connection(conn)
    
    @task(1)
    def get_account_entries(self):
        """Get all entries for an account."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                account_id = random.choice(self.account_ids)
                
                cursor.execute("""
                    SELECT * FROM investment_withdrawal_queue 
                    WHERE accountid = %s 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """, (account_id,))
                
                entries = cursor.fetchall()
                return [dict(entry) for entry in entries]
                
        except Exception as e:
            raise e
        finally:
            self.return_connection(conn)
    
    @task(1)
    def update_queue_status(self):
        """Update queue entry status."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                # Get a random PENDING entry
                cursor.execute("""
                    SELECT uuid FROM investment_withdrawal_queue 
                    WHERE status = 'PENDING' 
                    ORDER BY RANDOM() LIMIT 1
                """)
                result = cursor.fetchone()
                
                if result:
                    uuid = result['uuid']
                    new_status = random.choice(['PROCESSING', 'CANCELLED'])
                    
                    cursor.execute("""
                        UPDATE investment_withdrawal_queue 
                        SET status = %s 
                        WHERE uuid = %s
                    """, (new_status, uuid))
                    
                    conn.commit()
                    return cursor.rowcount
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            self.return_connection(conn)
    
    @task(1)
    def get_queue_statistics(self):
        """Get queue statistics."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM queue_statistics")
                stats = cursor.fetchall()
                return [dict(stat) for stat in stats]
                
        except Exception as e:
            raise e
        finally:
            self.return_connection(conn)
    
    @task(1)
    def get_account_summary(self):
        """Get account queue summary."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                account_id = random.choice(self.account_ids)
                
                cursor.execute("""
                    SELECT * FROM account_queue_summary 
                    WHERE accountid = %s
                """, (account_id,))
                
                summary = cursor.fetchone()
                return dict(summary) if summary else None
                
        except Exception as e:
            raise e
        finally:
            self.return_connection(conn)


class QueueDatabaseReadUser(HttpUser):
    """Read-only user for testing read performance."""
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """Initialize database connection pool."""
        self.connection_pool = SimpleConnectionPool(
            1, 5,
            host='localhost',
            port=5432,
            database='queue-db',
            user='queue-admin',
            password='queue-pwd'
        )
        
        self.account_ids = [
            '1011226111', '1011226112', '1011226113',
            '1011226114', '1011226115'
        ]
    
    def on_stop(self):
        """Clean up database connections."""
        if hasattr(self, 'connection_pool'):
            self.connection_pool.closeall()
    
    def get_connection(self):
        """Get database connection from pool."""
        return self.connection_pool.getconn()
    
    def return_connection(self, conn):
        """Return connection to pool."""
        self.connection_pool.putconn(conn)
    
    @task(5)
    def get_queue_statistics(self):
        """Get queue statistics."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM queue_statistics")
                stats = cursor.fetchall()
                return [dict(stat) for stat in stats]
                
        except Exception as e:
            raise e
        finally:
            self.return_connection(conn)
    
    @task(3)
    def get_account_summary(self):
        """Get account queue summary."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                account_id = random.choice(self.account_ids)
                
                cursor.execute("""
                    SELECT * FROM account_queue_summary 
                    WHERE accountid = %s
                """, (account_id,))
                
                summary = cursor.fetchone()
                return dict(summary) if summary else None
                
        except Exception as e:
            raise e
        finally:
            self.return_connection(conn)
    
    @task(2)
    def get_recent_entries(self):
        """Get recent queue entries."""
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM investment_withdrawal_queue 
                    ORDER BY created_at DESC 
                    LIMIT 20
                """)
                
                entries = cursor.fetchall()
                return [dict(entry) for entry in entries]
                
        except Exception as e:
            raise e
        finally:
            self.return_connection(conn)
