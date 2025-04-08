import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

from .config import settings

# Configure logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
JSON_LOG_FORMAT = {
    "timestamp": "%(asctime)s",
    "name": "%(name)s",
    "level": "%(levelname)s",
    "message": "%(message)s",
}

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the log record.
    """
    def __init__(self, fmt_dict: Dict[str, str] = JSON_LOG_FORMAT):
        self.fmt_dict = fmt_dict
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        record_dict = self._prepare_log_dict(record)
        return json.dumps(record_dict)

    def _prepare_log_dict(self, record: logging.LogRecord) -> Dict[str, Any]:
        """
        Prepares a JSON-serializable dictionary from the log record.
        """
        record_dict = {}
        for key, value in self.fmt_dict.items():
            if key == "asctime":
                record_dict[key] = self.formatTime(record)
            else:
                record_dict[key] = value % record.__dict__
        
        # Add exception info if available
        if record.exc_info:
            record_dict["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in record_dict and not key.startswith("_") and isinstance(value, (str, int, float, bool, type(None))):
                record_dict[key] = value
        
        return record_dict

def setup_logging(
    log_level: Optional[str] = None,
    json_logs: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format
        log_file: Path to a log file (if None, logs to stdout)
    """
    # Get log level from settings if not provided
    if log_level is None:
        log_level = settings.LOG_LEVEL
    
    # Convert string log level to numeric value
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    handlers.append(console_handler)
    
    # File handler if log file is specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)
    
    # Set formatter based on format preference
    if json_logs:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(LOG_FORMAT)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add and configure handlers
    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info(f"Logging configured with level: {log_level}")

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: The name of the logger
        
    Returns:
        A logger instance
    """
    return logging.getLogger(name)
