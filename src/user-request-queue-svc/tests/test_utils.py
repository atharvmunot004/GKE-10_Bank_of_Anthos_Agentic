"""
Unit tests for utils module
"""
import pytest
from unittest.mock import patch, MagicMock
import time
from decimal import Decimal

from utils import (
    setup_logging, get_metrics, record_batch_processed, record_transactions_processed,
    record_batch_processing_time, record_queue_size, record_external_service_time,
    record_failed_batch, Timer, create_error_response, validate_tier_amounts,
    format_decimal
)


class TestMetrics:
    """Test metrics functionality"""
    
    def test_get_metrics(self):
        """Test metrics collection"""
        metrics_data = get_metrics()
        
        # Prometheus client returns bytes, decode to string
        if isinstance(metrics_data, bytes):
            metrics_data = metrics_data.decode('utf-8')
        
        assert isinstance(metrics_data, str)
        # Should contain some basic prometheus metrics
        assert "python_info" in metrics_data or "process_" in metrics_data
    
    def test_record_batch_processed(self):
        """Test batch processed metric recording"""
        # This should not raise an exception
        record_batch_processed("COMPLETED", 1)
        record_batch_processed("FAILED", 2)
    
    def test_record_transactions_processed(self):
        """Test transactions processed metric recording"""
        record_transactions_processed("COMPLETED", 10)
        record_transactions_processed("FAILED", 5)
    
    def test_record_batch_processing_time(self):
        """Test batch processing time recording"""
        record_batch_processing_time("COMPLETED", 1.5)
        record_batch_processing_time("FAILED", 0.8)
    
    def test_record_queue_size(self):
        """Test queue size recording"""
        record_queue_size(25)
        record_queue_size(0)
    
    def test_record_external_service_time(self):
        """Test external service time recording"""
        record_external_service_time("bank-asset-agent", "success", 2.3)
        record_external_service_time("bank-asset-agent", "timeout", 30.0)
    
    def test_record_failed_batch(self):
        """Test failed batch recording"""
        record_failed_batch("database_error", 1)
        record_failed_batch("external_service_error", 2)


class TestTimer:
    """Test Timer context manager"""
    
    def test_timer_context_manager(self):
        """Test Timer as context manager"""
        mock_metric_func = MagicMock()
        
        with Timer(mock_metric_func, "test_status") as timer:
            time.sleep(0.01)  # Small delay
        
        # Verify the metric function was called with duration
        mock_metric_func.assert_called_once()
        call_args = mock_metric_func.call_args
        assert "test_status" in call_args[0]
        assert "duration" in call_args[1]
        assert call_args[1]["duration"] > 0
    
    def test_timer_with_exception(self):
        """Test Timer behavior when exception occurs"""
        mock_metric_func = MagicMock()
        
        try:
            with Timer(mock_metric_func, "test_status"):
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Timer should still record the duration even with exception
        mock_metric_func.assert_called_once()
    
    def test_timer_multiple_args(self):
        """Test Timer with multiple arguments"""
        mock_metric_func = MagicMock()
        
        with Timer(mock_metric_func, "arg1", "arg2", kwarg1="value1"):
            time.sleep(0.01)
        
        call_args = mock_metric_func.call_args
        assert "arg1" in call_args[0]
        assert "arg2" in call_args[0]
        assert "kwarg1" in call_args[1]
        assert call_args[1]["kwarg1"] == "value1"
        assert "duration" in call_args[1]


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_create_error_response(self):
        """Test error response creation"""
        response = create_error_response("Test error", "Test detail")
        
        assert response["error"] == "Test error"
        assert response["detail"] == "Test detail"
        assert "timestamp" in response
        assert isinstance(response["timestamp"], float)
    
    def test_create_error_response_no_detail(self):
        """Test error response creation without detail"""
        response = create_error_response("Test error")
        
        assert response["error"] == "Test error"
        assert response["detail"] is None
        assert "timestamp" in response
    
    def test_validate_tier_amounts_valid(self):
        """Test tier amounts validation - valid amounts"""
        assert validate_tier_amounts(1000.0, 2000.0, 500.0) is True
        assert validate_tier_amounts(0.0, 0.0, 0.0) is True
        assert validate_tier_amounts(0.01, 0.02, 0.03) is True
    
    def test_validate_tier_amounts_invalid(self):
        """Test tier amounts validation - invalid amounts"""
        assert validate_tier_amounts(-1.0, 2000.0, 500.0) is False
        assert validate_tier_amounts(1000.0, -1.0, 500.0) is False
        assert validate_tier_amounts(1000.0, 2000.0, -1.0) is False
        assert validate_tier_amounts(-1.0, -1.0, -1.0) is False
    
    def test_format_decimal_with_decimal(self):
        """Test decimal formatting with Decimal object"""
        decimal_value = Decimal("1234.56789012")
        result = format_decimal(decimal_value)
        
        assert result == "1234.56789012"
    
    def test_format_decimal_with_float(self):
        """Test decimal formatting with float"""
        float_value = 1234.5678
        result = format_decimal(float_value)
        
        assert result == "1234.5678"
    
    def test_format_decimal_with_string(self):
        """Test decimal formatting with string"""
        string_value = "1234.5678"
        result = format_decimal(string_value)
        
        assert result == "1234.5678"
    
    def test_format_decimal_with_int(self):
        """Test decimal formatting with integer"""
        int_value = 1234
        result = format_decimal(int_value)
        
        assert result == "1234"


class TestLogging:
    """Test logging setup"""
    
    def test_setup_logging_default(self):
        """Test logging setup with default level"""
        # This should not raise an exception
        setup_logging()
    
    def test_setup_logging_custom_level(self):
        """Test logging setup with custom level"""
        setup_logging("DEBUG")
        setup_logging("WARNING")
        setup_logging("ERROR")
    
    @patch('structlog.configure')
    def test_setup_logging_configuration(self, mock_configure):
        """Test logging configuration parameters"""
        setup_logging("INFO")
        
        mock_configure.assert_called_once()
        call_kwargs = mock_configure.call_args[1]
        
        assert "processors" in call_kwargs
        assert "context_class" in call_kwargs
        assert "logger_factory" in call_kwargs
        assert "wrapper_class" in call_kwargs
        assert "cache_logger_on_first_use" in call_kwargs
        
        # Verify some processors are included
        processors = call_kwargs["processors"]
        assert len(processors) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_timer_zero_duration(self):
        """Test Timer with very short duration"""
        mock_metric_func = MagicMock()
        
        with Timer(mock_metric_func, "test"):
            pass  # No delay
        
        mock_metric_func.assert_called_once()
        call_args = mock_metric_func.call_args
        assert call_args[1]["duration"] >= 0
    
    def test_validate_tier_amounts_edge_values(self):
        """Test tier validation with edge values"""
        # Very small positive values
        assert validate_tier_amounts(0.000001, 0.000001, 0.000001) is True
        
        # Very large values
        assert validate_tier_amounts(999999999.99, 999999999.99, 999999999.99) is True
        
        # Mixed valid/invalid
        assert validate_tier_amounts(0.0, 1000.0, -0.000001) is False
    
    def test_format_decimal_edge_cases(self):
        """Test decimal formatting edge cases"""
        # Very small decimal
        small_decimal = Decimal("0.00000001")
        assert format_decimal(small_decimal) == "0.00000001"
        
        # Very large decimal
        large_decimal = Decimal("999999999.99999999")
        assert format_decimal(large_decimal) == "999999999.99999999"
        
        # Zero
        zero_decimal = Decimal("0")
        result = format_decimal(zero_decimal)
        assert result == "0.00000000" or result == "0"  # Accept both formats
        
        # Negative (though not expected in our use case)
        negative_decimal = Decimal("-1234.5678")
        result = format_decimal(negative_decimal)
        assert result.startswith("-1234.5678")  # Accept formatting variations
    
    def test_create_error_response_special_characters(self):
        """Test error response with special characters"""
        response = create_error_response(
            "Error with special chars: áéíóú", 
            "Detail with symbols: @#$%^&*()"
        )
        
        assert "áéíóú" in response["error"]
        assert "@#$%^&*()" in response["detail"]
    
    def test_metrics_with_special_labels(self):
        """Test metrics recording with special label values"""
        # Should handle various status values
        record_batch_processed("COMPLETED_WITH_WARNINGS", 1)
        record_batch_processed("FAILED_TIMEOUT", 1)
        record_external_service_time("service-with-dashes", "success_partial", 1.0)
