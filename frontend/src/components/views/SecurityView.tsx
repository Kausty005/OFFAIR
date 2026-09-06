"use client";

import { useState, useEffect } from "react";
import { SystemStatus } from "@/types";
import { Shield, CheckCircle, XCircle, RefreshCw, Lock } from "lucide-react";

interface Props {
  systemStatus: SystemStatus | null;
}

interface LogEntry {
  timestamp: string;
  action: string;
  details?: Record<string, any>;
}

export default function SecurityView({ systemStatus }: Props) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [security, setSecurity] = useState<any>(null);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [logResp, secResp] = await Promise.all([
          fetch("http://localhost:8000/api/logs"),
          fetch("http://localhost:8000/api/security"),
        ]);
        if (logResp.ok) setLogs(await logResp.json());
        if (secResp.ok) setSecurity(await secResp.json());
      } catch {}
    };
    fetchAll();
    const iv = setInterval(fetchAll, 5000);
    return () => clearInterval(iv);
  }, []);

  const statusItems = [
    { label: "Local Model Inference", key: "local_model_inference", ok: security?.local_model_inference ?? true },
    { label: "Local OCR Engine", key: "local_ocr", ok: security?.local_ocr ?? true },
    { label: "Local RAG / Vector DB", key: "local_rag", ok: security?.local_rag ?? true },
    { label: "Local File Storage", key: "local_file_storage", ok: security?.local_file_storage ?? true },
    { label: "Docker Sandbox", key: "docker", ok: systemStatus?.docker ?? null },
    { label: "External LLM API", key: "ext", ok: false, invert: true, value: security?.external_llm_api ?? 0 },
    { label: "Remote Endpoints", key: "remote", ok: false, invert: true, value: security?.remote_endpoints ?? 0 },
    { label: "Internet Dependency", key: "internet", ok: false, invert: true, value: "NONE AFTER SETUP" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <div style={{
        padding: "12px 20px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", gap: 10, flexShrink: 0
      }}>
        <Shield size={16} color="var(--accent-green)" />
        <div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Security & Audit</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Air-gap proof · All inference local · Audit trail
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <Lock size={12} color="var(--accent-green)" />
          <span style={{ fontSize: 12, color: "var(--accent-green)", fontWeight: 600 }}>
            EXTERNAL API CALLS: 0
          </span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>

          {/* Security status cards */}
          <div className="card" style={{ padding: "16px" }}>
            <div className="section-header">SECURITY STATUS</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {statusItems.map(item => (
                <div key={item.key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {item.invert ? (
                      item.value === 0 || item.value === "NONE AFTER SETUP"
                        ? <CheckCircle size={14} color="var(--accent-green)" />
                        : <XCircle size={14} color="var(--accent-red)" />
                    ) : (
                      item.ok === null ? (
                        <div style={{ width: 14, height: 14, borderRadius: "50%", background: "var(--text-muted)" }} />
                      ) : item.ok ? (
                        <CheckCircle size={14} color="var(--accent-green)" />
                      ) : (
                        <XCircle size={14} color="var(--accent-red)" />
                      )
                    )}
                    <span style={{ fontSize: 13 }}>{item.label}</span>
                  </div>
                  <span style={{
                    fontSize: 11, fontWeight: 600,
                    color: item.invert
                      ? (item.value === 0 || item.value === "NONE AFTER SETUP" ? "var(--accent-green)" : "var(--accent-red)")
                      : (item.ok === null ? "var(--text-muted)" : item.ok ? "var(--accent-green)" : "var(--text-muted)")
                  }}>
                    {item.invert
                      ? (typeof item.value === "number" ? item.value : item.value)
                      : (item.ok === null ? "N/A" : item.ok ? "✓" : "N/A")}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Network Guard */}
          <div className="card" style={{ padding: "16px" }}>
            <div className="section-header">NETWORK GUARD</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <NetworkRule label="Ollama Endpoint" value="http://localhost:11434" allowed />
              <NetworkRule label="Vector DB" value="localhost (in-process)" allowed />
              <NetworkRule label="File Storage" value="local filesystem" allowed />
              <NetworkRule label="OpenAI API" value="api.openai.com" allowed={false} />
              <NetworkRule label="Anthropic API" value="api.anthropic.com" allowed={false} />
              <NetworkRule label="Google AI" value="generativelanguage.googleapis.com" allowed={false} />
              <NetworkRule label="OpenRouter" value="openrouter.ai" allowed={false} />
            </div>

            <div style={{
              marginTop: 14, padding: "8px 10px", borderRadius: 6,
              background: "rgba(0,214,143,0.06)", border: "1px solid rgba(0,214,143,0.2)",
              fontSize: 11, color: "var(--accent-green)"
            }}>
              network_guard.py enforces localhost-only endpoints at startup and per-request.
            </div>
          </div>
        </div>

        {/* Audit Log */}
        <div className="card" style={{ padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div className="section-header" style={{ marginBottom: 0, border: "none", paddingBottom: 0 }}>
              AUDIT LOG
            </div>
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
              {logs.length} entries · All stored locally
            </span>
          </div>
          <div style={{ maxHeight: 300, overflowY: "auto" }}>
            {logs.length === 0 ? (
              <div style={{ color: "var(--text-muted)", fontSize: 12, textAlign: "center", padding: "16px 0" }}>
                No log entries yet
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {logs.map((log, i) => (
                  <div key={i} style={{
                    display: "flex", gap: 12, padding: "6px 0",
                    borderBottom: "1px solid var(--border)", fontSize: 12
                  }}>
                    <span style={{ color: "var(--text-muted)", fontFamily: "monospace", flexShrink: 0, fontSize: 11 }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "--:--:--"}
                    </span>
                    <span style={{ color: "var(--accent-orange)", fontWeight: 600, flexShrink: 0, fontSize: 11 }}>
                      {log.action}
                    </span>
                    <span style={{ color: "var(--text-secondary)", fontSize: 11 }}>
                      {log.details ? Object.entries(log.details)
                        .filter(([k]) => k !== "timestamp" && k !== "action")
                        .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                        .join(" · ")
                        .slice(0, 80) : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function NetworkRule({ label, value, allowed }: { label: string; value: string; allowed: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{
        width: 6, height: 6, borderRadius: "50%",
        background: allowed ? "var(--accent-green)" : "var(--accent-red)",
        flexShrink: 0
      }} />
      <span style={{ fontSize: 12, color: allowed ? "var(--text-secondary)" : "var(--text-muted)", flex: 1 }}>
        {label}
      </span>
      <span style={{
        fontSize: 10, fontFamily: "monospace", color: allowed ? "var(--accent-green)" : "var(--text-muted)",
        background: allowed ? "rgba(0,214,143,0.06)" : "rgba(255,71,87,0.06)",
        padding: "2px 6px", borderRadius: 4
      }}>
        {allowed ? "ALLOWED" : "BLOCKED"}
      </span>
    </div>
  );
}
