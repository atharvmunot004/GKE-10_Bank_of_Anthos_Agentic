"""
Core business logic services for user-request-queue-svc
"""
import asyncio
import httpx
from decimal import Decimal
from typing import List, Dict, Any
from datetime import datetime
import uuid as uuid_lib
import structlog

from models import (
    QueueTransaction, BatchRequest, TierCalculation, 
    AssetAgentRequest, AssetAgentResponse, TransactionType, TransactionStatus
)
from database import db_manager
from config import settings

logger = structlog.get_logger(__name__)


class TierCalculator:
    """Handles tier calculations for batch processing"""
    
    @staticmethod
    def calculate_tier_differences(transactions: List[QueueTransaction]) -> TierCalculation:
        """Calculate tier differences between INVEST and WITHDRAW transactions"""
        invest_t1 = Decimal('0')
        invest_t2 = Decimal('0')
        invest_t3 = Decimal('0')
        withdraw_t1 = Decimal('0')
        withdraw_t2 = Decimal('0')
        withdraw_t3 = Decimal('0')
        
        for transaction in transactions:
            if transaction.purpose == TransactionType.INVEST:
                invest_t1 += transaction.tier1
                invest_t2 += transaction.tier2
                invest_t3 += transaction.tier3
            elif transaction.purpose == TransactionType.WITHDRAW:
                withdraw_t1 += transaction.tier1
                withdraw_t2 += transaction.tier2
                withdraw_t3 += transaction.tier3
        
        # Calculate net differences
        t1_net = invest_t1 - withdraw_t1
        t2_net = invest_t2 - withdraw_t2
        t3_net = invest_t3 - withdraw_t3
        
        logger.info("Calculated tier differences",
                   invest_t1=float(invest_t1), invest_t2=float(invest_t2), invest_t3=float(invest_t3),
                   withdraw_t1=float(withdraw_t1), withdraw_t2=float(withdraw_t2), withdraw_t3=float(withdraw_t3),
                   net_t1=float(t1_net), net_t2=float(t2_net), net_t3=float(t3_net))
        
        return TierCalculation(T1=t1_net, T2=t2_net, T3=t3_net)


class AssetAgentClient:
    """Client for communicating with bank-asset-agent service"""
    
    def __init__(self):
        self.base_url = settings.bank_asset_agent_url
        self.timeout = settings.bank_asset_agent_timeout
        self.retry_attempts = settings.bank_asset_agent_retry_attempts
        self.retry_delay = settings.bank_asset_agent_retry_delay
    
    async def process_portfolio(self, tier_calculation: TierCalculation) -> AssetAgentResponse:
        """Send portfolio processing request to bank-asset-agent"""
        request_data = AssetAgentRequest(
            T1=tier_calculation.T1,
            T2=tier_calculation.T2,
            T3=tier_calculation.T3
        )
        
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.base_url,
                        json=request_data.model_dump()
                    )
                    response.raise_for_status()
                    
                    response_data = response.json()
                    asset_response = AssetAgentResponse(**response_data)
                    
                    logger.info("Successfully processed portfolio with bank-asset-agent",
                               attempt=attempt + 1,
                               status=asset_response.status,
                               t1=float(tier_calculation.T1),
                               t2=float(tier_calculation.T2),
                               t3=float(tier_calculation.T3))
                    
                    return asset_response
                    
            except httpx.TimeoutException:
                logger.warning("Timeout communicating with bank-asset-agent",
                              attempt=attempt + 1,
                              timeout=self.timeout)
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise
                    
            except httpx.HTTPStatusError as e:
                logger.error("HTTP error from bank-asset-agent",
                            attempt=attempt + 1,
                            status_code=e.response.status_code,
                            response_text=e.response.text)
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise
                    
            except Exception as e:
                logger.error("Unexpected error communicating with bank-asset-agent",
                            attempt=attempt + 1,
                            error=str(e))
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise
        
        # This should never be reached, but just in case
        raise Exception("Failed to communicate with bank-asset-agent after all retry attempts")
    
    async def is_available(self) -> bool:
        """Check if bank-asset-agent service is available"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url.replace('/api/v1/process-portfolio', '')}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning("Bank-asset-agent health check failed", error=str(e))
            return False


class QueueProcessor:
    """Main queue processing service"""
    
    def __init__(self):
        self.tier_calculator = TierCalculator()
        self.asset_agent_client = AssetAgentClient()
        self.is_processing = False
    
    async def process_batch(self, transactions: List[QueueTransaction]) -> bool:
        """Process a batch of transactions"""
        if not transactions:
            logger.warning("Attempted to process empty batch")
            return False
        
        batch_id = str(uuid_lib.uuid4())
        logger.info("Starting batch processing", batch_id=batch_id, transaction_count=len(transactions))
        
        try:
            # Update status to PROCESSING
            uuids = [t.uuid for t in transactions]
            await db_manager.update_batch_status(uuids, TransactionStatus.PROCESSING.value)
            
            # Calculate tier differences
            tier_calculation = self.tier_calculator.calculate_tier_differences(transactions)
            
            # Send to bank-asset-agent
            asset_response = await self.asset_agent_client.process_portfolio(tier_calculation)
            
            # Update status based on response
            final_status = TransactionStatus.COMPLETED.value if asset_response.status == "COMPLETED" else TransactionStatus.FAILED.value
            await db_manager.update_batch_status(uuids, final_status)
            
            logger.info("Batch processing completed",
                       batch_id=batch_id,
                       final_status=final_status,
                       asset_response_status=asset_response.status)
            
            return final_status == TransactionStatus.COMPLETED.value
            
        except Exception as e:
            logger.error("Batch processing failed",
                        batch_id=batch_id,
                        error=str(e))
            
            # Mark batch as failed
            try:
                uuids = [t.uuid for t in transactions]
                await db_manager.update_batch_status(uuids, TransactionStatus.FAILED.value)
            except Exception as update_error:
                logger.error("Failed to update batch status to FAILED",
                            batch_id=batch_id,
                            error=str(update_error))
            
            return False
    
    async def poll_and_process(self) -> int:
        """Poll queue and process available batches"""
        if self.is_processing:
            logger.debug("Already processing, skipping poll cycle")
            return 0
        
        self.is_processing = True
        processed_batches = 0
        
        try:
            # Check if we have enough pending requests
            pending_count = await db_manager.count_pending_requests()
            logger.debug("Current pending requests", count=pending_count)
            
            if pending_count < settings.batch_size:
                logger.debug("Not enough pending requests for batch processing",
                           pending=pending_count,
                           required=settings.batch_size)
                return 0
            
            # Fetch and process batches
            while True:
                # Fetch a batch
                batch_data = await db_manager.fetch_batch(settings.batch_size)
                if not batch_data:
                    break
                
                # Convert to QueueTransaction objects
                transactions = []
                for data in batch_data:
                    transaction = QueueTransaction(
                        uuid=data['uuid'],
                        accountid=data['accountid'],
                        tier1=data['tier1'],
                        tier2=data['tier2'],
                        tier3=data['tier3'],
                        purpose=TransactionType(data['purpose']),
                        status=TransactionStatus(data['status']),
                        created_at=data['created_at'],
                        updated_at=data['updated_at'],
                        processed_at=data['processed_at']
                    )
                    transactions.append(transaction)
                
                # Process the batch
                success = await self.process_batch(transactions)
                processed_batches += 1
                
                if not success:
                    logger.warning("Batch processing failed, stopping further processing")
                    break
                
                # Check if we should continue processing
                remaining_count = await db_manager.count_pending_requests()
                if remaining_count < settings.batch_size:
                    break
            
            logger.info("Poll and process cycle completed", processed_batches=processed_batches)
            return processed_batches
            
        except Exception as e:
            logger.error("Poll and process cycle failed", error=str(e))
            return processed_batches
        finally:
            self.is_processing = False
    
    async def start_polling(self):
        """Start continuous polling process"""
        logger.info("Starting queue polling", interval=settings.polling_interval)
        
        while True:
            try:
                await self.poll_and_process()
            except Exception as e:
                logger.error("Polling cycle error", error=str(e))
            
            await asyncio.sleep(settings.polling_interval)


# Global service instances
queue_processor = QueueProcessor()
