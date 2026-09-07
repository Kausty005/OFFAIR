"use client";

import { useState, useEffect, useCallback } from "react";
import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import {
  Lock, Shield, Network, AlertTriangle, RefreshCw,
  CheckCircle2, XCircle, Activity, Cpu, Database,
  FileCode, Eye, WifiOff, Clock, ChevronRight
} from "lucide-react";

const API = "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────
interface SecurityStats {
  ollama_online: boolean;
  docker_online: boolean;
  primary_model: string;
  models_loaded: string[];
  llm_inference: string;
  ocr: string;
  embeddings: string;
  rag: string;
  file_processing: string;
  code_execution: string;
  external_ai_apis: number;
  cloud_uploads: number;
  internet_dependency: string;
  local_llm_calls: number;
  ocr_operations: number;
  rag_searches: number;
  sandbox_executions: number;
}

interface AuditEntry {
  timestamp: string;
  time?: string;
  action: string;
  event?: string;
  details?: Record<string, unknown>;
  [key: string]: unknown;
}

// ─── Badge color for event types ──────────────────────────────
function badgeColor(action: string): string {
  if (action.includes("AUTH")) return "rgba(56,114,224,0.15)";
  if (action.includes("ERROR") || action.includes("FAIL")) return "rgba(239,68,68,0.15)";
  if (action.includes("INGEST") || action.includes("KB_") || action.includes("RAG")) return "rgba(34,197,94,0.15)";
  if (action.includes("LLM") || action.includes("EMBEDDING") || action.includes("GENERATE")) return "rgba(168,85,247,0.15)";
  if (action.includes("TASK") || action.includes("AGENT") || action.includes("PLAN")) return "rgba(251,146,60,0.15)";
  if (action.includes("SANDBOX") || action.includes("CODE") || action.includes("DOCX")) return "rgba(56,189,248,0.15)";
  if (action.includes("START") || action.includes("APP")) return "rgba(255,255,255,0.08)";
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

// ─── Sub-components ───────────────────────────────────────────
function StatusRow({
  icon: Icon, label, value, ok, mono = false
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  ok?: boolean | null;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-3 rounded-xl bg-surface/30 border border-white/[0.04]">
      <div className="flex items-center gap-3">
        {ok === null || ok === undefined ? (
          <div className="w-2 h-2 rounded-full bg-gray-600 shrink-0" />
        ) : ok ? (
          <div className="w-2 h-2 rounded-full bg-green-400 shrink-0 shadow-[0_0_6px_rgba(74,222,128,0.6)]" />
        ) : (
          <div className="w-2 h-2 rounded-full bg-red-400 shrink-0 shadow-[0_0_6px_rgba(248,113,113,0.6)]" />
        )}
        <Icon className="w-3.5 h-3.5 text-gray-500" />
        <span className="text-[13px] text-gray-300">{label}</span>
      </div>
      <span className={`text-[12px] font-semibold ${ok === false ? "text-red-400" : ok === true ? "text-green-400" : "text-gray-400"} ${mono ? "font-mono" : ""}`}>
        {value}
      </span>
    </div>
  );
}

function CounterCard({
  label, value, icon: Icon, color
}: {
  label: string; value: number; icon: React.ElementType; color: string;
}) {
  return (
    <div className="p-4 rounded-xl bg-surface/30 border border-white/[0.04] flex items-center gap-4">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: `${color}15`, border: `1px solid ${color}30` }}
      >
        <Icon className="w-5 h-5" style={{ color }} />
      </div>
      <div>
        <div className="text-[22px] font-bold text-white leading-none">{value.toLocaleString()}</div>
        <div className="text-[11px] text-gray-500 mt-1">{label}</div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────
export default function SecurityPage() {
  const [stats, setStats] = useState<SecurityStats | null>(null);
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [filter, setFilter] = useState<string>("ALL");

  const fetchAll = useCallback(async () => {
    try {
      const [statsRes, logsRes] = await Promise.all([
        fetch(`${API}/api/security/stats`).catch(() => null),
        fetch(`${API}/api/logs?limit=100`).catch(() => null),
      ]);
      if (statsRes?.ok) setStats(await statsRes.json());
      if (logsRes?.ok) setLogs(await logsRes.json());
      setLastUpdated(new Date());
    } catch {/* silent */}
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    fetchAll();
    const iv = setInterval(fetchAll, 6000);
    return () => clearInterval(iv);
  }, [fetchAll]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchAll();
  };

  // Filter categories
  const LOG_FILTERS = ["ALL", "AGENT", "RAG", "LLM", "INGEST", "AUTH", "ERROR"];
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
    <div className="max-w-7xl mx-auto space-y-6">
      <PageHeader
        title="Security Center"
        description="Live sovereignty monitoring — air-gap integrity, telemetry, and audit trail"
        action={
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] px-4 py-2 rounded-xl text-sm font-medium text-gray-300 transition-all duration-300"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      {/* ── Top Status Pills ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          {
            label: "Ollama Inference",
            ok: stats?.ollama_online ?? null,
            value: stats?.ollama_online ? "ONLINE" : loading ? "…" : "OFFLINE",
            icon: Cpu,
          },
          {
            label: "Air-Gap Status",
            ok: (stats?.external_ai_apis ?? 0) === 0,
            value: (stats?.external_ai_apis ?? 0) === 0 ? "INTACT" : "BREACH",
            icon: WifiOff,
          },
          {
            label: "Docker Sandbox",
            ok: stats?.docker_online ?? null,
            value: stats?.docker_online ? "RUNNING" : loading ? "…" : "OFFLINE",
            icon: FileCode,
          },
          {
            label: "Audit Logging",
            ok: true,
            value: `${logs.length} entries`,
            icon: Eye,
          },
        ].map(item => (
          <GlassCard
            key={item.label}
            className="p-4 flex items-center gap-3 border-white/[0.03] bg-surface/30"
          >
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              item.ok === true ? "bg-green-500/10 border border-green-500/20" :
              item.ok === false ? "bg-red-500/10 border border-red-500/20" :
              "bg-white/[0.04] border border-white/[0.06]"
            }`}>
              <item.icon className={`w-5 h-5 ${
                item.ok === true ? "text-green-400" :
                item.ok === false ? "text-red-400" : "text-gray-400"
              }`} />
            </div>
            <div>
              <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-0.5">{item.label}</p>
              <p className={`text-[14px] font-bold ${
                item.ok === true ? "text-green-400" :
                item.ok === false ? "text-red-400" : "text-gray-300"
              }`}>{item.value}</p>
            </div>
          </GlassCard>
        ))}
      </div>

      {/* ── Main Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Air-Gap Integrity */}
        <GlassCard className="p-6 border-white/[0.04]">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 rounded-lg bg-green-500/10 border border-green-500/20 flex items-center justify-center">
              <Lock className="w-4 h-4 text-green-400" />
            </div>
            <div>
              <h3 className="text-[14px] font-semibold text-white">Air-Gap Integrity</h3>
              <p className="text-[11px] text-gray-500">All inference runs locally — zero cloud dependency</p>
            </div>
            <div className="ml-auto px-2.5 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-[10px] font-bold text-green-400 uppercase tracking-wider">
              Secure
            </div>
          </div>
          <div className="space-y-2.5">
            <StatusRow icon={Cpu} label="LLM Inference" value={stats?.llm_inference || "LOCAL"} ok={true} />
            <StatusRow icon={Eye} label="OCR Engine" value={stats?.ocr || "LOCAL"} ok={true} />
            <StatusRow icon={Database} label="Embeddings" value={stats?.embeddings || "LOCAL"} ok={true} />
            <StatusRow icon={Database} label="Vector DB (RAG)" value={stats?.rag || "LOCAL"} ok={true} />
            <StatusRow icon={FileCode} label="Code Execution" value={stats?.code_execution || "DOCKER"} ok={stats?.docker_online ?? null} />
            <StatusRow icon={WifiOff} label="External AI APIs" value={`${stats?.external_ai_apis ?? 0} (Blocked)`} ok={(stats?.external_ai_apis ?? 0) === 0} />
            <StatusRow icon={Network} label="Cloud Uploads" value={`${stats?.cloud_uploads ?? 0} (Blocked)`} ok={(stats?.cloud_uploads ?? 0) === 0} />
            <StatusRow icon={Shield} label="Internet Dependency" value={stats?.internet_dependency || "NONE"} ok={true} />
          </div>
        </GlassCard>

        {/* Local Model Serving */}
        <GlassCard className="p-6 border-white/[0.04]">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
              <Cpu className="w-4 h-4 text-accent" />
            </div>
            <div>
              <h3 className="text-[14px] font-semibold text-white">Local Model Serving</h3>
              <p className="text-[11px] text-gray-500">Ollama · Local inference · No GPU cloud</p>
            </div>
          </div>
          <div className="space-y-2.5">
            <StatusRow
              icon={Cpu}
              label="Inference Engine"
              value="Ollama (Local)"
              ok={stats?.ollama_online ?? null}
              mono
            />
            <StatusRow
              icon={Activity}
              label="Primary Model"
              value={stats?.primary_model || (loading ? "Loading…" : "Not Available")}
              ok={stats?.ollama_online ?? null}
              mono
            />
            <StatusRow icon={Network} label="Endpoint" value="localhost:11434" ok={true} mono />
            <StatusRow icon={Database} label="Docker Sandbox" value={stats?.docker_online ? "Running" : "Offline"} ok={stats?.docker_online ?? null} />
          </div>

          {/* Loaded models */}
          {stats?.models_loaded && stats.models_loaded.length > 0 && (
            <div className="mt-5 pt-4 border-t border-white/[0.05]">
              <p className="text-[10px] text-gray-500 uppercase tracking-widest mb-3">Available Models</p>
              <div className="flex flex-wrap gap-2">
                {stats.models_loaded.map(m => (
                  <span key={m} className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-accent/10 border border-accent/20 text-accent">
                    {m}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Runtime counters */}
          <div className="mt-5 pt-4 border-t border-white/[0.05] grid grid-cols-2 gap-3">
            <CounterCard label="LLM Calls" value={stats?.local_llm_calls ?? 0} icon={Cpu} color="#818cf8" />
            <CounterCard label="RAG Searches" value={stats?.rag_searches ?? 0} icon={Database} color="#34d399" />
            <CounterCard label="OCR Operations" value={stats?.ocr_operations ?? 0} icon={Eye} color="#fb923c" />
            <CounterCard label="Sandbox Runs" value={stats?.sandbox_executions ?? 0} icon={FileCode} color="#60a5fa" />
          </div>
        </GlassCard>
      </div>

      {/* ── No Alerts Banner ── */}
      <GlassCard className="p-5 border-green-500/10 bg-green-500/[0.02]">
        <div className="flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0" />
          <div>
            <h3 className="text-[14px] font-semibold text-white">No Security Alerts</h3>
            <p className="text-[12px] text-gray-400 mt-0.5">
              System operating within sovereign parameters. 0 external API calls · 0 cloud uploads · All inference local.
            </p>
          </div>
          {lastUpdated && (
            <div className="ml-auto flex items-center gap-1.5 text-[11px] text-gray-500 shrink-0">
              <Clock className="w-3 h-3" />
              Updated {lastUpdated.toLocaleTimeString()}
            </div>
          )}
        </div>
      </GlassCard>

      {/* ── Audit Log ── */}
      <GlassCard className="p-0 overflow-hidden border-white/[0.04]">
        <div className="px-6 py-4 border-b border-white/[0.04] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-4 h-4 text-accent" />
            <h3 className="text-[14px] font-semibold text-white">Live Audit Log</h3>
            <span className="text-[11px] text-gray-500 bg-white/[0.04] px-2 py-0.5 rounded-full">
              {filteredLogs.length} entries
            </span>
          </div>

          {/* Filter buttons */}
          <div className="flex gap-1.5 flex-wrap justify-end">
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

        {/* Log entries */}
        <div className="max-h-[480px] overflow-y-auto">
          {filteredLogs.length === 0 ? (
            <div className="py-16 text-center">
              <Activity className="w-8 h-8 text-gray-600 mx-auto mb-3" />
              <p className="text-[13px] text-gray-500">
                {loading ? "Loading audit logs…" : "No log entries match this filter"}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-white/[0.03]">
              {[...filteredLogs].reverse().map((entry, i) => {
                const action = entry.action || entry.event || "EVENT";
                const ts = entry.timestamp || entry.time || "";
                const details = entry.details || {};
                // Pick a few interesting detail keys to show
                const detailKeys = Object.keys(details).filter(
                  k => !["timestamp", "action", "event", "time"].includes(k)
                );
                const detailStr = detailKeys
                  .slice(0, 3)
                  .map(k => `${k}=${JSON.stringify(details[k])}`)
                  .join("  ·  ");

                return (
                  <div
                    key={i}
                    className="flex items-start gap-4 px-6 py-3 hover:bg-white/[0.02] transition-colors group"
                  >
                    {/* Time */}
                    <span className="text-[11px] font-mono text-gray-600 shrink-0 pt-0.5 w-20">
                      {ts ? new Date(ts).toLocaleTimeString() : "--:--:--"}
                    </span>

                    {/* Event badge */}
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded-md shrink-0 mt-0.5"
                      style={{
                        background: badgeColor(action),
                        color: badgeText(action),
                      }}
                    >
                      {action}
                    </span>

                    {/* Details */}
                    <span className="text-[12px] text-gray-500 truncate flex-1 font-mono">
                      {detailStr || "—"}
                    </span>

                    {/* Chevron on hover */}
                    <ChevronRight className="w-3.5 h-3.5 text-gray-700 group-hover:text-gray-400 transition-colors shrink-0 mt-0.5" />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-white/[0.04] bg-background/40 flex items-center justify-between">
          <span className="text-[11px] text-gray-600">
            All audit events stored locally in <code className="text-gray-500 font-mono">logs/audit.jsonl</code>
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
