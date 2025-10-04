"""
Request validation service
"""

import uuid
from typing import Optional
import structlog

from app.models.schemas import TierAllocationRequest, PurposeEnum

logger = structlog.get_logger(__name__)


class RequestValidator:
    """Request validation service"""
    
    @staticmethod
    def validate_allocation_request(request_data: dict) -> Optional[str]:
        """
        Validate tier allocation request data
        
        Args:
            request_data: Request data dictionary
            
        Returns:
            Error message if validation fails, None if valid
        """
        try:
            # Check required fields
            required_fields = ['uuid', 'accountid', 'amount', 'purpose']
            for field in required_fields:
                if field not in request_data:
                    return f"Missing required field: {field}"
            
            # Validate UUID
            try:
                uuid.UUID(request_data['uuid'])
            except (ValueError, TypeError):
                return "Invalid UUID format"
            
            # Validate account ID
            accountid = request_data.get('accountid', '').strip()
            if not accountid:
                return "Account ID cannot be empty"
            
            # Validate amount
            try:
                amount = float(request_data['amount'])
                if amount <= 0:
                    return "Amount must be greater than zero"
            except (ValueError, TypeError):
                return "Invalid amount format"
            
            # Validate purpose
            purpose = request_data.get('purpose', '').upper()
            if purpose not in [PurposeEnum.INVEST.value, PurposeEnum.WITHDRAW.value]:
                return f"Purpose must be either '{PurposeEnum.INVEST.value}' or '{PurposeEnum.WITHDRAW.value}'"
            
            return None
            
        except Exception as e:
            logger.error("Validation error", error=str(e))
            return f"Validation error: {str(e)}"
    
    @staticmethod
    def validate_tier_allocation(tier1: float, tier2: float, tier3: float, total_amount: float) -> bool:
        """
        Validate that tier allocation sums to total amount
        
        Args:
            tier1: Tier 1 amount
            tier2: Tier 2 amount
            tier3: Tier 3 amount
            total_amount: Total amount to allocate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check for negative amounts
            if tier1 < 0 or tier2 < 0 or tier3 < 0:
                logger.warning("Negative tier amounts detected", tier1=tier1, tier2=tier2, tier3=tier3)
                return False
            
            # Check if sum equals total amount (with small tolerance for floating point)
            calculated_total = tier1 + tier2 + tier3
            if abs(calculated_total - total_amount) > 0.01:
                logger.warning(
                    "Tier allocation sum mismatch",
                    calculated_total=calculated_total,
                    expected_total=total_amount
                )
                return False
            
            return True
            
        except Exception as e:
            logger.error("Tier allocation validation error", error=str(e))
            return False
    
    @staticmethod
    def sanitize_input(data: dict) -> dict:
        """
        Sanitize input data to prevent injection attacks
        
        Args:
            data: Input data dictionary
            
        Returns:
            Sanitized data dictionary
        """
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Remove potentially dangerous characters
                sanitized[key] = value.strip().replace('\x00', '')
            elif isinstance(value, (int, float)):
                sanitized[key] = value
            elif isinstance(value, dict):
                sanitized[key] = RequestValidator.sanitize_input(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    RequestValidator.sanitize_input(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
