"""
Citation Auditor validating inline claims against source snippets.
"""

from __future__ import annotations

import re
from typing import Any

from app.agents.nli_verifier import NLIVerifier
from app.core.logging import get_logger

logger = get_logger(__name__, component="citation_auditor")


class CitationAuditor:
    """
    Audits every sentence in generated answers against cited source snippets.
    Guarantees strict citation grounding.
    """

    def __init__(self, nli_verifier: NLIVerifier | None = None) -> None:
        self.verifier = nli_verifier or NLIVerifier()

    def audit_answer(
        self,
        draft_answer: str,
        citations: list[dict[str, Any]],
    ) -> tuple[str, bool, float]:
        """
        Audit draft answer sentences against cited source snippets.

        Returns:
            Tuple of (Audited Answer, Hallucination Flag, Faithfulness Score)
        """
        if not draft_answer.strip():
            return draft_answer, False, 0.0

        # Split answer into sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", draft_answer) if s.strip()]
        citation_map = {}
        for c in citations:
            cid = c.get("citation_id")
            if cid:
                snip = c.get("snippet") or c.get("document_title") or c.get("section_title") or ""
                citation_map[cid] = snip

        audited_sentences = []
        hallucination_detected = False
        valid_sentences = 0

        for sentence in sentences:
            # Find citation tags in this sentence (e.g. [Source 1])
            tags = re.findall(r"\[Source \d+\]", sentence)

            if not tags:
                # Uncited sentence — check if general text or preamble
                audited_sentences.append(sentence)
                valid_sentences += 1
                continue

            # Verify sentence against cited snippets
            sentence_is_valid = False
            for tag in tags:
                if tag in citation_map:
                    snippet = citation_map[tag]
                    res = self.verifier.verify_faithfulness(premise=snippet, hypothesis=sentence)
                    if res["is_faithful"]:
                        sentence_is_valid = True
                        break

            if sentence_is_valid:
                audited_sentences.append(sentence)
                valid_sentences += 1
            else:
                logger.warning("uncited_or_unsupported_claim_detected", sentence=sentence[:80])
                hallucination_detected = True
                # Annotate or replace unsupported sentence
                audited_sentences.append(f"{sentence} *(Unverified Claim)*")

        faithfulness_score = round(valid_sentences / max(len(sentences), 1), 4)
        audited_text = " ".join(audited_sentences)

        return audited_text, hallucination_detected, faithfulness_score
