"""
Main FastAPI application for user-request-queue-svc
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from datetime import datetime
import structlog

from config import settings
from models import HealthResponse, BatchStatusResponse, ErrorResponse
from database import db_manager
from services import queue_processor
from utils import setup_logging, get_metrics, record_queue_size

# Setup logging
setup_logging(settings.log_level)
logger = structlog.get_logger(__name__)

# Global polling task
polling_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting user-request-queue-svc", version="1.0.0")
    
    # Initialize database
    await db_manager.initialize()
    
    # Start background polling
    global polling_task
    polling_task = asyncio.create_task(queue_processor.start_polling())
    
    logger.info("Service startup completed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down user-request-queue-svc")
    
    # Stop polling
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    
    # Close database connections
    await db_manager.close()
    
    logger.info("Service shutdown completed")


# Create FastAPI app
app = FastAPI(
    title="User Request Queue Service",
    description="Microservice for polling and processing queue transactions",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connectivity
        db_connected = await db_manager.is_connected()
        
        # Check external service availability
        external_available = await queue_processor.asset_agent_client.is_available()
        
        # Determine overall health
        overall_status = "healthy" if db_connected and external_available else "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            database_connected=db_connected,
            external_service_available=external_available
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="unhealthy",
            database_connected=False,
            external_service_available=False
        )


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    try:
        db_connected = await db_manager.is_connected()
        if db_connected:
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Database not connected")
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    try:
        # Update queue size metric
        queue_size = await db_manager.count_pending_requests()
        record_queue_size(queue_size)
        
        metrics_data = get_metrics()
        return PlainTextResponse(metrics_data, media_type="text/plain")
    except Exception as e:
        logger.error("Metrics collection failed", error=str(e))
        raise HTTPException(status_code=500, detail="Metrics collection failed")


@app.post("/api/v1/poll")
async def force_poll(background_tasks: BackgroundTasks):
    """Manually trigger queue polling"""
    try:
        logger.info("Manual poll triggered")
        background_tasks.add_task(queue_processor.poll_and_process)
        return {"message": "Polling triggered", "timestamp": datetime.utcnow()}
    except Exception as e:
        logger.error("Manual poll failed", error=str(e))
        raise HTTPException(status_code=500, detail="Polling failed")


@app.get("/api/v1/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """Get batch processing status"""
    try:
        # This is a simplified implementation
        # In a real scenario, you'd track batch status in a separate table
        logger.info("Batch status requested", batch_id=batch_id)
        
        # For now, return a mock response
        return BatchStatusResponse(
            batch_id=batch_id,
            status="unknown",
            transaction_count=0,
            created_at=datetime.utcnow()
        )
    except Exception as e:
        logger.error("Failed to get batch status", error=str(e), batch_id=batch_id)
        raise HTTPException(status_code=500, detail="Failed to get batch status")


@app.get("/api/v1/queue/stats")
async def get_queue_stats():
    """Get queue statistics"""
    try:
        pending_count = await db_manager.count_pending_requests()
        
        return {
            "pending_requests": pending_count,
            "batch_size": settings.batch_size,
            "polling_interval": settings.polling_interval,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error("Failed to get queue stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get queue stats")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return ErrorResponse(
        error="Internal server error",
        detail="An unexpected error occurred"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        log_level=settings.log_level.lower(),
        reload=False
    )
