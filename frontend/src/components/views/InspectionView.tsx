"use client";

import { useState, useRef } from "react";
import { AgentCallbacks } from "@/types";
import { useAgent, uploadFiles } from "@/hooks/useAgent";
import { Factory, Upload, FileText, Play, AlertTriangle, CheckCircle, X } from "lucide-react";

interface Props {
  callbacks: AgentCallbacks;
}

const DEMO_TASK = "Analyze this inspection report using the organization's maintenance procedures and prepare an approval note.";

export default function InspectionView({ callbacks }: Props) {
  const [uploadedFile, setUploadedFile] = useState<{ name: string; path: string } | null>(null);
  const [task, setTask] = useState(DEMO_TASK);
  const [isDragging, setIsDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const { run, isRunning, steps, result, error } = useAgent({
    onStart: callbacks.onStart,
    onStep: callbacks.onStep,
    onComplete: callbacks.onComplete,
    onError: callbacks.onError,
    setRouterInfo: callbacks.setRouterInfo,
  });

  const handleFile = async (files: FileList | null) => {
    if (!files?.length) return;
    const f = files[0];
    const paths = await uploadFiles([f]);
    setUploadedFile({ name: f.name, path: paths[0] || "" });
  };

  const handleRun = async () => {
    if (!task.trim() || isRunning) return;
    const filePaths = uploadedFile ? [uploadedFile.path] : [];
    await run(task, filePaths);
  };

  const handleRunDemo = async () => {
    // Use demo file if exists, otherwise just run without file
    setTask(DEMO_TASK);
    const filePaths = uploadedFile ? [uploadedFile.path] : [];
    await run(DEMO_TASK, filePaths);
  };

  const progressPct = steps.length > 0
    ? Math.round((steps.filter(s => s.status === "done").length / steps.length) * 100)
    : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div style={{
        padding: "12px 20px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Factory size={16} color="var(--accent-orange)" />
          <div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>Inspection Agent</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              PDF → OCR → Vision → RAG → Approval Note
            </div>
          </div>
        </div>
        <button
          onClick={handleRunDemo}
          disabled={isRunning}
          className="btn btn-primary"
          style={{ fontSize: 12 }}
        >
          <Play size={12} />
          Run Demo
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        {/* Upload zone */}
        <div
          onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={e => { e.preventDefault(); setIsDragging(false); handleFile(e.dataTransfer.files); }}
          onClick={() => !uploadedFile && fileRef.current?.click()}
          style={{
            border: `2px dashed ${isDragging ? "var(--accent-orange)" : uploadedFile ? "var(--accent-green)" : "var(--border)"}`,
            borderRadius: 8, padding: "24px", textAlign: "center",
            cursor: uploadedFile ? "default" : "pointer",
            background: isDragging ? "var(--glow-orange)" : "var(--bg-card)",
            transition: "all 0.2s", marginBottom: 16
          }}
        >
          {uploadedFile ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 12 }}>
              <FileText size={24} color="var(--accent-green)" />
              <div style={{ textAlign: "left" }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--accent-green)" }}>
                  {uploadedFile.name}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>Ready to process</div>
              </div>
              <button
                onClick={e => { e.stopPropagation(); setUploadedFile(null); }}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  color: "var(--text-muted)", marginLeft: 8, padding: 4
                }}
              >
                <X size={16} />
              </button>
            </div>
          ) : (
            <div>
              <Upload size={28} color="var(--text-muted)" style={{ margin: "0 auto 8px" }} />
              <div style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 4 }}>
                Drop inspection report PDF here
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                Supports PDF, scanned documents · Local OCR applied automatically
              </div>
            </div>
          )}
          <input ref={fileRef} type="file" accept=".pdf" style={{ display: "none" }}
            onChange={e => handleFile(e.target.files)} />
        </div>

        {/* Task input */}
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
            TASK DESCRIPTION
          </label>
          <textarea
            className="input"
            value={task}
            onChange={e => setTask(e.target.value)}
            rows={3}
            style={{ resize: "none" }}
          />
        </div>

        {/* Run button */}
        <button
          onClick={handleRun}
          disabled={isRunning || !task.trim()}
          className="btn btn-primary"
          style={{ width: "100%", justifyContent: "center", padding: "12px" }}
        >
          {isRunning ? (
            <>
              <span className="thinking-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: "white" }} />
              Processing…
            </>
          ) : (
            <>
              <Play size={14} />
              Run Inspection Analysis
            </>
          )}
        </button>

        {/* Progress */}
        {steps.length > 0 && (
          <div style={{ marginTop: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 12 }}>
              <span style={{ color: "var(--text-muted)" }}>Progress</span>
              <span style={{ color: "var(--accent-orange)" }}>{progressPct}%</span>
            </div>
            <div className="progress-bar" style={{ marginBottom: 16 }}>
              <div className="progress-fill" style={{ width: `${progressPct}%` }} />
            </div>

            {/* Steps */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {steps.map((step, i) => (
                <StepCard key={i} step={step} />
              ))}
            </div>
          </div>
        )}

        {/* Final result */}
        {result && (
          <div style={{ marginTop: 20 }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 8, marginBottom: 12
            }}>
              <CheckCircle size={16} color="var(--accent-green)" />
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--accent-green)" }}>
                Analysis Complete {result.verified && "· Verified"}
              </span>
            </div>

            {result.final_output && (
              <div style={{
                background: "var(--bg-card)", border: "1px solid var(--border)",
                borderRadius: 8, padding: "16px", marginBottom: 12,
                whiteSpace: "pre-wrap", fontSize: 13, color: "var(--text-secondary)",
                lineHeight: 1.6, maxHeight: 400, overflowY: "auto"
              }}>
                {result.final_output}
              </div>
            )}

            {result.output_files?.length > 0 && (
              <div style={{
                background: "rgba(0,214,143,0.05)", border: "1px solid rgba(0,214,143,0.2)",
                borderRadius: 8, padding: "12px", display: "flex", alignItems: "center", gap: 10
              }}>
                <FileText size={16} color="var(--accent-green)" />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: "var(--accent-green)" }}>
                    Approval Note Generated
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {result.output_files[0].split(/[/\\]/).pop()}
                  </div>
                </div>
                <a
                  href={`/api/download/${encodeURIComponent(
                    result.output_files[0].split(/[/\\]/).pop() || ""
                  )}`}
                  download
                  className="btn btn-success"
                  style={{ fontSize: 12, padding: "6px 12px" }}
                >
                  Download DOCX
                </a>
              </div>
            )}
          </div>
        )}

        {error && (
          <div style={{
            marginTop: 16, display: "flex", gap: 8, padding: "12px",
            background: "rgba(255,71,87,0.08)", border: "1px solid rgba(255,71,87,0.25)",
            borderRadius: 8, color: "var(--accent-red)", fontSize: 13
          }}>
            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
            {error}
          </div>
        )}
      </div>
    </div>
  );
}

function StepCard({ step }: { step: any }) {
  const colors: Record<string, string> = {
    done: "var(--accent-green)",
    running: "var(--accent-orange)",
    failed: "var(--accent-red)",
    skipped: "var(--text-muted)",
    pending: "var(--text-muted)",
  };
  const icons: Record<string, string> = {
    done: "✓",
    running: "●",
    failed: "✗",
    skipped: "○",
    pending: "○",
  };
  const c = colors[step.status] || "var(--text-muted)";

  return (
    <div className="fade-in" style={{
      display: "flex", gap: 12, padding: "10px 14px",
      background: "var(--bg-card)", border: `1px solid ${step.status === "running" ? "var(--accent-orange)33" : "var(--border)"}`,
      borderRadius: 6, transition: "border-color 0.2s"
    }}>
      <span style={{ color: c, fontWeight: 700, fontSize: 12, flexShrink: 0 }}>
        {icons[step.status] || "○"}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, color: step.status === "running" ? "var(--text-primary)" : "var(--text-secondary)" }}>
          {step.description}
        </div>
        {step.result && (
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 3, lineHeight: 1.4 }}>
            {step.result.slice(0, 120)}{step.result.length > 120 ? "…" : ""}
          </div>
        )}
      </div>
      {step.tool && (
        <span style={{
          fontSize: 10, color: "var(--accent-blue)",
          background: "rgba(77,157,224,0.08)", padding: "1px 6px",
          borderRadius: 999, border: "1px solid rgba(77,157,224,0.2)",
          flexShrink: 0, alignSelf: "flex-start", fontFamily: "monospace"
        }}>
          {step.tool}
        </span>
      )}
    </div>
  );
}
