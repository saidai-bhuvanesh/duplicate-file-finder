"""
Structured logging fallback using Python's standard logging module.

Provides:
- Compatible logger API with structured key-value logging
- Request context binding (request_id, user_id)
- Performance timing helpers (log_duration)
"""

from __future__ import annotations

import contextvars
import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Generator

FilteringBoundLogger = Any

_request_ctx: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("request_ctx", default={})


def _get_context() -> dict[str, Any]:
    return _request_ctx.get()


class StructlogCompatLogger:
    """Wrapper around logging.Logger to mimic structlog's API."""

    def __init__(self, logger: logging.Logger, context: dict[str, Any] | None = None) -> None:
        self._logger = logger
        self._context = context or {}

    def bind(self, **new_values: Any) -> StructlogCompatLogger:
        merged = {**self._context, **new_values}
        return StructlogCompatLogger(self._logger, merged)

    def _log(self, level: int, event: str, *args: Any, **kwargs: Any) -> None:
        if not self._logger.isEnabledFor(level):
            return
        exc_info = kwargs.pop("exc_info", None)
        ctx = {**_get_context(), **self._context, **kwargs}
        if ctx:
            details = " ".join(f"{k}={v}" for k, v in ctx.items())
            msg = f"{event} | {details}"
        else:
            msg = event
        self._logger.log(level, msg, *args, exc_info=exc_info)

    def debug(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.DEBUG, event, *args, **kwargs)

    def info(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.INFO, event, *args, **kwargs)

    def warning(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.WARNING, event, *args, **kwargs)

    def error(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, event, *args, **kwargs)

    def critical(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, event, *args, **kwargs)

    def exception(self, event: str, *args: Any, **kwargs: Any) -> None:
        self._log(logging.ERROR, event, *args, exc_info=True, **kwargs)


def configure_logging(log_level: str = "INFO", is_production: bool = False) -> None:
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
        force=True,
    )
    for noisy_logger in ["uvicorn.access", "httpx", "httpcore", "asyncio"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def get_logger(name: str | None = None, **initial_values: Any) -> StructlogCompatLogger:
    base_logger = logging.getLogger(name or "app")
    logger = StructlogCompatLogger(base_logger)
    if initial_values:
        logger = logger.bind(**initial_values)
    return logger


def bind_request_context(
    request_id: str,
    user_id: str | None = None,
    path: str | None = None,
    method: str | None = None,
) -> None:
    ctx = dict(_request_ctx.get())
    ctx["request_id"] = request_id
    if user_id:
        ctx["user_id"] = user_id
    if path:
        ctx["path"] = path
    if method:
        ctx["method"] = method
    _request_ctx.set(ctx)


def clear_request_context() -> None:
    _request_ctx.set({})


@contextmanager
def log_duration(
    logger: Any,
    operation: str,
    **extra: Any,
) -> Generator[None, None, None]:
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
