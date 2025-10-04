"""
Allocation endpoints
"""

from typing import Dict, Any
import structlog
from fastapi import APIRouter, HTTPException, Request, Depends

from app.models.schemas import (
    TierAllocationRequest,
    TierAllocationResponse,
    ErrorResponse
)
from app.services.agent import tier_allocation_agent
from app.services.validation import RequestValidator
from app.services.error_handler import ErrorHandler

logger = structlog.get_logger(__name__)
router = APIRouter()


async def get_request_id(request: Request) -> str:
    """Get request ID from request state"""
    return getattr(request.state, 'request_id', 'unknown')


@router.post("/allocate-tiers", response_model=TierAllocationResponse)
async def allocate_tiers(
    request_data: TierAllocationRequest,
    request: Request,
    request_id: str = Depends(get_request_id)
) -> TierAllocationResponse:
    """
    Allocate tiers for investment or withdrawal request
    
    This endpoint processes tier allocation requests using AI-powered analysis
    of user transaction history to determine optimal tier distribution.
    """
    try:
        logger.info(
            "Tier allocation request received",
            request_id=request_id,
            uuid=request_data.uuid,
            accountid=request_data.accountid,
            amount=request_data.amount,
            purpose=request_data.purpose
        )
        
        # Validate request data
        validation_error = RequestValidator.validate_allocation_request(request_data.model_dump())
        if validation_error:
            raise ErrorHandler.handle_validation_error(validation_error, request_id)
        
        # Sanitize input
        sanitized_data = RequestValidator.sanitize_input(request_data.model_dump())
        
        # Create validated request object
        validated_request = TierAllocationRequest(**sanitized_data)
        
        # Check if user has transaction history
        # For now, we'll always try to get transaction history
        # In a real implementation, you might check if the user is new first
        
        try:
            # Get tier allocation from agent
            allocation = await tier_allocation_agent.allocate_tiers(validated_request)
            
            # Validate tier allocation
            if not RequestValidator.validate_tier_allocation(
                allocation.tier1, allocation.tier2, allocation.tier3, validated_request.amount
            ):
                logger.warning(
                    "Invalid tier allocation from agent, using default",
                    request_id=request_id,
                    uuid=validated_request.uuid
                )
                allocation = await tier_allocation_agent.get_default_allocation(validated_request.amount)
            
            logger.info(
                "Tier allocation completed successfully",
                request_id=request_id,
                uuid=validated_request.uuid,
                allocation=allocation.model_dump()
            )
            
            return TierAllocationResponse(
                success=True,
                allocation=allocation,
                reasoning="AI-powered tier allocation based on transaction history analysis",
                request_id=request_id
            )
            
        except Exception as agent_error:
            logger.error(
                "Agent allocation failed, using default allocation",
                request_id=request_id,
                uuid=validated_request.uuid,
                error=str(agent_error)
            )
            
            # Fallback to default allocation
            try:
                allocation = await tier_allocation_agent.get_default_allocation(validated_request.amount)
                
                return TierAllocationResponse(
                    success=True,
                    allocation=allocation,
                    reasoning="Default tier allocation used due to agent failure",
                    request_id=request_id
                )
            except Exception as fallback_error:
                raise ErrorHandler.handle_generic_error(fallback_error, request_id)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "Unexpected error in tier allocation",
            request_id=request_id,
            error=str(e)
        )
        raise ErrorHandler.handle_generic_error(e, request_id)


@router.get("/allocate-tiers/{accountid}/default")
async def get_default_allocation(
    accountid: str,
    amount: float,
    request: Request,
    request_id: str = Depends(get_request_id)
) -> TierAllocationResponse:
    """
    Get default tier allocation for a given amount
    
    This endpoint returns the default tier allocation without analyzing
    transaction history. Useful for new users or when agent is unavailable.
    """
    try:
        logger.info(
            "Default allocation request received",
            request_id=request_id,
            accountid=accountid,
            amount=amount
        )
        
        # Validate inputs
        if not accountid.strip():
            raise ErrorHandler.handle_validation_error("Account ID cannot be empty", request_id)
        
        if amount <= 0:
            raise ErrorHandler.handle_validation_error("Amount must be greater than zero", request_id)
        
        # Get default allocation
        allocation = await tier_allocation_agent.get_default_allocation(amount)
        
        logger.info(
            "Default allocation completed",
            request_id=request_id,
            accountid=accountid,
            allocation=allocation.model_dump()
        )
        
        return TierAllocationResponse(
            success=True,
            allocation=allocation,
            reasoning="Default tier allocation for new users or when transaction history is unavailable",
            request_id=request_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error in default allocation",
            request_id=request_id,
            error=str(e)
        )
        raise ErrorHandler.handle_generic_error(e, request_id)
