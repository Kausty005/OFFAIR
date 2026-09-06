"use client";

import { useState } from "react";
import { AgentCallbacks } from "@/types";
import { useAgent } from "@/hooks/useAgent";
import {
  Code2, Play, CheckCircle, AlertTriangle,
  Terminal, Lock, Wifi, WifiOff
} from "lucide-react";

interface Props {
  callbacks: AgentCallbacks;
}

const DEMO_TASK = "Create Python code to calculate pump efficiency from flow rate, input pressure, output pressure, and shaft power. Include proper error handling and unit tests.";

export default function CodingView({ callbacks }: Props) {
  const [task, setTask] = useState(DEMO_TASK);

  const { run, isRunning, steps, result, error } = useAgent({
    onStart: callbacks.onStart,
    onStep: callbacks.onStep,
    onComplete: callbacks.onComplete,
    onError: callbacks.onError,
    setRouterInfo: callbacks.setRouterInfo,
  });

  const handleRun = () => {
    if (!task.trim() || isRunning) return;
    run(task, []);
  };

  const sandboxResult = result?.tool_results?.sandbox_result;
  const generatedCode = result?.tool_results?.generated_code;
  const testsPassed = sandboxResult?.tests_passed ?? 0;
  const testsTotal = sandboxResult?.tests_total ?? 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div style={{
        padding: "12px 20px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Code2 size={16} color="var(--accent-orange)" />
          <div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>Coding Agent</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              Code generation → Docker sandbox → Tests → Verified
            </div>
          </div>
        </div>

        {/* Sandbox status */}
        <div style={{ display: "flex", gap: 12 }}>
          <InfoBadge label="MODEL" value="Qwen2.5-Coder" color="blue" />
          <InfoBadge label="SANDBOX" value="Docker" color="orange" />
          <InfoBadge label="NETWORK" value="NONE" color="red" icon={<WifiOff size={9} />} />
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left: Input + steps */}
        <div style={{
          flex: 1, overflowY: "auto", padding: "16px 20px",
          borderRight: "1px solid var(--border)"
        }}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
              TASK
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
            disabled={isRunning || !task.trim()}
            className="btn btn-primary"
            style={{ width: "100%", justifyContent: "center", padding: "12px", marginBottom: 20 }}
          >
            {isRunning ? (
              <>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "white", animation: "pulse-dot 1s infinite" }} />
                Generating & Testing…
              </>
            ) : (
              <>
                <Play size={14} />
                Generate Code + Run Tests
              </>
            )}
          </button>

          {/* Steps */}
          {steps.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {steps.map((step, i) => (
                <div key={i} className="fade-in" style={{
                  display: "flex", gap: 10, padding: "10px 12px",
                  background: "var(--bg-card)", border: "1px solid var(--border)",
                  borderRadius: 6
                }}>
                  <span style={{
                    color: {
                      done: "var(--accent-green)",
                      running: "var(--accent-orange)",
                      failed: "var(--accent-red)",
                      pending: "var(--text-muted)",
                      skipped: "var(--text-muted)",
                    }[step.status as string] || "var(--text-muted)",
                    fontWeight: 700, flexShrink: 0
                  }}>
                    {{ done: "✓", running: "●", failed: "✗", pending: "○", skipped: "○" }[step.status as string] || "○"}
                  </span>
                  <div>
                    <div style={{ fontSize: 13 }}>{step.description}</div>
                    {step.result && (
                      <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                        {step.result.slice(0, 100)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div style={{
              marginTop: 16, padding: "12px", display: "flex", gap: 8,
              background: "rgba(255,71,87,0.08)", border: "1px solid rgba(255,71,87,0.25)",
              borderRadius: 8, color: "var(--accent-red)", fontSize: 13
            }}>
              <AlertTriangle size={16} style={{ flexShrink: 0 }} />
              {error}
            </div>
          )}
        </div>

        {/* Right: Code + sandbox output */}
        <div style={{ width: 460, overflowY: "auto", padding: "16px 20px" }}>
          {!result && !isRunning && (
            <div style={{ textAlign: "center", marginTop: 60, color: "var(--text-muted)" }}>
              <Terminal size={32} style={{ margin: "0 auto 12px" }} />
              <div style={{ fontSize: 13 }}>Generated code will appear here</div>
              <div style={{ fontSize: 11, marginTop: 6 }}>
                Executed in isolated Docker container
              </div>
            </div>
          )}

          {generatedCode && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 8, fontWeight: 600, letterSpacing: "0.06em" }}>
                GENERATED CODE
              </div>
              <div className="code-block">
                {generatedCode}
              </div>
            </div>
          )}

          {sandboxResult && (
            <div style={{ marginBottom: 16 }}>
              <div style={{
                display: "flex", alignItems: "center", gap: 8, marginBottom: 10,
                padding: "10px 14px", borderRadius: 8,
                background: sandboxResult.success ? "rgba(0,214,143,0.06)" : "rgba(255,71,87,0.06)",
                border: `1px solid ${sandboxResult.success ? "rgba(0,214,143,0.2)" : "rgba(255,71,87,0.2)"}`
              }}>
                {sandboxResult.success
                  ? <CheckCircle size={16} color="var(--accent-green)" />
                  : <AlertTriangle size={16} color="var(--accent-red)" />
                }
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: sandboxResult.success ? "var(--accent-green)" : "var(--accent-red)" }}>
                    Tests {testsTotal > 0 ? `${testsPassed}/${testsTotal} PASSED` : sandboxResult.success ? "PASSED" : "FAILED"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    Docker · Network: NONE · Timeout enforced
                  </div>
                </div>
              </div>

              {sandboxResult.stdout && (
                <div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4, fontWeight: 600 }}>STDOUT</div>
                  <div className="code-block" style={{ fontSize: 11 }}>
                    {sandboxResult.stdout.slice(0, 1000)}
                  </div>
                </div>
              )}

              {sandboxResult.stderr && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 11, color: "var(--accent-red)", marginBottom: 4, fontWeight: 600 }}>STDERR</div>
                  <div className="code-block" style={{ fontSize: 11, borderColor: "rgba(255,71,87,0.3)", color: "var(--accent-red)" }}>
                    {sandboxResult.stderr.slice(0, 500)}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function InfoBadge({ label, value, color, icon }: {
  label: string; value: string; color: string; icon?: React.ReactNode;
}) {
  const colors: Record<string, string> = {
    blue: "var(--accent-blue)",
    orange: "var(--accent-orange)",
    green: "var(--accent-green)",
    red: "var(--accent-red)",
  };
  const c = colors[color];
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: "0.06em", marginBottom: 2 }}>{label}</div>
      <div style={{
        display: "flex", alignItems: "center", gap: 3,
        fontSize: 11, fontWeight: 700, color: c,
        background: `${c}15`, padding: "2px 8px",
        borderRadius: 999, border: `1px solid ${c}30`
      }}>
        {icon}
        {value}
      </div>
    </div>
  );
}
