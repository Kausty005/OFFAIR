import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import { BookOpen, Upload, Database, FileText } from "lucide-react";

export default function KnowledgePage() {
  return (
    <div className="max-w-6xl mx-auto">
      <PageHeader 
        title="Knowledge Base" 
        description="Manage secure documents for local vector search"
        action={
          <button className="flex items-center gap-2 bg-accent hover:bg-accent/90 px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors">
            <Upload className="w-4 h-4" />
            Upload Document
          </button>
        }
      />
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <GlassCard className="p-5 flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0">
            <Database className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-white">Total Documents</h3>
            <p className="text-2xl font-bold text-white mt-1">1,248</p>
          </div>
        </GlassCard>
        
        <GlassCard className="p-5 flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-white">Indexed Chunks</h3>
            <p className="text-2xl font-bold text-white mt-1">45.2k</p>
          </div>
        </GlassCard>
      </div>

      <GlassCard className="p-0 overflow-hidden">
        <div className="p-4 border-b border-white/5 flex items-center justify-between">
          <h3 className="text-sm font-medium text-white">Recent Documents</h3>
          <input 
            type="text" 
            placeholder="Search documents..." 
            className="bg-surface/50 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-accent/50 w-64"
          />
        </div>
        <div className="divide-y divide-white/5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="p-4 flex items-center justify-between hover:bg-white/[0.02] transition-colors cursor-pointer">
              <div className="flex items-center gap-3">
                <BookOpen className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-white">Engineering_Specs_v{i}.pdf</p>
                  <p className="text-xs text-gray-500">Uploaded 2 hours ago • 2.4 MB</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-xs font-medium text-green-400 bg-green-400/10 px-2 py-1 rounded-md">Indexed</span>
              </div>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
