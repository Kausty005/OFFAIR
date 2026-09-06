import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import { Lock, Network, AlertTriangle } from "lucide-react";

export default function SecurityPage() {
  return (
    <div className="max-w-6xl mx-auto">
      <PageHeader 
        title="Security Center" 
        description="Monitor system sovereignty and air-gap integrity"
      />
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <GlassCard className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <Lock className="w-5 h-5 text-green-400" />
            <h3 className="text-lg font-semibold text-white">Air Gap Status</h3>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface/30 border border-white/5">
              <span className="text-sm text-gray-300">External Network Requests</span>
              <span className="text-sm font-bold text-green-400">0 (Blocked)</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface/30 border border-white/5">
              <span className="text-sm text-gray-300">Local Telemetry</span>
              <span className="text-sm font-bold text-green-400">Active</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface/30 border border-white/5">
              <span className="text-sm text-gray-300">Encryption at Rest</span>
              <span className="text-sm font-bold text-green-400">AES-256</span>
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <Network className="w-5 h-5 text-accent" />
            <h3 className="text-lg font-semibold text-white">Local Model Serving</h3>
          </div>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface/30 border border-white/5">
              <span className="text-sm text-gray-300">Active Model</span>
              <span className="text-sm font-bold text-white">Llama-3-70B-Instruct</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface/30 border border-white/5">
              <span className="text-sm text-gray-300">VRAM Usage</span>
              <span className="text-sm font-bold text-orange-400">42GB / 48GB</span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface/30 border border-white/5">
              <span className="text-sm text-gray-300">Inference Engine</span>
              <span className="text-sm font-bold text-white">vLLM (Local)</span>
            </div>
          </div>
        </GlassCard>
      </div>
      
      <GlassCard className="p-6 border-orange-500/20 bg-orange-500/[0.02]">
        <div className="flex items-center gap-3 mb-4">
          <AlertTriangle className="w-5 h-5 text-orange-400" />
          <h3 className="text-lg font-semibold text-white">Security Alerts</h3>
        </div>
        <p className="text-sm text-gray-400">No active security alerts or breaches detected. The system is operating within defined sovereign parameters.</p>
      </GlassCard>
    </div>
  );
}
