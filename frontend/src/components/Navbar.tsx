import React from 'react';
import { Sparkles, FileText, BarChart3, Network, ShieldCheck } from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const navItems = [
    { id: 'search', label: 'Multi-Agent Search', icon: Sparkles },
    { id: 'graph', label: 'Knowledge Graph', icon: Network },
    { id: 'ingestion', label: 'Ingestion Pipeline', icon: FileText },
    { id: 'evaluation', label: 'RAG Benchmarks', icon: BarChart3 },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/80 px-6 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('search')}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-glow-cyan">
            <Sparkles className="w-6 h-6 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight text-white font-mono">EnterpriseIT<span className="text-cyan-400">-RAG</span></span>
              <span className="px-2 py-0.5 text-[10px] font-semibold bg-cyan-950/80 text-cyan-400 border border-cyan-800/50 rounded-full">v1.0 IEEE</span>
            </div>
            <p className="text-[11px] text-slate-400">Adaptive Multi-Agent Knowledge Platform</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* System Status Indicators */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span className="text-slate-300 font-mono">Backend: Online</span>
          </div>
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-xs text-emerald-400">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span className="font-semibold">NLI Guarded</span>
          </div>
        </div>
      </div>
    </header>
  );
};
