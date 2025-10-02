"""
Unit tests for services module
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime
import httpx

from services import TierCalculator, AssetAgentClient, QueueProcessor
from models import (
    QueueTransaction, TierCalculation, AssetAgentRequest, AssetAgentResponse,
    TransactionType, TransactionStatus
)


class TestTierCalculator:
    """Test TierCalculator service"""
    
    def test_calculate_tier_differences_balanced(self):
        """Test calculation with balanced INVEST/WITHDRAW amounts"""
        transactions = [
            QueueTransaction(
                uuid="uuid-1",
                accountid="12345678901234567890",
                tier1=Decimal("1000.00"),
                tier2=Decimal("2000.00"),
                tier3=Decimal("500.00"),
                purpose=TransactionType.INVEST
            ),
            QueueTransaction(
                uuid="uuid-2",
                accountid="12345678901234567890",
                tier1=Decimal("1000.00"),
                tier2=Decimal("2000.00"),
                tier3=Decimal("500.00"),
                purpose=TransactionType.WITHDRAW
            )
        ]
        
        result = TierCalculator.calculate_tier_differences(transactions)
        
        assert result.T1 == Decimal("0.00")
        assert result.T2 == Decimal("0.00")
        assert result.T3 == Decimal("0.00")
    
    def test_calculate_tier_differences_large_numbers(self):
        """Test calculation with large decimal numbers"""
        transactions = [
            QueueTransaction(
                uuid="uuid-1",
                accountid="12345678901234567890",
                tier1=Decimal("999999999.99999999"),
                tier2=Decimal("888888888.88888888"),
                tier3=Decimal("777777777.77777777"),
                purpose=TransactionType.INVEST
            ),
            QueueTransaction(
                uuid="uuid-2",
                accountid="12345678901234567890",
                tier1=Decimal("111111111.11111111"),
                tier2=Decimal("222222222.22222222"),
                tier3=Decimal("333333333.33333333"),
                purpose=TransactionType.WITHDRAW
            )
        ]
        
        result = TierCalculator.calculate_tier_differences(transactions)
        
        expected_t1 = Decimal("999999999.99999999") - Decimal("111111111.11111111")
        expected_t2 = Decimal("888888888.88888888") - Decimal("222222222.22222222")
        expected_t3 = Decimal("777777777.77777777") - Decimal("333333333.33333333")
        
        assert result.T1 == expected_t1
        assert result.T2 == expected_t2
        assert result.T3 == expected_t3


class TestAssetAgentClient:
    """Test AssetAgentClient service"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = AssetAgentClient()
    
    @pytest.mark.asyncio
    async def test_process_portfolio_success(self):
        """Test successful portfolio processing"""
        tier_calc = TierCalculation(
            T1=Decimal("1000.00"),
            T2=Decimal("2000.00"),
            T3=Decimal("500.00")
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "COMPLETED",
            "message": "Processing successful",
            "transaction_id": "tx-123"
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            result = await self.client.process_portfolio(tier_calc)
            
            assert result.status == "COMPLETED"
            assert result.message == "Processing successful"
            assert result.transaction_id == "tx-123"
    
    @pytest.mark.asyncio
    async def test_process_portfolio_timeout_retry(self):
        """Test timeout with retry mechanism"""
        tier_calc = TierCalculation(
            T1=Decimal("1000.00"),
            T2=Decimal("2000.00"),
            T3=Decimal("500.00")
        )
        
        # Mock first call to timeout, second to succeed
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "COMPLETED",
            "message": "Processing successful"
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.side_effect = [
                httpx.TimeoutException("Timeout"),
                mock_response
            ]
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await self.client.process_portfolio(tier_calc)
                
                assert result.status == "COMPLETED"
                assert mock_post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_portfolio_http_error(self):
        """Test HTTP error handling"""
        tier_calc = TierCalculation(
            T1=Decimal("1000.00"),
            T2=Decimal("2000.00"),
            T3=Decimal("500.00")
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_post = AsyncMock()
            mock_post.side_effect = httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            with pytest.raises(httpx.HTTPStatusError):
                await self.client.process_portfolio(tier_calc)
    
    @pytest.mark.asyncio
    async def test_is_available_success(self):
        """Test service availability check success"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await self.client.is_available()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_is_available_failure(self):
        """Test service availability check failure"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )
            
            result = await self.client.is_available()
            
            assert result is False


class TestQueueProcessor:
    """Test QueueProcessor service"""
    
    def setup_method(self):
        """Setup test processor"""
        self.processor = QueueProcessor()
    
    @pytest.mark.asyncio
    async def test_process_batch_success(self):
        """Test successful batch processing"""
        transactions = [
            QueueTransaction(
                uuid="uuid-1",
                accountid="12345678901234567890",
                tier1=Decimal("1000.00"),
                tier2=Decimal("2000.00"),
                tier3=Decimal("500.00"),
                purpose=TransactionType.INVEST
            ),
            QueueTransaction(
                uuid="uuid-2",
                accountid="12345678901234567890",
                tier1=Decimal("500.00"),
                tier2=Decimal("1000.00"),
                tier3=Decimal("250.00"),
                purpose=TransactionType.WITHDRAW
            )
        ]
        
        # Mock database operations
        with patch('database.db_manager.update_batch_status', new_callable=AsyncMock) as mock_update:
            # Mock asset agent response
            mock_response = AssetAgentResponse(
                status="COMPLETED",
                message="Success"
            )
            with patch.object(self.processor.asset_agent_client, 'process_portfolio', 
                            new_callable=AsyncMock, return_value=mock_response):
                
                result = await self.processor.process_batch(transactions)
                
                assert result is True
                # Verify database update calls
                assert mock_update.call_count == 2  # PROCESSING and COMPLETED
    
    @pytest.mark.asyncio
    async def test_process_batch_empty(self):
        """Test processing empty batch"""
        result = await self.processor.process_batch([])
        assert result is False
    
    @pytest.mark.asyncio
    async def test_process_batch_asset_agent_failure(self):
        """Test batch processing with asset agent failure"""
        transactions = [
            QueueTransaction(
                uuid="uuid-1",
                accountid="12345678901234567890",
                tier1=Decimal("1000.00"),
                tier2=Decimal("2000.00"),
                tier3=Decimal("500.00"),
                purpose=TransactionType.INVEST
            )
        ]
        
        with patch('database.db_manager.update_batch_status', new_callable=AsyncMock):
            # Mock asset agent failure
            mock_response = AssetAgentResponse(
                status="FAILED",
                message="Insufficient funds"
            )
            with patch.object(self.processor.asset_agent_client, 'process_portfolio',
                            new_callable=AsyncMock, return_value=mock_response):
                
                result = await self.processor.process_batch(transactions)
                
                assert result is False
    
    @pytest.mark.asyncio
    async def test_process_batch_exception_handling(self):
        """Test batch processing exception handling"""
        transactions = [
            QueueTransaction(
                uuid="uuid-1",
                accountid="12345678901234567890",
                tier1=Decimal("1000.00"),
                tier2=Decimal("2000.00"),
                tier3=Decimal("500.00"),
                purpose=TransactionType.INVEST
            )
        ]
        
        with patch('database.db_manager.update_batch_status', new_callable=AsyncMock) as mock_update:
            # Mock asset agent exception
            with patch.object(self.processor.asset_agent_client, 'process_portfolio',
                            new_callable=AsyncMock, side_effect=Exception("Network error")):
                
                result = await self.processor.process_batch(transactions)
                
                assert result is False
                # Verify FAILED status update was attempted
                mock_update.assert_called()
    
    @pytest.mark.asyncio
    async def test_poll_and_process_insufficient_requests(self):
        """Test polling when insufficient requests available"""
        with patch('database.db_manager.count_pending_requests', 
                  new_callable=AsyncMock, return_value=5):  # Less than batch size
            
            result = await self.processor.poll_and_process()
            
            assert result == 0  # No batches processed
    
    @pytest.mark.asyncio
    async def test_poll_and_process_success(self):
        """Test successful poll and process cycle"""
        # Mock database responses
        mock_batch_data = [
            {
                'uuid': 'uuid-1',
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
        
        with patch('database.db_manager.count_pending_requests', 
                  new_callable=AsyncMock, side_effect=[10, 0]):  # First call: enough, second: none
            with patch('database.db_manager.fetch_batch', 
                      new_callable=AsyncMock, return_value=mock_batch_data):
                with patch.object(self.processor, 'process_batch', 
                                new_callable=AsyncMock, return_value=True):
                    
                    result = await self.processor.poll_and_process()
                    
                    assert result == 1  # One batch processed
    
    @pytest.mark.asyncio
    async def test_poll_and_process_concurrent_protection(self):
        """Test concurrent processing protection"""
        self.processor.is_processing = True
        
        result = await self.processor.poll_and_process()
        
        assert result == 0  # No processing due to concurrent protection
