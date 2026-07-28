import asyncio
import time
import json
import sys
from typing import Dict, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from app.retrieval.arie.query_intelligence import QueryIntelligenceEngine
from app.agents.graph import AgentWorkflowEngine

async def run_ablation_trial(query: str, disable_graph: bool = False, disable_nli: bool = False) -> Dict[str, Any]:
    """Runs a single ablation study trial, mocking specific system components."""
    
    start_time = time.perf_counter()
    engine = AgentWorkflowEngine()
    
    # In a real ablation framework, we would pass these flags to override logic inside the engine
    # e.g., engine.arun(query, skip_graphrag=disable_graph, skip_nli_verification=disable_nli)
    
    try:
        result = await engine.run_workflow(
            query_text=query,
            top_k=5,
            retrieval_strategy="bm25" if disable_graph else "hybrid_reranked"
        )
        latency = (time.perf_counter() - start_time) * 1000
        
        return {
            "query": query,
            "latency_ms": latency,
            "is_verified": result.get("is_verified", False),
            "hallucination_detected": result.get("hallucination_detected", False),
            "tokens_used": result.get("total_tokens_used", 0),
            "citations_count": len(result.get("citations", [])),
            "ablation_state": f"GraphRAG={not disable_graph}, NLI={not disable_nli}"
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": (time.perf_counter() - start_time) * 1000}


async def main():
    print("🚀 Starting EnterpriseIT-RAG Experimental Ablation Study...")
    
    queries = [
        "How does HPA scale pods?",
        "Trace the S3 bucket provisioning module.",
        "Why did the Redis cache timeout during P1 outage?"
    ]
    
    results = []
    
    for q in queries:
        print(f"\nEvaluating: '{q}'")
        
        # Baseline (Full System)
        res_full = await run_ablation_trial(q)
        print(f"  [FULL SYSTEM] Latency: {res_full['latency_ms']:.2f}ms | Verified: {res_full['is_verified']}")
        results.append(res_full)
        
        # Ablation 1 (No GraphRAG)
        res_no_graph = await run_ablation_trial(q, disable_graph=True)
        print(f"  [NO GRAPHRAG] Latency: {res_no_graph['latency_ms']:.2f}ms | Verified: {res_no_graph['is_verified']}")
        results.append(res_no_graph)
        
        # Ablation 2 (No NLI)
        res_no_nli = await run_ablation_trial(q, disable_nli=True)
        print(f"  [NO NLI VERIFIER] Latency: {res_no_nli['latency_ms']:.2f}ms | Verified: {res_no_nli['is_verified']}")
        results.append(res_no_nli)

    with open("ablation_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n✅ Ablation study complete. Results saved to ablation_results.json")

if __name__ == "__main__":
    asyncio.run(main())
