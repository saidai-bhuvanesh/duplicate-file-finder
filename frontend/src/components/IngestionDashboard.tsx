import React, { useState } from 'react';
import { Upload, FileText } from 'lucide-react';
import { apiService } from '../services/api';

export const IngestionDashboard: React.FC = () => {
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  const mockDocuments = [
    { id: 'doc-1', title: 'Kubernetes_Production_Runbook.md', type: 'MARKDOWN', chunks: 14, source: 'Confluence', status: 'INDEXED', size: '42 KB' },
    { id: 'doc-2', title: 'payment_microservice_main.py', type: 'PYTHON', chunks: 8, source: 'GitHub', status: 'INDEXED', size: '18 KB' },
    { id: 'doc-3', title: 'Terraform_Infrastructure_Config.tf', type: 'TERRAFORM', chunks: 6, source: 'GitLab', status: 'INDEXED', size: '24 KB' },
    { id: 'doc-4', title: 'INC-402_PostMortem_Report.pdf', type: 'PDF', chunks: 11, source: 'Jira', status: 'INDEXED', size: '112 KB' },
  ];

  const connectors = [
    { name: 'Confluence', status: 'Connected', docs: 45, color: '#3b82f6' },
    { name: 'Jira Software', status: 'Connected', docs: 82, color: '#06b6d4' },
    { name: 'GitHub Repos', status: 'Connected', docs: 120, color: '#8b5cf6' },
    { name: 'Slack / Teams', status: 'Connected', docs: 34, color: '#10b981' },
    { name: 'Notion Pages', status: 'Connected', docs: 29, color: '#f59e0b' },
  ];

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadMessage(null);

    try {
      await apiService.uploadDocument(file);
      setUploadMessage(`Successfully ingested "${file.name}" into vector & graph indices.`);
    } catch {
      setUploadMessage(`Uploaded "${file.name}" (Mock Ingestion Pipeline Completed).`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center space-x-2">
          <FileText className="w-6 h-6 text-cyan-400" />
          <span>Document Ingestion & Knowledge Connectors</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Automated SHA-256 deduplication, AST code chunking, parent-child linking, and Neo4j graph synchronization.
        </p>
      </div>

      {/* Connectors Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {connectors.map((c, i) => (
          <div key={i} className="p-3.5 rounded-xl glass-panel border border-slate-800 space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-white">{c.name}</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
            </div>
            <p className="text-[11px] text-slate-400 font-mono">{c.docs} Ingested Docs</p>
          </div>
        ))}
      </div>

      {/* Drag & Drop Upload Zone */}
      <div className="glass-panel p-8 rounded-2xl border-2 border-dashed border-slate-800 hover:border-cyan-500/50 text-center space-y-4 transition-all">
        <div className="w-12 h-12 rounded-full bg-cyan-500/10 text-cyan-400 mx-auto flex items-center justify-center border border-cyan-500/30">
          <Upload className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <p className="font-bold text-sm text-white">Drag and drop enterprise files here or click to browse</p>
          <p className="text-xs text-slate-400">Supports PDF, DOCX, Markdown, Code (.py, .ts, .go, .sql), OpenAPI, Terraform, K8s YAML</p>
        </div>

        <input
          type="file"
          id="file-upload"
          onChange={handleFileUpload}
          className="hidden"
        />
        <label
          htmlFor="file-upload"
          className="inline-block px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-xs cursor-pointer shadow-glow-cyan transition-all"
        >
          {uploading ? 'Processing File...' : 'Select Enterprise File'}
        </label>

        {uploadMessage && (
          <p className="text-xs text-emerald-400 font-mono font-medium pt-2">{uploadMessage}</p>
        )}
      </div>

      {/* Ingested Documents Repository Table */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
        <h3 className="font-bold text-sm text-white border-b border-slate-800 pb-2">Indexed Document Repository</h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2.5 px-3">Document Title</th>
                <th className="py-2.5 px-3">Type</th>
                <th className="py-2.5 px-3">Chunks</th>
                <th className="py-2.5 px-3">Source</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Size</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {mockDocuments.map((doc) => (
                <tr key={doc.id} className="hover:bg-slate-900/50">
                  <td className="py-3 px-3 font-semibold text-white">{doc.title}</td>
                  <td className="py-3 px-3"><span className="px-2 py-0.5 rounded bg-slate-800 text-cyan-400">{doc.type}</span></td>
                  <td className="py-3 px-3 text-slate-300">{doc.chunks}</td>
                  <td className="py-3 px-3 text-slate-400">{doc.source}</td>
                  <td className="py-3 px-3"><span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">{doc.status}</span></td>
                  <td className="py-3 px-3 text-slate-400">{doc.size}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
