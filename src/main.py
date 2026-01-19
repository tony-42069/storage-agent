"""Main application entry point."""
import os
import time
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.core.config import get_settings
from src.routes import voice
from src.routes import health
from src.utils.logger import get_logger, init_app_logging
from src.utils.metrics import record_request, record_error
from src.db.session import init_database, close_async_engine

logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    init_app_logging(settings.APP_ENV)
    
    startup_errors = []
    
    required_env_vars = [
        ('TWILIO_ACCOUNT_SID', 'Twilio Account SID'),
        ('TWILIO_AUTH_TOKEN', 'Twilio Auth Token'),
        ('TWILIO_PHONE_NUMBER', 'Twilio Phone Number'),
    ]
    
    for var_name, description in required_env_vars:
        if not os.getenv(var_name):
            startup_errors.append(f"Missing required environment variable: {var_name} ({description})")
    
    if settings.APP_ENV == "production" and not os.getenv('DATABASE_URL'):
        startup_errors.append("DATABASE_URL is required in production")
    
    if startup_errors:
        error_msg = "; ".join(startup_errors)
        logger.error(f"Startup validation failed: {error_msg}")
        raise RuntimeError(f"Configuration validation failed: {error_msg}")
    
    logger.info(f"Application started in {settings.APP_ENV} mode")
    
    if settings.APP_ENV != "testing":
        try:
            init_database()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.warning(f"Database initialization failed (will retry on first request): {e}")
    
    yield
    logger.info("Application shutdown")
    await close_async_engine()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered storage facility management system",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(voice.router, prefix="/voice", tags=["voice"])
app.include_router(health.router, prefix="", tags=["health"])


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics."""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        record_error(type(e).__name__)
        raise
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        record_request(
            endpoint=request.url.path,
            method=request.method,
            status_code=status_code,
            duration_ms=duration_ms
        )
    
    return response


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
