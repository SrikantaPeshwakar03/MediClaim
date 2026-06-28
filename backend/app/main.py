"""
FastAPI Main Application

Entry point for the MediClaim API server.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from .config import settings
from .api.routes import router
from .exceptions import MediClaimException
from .loggers import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"API prefix: {settings.API_V1_PREFIX}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Pre-load services (singleton initialization)
    try:
        from .services import get_policy_engine, get_ocr_service, get_llm_service
        from .agents.orchestrator import get_orchestrator
        
        logger.info("Initializing services...")
        get_policy_engine()
        get_ocr_service()
        get_llm_service()
        get_orchestrator()
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Service initialization error: {e}")
        # Continue anyway - errors will be caught during request handling
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered health insurance claims adjudication system",
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"status={response.status_code} time={process_time:.3f}s"
    )
    
    return response


# Exception handlers
@app.exception_handler(MediClaimException)
async def mediclaim_exception_handler(request: Request, exc: MediClaimException):
    """Handle custom MediClaim exceptions"""
    logger.error(f"MediClaim exception: {exc.message}")
    
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": exc.user_message,
            "details": exc.details
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": {"error": str(exc)} if settings.DEBUG else {}
        }
    )


# Include routers
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health"
    }


if __name__ == "__main__":
    import os
    import uvicorn

    # Railway (and most PaaS) inject the port to bind to via $PORT.
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG
    )
