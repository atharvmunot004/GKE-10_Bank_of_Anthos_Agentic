"""
Integration tests for external service communication
"""
import pytest
import asyncio
import httpx
from unittest.mock import patch, MagicMock
from decimal import Decimal
import json

from services import AssetAgentClient
from models import TierCalculation, AssetAgentResponse


@pytest.mark.integration
@pytest.mark.external
class TestAssetAgentIntegration:
    """Integration tests for bank-asset-agent communication"""
    
    @pytest.fixture
    def mock_server_responses(self):
        """Fixture providing various server response scenarios"""
        return {
            'success': {
                'status_code': 200,
                'json_data': {
                    'status': 'COMPLETED',
                    'message': 'Portfolio processed successfully',
                    'transaction_id': 'tx-12345'
                }
            },
            'failure': {
                'status_code': 200,
                'json_data': {
                    'status': 'FAILED',
                    'message': 'Insufficient funds',
                    'transaction_id': 'tx-12346'
                }
            },
            'server_error': {
                'status_code': 500,
                'text': 'Internal Server Error'
            },
            'timeout': {
                'exception': httpx.TimeoutException("Request timeout")
            },
            'connection_error': {
                'exception': httpx.ConnectError("Connection failed")
            }
        }
    
    @pytest.fixture
    def asset_agent_client(self):
        """Fixture providing asset agent client"""
        return AssetAgentClient()
    
    @pytest.fixture
    def sample_tier_calculation(self):
        """Fixture providing sample tier calculation"""
        return TierCalculation(
            T1=Decimal("1500.00"),
            T2=Decimal("3000.00"),
            T3=Decimal("750.00")
        )
    
    @pytest.mark.asyncio
    async def test_process_portfolio_success(self, asset_agent_client, sample_tier_calculation, mock_server_responses):
        """Test successful portfolio processing"""
        success_response = mock_server_responses['success']
        
        mock_response = MagicMock()
        mock_response.status_code = success_response['status_code']
        mock_response.json.return_value = success_response['json_data']
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await asset_agent_client.process_portfolio(sample_tier_calculation)
            
            assert isinstance(result, AssetAgentResponse)
            assert result.status == 'COMPLETED'
            assert result.message == 'Portfolio processed successfully'
            assert result.transaction_id == 'tx-12345'
            
            # Verify the request was made correctly
            mock_client.return_value.__aenter__.return_value.post.assert_called_once()
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            
            # Check URL
            assert asset_agent_client.base_url in call_args[0]
            
            # Check request data
            request_data = call_args[1]['json']
            assert request_data['T1'] == float(sample_tier_calculation.T1)
            assert request_data['T2'] == float(sample_tier_calculation.T2)
            assert request_data['T3'] == float(sample_tier_calculation.T3)
    
    @pytest.mark.asyncio
    async def test_process_portfolio_failure(self, asset_agent_client, sample_tier_calculation, mock_server_responses):
        """Test portfolio processing failure response"""
        failure_response = mock_server_responses['failure']
        
        mock_response = MagicMock()
        mock_response.status_code = failure_response['status_code']
        mock_response.json.return_value = failure_response['json_data']
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await asset_agent_client.process_portfolio(sample_tier_calculation)
            
            assert isinstance(result, AssetAgentResponse)
            assert result.status == 'FAILED'
            assert result.message == 'Insufficient funds'
            assert result.transaction_id == 'tx-12346'
    
    @pytest.mark.asyncio
    async def test_process_portfolio_server_error(self, asset_agent_client, sample_tier_calculation, mock_server_responses):
        """Test handling of server errors"""
        server_error = mock_server_responses['server_error']
        
        mock_response = MagicMock()
        mock_response.status_code = server_error['status_code']
        mock_response.text = server_error['text']
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
            
            with pytest.raises(httpx.HTTPStatusError):
                await asset_agent_client.process_portfolio(sample_tier_calculation)
    
    @pytest.mark.asyncio
    async def test_process_portfolio_timeout_retry(self, asset_agent_client, sample_tier_calculation, mock_server_responses):
        """Test timeout handling with retry mechanism"""
        timeout_exception = mock_server_responses['timeout']['exception']
        success_response = mock_server_responses['success']
        
        mock_success_response = MagicMock()
        mock_success_response.status_code = success_response['status_code']
        mock_success_response.json.return_value = success_response['json_data']
        mock_success_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            # First call times out, second succeeds
            mock_client.return_value.__aenter__.return_value.post.side_effect = [
                timeout_exception,
                mock_success_response
            ]
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await asset_agent_client.process_portfolio(sample_tier_calculation)
                
                assert isinstance(result, AssetAgentResponse)
                assert result.status == 'COMPLETED'
                
                # Verify retry was attempted
                assert mock_client.return_value.__aenter__.return_value.post.call_count == 2
                mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_portfolio_max_retries_exceeded(self, asset_agent_client, sample_tier_calculation, mock_server_responses):
        """Test behavior when max retries are exceeded"""
        timeout_exception = mock_server_responses['timeout']['exception']
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = timeout_exception
            
            with patch('asyncio.sleep') as mock_sleep:
                with pytest.raises(httpx.TimeoutException):
                    await asset_agent_client.process_portfolio(sample_tier_calculation)
                
                # Verify all retry attempts were made
                assert mock_client.return_value.__aenter__.return_value.post.call_count == asset_agent_client.retry_attempts
                assert mock_sleep.call_count == asset_agent_client.retry_attempts - 1
    
    @pytest.mark.asyncio
    async def test_process_portfolio_connection_error(self, asset_agent_client, sample_tier_calculation, mock_server_responses):
        """Test handling of connection errors"""
        connection_error = mock_server_responses['connection_error']['exception']
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = connection_error
            
            with pytest.raises(httpx.ConnectError):
                await asset_agent_client.process_portfolio(sample_tier_calculation)
    
    @pytest.mark.asyncio
    async def test_is_available_success(self, asset_agent_client):
        """Test service availability check - success"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await asset_agent_client.is_available()
            
            assert result is True
            mock_client.return_value.__aenter__.return_value.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_is_available_failure(self, asset_agent_client):
        """Test service availability check - failure"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.ConnectError("Connection failed")
            
            result = await asset_agent_client.is_available()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, asset_agent_client, mock_server_responses):
        """Test concurrent requests to asset agent"""
        success_response = mock_server_responses['success']
        
        mock_response = MagicMock()
        mock_response.status_code = success_response['status_code']
        mock_response.json.return_value = success_response['json_data']
        mock_response.raise_for_status = MagicMock()
        
        # Create multiple tier calculations
        tier_calculations = [
            TierCalculation(T1=Decimal(f"{i * 100}.00"), T2=Decimal(f"{i * 200}.00"), T3=Decimal(f"{i * 50}.00"))
            for i in range(1, 6)
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Make concurrent requests
            tasks = [
                asset_agent_client.process_portfolio(calc)
                for calc in tier_calculations
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all requests succeeded
            assert len(results) == 5
            for result in results:
                assert isinstance(result, AssetAgentResponse)
                assert result.status == 'COMPLETED'
            
            # Verify all requests were made
            assert mock_client.return_value.__aenter__.return_value.post.call_count == 5
    
    @pytest.mark.asyncio
    async def test_request_data_serialization(self, asset_agent_client):
        """Test proper serialization of request data"""
        # Test with edge case decimal values
        tier_calc = TierCalculation(
            T1=Decimal("0.00000001"),  # Very small
            T2=Decimal("999999999.99999999"),  # Very large
            T3=Decimal("-500.00")  # Negative
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'COMPLETED',
            'message': 'Success'
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            await asset_agent_client.process_portfolio(tier_calc)
            
            # Verify request data serialization
            call_args = mock_client.return_value.__aenter__.return_value.post.call_args
            request_data = call_args[1]['json']
            
            # Check that decimals were properly converted to floats
            assert isinstance(request_data['T1'], float)
            assert isinstance(request_data['T2'], float)
            assert isinstance(request_data['T3'], float)
            
            # Check values
            assert request_data['T1'] == 0.00000001
            assert request_data['T2'] == 999999999.99999999
            assert request_data['T3'] == -500.00
    
    @pytest.mark.asyncio
    async def test_response_data_validation(self, asset_agent_client, sample_tier_calculation):
        """Test validation of response data"""
        # Test with invalid response format
        invalid_responses = [
            {},  # Empty response
            {'status': 'COMPLETED'},  # Missing optional fields (should still work)
            {'invalid_field': 'value'},  # Missing required status field
        ]
        
        for i, invalid_data in enumerate(invalid_responses):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = invalid_data
            mock_response.raise_for_status = MagicMock()
            
            with patch('httpx.AsyncClient') as mock_client:
                mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                
                if i == 1:  # This should work (only status required)
                    result = await asset_agent_client.process_portfolio(sample_tier_calculation)
                    assert result.status == 'COMPLETED'
                    assert result.message is None
                    assert result.transaction_id is None
                else:  # These should fail validation
                    with pytest.raises(Exception):  # Pydantic validation error
                        await asset_agent_client.process_portfolio(sample_tier_calculation)
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, asset_agent_client, sample_tier_calculation):
        """Test exponential backoff in retry mechanism"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
            
            with patch('asyncio.sleep') as mock_sleep:
                with pytest.raises(httpx.TimeoutException):
                    await asset_agent_client.process_portfolio(sample_tier_calculation)
                
                # Verify exponential backoff delays
                sleep_calls = mock_sleep.call_args_list
                assert len(sleep_calls) == asset_agent_client.retry_attempts - 1
                
                # Check that delays increase exponentially
                for i, call in enumerate(sleep_calls):
                    expected_delay = asset_agent_client.retry_delay * (2 ** i)
                    actual_delay = call[0][0]
                    assert actual_delay == expected_delay


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.slow
class TestAssetAgentPerformance:
    """Performance tests for asset agent communication"""
    
    @pytest.fixture
    def asset_agent_client(self):
        """Fixture providing asset agent client with shorter timeouts for testing"""
        client = AssetAgentClient()
        client.timeout = 5  # Shorter timeout for tests
        return client
    
    @pytest.mark.asyncio
    async def test_response_time_under_load(self, asset_agent_client):
        """Test response time under concurrent load"""
        import time
        
        tier_calc = TierCalculation(
            T1=Decimal("1000.00"),
            T2=Decimal("2000.00"),
            T3=Decimal("500.00")
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'COMPLETED',
            'message': 'Success'
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            # Add small delay to simulate network latency
            async def mock_post(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms simulated latency
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            # Make 20 concurrent requests
            start_time = time.time()
            
            tasks = [
                asset_agent_client.process_portfolio(tier_calc)
                for _ in range(20)
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # All requests should succeed
            assert len(results) == 20
            for result in results:
                assert result.status == 'COMPLETED'
            
            # Total time should be close to the simulated latency (due to concurrency)
            # Allow some overhead for test execution
            assert total_time < 0.5  # Should complete much faster than 20 * 0.1 = 2 seconds
    
    @pytest.mark.asyncio
    async def test_timeout_handling_performance(self, asset_agent_client):
        """Test timeout handling doesn't significantly impact performance"""
        import time
        
        tier_calc = TierCalculation(
            T1=Decimal("1000.00"),
            T2=Decimal("2000.00"),
            T3=Decimal("500.00")
        )
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
            
            with patch('asyncio.sleep') as mock_sleep:
                # Mock sleep to return immediately for performance testing
                mock_sleep.return_value = asyncio.sleep(0)
                
                start_time = time.time()
                
                with pytest.raises(httpx.TimeoutException):
                    await asset_agent_client.process_portfolio(tier_calc)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Should fail quickly despite retries (since we mocked sleep)
                assert total_time < 1.0
