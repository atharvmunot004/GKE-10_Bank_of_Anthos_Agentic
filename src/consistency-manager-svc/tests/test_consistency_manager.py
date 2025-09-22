#!/usr/bin/env python3
"""
Unit tests for consistency-manager-svc
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add the parent directory to the path to import the main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from consistency_manager import ConsistencyManager, app

class TestConsistencyManager(unittest.TestCase):
    """Test cases for ConsistencyManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = ConsistencyManager()
        self.manager.queue_db_uri = "postgresql://test:test@localhost:5432/test_queue"
        self.manager.portfolio_db_uri = "postgresql://test:test@localhost:5432/test_portfolio"
    
    def test_initialization(self):
        """Test ConsistencyManager initialization."""
        self.assertEqual(self.manager.queue_db_uri, "postgresql://test:test@localhost:5432/test_queue")
        self.assertEqual(self.manager.portfolio_db_uri, "postgresql://test:test@localhost:5432/test_portfolio")
        self.assertEqual(self.manager.sync_interval, 30)
        self.assertEqual(self.manager.batch_size, 100)
        self.assertTrue(self.manager.running)
    
    @patch('consistency_manager.psycopg2.connect')
    def test_get_queue_db_connection(self, mock_connect):
        """Test queue database connection."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        result = self.manager.get_queue_db_connection()
        
        mock_connect.assert_called_once_with(self.manager.queue_db_uri)
        self.assertEqual(result, mock_conn)
    
    @patch('consistency_manager.psycopg2.connect')
    def test_get_portfolio_db_connection(self, mock_connect):
        """Test portfolio database connection."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        result = self.manager.get_portfolio_db_connection()
        
        mock_connect.assert_called_once_with(self.manager.portfolio_db_uri)
        self.assertEqual(result, mock_conn)
    
    @patch('consistency_manager.psycopg2.connect')
    def test_get_pending_queue_entries(self, mock_connect):
        """Test getting pending queue entries."""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock query results
        mock_entries = [
            {
                'queue_type': 'investment',
                'queue_id': 1,
                'account_number': '1234567890',
                'tier_1': 100.0,
                'tier_2': 200.0,
                'tier_3': 300.0,
                'uuid': 'test-uuid-1',
                'status': 'COMPLETED',
                'created_at': '2024-01-01 10:00:00',
                'updated_at': '2024-01-01 10:05:00',
                'processed_at': '2024-01-01 10:05:00'
            }
        ]
        mock_cursor.fetchall.return_value = mock_entries
        
        result = self.manager.get_pending_queue_entries()
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['uuid'], 'test-uuid-1')
        self.assertEqual(result[0]['queue_type'], 'investment')
    
    @patch('consistency_manager.psycopg2.connect')
    def test_get_user_portfolio_id(self, mock_connect):
        """Test getting user portfolio ID."""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test case 1: Portfolio exists
        mock_cursor.fetchone.return_value = ('portfolio-id-123',)
        result = self.manager.get_user_portfolio_id('1234567890')
        self.assertEqual(result, 'portfolio-id-123')
        
        # Test case 2: Portfolio doesn't exist
        mock_cursor.fetchone.return_value = None
        result = self.manager.get_user_portfolio_id('1234567890')
        self.assertIsNone(result)
    
    @patch('consistency_manager.psycopg2.connect')
    def test_find_portfolio_transaction_by_uuid(self, mock_connect):
        """Test finding portfolio transaction by UUID."""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Mock query results
        mock_transactions = [
            {
                'id': 'trans-1',
                'portfolio_id': 'portfolio-1',
                'transaction_type': 'DEPOSIT',
                'total_amount': 1000.0,
                'user_id': '1234567890'
            }
        ]
        mock_cursor.fetchall.return_value = mock_transactions
        
        result = self.manager.find_portfolio_transaction_by_uuid('test-uuid-1')
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'trans-1')
    
    @patch('consistency_manager.psycopg2.connect')
    def test_update_or_create_portfolio_transaction(self, mock_connect):
        """Test updating or creating portfolio transaction."""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test data
        queue_entry = {
            'queue_type': 'investment',
            'uuid': 'test-uuid-1',
            'account_number': '1234567890',
            'tier_1': 100.0,
            'tier_2': 200.0,
            'tier_3': 300.0,
            'status': 'COMPLETED',
            'created_at': '2024-01-01 10:00:00',
            'updated_at': '2024-01-01 10:05:00',
            'processed_at': '2024-01-01 10:05:00'
        }
        
        # Mock get_user_portfolio_id
        with patch.object(self.manager, 'get_user_portfolio_id', return_value='portfolio-123'):
            # Test case 1: No existing transaction (create new)
            mock_cursor.fetchone.return_value = None
            result = self.manager.update_or_create_portfolio_transaction(queue_entry)
            self.assertTrue(result)
            
            # Test case 2: Existing transaction (update)
            mock_cursor.fetchone.return_value = ('trans-123',)
            result = self.manager.update_or_create_portfolio_transaction(queue_entry)
            self.assertTrue(result)
    
    @patch('consistency_manager.psycopg2.connect')
    def test_update_user_portfolio_values(self, mock_connect):
        """Test updating user portfolio values."""
        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Test data
        queue_entry = {
            'queue_type': 'investment',
            'account_number': '1234567890',
            'tier_1': 100.0,
            'tier_2': 200.0,
            'tier_3': 300.0,
            'status': 'COMPLETED'
        }
        
        # Mock current portfolio values
        mock_cursor.fetchone.return_value = (1000.0, 2000.0, 3000.0, 6000.0)
        
        # Mock get_user_portfolio_id
        with patch.object(self.manager, 'get_user_portfolio_id', return_value='portfolio-123'):
            result = self.manager.update_user_portfolio_values(queue_entry)
            self.assertTrue(result)
            mock_conn.commit.assert_called_once()

class TestConsistencyManagerAPI(unittest.TestCase):
    """Test cases for API endpoints."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    @patch('consistency_manager.consistency_manager.get_queue_db_connection')
    @patch('consistency_manager.consistency_manager.get_portfolio_db_connection')
    def test_health_check(self, mock_portfolio_conn, mock_queue_conn):
        """Test health check endpoint."""
        # Mock database connections
        mock_queue_conn.return_value.close.return_value = None
        mock_portfolio_conn.return_value.close.return_value = None
        
        response = self.client.get('/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
    
    @patch('consistency_manager.consistency_manager.get_queue_db_connection')
    @patch('consistency_manager.consistency_manager.get_portfolio_db_connection')
    def test_readiness_check(self, mock_portfolio_conn, mock_queue_conn):
        """Test readiness check endpoint."""
        # Mock database connections
        mock_queue_conn.return_value.close.return_value = None
        mock_portfolio_conn.return_value.close.return_value = None
        
        response = self.client.get('/ready')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ready')
    
    @patch('consistency_manager.consistency_manager.sync_queue_to_portfolio')
    def test_manual_sync(self, mock_sync):
        """Test manual sync endpoint."""
        # Mock sync results
        mock_sync.return_value = {
            'processed': 5,
            'created': 3,
            'updated': 2,
            'errors': 0
        }
        
        response = self.client.post('/api/v1/sync')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['stats']['processed'], 5)
    
    @patch('consistency_manager.consistency_manager.get_queue_db_connection')
    @patch('consistency_manager.consistency_manager.get_portfolio_db_connection')
    def test_get_stats(self, mock_portfolio_conn, mock_queue_conn):
        """Test get stats endpoint."""
        # Mock database connections and cursors
        mock_queue_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchall.return_value = [
            ('investment', 10, 5, 3, 2, 0),
            ('withdrawal', 8, 4, 2, 2, 0)
        ]
        mock_portfolio_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = (18, 10, 8, 9, 4, 5, 0)
        
        response = self.client.get('/api/v1/stats')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('queue_stats', data)
        self.assertIn('portfolio_stats', data)

if __name__ == '__main__':
    unittest.main()
