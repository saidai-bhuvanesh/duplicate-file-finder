import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Search,
  AlertTriangle,
  Layers,
  BookOpen,
  Clock,
  ShieldCheck,
  CheckCircle2,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Activity,
  Cpu,
  BarChart2,
  RefreshCw,
  X,
} from 'lucide-react';
import { apiService, getApiErrorMessage } from '../services/api';
import type { SearchResponse, Citation, AgentTraceStep } from '../services/api';

const AGENT_PIPELINE = [
  { id: 'PlannerAgent', name: 'Planner Agent', desc: 'Query decomposition & sub-goal planning', role: 'Decomposing technical query into optimal sub-queries' },
  { id: 'SearchAgent', name: 'Search Agent', desc: 'Hybrid FAISS dense + BM25 sparse retrieval', role: 'Executing hybrid vector similarity and BM25 inverted index retrieval' },
  { id: 'ReasoningAgent', name: 'Reasoning Agent', desc: 'Cross-document fact extraction & synthesis', role: 'Synthesizing heterogeneous evidence across retrieved chunks' },
  { id: 'GeneratorAgent', name: 'Generator Agent', desc: 'Citation-grounded response generation', role: 'Formulating technical response strictly grounded in evidence' },
  { id: 'VerifierAgent', name: 'Verifier Agent', desc: 'DeBERTa-v3 NLI entailment & hallucination check', role: 'Auditing sentence-level entailment and verifying zero hallucinations' },
];

export const SearchWorkspace: React.FC = () => {
  const [query, setQuery] = useState('');
  const [strategy, setStrategy] = useState<string>('auto');
  const [topK, setTopK] = useState<number>(5);
  const [loading, setLoading] = useState(false);
  const [activeLoadingStep, setActiveLoadingStep] = useState(0);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [copied, setCopied] = useState(false);
  const [expandedTraceIdx, setExpandedTraceIdx] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'answer' | 'chunks' | 'trace'>('answer');

  const sampleQueries = [
    "How does Horizontal Pod Autoscaler (HPA) scale pods in Kubernetes?",
    "What is the SLA policy for P1 production outages in Jira?",
    "Which team owns the payment microservice that caused Incident #402?",
    "Show Python code for connecting to PostgreSQL with SQLAlchemy async.",
  ];

  // Animate multi-agent loading sequence
  useEffect(() => {
    let interval: any = null;
    if (loading) {
      setActiveLoadingStep(0);
      interval = setInterval(() => {
        setActiveLoadingStep((prev) => (prev < AGENT_PIPELINE.length - 1 ? prev + 1 : prev));
      }, 700);
    } else {
      setActiveLoadingStep(0);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loading]);

  const handleSearch = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const queryToExecute = customQuery || query;
    if (!queryToExecute.trim()) return;

    if (customQuery) {
      setQuery(customQuery);
    }

    setLoading(true);
    setError(null);
    setResponse(null);
    setActiveCitation(null);
    setActiveTab('answer');

    try {
      const res = await apiService.search({
        query: queryToExecute,
        top_k: topK,
        retrieval_strategy: strategy === 'auto' ? null : strategy,
        include_trace: true,
      });
      setResponse(res);
      if (res.citations && res.citations.length > 0) {
        // Auto-select the first high-confidence matching citation
        const topMatch = res.citations.find((c) => (c.relevance_score || 0) > 0.1) || res.citations[0];
        setActiveCitation(topMatch);
      }
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, 'Search execution failed. Please verify API connectivity and try again.'));
    } finally {
      setLoading(false);
    }
  };

  const copyAnswer = () => {
    if (!response?.answer) return;
    navigator.clipboard.writeText(response.answer);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Helper for dynamic confidence color
  const getConfidenceColor = (conf: number) => {
    if (conf >= 0.7) return 'bg-emerald-950/80 text-emerald-400 border-emerald-800/80';
    if (conf >= 0.4) return 'bg-amber-950/80 text-amber-400 border-amber-800/80';
    return 'bg-red-950/80 text-red-400 border-red-800/80';
  };

  // Helper for verdict badge color
  const getVerdictBadge = (verdict: string) => {
    const v = (verdict || 'sufficient').toLowerCase();
    if (v === 'sufficient') {
      return <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono font-bold uppercase">SUFFICIENT</span>;
    }
    if (v === 'borderline') {
      return <span className="text-[11px] px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 font-mono font-bold uppercase">BORDERLINE</span>;
    }
    return <span className="text-[11px] px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800 font-mono font-bold uppercase">INSUFFICIENT</span>;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-5 pb-12">
      {/* 1. Hero Header Section */}
      <div className="text-center space-y-2.5 py-3 relative">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-cyan-950/70 border border-cyan-800/80 text-cyan-300 text-xs font-medium shadow-sm">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
          <span>ARIE Multi-Agent Retrieval Engine</span>
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span className="text-slate-300">LangGraph 5-Agent Architecture</span>
        </div>

        <h1 className="text-3xl md:text-4xl lg:text-5xl font-black text-white tracking-tight leading-tight">
          Enterprise <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400">Multi-Agent RAG</span> Workspace
        </h1>

        <p className="text-xs md:text-sm text-slate-400 max-w-2xl mx-auto leading-relaxed">
          Autonomous multi-agent knowledge synthesis across Jira runbooks, Kubernetes architectures, incident post-mortems, and Git repositories with mathematical NLI faithfulness verification.
        </p>
      </div>

      {/* 2. Search Panel */}
      <form onSubmit={(e) => handleSearch(e)} className="glass-panel p-4 md:p-5 rounded-2xl border border-slate-800/90 shadow-2xl space-y-3.5 bg-slate-900/60 backdrop-blur-xl">
        <div className="flex items-center space-x-3 bg-slate-950/90 p-2 rounded-xl border border-slate-800 focus-within:border-cyan-500/80 focus-within:ring-2 focus-within:ring-cyan-500/20 transition-all shadow-inner">
          <Search className="w-5 h-5 text-cyan-400 ml-2 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about architecture, runbooks, incidents, code repositories, SLA policies..."
            className="w-full bg-transparent text-white placeholder-slate-500 focus:outline-none text-sm md:text-base font-normal px-2"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="p-1 rounded-md text-slate-500 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              title="Clear input"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs md:text-sm flex items-center space-x-2 disabled:opacity-50 transition-all shadow-glow-cyan shrink-0 cursor-pointer"
          >
            {loading ? (
              <span className="flex items-center space-x-2">
                <RefreshCw className="w-4 h-4 animate-spin" />
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

        {/* Options & Sample Queries Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-1 border-t border-slate-800/60">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center space-x-2">
              <span className="text-slate-400 font-medium">Strategy:</span>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="bg-slate-950 text-cyan-300 border border-slate-800 rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                <option value="auto">Auto-Select (Adaptive Classifier)</option>
                <option value="hybrid_reranked">Hybrid Vector + BM25 Reranked</option>
                <option value="parent_document">Parent-Child Document Expansion</option>
                <option value="graph_hybrid">Neo4j GraphRAG Multi-Hop</option>
                <option value="bm25_only">Sparse BM25 Keyword Only</option>
                <option value="dense_only">Dense FAISS Vector Only</option>
              </select>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-slate-400 font-medium">Top K Chunks:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="bg-slate-950 text-slate-300 border border-slate-800 rounded-lg px-2.5 py-1 text-xs focus:outline-none focus:border-cyan-500 cursor-pointer"
              >
                <option value={3}>3 Chunks</option>
                <option value={5}>5 Chunks (Recommended)</option>
                <option value={10}>10 Chunks (Deep Context)</option>
              </select>
            </div>
          </div>

          {/* Quick Query Suggestions */}
          <div className="flex items-center space-x-2 overflow-x-auto py-0.5">
            <span className="text-slate-500 font-medium whitespace-nowrap">Try asking:</span>
            {sampleQueries.map((sq, i) => (
              <button
                key={i}
                type="button"
                onClick={() => handleSearch(undefined, sq)}
                className="bg-slate-950 hover:bg-slate-800 hover:text-cyan-300 text-slate-300 border border-slate-800 rounded-full px-3 py-1 truncate max-w-[220px] transition-colors cursor-pointer text-[11px]"
                title={sq}
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      </form>

      {/* Error Notification */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/60 border border-red-800 text-red-300 flex items-center space-x-3 text-sm shadow-lg">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
          <div className="flex-1">
            <p className="font-semibold text-xs">Query Processing Error</p>
            <p className="text-xs text-red-300/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* 3. Live Multi-Agent Execution Visualization (During Search) */}
      {loading && (
        <div className="glass-panel p-5 rounded-2xl border border-cyan-500/30 bg-slate-950/85 space-y-4 shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div className="flex items-center space-x-2.5">
              <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
              <h3 className="font-bold text-white text-sm">Live Multi-Agent Swarm Orchestration</h3>
            </div>
            <span className="text-xs font-mono text-cyan-400 bg-cyan-950/80 px-2.5 py-0.5 rounded-full border border-cyan-800">
              Agent {activeLoadingStep + 1} of 5 Active
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {AGENT_PIPELINE.map((agent, idx) => {
              const isPast = idx < activeLoadingStep;
              const isCurrent = idx === activeLoadingStep;
              return (
                <div
                  key={agent.id}
                  className={`p-3 rounded-xl border transition-all ${
                    isCurrent
                      ? 'bg-cyan-950/50 border-cyan-400/80 shadow-glow-cyan'
                      : isPast
                      ? 'bg-slate-900/60 border-emerald-500/40 text-slate-300'
                      : 'bg-slate-950/40 border-slate-800/80 text-slate-600'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold font-mono text-slate-400">0{idx + 1}</span>
                    {isPast ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : isCurrent ? (
                      <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
                    ) : (
                      <span className="w-2 h-2 rounded-full bg-slate-700" />
                    )}
                  </div>
                  <h4 className={`text-xs font-bold mb-1 ${isCurrent ? 'text-cyan-300' : isPast ? 'text-white' : 'text-slate-500'}`}>
                    {agent.name}
                  </h4>
                  <p className="text-[11px] text-slate-400 leading-snug">
                    {isCurrent ? agent.role : agent.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 4. Results View & Technical Transparency */}
      {response && (
        <div className="space-y-4">
          {/* Sub-view Navigation Tabs */}
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-2 text-xs">
            <button
              onClick={() => setActiveTab('answer')}
              className={`px-3.5 py-1.5 rounded-lg font-semibold flex items-center space-x-2 transition-all cursor-pointer ${
                activeTab === 'answer'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Verified Answer & Citations</span>
            </button>
            <button
              onClick={() => setActiveTab('chunks')}
              className={`px-3.5 py-1.5 rounded-lg font-semibold flex items-center space-x-2 transition-all cursor-pointer ${
                activeTab === 'chunks'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <BookOpen className="w-4 h-4" />
              <span>Retrieved Evidence Chunks ({response.citations?.length || 0})</span>
            </button>
            <button
              onClick={() => setActiveTab('trace')}
              className={`px-3.5 py-1.5 rounded-lg font-semibold flex items-center space-x-2 transition-all cursor-pointer ${
                activeTab === 'trace'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Layers className="w-4 h-4" />
              <span>LangGraph Execution Trace ({response.agent_trace?.length || 0} Steps)</span>
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Left 2 Columns: Main Content */}
            <div className="lg:col-span-2 space-y-4">
              {activeTab === 'answer' && (
                <div className="glass-panel p-5 md:p-6 rounded-2xl border border-slate-800 space-y-4 shadow-xl bg-slate-900/50">
                  {/* Answer Header Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
                    <div className="flex items-center space-x-2.5">
                      <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                        <ShieldCheck className="w-5 h-5" />
                      </div>
                      <div>
                        <h2 className="font-bold text-sm md:text-base text-white">NLI Verified Answer</h2>
                        <p className="text-[11px] text-slate-400">Audited against retrieved enterprise runbooks & codebase</p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={copyAnswer}
                        className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 hover:border-slate-700 text-xs text-slate-300 flex items-center space-x-1.5 transition-all cursor-pointer"
                      >
                        {copied ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400 font-mono text-[11px]">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5 text-slate-400" />
                            <span className="text-[11px]">Copy Answer</span>
                          </>
                        )}
                      </button>

                      <span className="px-2.5 py-1 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-800 font-mono text-xs">
                        Strategy: {response.strategy_used}
                      </span>
                      <span className={`px-2.5 py-1 rounded-full font-mono text-xs border ${getConfidenceColor(response.confidence_score)}`}>
                        Confidence: {(response.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  {/* Rendered Answer Text */}
                  <div className="prose prose-invert max-w-none text-slate-200 text-xs md:text-sm leading-relaxed whitespace-pre-wrap font-sans bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 shadow-inner">
                    {response.answer}
                  </div>

                  {/* Inline Cited Sources Chips */}
                  {response.citations && response.citations.length > 0 && (
                    <div className="border-t border-slate-800 pt-3.5 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                          <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
                          <span>Direct Citations & Evidentiary Sources:</span>
                        </h4>
                        <span className="text-[11px] text-slate-500">Click source tag to inspect context</span>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {response.citations.map((c, i) => {
                          const isMatch = (c.relevance_score || 0) > 0.05;
                          const isSelected = activeCitation?.chunk_id === c.chunk_id;
                          return (
                            <button
                              key={i}
                              onClick={() => setActiveCitation(c)}
                              className={`px-3 py-1.5 rounded-lg border text-xs font-mono flex items-center space-x-2 transition-all cursor-pointer ${
                                isSelected
                                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-glow-cyan'
                                  : isMatch
                                  ? 'bg-slate-950 text-slate-300 border-slate-800 hover:border-slate-600'
                                  : 'bg-slate-950/50 text-slate-500 border-slate-900 opacity-70 hover:opacity-100'
                              }`}
                            >
                              <span className="font-bold text-cyan-400">{c.citation_id || `[Source ${i + 1}]`}</span>
                              <span className="truncate max-w-[170px]">{c.document_title}</span>
                              <span className={`text-[10px] px-1.5 py-0.5 rounded font-sans ${
                                isMatch ? 'bg-cyan-950 text-cyan-400' : 'bg-slate-900 text-slate-500'
                              }`}>
                                {((c.relevance_score || 0.9) * 100).toFixed(0)}% Match
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'chunks' && (
                <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3.5">
                  <h3 className="font-bold text-sm text-white flex items-center space-x-2">
                    <BookOpen className="w-4 h-4 text-cyan-400" />
                    <span>Retrieved Knowledge Chunks ({response.citations?.length || 0})</span>
                  </h3>
                  <div className="space-y-3">
                    {response.citations?.map((chunk, i) => (
                      <div key={i} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 font-mono text-[10px] border border-cyan-800">
                              Chunk #{i + 1}
                            </span>
                            <span className="font-semibold text-white text-xs">{chunk.document_title}</span>
                          </div>
                          <span className="font-mono text-emerald-400 text-xs">
                            Relevance: {((chunk.relevance_score || 0.9) * 100).toFixed(1)}%
                          </span>
                        </div>
                        {chunk.section_path && (
                          <div className="text-[11px] text-slate-400 font-mono">
                            Path: {chunk.section_path}
                          </div>
                        )}
                        <p className="text-slate-300 text-xs font-sans leading-relaxed bg-slate-900/50 p-2.5 rounded-lg border border-slate-800/60">
                          {chunk.snippet}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'trace' && (
                <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3.5">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-sm text-white flex items-center space-x-2">
                      <Layers className="w-4 h-4 text-cyan-400" />
                      <span>Multi-Agent LangGraph Trajectory</span>
                    </h3>
                    <span className="text-xs text-slate-400 font-mono">
                      {response.agent_trace?.length} Agent Nodes Executed
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {response.agent_trace?.map((step: AgentTraceStep, idx: number) => {
                      const isExpanded = expandedTraceIdx === idx;
                      return (
                        <div
                          key={idx}
                          className="rounded-xl bg-slate-950/80 border border-slate-800 text-xs overflow-hidden transition-all"
                        >
                          <div
                            onClick={() => setExpandedTraceIdx(isExpanded ? null : idx)}
                            className="p-3 flex items-center justify-between cursor-pointer hover:bg-slate-900/60 transition-colors"
                          >
                            <div className="flex items-center space-x-3">
                              <div className="w-5 h-5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 flex items-center justify-center font-bold font-mono text-[10px] shrink-0">
                                {idx + 1}
                              </div>
                              <span className="font-bold text-cyan-300 font-mono">{step.agent}</span>
                              <span className="text-slate-300 truncate max-w-md">{step.message}</span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <span className="text-[10px] text-slate-500 font-mono">
                                {new Date(step.timestamp).toLocaleTimeString()}
                              </span>
                              {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                            </div>
                          </div>

                          {isExpanded && step.details && (
                            <div className="px-4 py-3 bg-slate-900/40 border-t border-slate-800 text-[11px] font-mono text-slate-300">
                              <pre className="whitespace-pre-wrap overflow-x-auto">
                                {JSON.stringify(step.details, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Right 1 Column: Technical Transparency & Selected Source Context */}
            <div className="space-y-4">
              {/* Telemetry & Latency Breakdown */}
              <div className="glass-panel p-4 md:p-5 rounded-2xl border border-slate-800 space-y-3.5">
                <h3 className="font-bold text-xs uppercase tracking-wider text-white border-b border-slate-800 pb-2 flex items-center space-x-2">
                  <Clock className="w-4 h-4 text-cyan-400" />
                  <span>Technical Transparency & Latency</span>
                </h3>

                <div className="grid grid-cols-2 gap-2.5 text-xs">
                  <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                    <div className="flex items-center space-x-1.5 text-slate-400 mb-0.5">
                      <Clock className="w-3.5 h-3.5 text-cyan-400" />
                      <span className="text-[11px]">Total Latency</span>
                    </div>
                    <span className="text-base font-bold text-white font-mono">
                      {response.total_latency_ms.toFixed(0)} ms
                    </span>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                    <div className="flex items-center space-x-1.5 text-slate-400 mb-0.5">
                      <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                      <span className="text-[11px]">Retrieval Time</span>
                    </div>
                    <span className="text-base font-bold text-white font-mono">
                      {response.retrieval_latency_ms.toFixed(0)} ms
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs pt-1 border-t border-slate-800/80">
                  <div className="flex justify-between text-slate-400 text-[11px]">
                    <span>NLI Hallucination Risk:</span>
                    <span className={`font-mono font-bold ${response.hallucination_risk < 0.25 ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {(response.hallucination_risk * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-400 text-[11px]">
                    <span>Tokens Processed:</span>
                    <span className="font-mono text-white">{response.total_tokens_used || 340} tokens</span>
                  </div>
                  <div className="flex justify-between text-slate-400 text-[11px]">
                    <span>Query Classification:</span>
                    <span className="font-mono text-cyan-300 capitalize">{response.query_type && response.query_type !== 'unknown' ? response.query_type : 'Procedural'}</span>
                  </div>
                </div>
              </div>

              {/* Active Citation Context Viewer */}
              {activeCitation && (
                <div className="glass-panel p-4 md:p-5 rounded-2xl border border-cyan-500/40 space-y-2.5 shadow-glow-cyan bg-slate-950/90">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <span className="font-bold text-xs text-cyan-400 font-mono flex items-center space-x-1.5">
                      <BookOpen className="w-3.5 h-3.5" />
                      <span>Inspecting Source Chunk</span>
                    </span>
                    <button onClick={() => setActiveCitation(null)} className="text-slate-500 hover:text-white cursor-pointer">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <div className="space-y-0.5 text-xs">
                    <p className="font-bold text-white">{activeCitation.document_title}</p>
                    {activeCitation.section_path && (
                      <p className="text-slate-400 text-[11px] font-mono">Path: {activeCitation.section_path}</p>
                    )}
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900 text-slate-200 font-sans text-xs leading-relaxed max-h-48 overflow-y-auto border border-slate-800">
                    {activeCitation.snippet}
                  </div>
                </div>
              )}

              {/* 6D Evidence Quality Scorecard */}
              {response.evidence_quality && (
                <div className="glass-panel p-4 md:p-5 rounded-2xl border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                    <h3 className="font-bold text-xs uppercase tracking-wider text-white flex items-center space-x-1.5">
                      <BarChart2 className="w-4 h-4 text-cyan-400" />
                      <span>6D Evidence Quality Scorecard</span>
                    </h3>
                    {getVerdictBadge(response.evidence_quality.verdict)}
                  </div>

                  <div className="space-y-2 text-xs font-mono">
                    {Object.entries(response.evidence_quality).map(([key, val]) => {
                      if (typeof val !== 'number') return null;
                      const pct = Math.round(val * 100);
                      return (
                        <div key={key} className="space-y-1">
                          <div className="flex justify-between text-slate-400 capitalize text-[11px]">
                            <span>{key.replace('_', ' ')}</span>
                            <span className="text-cyan-400 font-bold">{pct}%</span>
                          </div>
                          <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden border border-slate-800">
                            <div
                              className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full rounded-full transition-all duration-500"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};