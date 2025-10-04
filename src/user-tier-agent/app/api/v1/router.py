"""
API v1 router
"""

from fastapi import APIRouter

from app.api.v1.endpoints import allocation

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    allocation.router,
    prefix="/allocation",
    tags=["allocation"]
)
