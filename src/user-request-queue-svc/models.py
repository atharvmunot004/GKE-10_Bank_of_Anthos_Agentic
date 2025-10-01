"""
Data models for user-request-queue-svc
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class TransactionType(str, Enum):
    """Transaction type enumeration"""
    INVEST = "INVEST"
    WITHDRAW = "WITHDRAW"


class TransactionStatus(str, Enum):
    """Transaction status enumeration"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class QueueTransaction(BaseModel):
    """Queue transaction model"""
    uuid: str = Field(..., description="Unique identifier for the transaction")
    accountid: str = Field(..., description="Bank account number")
    tier1: Decimal = Field(..., description="Amount for Tier 1")
    tier2: Decimal = Field(..., description="Amount for Tier 2")
    tier3: Decimal = Field(..., description="Amount for Tier 3")
    purpose: TransactionType = Field(..., description="Transaction type")
    status: TransactionStatus = Field(default=TransactionStatus.PENDING, description="Transaction status")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    processed_at: Optional[datetime] = Field(default=None, description="Processing timestamp")


class BatchRequest(BaseModel):
    """Batch request model"""
    transactions: List[QueueTransaction] = Field(..., description="List of transactions in the batch")
    batch_id: str = Field(..., description="Unique batch identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Batch creation timestamp")


class TierCalculation(BaseModel):
    """Tier calculation result model"""
    T1: Decimal = Field(..., description="Tier 1 net amount (INVEST - WITHDRAW)")
    T2: Decimal = Field(..., description="Tier 2 net amount (INVEST - WITHDRAW)")
    T3: Decimal = Field(..., description="Tier 3 net amount (INVEST - WITHDRAW)")


class AssetAgentRequest(BaseModel):
    """Request to bank-asset-agent"""
    T1: Decimal = Field(..., description="Tier 1 amount")
    T2: Decimal = Field(..., description="Tier 2 amount")
    T3: Decimal = Field(..., description="Tier 3 amount")


class AssetAgentResponse(BaseModel):
    """Response from bank-asset-agent"""
    status: str = Field(..., description="Processing status")
    message: Optional[str] = Field(default=None, description="Optional message")
    transaction_id: Optional[str] = Field(default=None, description="Optional transaction ID")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    database_connected: bool = Field(..., description="Database connectivity status")
    external_service_available: bool = Field(..., description="External service availability")


class BatchStatusResponse(BaseModel):
    """Batch status response"""
    batch_id: str = Field(..., description="Batch identifier")
    status: str = Field(..., description="Batch processing status")
    transaction_count: int = Field(..., description="Number of transactions in batch")
    created_at: datetime = Field(..., description="Batch creation timestamp")
    processed_at: Optional[datetime] = Field(default=None, description="Batch processing timestamp")


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
