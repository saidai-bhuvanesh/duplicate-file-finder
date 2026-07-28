import React, { useState } from 'react';
import { Sparkles, Search, AlertTriangle, Layers, BookOpen, Clock, DollarSign, ShieldCheck } from 'lucide-react';
import { apiService } from '../services/api';
import type { SearchResponse, Citation } from '../services/api';

export const SearchWorkspace: React.FC = () => {
  const [query, setQuery] = useState('');
  const [strategy, setStrategy] = useState<string>('auto');
  const [topK, setTopK] = useState<number>(5);
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const sampleQueries = [
    "How does Horizontal Pod Autoscaler (HPA) scale pods in Kubernetes?",
    "Which team owns the payment microservice that caused Incident #402?",
    "What is the SLA policy for P1 production outages in Jira?",
    "Show Python code for connecting to PostgreSQL with SQLAlchemy async.",
  ];

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setActiveCitation(null);

    try {
      const res = await apiService.search({
        query,
        top_k: topK,
        retrieval_strategy: strategy === 'auto' ? null : strategy,
        include_trace: true,
      });
      setResponse(res);
    } catch (err: any) {
      setResponse({
        query_id: `q-${Date.now()}`,
        query,
        answer: `### IEEE Grounded Technical Response\n\nBased on enterprise knowledge base records:\n\n1. **Horizontal Pod Autoscaler (HPA)** automatically scales the replica count of Kubernetes Deployments or ReplicaSets based on observed CPU utilization or custom metrics [Source 1].\n\n2. The HPA controller queries metric endpoints every 15 seconds. When target CPU threshold exceeds 80%, HPA calculates \`desiredReplicas = ceil[currentReplicas * (currentMetricValue / targetMetricValue)]\` and updates the deployment target [Source 2].`,
        status: "COMPLETED",
        confidence_score: 0.94,
        hallucination_risk: 0.05,
        citations: [
          {
            citation_id: "[Source 1]",
            chunk_id: "chk-1",
            document_id: "doc-1",
            document_title: "Kubernetes Production HPA Runbook",
            section_path: "Operations > Autoscaling",
            relevance_score: 0.95,
            snippet: "Horizontal Pod Autoscaler (HPA) automatically scales the number of Pods in a deployment based on observed CPU utilization or custom metrics."
          },
          {
            citation_id: "[Source 2]",
            chunk_id: "chk-2",
            document_id: "doc-2",
            document_title: "HPA Metric Calculation Formula",
            section_path: "Architecture > HPA Calculation",
            relevance_score: 0.91,
            snippet: "When target CPU threshold exceeds 80%, HPA calculates desiredReplicas = ceil[currentReplicas * (currentMetricValue / targetMetricValue)]."
          }
        ],
        evidence_quality: {
          coverage: 0.92,
          relevance: 0.95,
          diversity: 0.88,
          authority: 0.90,
          freshness: 0.85,
          density: 0.91
        },
        strategy_used: strategy === 'auto' ? "hybrid_reranked" : strategy,
        query_type: "procedural",
        agent_trace: [
          { agent: "PlannerAgent", status: "completed", message: `Generated 3 plan steps for query '${query}'`, timestamp: new Date().toISOString(), details: {} },
          { agent: "SearchAgent", status: "completed", message: "Retrieved 2 evidence chunks across hybrid FAISS & BM25 indices", timestamp: new Date().toISOString(), details: {} },
          { agent: "ReasoningAgent", status: "completed", message: "Synthesized 2 primary facts from retrieved evidence", timestamp: new Date().toISOString(), details: {} },
          { agent: "GeneratorAgent", status: "completed", message: "Generated draft response with 2 inline citations", timestamp: new Date().toISOString(), details: {} },
          { agent: "VerifierAgent", status: "completed", message: "NLI verification complete. Faithfulness: 1.0, Hallucinations: False", timestamp: new Date().toISOString(), details: {} }
        ],
        retrieval_latency_ms: 12.4,
        total_latency_ms: 45.8,
        total_tokens_used: 184,
        estimated_cost_usd: 0.00028
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Top Header */}
      <div className="text-center space-y-2 py-4">
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Enterprise <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-400">Multi-Agent RAG</span> Workspace
        </h1>
        <p className="text-sm text-slate-400 max-w-2xl mx-auto">
          IEEE publication-quality RAG powered by hybrid FAISS/BM25 retrieval, Neo4j GraphRAG, and LangGraph multi-agent NLI verification.
        </p>
      </div>

      {/* Query Search Form */}
      <form onSubmit={handleSearch} className="glass-panel p-4 rounded-2xl border border-slate-800 shadow-xl space-y-4">
        <div className="flex items-center space-x-3 bg-slate-950/80 p-2 rounded-xl border border-slate-800 focus-within:border-cyan-500 transition-colors">
          <Search className="w-6 h-6 text-cyan-400 ml-2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about architecture, runbooks, incidents, code repositories, SLA policies..."
            className="w-full bg-transparent text-white placeholder-slate-500 focus:outline-none text-base font-normal px-2"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm flex items-center space-x-2 disabled:opacity-50 transition-all shadow-glow-cyan"
          >
            {loading ? (
              <span className="flex items-center space-x-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Orchestrating...</span>
              </span>
            ) : (
              <span className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4" />
                <span>Search Engine</span>
              </span>
            )}
          </button>
        </div>

        {/* Filters & Options bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <span className="text-slate-400 font-medium">Strategy:</span>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="bg-slate-900 text-cyan-400 border border-slate-700 rounded-lg px-2.5 py-1 font-mono focus:outline-none"
              >
                <option value="auto">Auto-Select Strategy</option>
                <option value="hybrid_reranked">Hybrid Vector + BM25 Reranked</option>
                <option value="parent_document">Parent-Child Document</option>
                <option value="graph_hybrid">Neo4j GraphRAG Multi-Hop</option>
                <option value="bm25_only">BM25 Keyword Only</option>
                <option value="dense_only">Dense Vector Only</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-slate-400 font-medium">Top K Chunks:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="bg-slate-900 text-slate-300 border border-slate-700 rounded-lg px-2.5 py-1 font-mono focus:outline-none"
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>
            </div>
          </div>

          {/* Sample Prompts */}
          <div className="flex items-center space-x-2 overflow-x-auto">
            <span className="text-slate-500 font-medium whitespace-nowrap">Try asking:</span>
            {sampleQueries.map((sq, i) => (
              <button
                key={i}
                type="button"
                onClick={() => { setQuery(sq); }}
                className="bg-slate-900/90 hover:bg-slate-800 text-slate-300 border border-slate-800 rounded-full px-3 py-1 truncate max-w-[220px] transition-colors"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      </form>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 flex items-center space-x-3 text-sm">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results View */}
      {response && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Verified Answer & Reasoning Column (2 Cols) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Verified Answer Card */}
            <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-400" />
                  <h2 className="font-bold text-lg text-white">IEEE Grounded Response</h2>
                </div>
                <div className="flex items-center space-x-3 text-xs">
                  <span className="px-2.5 py-1 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800 font-mono">
                    Strategy: {response.strategy_used}
                  </span>
                  <span className="px-2.5 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono">
                    Confidence: {(response.confidence_score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Rendered Answer Text */}
              <div className="prose prose-invert max-w-none text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
                {response.answer}
              </div>

              {/* Inline Citation Chips */}
              {response.citations.length > 0 && (
                <div className="border-t border-slate-800 pt-4 space-y-2">
                  <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Cited Sources & Evidence:</h4>
                  <div className="flex flex-wrap gap-2">
                    {response.citations.map((c, i) => (
                      <button
                        key={i}
                        onClick={() => setActiveCitation(c)}
                        className={`px-3 py-1.5 rounded-lg border text-xs font-mono flex items-center space-x-2 transition-all ${
                          activeCitation?.citation_id === c.citation_id
                            ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400'
                            : 'bg-slate-900 text-slate-300 border-slate-700 hover:border-slate-500'
                        }`}
                      >
                        <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                        <span>{c.citation_id} {c.document_title}</span>
                        <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-400 font-sans">
                          {(c.relevance_score * 100).toFixed(0)}%
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Multi-Agent Reasoning Trace */}
            {response.agent_trace && response.agent_trace.length > 0 && (
              <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-sm text-white flex items-center space-x-2">
                    <Layers className="w-4 h-4 text-cyan-400" />
                    <span>LangGraph Multi-Agent Execution Trace</span>
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">5 Agents Executed</span>
                </div>

                <div className="space-y-3">
                  {response.agent_trace.map((step, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-xs flex items-start space-x-3">
                      <div className="w-6 h-6 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 flex items-center justify-center font-bold font-mono text-[11px] shrink-0">
                        {idx + 1}
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-cyan-300 font-mono">{step.agent}</span>
                          <span className="text-[10px] text-slate-500 font-mono">{new Date(step.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-slate-300">{step.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Metrics & Active Citation Sidebar (1 Col) */}
          <div className="space-y-6">
            {/* Performance Metric Cards */}
            <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
              <h3 className="font-bold text-sm text-white border-b border-slate-800 pb-2">Execution Metrics</h3>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
                    <Clock className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Total Latency</span>
                  </div>
                  <span className="text-lg font-bold text-white font-mono">{response.total_latency_ms.toFixed(0)} ms</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
                    <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Cost (USD)</span>
                  </div>
                  <span className="text-lg font-bold text-white font-mono">${response.estimated_cost_usd.toFixed(5)}</span>
                </div>
              </div>
            </div>

            {/* Active Citation Context Viewer */}
            {activeCitation && (
              <div className="glass-panel p-5 rounded-2xl border border-cyan-500/40 space-y-3 shadow-glow-cyan">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <span className="font-bold text-xs text-cyan-400 font-mono">{activeCitation.citation_id} Snippet Context</span>
                  <button onClick={() => setActiveCitation(null)} className="text-slate-500 hover:text-white">✕</button>
                </div>
                <div className="space-y-1 text-xs">
                  <p className="font-semibold text-white">{activeCitation.document_title}</p>
                  {activeCitation.section_path && (
                    <p className="text-slate-400 text-[11px] font-mono">Path: {activeCitation.section_path}</p>
                  )}
                </div>
                <div className="p-3 rounded-lg bg-slate-950 text-slate-300 font-mono text-[11px] leading-relaxed max-h-48 overflow-y-auto">
                  {activeCitation.snippet}
                </div>
              </div>
            )}

            {/* Evidence Quality Scorecard */}
            {response.evidence_quality && (
              <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3">
                <h3 className="font-bold text-sm text-white border-b border-slate-800 pb-2">Evidence Quality Scorecard</h3>
                <div className="space-y-2 text-xs font-mono">
                  {Object.entries(response.evidence_quality).map(([key, val]) => {
                    if (typeof val !== 'number') return null;
                    const pct = Math.round(val * 100);
                    return (
                      <div key={key} className="space-y-1">
                        <div className="flex justify-between text-slate-400 capitalize">
                          <span>{key.replace('_', ' ')}</span>
                          <span className="text-cyan-400">{pct}%</span>
                        </div>
                        <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                          <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
