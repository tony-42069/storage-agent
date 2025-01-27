import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = "logs/storage_agent.log",
    max_bytes: int = 10_000_000,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up application logging with both console and file handlers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, only console logging is enabled
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
    
    Returns:
        Logger instance configured with specified handlers
    """
    # Create logger
    logger = logging.getLogger('storage_agent')
    logger.setLevel(getattr(logging, log_level.upper()))

    # Create formatters
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file specified)
    if log_file:
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

# Create default logger instance
logger = setup_logging()

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Name for the logger, typically __name__ of the module
    
    Returns:
        Logger instance configured with project settings
    """
    return logging.getLogger(f'storage_agent.{name}')
