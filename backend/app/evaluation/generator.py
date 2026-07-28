"""
Synthetic Ground-Truth Testset Generator for RAG Evaluation.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.logging import get_logger
from app.domain.entities.document import Document
from app.infrastructure.external.llm_client import LLMClient

logger = get_logger(__name__, component="synthetic_testset_generator")


class SyntheticTestsetGenerator:
    """
    Generates synthetic QA test pairs from ingested documents for RAG evaluation.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    async def generate_test_samples_from_document(
        self,
        document: Document,
        num_samples: int = 2,
    ) -> list[dict[str, Any]]:
        """
        Generate QA test samples for a single Document entity.
        """
        samples: list[dict[str, Any]] = []
        if not document.content.strip():
            return samples

        title = document.title
        paragraphs = [p.strip() for p in document.content.split("\n\n") if len(p.strip()) > 50]
        if not paragraphs:
            paragraphs = [document.content[:500]]

        for idx, para in enumerate(paragraphs[:num_samples], 1):
            sample_id = str(uuid.uuid4())
            prompt = (
                f"Document Title: {title}\n"
                f"Content Snippet:\n{para[:1000]}\n\n"
                f"Task: Generate a realistic technical question that an IT engineer would ask based on this snippet, "
                f"along with an accurate, concise answer.\n"
                f"Format exact output as:\nQuestion: <question>\nAnswer: <answer>"
            )

            try:
                res = await self.llm_client.complete(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                )
                output = res["content"]
                question = self._extract_field(output, "Question:") or f"What is discussed in {title} (Section {idx})?"
                answer = self._extract_field(output, "Answer:") or para[:300]
            except Exception as exc:
                logger.warning("llm_synthetic_testset_generation_fallback", error=str(exc))
                question = f"What is discussed in {title} (Section {idx})?"
                answer = para[:300]

            samples.append(
                {
                    "sample_id": sample_id,
                    "document_id": document.id,
                    "document_title": title,
                    "question": question,
                    "ground_truth": answer,
                    "source_snippet": para[:300],
                }
            )

        logger.info("synthetic_samples_generated", doc_id=document.id, count=len(samples))
        return samples

    def _extract_field(self, text: str, prefix: str) -> str | None:
        for line in text.split("\n"):
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
        return None
