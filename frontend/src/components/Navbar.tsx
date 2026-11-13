import React, { useEffect, useState } from 'react';
import { Sparkles, FileText, BarChart3, Network, ShieldCheck } from 'lucide-react';
import { apiService } from '../services/api';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, setActiveTab }) => {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'ready' | 'degraded' | 'offline'>('checking');

  useEffect(() => {
    let active = true;
    let checking = false;

    const checkBackend = async () => {
      if (checking) return;
      checking = true;
      try {
        const status = await apiService.getBackendStatus();
        if (active) setBackendStatus(status);
      } catch {
        if (active) setBackendStatus('offline');
      } finally {
        checking = false;
      }
    };

    void checkBackend();
    const intervalId = window.setInterval(checkBackend, 10000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

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
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center shadow-glow-cyan shrink-0">
            <Sparkles className="w-5 h-5 text-white animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight text-white">
                EnterpriseIT <span className="text-cyan-400 font-extrabold">RAG</span>
              </span>
              <span className="px-2 py-0.5 text-[10px] font-bold bg-cyan-950/90 text-cyan-400 border border-cyan-800/80 rounded-full font-mono">
                v1.0 ARIE
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Adaptive Multi-Agent Knowledge Platform</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center space-x-1 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800 shadow-inner">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* System Status Indicators */}
        <div className="flex items-center space-x-2.5">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs shadow-sm">
            <span className={`w-2 h-2 rounded-full ${
              backendStatus === 'ready' || backendStatus === 'degraded'
                ? 'bg-emerald-400 animate-pulse'
                : backendStatus === 'offline'
                  ? 'bg-red-400'
                  : 'bg-amber-400 animate-pulse'
            }`} />
            <span className="text-slate-200 font-mono text-[11px]">
              {backendStatus === 'ready' || backendStatus === 'degraded'
                ? 'API: Operational'
                : backendStatus === 'offline'
                  ? 'API: Offline'
                  : 'API: Connecting...'}
            </span>
          </div>

          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-xs text-emerald-300 shadow-sm">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-semibold text-[11px]">NLI Guard Active</span>
          </div>
        </div>
      </div>
    </header>
  );
};
