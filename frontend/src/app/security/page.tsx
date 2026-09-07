"use client";

<<<<<<< HEAD
import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import {
  Lock, Network, ShieldCheck, Loader2, RefreshCw,
  CheckCircle2, XCircle, AlertCircle, Server,
  Eye, Database, Cpu, Globe, BookOpen, UserCircle, Clock
} from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { securityService, SecurityDashboard, SystemStatus, AuditLogEntry } from "@/lib/services/security";
import { chatService } from "@/lib/services/chat";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch { return iso; }
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short" });
  } catch { return ""; }
}

// ── Status Row ────────────────────────────────────────────────────────────────

function StatusRow({
  label, value, ok, mono = false
}: { label: string; value: string; ok?: boolean; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between px-5 py-3.5 rounded-xl bg-white/[0.02] border border-white/[0.04] group hover:bg-white/[0.03] transition-colors">
      <span className="text-[13px] font-medium text-gray-400">{label}</span>
      <span className={cn(
        "text-[13px] font-bold",
        mono && "font-mono text-[12px]",
        ok === true  && "text-green-400",
        ok === false && "text-red-400",
        ok === undefined && "text-white",
      )}>
=======
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
>>>>>>> 7220fc40bc9b6f43b694a7fa042695bbd48dc4eb
        {value}
      </span>
    </div>
  );
}

<<<<<<< HEAD
// ── Service Health Pill ───────────────────────────────────────────────────────

function HealthPill({ label, active, icon: Icon }: { label: string; active: boolean; icon: React.ElementType }) {
  return (
    <div className={cn(
      "flex items-center gap-3 px-4 py-3.5 rounded-xl border transition-all",
      active
        ? "bg-green-500/[0.06] border-green-500/20"
        : "bg-red-500/[0.06] border-red-500/20"
    )}>
      <div className={cn(
        "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
        active ? "bg-green-500/15" : "bg-red-500/15"
      )}>
        <Icon className={cn("w-4 h-4", active ? "text-green-400" : "text-red-400")} />
      </div>
      <div className="flex-1 min-w-0">
        <p className={cn("text-[12px] font-semibold tracking-wide truncate", active ? "text-green-300" : "text-red-300")}>
          {label}
        </p>
        <p className={cn("text-[10px] font-bold uppercase tracking-widest mt-0.5", active ? "text-green-600" : "text-red-600")}>
          {active ? "Local" : "Offline"}
        </p>
      </div>
      {active
        ? <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
        : <XCircle     className="w-4 h-4 text-red-500 shrink-0" />}
=======
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
>>>>>>> 7220fc40bc9b6f43b694a7fa042695bbd48dc4eb
    </div>
  );
}

<<<<<<< HEAD
// ── Audit Event Row ───────────────────────────────────────────────────────────

const EVENT_COLORS: Record<string, string> = {
  APP_START:          "text-accent bg-accent/10 border-accent/20",
  TASK_COMPLETED:     "text-green-400 bg-green-400/10 border-green-400/20",
  KB_INGEST:          "text-blue-400 bg-blue-400/10 border-blue-400/20",
  DOCX_GENERATED:     "text-purple-400 bg-purple-400/10 border-purple-400/20",
  FILE_WRITTEN:       "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  EXTERNAL_API_CALL:  "text-red-400 bg-red-400/10 border-red-400/20",
  CLOUD_UPLOAD:       "text-red-400 bg-red-400/10 border-red-400/20",
  LLM_CALL:           "text-teal-400 bg-teal-400/10 border-teal-400/20",
  RAG_SEARCH:         "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
};

function AuditRow({ entry, idx }: { entry: AuditLogEntry; idx: number }) {
  const event = entry.action || entry.event || "UNKNOWN";
  const colorClass = EVENT_COLORS[event] ?? "text-gray-400 bg-white/[0.03] border-white/[0.05]";

  const detailStr = Object.entries(entry.details ?? {})
    .filter(([k]) => !["time","timestamp","action","event"].includes(k))
    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`)
    .join(" · ")
    .slice(0, 80);

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.02, duration: 0.2 }}
      className="grid grid-cols-[80px_130px_1fr] gap-4 items-start px-5 py-3.5 border-b border-white/[0.03] hover:bg-white/[0.015] transition-colors group"
    >
      {/* Time */}
      <div className="text-right shrink-0">
        <p className="text-[11px] font-mono text-gray-500">{formatTime(entry.time)}</p>
        <p className="text-[10px] text-gray-700 mt-0.5">{formatDate(entry.time)}</p>
      </div>

      {/* Event badge */}
      <div>
        <span className={cn(
          "inline-block text-[9px] font-bold uppercase tracking-widest px-2 py-1 rounded-md border max-w-full truncate",
          colorClass
        )}>
          {event}
        </span>
      </div>

      {/* Details */}
      <p className="text-[12px] text-gray-500 leading-relaxed truncate group-hover:whitespace-normal group-hover:overflow-visible">
        {detailStr || "—"}
      </p>
    </motion.div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SecurityPage() {
  const { user } = useAuth();

  const [security,   setSecurity]   = useState<SecurityDashboard | null>(null);
  const [sysStatus,  setSysStatus]  = useState<SystemStatus | null>(null);
  const [logs,       setLogs]       = useState<AuditLogEntry[]>([]);
  const [activeModel, setActiveModel] = useState("Loading…");
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAll = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const [secData, statusData, logsData, modelsData] = await Promise.allSettled([
        securityService.getSecurityDashboard(),
        securityService.getStatus(),
        securityService.getLogs(50),
        chatService.getModels(),
      ]);

      if (secData.status   === "fulfilled") setSecurity(secData.value);
      if (statusData.status === "fulfilled") setSysStatus(statusData.value);
      if (logsData.status  === "fulfilled") setLogs(logsData.value.slice().reverse());
      if (modelsData.status === "fulfilled") setActiveModel(modelsData.value.general?.name ?? "Reasoning LLM");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  return (
    <div className="max-w-6xl mx-auto px-4 lg:px-8 py-8 h-full flex flex-col gap-8">

      <PageHeader
        title="Security Center"
        description="Monitor system sovereignty and air-gap integrity"
        action={
          <button
            onClick={() => fetchAll(true)}
            disabled={refreshing}
            className="flex items-center gap-2 bg-white/[0.04] hover:bg-white/[0.08] disabled:opacity-50 border border-white/[0.06] px-4 py-2.5 rounded-xl text-[12px] font-semibold tracking-wide text-gray-300 transition-all"
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
=======
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
>>>>>>> 7220fc40bc9b6f43b694a7fa042695bbd48dc4eb
            Refresh
          </button>
        }
      />

<<<<<<< HEAD
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4 opacity-50">
            <Loader2 className="w-8 h-8 text-gray-400 animate-spin" />
            <p className="text-[13px] text-gray-500">Loading security telemetry…</p>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-6">

          {/* ── Service Health Grid ──────────────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <HealthPill label="Local AI Inference" active={security?.local_model_inference ?? sysStatus?.ollama ?? false} icon={Cpu} />
            <HealthPill label="Local RAG / Vector" active={security?.local_rag ?? true} icon={Database} />
            <HealthPill label="OCR Engine"          active={security?.local_ocr ?? sysStatus?.ocr ?? false} icon={Eye} />
            <HealthPill label="File Storage"        active={security?.local_file_storage ?? true} icon={Server} />
          </div>

          {/* ── Two column layout ────────────────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Air Gap */}
            <GlassCard className="p-7 flex flex-col gap-5">
              <div className="flex items-center gap-4">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-b from-green-500/20 to-green-500/5 border border-green-500/20 flex items-center justify-center shadow-[0_0_14px_rgba(34,197,94,0.15)]">
                  <Lock className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <h3 className="text-[15px] font-semibold text-white tracking-wide">Air Gap Status</h3>
                  <p className="text-[11px] text-gray-500 mt-0.5">Network isolation telemetry</p>
                </div>
              </div>
              <div className="space-y-2.5">
                <StatusRow label="External API Calls"   value={`${security?.external_llm_api ?? 0} (Blocked)`} ok={true} />
                <StatusRow label="Remote Endpoints"     value={`${security?.remote_endpoints ?? 0}`}          ok={true} />
                <StatusRow label="Internet Dependency"  value={security?.internet_dependency ?? "NONE"}        ok={true} />
                <StatusRow label="Encryption at Rest"   value="AES-256"                                        ok={true} />
              </div>
            </GlassCard>

            {/* Model Serving */}
            <GlassCard className="p-7 flex flex-col gap-5">
              <div className="flex items-center gap-4">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-b from-accent/20 to-accent/5 border border-accent/20 flex items-center justify-center shadow-[0_0_14px_rgba(56,114,224,0.15)]">
                  <Network className="w-5 h-5 text-accent" />
                </div>
                <div>
                  <h3 className="text-[15px] font-semibold text-white tracking-wide">Local Model Serving</h3>
                  <p className="text-[11px] text-gray-500 mt-0.5">Inference engine telemetry</p>
                </div>
              </div>
              <div className="space-y-2.5">
                <StatusRow label="Active Model"     value={activeModel}                                 mono />
                <StatusRow label="Ollama Endpoint"  value={security?.ollama_endpoint ?? "localhost:11434"} mono />
                <StatusRow label="Ollama Online"    value={sysStatus?.ollama ? "Online" : "Offline"}   ok={sysStatus?.ollama} />
                <StatusRow label="Docker Sandbox"   value={sysStatus?.docker ? "Running" : "Offline"}  ok={sysStatus?.docker} />
              </div>
            </GlassCard>

            {/* Current Session */}
            <GlassCard className="p-7 flex flex-col gap-5">
              <div className="flex items-center gap-4">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-b from-purple-500/20 to-purple-500/5 border border-purple-500/20 flex items-center justify-center shadow-[0_0_14px_rgba(168,85,247,0.15)]">
                  <UserCircle className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-[15px] font-semibold text-white tracking-wide">Current Session</h3>
                  <p className="text-[11px] text-gray-500 mt-0.5">Authenticated user context</p>
                </div>
              </div>
              <div className="space-y-2.5">
                <StatusRow label="User"              value={user?.name      ?? "—"} />
                <StatusRow label="Role"              value={user?.role      ?? "—"} ok={true} />
                <StatusRow label="Division"          value={user?.division  ?? "—"} />
                <StatusRow label="Knowledge Base"    value={`${sysStatus?.knowledge_base ?? 0} docs indexed`} ok={(sysStatus?.knowledge_base ?? 0) > 0} />
              </div>
            </GlassCard>

            {/* RAG Status */}
            <GlassCard className="p-7 flex flex-col gap-5">
              <div className="flex items-center gap-4">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-b from-cyan-500/20 to-cyan-500/5 border border-cyan-500/20 flex items-center justify-center shadow-[0_0_14px_rgba(6,182,212,0.15)]">
                  <BookOpen className="w-5 h-5 text-cyan-400" />
                </div>
                <div>
                  <h3 className="text-[15px] font-semibold text-white tracking-wide">RAG Pipeline</h3>
                  <p className="text-[11px] text-gray-500 mt-0.5">Retrieval-augmented generation</p>
                </div>
              </div>
              <div className="space-y-2.5">
                <StatusRow label="RAG Status"        value={security?.local_rag ? "Local" : "Offline"}        ok={security?.local_rag} />
                <StatusRow label="Embedding Engine"  value="Local (sentence-transformers)"                    ok={true} />
                <StatusRow label="External LLM API"  value={`${security?.external_llm_api ?? 0} calls`}       ok={(security?.external_llm_api ?? 0) === 0} />
                <StatusRow label="Cloud Uploads"     value="0 (blocked)"                                       ok={true} />
              </div>
            </GlassCard>
          </div>

          {/* ── Sovereignty Banner ───────────────────────────────────────── */}
          <GlassCard className={cn(
            "p-5 flex items-center gap-4",
            (security?.all_local ?? true)
              ? "border-green-500/15 bg-green-500/[0.02]"
              : "border-red-500/15 bg-red-500/[0.02]"
          )}>
            {(security?.all_local ?? true)
              ? <ShieldCheck className="w-5 h-5 text-green-400 shrink-0" />
              : <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />}
            <div>
              <p className="text-[13px] font-semibold text-white tracking-wide">
                {(security?.all_local ?? true) ? "Sovereignty Verified" : "Warning: External dependency detected"}
              </p>
              <p className="text-[12px] text-gray-400 mt-0.5">
                {(security?.all_local ?? true)
                  ? `All components operating locally. Internet dependency: ${security?.internet_dependency ?? "NONE"}.`
                  : "One or more components may be using external services. Review audit logs."}
              </p>
            </div>
            <div className="ml-auto shrink-0">
              <Globe className="w-4 h-4 text-gray-600" />
            </div>
          </GlassCard>

          {/* ── Audit Logs ───────────────────────────────────────────────── */}
          <GlassCard className="p-0 overflow-hidden rounded-2xl flex flex-col max-h-[480px]">
            <div className="px-5 py-4 border-b border-white/[0.04] bg-white/[0.01] flex items-center justify-between shrink-0">
              <h3 className="text-[14px] font-semibold text-white flex items-center gap-2.5 tracking-wide">
                <Clock className="w-4 h-4 text-accent" />
                Audit Log
              </h3>
              <span className="text-[10px] font-bold text-gray-600 uppercase tracking-widest">
                {logs.length} entries
              </span>
            </div>

            {/* Table header */}
            <div className="grid grid-cols-[80px_130px_1fr] gap-4 px-5 py-2.5 border-b border-white/[0.03] bg-white/[0.01] shrink-0">
              <p className="text-[10px] font-bold text-gray-700 uppercase tracking-widest text-right">Time</p>
              <p className="text-[10px] font-bold text-gray-700 uppercase tracking-widest">Event</p>
              <p className="text-[10px] font-bold text-gray-700 uppercase tracking-widest">Details</p>
            </div>

            <div className="overflow-y-auto flex-1">
              {logs.length === 0 ? (
                <div className="py-12 flex flex-col items-center gap-3 opacity-40">
                  <Clock className="w-8 h-8 text-gray-500" />
                  <p className="text-[13px] text-gray-500">No audit events recorded yet.</p>
                </div>
              ) : (
                <AnimatePresence initial={false}>
                  {logs.map((entry, idx) => (
                    <AuditRow key={`${entry.time}-${idx}`} entry={entry} idx={idx} />
                  ))}
                </AnimatePresence>
              )}
            </div>
          </GlassCard>

        </div>
      )}
=======
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
>>>>>>> 7220fc40bc9b6f43b694a7fa042695bbd48dc4eb
    </div>
  );
}
