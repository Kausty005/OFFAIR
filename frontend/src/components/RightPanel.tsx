"use client";

import { AgentStep, ModelRouterInfo, RAGSource } from "@/types";
import { CheckCircle, Circle, XCircle, Loader2, Zap, Database, FileText, Download, GitBranch } from "lucide-react";
import { useEffect, useRef } from "react";

interface Props {
  agentSteps: AgentStep[];
  routerInfo: ModelRouterInfo | null;
  isRunning: boolean;
  outputFiles: string[];
  ragSources: RAGSource[];
}

export default function RightPanel({ agentSteps, routerInfo, isRunning, outputFiles, ragSources }: Props) {
  const stepsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (stepsRef.current) stepsRef.current.scrollTop = stepsRef.current.scrollHeight;
  }, [agentSteps]);

  return (
    <div style={{
      width: 272,
      backgroundColor: "var(--bg-secondary)",
      borderLeft: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      flexShrink: 0,
      overflow: "hidden",
    }}>

      {/* ── Agent Activity ── */}
      <Section
        icon={<Zap size={10} />}
        title="AGENT ACTIVITY"
        extra={isRunning && <Loader2 size={10} style={{ animation: "spin 1s linear infinite" }} />}
      >
        <div ref={stepsRef} style={{ maxHeight: 250, overflowY: "auto", display: "flex", flexDirection: "column", gap: 5 }}>
          {agentSteps.length === 0 ? (
            <div style={{ fontSize: 12, color: "var(--text-muted)", padding: "8px 0" }}>
              No active task
            </div>
          ) : (
            agentSteps.map((step, i) => <StepRow key={i} step={step} />)
          )}
        </div>
      </Section>

      <Divider />

      {/* ── Model Router ── */}
      <Section icon={<GitBranch size={10} />} title="MODEL ROUTER">
        {routerInfo ? (
          <RouterDisplay info={routerInfo} />
        ) : (
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Awaiting task…</div>
        )}
      </Section>

      <Divider />

      {/* ── RAG Sources ── */}
      {ragSources.length > 0 && (
        <>
          <Section icon={<Database size={10} />} title="RAG SOURCES">
            <div style={{ maxHeight: 180, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
              {ragSources.slice(0, 4).map((src, i) => (
                <div key={i} style={{
                  background: "var(--bg-card)", border: "1px solid var(--border)",
                  borderRadius: 6, padding: "8px 10px",
                }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "var(--accent-blue)", marginBottom: 3 }}>
                    {src.document}{src.page && <span style={{ color: "var(--text-muted)", fontWeight: 400 }}> · p.{src.page}</span>}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.4 }}>
                    {src.text?.slice(0, 90)}…
                  </div>
                </div>
              ))}
            </div>
          </Section>
          <Divider />
        </>
      )}

      {/* ── Generated Files ── */}
      {outputFiles.length > 0 && (
        <>
          <Section icon={<FileText size={10} />} title="GENERATED FILES">
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {outputFiles.map((file, i) => {
                const name = file.split(/[/\\]/).pop() || file;
                return (
                  <a
                    key={i}
                    href={`http://localhost:8000/api/download/${encodeURIComponent(name)}`}
                    download={name}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "8px 10px", borderRadius: 6,
                      background: "rgba(34,197,94,0.06)",
                      border: "1px solid rgba(34,197,94,0.2)",
                      color: "var(--accent-green)", fontSize: 12,
                      textDecoration: "none", transition: "all 0.15s",
                    }}
                  >
                    <FileText size={12} />
                    <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {name}
                    </span>
                    <Download size={11} />
                  </a>
                );
              })}
            </div>
          </Section>
          <Divider />
        </>
      )}

      {/* ── Security mini ── */}
      <div style={{ marginTop: "auto", padding: "12px" }}>
        <SecurityMini />
      </div>
    </div>
  );
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function Section({ icon, title, extra, children }: {
  icon: React.ReactNode; title: string; extra?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <div style={{ padding: "12px" }}>
      <div style={{
        display: "flex", alignItems: "center", gap: 5, marginBottom: 10,
        fontSize: 10, fontWeight: 700, color: "var(--text-muted)", letterSpacing: "0.08em",
        paddingBottom: 6, borderBottom: "1px solid var(--border)",
      }}>
        {icon}{title}
        {extra && <span style={{ marginLeft: "auto", color: "var(--accent-orange)" }}>{extra}</span>}
      </div>
      {children}
    </div>
  );
}

function Divider() {
  return <div style={{ height: 1, background: "var(--border)", flexShrink: 0 }} />;
}

function StepRow({ step }: { step: AgentStep }) {
  const icon = {
    done:    <CheckCircle size={12} style={{ color: "var(--accent-green)", flexShrink: 0 }} />,
    running: <Loader2 size={12} style={{ color: "var(--accent-orange)", flexShrink: 0, animation: "spin 1s linear infinite" }} />,
    failed:  <XCircle size={12} style={{ color: "var(--accent-red)", flexShrink: 0 }} />,
    skipped: <Circle size={12} style={{ color: "var(--text-muted)", flexShrink: 0 }} />,
    pending: <Circle size={12} style={{ color: "var(--text-muted)", flexShrink: 0 }} />,
  }[step.status] ?? <Circle size={12} style={{ color: "var(--text-muted)", flexShrink: 0 }} />;

  const textColor = {
    done:    "var(--text-secondary)",
    running: "var(--text-primary)",
    failed:  "var(--accent-red)",
    skipped: "var(--text-muted)",
    pending: "var(--text-muted)",
  }[step.status] ?? "var(--text-muted)";

  return (
    <div className="fade-in" style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
      <div style={{ marginTop: 1 }}>{icon}</div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 12, color: textColor, lineHeight: 1.4 }}>{step.description}</div>
        {step.result && step.status === "done" && (
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 1, lineHeight: 1.3 }}>
            {step.result.slice(0, 80)}{step.result.length > 80 ? "…" : ""}
          </div>
        )}
      </div>
    </div>
  );
}

function RouterDisplay({ info }: { info: ModelRouterInfo }) {
  const taskColors: Record<string, string> = {
    vision:             "var(--accent-blue)",
    coding:             "var(--accent-orange)",
    document:           "var(--accent-green)",
    document_operation: "var(--accent-green)",
    ocr:                "var(--accent-blue)",
    general:            "var(--accent-green)",
    calculation:        "var(--accent-purple)",
  };
  const color = taskColors[info.taskType] || "var(--accent-orange)";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <Row label="TASK">
        <span style={{
          fontSize: 11, fontWeight: 700, color,
          background: `${color}18`, padding: "1px 8px", borderRadius: 999,
          border: `1px solid ${color}35`,
        }}>{info.taskType.toUpperCase()}</span>
      </Row>
      <Row label="SELECTED MODEL">
        <span style={{ fontSize: 12, color: "var(--text-primary)", fontFamily: "monospace" }}>
          {info.selectedModel || "—"}
        </span>
      </Row>
      <Row label="REASON">
        <span style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.4 }}>{info.reason}</span>
      </Row>
      <Row label="INFERENCE">
        <span style={{ fontSize: 11, color: "var(--accent-green)", fontWeight: 600 }}>{info.inference}</span>
      </Row>
      <Row label="ENDPOINT">
        <span style={{ fontSize: 11, color: "var(--text-secondary)", fontFamily: "monospace" }}>{info.endpoint}</span>
      </Row>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
      <span style={{ fontSize: 10, color: "var(--text-muted)", flexShrink: 0, paddingTop: 1 }}>{label}</span>
      <div style={{ textAlign: "right" }}>{children}</div>
    </div>
  );
}

function SecurityMini() {
  const rows: [string, boolean][] = [
    ["Local AI",  true],
    ["Local OCR", true],
    ["Local RAG", true],
    ["Ext API",   false],
  ];
  return (
    <div style={{
      background: "rgba(34,197,94,0.04)",
      border: "1px solid rgba(34,197,94,0.15)",
      borderRadius: 6, padding: "8px 10px",
    }}>
      <div style={{ fontSize: 10, color: "var(--accent-green)", fontWeight: 700, marginBottom: 6, letterSpacing: "0.06em" }}>
        SECURITY
      </div>
      {rows.map(([label, ok]) => (
        <div key={label} style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{label}</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: ok ? "var(--accent-green)" : "var(--accent-red)" }}>
            {ok ? "✓" : "✗"}
          </span>
        </div>
      ))}
    </div>
  );
}
