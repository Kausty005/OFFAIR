"use client";

import { useState, useRef, useEffect } from "react";
import { AgentCallbacks } from "@/types";
import { useAgent, uploadFiles } from "@/hooks/useAgent";
import { Send, Paperclip, X, Cloud, Search, FileText, FileCheck, BookOpen, ShieldCheck, Plus, Brain, Mic, ArrowUp } from "lucide-react";

interface Props {
  callbacks: AgentCallbacks;
}

interface Message {
  role: "user" | "ai";
  content: string;
  files?: string[];
  outputFiles?: string[]; // generated files (docx, py, etc.) from agent
}

export default function WorkbenchView({ callbacks }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState<{ name: string; path: string }[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { run, isRunning, steps, result, error } = useAgent({
    onStart: callbacks.onStart,
    onStep: callbacks.onStep,
    onComplete: (r) => {
      callbacks.onComplete(r);
      setMessages(prev => [...prev, {
        role: "ai",
        content: r.final_output || "Task completed.",
        outputFiles: r.output_files || [],
      }]);
    },
    onError: (e) => {
      callbacks.onError(e);
      setMessages(prev => [...prev, {
        role: "ai",
        content: `⚠️ Error: ${e}`,
      }]);
    },
    setRouterInfo: callbacks.setRouterInfo,
  });

  // Render markdown-like content: code blocks, bold, etc.
  const renderContent = (content: string) => {
    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, i) => {
      const codeMatch = part.match(/^```(\w*)\n?([\s\S]*?)```$/);
      if (codeMatch) {
        const lang = codeMatch[1] || "";
        const code = codeMatch[2];
        return (
          <div key={i} style={{
            backgroundColor: "#0d1117",
            border: "1px solid var(--border)",
            borderRadius: "8px",
            padding: "16px",
            margin: "8px 0",
            overflowX: "auto",
          }}>
            {lang && <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>{lang}</div>}
            <pre style={{ margin: 0, fontFamily: "'Fira Code', 'Cascadia Code', monospace", fontSize: "13px", color: "#e6edf3", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{code}</pre>
          </div>
        );
      }
      // Render bold **text**
      const boldParts = part.split(/(\*\*[^*]+\*\*)/g);
      return (
        <span key={i}>
          {boldParts.map((bp, j) => {
            if (bp.startsWith("**") && bp.endsWith("**")) {
              return <strong key={j}>{bp.slice(2, -2)}</strong>;
            }
            return <span key={j} style={{ whiteSpace: "pre-wrap" }}>{bp}</span>;
          })}
        </span>
      );
    });
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isRunning) return;

    const filePaths = uploadedFiles.map(f => f.path);
    setMessages(prev => [...prev, {
      role: "user",
      content: text,
      files: uploadedFiles.map(f => f.name),
    }]);
    setInput("");
    setUploadedFiles([]);

    await run(text, filePaths);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const paths = await uploadFiles(files);
    setUploadedFiles(prev => [...prev, ...files.map((f, i) => ({
      name: f.name,
      path: paths[i] || "",
    }))]);
    e.target.value = "";
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", position: "relative" }}>
      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "40px 10% 150px", display: "flex", flexDirection: "column", gap: 24 }}>
        {messages.length === 0 && (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
            <Cloud size={48} color="var(--text-muted)" style={{ marginBottom: "24px" }} />
            <h1 style={{ fontSize: "28px", fontWeight: 400, color: "var(--text-primary)", marginBottom: "40px" }}>
              How should I help you?
            </h1>

            <div style={{ display: "flex", gap: "16px", flexWrap: "wrap", justifyContent: "center", maxWidth: "800px" }}>
              <ActionCard icon={<FileText size={20} color="#4d9de0" />} title="Analyse document" onClick={() => setInput("Analyse document")} />
              <ActionCard icon={<FileCheck size={20} color="#ff6b35" />} title="Generate inspection report" onClick={() => setInput("Generate inspection report")} />
              <ActionCard icon={<BookOpen size={20} color="#00d68f" />} title="Query knowledge base" onClick={() => setInput("Query knowledge base")} />
              <ActionCard icon={<ShieldCheck size={20} color="#a55eea" />} title="Verify air-gap security" onClick={() => setInput("Verify air-gap security")} />
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className="fade-in" style={{ 
            alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
            maxWidth: "85%",
            width: msg.role === "user" ? "auto" : "100%"
          }}>
            {msg.role === "user" ? (
              <div style={{ 
                backgroundColor: "var(--bg-input)", 
                padding: "12px 16px", 
                borderRadius: "12px", 
                border: "1px solid var(--border)",
              }}>
                {msg.files && msg.files.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
                    {msg.files.map((f, fi) => (
                      <span key={fi} className="source-chip">📁 {f}</span>
                    ))}
                  </div>
                )}
                {msg.content}
              </div>
            ) : (
              <div className="ai-output" style={{ color: "var(--text-primary)", lineHeight: 1.7, fontSize: "14px" }}>
                {renderContent(msg.content)}
                {msg.outputFiles && msg.outputFiles.length > 0 && (
                  <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: 4 }}>📎 Generated Files</div>
                    {msg.outputFiles.map((fpath, fi) => {
                      const fname = fpath.split(/[\\/]/).pop() || fpath;
                      return (
                        <a
                          key={fi}
                          href={`/api/download?path=${encodeURIComponent(fpath)}`}
                          download={fname}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 8,
                            backgroundColor: "rgba(0,214,143,0.1)",
                            border: "1px solid rgba(0,214,143,0.3)",
                            borderRadius: "8px",
                            padding: "8px 16px",
                            color: "var(--accent-green)",
                            fontSize: "13px",
                            textDecoration: "none",
                            fontWeight: 500,
                            width: "fit-content",
                            cursor: "pointer",
                          }}
                        >
                          ⬇️ {fname}
                        </a>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {isRunning && (
          <div className="fade-in" style={{ alignSelf: "flex-start" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "var(--text-muted)", fontSize: "14px" }}>
              <div className="activity-dot bg-orange-500 pulse" style={{ width: 8, height: 8, backgroundColor: "var(--accent-orange)", borderRadius: "50%" }} />
              <span>Agent is thinking...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Floating Input Area */}
      <div style={{
        position: "absolute",
        bottom: "24px",
        left: "50%",
        transform: "translateX(-50%)",
        width: "90%",
        maxWidth: "800px",
        backgroundColor: "var(--bg-input)",
        borderRadius: "12px",
        border: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 10px 30px rgba(0,0,0,0.4)",
        overflow: "visible" // To show the dropdowns if any
      }}>
        {/* Uploaded files chips inside input box */}
        {uploadedFiles.length > 0 && (
          <div style={{ padding: "12px 16px 0", display: "flex", flexWrap: "wrap", gap: 6 }}>
            {uploadedFiles.map((f, i) => (
              <span key={i} className="source-chip" style={{ cursor: "default" }}>
                {f.name}
                <X size={10} style={{ cursor: "pointer" }} onClick={() =>
                  setUploadedFiles(prev => prev.filter((_, j) => j !== i))
                } />
              </span>
            ))}
          </div>
        )}

        <div style={{ position: "relative" }}>
          <textarea
            ref={textareaRef}
            className="input"
            placeholder="Ask anything... or upload a file and describe your task"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            disabled={isRunning}
            style={{
              width: "100%",
              minHeight: "100px",
              maxHeight: "300px",
              backgroundColor: "transparent",
              border: "none",
              color: "var(--text-primary)",
              padding: "16px",
              paddingBottom: "48px",
              fontSize: "15px",
              resize: "none",
              outline: "none",
              boxShadow: "none"
            }}
          />
          
          <input ref={fileRef} type="file" multiple style={{ display: "none" }} onChange={handleFileUpload} />

          {/* Bottom Actions */}
          <div style={{
            position: "absolute",
            bottom: "12px",
            left: "16px",
            right: "12px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <button 
                onClick={() => fileRef.current?.click()}
                disabled={isRunning}
                style={{
                  background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center"
                }}
              >
                <Paperclip size={18} />
              </button>
              <div 
                onClick={() => fileRef.current?.click()}
                style={{ 
                  display: "flex", alignItems: "center", gap: "4px", fontSize: "12px", 
                  color: "var(--accent-orange)", cursor: "pointer",
                  padding: "2px 8px", borderRadius: "6px",
                  background: "rgba(255,107,53,0.1)",
                  border: "1px solid rgba(255,107,53,0.2)"
                }}
              >
                <Plus size={13} /> Add document
              </div>
            </div>
            
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "4px", cursor: "pointer" }}>
                Local AI <span style={{ fontSize: "10px" }}>▼</span>
              </div>
              <Mic size={18} color="var(--text-muted)" style={{ cursor: "pointer" }} />
              <button 
                onClick={handleSend}
                disabled={isRunning || !input.trim()}
                style={{
                  width: "28px", height: "28px", borderRadius: "50%",
                  backgroundColor: (input.trim() && !isRunning) ? "var(--text-primary)" : "var(--border)",
                  color: "var(--bg-primary)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  border: "none", cursor: (input.trim() && !isRunning) ? "pointer" : "not-allowed",
                  transition: "background-color 0.2s"
                }}
              >
                <ArrowUp size={16} strokeWidth={3} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ActionCard({ icon, title, onClick }: { icon: React.ReactNode, title: string, onClick?: () => void }) {
  return (
    <div 
      onClick={onClick}
      style={{
        width: "180px",
        height: "120px",
        backgroundColor: "var(--bg-primary)",
        border: "1px solid var(--border)",
        borderRadius: "12px",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        cursor: "pointer",
        transition: "border-color 0.2s"
      }} 
      onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--border-accent)")}
      onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}
    >
      <div>{icon}</div>
      <div style={{ fontSize: "13px", color: "var(--text-primary)", lineHeight: 1.4 }}>{title}</div>
    </div>
  );
}
