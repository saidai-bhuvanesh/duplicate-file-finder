import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

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

export interface HealthResponse {
  status: string;
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
  nodes: Record<string, number>;
  relationships: Record<string, number>;
  total_nodes: number;
  total_relationships: number;
  status: string;
  database: string;
}

export interface GraphNode {
  node_id: number | string;
  label: string;
  name_id: string | null;
  name: string | null;
  props: Record<string, unknown>;
}

export interface GraphNodesResponse {
  nodes: GraphNode[];
  total: number;
  message?: string;
}

export interface CypherQueryResponse {
  records: Record<string, unknown>[];
  total: number;
}

export interface DocumentSummary {
  id: string;
  title: string;
  document_type: string;
  source_system: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

export interface DocumentListResponse {
  items: DocumentSummary[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface IngestionJobResponse {
  job_id: string;
  task_id: string;
  status: string;
  message: string;
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
  async getBackendStatus(): Promise<'ready' | 'degraded'> {
    const health = await apiClient.get<HealthResponse>('/health', { timeout: 5000 });
    if (health.data.status !== 'healthy') {
      throw new Error('Backend health check failed.');
    }

    try {
      await apiClient.get('/ready', { timeout: 5000 });
      return 'ready';
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 503) {
        return 'degraded';
      }
      throw error;
    }
  },

  async getHealth(): Promise<HealthResponse> {
    const res = await apiClient.get<HealthResponse>('/health', { timeout: 5000 });
    return res.data;
  },

  // Search API
  async search(params: SearchRequest): Promise<SearchResponse> {
    const res = await apiClient.post<SearchResponse>('/search/', params);
    return res.data;
  },

  // Knowledge Graph API
  async getGraphStats(): Promise<GraphStats> {
    const res = await apiClient.get<GraphStats>('/graph/stats');
    return res.data;
  },

  async searchGraphNodes(label?: string, search?: string): Promise<GraphNodesResponse> {
    const res = await apiClient.get<GraphNodesResponse>('/graph/nodes', {
      params: { label, search },
    });
    return res.data;
  },

  async executeCypher(cypher: string): Promise<CypherQueryResponse> {
    const res = await apiClient.post<CypherQueryResponse>('/graph/cypher', { cypher });
    return res.data;
  },

  // Evaluation API
  async getEvalRuns(): Promise<EvalRun[]> {
    const res = await apiClient.get<EvalRun[]>('/evaluation/runs');
    return res.data;
  },

  async triggerEvalRun(name: string, dataset_name: string): Promise<any> {
    const res = await apiClient.post('/evaluation/runs', { name, dataset_name });
    return res.data;
  },

  // Ingestion API
  async getDocuments(): Promise<DocumentListResponse> {
    const res = await apiClient.get<DocumentListResponse>('/documents/');
    return res.data;
  },

  async uploadDocument(file: File): Promise<IngestionJobResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<IngestionJobResponse>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
};

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const message = detail.message;
      if (typeof message === 'string') return message;
    }
    if (!error.response) return 'Unable to reach the API. Check that the backend is running.';
  }

  return error instanceof Error ? error.message : fallback;
}
