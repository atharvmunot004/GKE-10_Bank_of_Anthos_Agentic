"""
Unit tests for validation service
"""

import pytest
import uuid
from app.services.validation import RequestValidator
from app.models.schemas import PurposeEnum


class TestRequestValidator:
    """Test cases for RequestValidator"""
    
    def test_validate_allocation_request_valid(self):
        """Test validation of valid allocation request"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": "test-account-123",
            "amount": 10000.0,
            "purpose": "INVEST"
        }
        
        error = RequestValidator.validate_allocation_request(request_data)
        assert error is None
    
    def test_validate_allocation_request_missing_fields(self):
        """Test validation with missing required fields"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": "test-account-123",
            "amount": 10000.0
            # Missing "purpose"
        }
        
        error = RequestValidator.validate_allocation_request(request_data)
        assert error is not None
        assert "Missing required field" in error
    
    def test_validate_allocation_request_invalid_uuid(self):
        """Test validation with invalid UUID"""
        request_data = {
            "uuid": "invalid-uuid",
            "accountid": "test-account-123",
            "amount": 10000.0,
            "purpose": "INVEST"
        }
        
        error = RequestValidator.validate_allocation_request(request_data)
        assert error is not None
        assert "Invalid UUID format" in error
    
    def test_validate_allocation_request_empty_accountid(self):
        """Test validation with empty account ID"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": "",
            "amount": 10000.0,
            "purpose": "INVEST"
        }
        
        error = RequestValidator.validate_allocation_request(request_data)
        assert error is not None
        assert "Account ID cannot be empty" in error
    
    def test_validate_allocation_request_negative_amount(self):
        """Test validation with negative amount"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": "test-account-123",
            "amount": -1000.0,
            "purpose": "INVEST"
        }
        
        error = RequestValidator.validate_allocation_request(request_data)
        assert error is not None
        assert "Amount must be greater than zero" in error
    
    def test_validate_allocation_request_zero_amount(self):
        """Test validation with zero amount"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": "test-account-123",
            "amount": 0.0,
            "purpose": "INVEST"
        }
        
        error = RequestValidator.validate_allocation_request(request_data)
        assert error is not None
        assert "Amount must be greater than zero" in error
    
    def test_validate_allocation_request_invalid_amount(self):
        """Test validation with invalid amount format"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": "test-account-123",
            "amount": "not-a-number",
            "purpose": "INVEST"
        }
        
        error = RequestValidator.validate_allocation_request(request_data)
        assert error is not None
        assert "Invalid amount format" in error
    
    def test_validate_allocation_request_invalid_purpose(self):
        """Test validation with invalid purpose"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": "test-account-123",
            "amount": 10000.0,
            "purpose": "INVALID"
        }
        
        error = RequestValidator.validate_allocation_request(request_data)
        assert error is not None
        assert "Purpose must be either" in error
    
    def test_validate_allocation_request_case_insensitive_purpose(self):
        """Test validation with case insensitive purpose"""
        request_data = {
            "uuid": str(uuid.uuid4()),
            "accountid": "test-account-123",
            "amount": 10000.0,
            "purpose": "invest"  # lowercase
        }
        
        error = RequestValidator.validate_allocation_request(request_data)
        assert error is None
    
    def test_validate_tier_allocation_valid(self):
        """Test validation of valid tier allocation"""
        is_valid = RequestValidator.validate_tier_allocation(1000.0, 2000.0, 7000.0, 10000.0)
        assert is_valid is True
    
    def test_validate_tier_allocation_wrong_sum(self):
        """Test validation with wrong sum"""
        is_valid = RequestValidator.validate_tier_allocation(1000.0, 2000.0, 6000.0, 10000.0)
        assert is_valid is False
    
    def test_validate_tier_allocation_negative_amounts(self):
        """Test validation with negative amounts"""
        is_valid = RequestValidator.validate_tier_allocation(-100.0, 2000.0, 8000.0, 10000.0)
        assert is_valid is False
    
    def test_validate_tier_allocation_floating_point_precision(self):
        """Test validation with floating point precision issues"""
        # Test with small floating point differences
        is_valid = RequestValidator.validate_tier_allocation(1000.001, 2000.001, 6999.998, 10000.0)
        assert is_valid is True
    
    def test_sanitize_input_string(self):
        """Test input sanitization for strings"""
        data = {
            "accountid": "  test-account-123  ",
            "description": "test\x00description"
        }
        
        sanitized = RequestValidator.sanitize_input(data)
        
        assert sanitized["accountid"] == "test-account-123"
        assert sanitized["description"] == "testdescription"
    
    def test_sanitize_input_nested_dict(self):
        """Test input sanitization for nested dictionaries"""
        data = {
            "request": {
                "accountid": "  test-account-123  ",
                "amount": 10000.0
            },
            "metadata": {
                "source": "test\x00source"
            }
        }
        
        sanitized = RequestValidator.sanitize_input(data)
        
        assert sanitized["request"]["accountid"] == "test-account-123"
        assert sanitized["request"]["amount"] == 10000.0
        assert sanitized["metadata"]["source"] == "testsource"
    
    def test_sanitize_input_list(self):
        """Test input sanitization for lists"""
        data = {
            "transactions": [
                {"id": "tx-001", "amount": 100.0},
                {"id": "tx-002", "amount": 200.0}
            ],
            "tags": ["tag1", "tag2\x00"]
        }
        
        sanitized = RequestValidator.sanitize_input(data)
        
        assert len(sanitized["transactions"]) == 2
        assert sanitized["transactions"][0]["id"] == "tx-001"
        assert sanitized["tags"][1] == "tag2\x00"  # Null bytes are preserved in lists
    
    def test_sanitize_input_preserves_types(self):
        """Test that sanitization preserves data types"""
        data = {
            "string_field": "test",
            "int_field": 123,
            "float_field": 123.45,
            "bool_field": True,
            "none_field": None
        }
        
        sanitized = RequestValidator.sanitize_input(data)
        
        assert isinstance(sanitized["string_field"], str)
        assert isinstance(sanitized["int_field"], int)
        assert isinstance(sanitized["float_field"], float)
        assert isinstance(sanitized["bool_field"], bool)
        assert sanitized["none_field"] is None
