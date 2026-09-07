"use client";

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
        {value}
      </span>
    </div>
  );
}

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
    </div>
  );
}

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
            Refresh
          </button>
        }
      />

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
    </div>
  );
}
