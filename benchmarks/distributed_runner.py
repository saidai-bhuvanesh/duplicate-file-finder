import asyncio
import time
import json
import csv
import math
from typing import List, Dict, Any
import httpx

API_URL = "http://localhost:8000/api/v1/search"

# Generation of 1000-query synthetic test suite matrix
DOMAINS = ["Kubernetes", "AWS", "Azure", "GCP", "Terraform", "Security", "Networking", "Database", "IncidentResponse", "CI_CD"]
STRATEGIES = ["bm25", "dense", "hybrid_reranked", "graph_traversal"]

def generate_benchmark_queries(total: int = 1000) -> List[Dict[str, Any]]:
    queries = []
    for i in range(total):
        domain = DOMAINS[i % len(DOMAINS)]
        strat = STRATEGIES[i % len(STRATEGIES)]
        queries.append({
            "id": f"Q-{i+1:04d}",
            "domain": domain,
            "query_text": f"Evaluate {domain} configuration and architectural relationship for scenario #{i+1}.",
            "expected_strategy": strat,
            "difficulty": "Medium" if i % 2 == 0 else "Hard"
        })
    return queries

def calculate_stats(data: List[float]) -> Dict[str, float]:
    if not data:
        return {"mean": 0, "std_dev": 0, "ci95_low": 0, "ci95_high": 0}
    n = len(data)
    mean = sum(data) / n
    variance = sum((x - mean) ** 2 for x in data) / n if n > 1 else 0
    std_dev = math.sqrt(variance)
    margin = 1.96 * (std_dev / math.sqrt(n)) if n > 0 else 0
    return {
        "mean": round(mean, 2),
        "std_dev": round(std_dev, 2),
        "ci95_low": round(mean - margin, 2),
        "ci95_high": round(mean + margin, 2)
    }

async def run_distributed_benchmark():
    print("🚀 Initializing 1,000-Query Distributed Benchmark Runner...")
    queries = generate_benchmark_queries(1000)
    
    results = []
    latencies = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for idx, q in enumerate(queries):
            start = time.perf_counter()
            try:
                # Simulate request to API endpoint (or hit live if running)
                response = await client.post(API_URL, json={
                    "query_text": q["query_text"],
                    "top_k": 5,
                    "retrieval_strategy": q["expected_strategy"]
                })
                elapsed = (time.perf_counter() - start) * 1000
                status = response.status_code
                is_verified = True if status == 200 else False
            except Exception:
                elapsed = (time.perf_counter() - start) * 1000
                status = 500
                is_verified = False

            latencies.append(elapsed)
            results.append({
                "query_id": q["id"],
                "domain": q["domain"],
                "strategy": q["expected_strategy"],
                "latency_ms": round(elapsed, 2),
                "status_code": status,
                "verified": is_verified
            })

            if (idx + 1) % 100 == 0:
                print(f"  Processed {idx + 1}/1000 queries...")

    # Calculate Statistical Summary
    stats = calculate_stats(latencies)
    print("\n📊 Benchmark Execution Completed!")
    print(f"  Mean Latency: {stats['mean']} ms")
    print(f"  Standard Deviation: {stats['std_dev']} ms")
    print(f"  95% Confidence Interval: [{stats['ci95_low']} ms, {stats['ci95_high']} ms]")

    # Persist CSV & JSON Artifacts
    with open("benchmarks_raw_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["query_id", "domain", "strategy", "latency_ms", "status_code", "verified"])
        writer.writeheader()
        writer.writerows(results)

    with open("benchmark_statistical_summary.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_queries": len(queries),
            "statistics": stats,
            "samples": results[:10]
        }, f, indent=2)

    print("✅ Raw results saved to 'benchmarks_raw_results.csv' and 'benchmark_statistical_summary.json'.")

if __name__ == "__main__":
    asyncio.run(run_distributed_benchmark())
