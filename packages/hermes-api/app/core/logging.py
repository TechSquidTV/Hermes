"""
Logging configuration for the Hermes API.
"""

import logging
import sys
from typing import Any, Dict

import structlog


def setup_logging(debug: bool = False) -> None:
    """Configure structured logging for the application."""

    # Configure standard library logging
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Replace standard loggers with structlog
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Convenience functions for common logging patterns
def log_request(
    logger: structlog.stdlib.BoundLogger, method: str, path: str, **kwargs
) -> None:
    """Log an incoming request."""
    logger.info("Request received", method=method, path=path, **kwargs)


def log_response(
    logger: structlog.stdlib.BoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs,
) -> None:
    """Log a response."""
    logger.info(
        "Request completed",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs,
    )


def log_error(
    logger: structlog.stdlib.BoundLogger,
    error: Exception,
    context: Dict[str, Any] = None,
) -> None:
    """Log an error with context."""
    context = context or {}
    logger.error(
        "Error occurred",
        error=str(error),
        error_type=type(error).__name__,
        **context,
        exc_info=True,
    )
