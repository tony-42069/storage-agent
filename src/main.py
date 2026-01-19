"""Main application entry point."""
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.core.config import get_settings
from src.routes import voice
from src.utils.logger import get_logger
from src.db.session import init_database, close_async_engine

logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
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
    yield
    logger.info("Application shutdown")


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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational"
    }



# Include routers
app.include_router(voice.router, prefix="/voice", tags=["voice"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    import os
    required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER']
    missing_vars = [v for v in required_vars if not os.getenv(v)]
    
    return {
        "status": "healthy" if not missing_vars else "degraded",
        "environment": settings.APP_ENV,
        "config_valid": len(missing_vars) == 0,
        "missing_config": missing_vars if missing_vars else None
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
        "environment": settings.ENVIRONMENT,
        "config_valid": len(missing_vars) == 0,
        "missing_config": missing_vars if missing_vars else None
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
