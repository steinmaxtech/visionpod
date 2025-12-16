"""SteinMax Vision Cloud - Main Application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import close_db, init_db
from app.routers import (
    devices_router,
    events_router,
    plates_router,
    properties_router,
    sync_router,
    webhooks_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting SteinMax Vision Cloud...")
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="SteinMax Vision Cloud",
    description="Vehicle Access Control Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - configure for your frontend domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # Add your production domains here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy", "version": "0.1.0"}


# Mount routers
app.include_router(properties_router, prefix=settings.api_prefix)
app.include_router(devices_router, prefix=settings.api_prefix)
app.include_router(plates_router, prefix=settings.api_prefix)
app.include_router(events_router, prefix=settings.api_prefix)
app.include_router(webhooks_router, prefix=settings.api_prefix)
app.include_router(sync_router, prefix=settings.api_prefix)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "SteinMax Vision Cloud",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
