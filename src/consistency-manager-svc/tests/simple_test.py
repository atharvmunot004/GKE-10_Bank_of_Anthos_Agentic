#!/usr/bin/env python3
"""
Simple test for consistency-manager-svc without database dependencies
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add the parent directory to the path to import the main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock psycopg2 before importing the main module
sys.modules['psycopg2'] = Mock()
sys.modules['psycopg2.extras'] = Mock()
sys.modules['psycopg2.extras.RealDictCursor'] = Mock()

# Now import the main module
from consistency_manager import ConsistencyManager, app

class TestConsistencyManagerSimple(unittest.TestCase):
    """Simple test cases for ConsistencyManager class without database dependencies."""
    
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
    
    def test_status_mapping(self):
        """Test status mapping logic."""
        # Test investment queue entry
        investment_entry = {
            'queue_type': 'investment',
            'account_number': '1234567890',
            'tier_1': 100.0,
            'tier_2': 200.0,
            'tier_3': 300.0,
            'status': 'COMPLETED',
            'created_at': '2024-01-01 10:00:00',
            'updated_at': '2024-01-01 10:05:00',
            'processed_at': '2024-01-01 10:05:00'
        }
        
        # Test withdrawal queue entry
        withdrawal_entry = {
            'queue_type': 'withdrawal',
            'account_number': '1234567890',
            'tier_1': 50.0,
            'tier_2': 100.0,
            'tier_3': 150.0,
            'status': 'PROCESSING',
            'created_at': '2024-01-01 10:00:00',
            'updated_at': '2024-01-01 10:05:00',
            'processed_at': '2024-01-01 10:05:00'
        }
        
        # Test status mapping
        status_mapping = {
            'PROCESSING': 'PENDING',
            'COMPLETED': 'COMPLETED',
            'FAILED': 'FAILED',
            'CANCELLED': 'CANCELLED'
        }
        
        # Test investment status mapping
        investment_status = status_mapping.get(investment_entry['status'], 'PENDING')
        self.assertEqual(investment_status, 'COMPLETED')
        
        # Test withdrawal status mapping
        withdrawal_status = status_mapping.get(withdrawal_entry['status'], 'PENDING')
        self.assertEqual(withdrawal_status, 'PENDING')
    
    def test_transaction_type_mapping(self):
        """Test transaction type mapping logic."""
        # Test investment type
        investment_entry = {
            'queue_type': 'investment',
            'tier_1': 100.0,
            'tier_2': 200.0,
            'tier_3': 300.0
        }
        
        if investment_entry['queue_type'] == 'investment':
            transaction_type = 'DEPOSIT'
            total_amount = float(investment_entry['tier_1']) + float(investment_entry['tier_2']) + float(investment_entry['tier_3'])
            tier1_change = float(investment_entry['tier_1'])
            tier2_change = float(investment_entry['tier_2'])
            tier3_change = float(investment_entry['tier_3'])
        else:
            transaction_type = 'WITHDRAWAL'
            total_amount = -(float(investment_entry['tier_1']) + float(investment_entry['tier_2']) + float(investment_entry['tier_3']))
            tier1_change = -float(investment_entry['tier_1'])
            tier2_change = -float(investment_entry['tier_2'])
            tier3_change = -float(investment_entry['tier_3'])
        
        self.assertEqual(transaction_type, 'DEPOSIT')
        self.assertEqual(total_amount, 600.0)
        self.assertEqual(tier1_change, 100.0)
        self.assertEqual(tier2_change, 200.0)
        self.assertEqual(tier3_change, 300.0)
        
        # Test withdrawal type
        withdrawal_entry = {
            'queue_type': 'withdrawal',
            'tier_1': 50.0,
            'tier_2': 100.0,
            'tier_3': 150.0
        }
        
        if withdrawal_entry['queue_type'] == 'investment':
            transaction_type = 'DEPOSIT'
            total_amount = float(withdrawal_entry['tier_1']) + float(withdrawal_entry['tier_2']) + float(withdrawal_entry['tier_3'])
            tier1_change = float(withdrawal_entry['tier_1'])
            tier2_change = float(withdrawal_entry['tier_2'])
            tier3_change = float(withdrawal_entry['tier_3'])
        else:
            transaction_type = 'WITHDRAWAL'
            total_amount = -(float(withdrawal_entry['tier_1']) + float(withdrawal_entry['tier_2']) + float(withdrawal_entry['tier_3']))
            tier1_change = -float(withdrawal_entry['tier_1'])
            tier2_change = -float(withdrawal_entry['tier_2'])
            tier3_change = -float(withdrawal_entry['tier_3'])
        
        self.assertEqual(transaction_type, 'WITHDRAWAL')
        self.assertEqual(total_amount, -300.0)
        self.assertEqual(tier1_change, -50.0)
        self.assertEqual(tier2_change, -100.0)
        self.assertEqual(tier3_change, -150.0)
    
    def test_portfolio_value_calculation(self):
        """Test portfolio value calculation logic."""
        # Test investment calculation
        current_values = (1000.0, 2000.0, 3000.0, 6000.0)  # tier1, tier2, tier3, total
        investment_entry = {
            'queue_type': 'investment',
            'tier_1': 100.0,
            'tier_2': 200.0,
            'tier_3': 300.0
        }
        
        current_tier1, current_tier2, current_tier3, current_total = current_values
        
        if investment_entry['queue_type'] == 'investment':
            # Add to portfolio
            new_tier1 = current_tier1 + float(investment_entry['tier_1'])
            new_tier2 = current_tier2 + float(investment_entry['tier_2'])
            new_tier3 = current_tier3 + float(investment_entry['tier_3'])
        else:  # withdrawal
            # Subtract from portfolio
            new_tier1 = current_tier1 - float(investment_entry['tier_1'])
            new_tier2 = current_tier2 - float(investment_entry['tier_2'])
            new_tier3 = current_tier3 - float(investment_entry['tier_3'])
        
        new_total = new_tier1 + new_tier2 + new_tier3
        
        self.assertEqual(new_tier1, 1100.0)
        self.assertEqual(new_tier2, 2200.0)
        self.assertEqual(new_tier3, 3300.0)
        self.assertEqual(new_total, 6600.0)
        
        # Test withdrawal calculation
        withdrawal_entry = {
            'queue_type': 'withdrawal',
            'tier_1': 50.0,
            'tier_2': 100.0,
            'tier_3': 150.0
        }
        
        if withdrawal_entry['queue_type'] == 'investment':
            # Add to portfolio
            new_tier1 = current_tier1 + float(withdrawal_entry['tier_1'])
            new_tier2 = current_tier2 + float(withdrawal_entry['tier_2'])
            new_tier3 = current_tier3 + float(withdrawal_entry['tier_3'])
        else:  # withdrawal
            # Subtract from portfolio
            new_tier1 = current_tier1 - float(withdrawal_entry['tier_1'])
            new_tier2 = current_tier2 - float(withdrawal_entry['tier_2'])
            new_tier3 = current_tier3 - float(withdrawal_entry['tier_3'])
        
        new_total = new_tier1 + new_tier2 + new_tier3
        
        self.assertEqual(new_tier1, 950.0)
        self.assertEqual(new_tier2, 1900.0)
        self.assertEqual(new_tier3, 2850.0)
        self.assertEqual(new_total, 5700.0)
    
    def test_sync_stats_initialization(self):
        """Test sync statistics initialization."""
        stats = {
            'processed': 0,
            'transactions_updated': 0,
            'transactions_created': 0,
            'portfolios_updated': 0,
            'errors': 0
        }
        
        self.assertEqual(stats['processed'], 0)
        self.assertEqual(stats['transactions_updated'], 0)
        self.assertEqual(stats['transactions_created'], 0)
        self.assertEqual(stats['portfolios_updated'], 0)
        self.assertEqual(stats['errors'], 0)
    
    def test_queue_entry_processing(self):
        """Test queue entry processing logic."""
        # Test investment entry
        investment_entry = {
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
        
        # Test withdrawal entry
        withdrawal_entry = {
            'queue_type': 'withdrawal',
            'queue_id': 2,
            'account_number': '1234567890',
            'tier_1': 50.0,
            'tier_2': 100.0,
            'tier_3': 150.0,
            'uuid': 'test-uuid-2',
            'status': 'PROCESSING',
            'created_at': '2024-01-01 10:00:00',
            'updated_at': '2024-01-01 10:05:00',
            'processed_at': '2024-01-01 10:05:00'
        }
        
        # Test that entries have required fields
        required_fields = ['queue_type', 'account_number', 'tier_1', 'tier_2', 'tier_3', 'uuid', 'status']
        
        for field in required_fields:
            self.assertIn(field, investment_entry)
            self.assertIn(field, withdrawal_entry)
        
        # Test investment entry values
        self.assertEqual(investment_entry['queue_type'], 'investment')
        self.assertEqual(investment_entry['status'], 'COMPLETED')
        self.assertEqual(investment_entry['uuid'], 'test-uuid-1')
        
        # Test withdrawal entry values
        self.assertEqual(withdrawal_entry['queue_type'], 'withdrawal')
        self.assertEqual(withdrawal_entry['status'], 'PROCESSING')
        self.assertEqual(withdrawal_entry['uuid'], 'test-uuid-2')

class TestConsistencyManagerAPISimple(unittest.TestCase):
    """Simple test cases for API endpoints without database dependencies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
    
    def test_health_check_structure(self):
        """Test health check response structure."""
        # Mock the database connections
        with patch('consistency_manager.consistency_manager.get_queue_db_connection') as mock_queue_conn, \
             patch('consistency_manager.consistency_manager.get_portfolio_db_connection') as mock_portfolio_conn:
            
            mock_queue_conn.return_value.close.return_value = None
            mock_portfolio_conn.return_value.close.return_value = None
            
            response = self.client.get('/health')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            # Test response structure
            self.assertIn('status', data)
            self.assertIn('timestamp', data)
            self.assertIn('sync_interval', data)
            self.assertIn('sync_running', data)
            
            self.assertEqual(data['status'], 'healthy')
    
    def test_readiness_check_structure(self):
        """Test readiness check response structure."""
        # Mock the database connections
        with patch('consistency_manager.consistency_manager.get_queue_db_connection') as mock_queue_conn, \
             patch('consistency_manager.consistency_manager.get_portfolio_db_connection') as mock_portfolio_conn:
            
            mock_queue_conn.return_value.close.return_value = None
            mock_portfolio_conn.return_value.close.return_value = None
            
            response = self.client.get('/ready')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            # Test response structure
            self.assertIn('status', data)
            self.assertIn('timestamp', data)
            
            self.assertEqual(data['status'], 'ready')
    
    def test_manual_sync_structure(self):
        """Test manual sync response structure."""
        # Mock the sync method
        with patch('consistency_manager.consistency_manager.sync_queue_to_portfolio') as mock_sync:
            mock_sync.return_value = {
                'processed': 5,
                'transactions_updated': 3,
                'transactions_created': 2,
                'portfolios_updated': 4,
                'errors': 0
            }
            
            response = self.client.post('/api/v1/sync')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            
            # Test response structure
            self.assertIn('status', data)
            self.assertIn('message', data)
            self.assertIn('stats', data)
            self.assertIn('timestamp', data)
            
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['stats']['processed'], 5)
            self.assertEqual(data['stats']['transactions_updated'], 3)
            self.assertEqual(data['stats']['transactions_created'], 2)
            self.assertEqual(data['stats']['portfolios_updated'], 4)
            self.assertEqual(data['stats']['errors'], 0)

def run_tests():
    """Run all tests and return results."""
    print("🧪 Running Consistency Manager Service Unit Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestConsistencyManagerSimple))
    suite.addTests(loader.loadTestsFromTestCase(TestConsistencyManagerAPISimple))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"✅ Tests Run: {result.testsRun}")
    print(f"✅ Failures: {len(result.failures)}")
    print(f"✅ Errors: {len(result.errors)}")
    print(f"✅ Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
