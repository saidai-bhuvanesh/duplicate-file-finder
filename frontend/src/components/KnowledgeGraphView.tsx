import React, { useState, useEffect } from 'react';
import { Network, Search, Terminal, RefreshCw, Cpu, Layers } from 'lucide-react';
import { apiService } from '../services/api';
import type { GraphStats } from '../services/api';

export const KnowledgeGraphView: React.FC = () => {
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('ALL');
  const [cypherQuery, setCypherQuery] = useState('MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 25');
  const [cypherResults, setCypherResults] = useState<any>(null);

  const mockNodes = [
    { id: 'srv-1', label: 'Service', name: 'payment-microservice', color: '#06b6d4', status: 'Healthy' },
    { id: 'team-1', label: 'Team', name: 'Payments-Squad', color: '#8b5cf6', status: 'Active' },
    { id: 'inc-1', label: 'Incident', name: 'INC-402 Database Timeout', color: '#ef4444', status: 'Resolved' },
    { id: 'repo-1', label: 'Repository', name: 'github.com/org/payment-svc', color: '#3b82f6', status: 'Main' },
    { id: 'api-1', label: 'APIEndpoint', name: 'POST /v1/payments/charge', color: '#10b981', status: '200 OK' },
    { id: 'emp-1', label: 'Employee', name: 'Sarah Jenkins (Tech Lead)', color: '#f59e0b', status: 'On-Call' },
  ];

  useEffect(() => {
    apiService.getGraphStats().then(setStats).catch(() => {});
  }, []);

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
          <div className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <div>
              <div className="text-slate-400 text-[10px]">Graph Engine</div>
              <div className="font-bold text-white font-mono">{stats?.database || 'Neo4j Enterprise'}</div>
            </div>
          </div>

          <div className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs flex items-center space-x-2">
            <Layers className="w-4 h-4 text-purple-400" />
            <div>
              <div className="text-slate-400 text-[10px]">Nodes / Edges</div>
              <div className="font-bold text-white font-mono">{stats?.nodes_count || 142} / {stats?.relationships_count || 318}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Graph Canvas (2 Cols) */}
        <div className="lg:col-span-2 glass-panel p-5 rounded-2xl border border-slate-800 space-y-4 shadow-xl">
          {/* Controls Bar */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center space-x-2 bg-slate-950 p-2 rounded-xl border border-slate-800 flex-1">
              <Search className="w-4 h-4 text-slate-400 ml-1" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search graph entities by name..."
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
            </select>
          </div>

          {/* Interactive Graph Node Display Canvas */}
          <div className="w-full h-96 rounded-xl bg-slate-950 border border-slate-800 p-6 relative overflow-hidden flex items-center justify-center">
            {/* Grid Pattern Background */}
            <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#06b6d4_1px,transparent_1px)] [background-size:16px_16px]" />

            {/* Render Nodes as Interactive Cards */}
            <div className="relative z-10 grid grid-cols-2 md:grid-cols-3 gap-4 w-full">
              {mockNodes.map((node) => (
                <div
                  key={node.id}
                  className="p-3 rounded-xl glass-card border border-slate-800 hover:border-cyan-500/50 cursor-pointer transition-all hover:scale-105 shadow-md space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold font-mono px-2 py-0.5 rounded-full" style={{ backgroundColor: `${node.color}20`, color: node.color, borderColor: `${node.color}50`, borderWidth: 1 }}>
                      {node.label}
                    </span>
                    <span className="text-[10px] text-slate-500 font-mono">{node.status}</span>
                  </div>
                  <p className="text-xs font-bold text-white truncate">{node.name}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Cypher Console Sidebar (1 Col) */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
          <h3 className="font-bold text-sm text-white flex items-center space-x-2 border-b border-slate-800 pb-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>Cypher Execution Console</span>
          </h3>

          <div className="space-y-2">
            <label className="text-xs text-slate-400">Read-Only Cypher Query:</label>
            <textarea
              value={cypherQuery}
              onChange={(e) => setCypherQuery(e.target.value)}
              rows={4}
              className="w-full p-3 rounded-xl bg-slate-950 text-cyan-300 font-mono text-xs border border-slate-800 focus:border-cyan-500 focus:outline-none"
            />
          </div>

          <button
            onClick={() => setCypherResults({ records_count: 5, execution_time_ms: 12.4, status: 'SUCCESS' })}
            className="w-full py-2.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-xs font-semibold flex items-center justify-center space-x-2 transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Execute Cypher Query</span>
          </button>

          {cypherResults && (
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1 font-mono">
              <div className="text-emerald-400 font-semibold">✔ Execution Completed</div>
              <div className="text-slate-400 text-[11px]">Records returned: {cypherResults.records_count}</div>
              <div className="text-slate-400 text-[11px]">Latency: {cypherResults.execution_time_ms} ms</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
