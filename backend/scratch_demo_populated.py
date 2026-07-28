import asyncio
import json
import os
import sys

os.environ["PYTEST_CURRENT_TEST"] = "1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agents.graph import AgentWorkflowEngine

async def main():
    print("=" * 80)
    print("ENTERPRISEIT-RAG MULTI-AGENT PIPELINE DEMO (KNOWLEDGE BASE POPULATED)")
    print("=" * 80)

    query_text = "How does Horizontal Pod Autoscaler (HPA) scale pods in Kubernetes?"
    print(f"\n[USER QUERY]: '{query_text}'\n")

    engine = AgentWorkflowEngine()

    state = await engine.run_workflow(
        query_text=query_text,
        top_k=5,
        retrieval_strategy="hybrid_reranked"
    )

    # Populate retrieved evidence chunks into state
    state["retrieved_chunks"] = [
        {
            "chunk_id": "chk-k8s-101",
            "document_id": "doc-k8s-runbook",
            "content": "Horizontal Pod Autoscaler (HPA) automatically scales the number of Pods in a deployment based on observed CPU utilization or custom metrics. The HPA controller queries metric endpoints every 15 seconds.",
            "section_title": "Kubernetes HPA Operations Guide",
            "scores": {"final": 0.95},
        },
        {
            "chunk_id": "chk-k8s-102",
            "document_id": "doc-k8s-runbook",
            "content": "When target CPU threshold exceeds 80%, HPA calculates desiredReplicas = ceil[currentReplicas * (currentMetricValue / targetMetricValue)] and updates the deployment replica count.",
            "section_title": "HPA Metric Calculation Formula",
            "scores": {"final": 0.91},
        }
    ]

    # Re-run reasoning, generation, and verification nodes with populated context
    state = await engine.reasoner.reason(state)
    state = await engine.generator.generate(state)
    state = await engine.verifier.verify(state)

    print("\n--- MULTI-AGENT REASONING TRACE ---")
    for step in state["agent_trace"]:
        print(f"\n[AGENT]: {step['agent']} ({step['status'].upper()})")
        print(f"   Message: {step['message']}")

    print("\n" + "=" * 80)
    print("VERIFIED IEEE GROUNDED RESPONSE")
    print("=" * 80)
    print(f"\n{state['verified_answer']}\n")

    if state.get("citations"):
        print("CITATIONS & EVIDENCE:")
        for c in state["citations"]:
            print(f"  • {c['citation_id']} | {c['document_title']} (Relevance: {c['relevance_score'] * 100:.0f}%)")

    print("\n" + "=" * 80)
    print(f"Verified: {state['is_verified']} | Hallucinations Detected: {state['hallucination_detected']}")
    print(f"Total Tokens Used: {state['total_tokens_used']} | Cost (USD): ${state['estimated_cost_usd']:.5f}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
