"""
Unit tests for error handler service
"""

import pytest
from fastapi import HTTPException
from httpx import HTTPError, TimeoutException, ConnectError
from unittest.mock import Mock

from app.services.error_handler import ErrorHandler
from app.models.schemas import ErrorResponse


class TestErrorHandler:
    """Test cases for ErrorHandler"""
    
    def test_handle_validation_error(self):
        """Test handling validation errors"""
        error_message = "Invalid input data"
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_validation_error(error_message, request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 400
        
        detail = exception.detail
        assert detail["error"] == "Validation Error"
        assert detail["detail"] == error_message
        assert detail["request_id"] == request_id
    
    def test_handle_tool_execution_error(self):
        """Test handling tool execution errors"""
        error_message = "Tool failed to execute"
        tool_name = "test-tool"
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_tool_execution_error(error_message, tool_name, request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 503
        
        detail = exception.detail
        assert detail["error"] == "Tool Execution Error"
        assert f"Tool '{tool_name}' failed" in detail["detail"]
        assert detail["request_id"] == request_id
    
    def test_handle_llm_error(self):
        """Test handling LLM errors"""
        error_message = "LLM service unavailable"
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_llm_error(error_message, request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 503
        
        detail = exception.detail
        assert detail["error"] == "LLM Error"
        assert "Language model error" in detail["detail"]
        assert detail["request_id"] == request_id
    
    def test_handle_database_connection_error(self):
        """Test handling database connection errors"""
        error_message = "Connection timeout"
        service_name = "ledger-db"
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_database_connection_error(error_message, service_name, request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 503
        
        detail = exception.detail
        assert detail["error"] == "Database Connection Error"
        assert f"Failed to connect to {service_name}" in detail["detail"]
        assert detail["request_id"] == request_id
    
    def test_handle_http_error(self):
        """Test handling HTTP errors"""
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = HTTPError("Not found")
        http_error.response = mock_response
        service_name = "ledger-db"
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_http_error(http_error, service_name, request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 503  # Always return 503 for external service errors
        
        detail = exception.detail
        assert detail["error"] == "External Service Error"
        assert f"HTTP error from {service_name}" in detail["detail"]
        assert detail["request_id"] == request_id
    
    def test_handle_timeout_error(self):
        """Test handling timeout errors"""
        timeout_error = TimeoutException("Request timed out")
        service_name = "ledger-db"
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_timeout_error(timeout_error, service_name, request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 504
        
        detail = exception.detail
        assert detail["error"] == "Timeout Error"
        assert f"Timeout error from {service_name}" in detail["detail"]
        assert detail["request_id"] == request_id
    
    def test_handle_connection_error(self):
        """Test handling connection errors"""
        connection_error = ConnectError("Connection refused")
        service_name = "ledger-db"
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_connection_error(connection_error, service_name, request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 503
        
        detail = exception.detail
        assert detail["error"] == "Connection Error"
        assert f"Connection error to {service_name}" in detail["detail"]
        assert detail["request_id"] == request_id
    
    def test_handle_generic_error(self):
        """Test handling generic errors"""
        generic_error = Exception("Unexpected error occurred")
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_generic_error(generic_error, request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 500
        
        detail = exception.detail
        assert detail["error"] == "Internal Server Error"
        assert detail["detail"] == "An unexpected error occurred"
        assert detail["request_id"] == request_id
    
    def test_handle_circuit_breaker_error(self):
        """Test handling circuit breaker errors"""
        service_name = "ledger-db"
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_circuit_breaker_error(service_name, request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 503
        
        detail = exception.detail
        assert detail["error"] == "Service Temporarily Unavailable"
        assert f"Circuit breaker open for {service_name}" in detail["detail"]
        assert detail["request_id"] == request_id
    
    def test_handle_rate_limit_error(self):
        """Test handling rate limit errors"""
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_rate_limit_error(request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 429
        
        detail = exception.detail
        assert detail["error"] == "Rate Limit Exceeded"
        assert detail["detail"] == "Rate limit exceeded"
        assert detail["request_id"] == request_id
    
    def test_handle_authentication_error(self):
        """Test handling authentication errors"""
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_authentication_error(request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 401
        
        detail = exception.detail
        assert detail["error"] == "Authentication Error"
        assert detail["detail"] == "Authentication failed"
        assert detail["request_id"] == request_id
    
    def test_handle_authorization_error(self):
        """Test handling authorization errors"""
        request_id = "test-request-123"
        
        exception = ErrorHandler.handle_authorization_error(request_id)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 403
        
        detail = exception.detail
        assert detail["error"] == "Authorization Error"
        assert detail["detail"] == "Access denied"
        assert detail["request_id"] == request_id
    
    def test_error_handler_without_request_id(self):
        """Test error handlers work without request ID"""
        error_message = "Test error"
        
        exception = ErrorHandler.handle_validation_error(error_message)
        
        assert isinstance(exception, HTTPException)
        assert exception.status_code == 400
        assert exception.detail["request_id"] is None
