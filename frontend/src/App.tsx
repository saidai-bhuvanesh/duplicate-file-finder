import { useState } from 'react';
import { Navbar } from './components/Navbar';
import { SearchWorkspace } from './components/SearchWorkspace';
import { KnowledgeGraphView } from './components/KnowledgeGraphView';
import { IngestionDashboard } from './components/IngestionDashboard';
import { EvaluationDashboard } from './components/EvaluationDashboard';

export function App() {
  const [activeTab, setActiveTab] = useState<string>('search');

  return (
    <div className="min-h-screen bg-[#0b0f17] text-slate-100 selection:bg-cyan-500 selection:text-black">
      {/* Top Sticky Navigation */}
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main View Container */}
      <main className="px-6 py-6 max-w-7xl mx-auto">
        {activeTab === 'search' && <SearchWorkspace />}
        {activeTab === 'graph' && <KnowledgeGraphView />}
        {activeTab === 'ingestion' && <IngestionDashboard />}
        {activeTab === 'evaluation' && <EvaluationDashboard />}
      </main>
    </div>
  );
}

export default App;
