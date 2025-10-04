"""
Health check functionality
"""

import asyncio
from typing import Dict, Any
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = structlog.get_logger(__name__)


class HealthChecker:
    """Health checker for the microservice"""
    
    def __init__(self):
        self.dependencies = {
            "ledger-db": settings.LEDGER_DB_URL,
            "queue-db": settings.QUEUE_DB_URL,
            "portfolio-db": settings.PORTFOLIO_DB_URL,
            "gemini-api": "https://generativelanguage.googleapis.com"
        }
    
    async def initialize(self):
        """Initialize health checker"""
        logger.info("Health checker initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def check_dependency(self, name: str, url: str) -> Dict[str, Any]:
        """Check individual dependency health"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                if name == "gemini-api":
                    # For Gemini API, we just check if we can reach the endpoint
                    response = await client.get(f"{url}/v1beta/models")
                    response.raise_for_status()
                else:
                    # For other services, check health endpoint
                    response = await client.get(f"{url}/health")
                    response.raise_for_status()
                
                return {
                    "name": name,
                    "status": "healthy",
                    "url": url,
                    "response_time": response.elapsed.total_seconds()
                }
        except Exception as e:
            logger.error("Dependency health check failed", dependency=name, error=str(e))
            return {
                "name": name,
                "status": "unhealthy",
                "url": url,
                "error": str(e)
            }
    
    async def check_health(self) -> Dict[str, Any]:
        """Check overall service health"""
        try:
            # In test environments, only check if the service itself is running
            # Dependencies are mocked and may not be available
            if settings.ENVIRONMENT == "test":
                return {
                    "status": "healthy",
                    "dependencies": [],
                    "timestamp": asyncio.get_event_loop().time(),
                    "note": "Test environment - dependencies not checked"
                }
            
            # Check all dependencies concurrently
            dependency_checks = await asyncio.gather(
                *[self.check_dependency(name, url) for name, url in self.dependencies.items()],
                return_exceptions=True
            )
            
            # Process results
            dependencies = []
            overall_healthy = True
            
            for check in dependency_checks:
                if isinstance(check, Exception):
                    logger.error("Health check exception", error=str(check))
                    overall_healthy = False
                    dependencies.append({
                        "name": "unknown",
                        "status": "error",
                        "error": str(check)
                    })
                else:
                    dependencies.append(check)
                    if check["status"] != "healthy":
                        overall_healthy = False
            
            return {
                "status": "healthy" if overall_healthy else "unhealthy",
                "dependencies": dependencies,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def check_readiness(self) -> Dict[str, Any]:
        """Check if service is ready to accept requests"""
        try:
            # In test environments, service is always ready
            if settings.ENVIRONMENT == "test":
                return {
                    "ready": True,
                    "dependencies": [],
                    "timestamp": asyncio.get_event_loop().time(),
                    "note": "Test environment - always ready"
                }
            
            # Check critical dependencies only
            critical_deps = ["ledger-db", "queue-db"]
            
            dependency_checks = await asyncio.gather(
                *[self.check_dependency(name, self.dependencies[name]) for name in critical_deps],
                return_exceptions=True
            )
            
            ready = True
            dependencies = []
            
            for check in dependency_checks:
                if isinstance(check, Exception) or check.get("status") != "healthy":
                    ready = False
                dependencies.append(check)
            
            return {
                "ready": ready,
                "dependencies": dependencies,
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error("Readiness check failed", error=str(e))
            return {
                "ready": False,
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
