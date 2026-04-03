"""
RefurbAdmin AI - Main Application Entry Point

FastAPI application with middleware, error handlers, and lifespan events.
South African context (ZAR currency, SAST timezone, POPIA compliance).
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import init_db, close_db
from app.api.v1.router import router as v1_router

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

def setup_logging():
    """Configure application logging."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Create logs directory
    import os
    log_dir = os.path.dirname(settings.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(settings.log_file) if settings.log_file else logging.NullHandler(),
        ],
    )
    
    # Set third-party loggers to WARNING
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={settings.log_level}, file={settings.log_file}")
    
    return logging.getLogger(__name__)


logger = setup_logging()


# =============================================================================
# LIFESPAN EVENTS
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting RefurbAdmin AI...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Database: {'SQLite (dev)' if settings.uses_sqlite else 'PostgreSQL (prod)'}")
    logger.info(f"Timezone: {settings.timezone}")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down RefurbAdmin AI...")
    await close_db()
    logger.info("Database connections closed")


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title=settings.app_name,
    description="""
## RefurbAdmin AI - Inventory & Pricing Automation Platform

A comprehensive inventory and pricing automation platform for IT refurbishment businesses in South Africa.

### Key Features

**🏷️ Dynamic Pricing Engine**
- Real-time market data integration
- Inventory velocity-based adjustments
- Retail psychology price rounding

**📦 Inventory Management**
- Full CRUD operations
- Serial number tracking
- Status management (Intake → Diagnosis → Ready → Sold)

**🔒 POPIA Compliant**
- Encrypted customer data
- Secure API authentication
- Audit logging

### South African Context
- **Currency:** ZAR (R)
- **Timezone:** SAST (Africa/Johannesburg)
- **Compliance:** POPIA

### API Authentication
All endpoints require an API key passed in the `X-API-Key` header.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# =============================================================================
# MIDDLEWARE
# =============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing."""
    import time
    
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.3f}s"
    )
    
    return response


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """Handle request validation errors."""
    logger.warning(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "An internal error occurred",
        },
    )


# =============================================================================
# API ROUTES
# =============================================================================

# Include v1 API router
app.include_router(v1_router)


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================

@app.get(
    "/",
    tags=["Root"],
    summary="Root endpoint",
)
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "description": "Inventory & Pricing Automation Platform",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
)
async def health_check():
    """
    Health check endpoint.
    
    Returns application status and version.
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.app_env,
        "timestamp": datetime.utcnow().isoformat(),
    }


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
