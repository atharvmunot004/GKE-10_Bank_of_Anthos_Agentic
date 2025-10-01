"""
Unit tests for data models
"""
import pytest
from decimal import Decimal
from datetime import datetime
from models import (
    QueueTransaction, BatchRequest, TierCalculation, 
    AssetAgentRequest, AssetAgentResponse, TransactionType, TransactionStatus
)


class TestQueueTransaction:
    """Test QueueTransaction model"""
    
    def test_valid_transaction(self):
        """Test creating a valid transaction"""
        transaction = QueueTransaction(
            uuid="test-uuid-123",
            accountid="12345678901234567890",
            tier1=Decimal("1000.50"),
            tier2=Decimal("2000.75"),
            tier3=Decimal("500.25"),
            purpose=TransactionType.INVEST
        )
        
        assert transaction.uuid == "test-uuid-123"
        assert transaction.accountid == "12345678901234567890"
        assert transaction.tier1 == Decimal("1000.50")
        assert transaction.tier2 == Decimal("2000.75")
        assert transaction.tier3 == Decimal("500.25")
        assert transaction.purpose == TransactionType.INVEST
        assert transaction.status == TransactionStatus.PENDING
    
    def test_withdrawal_transaction(self):
        """Test creating a withdrawal transaction"""
        transaction = QueueTransaction(
            uuid="test-uuid-456",
            accountid="12345678901234567890",
            tier1=Decimal("500.00"),
            tier2=Decimal("1000.00"),
            tier3=Decimal("250.00"),
            purpose=TransactionType.WITHDRAW,
            status=TransactionStatus.PROCESSING
        )
        
        assert transaction.purpose == TransactionType.WITHDRAW
        assert transaction.status == TransactionStatus.PROCESSING


class TestTierCalculation:
    """Test TierCalculation model"""
    
    def test_tier_calculation(self):
        """Test tier calculation creation"""
        calc = TierCalculation(
            T1=Decimal("1000.00"),
            T2=Decimal("2000.00"),
            T3=Decimal("500.00")
        )
        
        assert calc.T1 == Decimal("1000.00")
        assert calc.T2 == Decimal("2000.00")
        assert calc.T3 == Decimal("500.00")


class TestAssetAgentRequest:
    """Test AssetAgentRequest model"""
    
    def test_asset_agent_request(self):
        """Test asset agent request creation"""
        request = AssetAgentRequest(
            T1=Decimal("1000.00"),
            T2=Decimal("2000.00"),
            T3=Decimal("500.00")
        )
        
        assert request.T1 == Decimal("1000.00")
        assert request.T2 == Decimal("2000.00")
        assert request.T3 == Decimal("500.00")


class TestAssetAgentResponse:
    """Test AssetAgentResponse model"""
    
    def test_successful_response(self):
        """Test successful response"""
        response = AssetAgentResponse(
            status="COMPLETED",
            message="Processing successful",
            transaction_id="tx-123"
        )
        
        assert response.status == "COMPLETED"
        assert response.message == "Processing successful"
        assert response.transaction_id == "tx-123"
    
    def test_failed_response(self):
        """Test failed response"""
        response = AssetAgentResponse(
            status="FAILED",
            message="Insufficient funds"
        )
        
        assert response.status == "FAILED"
        assert response.message == "Insufficient funds"
        assert response.transaction_id is None


class TestBatchRequest:
    """Test BatchRequest model"""
    
    def test_batch_request(self):
        """Test batch request creation"""
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
        
        batch = BatchRequest(
            transactions=transactions,
            batch_id="batch-123"
        )
        
        assert len(batch.transactions) == 2
        assert batch.batch_id == "batch-123"
        assert isinstance(batch.created_at, datetime)
