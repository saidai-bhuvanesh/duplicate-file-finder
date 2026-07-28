"""
Structured logging configuration using structlog.

Provides:
- JSON logging in production
- Pretty console logging in development
- Request context binding (request_id, user_id)
- Performance timing helpers
"""

from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Generator

import structlog
from structlog.types import FilteringBoundLogger


def configure_logging(log_level: str = "INFO", is_production: bool = False) -> None:
    """
    Configure structlog for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        is_production: If True, uses JSON renderer. Otherwise pretty console.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if is_production:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Silence noisy libraries
    for noisy_logger in [
        "uvicorn.access",
        "httpx",
        "httpcore",
        "asyncio",
    ]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str | None = None, **initial_values: Any) -> FilteringBoundLogger:
    """
    Get a structlog logger instance.

    Args:
        name: Logger name (usually __name__).
        **initial_values: Initial context key-value pairs to bind.

    Returns:
        A structlog bound logger.

    Usage:
        logger = get_logger(__name__, component="retrieval")
        logger.info("Query processed", query_id="abc123", latency_ms=45.2)
    """
    logger = structlog.get_logger(name)
    if initial_values:
        logger = logger.bind(**initial_values)
    return logger


def bind_request_context(
    request_id: str,
    user_id: str | None = None,
    path: str | None = None,
    method: str | None = None,
) -> None:
    """
    Bind request context variables to the current async context.

    These values will automatically appear in all log calls made within
    the same async context (FastAPI request lifecycle).

    Args:
        request_id: Unique request identifier.
        user_id: Authenticated user identifier.
        path: HTTP request path.
        method: HTTP method.
    """
    ctx: dict[str, Any] = {"request_id": request_id}
    if user_id:
        ctx["user_id"] = user_id
    if path:
        ctx["path"] = path
    if method:
        ctx["method"] = method
    structlog.contextvars.bind_contextvars(**ctx)


def clear_request_context() -> None:
    """Clear bound context variables after request completion."""
    structlog.contextvars.clear_contextvars()


@contextmanager
def log_duration(
    logger: FilteringBoundLogger,
    operation: str,
    **extra: Any,
) -> Generator[None, None, None]:
    """
    Context manager that logs the duration of an operation.

    Args:
        logger: Structlog logger instance.
        operation: Name of the operation being timed.
        **extra: Additional key-value pairs to include in the log.

    Usage:
        with log_duration(logger, "faiss_search", top_k=5):
            results = faiss_index.search(query_embedding)
    """
    start = time.perf_counter()
    try:
        yield
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "operation_completed",
            operation=operation,
            duration_ms=round(elapsed_ms, 2),
            **extra,
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "operation_failed",
            operation=operation,
            duration_ms=round(elapsed_ms, 2),
            error=str(exc),
            error_type=type(exc).__name__,
            **extra,
        )
        raise
