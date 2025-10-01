"""
Unit tests for tier calculator
"""
import pytest
from decimal import Decimal
from services import TierCalculator
from models import QueueTransaction, TransactionType


class TestTierCalculator:
    """Test TierCalculator functionality"""
    
    def test_calculate_tier_differences_invest_only(self):
        """Test calculation with only INVEST transactions"""
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
                purpose=TransactionType.INVEST
            )
        ]
        
        result = TierCalculator.calculate_tier_differences(transactions)
        
        assert result.T1 == Decimal("1500.00")  # 1000 + 500
        assert result.T2 == Decimal("3000.00")  # 2000 + 1000
        assert result.T3 == Decimal("750.00")   # 500 + 250
    
    def test_calculate_tier_differences_withdraw_only(self):
        """Test calculation with only WITHDRAW transactions"""
        transactions = [
            QueueTransaction(
                uuid="uuid-1",
                accountid="12345678901234567890",
                tier1=Decimal("1000.00"),
                tier2=Decimal("2000.00"),
                tier3=Decimal("500.00"),
                purpose=TransactionType.WITHDRAW
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
        
        result = TierCalculator.calculate_tier_differences(transactions)
        
        assert result.T1 == Decimal("-1500.00")  # -(1000 + 500)
        assert result.T2 == Decimal("-3000.00")  # -(2000 + 1000)
        assert result.T3 == Decimal("-750.00")   # -(500 + 250)
    
    def test_calculate_tier_differences_mixed(self):
        """Test calculation with mixed INVEST and WITHDRAW transactions"""
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
                tier1=Decimal("300.00"),
                tier2=Decimal("600.00"),
                tier3=Decimal("150.00"),
                purpose=TransactionType.WITHDRAW
            ),
            QueueTransaction(
                uuid="uuid-3",
                accountid="12345678901234567890",
                tier1=Decimal("200.00"),
                tier2=Decimal("400.00"),
                tier3=Decimal("100.00"),
                purpose=TransactionType.INVEST
            )
        ]
        
        result = TierCalculator.calculate_tier_differences(transactions)
        
        # INVEST: 1000 + 200 = 1200, WITHDRAW: 300, Net: 1200 - 300 = 900
        assert result.T1 == Decimal("900.00")
        # INVEST: 2000 + 400 = 2400, WITHDRAW: 600, Net: 2400 - 600 = 1800
        assert result.T2 == Decimal("1800.00")
        # INVEST: 500 + 100 = 600, WITHDRAW: 150, Net: 600 - 150 = 450
        assert result.T3 == Decimal("450.00")
    
    def test_calculate_tier_differences_empty_list(self):
        """Test calculation with empty transaction list"""
        transactions = []
        
        result = TierCalculator.calculate_tier_differences(transactions)
        
        assert result.T1 == Decimal("0")
        assert result.T2 == Decimal("0")
        assert result.T3 == Decimal("0")
    
    def test_calculate_tier_differences_zero_amounts(self):
        """Test calculation with zero amounts"""
        transactions = [
            QueueTransaction(
                uuid="uuid-1",
                accountid="12345678901234567890",
                tier1=Decimal("0.00"),
                tier2=Decimal("0.00"),
                tier3=Decimal("0.00"),
                purpose=TransactionType.INVEST
            ),
            QueueTransaction(
                uuid="uuid-2",
                accountid="12345678901234567890",
                tier1=Decimal("0.00"),
                tier2=Decimal("0.00"),
                tier3=Decimal("0.00"),
                purpose=TransactionType.WITHDRAW
            )
        ]
        
        result = TierCalculator.calculate_tier_differences(transactions)
        
        assert result.T1 == Decimal("0.00")
        assert result.T2 == Decimal("0.00")
        assert result.T3 == Decimal("0.00")
    
    def test_calculate_tier_differences_decimal_precision(self):
        """Test calculation with decimal precision"""
        transactions = [
            QueueTransaction(
                uuid="uuid-1",
                accountid="12345678901234567890",
                tier1=Decimal("1000.12345678"),
                tier2=Decimal("2000.98765432"),
                tier3=Decimal("500.55555555"),
                purpose=TransactionType.INVEST
            ),
            QueueTransaction(
                uuid="uuid-2",
                accountid="12345678901234567890",
                tier1=Decimal("100.11111111"),
                tier2=Decimal("200.22222222"),
                tier3=Decimal("50.33333333"),
                purpose=TransactionType.WITHDRAW
            )
        ]
        
        result = TierCalculator.calculate_tier_differences(transactions)
        
        expected_t1 = Decimal("1000.12345678") - Decimal("100.11111111")
        expected_t2 = Decimal("2000.98765432") - Decimal("200.22222222")
        expected_t3 = Decimal("500.55555555") - Decimal("50.33333333")
        
        assert result.T1 == expected_t1
        assert result.T2 == expected_t2
        assert result.T3 == expected_t3
