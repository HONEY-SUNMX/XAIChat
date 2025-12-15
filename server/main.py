#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen Chat API - FastAPI Application
Main entry point for the backend API server.

Author: Generated with love by Harei-chan

Usage:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Explicitly disable CUDA before any torch imports to avoid NVML warnings
# This must be set before importing any libraries that use PyTorch
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from core.config import settings
from core.log_listener import get_log_listener, LogLevel, LogRecord, create_log_forwarder
from server.routers import chat, vision, image, multimodal
from server.models.schemas import HealthResponse, ErrorResponse


# =============================================================================
# Application Logger Setup (must be at module level, before uvicorn logs)
# =============================================================================

# Create application-specific logger for intercepted logs
app_logger = logging.getLogger("qwen.server")
app_logger.setLevel(logging.DEBUG)

# Configure output format
_app_handler = logging.StreamHandler()
_app_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
app_logger.addHandler(_app_handler)
app_logger.propagate = False  # Prevent duplicate output

# Initialize log listener immediately at module load time
# This ensures we capture uvicorn's early startup logs (before lifespan)
_log_forwarder = create_log_forwarder(app_logger)
_listener = get_log_listener()
_listener.watch_all_uvicorn(intercept=True) \
         .watch_all_watchfiles(intercept=True) \
         .watch("watchgod", intercept=True) \
         .on_any(_log_forwarder) \
         .start()



# =============================================================================
# Log Listener Callbacks (Placeholders for Future Implementation)
# =============================================================================

def on_server_reload(record: LogRecord) -> None:
    """Callback for server reload events."""
    pass  # TODO: Add logic here, e.g., notify frontend, clear cache, etc.


def on_server_error(record: LogRecord) -> None:
    """Callback for server error events."""
    pass  # TODO: Add logic here, e.g., send alerts, log to database, etc.


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Register additional callbacks (listener already started at module level)
    _listener.on_keyword("reload", on_server_reload) \
             .on_keyword("shutdown", on_server_reload) \
             .on_level(LogLevel.ERROR, on_server_error)

    # Startup
    app_logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    settings.ensure_directories()
    app_logger.info(f"Upload directory: {settings.upload_dir}")
    app_logger.info(f"Output directory: {settings.output_dir}")
    yield
    # Shutdown
    _listener.stop()
    app_logger.info("Shutting down API server...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="AI Chat API with Text, Vision, and Image Generation capabilities",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# =============================================================================
# Middleware
# =============================================================================

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.debug else None
        ).model_dump()
    )


# =============================================================================
# Routes
# =============================================================================

# Include API routers
app.include_router(
    chat.router,
    prefix="/api/chat",
    tags=["Chat"]
)

app.include_router(
    vision.router,
    prefix="/api/vision",
    tags=["Vision"]
)

app.include_router(
    image.router,
    prefix="/api/image",
    tags=["Image Generation"]
)

app.include_router(
    multimodal.router,
    prefix="/api",
    tags=["Multimodal Chat"]
)


# Static file serving for generated images and uploads
if os.path.exists(settings.output_dir):
    app.mount(
        "/outputs",
        StaticFiles(directory=settings.output_dir),
        name="outputs"
    )

if os.path.exists(settings.upload_dir):
    app.mount(
        "/uploads",
        StaticFiles(directory=settings.upload_dir),
        name="uploads"
    )


# =============================================================================
# Root Endpoints
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "endpoints": {
            "chat": "/api/chat",
            "vision": "/api/vision",
            "image": "/api/image",
            "multimodal": "/api/multimodal",
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Root"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        models={
            "chat": {
                "model_id": settings.chat_model_id,
                "filename": settings.chat_model_filename,
                "loaded": False  # Will be updated by service
            },
            "vision": {
                "model_id": settings.vision_model_id,
                "loaded": False
            },
            "image": {
                "model_id": settings.image_model_id,
                "loaded": False
            }
        }
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        access_log=settings.uvicorn_access_log,
    )
