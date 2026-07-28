import asyncio
import json
import sys

# Ensure UTF-8 output encoding for Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.agents.graph import AgentWorkflowEngine

async def main():
    print("=" * 80)
    print("ENTERPRISEIT-RAG MULTI-AGENT PIPELINE DEMO")
    print("=" * 80)

    query_text = "How does Horizontal Pod Autoscaler (HPA) scale pods in Kubernetes?"
    print(f"\n[USER QUERY]: '{query_text}'\n")

    engine = AgentWorkflowEngine()

    state = await engine.run_workflow(
        query_text=query_text,
        top_k=5,
        retrieval_strategy="hybrid_reranked"
    )

    print("\n--- MULTI-AGENT REASONING TRACE ---")
    for step in state["agent_trace"]:
        print(f"\n[AGENT]: {step['agent']} ({step['status'].upper()})")
        print(f"   Message: {step['message']}")
        if step.get('details'):
            print(f"   Details: {json.dumps(step['details'], indent=2)}")

    print("\n" + "=" * 80)
    print("VERIFIED IEEE GROUNDED RESPONSE")
    print("=" * 80)
    print(f"\n{state['verified_answer']}\n")

    print("=" * 80)
    print(f"Verified: {state['is_verified']} | Hallucinations Detected: {state['hallucination_detected']}")
    print(f"Total Tokens Used: {state['total_tokens_used']} | Cost (USD): ${state['estimated_cost_usd']:.5f}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
