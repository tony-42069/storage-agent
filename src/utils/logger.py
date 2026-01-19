import logging
import os
import sys
import json
import uuid
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any
from contextlib import contextmanager

import pythonjsonlogger

_loggers: Dict[str, logging.Logger] = {}
_request_id_context: Optional[str] = None


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return _request_id_context


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())[:8]


def set_request_id(request_id: str):
    """Set request ID in context."""
    global _request_id_context
    _request_id_context = request_id


@contextmanager
def request_context(request_id: Optional[str] = None):
    """Context manager for request-scoped logging."""
    global _request_id_context
    old_id = _request_id_context
    _request_id_context = request_id or generate_request_id()
    try:
        yield _request_id_context
    finally:
        _request_id_context = old_id


class RequestIdFilter(logging.Filter):
    """Filter to add request ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_context or ""
        return True


class StructuredLogFormatter(pythonjsonlogger.jsonhandler.JsonFormatter):
    """JSON formatter for structured logging."""
    
    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ):
        super().add_fields(log_record, record, message_dict)
        
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['request_id'] = getattr(record, 'request_id', '')
        
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        if hasattr(record, 'extra_data'):
            log_record['extra'] = record.extra_data


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = "logs/storage_agent.log",
    max_bytes: int = 10_000_000,
    backup_count: int = 5,
    json_format: bool = False,
    module_levels: Optional[Dict[str, str]] = None
) -> logging.Logger:
    """
    Set up application logging with both console and file handlers.
    
    Args:
        log_level: Default logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, only console logging is enabled
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
        json_format: Use JSON formatting for structured logs
        module_levels: Dict of module-specific log levels (e.g., {'sqlalchemy': 'WARNING'})
    
    Returns:
        Configured root logger
    """
    root_logger = logging.getLogger('storage_agent')
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    root_logger.handlers.clear()
    
    request_filter = RequestIdFilter()
    
    if json_format:
        formatter = StructuredLogFormatter(
            '%(timestamp)s %(level)s %(name)s %(request_id)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(request_id)s - %(message)s'
        )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(request_filter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(request_filter)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        root_logger.addHandler(file_handler)
    
    if module_levels:
        for module, level in module_levels.items():
            logging.getLogger(module).setLevel(getattr(logging, level.upper()))
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    if name not in _loggers:
        _loggers[name] = logging.getLogger(f'storage_agent.{name}')
    return _loggers[name]


def log_request(
    logger: logging.Logger,
    level: int = logging.INFO,
    message: str = "",
    **extra
):
    """Log with request context automatically included."""
    extra['request_id'] = get_request_id() or ""
    logger.log(level, message, extra=extra)


class LoggerMixin:
    """Mixin class to add logging capability to any class."""
    
    @property
    def logger(self) -> logging.Logger:
        return get_logger(self.__class__.__module__)


def init_app_logging(
    app_env: str = "development",
    log_level: str = "INFO"
):
    """
    Initialize logging for the FastAPI application.
    
    Args:
        app_env: Application environment (development, staging, production)
        log_level: Default log level
    """
    module_levels = {
        'sqlalchemy': 'WARNING',
        'alembic': 'INFO',
        'uvicorn': 'INFO',
    }
    
    if app_env == "production":
        json_format = True
        log_file = "logs/app.log"
    else:
        json_format = False
        log_file = "logs/storage_agent.log"
    
    setup_logging(
        log_level=log_level,
        log_file=log_file,
        json_format=json_format,
        module_levels=module_levels
    )
    
    logger = get_logger(__name__)
    logger.info(f"Logging initialized (env: {app_env}, format: {'JSON' if json_format else 'Text'})")


setup_logging()
logger = get_logger(__name__)
