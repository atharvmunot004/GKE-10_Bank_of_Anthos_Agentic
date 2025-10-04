"""
Centralized error handling service
"""

from typing import Dict, Any, Optional
import structlog
from fastapi import HTTPException
from httpx import HTTPError, TimeoutException, ConnectError
# BaseException is a built-in Python exception class

from app.models.schemas import ErrorResponse

logger = structlog.get_logger(__name__)


class ErrorHandler:
    """Centralized error handling service"""
    
    @staticmethod
    def handle_validation_error(error_message: str, request_id: Optional[str] = None) -> HTTPException:
        """Handle validation errors"""
        logger.warning("Validation error", error=error_message, request_id=request_id)
        return HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="Validation Error",
                detail=error_message,
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_tool_execution_error(error_message: str, tool_name: str, request_id: Optional[str] = None) -> HTTPException:
        """Handle tool execution errors"""
        logger.error("Tool execution error", tool_name=tool_name, error=error_message, request_id=request_id)
        return HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="Tool Execution Error",
                detail=f"Tool '{tool_name}' failed: {error_message}",
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_llm_error(error_message: str, request_id: Optional[str] = None) -> HTTPException:
        """Handle LLM errors"""
        logger.error("LLM error", error=error_message, request_id=request_id)
        return HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="LLM Error",
                detail=f"Language model error: {error_message}",
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_database_connection_error(error_message: str, service_name: str, request_id: Optional[str] = None) -> HTTPException:
        """Handle database connection errors"""
        logger.error("Database connection error", service=service_name, error=error_message, request_id=request_id)
        return HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="Database Connection Error",
                detail=f"Failed to connect to {service_name}: {error_message}",
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_http_error(error: HTTPError, service_name: str, request_id: Optional[str] = None) -> HTTPException:
        """Handle HTTP errors from external services"""
        error_message = f"HTTP error from {service_name}: {str(error)}"
        logger.error("HTTP error", service=service_name, error=str(error), request_id=request_id)
        
        status_code = 503
        if hasattr(error, 'response') and error.response:
            status_code = error.response.status_code
        
        return HTTPException(
            status_code=503,  # Always return 503 for external service errors
            detail=ErrorResponse(
                error="External Service Error",
                detail=error_message,
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_timeout_error(error: TimeoutException, service_name: str, request_id: Optional[str] = None) -> HTTPException:
        """Handle timeout errors"""
        error_message = f"Timeout error from {service_name}: {str(error)}"
        logger.error("Timeout error", service=service_name, error=str(error), request_id=request_id)
        
        return HTTPException(
            status_code=504,
            detail=ErrorResponse(
                error="Timeout Error",
                detail=error_message,
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_connection_error(error: ConnectError, service_name: str, request_id: Optional[str] = None) -> HTTPException:
        """Handle connection errors"""
        error_message = f"Connection error to {service_name}: {str(error)}"
        logger.error("Connection error", service=service_name, error=str(error), request_id=request_id)
        
        return HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="Connection Error",
                detail=error_message,
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_generic_error(error: Exception, request_id: Optional[str] = None) -> HTTPException:
        """Handle generic errors"""
        error_message = str(error)
        logger.error("Generic error", error=error_message, request_id=request_id)
        
        return HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="Internal Server Error",
                detail="An unexpected error occurred",
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_circuit_breaker_error(service_name: str, request_id: Optional[str] = None) -> HTTPException:
        """Handle circuit breaker errors"""
        error_message = f"Circuit breaker open for {service_name}"
        logger.warning("Circuit breaker error", service=service_name, request_id=request_id)
        
        return HTTPException(
            status_code=503,
            detail=ErrorResponse(
                error="Service Temporarily Unavailable",
                detail=error_message,
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_rate_limit_error(request_id: Optional[str] = None) -> HTTPException:
        """Handle rate limit errors"""
        error_message = "Rate limit exceeded"
        logger.warning("Rate limit error", request_id=request_id)
        
        return HTTPException(
            status_code=429,
            detail=ErrorResponse(
                error="Rate Limit Exceeded",
                detail=error_message,
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_authentication_error(request_id: Optional[str] = None) -> HTTPException:
        """Handle authentication errors"""
        error_message = "Authentication failed"
        logger.warning("Authentication error", request_id=request_id)
        
        return HTTPException(
            status_code=401,
            detail=ErrorResponse(
                error="Authentication Error",
                detail=error_message,
                request_id=request_id
            ).model_dump()
        )
    
    @staticmethod
    def handle_authorization_error(request_id: Optional[str] = None) -> HTTPException:
        """Handle authorization errors"""
        error_message = "Access denied"
        logger.warning("Authorization error", request_id=request_id)
        
        return HTTPException(
            status_code=403,
            detail=ErrorResponse(
                error="Authorization Error",
                detail=error_message,
                request_id=request_id
            ).model_dump()
        )
