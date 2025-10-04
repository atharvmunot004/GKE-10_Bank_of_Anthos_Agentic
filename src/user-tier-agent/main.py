"""
User Tier Agent - Main FastAPI Application
AI-powered financial tier allocation agent using Gemini LLM
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1.router import api_router
from app.core.middleware import add_request_id_middleware
from app.core.health import HealthChecker

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

# Setup structured logging
setup_logging()
logger = structlog.get_logger(__name__)

# Health checker instance
health_checker = HealthChecker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting User Tier Agent microservice", version=settings.VERSION)
    
    # Initialize health checker
    await health_checker.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down User Tier Agent microservice")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="User Tier Agent",
        description="AI-powered financial tier allocation agent using Gemini LLM",
        version=settings.VERSION,
        docs_url="/docs" if settings.LOG_LEVEL == "DEBUG" else None,
        redoc_url="/redoc" if settings.LOG_LEVEL == "DEBUG" else None,
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure appropriately for production
    )
    
    # Add request ID middleware
    add_request_id_middleware(app)
    
    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    
    # Metrics endpoint
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    return app


# Create app instance
app = create_app()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = await health_checker.check_health()
        if health_status["status"] == "healthy":
            return {"status": "healthy", "version": settings.VERSION}
        else:
            raise HTTPException(status_code=503, detail=health_status)
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    try:
        readiness_status = await health_checker.check_readiness()
        if readiness_status["ready"]:
            return {"ready": True, "version": settings.VERSION}
        else:
            raise HTTPException(status_code=503, detail=readiness_status)
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.LOG_LEVEL == "DEBUG"
    )
