"""Main application entry point."""
import os
import time
import uvicorn
from fastapi import FastAPI, Request
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.core.config import get_settings
from src.routes import voice, health
from src.auth import routes as auth_routes
from src.routes.v1 import router as v1_router
from src.routes import v1 as api_v1
from src.utils.logger import get_logger, init_app_logging
from src.utils.metrics import record_request, record_error
from src.utils.alerting import init_alerting, send_alert, AlertLevel
from src.middleware.rate_limit import rate_limit_middleware
from src.routes import voice
from src.routes import health
from src.utils.logger import get_logger, init_app_logging
from src.utils.metrics import record_request, record_error
from src.utils.logger import get_logger
from src.db.session import init_database, close_async_engine

logger = get_logger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    init_app_logging(settings.APP_ENV)
    init_alerting(
        error_rate_threshold=int(os.getenv("ALERT_ERROR_RATE_THRESHOLD", "10")),
        error_rate_window=int(os.getenv("ALERT_ERROR_RATE_WINDOW", "60")),
        channels=["log"] if settings.APP_ENV != "production" else ["log", "webhook"],
        webhook_url=os.getenv("ALERT_WEBHOOK_URL")
    )
    
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


@app.middleware("http")
async def rate_limit_and_metrics_middleware(request: Request, call_next):
    """Combined middleware for rate limiting and metrics."""
    # Apply rate limiting based on path
    if request.url.path.startswith("/voice"):
        response = await rate_limit_middleware(request, call_next, "voice")
    elif request.url.path.startswith("/auth"):
        response = await rate_limit_middleware(request, call_next, "auth")
    elif request.url.path.startswith("/health"):
        response = await rate_limit_middleware(request, call_next, "health")
    else:
        response = await rate_limit_middleware(request, call_next, "default")
    
    return response
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
        error_type = type(e).__name__
        record_error(error_type)
        
        from src.utils.alerting import get_alerting_service
        alerting = get_alerting_service()
        alerting.check_error_rate(error_type)
        
        send_alert(
            level=AlertLevel.ERROR,
            title=f"Request Error: {request.url.path}",
            message=str(e),
            component="http",
            metadata={"path": request.url.path, "method": request.method, "error": error_type}
        )
        
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


# Include routers
app.include_router(voice.router, prefix="/voice", tags=["voice"])
app.include_router(health.router, prefix="", tags=["health"])
app.include_router(auth_routes.router, prefix="/api", tags=["authentication"])
app.include_router(v1_router, prefix="/api", tags=["v1"])



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
