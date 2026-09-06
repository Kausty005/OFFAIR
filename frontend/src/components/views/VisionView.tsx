"use client";

import { useState, useRef } from "react";
import { AgentCallbacks } from "@/types";
import { useAgent, uploadFiles } from "@/hooks/useAgent";
import { Eye, Upload, AlertTriangle, Info } from "lucide-react";

interface Props {
  callbacks: AgentCallbacks;
}

export default function VisionView({ callbacks }: Props) {
  const [uploadedFile, setUploadedFile] = useState<{ name: string; path: string; preview: string } | null>(null);
  const [task, setTask] = useState("Analyze this inspection photograph and identify visible equipment, measurements, damage, or anomalies.");
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
    const preview = URL.createObjectURL(f);
    const paths = await uploadFiles([f]);
    setUploadedFile({ name: f.name, path: paths[0] || "", preview });
  };

  const handleRun = () => {
    if (!uploadedFile || isRunning) return;
    run(task, [uploadedFile.path]);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <div style={{
        padding: "12px 20px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", gap: 10, flexShrink: 0
      }}>
        <Eye size={16} color="var(--accent-blue)" />
        <div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Vision Analysis</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Multimodal · Local vision model · Industrial image understanding
          </div>
        </div>
        <div style={{ marginLeft: "auto" }}>
          <span style={{
            fontSize: 11, color: "var(--accent-blue)", fontWeight: 600,
            background: "rgba(77,157,224,0.1)", padding: "3px 8px",
            borderRadius: 999, border: "1px solid rgba(77,157,224,0.25)"
          }}>
            Qwen3-VL / LLaVA-Phi3
          </span>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left: Upload + config */}
        <div style={{ width: 340, borderRight: "1px solid var(--border)", overflowY: "auto", padding: "16px" }}>
          {/* Upload zone */}
          <div
            onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={e => { e.preventDefault(); setIsDragging(false); handleFile(e.dataTransfer.files); }}
            onClick={() => !uploadedFile && fileRef.current?.click()}
            style={{
              border: `2px dashed ${isDragging ? "var(--accent-blue)" : uploadedFile ? "var(--accent-green)" : "var(--border)"}`,
              borderRadius: 8, overflow: "hidden", cursor: uploadedFile ? "default" : "pointer",
              transition: "all 0.2s", marginBottom: 16, minHeight: 200,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "var(--bg-card)"
            }}
          >
            {uploadedFile ? (
              <img
                src={uploadedFile.preview}
                alt="Uploaded"
                style={{ width: "100%", objectFit: "contain", maxHeight: 260 }}
              />
            ) : (
              <div style={{ textAlign: "center", padding: 24 }}>
                <Upload size={32} color="var(--text-muted)" style={{ margin: "0 auto 8px" }} />
                <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                  Drop inspection image here
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
                  PNG, JPG, JPEG
                </div>
              </div>
            )}
            <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }}
              onChange={e => handleFile(e.target.files)} />
          </div>

          {uploadedFile && (
            <div style={{ marginBottom: 12 }}>
              <button
                onClick={() => setUploadedFile(null)}
                className="btn btn-ghost"
                style={{ fontSize: 11, padding: "4px 10px", width: "100%", justifyContent: "center" }}
              >
                Remove image
              </button>
            </div>
          )}

          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
              ANALYSIS PROMPT
            </label>
            <textarea
              className="input"
              value={task}
              onChange={e => setTask(e.target.value)}
              rows={4}
              style={{ resize: "none" }}
            />
          </div>

          <button
            onClick={handleRun}
            disabled={isRunning || !uploadedFile}
            className="btn"
            style={{
              width: "100%", justifyContent: "center", padding: "11px",
              background: "rgba(77,157,224,0.1)", border: "1px solid rgba(77,157,224,0.3)",
              color: "var(--accent-blue)", fontWeight: 600
            }}
          >
            {isRunning ? "Analyzing…" : "Analyze Image"}
          </button>

          {/* Disclaimer */}
          <div style={{
            marginTop: 16, padding: "10px 12px",
            background: "rgba(255,107,53,0.05)", border: "1px solid rgba(255,107,53,0.2)",
            borderRadius: 6, display: "flex", gap: 8
          }}>
            <Info size={13} color="var(--accent-orange)" style={{ flexShrink: 0, marginTop: 1 }} />
            <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.4 }}>
              AI-generated observation — human verification required.
            </div>
          </div>
        </div>

        {/* Right: Result */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {!result && !isRunning && !steps.length && (
            <div style={{ textAlign: "center", marginTop: 60, color: "var(--text-muted)" }}>
              <Eye size={32} style={{ margin: "0 auto 12px" }} />
              <div style={{ fontSize: 13 }}>Upload an image and click Analyze</div>
              <div style={{ fontSize: 11, marginTop: 6 }}>
                Vision model runs entirely on local hardware
              </div>
            </div>
          )}

          {steps.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8, fontWeight: 600, letterSpacing: "0.06em" }}>
                AGENT STEPS
              </div>
              {steps.map((step, i) => (
                <div key={i} className="fade-in" style={{
                  display: "flex", gap: 8, marginBottom: 6,
                  color: { done: "var(--text-secondary)", running: "var(--text-primary)", failed: "var(--accent-red)", pending: "var(--text-muted)", skipped: "var(--text-muted)" }[step.status as string] || "var(--text-muted)",
                  fontSize: 13
                }}>
                  <span style={{ fontWeight: 700 }}>
                    {{ done: "✓", running: "●", failed: "✗", pending: "○", skipped: "○" }[step.status as string] || "○"}
                  </span>
                  <span>{step.description}</span>
                </div>
              ))}
            </div>
          )}

          {result?.final_output && (
            <div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8, fontWeight: 600, letterSpacing: "0.06em" }}>
                VISION ANALYSIS RESULT
              </div>
              <div style={{
                background: "var(--bg-card)", border: "1px solid var(--border)",
                borderRadius: 8, padding: "16px",
                fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7,
                whiteSpace: "pre-wrap"
              }}>
                {result.final_output}
              </div>

              <div style={{
                marginTop: 12, padding: "8px 12px",
                background: "rgba(255,107,53,0.05)", border: "1px solid rgba(255,107,53,0.2)",
                borderRadius: 6, fontSize: 11, color: "var(--accent-orange)"
              }}>
                ⚠️ AI-generated observation — human expert verification required before action.
              </div>
            </div>
          )}

          {error && (
            <div style={{
              padding: "12px", display: "flex", gap: 8,
              background: "rgba(255,71,87,0.08)", border: "1px solid rgba(255,71,87,0.25)",
              borderRadius: 8, color: "var(--accent-red)", fontSize: 13
            }}>
              <AlertTriangle size={16} style={{ flexShrink: 0 }} />
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
