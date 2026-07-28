import random
from locust import HttpUser, task, between

SAMPLE_QUERIES = [
    "How does HPA scale pods?",
    "Which team owns the payment microservice?",
    "What is the SLA policy for P1 incidents?",
    "Show Python code for connecting to Redis cache.",
    "Trace the S3 bucket provisioning module in Terraform.",
    "Why did the database connection pool exhaust during Black Friday load?",
    "Explain the NLI verification step in the retrieval pipeline."
]

class RAGEnterpriseUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def query_search(self):
        query = random.choice(SAMPLE_QUERIES)
        payload = {
            "query_text": query,
            "top_k": 5,
            "retrieval_strategy": "auto"
        }
        headers = {"Content-Type": "application/json"}
        self.client.post("/api/v1/search", json=payload, headers=headers, name="/api/v1/search")

    @task(1)
    def check_health(self):
        self.client.get("/health", name="/health")

    @task(1)
    def fetch_metrics(self):
        self.client.get("/api/v1/metrics", name="/api/v1/metrics")
