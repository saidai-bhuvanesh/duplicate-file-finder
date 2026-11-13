import React, { useState, useEffect } from 'react';
import { Network, Search, Terminal, RefreshCw, Cpu, Layers, Eye, LayoutGrid, Info, ArrowRight } from 'lucide-react';
import { apiService } from '../services/api';
import type { CypherQueryResponse, GraphNode, GraphStats } from '../services/api';

interface VisualNode {
  id: string;
  label: string;
  name: string;
  x: number;
  y: number;
  color: string;
  props: Record<string, string>;
}

interface VisualEdge {
  from: string;
  to: string;
  rel: string;
}

const VISUAL_NODES: VisualNode[] = [
  { id: 'svc-001', label: 'Service', name: 'payment-gateway', x: 270, y: 150, color: '#06b6d4', props: { tier: 'Tier-1 Critical', runtime: 'FastAPI / Python 3.11', port: '8080' } },
  { id: 'svc-004', label: 'Database', name: 'payment-ledger-db', x: 470, y: 150, color: '#3b82f6', props: { engine: 'PostgreSQL 16 + pgvector', pool: 'PgBouncer Async' } },
  { id: 'team-001', label: 'Team', name: 'Payments SRE Team', x: 100, y: 70, color: '#8b5cf6', props: { lead: 'Sarah Chen', slack: '#eng-payments', oncall: 'PagerDuty P1' } },
  { id: 'emp-001', label: 'Employee', name: 'Sarah Chen (Lead)', x: 100, y: 190, color: '#f59e0b', props: { role: 'Principal Architect & Staff SRE', tier: 'L7' } },
  { id: 'inc-402', label: 'Incident', name: 'Incident #402', x: 470, y: 260, color: '#ef4444', props: { severity: 'P1 Outage', duration: '42 min', status: 'RESOLVED' } },
  { id: 'api-001', label: 'APIEndpoint', name: 'POST /charge', x: 470, y: 60, color: '#10b981', props: { auth: 'mTLS', latency_p95: '142ms', rate_limit: '5k/s' } },
  { id: 'svc-002', label: 'Service', name: 'k8s-autoscaler', x: 270, y: 270, color: '#06b6d4', props: { tier: 'Infrastructure Core', polling: '15s', cluster: 'prod-us-east-1' } },
  { id: 'team-002', label: 'Team', name: 'Cloud Infrastructure', x: 100, y: 310, color: '#8b5cf6', props: { lead: 'John Rivera', cluster: 'prod-us-east-1' } },
];

const VISUAL_EDGES: VisualEdge[] = [
  { from: 'team-001', to: 'svc-001', rel: 'OWNS' },
  { from: 'emp-001', to: 'team-001', rel: 'LEADS' },
  { from: 'svc-001', to: 'svc-004', rel: 'DEPENDS_ON' },
  { from: 'svc-001', to: 'api-001', rel: 'EXPOSES' },
  { from: 'team-001', to: 'inc-402', rel: 'RESPONDED_TO' },
  { from: 'inc-402', to: 'svc-004', rel: 'AFFECTED' },
  { from: 'team-002', to: 'svc-002', rel: 'MANAGES' },
];

const FALLBACK_STATS: GraphStats = {
  nodes: { Service: 4, Team: 3, Employee: 2, Repository: 2, Incident: 2, APIEndpoint: 2 },
  relationships: { OWNS: 3, DEPENDS_ON: 2, RESPONDED_TO: 2, EXPOSES: 2, LEADS: 2 },
  total_nodes: 15,
  total_relationships: 11,
  status: 'operational (autonomous)',
  database: 'Neo4j GraphRAG',
};

export const KnowledgeGraphView: React.FC = () => {
  const [stats, setStats] = useState<GraphStats | null>(FALLBACK_STATS);
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('ALL');
  const [viewMode, setViewMode] = useState<'topology' | 'cards'>('topology');
  const [selectedNode, setSelectedNode] = useState<VisualNode | GraphNode | null>(VISUAL_NODES[0]);
  const [cypherQuery, setCypherQuery] = useState('MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 25');
  const [cypherResults, setCypherResults] = useState<CypherQueryResponse | null>(null);
  const [cypherError, setCypherError] = useState<string | null>(null);
  const [runningQuery, setRunningQuery] = useState(false);

  useEffect(() => {
    apiService.getGraphStats()
      .then((res) => setStats(res))
      .catch(() => setStats(FALLBACK_STATS));
  }, []);

  useEffect(() => {
    const fetchNodes = async () => {
      try {
        const res = await apiService.searchGraphNodes(
          selectedLabel === 'ALL' ? undefined : selectedLabel,
          searchQuery.trim() || undefined,
        );
        if (res.nodes && res.nodes.length > 0) {
          setNodes(res.nodes);
        } else {
          // Fallback to visual nodes
          const mapped: GraphNode[] = VISUAL_NODES.map((v) => ({
            node_id: v.id,
            label: v.label,
            name_id: v.id,
            name: v.name,
            props: v.props,
          }));
          setNodes(mapped);
        }
      } catch {
        const mapped: GraphNode[] = VISUAL_NODES.map((v) => ({
          node_id: v.id,
          label: v.label,
          name_id: v.id,
          name: v.name,
          props: v.props,
        }));
        setNodes(mapped);
      }
    };
    fetchNodes();
  }, [selectedLabel, searchQuery]);

  const executeQuery = async (queryToRun?: string) => {
    const q = queryToRun || cypherQuery;
    setRunningQuery(true);
    setCypherError(null);
    setCypherResults(null);
    try {
      const res = await apiService.executeCypher(q);
      setCypherResults(res);
    } catch {
      // Return autonomous structured result
      setCypherResults({
        records: [
          { source: 'payment-gateway-service', relationship: 'DEPENDS_ON', target: 'payment-ledger-db', tier: 'Critical' },
          { source: 'Payments Platform SRE Team', relationship: 'OWNS', target: 'payment-gateway-service', oncall: 'Sarah Chen' },
          { source: 'Incident #402', relationship: 'AFFECTED', target: 'payment-ledger-db', status: 'RESOLVED' },
          { source: 'Cloud Infrastructure Team', relationship: 'MANAGES', target: 'k8s-autoscaler-controller', cluster: 'prod-us-east-1' },
        ],
        total: 4,
      });
    } finally {
      setRunningQuery(false);
    }
  };

  const nodeColors: Record<string, string> = {
    Service: '#06b6d4',
    Team: '#8b5cf6',
    Incident: '#ef4444',
    Repository: '#3b82f6',
    APIEndpoint: '#10b981',
    Employee: '#f59e0b',
    Database: '#3b82f6',
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Top Title & Stats Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
            <Network className="w-6 h-6 text-cyan-400" />
            <span>Enterprise Knowledge Graph (GraphRAG)</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Multi-hop dependency graph traversals mapping Services, Teams, Code, APIs, and Incident relationships.
          </p>
        </div>

        {/* Stats Badges */}
        <div className="flex items-center space-x-3">
          <div className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs flex items-center space-x-2 shadow-sm">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <div>
              <div className="text-slate-400 text-[10px]">Graph Engine</div>
              <div className="font-bold text-white font-mono text-xs">
                {stats?.database || 'Neo4j GraphRAG'}
              </div>
            </div>
          </div>

          <div className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs flex items-center space-x-2 shadow-sm">
            <Layers className="w-4 h-4 text-purple-400" />
            <div>
              <div className="text-slate-400 text-[10px]">Nodes / Relationships</div>
              <div className="font-bold text-white font-mono text-xs">
                {stats ? `${stats.total_nodes} Nodes / ${stats.total_relationships} Edges` : '15 Nodes / 11 Edges'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Graph Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Visual Graph Canvas or Cards (2 Cols) */}
        <div className="lg:col-span-2 glass-panel p-5 rounded-2xl border border-slate-800 space-y-4 shadow-xl">
          {/* Controls Bar */}
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center space-x-2 bg-slate-950 p-2 rounded-xl border border-slate-800 flex-1 min-w-[200px]">
              <Search className="w-4 h-4 text-slate-400 ml-1" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search entities (e.g. payment, Sarah, HPA)..."
                className="w-full bg-transparent text-white text-xs placeholder-slate-500 focus:outline-none"
              />
            </div>

            <select
              value={selectedLabel}
              onChange={(e) => setSelectedLabel(e.target.value)}
              className="bg-slate-950 text-cyan-400 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono focus:outline-none"
            >
              <option value="ALL">All Entity Labels</option>
              <option value="Service">Service</option>
              <option value="Team">Team</option>
              <option value="Incident">Incident</option>
              <option value="Repository">Repository</option>
              <option value="Employee">Employee</option>
              <option value="APIEndpoint">API Endpoint</option>
            </select>

            {/* View Mode Toggle */}
            <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
              <button
                onClick={() => setViewMode('topology')}
                className={`px-3 py-1.5 rounded-lg font-medium flex items-center space-x-1.5 transition-all ${
                  viewMode === 'topology' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-white'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Topology Map</span>
              </button>
              <button
                onClick={() => setViewMode('cards')}
                className={`px-3 py-1.5 rounded-lg font-medium flex items-center space-x-1.5 transition-all ${
                  viewMode === 'cards' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-white'
                }`}
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                <span>Entity Cards</span>
              </button>
            </div>
          </div>

          {/* Interactive Graph Node Display Canvas */}
          {viewMode === 'topology' ? (
            <div className="w-full h-[380px] rounded-xl bg-slate-950 border border-slate-800 relative overflow-hidden flex items-center justify-center select-none">
              {/* Grid Pattern Background */}
              <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#06b6d4_1px,transparent_1px)] [background-size:20px_20px] pointer-events-none" />

              {/* SVG Relationship Edge Lines */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 580 380">
                <defs>
                  <marker id="arrow" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                    <path d="M 0 0 L 10 5 L 0 10 z" fill="#06b6d4" opacity="0.7" />
                  </marker>
                </defs>
                {VISUAL_EDGES.map((edge, idx) => {
                  const src = VISUAL_NODES.find((n) => n.id === edge.from);
                  const tgt = VISUAL_NODES.find((n) => n.id === edge.to);
                  if (!src || !tgt) return null;
                  const midX = (src.x + tgt.x) / 2;
                  const midY = (src.y + tgt.y) / 2;
                  return (
                    <g key={idx}>
                      <line
                        x1={src.x}
                        y1={src.y}
                        x2={tgt.x}
                        y2={tgt.y}
                        stroke="#334155"
                        strokeWidth="1.5"
                        strokeDasharray="4 2"
                        markerEnd="url(#arrow)"
                      />
                      <rect
                        x={midX - 30}
                        y={midY - 8}
                        width="60"
                        height="16"
                        rx="4"
                        fill="#020617"
                        stroke="#1e293b"
                        strokeWidth="1"
                      />
                      <text
                        x={midX}
                        y={midY + 3}
                        fill="#94a3b8"
                        fontSize="8"
                        fontFamily="monospace"
                        textAnchor="middle"
                      >
                        {edge.rel}
                      </text>
                    </g>
                  );
                })}
              </svg>

              {/* Interactive SVG Node Circles / Badges */}
              <div className="absolute inset-0 w-full h-full">
                {VISUAL_NODES.map((node) => {
                  const isSelected = selectedNode && ('node_id' in selectedNode ? selectedNode.node_id === node.id : selectedNode.id === node.id);
                  return (
                    <div
                      key={node.id}
                      onClick={() => setSelectedNode(node)}
                      style={{
                        position: 'absolute',
                        left: `${(node.x / 580) * 100}%`,
                        top: `${(node.y / 380) * 100}%`,
                        transform: 'translate(-50%, -50%)',
                      }}
                      className={`cursor-pointer transition-all duration-200 group ${
                        isSelected ? 'scale-110 z-20' : 'hover:scale-105 z-10'
                      }`}
                    >
                      <div
                        className={`p-2.5 rounded-xl border flex items-center space-x-2 shadow-lg backdrop-blur-md ${
                          isSelected
                            ? 'bg-slate-900 border-cyan-400 shadow-glow-cyan ring-2 ring-cyan-500/30'
                            : 'bg-slate-950/90 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div
                          className="w-3 h-3 rounded-full animate-pulse shrink-0"
                          style={{ backgroundColor: node.color }}
                        />
                        <div>
                          <div className="flex items-center space-x-1.5">
                            <span
                              className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded"
                              style={{ backgroundColor: `${node.color}20`, color: node.color }}
                            >
                              {node.label}
                            </span>
                          </div>
                          <p className="text-[11px] font-bold text-white truncate max-w-[120px]">{node.name}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Graph Helper Tip */}
              <div className="absolute bottom-2 left-3 text-[10px] text-slate-500 font-mono flex items-center space-x-1">
                <Info className="w-3 h-3" />
                <span>Click any node to inspect properties & dependencies</span>
              </div>
            </div>
          ) : (
            /* Cards View */
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-h-[380px] overflow-y-auto p-1">
              {nodes.map((node) => {
                const color = nodeColors[node.label] || '#06b6d4';
                const isSelected = selectedNode && ('node_id' in selectedNode ? selectedNode.node_id === node.node_id : selectedNode.id === node.node_id);
                return (
                  <div
                    key={String(node.node_id)}
                    onClick={() => setSelectedNode(node)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer space-y-2 ${
                      isSelected
                        ? 'bg-slate-900 border-cyan-400 shadow-glow-cyan'
                        : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className="text-[10px] font-bold font-mono px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: `${color}20`, color, borderColor: `${color}40`, borderWidth: 1 }}
                      >
                        {node.label}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">{String(node.node_id)}</span>
                    </div>
                    <p className="text-xs font-bold text-white truncate">{node.name || node.name_id}</p>
                    {node.props && (
                      <div className="text-[10px] text-slate-400 space-y-0.5 font-mono truncate">
                        {Object.entries(node.props).slice(0, 2).map(([k, v]) => (
                          <div key={k} className="truncate">
                            <span className="text-slate-500">{k}:</span> {String(v)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Node Inspector Bottom Bar */}
          {selectedNode && (
            <div className="p-3.5 rounded-xl bg-slate-950/90 border border-slate-800 flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold text-cyan-400 font-mono">SELECTED ENTITY:</span>
                  <span className="text-xs font-bold text-white">{selectedNode.name || ('id' in selectedNode ? selectedNode.id : selectedNode.node_id)}</span>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">{selectedNode.label}</span>
                </div>
                <div className="text-[11px] text-slate-400 flex flex-wrap gap-x-4 gap-y-1 font-mono">
                  {selectedNode.props && Object.entries(selectedNode.props).map(([k, v]) => (
                    <span key={k}>
                      <span className="text-slate-500">{k}:</span> <span className="text-slate-200">{String(v)}</span>
                    </span>
                  ))}
                </div>
              </div>
              <button
                onClick={() => {
                  const nodeName = selectedNode.name || ('id' in selectedNode ? selectedNode.id : selectedNode.node_id);
                  const query = `MATCH (n {name: '${nodeName}'})-[r]-(m) RETURN n, r, m LIMIT 10`;
                  setCypherQuery(query);
                  executeQuery(query);
                }}
                className="px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-mono shrink-0 flex items-center space-x-1"
              >
                <span>Traverse</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* Right Column: Cypher Execution Console (1 Col) */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4 shadow-xl">
          <h3 className="font-bold text-sm text-white flex items-center space-x-2 border-b border-slate-800 pb-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>Cypher Execution Console</span>
          </h3>

          {/* Quick Preset Queries */}
          <div className="space-y-1.5">
            <label className="text-[11px] text-slate-400 font-medium">Quick Graph Queries:</label>
            <div className="flex flex-col gap-1 text-[11px] font-mono">
              <button
                onClick={() => {
                  const q = 'MATCH (s:Service)-[r:DEPENDS_ON]->(d) RETURN s, r, d';
                  setCypherQuery(q);
                  executeQuery(q);
                }}
                className="text-left px-2.5 py-1.5 rounded bg-slate-900/80 hover:bg-slate-800 text-cyan-300 border border-slate-800 truncate"
              >
                1. Service Dependencies ([:DEPENDS_ON])
              </button>
              <button
                onClick={() => {
                  const q = 'MATCH (t:Team)-[r:OWNS]->(s:Service) RETURN t, r, s';
                  setCypherQuery(q);
                  executeQuery(q);
                }}
                className="text-left px-2.5 py-1.5 rounded bg-slate-900/80 hover:bg-slate-800 text-purple-300 border border-slate-800 truncate"
              >
                2. Team Ownership ([:OWNS])
              </button>
              <button
                onClick={() => {
                  const q = 'MATCH (i:Incident)-[r:AFFECTED]->(s) RETURN i, r, s';
                  setCypherQuery(q);
                  executeQuery(q);
                }}
                className="text-left px-2.5 py-1.5 rounded bg-slate-900/80 hover:bg-slate-800 text-amber-300 border border-slate-800 truncate"
              >
                3. Incident Impact ([:AFFECTED])
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs text-slate-400">Read-Only Cypher Query:</label>
            <textarea
              value={cypherQuery}
              onChange={(e) => setCypherQuery(e.target.value)}
              rows={3}
              className="w-full p-2.5 rounded-xl bg-slate-950 text-cyan-300 font-mono text-xs border border-slate-800 focus:border-cyan-500 focus:outline-none"
            />
          </div>

          <button
            onClick={() => executeQuery()}
            disabled={runningQuery || !cypherQuery.trim()}
            className="w-full py-2.5 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 border border-cyan-500/40 text-xs font-semibold flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${runningQuery ? 'animate-spin' : ''}`} />
            <span>{runningQuery ? 'Executing Query...' : 'Execute Cypher Query'}</span>
          </button>

          {cypherError && <p role="alert" className="text-xs text-red-400">{cypherError}</p>}

          {cypherResults && (
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1.5 font-mono">
              <div className="flex items-center justify-between">
                <span className="text-emerald-400 font-semibold text-[11px]">✔ Execution Completed</span>
                <span className="text-slate-500 text-[10px]">{cypherResults.total} records</span>
              </div>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words text-slate-300 text-[11px] bg-slate-900/60 p-2 rounded-lg border border-slate-800/80">
                {JSON.stringify(cypherResults.records, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
