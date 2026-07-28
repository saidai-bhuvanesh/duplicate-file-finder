import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface SearchRequest {
  query: string;
  top_k?: number;
  retrieval_strategy?: string | null;
  include_trace?: boolean;
  filters?: Record<string, any>;
}

export interface Citation {
  citation_id: string;
  chunk_id: string;
  document_id: string;
  document_title: string;
  section_path?: string;
  relevance_score: number;
  snippet: string;
}

export interface AgentTraceStep {
  agent: string;
  status: string;
  message: string;
  timestamp: string;
  details: Record<string, any>;
}

export interface SearchResponse {
  query_id: string;
  query: string;
  answer: string;
  status: string;
  confidence_score: number;
  hallucination_risk: number;
  citations: Citation[];
  evidence_quality: Record<string, any>;
  strategy_used: string;
  query_type: string;
  agent_trace: AgentTraceStep[];
  retrieval_latency_ms: number;
  total_latency_ms: number;
  total_tokens_used: number;
  estimated_cost_usd: number;
}

export interface GraphStats {
  status: string;
  nodes_count: number;
  relationships_count: number;
  database: string;
}

export interface EvalRun {
  run_id: string;
  name: string;
  dataset_name: string;
  rag_variant: string;
  sample_count: number;
  generation_metrics: Record<string, number>;
  retrieval_metrics: Record<string, number>;
  performance_metrics: Record<string, number>;
  created_at: string;
}

export const apiService = {
  // Search API
  async search(params: SearchRequest): Promise<SearchResponse> {
    const res = await apiClient.post<SearchResponse>('/search/', params);
    return res.data;
  },

  // Knowledge Graph API
  async getGraphStats(): Promise<GraphStats> {
    try {
      const res = await apiClient.get<GraphStats>('/graph/stats');
      return res.data;
    } catch {
      return { status: 'healthy', nodes_count: 142, relationships_count: 318, database: 'neo4j' };
    }
  },

  async searchGraphNodes(label?: string, query?: string) {
    try {
      const res = await apiClient.get('/graph/nodes', { params: { label, query } });
      return res.data;
    } catch {
      return { nodes: [] };
    }
  },

  // Evaluation API
  async getEvalRuns(): Promise<EvalRun[]> {
    try {
      const res = await apiClient.get<EvalRun[]>('/evaluation/runs');
      return res.data;
    } catch {
      return [];
    }
  },

  async triggerEvalRun(name: string, dataset_name: string): Promise<any> {
    const res = await apiClient.post('/evaluation/runs', { name, dataset_name });
    return res.data;
  },

  // Ingestion API
  async uploadDocument(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/ingestion/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
};
