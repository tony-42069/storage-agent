"""Error alerting and notification system."""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import threading
from queue import Queue, Empty

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AlertLevel(Enum):
    """Alert severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Represents an alert."""
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    component: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False


class AlertStore:
    """In-memory alert storage with deduplication."""
    
    def __init__(self, max_size: int = 1000, dedup_window_seconds: int = 300):
        self._alerts: List[Alert] = []
        self._alert_counts: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._max_size = max_size
        self._dedup_window = timedelta(seconds=dedup_window_seconds)
        self._last_alert_time: Dict[str, datetime] = {}
    
    def add(self, alert: Alert) -> bool:
        """
        Add an alert with deduplication.
        
        Returns:
            True if alert was added, False if duplicate/suppressed
        """
        with self._lock:
            alert_key = f"{alert.level.value}:{alert.component}:{alert.title}"
            now = datetime.utcnow()
            
            # Check deduplication window
            if alert_key in self._last_alert_time:
                time_since_last = now - self._last_alert_time[alert_key]
                if time_since_last < self._dedup_window:
                    self._alert_counts[alert_key] = self._alert_counts.get(alert_key, 0) + 1
                    return False
            
            self._last_alert_time[alert_key] = now
            self._alerts.append(alert)
            
            # Trim if over max size
            while len(self._alerts) > self._max_size:
                self._alerts.pop(0)
            
            return True
    
    def get_recent(self, level: Optional[AlertLevel] = None, limit: int = 100) -> List[Alert]:
        """Get recent alerts."""
        with self._lock:
            alerts = [
                a for a in self._alerts
                if level is None or a.level == level
            ]
            return sorted(alerts, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_counts_by_level(self) -> Dict[str, int]:
        """Get alert counts by level."""
        with self._lock:
            return {
                level.value: sum(1 for a in self._alerts if a.level == level)
                for level in AlertLevel
            }
    
    def clear_old_alerts(self, older_than: timedelta = timedelta(hours=24)):
        """Remove alerts older than specified time."""
        with self._lock:
            cutoff = datetime.utcnow() - older_than
            self._alerts = [a for a in self._alerts if a.timestamp > cutoff]
    
    def acknowledge(self, alert_index: int):
        """Acknowledge an alert by index."""
        with self._lock:
            if 0 <= alert_index < len(self._alerts):
                self._alerts[alert_index].acknowledged = True


class AlertingService:
    """Service for managing and sending alerts."""
    
    def __init__(self):
        self._store = AlertStore()
        self._notification_channels: List[str] = []
        self._error_rate_window_seconds = 60
        self._error_rate_threshold = 10
        self._error_count_window = 0
        self._last_window_reset = datetime.utcnow()
        self._lock = threading.Lock()
        
        logger.info("Alerting service initialized")
    
    def add_notification_channel(self, channel_type: str, config: Dict[str, Any]):
        """Add a notification channel."""
        self._notification_channels.append(channel_type)
        logger.info(f"Added notification channel: {channel_type}")
    
    def set_error_rate_threshold(self, threshold: int, window_seconds: int = 60):
        """Set error rate threshold for alerts."""
        self._error_rate_threshold = threshold
        self._error_rate_window_seconds = window_seconds
        logger.info(f"Error rate threshold: {threshold} per {window_seconds}s")
    
    def check_error_rate(self, error_type: str):
        """Check if error rate threshold is exceeded."""
        with self._lock:
            now = datetime.utcnow()
            
            # Reset window if needed
            if (now - self._last_window_reset).total_seconds() >= self._error_rate_window_seconds:
                self._error_count_window = 0
                self._last_window_reset = now
            
            self._error_count_window += 1
            
            if self._error_count_window >= self._error_rate_threshold:
                self.send_alert(
                    level=AlertLevel.WARNING,
                    title="High Error Rate",
                    message=f"Error rate exceeded threshold: {self._error_count_window} errors in {self._error_rate_window_seconds}s",
                    component="error_rate",
                    metadata={"error_type": error_type, "count": self._error_count_window}
                )
    
    def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        component: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False
    ) -> bool:
        """
        Send an alert through configured channels.
        
        Args:
            level: Alert severity level
            title: Alert title
            message: Alert message
            component: Component that triggered the alert
            metadata: Additional context
            force: Skip deduplication
            
        Returns:
            True if alert was sent
        """
        alert = Alert(
            level=level,
            title=title,
            message=message,
            component=component,
            metadata=metadata or {}
        )
        
        if force or self._store.add(alert):
            self._notify_channels(alert)
            logger.warning(f"Alert sent: [{level.value}] {title}")
            return True
        
        return False
    
    def _notify_channels(self, alert: Alert):
        """Notify all configured channels."""
        for channel in self._notification_channels:
            try:
                if channel == "log":
                    self._notify_log(alert)
                elif channel == "webhook":
                    self._notify_webhook(alert)
            except Exception as e:
                logger.error(f"Failed to notify channel {channel}: {e}")
    
    def _notify_log(self, alert: Alert):
        """Log the alert."""
        log_method = getattr(logger, alert.level.value, logger.warning)
        log_method(f"ALERT [{alert.level.value.upper()}] {alert.title}: {alert.message}")
    
    def _notify_webhook(self, alert: Alert):
        """Send alert to webhook."""
        webhook_url = os.getenv("ALERT_WEBHOOK_URL")
        if not webhook_url:
            return
        
        import requests
        payload = {
            "level": alert.level.value,
            "title": alert.title,
            "message": alert.message,
            "component": alert.component,
            "timestamp": alert.timestamp.isoformat(),
            "metadata": alert.metadata,
        }
        
        try:
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get recent alerts."""
        return self._store.get_recent(level, limit)
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary."""
        return {
            "counts_by_level": self._store.get_counts_by_level(),
            "total_alerts": len(self._store._alerts),
            "error_rate": {
                "current_window": self._error_count_window,
                "threshold": self._error_rate_threshold,
                "window_seconds": self._error_rate_window_seconds,
            }
        }
    
    def cleanup(self, older_than: timedelta = timedelta(hours=24)):
        """Clean up old alerts."""
        self._store.clear_old_alerts(older_than)


_alerting_service = AlertingService()


def get_alerting_service() -> AlertingService:
    """Get the alerting service instance."""
    return _alerting_service


def send_alert(
    level: AlertLevel,
    title: str,
    message: str,
    component: str = "general",
    metadata: Optional[Dict[str, Any]] = None,
    force: bool = False
) -> bool:
    """Send an alert."""
    return _alerting_service.send_alert(level, title, message, component, metadata, force)


def alert_on_error(component: str = "general"):
    """Decorator to automatically alert on function errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                send_alert(
                    level=AlertLevel.ERROR,
                    title=f"Function Error: {func.__name__}",
                    message=str(e),
                    component=component,
                    metadata={"function": func.__name__, "args": str(args)}
                )
                raise
        return wrapper
    return decorator


def init_alerting(
    error_rate_threshold: int = 10,
    error_rate_window: int = 60,
    channels: Optional[List[str]] = None,
    webhook_url: Optional[str] = None
):
    """Initialize alerting service."""
    service = get_alerting_service()
    
    service.set_error_rate_threshold(error_rate_threshold, error_rate_window)
    
    if channels:
        for channel in channels:
            service.add_notification_channel(channel, {})
    
    if webhook_url:
        os.environ["ALERT_WEBHOOK_URL"] = webhook_url
        service.add_notification_channel("webhook", {})
    
    logger.info("Alerting service configured")


# Initialize with defaults
init_alerting(
    error_rate_threshold=10,
    error_rate_window=60,
    channels=["log"]
)
