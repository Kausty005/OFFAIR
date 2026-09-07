"use client";

import { useState, useEffect, useCallback } from "react";
import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import { Activity, RefreshCw, ChevronRight } from "lucide-react";

const API = "http://localhost:8000";

const LOG_FILTERS = ["ALL", "AGENT", "RAG", "LLM", "INGEST", "AUTH", "ERROR"];

function badgeColor(action: string): string {
  if (action.includes("AUTH")) return "rgba(56,114,224,0.15)";
  if (action.includes("ERROR") || action.includes("FAIL")) return "rgba(239,68,68,0.15)";
  if (action.includes("INGEST") || action.includes("KB_") || action.includes("RAG")) return "rgba(34,197,94,0.15)";
  if (action.includes("LLM") || action.includes("EMBEDDING") || action.includes("GENERATE")) return "rgba(168,85,247,0.15)";
  if (action.includes("TASK") || action.includes("AGENT") || action.includes("PLAN")) return "rgba(251,146,60,0.15)";
  if (action.includes("SANDBOX") || action.includes("CODE") || action.includes("DOCX")) return "rgba(56,189,248,0.15)";
  return "rgba(255,255,255,0.06)";
}
function badgeText(action: string): string {
  if (action.includes("AUTH")) return "#60a5fa";
  if (action.includes("ERROR") || action.includes("FAIL")) return "#f87171";
  if (action.includes("INGEST") || action.includes("KB_") || action.includes("RAG")) return "#4ade80";
  if (action.includes("LLM") || action.includes("EMBEDDING") || action.includes("GENERATE")) return "#c084fc";
  if (action.includes("TASK") || action.includes("AGENT") || action.includes("PLAN")) return "#fb923c";
  if (action.includes("SANDBOX") || action.includes("CODE") || action.includes("DOCX")) return "#38bdf8";
  return "#9ca3af";
}

interface AuditEntry {
  timestamp?: string;
  time?: string;
  action?: string;
  event?: string;
  details?: Record<string, unknown>;
  [key: string]: unknown;
}

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState("ALL");

  const fetchLogs = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/logs?limit=200`);
      if (r.ok) setLogs(await r.json());
    } catch { /* silent */ }
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    fetchLogs();
    const iv = setInterval(fetchLogs, 5000);
    return () => clearInterval(iv);
  }, [fetchLogs]);

  const filteredLogs = logs.filter(entry => {
    const action = entry.action || entry.event || "";
    if (filter === "ALL") return true;
    if (filter === "AGENT") return action.includes("AGENT") || action.includes("TASK") || action.includes("PLAN");
    if (filter === "RAG") return action.includes("RAG") || action.includes("KB_") || action.includes("VECTOR");
    if (filter === "LLM") return action.includes("LLM") || action.includes("EMBEDDING") || action.includes("GENERATE");
    if (filter === "INGEST") return action.includes("INGEST") || action.includes("DOCX") || action.includes("CODE");
    if (filter === "AUTH") return action.includes("AUTH") || action.includes("LOGIN");
    if (filter === "ERROR") return action.includes("ERROR") || action.includes("FAIL");
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto">
      <PageHeader
        title="Audit Logs"
        description="Complete chronological record of all agent activity — stored locally"
        action={
          <button
            onClick={() => { setRefreshing(true); fetchLogs(); }}
            disabled={refreshing}
            className="flex items-center gap-2 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] px-4 py-2 rounded-xl text-sm font-medium text-gray-300 transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      <GlassCard className="p-0 overflow-hidden border-white/[0.04]">
        <div className="px-6 py-4 border-b border-white/[0.04] flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <Activity className="w-4 h-4 text-accent" />
            <h3 className="text-[14px] font-semibold text-white">All Events</h3>
            <span className="text-[11px] text-gray-500 bg-white/[0.04] px-2 py-0.5 rounded-full">
              {filteredLogs.length} entries
            </span>
          </div>
          <div className="flex gap-1.5 flex-wrap">
            {LOG_FILTERS.map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-lg transition-all ${
                  filter === f
                    ? "bg-accent/20 border border-accent/40 text-accent"
                    : "bg-white/[0.02] border border-white/[0.05] text-gray-500 hover:text-gray-300 hover:bg-white/[0.05]"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="max-h-[600px] overflow-y-auto">
          {loading ? (
            <div className="py-20 text-center text-gray-500">
              <RefreshCw className="w-6 h-6 mx-auto mb-3 animate-spin opacity-50" />
              Loading audit logs…
            </div>
          ) : filteredLogs.length === 0 ? (
            <div className="py-20 text-center">
              <Activity className="w-8 h-8 text-gray-700 mx-auto mb-3" />
              <p className="text-[13px] text-gray-500">No log entries match this filter</p>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.03]">
              {[...filteredLogs].reverse().map((entry, i) => {
                const action = entry.action || entry.event || "EVENT";
                const ts = entry.timestamp || entry.time || "";
                const details = entry.details || {};
                const detailStr = Object.keys(details)
                  .filter(k => !["timestamp","action","event","time"].includes(k))
                  .slice(0, 3)
                  .map(k => `${k}=${JSON.stringify(details[k])}`)
                  .join("  ·  ");
                return (
                  <div key={i} className="flex items-start gap-4 px-6 py-3 hover:bg-white/[0.02] transition-colors group">
                    <span className="text-[11px] font-mono text-gray-600 shrink-0 pt-0.5 w-20">
                      {ts ? new Date(ts).toLocaleTimeString() : "--:--:--"}
                    </span>
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded-md shrink-0 mt-0.5"
                      style={{ background: badgeColor(action), color: badgeText(action) }}
                    >
                      {action}
                    </span>
                    <span className="text-[12px] text-gray-500 truncate flex-1 font-mono">{detailStr || "—"}</span>
                    <ChevronRight className="w-3.5 h-3.5 text-gray-700 group-hover:text-gray-400 shrink-0 mt-0.5" />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="px-6 py-3 border-t border-white/[0.04] bg-background/40 flex items-center justify-between">
          <span className="text-[11px] text-gray-600">
            Stored in <code className="font-mono text-gray-500">logs/audit.jsonl</code> — auto-refreshes every 5s
          </span>
          <div className="flex items-center gap-1.5 text-[11px] text-green-400">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Live
          </div>
        </div>
      </GlassCard>
    </div>
  );
}
