"""
Custom exception hierarchy for EnterpriseIT-RAG.

All application exceptions inherit from EnterpriseRAGException.
HTTP exceptions are mapped in the FastAPI exception handlers.
"""

from __future__ import annotations

from typing import Any


class EnterpriseRAGException(Exception):
    """
    Base exception for all EnterpriseIT-RAG errors.

    Attributes:
        message: Human-readable error message.
        code: Machine-readable error code for clients.
        details: Optional structured details for debugging.
    """

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


# ── Configuration ─────────────────────────────────────────────────────────────


class ConfigurationError(EnterpriseRAGException):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="CONFIGURATION_ERROR", details=details)


# ── Domain / Business Logic ───────────────────────────────────────────────────


class DocumentNotFoundError(EnterpriseRAGException):
    """Raised when a document cannot be found in the repository."""

    def __init__(self, document_id: str) -> None:
        super().__init__(
            f"Document not found: {document_id}",
            code="DOCUMENT_NOT_FOUND",
            details={"document_id": document_id},
        )


class ChunkNotFoundError(EnterpriseRAGException):
    """Raised when a chunk cannot be found."""

    def __init__(self, chunk_id: str) -> None:
        super().__init__(
            f"Chunk not found: {chunk_id}",
            code="CHUNK_NOT_FOUND",
            details={"chunk_id": chunk_id},
        )


class DuplicateDocumentError(EnterpriseRAGException):
    """Raised when attempting to ingest a document that already exists."""

    def __init__(self, content_hash: str) -> None:
        super().__init__(
            f"Document already exists with hash: {content_hash}",
            code="DUPLICATE_DOCUMENT",
            details={"content_hash": content_hash},
        )


# ── Ingestion ─────────────────────────────────────────────────────────────────


class IngestionError(EnterpriseRAGException):
    """Raised when document ingestion fails."""

    def __init__(
        self,
        message: str,
        source_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        extra = {"source_path": source_path} if source_path else {}
        super().__init__(
            message,
            code="INGESTION_ERROR",
            details={**extra, **(details or {})},
        )


class UnsupportedDocumentTypeError(IngestionError):
    """Raised when attempting to ingest an unsupported file type."""

    def __init__(self, file_type: str) -> None:
        super().__init__(
            f"Unsupported document type: {file_type}",
            details={"file_type": file_type},
        )
        self.code = "UNSUPPORTED_DOCUMENT_TYPE"


class DocumentTooLargeError(IngestionError):
    """Raised when a document exceeds the maximum allowed size."""

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        super().__init__(
            f"Document size {size_bytes} bytes exceeds maximum {max_bytes} bytes",
            details={"size_bytes": size_bytes, "max_bytes": max_bytes},
        )
        self.code = "DOCUMENT_TOO_LARGE"


# ── Retrieval ─────────────────────────────────────────────────────────────────


class RetrievalError(EnterpriseRAGException):
    """Raised when retrieval fails."""

    def __init__(self, message: str, strategy: str | None = None) -> None:
        super().__init__(
            message,
            code="RETRIEVAL_ERROR",
            details={"strategy": strategy} if strategy else {},
        )


class InsufficientEvidenceError(EnterpriseRAGException):
    """
    Raised by the Evidence Gate when retrieved context is too weak.

    This is a critical component of hallucination prevention.
    Instead of generating a low-quality answer, we surface this error.
    """

    def __init__(
        self,
        coverage: float,
        confidence: float,
        sources_found: int,
        query: str,
    ) -> None:
        super().__init__(
            "Insufficient evidence found to answer this query reliably",
            code="INSUFFICIENT_EVIDENCE",
            details={
                "coverage": coverage,
                "confidence": confidence,
                "sources_found": sources_found,
                "query": query,
            },
        )


class IndexNotReadyError(RetrievalError):
    """Raised when a retrieval index is not yet built."""

    def __init__(self, index_name: str) -> None:
        super().__init__(
            f"Index '{index_name}' is not ready. Run ingestion first.",
            strategy=index_name,
        )
        self.code = "INDEX_NOT_READY"


# ── Agent / LLM ───────────────────────────────────────────────────────────────


class LLMError(EnterpriseRAGException):
    """Raised when LLM call fails."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(
            message,
            code="LLM_ERROR",
            details={"provider": provider, "model": model},
        )


class AgentError(EnterpriseRAGException):
    """Raised when an agent encounters an unrecoverable error."""

    def __init__(self, agent_name: str, message: str) -> None:
        super().__init__(
            f"Agent '{agent_name}' failed: {message}",
            code="AGENT_ERROR",
            details={"agent_name": agent_name},
        )


class HallucinationDetectedError(EnterpriseRAGException):
    """
    Raised when generated content cannot be grounded in retrieved evidence.

    Contains details of which sentences failed grounding.
    """

    def __init__(self, ungrounded_sentences: list[str]) -> None:
        super().__init__(
            "Generated content contains ungrounded claims",
            code="HALLUCINATION_DETECTED",
            details={"ungrounded_sentences": ungrounded_sentences},
        )


# ── Infrastructure ────────────────────────────────────────────────────────────


class DatabaseError(EnterpriseRAGException):
    """Raised when a database operation fails."""

    def __init__(self, message: str, operation: str | None = None) -> None:
        super().__init__(
            message,
            code="DATABASE_ERROR",
            details={"operation": operation} if operation else {},
        )


class CacheError(EnterpriseRAGException):
    """Raised when a cache operation fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="CACHE_ERROR")


class GraphDatabaseError(EnterpriseRAGException):
    """Raised when a Neo4j operation fails."""

    def __init__(self, message: str, query: str | None = None) -> None:
        super().__init__(
            message,
            code="GRAPH_DATABASE_ERROR",
            details={"query": query} if query else {},
        )


class ExternalServiceError(EnterpriseRAGException):
    """Raised when an external service call fails."""

    def __init__(self, service: str, message: str, status_code: int | None = None) -> None:
        super().__init__(
            f"External service '{service}' failed: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, "status_code": status_code},
        )


# ── Validation ────────────────────────────────────────────────────────────────


class ValidationError(EnterpriseRAGException):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            details={"field": field} if field else {},
        )


# ── Authentication / Authorization ────────────────────────────────────────────


class AuthenticationError(EnterpriseRAGException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTHENTICATION_ERROR")


class AuthorizationError(EnterpriseRAGException):
    """Raised when user lacks permission for an operation."""

    def __init__(self, resource: str, action: str) -> None:
        super().__init__(
            f"Access denied: cannot '{action}' on '{resource}'",
            code="AUTHORIZATION_ERROR",
            details={"resource": resource, "action": action},
        )
