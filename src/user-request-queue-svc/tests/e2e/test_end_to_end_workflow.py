"""
End-to-end tests for complete workflow
"""
import pytest
import asyncio
import httpx
from decimal import Decimal
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock
import time

from services import QueueProcessor
from database import DatabaseManager
from models import QueueTransaction, TransactionType, TransactionStatus


@pytest.mark.e2e
class TestEndToEndWorkflow:
    """End-to-end tests for complete transaction processing workflow"""
    
    @pytest.fixture
    async def e2e_setup(self):
        """Setup for end-to-end tests with mocked dependencies"""
        # Mock database manager
        mock_db = MagicMock(spec=DatabaseManager)
        mock_db.initialize = AsyncMock()
        mock_db.close = AsyncMock()
        mock_db.is_connected = AsyncMock(return_value=True)
        
        # Mock queue processor
        processor = QueueProcessor()
        
        # Setup test data
        test_transactions = [
            {
                'uuid': 'e2e-uuid-1',
                'accountid': '12345678901234567890',
                'tier1': Decimal('1000.00'),
                'tier2': Decimal('2000.00'),
                'tier3': Decimal('500.00'),
                'purpose': 'INVEST',
                'status': 'PENDING',
                'created_at': datetime.utcnow(),
                'updated_at': None,
                'processed_at': None
            },
            {
                'uuid': 'e2e-uuid-2',
                'accountid': '12345678901234567890',
                'tier1': Decimal('300.00'),
                'tier2': Decimal('600.00'),
                'tier3': Decimal('150.00'),
                'purpose': 'WITHDRAW',
                'status': 'PENDING',
                'created_at': datetime.utcnow(),
                'updated_at': None,
                'processed_at': None
            }
        ]
        
        return {
            'processor': processor,
            'mock_db': mock_db,
            'test_transactions': test_transactions
        }
    
    @pytest.mark.asyncio
    async def test_complete_batch_processing_workflow(self, e2e_setup):
        """Test complete workflow from queue polling to status update"""
        processor = e2e_setup['processor']
        mock_db = e2e_setup['mock_db']
        test_transactions = e2e_setup['test_transactions']
        
        # Setup database mocks
        mock_db.count_pending_requests = AsyncMock(side_effect=[10, 0])  # First call: enough, second: none
        mock_db.fetch_batch = AsyncMock(return_value=test_transactions)
        mock_db.update_batch_status = AsyncMock(return_value=True)
        
        # Setup asset agent mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'COMPLETED',
            'message': 'Portfolio processed successfully',
            'transaction_id': 'tx-e2e-123'
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('database.db_manager', mock_db):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                
                # Execute the workflow
                processed_batches = await processor.poll_and_process()
                
                # Verify workflow execution
                assert processed_batches == 1
                
                # Verify database interactions
                mock_db.count_pending_requests.assert_called()
                mock_db.fetch_batch.assert_called_once_with(10)  # Default batch size
                
                # Verify status updates (PROCESSING and COMPLETED)
                assert mock_db.update_batch_status.call_count == 2
                
                # Verify first call was to set PROCESSING status
                first_call = mock_db.update_batch_status.call_args_list[0]
                assert first_call[0][0] == ['e2e-uuid-1', 'e2e-uuid-2']  # UUIDs
                assert first_call[0][1] == 'PROCESSING'  # Status
                
                # Verify second call was to set COMPLETED status
                second_call = mock_db.update_batch_status.call_args_list[1]
                assert second_call[0][0] == ['e2e-uuid-1', 'e2e-uuid-2']  # UUIDs
                assert second_call[0][1] == 'COMPLETED'  # Status
                
                # Verify asset agent was called
                mock_client.return_value.__aenter__.return_value.post.assert_called_once()
                
                # Verify request to asset agent
                call_args = mock_client.return_value.__aenter__.return_value.post.call_args
                request_data = call_args[1]['json']
                
                # Expected calculation: INVEST(1000, 2000, 500) - WITHDRAW(300, 600, 150) = (700, 1400, 350)
                assert request_data['T1'] == 700.0
                assert request_data['T2'] == 1400.0
                assert request_data['T3'] == 350.0
    
    @pytest.mark.asyncio
    async def test_workflow_with_asset_agent_failure(self, e2e_setup):
        """Test workflow when asset agent returns failure"""
        processor = e2e_setup['processor']
        mock_db = e2e_setup['mock_db']
        test_transactions = e2e_setup['test_transactions']
        
        # Setup database mocks
        mock_db.count_pending_requests = AsyncMock(return_value=10)
        mock_db.fetch_batch = AsyncMock(return_value=test_transactions)
        mock_db.update_batch_status = AsyncMock(return_value=True)
        
        # Setup asset agent failure response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'FAILED',
            'message': 'Insufficient funds',
            'transaction_id': 'tx-e2e-failed'
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('database.db_manager', mock_db):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                
                # Execute the workflow
                processed_batches = await processor.poll_and_process()
                
                # Verify workflow execution
                assert processed_batches == 1
                
                # Verify status updates (PROCESSING and FAILED)
                assert mock_db.update_batch_status.call_count == 2
                
                # Verify final status was FAILED
                final_call = mock_db.update_batch_status.call_args_list[1]
                assert final_call[0][1] == 'FAILED'
    
    @pytest.mark.asyncio
    async def test_workflow_with_database_error(self, e2e_setup):
        """Test workflow error handling when database operations fail"""
        processor = e2e_setup['processor']
        mock_db = e2e_setup['mock_db']
        test_transactions = e2e_setup['test_transactions']
        
        # Setup database mocks with error
        mock_db.count_pending_requests = AsyncMock(return_value=10)
        mock_db.fetch_batch = AsyncMock(return_value=test_transactions)
        mock_db.update_batch_status = AsyncMock(side_effect=[True, Exception("Database error")])
        
        # Setup asset agent success response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'COMPLETED',
            'message': 'Success'
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('database.db_manager', mock_db):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                
                # Execute the workflow - should handle database error gracefully
                processed_batches = await processor.poll_and_process()
                
                # Should still report processing attempt
                assert processed_batches == 1
                
                # Verify both status update attempts were made
                assert mock_db.update_batch_status.call_count == 2
    
    @pytest.mark.asyncio
    async def test_workflow_with_network_timeout(self, e2e_setup):
        """Test workflow handling of network timeouts with retry"""
        processor = e2e_setup['processor']
        mock_db = e2e_setup['mock_db']
        test_transactions = e2e_setup['test_transactions']
        
        # Setup database mocks
        mock_db.count_pending_requests = AsyncMock(return_value=10)
        mock_db.fetch_batch = AsyncMock(return_value=test_transactions)
        mock_db.update_batch_status = AsyncMock(return_value=True)
        
        # Setup network timeout followed by success
        mock_success_response = MagicMock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            'status': 'COMPLETED',
            'message': 'Success after retry'
        }
        mock_success_response.raise_for_status = MagicMock()
        
        with patch('database.db_manager', mock_db):
            with patch('httpx.AsyncClient') as mock_client:
                # First call times out, second succeeds
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=[httpx.TimeoutException("Timeout"), mock_success_response]
                )
                
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    # Execute the workflow
                    processed_batches = await processor.poll_and_process()
                    
                    # Should succeed after retry
                    assert processed_batches == 1
                    
                    # Verify retry was attempted
                    assert mock_client.return_value.__aenter__.return_value.post.call_count == 2
                    
                    # Verify final status was COMPLETED
                    final_call = mock_db.update_batch_status.call_args_list[1]
                    assert final_call[0][1] == 'COMPLETED'
    
    @pytest.mark.asyncio
    async def test_multiple_batch_processing_workflow(self, e2e_setup):
        """Test processing multiple batches in sequence"""
        processor = e2e_setup['processor']
        mock_db = e2e_setup['mock_db']
        
        # Create multiple batches of test data
        batch1 = [
            {
                'uuid': 'batch1-uuid-1',
                'accountid': '12345678901234567890',
                'tier1': Decimal('1000.00'),
                'tier2': Decimal('2000.00'),
                'tier3': Decimal('500.00'),
                'purpose': 'INVEST',
                'status': 'PENDING',
                'created_at': datetime.utcnow(),
                'updated_at': None,
                'processed_at': None
            }
        ]
        
        batch2 = [
            {
                'uuid': 'batch2-uuid-1',
                'accountid': '98765432109876543210',
                'tier1': Decimal('500.00'),
                'tier2': Decimal('1000.00'),
                'tier3': Decimal('250.00'),
                'purpose': 'WITHDRAW',
                'status': 'PENDING',
                'created_at': datetime.utcnow(),
                'updated_at': None,
                'processed_at': None
            }
        ]
        
        # Setup database mocks for multiple batches
        mock_db.count_pending_requests = AsyncMock(side_effect=[20, 10, 0])  # Two batches, then none
        mock_db.fetch_batch = AsyncMock(side_effect=[batch1, batch2])
        mock_db.update_batch_status = AsyncMock(return_value=True)
        
        # Setup asset agent success response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'COMPLETED',
            'message': 'Success'
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('database.db_manager', mock_db):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                
                # Execute the workflow
                processed_batches = await processor.poll_and_process()
                
                # Should process both batches
                assert processed_batches == 2
                
                # Verify database interactions for both batches
                assert mock_db.fetch_batch.call_count == 2
                assert mock_db.update_batch_status.call_count == 4  # 2 batches × 2 status updates each
                
                # Verify asset agent was called for both batches
                assert mock_client.return_value.__aenter__.return_value.post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_protection(self, e2e_setup):
        """Test that concurrent processing is properly prevented"""
        processor = e2e_setup['processor']
        mock_db = e2e_setup['mock_db']
        
        # Setup database mocks
        mock_db.count_pending_requests = AsyncMock(return_value=10)
        mock_db.fetch_batch = AsyncMock(return_value=e2e_setup['test_transactions'])
        mock_db.update_batch_status = AsyncMock(return_value=True)
        
        # Setup asset agent with delay to simulate processing time
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'COMPLETED'}
        mock_response.raise_for_status = MagicMock()
        
        async def delayed_post(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing delay
            return mock_response
        
        with patch('database.db_manager', mock_db):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.post = delayed_post
                
                # Start two concurrent processing tasks
                task1 = asyncio.create_task(processor.poll_and_process())
                task2 = asyncio.create_task(processor.poll_and_process())
                
                results = await asyncio.gather(task1, task2)
                
                # Only one should have processed (the other should return 0 due to concurrent protection)
                assert sum(results) == 1
                assert 0 in results  # One task should return 0 (skipped due to concurrent processing)
    
    @pytest.mark.asyncio
    async def test_edge_case_zero_amounts_workflow(self, e2e_setup):
        """Test workflow with zero tier amounts"""
        processor = e2e_setup['processor']
        mock_db = e2e_setup['mock_db']
        
        # Test transactions with zero amounts
        zero_transactions = [
            {
                'uuid': 'zero-uuid-1',
                'accountid': '12345678901234567890',
                'tier1': Decimal('0.00'),
                'tier2': Decimal('0.00'),
                'tier3': Decimal('0.00'),
                'purpose': 'INVEST',
                'status': 'PENDING',
                'created_at': datetime.utcnow(),
                'updated_at': None,
                'processed_at': None
            }
        ]
        
        # Setup database mocks
        mock_db.count_pending_requests = AsyncMock(side_effect=[10, 0])
        mock_db.fetch_batch = AsyncMock(return_value=zero_transactions)
        mock_db.update_batch_status = AsyncMock(return_value=True)
        
        # Setup asset agent response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'COMPLETED'}
        mock_response.raise_for_status = MagicMock()
        
        with patch('database.db_manager', mock_db):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                
                # Execute the workflow
                processed_batches = await processor.poll_and_process()
                
                # Should process successfully
                assert processed_batches == 1
                
                # Verify asset agent received zero amounts
                call_args = mock_client.return_value.__aenter__.return_value.post.call_args
                request_data = call_args[1]['json']
                assert request_data['T1'] == 0.0
                assert request_data['T2'] == 0.0
                assert request_data['T3'] == 0.0


@pytest.mark.e2e
@pytest.mark.slow
class TestEndToEndPerformance:
    """Performance tests for end-to-end workflow"""
    
    @pytest.mark.asyncio
    async def test_large_batch_processing_performance(self):
        """Test performance with large batches"""
        processor = QueueProcessor()
        
        # Create large batch of test transactions
        large_batch = []
        for i in range(100):
            large_batch.append({
                'uuid': f'perf-uuid-{i}',
                'accountid': f'account-{i % 10}',
                'tier1': Decimal(f'{i * 10}.00'),
                'tier2': Decimal(f'{i * 20}.00'),
                'tier3': Decimal(f'{i * 5}.00'),
                'purpose': 'INVEST' if i % 2 == 0 else 'WITHDRAW',
                'status': 'PENDING',
                'created_at': datetime.utcnow(),
                'updated_at': None,
                'processed_at': None
            })
        
        # Mock database
        mock_db = MagicMock()
        mock_db.count_pending_requests = AsyncMock(side_effect=[100, 0])
        mock_db.fetch_batch = AsyncMock(return_value=large_batch)
        mock_db.update_batch_status = AsyncMock(return_value=True)
        
        # Mock asset agent with minimal delay
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'COMPLETED'}
        mock_response.raise_for_status = MagicMock()
        
        with patch('database.db_manager', mock_db):
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                
                # Measure processing time
                start_time = time.time()
                processed_batches = await processor.poll_and_process()
                end_time = time.time()
                
                processing_time = end_time - start_time
                
                # Verify processing completed
                assert processed_batches == 1
                
                # Performance assertion - should complete within reasonable time
                assert processing_time < 1.0  # Should complete within 1 second
    
    @pytest.mark.asyncio
    async def test_continuous_polling_simulation(self):
        """Test continuous polling behavior simulation"""
        processor = QueueProcessor()
        
        # Simulate multiple polling cycles
        poll_results = []
        
        # Mock database with varying queue sizes
        queue_sizes = [0, 5, 10, 15, 8, 0]  # Simulate varying queue activity
        mock_db = MagicMock()
        mock_db.count_pending_requests = AsyncMock(side_effect=queue_sizes)
        mock_db.fetch_batch = AsyncMock(return_value=[])
        mock_db.update_batch_status = AsyncMock(return_value=True)
        
        with patch('database.db_manager', mock_db):
            # Simulate multiple polling cycles
            for _ in range(len(queue_sizes)):
                result = await processor.poll_and_process()
                poll_results.append(result)
        
        # Verify polling behavior
        assert len(poll_results) == len(queue_sizes)
        
        # Should only process when queue size >= batch size (10)
        expected_processing = [0, 0, 0, 0, 0, 0]  # No actual batches returned, so no processing
        assert poll_results == expected_processing
