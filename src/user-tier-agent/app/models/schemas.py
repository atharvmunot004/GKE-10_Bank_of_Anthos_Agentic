"""
Pydantic models for request/response schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class PurposeEnum(str, Enum):
    """Purpose enumeration for allocation requests"""
    INVEST = "INVEST"
    WITHDRAW = "WITHDRAW"


class TierAllocationRequest(BaseModel):
    """Request model for tier allocation"""
    uuid: str = Field(..., description="Unique request identifier")
    accountid: str = Field(..., description="Account identifier")
    amount: float = Field(..., gt=0, description="Amount to allocate (must be positive)")
    purpose: PurposeEnum = Field(..., description="Purpose of allocation")
    
    @field_validator('uuid')
    @classmethod
    def validate_uuid(cls, v):
        """Validate UUID format"""
        import uuid
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('Invalid UUID format')
    
    @field_validator('accountid')
    @classmethod
    def validate_accountid(cls, v):
        """Validate account ID"""
        if not v or not v.strip():
            raise ValueError('Account ID cannot be empty')
        return v.strip()


class TierAllocation(BaseModel):
    """Tier allocation model"""
    tier1: float = Field(..., ge=0, description="Tier 1 allocation amount")
    tier2: float = Field(..., ge=0, description="Tier 2 allocation amount")
    tier3: float = Field(..., ge=0, description="Tier 3 allocation amount")
    
    @field_validator('tier1', 'tier2', 'tier3')
    @classmethod
    def validate_tier_amounts(cls, v):
        """Validate tier amounts are non-negative"""
        if v < 0:
            raise ValueError('Tier amounts must be non-negative')
        return v


class TierAllocationResponse(BaseModel):
    """Response model for tier allocation"""
    success: bool = Field(..., description="Whether allocation was successful")
    allocation: Optional[TierAllocation] = Field(None, description="Tier allocation")
    reasoning: Optional[str] = Field(None, description="Reasoning for allocation")
    error: Optional[str] = Field(None, description="Error message if failed")
    request_id: Optional[str] = Field(None, description="Request identifier")


class Transaction(BaseModel):
    """Transaction model"""
    transaction_id: str = Field(..., description="Transaction identifier")
    from_acct: str = Field(..., description="Source account")
    to_acct: str = Field(..., description="Destination account")
    from_route: str = Field(..., description="Source routing")
    to_route: str = Field(..., description="Destination routing")
    amount: float = Field(..., description="Transaction amount")
    timestamp: str = Field(..., description="Transaction timestamp")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
    request_id: Optional[str] = Field(None, description="Request identifier")


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Service version")
    dependencies: Optional[List[Dict[str, Any]]] = Field(None, description="Dependency status")


class ReadinessResponse(BaseModel):
    """Readiness check response model"""
    ready: bool = Field(..., description="Readiness status")
    version: str = Field(..., description="Service version")
    dependencies: Optional[List[Dict[str, Any]]] = Field(None, description="Dependency status")
