"""Application metrics collection for Prometheus."""
import time
from typing import Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta
import threading

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """In-memory metrics collector."""
    
    def __init__(self):
        self._requests_total: Dict[str, int] = defaultdict(int)
        self._request_duration_ms: Dict[str, list] = defaultdict(list)
        self._errors_total: Dict[str, int] = defaultdict(int)
        self._conversations_total: Dict[str, int] = defaultdict(int)
        self._intents_total: Dict[str, int] = defaultdict(int)
        self._start_time = datetime.utcnow()
        self._lock = threading.Lock()
        
        logger.info("Metrics collector initialized")
    
    def record_request(self, endpoint: str, method: str, status_code: int, duration_ms: int):
        """Record a request metric."""
        with self._lock:
            self._requests_total[f"{method}_{endpoint}_{status_code}"] += 1
            self._request_duration_ms[endpoint].append(duration_ms)
    
    def record_error(self, error_type: str):
        """Record an error."""
        with self._lock:
            self._errors_total[error_type] += 1
    
    def record_conversation(self, session_id: str, intent: str):
        """Record a conversation event."""
        with self._lock:
            self._conversations_total[session_id] += 1
            if intent:
                self._intents_total[intent] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
            
            avg_durations = {}
            for endpoint, durations in self._request_duration_ms.items():
                if durations:
                    avg_durations[endpoint] = sum(durations) / len(durations)
            
            return {
                "app_uptime_seconds": uptime_seconds,
                "app_requests_total": sum(self._requests_total.values()),
                "app_errors_total": sum(self._errors_total.values()),
                "app_conversations_total": len(self._conversations_total),
                "http_request_duration_ms_avg": avg_durations,
                "requests_by_endpoint": dict(self._requests_total),
                "errors_by_type": dict(self._errors_total),
                "intents_total": dict(self._intents_total),
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._requests_total.clear()
            self._request_duration_ms.clear()
            self._errors_total.clear()
            self._conversations_total.clear()
            self._intents_total.clear()
            self._start_time = datetime.utcnow()
            logger.info("Metrics reset")


_metrics_collector = MetricsCollector()


def get_metrics() -> Dict[str, Any]:
    """Get current metrics."""
    return _metrics_collector.get_metrics()


def record_request(endpoint: str, method: str, status_code: int, duration_ms: int):
    """Record a request metric."""
    _metrics_collector.record_request(endpoint, method, status_code, duration_ms)


def record_error(error_type: str):
    """Record an error."""
    _metrics_collector.record_error(error_type)


def record_conversation(session_id: str, intent: str):
    """Record a conversation event."""
    _metrics_collector.record_conversation(session_id, intent)


def reset_metrics():
    """Reset all metrics."""
    _metrics_collector.reset()


class RequestMetricsMiddleware:
    """Middleware to collect request metrics."""
    
    def __init__(self):
        self._enabled = True
    
    def record(self, endpoint: str, method: str, status_code: int, duration_ms: int):
        if self._enabled:
            record_request(endpoint, method, status_code, duration_ms)
    
    def disable(self):
        self._enabled = False
    
    def enable(self):
        self._enabled = True


request_metrics = RequestMetricsMiddleware()
