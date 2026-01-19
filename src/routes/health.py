"""Health check endpoints for monitoring and Kubernetes probes."""
import os
import time
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends
import sqlalchemy

from src.utils.logger import get_logger
from src.core.config import get_settings
from src.db.session import get_sync_engine

logger = get_logger(__name__)

router = APIRouter()


def check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


def check_twilio() -> Dict[str, Any]:
    """Check Twilio configuration."""
    required = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_PHONE_NUMBER']
    missing = [v for v in required if not os.getenv(v)]
    
    if missing:
        return {"status": "degraded", "missing": missing}
    return {"status": "healthy"}


def check_environment() -> Dict[str, Any]:
    """Check environment configuration."""
    settings = get_settings()
    return {
        "environment": settings.APP_ENV,
        "debug": settings.DEBUG,
        "version": settings.VERSION,
    }


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 if the application is running.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness_check() -> Dict[str, Any]:
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 if the application is ready to serve traffic.
    Checks database connectivity and required configurations.
    """
    start_time = time.time()
    checks = {
        "database": check_database(),
        "twilio": check_twilio(),
        "environment": check_environment(),
    }
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    overall_status = "ready"
    for check_name, result in checks.items():
        if result.get("status") == "unhealthy":
            overall_status = "not_ready"
        elif result.get("status") == "degraded" and overall_status == "ready":
            overall_status = "degraded"
    
    return {
        "status": overall_status,
        "checks": checks,
        "latency_ms": elapsed_ms,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint.
    
    Returns comprehensive health status including all components.
    """
    start_time = time.time()
    
    db_check = check_database()
    twilio_check = check_twilio()
    env_check = check_environment()
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    healthy_components = sum(1 for c in [db_check, twilio_check] if c.get("status") == "healthy")
    total_components = 2
    
    overall_status = "healthy"
    if db_check.get("status") == "unhealthy":
        overall_status = "unhealthy"
    elif twilio_check.get("status") == "degraded":
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "components": {
            "database": db_check,
            "twilio": twilio_check,
            "environment": env_check,
        },
        "summary": {
            "healthy": healthy_components,
            "total": total_components,
        },
        "latency_ms": elapsed_ms,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics")
async def prometheus_metrics() -> str:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus format.
    """
    from src.utils.metrics import get_metrics
    
    metrics = get_metrics()
    
    output = []
    for metric_name, value in metrics.items():
        output.append(f"# TYPE {metric_name} gauge")
        output.append(f"{metric_name} {value}")
    
    return "\n".join(output)
