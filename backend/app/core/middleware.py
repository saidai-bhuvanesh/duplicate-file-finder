"""
FastAPI middleware stack.

Implements:
- Request ID injection (X-Request-ID header)
- Structured request/response logging
- Timing and latency tracking
- CORS configuration
- Exception → JSON error response mapping
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.exceptions import (
    AgentError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    DocumentNotFoundError,
    EnterpriseRAGException,
    InsufficientEvidenceError,
    LLMError,
    ValidationError,
)
from app.core.logging import bind_request_context, clear_request_context, get_logger

logger = get_logger(__name__, component="middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every HTTP request with request_id, method, path, status, and latency.

    Also binds request context for structured logging throughout the request.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start_time = time.perf_counter()

        # Bind context so all downstream logs include request_id
        bind_request_context(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        logger.info(
            "request_started",
            client_ip=request.client.host if request.client else "unknown",
            query_string=str(request.query_params),
        )

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = str(duration_ms)
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=duration_ms,
            )
            raise
        finally:
            clear_request_context()


def _make_error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    """Build a standardized error JSON response."""
    content: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        content["error"]["details"] = details
    if request_id:
        content["error"]["request_id"] = request_id

    return JSONResponse(status_code=status_code, content=content)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers that map domain exceptions to HTTP responses.

    This keeps HTTP status code logic out of the domain and application layers.
    """

    @app.exception_handler(DocumentNotFoundError)
    async def handle_not_found(request: Request, exc: DocumentNotFoundError) -> JSONResponse:
        return _make_error_response(
            status_code=404,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request.headers.get("X-Request-ID"),
        )

    @app.exception_handler(InsufficientEvidenceError)
    async def handle_insufficient_evidence(
        request: Request, exc: InsufficientEvidenceError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=422,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request.headers.get("X-Request-ID"),
        )

    @app.exception_handler(AuthenticationError)
    async def handle_auth(request: Request, exc: AuthenticationError) -> JSONResponse:
        return _make_error_response(
            status_code=401,
            code=exc.code,
            message=exc.message,
            request_id=request.headers.get("X-Request-ID"),
        )

    @app.exception_handler(AuthorizationError)
    async def handle_authz(request: Request, exc: AuthorizationError) -> JSONResponse:
        return _make_error_response(
            status_code=403,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request.headers.get("X-Request-ID"),
        )

    @app.exception_handler(ValidationError)
    async def handle_validation(request: Request, exc: ValidationError) -> JSONResponse:
        return _make_error_response(
            status_code=422,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request.headers.get("X-Request-ID"),
        )

    @app.exception_handler(LLMError)
    async def handle_llm_error(request: Request, exc: LLMError) -> JSONResponse:
        return _make_error_response(
            status_code=503,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request.headers.get("X-Request-ID"),
        )

    @app.exception_handler(AgentError)
    async def handle_agent_error(request: Request, exc: AgentError) -> JSONResponse:
        return _make_error_response(
            status_code=500,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request.headers.get("X-Request-ID"),
        )

    @app.exception_handler(DatabaseError)
    async def handle_database_error(request: Request, exc: DatabaseError) -> JSONResponse:
        logger.error("database_error", error=exc.message, details=exc.details)
        return _make_error_response(
            status_code=503,
            code=exc.code,
            message="A database error occurred. Please try again later.",
            request_id=request.headers.get("X-Request-ID"),
        )

    @app.exception_handler(EnterpriseRAGException)
    async def handle_generic_rag_error(
        request: Request, exc: EnterpriseRAGException
    ) -> JSONResponse:
        logger.error("unhandled_rag_exception", error=exc.message, code=exc.code)
        return _make_error_response(
            status_code=500,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            request_id=request.headers.get("X-Request-ID"),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_error", error=str(exc), error_type=type(exc).__name__)
        return _make_error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            request_id=request.headers.get("X-Request-ID"),
        )


def configure_cors(app: FastAPI) -> None:
    """Add CORS middleware using settings-defined allowed origins."""
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Response-Time-Ms"],
    )
