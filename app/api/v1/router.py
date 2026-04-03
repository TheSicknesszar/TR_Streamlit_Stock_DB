"""
RefurbAdmin AI - API v1 Router

Aggregates all v1 API endpoints.
"""

from fastapi import APIRouter

from app.api.v1.price_check import router as price_check_router
from app.api.v1.inventory import router as inventory_router

# Create v1 router
router = APIRouter(prefix="/api/v1")

# Include sub-routers
router.include_router(price_check_router)
router.include_router(inventory_router)

# Health check endpoint
@router.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
    }
