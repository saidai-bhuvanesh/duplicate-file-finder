"""
Source Code and Infrastructure configuration loader.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, BinaryIO

from app.core.logging import get_logger
from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
from app.ingestion.loaders.base import BaseLoader

logger = get_logger(__name__, component="code_loader")


class CodeLoader(BaseLoader):
    """
    Loader for Source Code and Infrastructure configuration files.
    Supports Python, JavaScript, TypeScript, Java, Go, Rust, C/C++, SQL,
    Terraform (.tf), Kubernetes YAML, Docker Compose, Dockerfile, Shell scripts.
    """

    CODE_EXTENSIONS = {
        ".py": ("python", DocumentType.CODE),
        ".js": ("javascript", DocumentType.CODE),
        ".ts": ("typescript", DocumentType.CODE),
        ".jsx": ("react_js", DocumentType.CODE),
        ".tsx": ("react_ts", DocumentType.CODE),
        ".java": ("java", DocumentType.CODE),
        ".go": ("go", DocumentType.CODE),
        ".rs": ("rust", DocumentType.CODE),
        ".cpp": ("cpp", DocumentType.CODE),
        ".c": ("c", DocumentType.CODE),
        ".h": ("c_header", DocumentType.CODE),
        ".hpp": ("cpp_header", DocumentType.CODE),
        ".sql": ("sql", DocumentType.CODE),
        ".sh": ("shell", DocumentType.CODE),
        ".bash": ("shell", DocumentType.CODE),
        ".tf": ("terraform", DocumentType.TERRAFORM),
        ".tfvars": ("terraform", DocumentType.TERRAFORM),
        ".yaml": ("yaml", DocumentType.KUBERNETES),
        ".yml": ("yaml", DocumentType.KUBERNETES),
    }

    SPECIAL_FILENAMES = {
        "dockerfile": ("docker", DocumentType.DOCKER),
        "docker-compose.yml": ("docker-compose", DocumentType.DOCKER),
        "docker-compose.yaml": ("docker-compose", DocumentType.DOCKER),
    }

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        ext = file_extension.lower() if file_extension.startswith(".") else f".{file_extension.lower()}"
        return ext in self.CODE_EXTENSIONS or file_extension.lower() in self.SPECIAL_FILENAMES

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> list[Document]:
        content_text = _read_text(source)
        filename = (metadata or {}).get("filename", "")
        file_ext = (metadata or {}).get("file_extension", "").lower()
        if not file_ext.startswith("."):
            file_ext = f".{file_ext}"

        lang, doc_type = self._detect_code_type(filename, file_ext, content_text)

        doc_title = title or filename or "Source Code File"
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

        doc_meta = DocumentMetadata.from_dict(
            {"language": lang, **(metadata or {})},
            source_system=source_system,
        )

        doc = Document(
            title=doc_title,
            content=content_text,
            document_type=doc_type,
            metadata=doc_meta,
            content_hash=content_hash,
            token_count=len(content_text.split()),
        )
        return [doc]

    def _detect_code_type(self, filename: str, file_ext: str, content: str) -> tuple[str, DocumentType]:
        """Detect language and document type from extension, filename, or content."""
        fn_lower = filename.lower()
        if fn_lower in self.SPECIAL_FILENAMES:
            return self.SPECIAL_FILENAMES[fn_lower]

        if file_ext in self.CODE_EXTENSIONS:
            lang, doc_type = self.CODE_EXTENSIONS[file_ext]
            # Disambiguate Kubernetes YAML vs Docker Compose vs Generic YAML
            if doc_type == DocumentType.KUBERNETES:
                if "apiVersion:" in content and "kind:" in content:
                    return "kubernetes", DocumentType.KUBERNETES
                elif "services:" in content and ("version:" in content or "networks:" in content):
                    return "docker-compose", DocumentType.DOCKER
                else:
                    return "yaml", DocumentType.CODE
            return lang, doc_type

        return "text", DocumentType.CODE


def _read_text(source: str | bytes | BinaryIO) -> str:
    if isinstance(source, str):
        if os.path.exists(source) and os.path.isfile(source):
            with open(source, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        return source
    elif isinstance(source, bytes):
        return source.decode("utf-8", errors="replace")
    elif hasattr(source, "read"):
        content = source.read()
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        return str(content)
    return str(source)
