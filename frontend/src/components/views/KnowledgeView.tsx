"use client";

import { useState, useEffect, useRef } from "react";
import { BookOpen, Upload, FileText, RefreshCw, Search, Sparkles, Database } from "lucide-react";
import { SessionUser } from "@/components/LoginPage";

interface KBDoc {
  name: string;
  size: number;
  path: string;
  ext?: string;
  uploaded_by?: string;
  uploaded_at?: string;
  allowed_roles?: string[];
  min_role_level?: number;
}

interface SearchResult {
  id: string;
  text: string;
  document: string;
  page?: string | number;
  score: number;
}

interface RAGAnswer {
  answer: string;
  sources: Array<{ index: number; document: string; page?: string | number; score: number; text: string }>;
  rag_used: boolean;
  warning?: string;
  model?: string;
}

export default function KnowledgeView({ session }: { session: SessionUser }) {
  const [docs, setDocs] = useState<KBDoc[]>([]);
  const [chunkCount, setChunkCount] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [uploadRoleAccess, setUploadRoleAccess] = useState<"all" | "eng" | "admin">("all");
  
  // Search & Q&A state
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [ragAnswer, setRagAnswer] = useState<RAGAnswer | null>(null);
  const [activeTab, setActiveTab] = useState<"search" | "ask">("search");
  
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch("http://localhost:8000/api/knowledge");
      if (r.ok) {
        const data = await r.json();
        setDocs(data.documents || []);
        if (data.vector_store) {
          setChunkCount(data.vector_store.count || 0);
        }
      }
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);

    let targetRoles = "admin,engineer,employee";
    if (uploadRoleAccess === "admin") {
      targetRoles = "admin";
    } else if (uploadRoleAccess === "eng") {
      targetRoles = "admin,engineer";
    }

    for (const f of files) {
      const form = new FormData();
      form.append("file", f);
      form.append("auto_ingest", "true");
      form.append("session_token", session.token);
      form.append("allowed_roles", targetRoles);
      form.append("classification", "internal");
      await fetch("http://localhost:8000/api/knowledge/upload", { method: "POST", body: form });
    }
    setUploading(false);
    load();
    e.target.value = "";
  };

  const handleIngestAll = async () => {
    setIngesting(true);
    try {
      const form = new FormData();
      form.append("session_token", session.token);
      form.append("allowed_roles", session.role);
      form.append("classification", "internal");
      await fetch("http://localhost:8000/api/knowledge/ingest", { method: "POST", body: form });
      setTimeout(() => {
        load();
        setIngesting(false);
      }, 2500);
    } catch {
      setIngesting(false);
    }
  };

  const handleSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    setSearchResults(null);
    setRagAnswer(null);

    try {
      if (activeTab === "search") {
        const res = await fetch("http://localhost:8000/api/knowledge/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, top_k: 4, session_token: session.token }),
        });
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data.results || []);
        }
      } else {
        const res = await fetch("http://localhost:8000/api/knowledge/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, top_k: 4, session_token: session.token }),
        });
        if (res.ok) {
          const data = await res.json();
          setRagAnswer(data);
        }
      }
    } catch (e) {
      console.error(e);
    }
    setSearching(false);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Top Header */}
      <div style={{
        padding: "12px 20px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <BookOpen size={18} color="var(--accent-green)" />
          <div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>Local RAG Knowledge Base</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              100% Air-Gapped Semantic Search & Ingestion · {docs.length} Documents · {chunkCount} Vectors Indexed
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button onClick={load} className="btn btn-ghost" style={{ padding: "6px 12px", fontSize: 12 }}>
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <button
            onClick={handleIngestAll}
            disabled={ingesting || session.role !== "admin"}
            className="btn btn-ghost"
            style={{ padding: "6px 12px", fontSize: 12, border: "1px solid var(--border)" }}
          >
            <Database size={12} />
            {ingesting ? "Indexing..." : session.role === "admin" ? "Index All Chunks" : "Admin Indexing Only"}
          </button>
          <div style={{ display: "flex", alignItems: "center", gap: 4, background: "var(--bg-secondary)", borderRadius: 6, padding: "2px 8px", border: "1px solid var(--border)" }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Target:</span>
            <select
              value={uploadRoleAccess}
              onChange={(e) => setUploadRoleAccess(e.target.value as any)}
              style={{
                background: "transparent",
                border: "none",
                fontSize: 11,
                color: "var(--text-primary)",
                cursor: "pointer",
                outline: "none",
              }}
            >
              <option value="all" style={{ background: "var(--bg-primary)" }}>Emp+ (All Users)</option>
              <option value="eng" style={{ background: "var(--bg-primary)" }}>Eng+ (Engineers & Admin)</option>
              <option value="admin" style={{ background: "var(--bg-primary)" }}>Admin Only</option>
            </select>
          </div>
          <button
            onClick={() => fileRef.current?.click()}
            className="btn btn-primary"
            style={{ fontSize: 12 }}
          >
            <Upload size={12} />
            {uploading ? "Uploading…" : "Add Document"}
          </button>
          <input ref={fileRef} type="file" multiple accept=".pdf,.txt,.docx,.md,.csv,.json" style={{ display: "none" }}
            onChange={handleUpload} />
        </div>
      </div>

      {/* Main Body */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
        
        {/* Quick Stats Banner */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 12,
          marginBottom: 20
        }}>
          <div className="card" style={{ padding: "12px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Total Documents</div>
            <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4, color: "var(--text-primary)" }}>
              {docs.length}
            </div>
          </div>
          <div className="card" style={{ padding: "12px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Indexed Vector Chunks</div>
            <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4, color: "var(--accent-green)" }}>
              {chunkCount}
            </div>
          </div>
          <div className="card" style={{ padding: "12px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Embedding Model</div>
            <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4, color: "var(--accent-blue)" }}>
              nomic-embed-text
            </div>
          </div>
          <div className="card" style={{ padding: "12px 16px" }}>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Air-Gap Status</div>
            <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4, color: "var(--accent-green)" }}>
              🔒 100% Local / Zero Cloud
            </div>
          </div>
        </div>

        {/* Interactive RAG Search / Query Section */}
        <div className="card" style={{ padding: "16px", marginBottom: 20 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Search size={16} color="var(--accent-blue)" />
              <span style={{ fontSize: 13, fontWeight: 600 }}>Test RAG Semantic Retrieval & Grounding</span>
            </div>
            <div style={{ display: "flex", background: "var(--bg-secondary)", borderRadius: 6, padding: 2 }}>
              <button
                onClick={() => setActiveTab("search")}
                style={{
                  padding: "4px 10px", fontSize: 11, borderRadius: 4, border: "none", cursor: "pointer",
                  background: activeTab === "search" ? "var(--bg-card)" : "transparent",
                  color: activeTab === "search" ? "var(--text-primary)" : "var(--text-muted)",
                  fontWeight: activeTab === "search" ? 600 : 400
                }}
              >
                Semantic Search
              </button>
              <button
                onClick={() => setActiveTab("ask")}
                style={{
                  padding: "4px 10px", fontSize: 11, borderRadius: 4, border: "none", cursor: "pointer",
                  background: activeTab === "ask" ? "var(--bg-card)" : "transparent",
                  color: activeTab === "ask" ? "var(--text-primary)" : "var(--text-muted)",
                  fontWeight: activeTab === "ask" ? 600 : 400
                }}
              >
                Grounded Q&A (LLM)
              </button>
            </div>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="text"
              placeholder={activeTab === "search" ? "e.g., 'What is the acceptable vibration limit?' or 'Bearing temperature threshold'..." : "Ask a question to answer from the knowledge base..."}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              style={{
                flex: 1,
                padding: "8px 12px",
                fontSize: 13,
                borderRadius: 6,
                background: "var(--bg-secondary)",
                border: "1px solid var(--border)",
                color: "var(--text-primary)"
              }}
            />
            <button
              onClick={handleSearch}
              disabled={searching || !query.trim()}
              className="btn btn-primary"
              style={{ fontSize: 12 }}
            >
              {searching ? (
                <span>Searching...</span>
              ) : activeTab === "search" ? (
                <>
                  <Search size={12} /> Search
                </>
              ) : (
                <>
                  <Sparkles size={12} /> Ask RAG
                </>
              )}
            </button>
          </div>

          {/* Search Results Display */}
          {searchResults && (
            <div style={{ marginTop: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>
                Found {searchResults.length} relevant chunks:
              </div>
              {searchResults.length === 0 ? (
                <div style={{ fontSize: 12, color: "var(--text-muted)", fontStyle: "italic" }}>
                  No matching chunks found. Try uploading relevant documents or adjusting query terms.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {searchResults.map((r, i) => (
                    <div
                      key={r.id || i}
                      style={{
                        padding: "10px 12px",
                        background: "var(--bg-secondary)",
                        borderRadius: 6,
                        border: "1px solid var(--border)"
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: "2px 6px", borderRadius: 4,
                            background: "rgba(56,189,248,0.1)", color: "var(--accent-blue)"
                          }}>
                            #{i + 1}
                          </span>
                          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
                            {r.document}
                          </span>
                          {r.page && (
                            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                              (Page {r.page})
                            </span>
                          )}
                        </div>
                        <span style={{
                          fontSize: 10, padding: "2px 6px", borderRadius: 4,
                          background: "rgba(0,214,143,0.1)", color: "var(--accent-green)", fontWeight: 600
                        }}>
                          Score: {r.score ? (r.score * 100).toFixed(1) + "%" : "N/A"}
                        </span>
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                        {r.text}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Grounded RAG Answer Display */}
          {ragAnswer && (
            <div style={{ marginTop: 14 }}>
              <div style={{
                padding: "14px",
                background: "rgba(0,214,143,0.04)",
                border: "1px solid rgba(0,214,143,0.2)",
                borderRadius: 8
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
                  <Sparkles size={14} color="var(--accent-green)" />
                  <span style={{ fontSize: 12, fontWeight: 700, color: "var(--accent-green)" }}>
                    Grounded AI Answer (Local Model: {ragAnswer.model || "Local"})
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "var(--text-primary)", lineHeight: 1.6, whiteSpace: "pre-wrap", marginBottom: 12 }}>
                  {ragAnswer.answer}
                </div>
                {ragAnswer.sources && ragAnswer.sources.length > 0 && (
                  <div style={{ borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>
                      CITED SOURCES:
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {ragAnswer.sources.map((s) => (
                        <span
                          key={s.index}
                          style={{
                            fontSize: 11, padding: "2px 8px", borderRadius: 4,
                            background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-secondary)"
                          }}
                        >
                          [Source {s.index}: {s.document}{s.page ? ` - Page ${s.page}` : ""}]
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {ragAnswer.warning && (
                  <div style={{ fontSize: 11, color: "var(--accent-yellow)", marginTop: 6 }}>
                    ⚠️ {ragAnswer.warning}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Uploaded Documents List */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 10 }}>
            Managed Knowledge Files ({docs.length})
          </div>

          {docs.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 20px" }} className="card">
              <BookOpen size={32} color="var(--text-muted)" style={{ margin: "0 auto 12px" }} />
              <div style={{ fontSize: 14, color: "var(--text-secondary)", marginBottom: 6 }}>
                Knowledge base has no documents
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16 }}>
                Add maintenance SOPs, safety manuals, and inspection guidelines from `demo_data/`
              </div>
              <button onClick={() => fileRef.current?.click()} className="btn btn-primary">
                <Upload size={14} />
                Upload Documents
              </button>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
              {docs.map((doc, i) => {
                const isAdminOnly = doc.allowed_roles && doc.allowed_roles.length === 1 && doc.allowed_roles[0] === "admin";
                const isEngPlus = doc.allowed_roles && doc.allowed_roles.includes("engineer") && !doc.allowed_roles.includes("employee");
                return (
                  <div key={i} className="card card-hover" style={{ padding: "14px 16px" }}>
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                      <FileText size={20} color="var(--accent-blue)" style={{ flexShrink: 0, marginTop: 2 }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{
                          fontSize: 13, fontWeight: 600, color: "var(--text-primary)",
                          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap"
                        }}>
                          {doc.name}
                        </div>
                        <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 3, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                          <span>{formatSize(doc.size)}</span>
                          <span>·</span>
                          <span style={{ color: "var(--text-secondary)" }}>
                            👤 @{doc.uploaded_by || "admin"}
                          </span>
                        </div>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                        <span style={{
                          fontSize: 10, padding: "2px 6px", borderRadius: 4,
                          background: isAdminOnly
                            ? "rgba(239,68,68,0.12)"
                            : isEngPlus
                            ? "rgba(56,189,248,0.12)"
                            : "rgba(0,214,143,0.08)",
                          color: isAdminOnly
                            ? "var(--accent-red, #f87171)"
                            : isEngPlus
                            ? "var(--accent-blue, #38bdf8)"
                            : "var(--accent-green)",
                          border: `1px solid ${
                            isAdminOnly
                              ? "rgba(239,68,68,0.3)"
                              : isEngPlus
                              ? "rgba(56,189,248,0.3)"
                              : "rgba(0,214,143,0.2)"
                          }`,
                          fontWeight: 600,
                        }}>
                          {isAdminOnly ? "Admin Only" : isEngPlus ? "Engineer+" : "Emp+ (All)"}
                        </span>
                        <span style={{
                          fontSize: 9, padding: "1px 5px", borderRadius: 3,
                          background: "var(--bg-secondary)", color: "var(--text-muted)",
                          border: "1px solid var(--border)",
                        }}>
                          {(doc.ext || doc.name.split(".").pop() || "DOC").toUpperCase()}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* RAG Info Box */}
        <div style={{
          padding: "16px", borderRadius: 8,
          background: "var(--bg-card)", border: "1px solid var(--border)"
        }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginBottom: 8 }}>
            OffAir RAG Technical Parameters
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {[
              ["Vector Store", "Local Pure-Python JSON / ChromaDB"],
              ["Embeddings", "Ollama nomic-embed-text (Local)"],
              ["Chunking Strategy", "512 tokens / 50 overlap"],
              ["Retrieval Scoring", "Cosine Similarity (threshold = 0.25)"],
              ["Grounding Policy", "Strict Contextual Citations ([Source N])"],
              ["Air-Gap Guarantee", "0 External Calls / 0 Cloud APIs"],
            ].map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                <span style={{ color: "var(--text-muted)" }}>{k}</span>
                <span style={{ color: "var(--text-secondary)" }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
