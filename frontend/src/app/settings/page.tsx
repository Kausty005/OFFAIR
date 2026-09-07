import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import { Settings, Lock, Shield, Server, Database } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="max-w-4xl mx-auto">
      <PageHeader
        title="Settings"
        description="OFFAIR AI workbench configuration"
      />

      <div className="space-y-6">
        {[
          {
            icon: Server,
            title: "Backend Server",
            items: [
              { label: "API Endpoint", value: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000" },
              { label: "LLM Endpoint", value: "Internal (Ollama)" },
              { label: "CORS Policy", value: "Private LAN Access" },
            ],
          },
          {
            icon: Database,
            title: "Knowledge Base",
            items: [
              { label: "Vector Store", value: "Pure-Python Local (JSON)" },
              { label: "Embedding Model", value: "nomic-embed-text (local)" },
              { label: "Chunk Size", value: "512 tokens / 50 overlap" },
            ],
          },
          {
            icon: Shield,
            title: "Security Policy",
            items: [
              { label: "External API Calls", value: "0 (Blocked by network_guard.py)" },
              { label: "Cloud Uploads", value: "0 (Disabled)" },
              { label: "Internet Dependency", value: "NONE after setup" },
            ],
          },
          {
            icon: Lock,
            title: "Workspace",
            items: [
              { label: "Upload Directory", value: "workspace/uploads/" },
              { label: "Output Directory", value: "workspace/outputs/" },
              { label: "Audit Log", value: "logs/audit.jsonl" },
            ],
          },
        ].map(section => (
          <GlassCard key={section.title} className="p-6 border-white/[0.04]">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
                <section.icon className="w-4 h-4 text-accent" />
              </div>
              <h3 className="text-[14px] font-semibold text-white">{section.title}</h3>
            </div>
            <div className="space-y-3">
              {section.items.map(item => (
                <div key={item.label} className="flex items-center justify-between py-2.5 px-4 rounded-xl bg-surface/30 border border-white/[0.04]">
                  <span className="text-[13px] text-gray-400">{item.label}</span>
                  <span className="text-[12px] font-mono text-gray-300">{item.value}</span>
                </div>
              ))}
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  );
}
