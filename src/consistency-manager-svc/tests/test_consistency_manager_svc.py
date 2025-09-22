import unittest
from unittest.mock import patch, Mock, MagicMock
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from consistency_manager_svc import app

class TestConsistencyManagerSvc(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        os.environ['QUEUE_DB_URI'] = 'postgresql://user:password@host:port/queue-db'
        os.environ['USER_PORTFOLIO_DB_URI'] = 'postgresql://user:password@host:port/portfolio-db'
        os.environ['POLLING_INTERVAL'] = '30'
        os.environ['TIER1'] = '1000000.0'
        os.environ['TIER1_MV'] = '1100000.0'
        os.environ['TIER2'] = '2000000.0'
        os.environ['TIER2_MV'] = '2100000.0'
        os.environ['TIER3'] = '500000.0'
        os.environ['TIER3_MV'] = '550000.0'

    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "healthy"})

    @patch('consistency_manager_svc.get_queue_db_connection')
    @patch('consistency_manager_svc.get_portfolio_db_connection')
    def test_ready_endpoint(self, mock_portfolio_conn, mock_queue_conn):
        """Test readiness check endpoint."""
        # Mock database connections
        mock_queue_cursor = Mock()
        mock_queue_conn.return_value.cursor.return_value = mock_queue_cursor
        
        mock_portfolio_cursor = Mock()
        mock_portfolio_conn.return_value.cursor.return_value = mock_portfolio_cursor
        
        response = self.app.get('/ready')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"status": "ready"})

    def test_calculate_delta_values(self):
        """Test delta value calculation."""
        from consistency_manager_svc import calculate_delta_values
        
        result = calculate_delta_values()
        
        # Expected: del_t1_mv = (1100000 - 1000000) / 1000000 = 0.1
        # Expected: del_t2_mv = (2100000 - 2000000) / 2000000 = 0.05
        # Expected: del_t3_mv = (550000 - 500000) / 500000 = 0.1
        self.assertAlmostEqual(result['del_t1_mv'], 0.1, places=4)
        self.assertAlmostEqual(result['del_t2_mv'], 0.05, places=4)
        self.assertAlmostEqual(result['del_t3_mv'], 0.1, places=4)

    @patch('consistency_manager_svc.get_queue_db_connection')
    def test_get_updated_investment_queue_entries(self, mock_db_connect):
        """Test getting updated investment queue entries."""
        from consistency_manager_svc import get_updated_investment_queue_entries
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock database response
        mock_entries = [
            {
                'uuid': 'uuid-001',
                'accountid': '1234567890',
                'status': 'COMPLETED',
                'updated_at': datetime.now()
            },
            {
                'uuid': 'uuid-002',
                'accountid': '1234567891',
                'status': 'PROCESSING',
                'updated_at': datetime.now()
            }
        ]
        mock_cursor.fetchall.return_value = mock_entries
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        timestamp = datetime.now()
        result = get_updated_investment_queue_entries(timestamp)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['uuid'], 'uuid-001')
        self.assertEqual(result[1]['status'], 'PROCESSING')

    @patch('consistency_manager_svc.get_portfolio_db_connection')
    def test_update_portfolio_transaction_status(self, mock_db_connect):
        """Test updating portfolio transaction status."""
        from consistency_manager_svc import update_portfolio_transaction_status
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        uuids = ['uuid-001', 'uuid-002']
        status = 'PROCESSED'
        
        result = update_portfolio_transaction_status(uuids, status)
        
        self.assertTrue(result)
        # Should call execute for each UUID
        self.assertEqual(mock_cursor.execute.call_count, len(uuids))
        mock_conn.commit.assert_called_once()

    @patch('consistency_manager_svc.get_portfolio_db_connection')
    def test_update_portfolio_tier_values_invest(self, mock_db_connect):
        """Test updating portfolio tier values for investment."""
        from consistency_manager_svc import update_portfolio_tier_values
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock portfolio data
        mock_portfolio = {
            'tier1_value': 1000.0,
            'tier2_value': 2000.0,
            'tier3_value': 500.0,
            'tier1_allocation': 1000.0,
            'tier2_allocation': 2000.0,
            'tier3_allocation': 500.0
        }
        mock_cursor.fetchone.return_value = mock_portfolio
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        accountid = '1234567890'
        delta_values = {'del_t1_mv': 0.1, 'del_t2_mv': 0.05, 'del_t3_mv': 0.1}
        
        result = update_portfolio_tier_values(
            accountid, 
            delta_values['del_t1_mv'], 
            delta_values['del_t2_mv'], 
            delta_values['del_t3_mv'],
            'invest'
        )
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    @patch('consistency_manager_svc.get_portfolio_db_connection')
    def test_update_portfolio_tier_values_withdrawal(self, mock_db_connect):
        """Test updating portfolio tier allocations for withdrawal."""
        from consistency_manager_svc import update_portfolio_tier_values
        
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock portfolio data
        mock_portfolio = {
            'tier1_value': 1000.0,
            'tier2_value': 2000.0,
            'tier3_value': 500.0,
            'tier1_allocation': 1000.0,
            'tier2_allocation': 2000.0,
            'tier3_allocation': 500.0
        }
        mock_cursor.fetchone.return_value = mock_portfolio
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        
        accountid = '1234567890'
        delta_values = {'del_t1_mv': 0.1, 'del_t2_mv': 0.05, 'del_t3_mv': 0.1}
        
        result = update_portfolio_tier_values(
            accountid, 
            delta_values['del_t1_mv'], 
            delta_values['del_t2_mv'], 
            delta_values['del_t3_mv'],
            'withdrawal'
        )
        
        self.assertTrue(result)
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()

    def test_get_consistency_status(self):
        """Test getting consistency status."""
        response = self.app.get('/api/v1/consistency/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('tier_values', data)
        self.assertIn('delta_values', data)

    def test_update_tier_values(self):
        """Test updating tier values."""
        update_data = {
            'TIER1': '1200000.0',
            'TIER1_MV': '1300000.0',
            'TIER2': '2200000.0',
            'TIER2_MV': '2300000.0'
        }
        
        response = self.app.post('/api/v1/consistency/update-tier-values', 
                                json=update_data)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['updated_tier_values']['TIER1'], 1200000.0)

    @patch('consistency_manager_svc.get_queue_db_connection')
    @patch('consistency_manager_svc.get_portfolio_db_connection')
    def test_consistency_cycle(self, mock_portfolio_conn, mock_queue_conn):
        """Test consistency cycle execution."""
        from consistency_manager_svc import consistency_cycle
        
        # Mock database connections
        mock_queue_cursor = Mock()
        mock_queue_conn.return_value.cursor.return_value = mock_queue_cursor
        
        mock_portfolio_cursor = Mock()
        mock_portfolio_conn.return_value.cursor.return_value = mock_portfolio_cursor
        
        # Mock empty results
        mock_queue_cursor.fetchall.return_value = []
        mock_queue_cursor.__enter__ = Mock(return_value=mock_queue_cursor)
        mock_queue_cursor.__exit__ = Mock(return_value=None)
        
        mock_portfolio_cursor.__enter__ = Mock(return_value=mock_portfolio_cursor)
        mock_portfolio_cursor.__exit__ = Mock(return_value=None)
        
        result = consistency_cycle()
        
        self.assertEqual(result['status'], 'success')
        self.assertIn('delta_values', result)
        self.assertIn('timestamp', result)

    def test_process_investment_queue_entries(self):
        """Test processing investment queue entries."""
        from consistency_manager_svc import process_investment_queue_entries
        
        entries = [
            {
                'uuid': 'uuid-001',
                'accountid': '1234567890',
                'status': 'COMPLETED',
                'updated_at': datetime.now()
            },
            {
                'uuid': 'uuid-002',
                'accountid': '1234567891',
                'status': 'PROCESSING',
                'updated_at': datetime.now()
            }
        ]
        
        delta_values = {'del_t1_mv': 0.1, 'del_t2_mv': 0.05, 'del_t3_mv': 0.1}
        
        with patch('consistency_manager_svc.update_portfolio_transaction_status') as mock_update_status, \
             patch('consistency_manager_svc.update_portfolio_tier_values') as mock_update_values:
            
            processed, completed = process_investment_queue_entries(entries, delta_values)
            
            self.assertEqual(processed, 2)
            self.assertEqual(completed, 1)
            mock_update_status.assert_called_once()
            mock_update_values.assert_called_once()

    def test_process_withdrawal_queue_entries(self):
        """Test processing withdrawal queue entries."""
        from consistency_manager_svc import process_withdrawal_queue_entries
        
        entries = [
            {
                'uuid': 'uuid-003',
                'accountid': '1234567892',
                'status': 'COMPLETED',
                'updated_at': datetime.now()
            }
        ]
        
        delta_values = {'del_t1_mv': 0.1, 'del_t2_mv': 0.05, 'del_t3_mv': 0.1}
        
        with patch('consistency_manager_svc.update_portfolio_transaction_status') as mock_update_status, \
             patch('consistency_manager_svc.update_portfolio_tier_values') as mock_update_values:
            
            processed, completed = process_withdrawal_queue_entries(entries, delta_values)
            
            self.assertEqual(processed, 1)
            self.assertEqual(completed, 1)
            mock_update_status.assert_called_once()
            mock_update_values.assert_called_once()

if __name__ == '__main__':
    print("🧪 Running Consistency Manager Service Unit Tests")
    print("============================================================")
    unittest.main()
