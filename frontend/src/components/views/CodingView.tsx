"use client";

import { useState } from "react";
import { AgentCallbacks } from "@/types";
import { useAgent } from "@/hooks/useAgent";
import {
  Code2, Play, CheckCircle, AlertTriangle,
  Terminal, Lock, WifiOff, Copy, Check,
  RotateCcw, ArrowRight, CornerDownLeft, ShieldCheck,
  Zap, Sparkles, Clock, Layers, ChevronDown
} from "lucide-react";

interface Props {
  callbacks: AgentCallbacks;
}

const DEMO_TASK = "Create Python code to calculate pump efficiency from flow rate, input pressure, output pressure, and shaft power. Include proper error handling and unit tests.";

const SAMPLE_INTERACTIVE_CODE = `import sys

def main():
    print("=== INDUSTRIAL PUMP MONITOR ===")
    print("Reading sensor parameters from stdin...")
    
    # Read operator or equipment tag
    line1 = sys.stdin.readline().strip()
    tag = line1 if line1 else "PUMP-104-A"
    
    # Read temperature and pressure values
    try:
        temp_input = sys.stdin.readline().strip()
        press_input = sys.stdin.readline().strip()
        temperature = float(temp_input) if temp_input else 72.5
        pressure_bar = float(press_input) if press_input else 4.2
    except ValueError as e:
        print(f"Error parsing numeric telemetry: {e}", file=sys.stderr)
        return 1
        
    print(f"Equipment Tag : {tag}")
    print(f"Temperature   : {temperature:.1f} °C")
    print(f"Pressure      : {pressure_bar:.2f} bar")
    
    # Safety evaluation
    if temperature > 85.0:
        print("ALERT: CRITICAL BEARING OVERHEATING DETECTED!", file=sys.stderr)
        status = "CRITICAL_SHUTDOWN"
    elif temperature > 75.0:
        print("WARNING: Elevated operating temperature, monitor closely.")
        status = "ADVISORY"
    else:
        print("STATUS: Operating normally within ISO-10816 tolerances.")
        status = "NOMINAL"
        
    print(f"Operational Directive: {status}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
`;

const SAMPLE_STDIN = `PUMP-104-CRUDE
78.4
4.65`;

const PYTHON_KEYWORDS = new Set([
  "and", "as", "assert", "break", "class", "continue", "def", "del", "elif", "else",
  "except", "False", "finally", "for", "from", "global", "if", "import", "in", "is",
  "lambda", "None", "nonlocal", "not", "or", "pass", "raise", "return", "True", "try",
  "while", "with", "yield",
]);

function escapeHtml(value: string) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function highlightPython(source: string) {
  const tokenPattern = /(#[^\n]*|"""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b)/g;
  let result = "";
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = tokenPattern.exec(source)) !== null) {
    result += escapeHtml(source.slice(lastIndex, match.index));
    const token = match[0];
    const className = token.startsWith("#")
      ? "syntax-comment"
      : token.startsWith("\"") || token.startsWith("'")
        ? "syntax-string"
        : /^\d/.test(token)
          ? "syntax-number"
          : PYTHON_KEYWORDS.has(token)
            ? "syntax-keyword"
            : "syntax-name";
    result += `<span class="${className}">${escapeHtml(token)}</span>`;
    lastIndex = match.index + token.length;
  }
  return result + escapeHtml(source.slice(lastIndex));
}

export default function CodingView({ callbacks }: Props) {
  // Mode: "sandbox" (Direct interactive stdin execution) vs "agent" (AI code generation & agent testing)
  const [activeTab, setActiveTab] = useState<"sandbox" | "agent">("sandbox");

  // Agent State
  const [task, setTask] = useState(DEMO_TASK);
  const { run, isRunning, steps, result, error } = useAgent({
    onStart: callbacks.onStart,
    onStep: callbacks.onStep,
    onComplete: callbacks.onComplete,
    onError: callbacks.onError,
    setRouterInfo: callbacks.setRouterInfo,
  });

  // Interactive Sandbox State
  const [code, setCode] = useState(SAMPLE_INTERACTIVE_CODE);
  const [stdinText, setStdinText] = useState(SAMPLE_STDIN);
  const [timeoutSec, setTimeoutSec] = useState(30);
  const [timeoutOpen, setTimeoutOpen] = useState(false);
  const [isExecutingSandbox, setIsExecutingSandbox] = useState(false);
  const [sandboxExecResult, setSandboxExecResult] = useState<any>(null);
  const [sandboxError, setSandboxError] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedOutput, setCopiedOutput] = useState(false);

  // Agent results
  const agentSandboxResult = result?.tool_results?.sandbox_result;
  const agentGeneratedCode = result?.tool_results?.generated_code;
  const agentTestsPassed = agentSandboxResult?.tests_passed ?? 0;
  const agentTestsTotal = agentSandboxResult?.tests_total ?? 0;

  const handleRunAgent = () => {
    if (!task.trim() || isRunning) return;
    run(task, []);
  };

  const handleExecuteSandbox = async () => {
    if (!code.trim() || isExecutingSandbox) return;
    setIsExecutingSandbox(true);
    setSandboxError(null);
    try {
      const resp = await fetch("/api/code/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code: code,
          language: "python",
          stdin: stdinText,
          timeout: timeoutSec,
        }),
      });

      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`Server returned status ${resp.status}: ${errText}`);
      }

      const data = await resp.json();
      setSandboxExecResult(data);
    } catch (err: any) {
      setSandboxError(err.message || "Failed to execute code in Docker sandbox");
    } finally {
      setIsExecutingSandbox(false);
    }
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleCopyOutput = () => {
    if (sandboxExecResult?.stdout) {
      navigator.clipboard.writeText(sandboxExecResult.stdout);
      setCopiedOutput(true);
      setTimeout(() => setCopiedOutput(false), 2000);
    }
  };

  const handleSendAgentCodeToSandbox = () => {
    if (agentGeneratedCode) {
      setCode(agentGeneratedCode);
      setActiveTab("sandbox");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden", background: "var(--bg-primary)" }}>
      {/* Top Header */}
      <div style={{
        padding: "10px 20px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0,
        background: "var(--bg-secondary)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 8,
            background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)",
            display: "flex", alignItems: "center", justifyContent: "center"
          }}>
            <Code2 size={18} color="var(--accent-orange)" />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: "-0.01em" }}>
              Code Workbench & Docker Sandbox
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              Interactive stdin execution · Ephemeral container sandbox · Network disabled
            </div>
          </div>

          {/* Mode Switcher Tabs */}
          <div style={{
            marginLeft: 20, display: "flex", gap: 4,
            background: "var(--bg-card)", padding: "3px", borderRadius: 8,
            border: "1px solid var(--border)"
          }}>
            <button
              onClick={() => setActiveTab("sandbox")}
              className={`coding-mode-tab ${activeTab === "sandbox" ? "is-active" : ""}`}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "5px 12px", borderRadius: 6, fontSize: 12, fontWeight: 600,
                border: "none", cursor: "pointer",
                background: activeTab === "sandbox" ? "var(--accent-orange)" : "transparent",
                color: activeTab === "sandbox" ? "#000" : "var(--text-secondary)",
                transition: "all 0.15s ease",
              }}
            >
              <Zap size={13} />
              Interactive Sandbox (stdin)
            </button>
            <button
              onClick={() => setActiveTab("agent")}
              className={`coding-mode-tab ${activeTab === "agent" ? "is-active" : ""}`}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "5px 12px", borderRadius: 6, fontSize: 12, fontWeight: 600,
                border: "none", cursor: "pointer",
                background: activeTab === "agent" ? "var(--accent-orange)" : "transparent",
                color: activeTab === "agent" ? "#000" : "var(--text-secondary)",
                transition: "all 0.15s ease",
              }}
            >
              <Sparkles size={13} />
              AI Code Agent (Qwen2.5)
            </button>
          </div>
        </div>

        {/* Security & Sandbox Telemetry Badges */}
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <InfoBadge label="RUNTIME" value="Docker Engine" color="orange" icon={<Layers size={10} />} />
          <InfoBadge label="NETWORK" value="ISOLATED" color="red" icon={<WifiOff size={10} />} />
          <InfoBadge label="PERMISSIONS" value="NON-ROOT" color="green" icon={<ShieldCheck size={10} />} />
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* TAB 1: INTERACTIVE SANDBOX (DIRECT STDIN) */}
      {/* ───────────────────────────────────────────────────────────── */}
      {activeTab === "sandbox" && (
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          {/* Left Editor Column */}
          <div style={{
            flex: 1.1, display: "flex", flexDirection: "column",
            borderRight: "1px solid var(--border)", overflow: "hidden"
          }}>
            {/* Code Editor Header */}
            <div style={{
              padding: "8px 16px", background: "var(--bg-card)",
              borderBottom: "1px solid var(--border)", display: "flex",
              alignItems: "center", justifyContent: "space-between", flexShrink: 0
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Terminal size={14} color="var(--accent-orange)" />
                <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                  Python Code Editor
                </span>
                <span style={{
                  fontSize: 10, padding: "2px 6px", borderRadius: 4,
                  background: "rgba(255,255,255,0.06)", color: "var(--text-muted)",
                  fontFamily: "monospace"
                }}>
                  python 3.11-slim
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <button
                  onClick={() => {
                    setCode(SAMPLE_INTERACTIVE_CODE);
                    setStdinText(SAMPLE_STDIN);
                  }}
                  className="btn btn-ghost coding-control"
                  style={{ fontSize: 11, padding: "4px 8px", display: "flex", alignItems: "center", gap: 4 }}
                  title="Reset to sample code"
                >
                  <RotateCcw size={11} /> Reset Sample
                </button>
                <button
                  onClick={handleCopyCode}
                  className="btn btn-ghost coding-control"
                  style={{ fontSize: 11, padding: "4px 8px", display: "flex", alignItems: "center", gap: 4 }}
                  title="Copy code to clipboard"
                >
                  {copiedCode ? <Check size={11} color="var(--accent-green)" /> : <Copy size={11} />}
                  {copiedCode ? "Copied" : "Copy"}
                </button>
              </div>
            </div>

            {/* Numbered syntax-highlighted code editor */}
            <div className="code-editor-shell">
              <div className="code-editor-gutter" aria-hidden="true">
                {code.split("\n").map((_, index) => <span key={index}>{index + 1}</span>)}
              </div>
              <div className="code-editor-stage">
                <pre className="code-highlight" aria-hidden="true" dangerouslySetInnerHTML={{ __html: `${highlightPython(code)}\n` }} />
                <textarea
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  spellCheck={false}
                  className="code-editor-input"
                  placeholder="Write or paste Python code here..."
                />
              </div>
            </div>

            {/* Stdin Section */}
            <div style={{
              height: 160, borderTop: "1px solid var(--border)",
              background: "var(--bg-secondary)", display: "flex", flexDirection: "column",
              flexShrink: 0
            }}>
              <div style={{
                padding: "6px 16px", borderBottom: "1px solid var(--border)",
                display: "flex", alignItems: "center", justifyContent: "space-between"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <CornerDownLeft size={13} color="var(--accent-orange)" />
                  <span style={{ fontSize: 11, fontWeight: 700, color: "var(--accent-orange)", letterSpacing: "0.04em" }}>
                    STANDARD INPUT (STDIN)
                  </span>
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                    — Lines fed into input() / sys.stdin
                  </span>
                </div>
                <div style={{ fontSize: 10, color: "var(--text-muted)" }}>
                  {stdinText.split("\n").filter(Boolean).length} line(s)
                </div>
              </div>
              <textarea
                value={stdinText}
                onChange={(e) => setStdinText(e.target.value)}
                spellCheck={false}
                style={{
                  flex: 1, padding: "10px 16px", background: "#fff",
                  color: "var(--accent-orange)", fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12, lineHeight: 1.5, resize: "none", border: "none",
                  outline: "none"
                }}
                placeholder="Enter standard input values (one per line)..."
              />
            </div>

            {/* Bottom Controls Bar */}
            <div style={{
              padding: "10px 16px", background: "var(--bg-card)",
              borderTop: "1px solid var(--border)", display: "flex",
              alignItems: "center", justifyContent: "space-between", flexShrink: 0
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-muted)" }}>
                  <Clock size={13} />
                  <span>Timeout:</span>
                  <div className="timeout-custom role-select">
                    <button type="button" className="timeout-trigger" onClick={() => setTimeoutOpen((open) => !open)} aria-haspopup="listbox" aria-expanded={timeoutOpen}>
                      <span>{timeoutSec === 30 ? "30s (Default)" : `${timeoutSec}s`}</span>
                      <ChevronDown size={14} className={`role-select-chevron ${timeoutOpen ? "is-rotated" : ""}`} />
                    </button>
                    {timeoutOpen && (
                      <div className="timeout-menu role-select-menu" role="listbox" aria-label="Execution timeout">
                        {[10, 30, 60].map((seconds) => (
                          <button key={seconds} type="button" role="option" aria-selected={timeoutSec === seconds} className={`role-option ${timeoutSec === seconds ? "is-selected" : ""}`} onClick={() => { setTimeoutSec(seconds); setTimeoutOpen(false); }}>
                            <span className="role-option-marker" />{seconds === 30 ? "30s (Default)" : `${seconds}s`}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  Isolated Container · RAM: 256MB
                </span>
              </div>

              <button
                onClick={handleExecuteSandbox}
                disabled={isExecutingSandbox || !code.trim()}
                className="btn btn-primary"
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "8px 20px", fontSize: 13, fontWeight: 600,
                  background: "linear-gradient(135deg, #f59e0b, #d97706)",
                  border: "none", color: "#000"
                }}
              >
                {isExecutingSandbox ? (
                  <>
                    <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#000", animation: "pulse-dot 1s infinite" }} />
                    Executing in Docker…
                  </>
                ) : (
                  <>
                    <Play size={14} fill="#000" />
                    Run in Docker Sandbox
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Right Console Output Column */}
          <div style={{
            flex: 0.9, display: "flex", flexDirection: "column",
            background: "#f8fafc", overflowY: "auto", padding: "16px 20px"
          }}>
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid var(--border)"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Terminal size={15} color="var(--accent-orange)" />
                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                  Execution Console
                </span>
              </div>
              {sandboxExecResult && (
                <button
                  onClick={handleCopyOutput}
                  className="btn btn-ghost"
                  style={{ fontSize: 11, padding: "3px 8px", display: "flex", alignItems: "center", gap: 4 }}
                >
                  {copiedOutput ? <Check size={11} color="var(--accent-green)" /> : <Copy size={11} />}
                  {copiedOutput ? "Copied" : "Copy Output"}
                </button>
              )}
            </div>

            {/* Idle State */}
            {!sandboxExecResult && !isExecutingSandbox && !sandboxError && (
              <div style={{
                textAlign: "center", marginTop: 80, padding: "20px",
                color: "var(--text-muted)", display: "flex", flexDirection: "column",
                alignItems: "center", gap: 12
              }}>
                <div style={{
                  width: 54, height: 54, borderRadius: "50%",
                  background: "#fff", border: "1px solid var(--border)",
                  display: "flex", alignItems: "center", justifyContent: "center"
                }}>
                  <Play size={24} color="var(--accent-orange)" style={{ marginLeft: 3 }} />
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
                  Ready to Execute
                </div>
                <div style={{ fontSize: 12, maxWidth: 320, lineHeight: 1.6 }}>
                  Click <b>Run in Docker Sandbox</b> to execute your Python script with the supplied stdin inputs in an air-gapped container.
                </div>
              </div>
            )}

            {/* Error Message */}
            {sandboxError && (
              <div style={{
                marginBottom: 16, padding: "12px 14px", borderRadius: 8,
                background: "rgba(255,71,87,0.08)", border: "1px solid rgba(255,71,87,0.3)",
                color: "var(--accent-red)", fontSize: 13, display: "flex", gap: 10
              }}>
                <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <div style={{ fontWeight: 600 }}>Execution Error</div>
                  <div style={{ fontSize: 12, marginTop: 2 }}>{sandboxError}</div>
                </div>
              </div>
            )}

            {/* Live Result Details */}
            {sandboxExecResult && (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                {/* Status Bar */}
                <div style={{
                  padding: "10px 14px", borderRadius: 8,
                  background: sandboxExecResult.status === "success" && sandboxExecResult.exit_code === 0
                    ? "rgba(0,214,143,0.08)"
                    : "rgba(255,71,87,0.08)",
                  border: `1px solid ${sandboxExecResult.status === "success" && sandboxExecResult.exit_code === 0
                    ? "rgba(0,214,143,0.25)"
                    : "rgba(255,71,87,0.25)"}`,
                  display: "flex", alignItems: "center", justifyContent: "space-between"
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    {sandboxExecResult.exit_code === 0 ? (
                      <CheckCircle size={18} color="var(--accent-green)" />
                    ) : (
                      <AlertTriangle size={18} color="var(--accent-red)" />
                    )}
                    <div>
                      <div style={{
                        fontSize: 13, fontWeight: 700,
                        color: sandboxExecResult.exit_code === 0 ? "var(--accent-green)" : "var(--accent-red)"
                      }}>
                        {sandboxExecResult.exit_code === 0 ? "EXIT CODE 0 (SUCCESS)" : `EXIT CODE ${sandboxExecResult.exit_code} (FAILED)`}
                      </div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 1 }}>
                        Execution time: {sandboxExecResult.execution_time}s · Sandbox: Docker
                      </div>
                    </div>
                  </div>

                  <div style={{
                    fontSize: 11, fontWeight: 700, padding: "3px 8px", borderRadius: 4,
                    background: "#fff", color: "var(--text-secondary)"
                  }}>
                    {sandboxExecResult.network_disabled ? "Air-Gapped" : "Online"}
                  </div>
                </div>

                {/* STDOUT Block */}
                <div>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", marginBottom: 6, letterSpacing: "0.05em" }}>
                    STANDARD OUTPUT (STDOUT)
                  </div>
                  <div style={{
                    background: "#fff", border: "1px solid var(--border)",
                    borderRadius: 8, padding: "12px 14px", fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 12, lineHeight: 1.6, color: "#166534", whiteSpace: "pre-wrap",
                    wordBreak: "break-word", minHeight: 80
                  }}>
                    {sandboxExecResult.stdout || <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>[No output generated on stdout]</span>}
                  </div>
                </div>

                {/* STDERR Block */}
                {sandboxExecResult.stderr && (
                  <div>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "var(--accent-red)", marginBottom: 6, letterSpacing: "0.05em" }}>
                      STANDARD ERROR (STDERR)
                    </div>
                    <div style={{
                      background: "rgba(255,71,87,0.05)", border: "1px solid rgba(255,71,87,0.25)",
                      borderRadius: 8, padding: "12px 14px", fontFamily: "'Fira Code', monospace",
                      fontSize: 12, lineHeight: 1.6, color: "#ff7b72", whiteSpace: "pre-wrap",
                      wordBreak: "break-word"
                    }}>
                      {sandboxExecResult.stderr}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ───────────────────────────────────────────────────────────── */}
      {/* TAB 2: AI CODE AGENT (GENERATE + TEST) */}
      {/* ───────────────────────────────────────────────────────────── */}
      {activeTab === "agent" && (
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          {/* Left: Input + steps */}
          <div style={{
            flex: 1, overflowY: "auto", padding: "16px 20px",
            borderRight: "1px solid var(--border)"
          }}>
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
                TASK SPECIFICATION
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
              onClick={handleRunAgent}
              disabled={isRunning || !task.trim()}
              className="btn btn-primary"
              style={{ width: "100%", justifyContent: "center", padding: "12px", marginBottom: 20 }}
            >
              {isRunning ? (
                <>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "white", animation: "pulse-dot 1s infinite" }} />
                  Synthesizing & Executing Tests…
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

          {/* Right: Generated Code + test results */}
          <div style={{ width: 480, overflowY: "auto", padding: "16px 20px" }}>
            {!result && !isRunning && (
              <div style={{ textAlign: "center", marginTop: 60, color: "var(--text-muted)" }}>
                <Terminal size={32} style={{ margin: "0 auto 12px" }} />
                <div style={{ fontSize: 13 }}>Generated code will appear here</div>
                <div style={{ fontSize: 11, marginTop: 6 }}>
                  Synthesized via Qwen2.5-Coder and verified in Docker
                </div>
              </div>
            )}

            {agentGeneratedCode && (
              <div style={{ marginBottom: 16 }}>
                <div style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  marginBottom: 8
                }}>
                  <div style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 600, letterSpacing: "0.06em" }}>
                    GENERATED CODE
                  </div>
                  <button
                    onClick={handleSendAgentCodeToSandbox}
                    className="btn btn-ghost"
                    style={{
                      fontSize: 11, padding: "3px 8px", display: "flex", alignItems: "center", gap: 4,
                      color: "var(--accent-orange)"
                    }}
                  >
                    Open in Interactive Sandbox <ArrowRight size={11} />
                  </button>
                </div>
                <div className="code-block" style={{ fontSize: 12, maxHeight: 300, overflowY: "auto" }}>
                  {agentGeneratedCode}
                </div>
              </div>
            )}

            {agentSandboxResult && (
              <div style={{ marginBottom: 16 }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 8, marginBottom: 10,
                  padding: "10px 14px", borderRadius: 8,
                  background: agentSandboxResult.success ? "rgba(0,214,143,0.06)" : "rgba(255,71,87,0.06)",
                  border: `1px solid ${agentSandboxResult.success ? "rgba(0,214,143,0.2)" : "rgba(255,71,87,0.2)"}`
                }}>
                  {agentSandboxResult.success
                    ? <CheckCircle size={16} color="var(--accent-green)" />
                    : <AlertTriangle size={16} color="var(--accent-red)" />
                  }
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: agentSandboxResult.success ? "var(--accent-green)" : "var(--accent-red)" }}>
                      Tests {agentTestsTotal > 0 ? `${agentTestsPassed}/${agentTestsTotal} PASSED` : agentSandboxResult.success ? "PASSED" : "FAILED"}
                    </div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                      Docker · Network: NONE · Isolated Container
                    </div>
                  </div>
                </div>

                {agentSandboxResult.stdout && (
                  <div>
                    <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4, fontWeight: 600 }}>STDOUT</div>
                    <div className="code-block" style={{ fontSize: 11, maxHeight: 150, overflowY: "auto" }}>
                      {agentSandboxResult.stdout.slice(0, 1000)}
                    </div>
                  </div>
                )}

                {agentSandboxResult.stderr && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 11, color: "var(--accent-red)", marginBottom: 4, fontWeight: 600 }}>STDERR</div>
                    <div className="code-block" style={{ fontSize: 11, borderColor: "rgba(255,71,87,0.3)", color: "var(--accent-red)" }}>
                      {agentSandboxResult.stderr.slice(0, 500)}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
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
