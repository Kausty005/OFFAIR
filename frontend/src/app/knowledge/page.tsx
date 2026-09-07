"use client";

import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import {
  BookOpen, Upload, Database, FileText, Loader2,
  Lock, CheckCircle2, RefreshCw, Search, X,
  FileImage, FileCode, FileJson, Sparkles, Trash2,
  AlertTriangle, ChevronDown, ChevronUp, Zap
} from "lucide-react";
import { useEffect, useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { knowledgeService, KnowledgeDocument } from "@/lib/services/knowledge";
import { cn } from "@/lib/utils";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const ACCEPTED_EXTS = ".pdf,.docx,.txt,.md,.csv,.jpg,.jpeg,.png,.webp";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function ExtIcon({ ext }: { ext: string }) {
  const imgExts = ["jpg", "jpeg", "png", "webp", "bmp"];
  const codeExts = ["py", "js", "ts", "sh", "yaml", "yml"];
  const jsonExts = ["json", "csv"];

  if (imgExts.includes(ext))  return <FileImage className="w-4 h-4 text-purple-400" />;
  if (codeExts.includes(ext)) return <FileCode  className="w-4 h-4 text-yellow-400" />;
  if (jsonExts.includes(ext)) return <FileJson  className="w-4 h-4 text-cyan-400"   />;
  if (ext === "pdf")          return <FileText  className="w-4 h-4 text-red-400"    />;
  if (ext === "docx")         return <FileText  className="w-4 h-4 text-blue-400"   />;
  return <BookOpen className="w-4 h-4 text-gray-400" />;
}

function ExtBadge({ ext }: { ext: string }) {
  const colorMap: Record<string, string> = {
    pdf:  "text-red-400   bg-red-400/10   border-red-400/20",
    docx: "text-blue-400  bg-blue-400/10  border-blue-400/20",
    txt:  "text-gray-400  bg-white/[0.03] border-white/[0.05]",
    md:   "text-teal-400  bg-teal-400/10  border-teal-400/20",
    csv:  "text-cyan-400  bg-cyan-400/10  border-cyan-400/20",
    json: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
    jpg:  "text-purple-400 bg-purple-400/10 border-purple-400/20",
    jpeg: "text-purple-400 bg-purple-400/10 border-purple-400/20",
    png:  "text-purple-400 bg-purple-400/10 border-purple-400/20",
    webp: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  };
  return (
    <span className={cn(
      "text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-md border",
      colorMap[ext] ?? "text-gray-400 bg-white/[0.02] border-white/[0.04]"
    )}>
      {ext}
    </span>
  );
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface UploadItem {
  id: string;
  file: File;
  progress: number;
  status: "uploading" | "ingesting" | "done" | "error";
  error?: string;
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

// ─── Permission badge ─────────────────────────────────────────────────────────

function PermissionBadge({ doc }: { doc: KnowledgeDocument }) {
  const isRestricted =
    doc.permission === "RESTRICTED" || doc.classification === "RESTRICTED" || doc.classification === "CONFIDENTIAL";

  if (isRestricted) {
    return (
      <div className="flex items-center gap-1.5 text-[10px] font-bold text-red-400 bg-red-400/10 border border-red-400/20 px-2.5 py-1 rounded-md uppercase tracking-wider">
        <Lock className="w-3 h-3" />
        Restricted
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 text-[10px] font-bold text-green-400 bg-green-400/10 border border-green-400/20 px-2.5 py-1 rounded-md uppercase tracking-wider">
      <CheckCircle2 className="w-3 h-3" />
      Authorized
    </div>
  );
}

// ─── Score Bar ────────────────────────────────────────────────────────────────

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    pct >= 70 ? "bg-green-500" :
    pct >= 45 ? "bg-yellow-500" :
    "bg-orange-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-white/[0.06] overflow-hidden">
        <div className={cn("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className={cn(
        "text-[11px] font-bold tabular-nums",
        pct >= 70 ? "text-green-400" : pct >= 45 ? "text-yellow-400" : "text-orange-400"
      )}>
        {pct}%
      </span>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function KnowledgePage() {
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [stats, setStats] = useState({ total_documents: 0, vector_store: { count: 0 } });
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [uploadQueue, setUploadQueue] = useState<UploadItem[]>([]);
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  // ── RAG panel state ───────────────────────────────────────────────────────
  const [ragQuery, setRagQuery] = useState("");
  const [ragTab, setRagTab] = useState<"search" | "ask">("search");
  const [ragSearching, setRagSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [ragAnswer, setRagAnswer] = useState<RAGAnswer | null>(null);
  const [ragPanelOpen, setRagPanelOpen] = useState(true);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const ragInputRef  = useRef<HTMLInputElement>(null);

  // ── Fetch ─────────────────────────────────────────────────────────────────
  const fetchKnowledge = useCallback(async () => {
    setLoading(true);
    try {
      const data = await knowledgeService.listKnowledge();
      setDocs(data.documents ?? []);
      setStats({
        total_documents: data.total_documents ?? 0,
        vector_store: (data.vector_store as { count: number }) ?? { count: 0 },
      });
    } catch {
      // Backend might be offline — show empty state gracefully
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchKnowledge(); }, [fetchKnowledge]);

  // ── Upload ────────────────────────────────────────────────────────────────
  const handleFiles = useCallback(async (files: FileList | File[]) => {
    const fileArr = Array.from(files);

    const newItems: UploadItem[] = fileArr.map(f => ({
      id: `${f.name}-${Date.now()}`,
      file: f,
      progress: 0,
      status: "uploading",
    }));

    setUploadQueue(prev => [...prev, ...newItems]);

    for (const item of newItems) {
      try {
        await knowledgeService.uploadKnowledge(
          item.file,
          true, // auto_ingest
          (pct) => {
            setUploadQueue(prev =>
              prev.map(u => u.id === item.id ? { ...u, progress: pct } : u)
            );
          }
        );

        setUploadQueue(prev =>
          prev.map(u => u.id === item.id ? { ...u, status: "done", progress: 100 } : u)
        );
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        setUploadQueue(prev =>
          prev.map(u => u.id === item.id ? { ...u, status: "error", error: msg } : u)
        );
      }
    }

    await fetchKnowledge();
    setTimeout(() => {
      setUploadQueue(prev => prev.filter(u => u.status !== "done"));
    }, 3000);
  }, [fetchKnowledge]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) handleFiles(e.target.files);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ── Drag-and-drop ─────────────────────────────────────────────────────────
  const [isDragging, setIsDragging] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) handleFiles(e.dataTransfer.files);
  };

  // ── Ingest all ────────────────────────────────────────────────────────────
  const handleIngestAll = async () => {
    setIngesting(true);
    try {
      await knowledgeService.ingestKnowledge();
      await new Promise(r => setTimeout(r, 1500));
      await fetchKnowledge();
    } catch {/* non-fatal */} finally {
      setIngesting(false);
    }
  };

  // ── Delete document ───────────────────────────────────────────────────────
  const handleDeleteDoc = async (filename: string) => {
    setDeletingDoc(filename);
    setConfirmDelete(null);
    try {
      await knowledgeService.deleteDocument(filename);
      await fetchKnowledge();
    } catch {
      // non-fatal
    } finally {
      setDeletingDoc(null);
    }
  };

  // ── RAG Search / Ask ──────────────────────────────────────────────────────
  const handleRagQuery = useCallback(async () => {
    if (!ragQuery.trim()) return;
    setRagSearching(true);
    setSearchResults(null);
    setRagAnswer(null);

    try {
      if (ragTab === "search") {
        const data = await knowledgeService.search(ragQuery, 5);
        setSearchResults(data.results ?? []);
      } else {
        const data = await knowledgeService.ask(ragQuery, null, 5);
        setRagAnswer(data);
      }
    } catch (e) {
      console.error("RAG query failed:", e);
    } finally {
      setRagSearching(false);
    }
  }, [ragQuery, ragTab]);

  const handleRagKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleRagQuery();
    }
  };

  // ── Filtered docs ─────────────────────────────────────────────────────────
  const filteredDocs = docs.filter(d =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (d.department ?? "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  const chunkCount = (stats.vector_store as { count?: number })?.count ?? 0;

  return (
    <div className="max-w-6xl mx-auto px-4 lg:px-8 py-8 h-full flex flex-col gap-8">

      <PageHeader
        title="Knowledge Base"
        description="Manage secure documents for local vector search"
        action={
          <div className="flex items-center gap-3">
            <button
              onClick={handleIngestAll}
              disabled={ingesting || loading}
              className="flex items-center gap-2 bg-white/[0.04] hover:bg-white/[0.08] disabled:opacity-50 border border-white/[0.06] px-4 py-2.5 rounded-xl text-[12px] font-semibold tracking-wide text-gray-300 transition-all"
            >
              <RefreshCw className={cn("w-4 h-4", ingesting && "animate-spin")} />
              Re-Index
            </button>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              multiple
              accept={ACCEPTED_EXTS}
              onChange={handleFileInput}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 bg-accent hover:bg-accent/90 px-5 py-2.5 rounded-xl text-[13px] font-semibold tracking-wide text-white transition-all shadow-[0_0_15px_rgba(56,114,224,0.3)] hover:shadow-[0_0_22px_rgba(56,114,224,0.5)]"
            >
              <Upload className="w-4 h-4" />
              Upload Document
            </button>
          </div>
        }
      />

      {/* ── Stats ─────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 shrink-0">
        <GlassCard className="p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-b from-blue-500/20 to-blue-500/5 border border-blue-500/20 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(59,130,246,0.15)]">
            <Database className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-0.5">Documents</p>
            <p className="text-[26px] font-bold text-white leading-none">{loading ? "…" : stats.total_documents}</p>
          </div>
        </GlassCard>

        <GlassCard className="p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-b from-green-500/20 to-green-500/5 border border-green-500/20 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(34,197,94,0.15)]">
            <FileText className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-0.5">Indexed Chunks</p>
            <p className="text-[26px] font-bold text-white leading-none">{loading ? "…" : chunkCount}</p>
          </div>
        </GlassCard>

        <GlassCard className="p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-b from-purple-500/20 to-purple-500/5 border border-purple-500/20 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(168,85,247,0.15)]">
            <Zap className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-0.5">Embedding</p>
            <p className="text-[12px] font-bold text-purple-300 leading-none mt-1">nomic-embed-text</p>
          </div>
        </GlassCard>

        <GlassCard className="p-5 flex items-center gap-4">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-b from-emerald-500/20 to-emerald-500/5 border border-emerald-500/20 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(16,185,129,0.15)]">
            <Lock className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-0.5">Air-Gap</p>
            <p className="text-[12px] font-bold text-emerald-400 leading-none mt-1">100% Local</p>
          </div>
        </GlassCard>
      </div>

      {/* ── Upload Queue ──────────────────────────────────────────────────── */}
      <AnimatePresence>
        {uploadQueue.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-3"
          >
            {uploadQueue.map(item => (
              <div key={item.id} className="flex items-center gap-4 px-5 py-4 rounded-2xl bg-surface/40 border border-white/[0.04] backdrop-blur-xl">
                <div className="w-9 h-9 rounded-xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center shrink-0">
                  <ExtIcon ext={item.file.name.split(".").pop() ?? ""} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1.5">
                    <p className="text-[13px] font-medium text-white truncate pr-4">{item.file.name}</p>
                    <span className={cn(
                      "text-[10px] font-bold uppercase tracking-widest shrink-0",
                      item.status === "done"     && "text-green-400",
                      item.status === "error"    && "text-red-400",
                      item.status === "uploading" && "text-gray-400",
                      item.status === "ingesting" && "text-accent",
                    )}>
                      {item.status === "uploading" && `${item.progress}%`}
                      {item.status === "ingesting" && "Indexing…"}
                      {item.status === "done"      && "✓ Done"}
                      {item.status === "error"     && `✗ ${item.error ?? "Failed"}`}
                    </span>
                  </div>
                  <div className="h-1 w-full rounded-full bg-white/[0.05] overflow-hidden">
                    <motion.div
                      className={cn(
                        "h-full rounded-full",
                        item.status === "done"  && "bg-green-500",
                        item.status === "error" && "bg-red-500",
                        !["done","error"].includes(item.status) && "bg-accent",
                      )}
                      initial={{ width: 0 }}
                      animate={{ width: `${item.progress}%` }}
                      transition={{ ease: "easeOut" }}
                    />
                  </div>
                </div>
                {(item.status === "done" || item.status === "error") && (
                  <button
                    onClick={() => setUploadQueue(prev => prev.filter(u => u.id !== item.id))}
                    className="w-7 h-7 rounded-lg flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/[0.06] transition-all shrink-0"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── RAG Panel ─────────────────────────────────────────────────────── */}
      <GlassCard className="p-0 overflow-hidden rounded-2xl shrink-0">
        {/* Header row */}
        <button
          onClick={() => setRagPanelOpen(v => !v)}
          className="w-full p-5 flex items-center justify-between border-b border-white/[0.04] bg-surface/30 hover:bg-white/[0.01] transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
              <Search className="w-4 h-4 text-accent" />
            </div>
            <div className="text-left">
              <p className="text-[13px] font-semibold text-white">Semantic Search &amp; Grounded Q&amp;A</p>
              <p className="text-[11px] text-gray-500 mt-0.5">
                {chunkCount > 0
                  ? `${chunkCount} chunks indexed · RAG ready`
                  : "Upload & index documents first to enable search"}
              </p>
            </div>
          </div>
          {ragPanelOpen
            ? <ChevronUp className="w-4 h-4 text-gray-500" />
            : <ChevronDown className="w-4 h-4 text-gray-500" />}
        </button>

        <AnimatePresence initial={false}>
          {ragPanelOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="p-5 space-y-4">
                {/* Tab toggle + search bar */}
                <div className="flex flex-col sm:flex-row gap-3">
                  {/* Tabs */}
                  <div className="flex bg-white/[0.03] border border-white/[0.05] rounded-xl p-1 shrink-0">
                    {(["search", "ask"] as const).map(tab => (
                      <button
                        key={tab}
                        onClick={() => { setRagTab(tab); setSearchResults(null); setRagAnswer(null); }}
                        className={cn(
                          "flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-semibold transition-all",
                          ragTab === tab
                            ? "bg-accent text-white shadow-[0_0_10px_rgba(56,114,224,0.3)]"
                            : "text-gray-500 hover:text-gray-300"
                        )}
                      >
                        {tab === "search" ? <Search className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5" />}
                        {tab === "search" ? "Semantic Search" : "Grounded Q&A"}
                      </button>
                    ))}
                  </div>

                  {/* Input + Submit */}
                  <div className="flex flex-1 gap-2">
                    <div className="relative flex-1">
                      <input
                        ref={ragInputRef}
                        type="text"
                        value={ragQuery}
                        onChange={e => setRagQuery(e.target.value)}
                        onKeyDown={handleRagKeyDown}
                        placeholder={
                          ragTab === "search"
                            ? "e.g. acceptable vibration limit, bearing temperature threshold…"
                            : "Ask a question to be answered from the knowledge base…"
                        }
                        className="w-full bg-white/[0.02] border border-white/[0.06] rounded-xl pl-4 pr-10 py-2.5 text-[13px] text-white placeholder:text-gray-600 focus:outline-none focus:border-accent/50 focus:bg-white/[0.04] transition-all"
                      />
                      {ragQuery && (
                        <button
                          onClick={() => { setRagQuery(""); setSearchResults(null); setRagAnswer(null); }}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                    <button
                      onClick={handleRagQuery}
                      disabled={ragSearching || !ragQuery.trim() || chunkCount === 0}
                      className="flex items-center gap-2 bg-accent hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed px-4 py-2.5 rounded-xl text-[12px] font-semibold text-white transition-all shadow-[0_0_12px_rgba(56,114,224,0.25)] whitespace-nowrap"
                    >
                      {ragSearching
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : ragTab === "search"
                          ? <Search className="w-4 h-4" />
                          : <Sparkles className="w-4 h-4" />
                      }
                      {ragSearching
                        ? ragTab === "ask" ? "LLM Thinking…" : "Searching…"
                        : ragTab === "search" ? "Search" : "Ask RAG"}
                    </button>
                  </div>
                </div>

                {/* LLM latency hint */}
                {ragTab === "ask" && !ragSearching && chunkCount > 0 && (
                  <p className="text-[11px] text-gray-600 -mt-1">
                    ⏱ Grounded Q&amp;A calls the local LLM — response may take <span className="text-gray-500 font-medium">30–90 seconds</span> depending on hardware.
                  </p>
                )}
                {ragSearching && ragTab === "ask" && (
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-[11px] text-accent/80 -mt-1 flex items-center gap-1.5"
                  >
                    <Loader2 className="w-3 h-3 animate-spin" />
                    Local LLM is generating a grounded answer from your indexed documents…
                  </motion.p>
                )}

                {chunkCount === 0 && (
                  <div className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-yellow-500/5 border border-yellow-500/15 text-[12px] text-yellow-400/80">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    Knowledge base is empty. Upload documents and click <strong className="text-yellow-300">Re-Index</strong> to enable RAG search.
                  </div>
                )}

                {/* Search Results */}
                <AnimatePresence>
                  {searchResults !== null && (
                    <motion.div
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="space-y-3"
                    >
                      <p className="text-[11px] font-bold text-gray-500 uppercase tracking-widest">
                        {searchResults.length > 0
                          ? `${searchResults.length} relevant chunk${searchResults.length !== 1 ? "s" : ""} found`
                          : "No matching chunks — try different terms or re-index"}
                      </p>
                      {searchResults.map((r, i) => (
                        <div
                          key={r.id || i}
                          className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-white/[0.09] transition-all"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2.5">
                              <span className="w-5 h-5 rounded-md bg-accent/15 text-accent text-[10px] font-bold flex items-center justify-center">
                                {i + 1}
                              </span>
                              <span className="text-[12px] font-semibold text-white">{r.document}</span>
                              {r.page && (
                                <span className="text-[10px] text-gray-500 bg-white/[0.03] border border-white/[0.05] px-1.5 py-0.5 rounded">
                                  Page {r.page}
                                </span>
                              )}
                            </div>
                            <ScoreBar score={r.score} />
                          </div>
                          <p className="text-[12px] text-gray-400 leading-relaxed line-clamp-4">
                            {r.text}
                          </p>
                        </div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Grounded Q&A Answer */}
                <AnimatePresence>
                  {ragAnswer && (
                    <motion.div
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      className="rounded-xl border overflow-hidden"
                      style={{
                        background: "linear-gradient(135deg, rgba(16,185,129,0.03) 0%, rgba(56,114,224,0.03) 100%)",
                        borderColor: "rgba(16,185,129,0.2)",
                      }}
                    >
                      {/* Answer header */}
                      <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-emerald-500/10 bg-emerald-500/5">
                        <Sparkles className="w-4 h-4 text-emerald-400" />
                        <span className="text-[12px] font-bold text-emerald-400 uppercase tracking-wider">
                          Grounded Answer
                        </span>
                        {ragAnswer.model && (
                          <span className="ml-auto text-[10px] text-gray-500 bg-white/[0.03] border border-white/[0.05] px-2 py-0.5 rounded-md">
                            {ragAnswer.model}
                          </span>
                        )}
                        {!ragAnswer.rag_used && (
                          <span className="ml-auto text-[10px] text-yellow-400 bg-yellow-400/10 border border-yellow-400/20 px-2 py-0.5 rounded-md">
                            No KB context — model only
                          </span>
                        )}
                      </div>

                      {/* Answer body */}
                      <div className="px-5 py-4">
                        <p className="text-[13px] text-gray-200 leading-relaxed whitespace-pre-wrap">
                          {ragAnswer.answer}
                        </p>

                        {/* Sources */}
                        {ragAnswer.sources && ragAnswer.sources.length > 0 && (
                          <div className="mt-4 pt-4 border-t border-white/[0.05]">
                            <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">
                              Cited Sources
                            </p>
                            <div className="flex flex-wrap gap-2">
                              {ragAnswer.sources.map(s => (
                                <div
                                  key={s.index}
                                  className="flex items-center gap-1.5 text-[11px] text-gray-400 bg-white/[0.02] border border-white/[0.05] px-2.5 py-1 rounded-lg"
                                >
                                  <span className="text-accent font-bold">[{s.index}]</span>
                                  {s.document}
                                  {s.page && <span className="text-gray-600">· p.{s.page}</span>}
                                  <span className="text-gray-600">·</span>
                                  <ScoreBar score={s.score} />
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {ragAnswer.warning && (
                          <div className="mt-3 flex items-center gap-2 text-[11px] text-yellow-400/80">
                            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                            {ragAnswer.warning}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </GlassCard>

      {/* ── Drop zone + Library ───────────────────────────────────────────── */}
      <GlassCard
        className="p-0 overflow-hidden rounded-2xl flex-1 flex flex-col"
        onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        {/* Drag overlay */}
        <AnimatePresence>
          {isDragging && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-accent/10 border-2 border-dashed border-accent/50 rounded-2xl backdrop-blur-sm"
            >
              <Upload className="w-10 h-10 text-accent mb-3" />
              <p className="text-[15px] font-semibold text-white">Drop files to upload</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Header */}
        <div className="p-5 border-b border-white/[0.04] bg-surface/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
          <h3 className="text-[14px] font-semibold text-white tracking-wide">Document Library</h3>
          <div className="relative">
            <Search className="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search documents…"
              className="bg-white/[0.02] border border-white/[0.05] rounded-xl pl-10 pr-4 py-2 text-[13px] text-white focus:outline-none focus:border-accent/50 focus:bg-white/[0.04] transition-all w-full sm:w-64 shadow-inner"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Table header */}
        {!loading && filteredDocs.length > 0 && (
          <div className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-4 px-5 py-3 border-b border-white/[0.03] bg-white/[0.01]">
            <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest">Name</p>
            <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest w-24 text-right hidden md:block">Department</p>
            <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest w-20 text-center hidden lg:block">Class</p>
            <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest w-20 text-center">Type</p>
            <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest w-28 text-right">Permission</p>
            <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest w-8 text-right"></p>
          </div>
        )}

        {/* Rows */}
        <div className="divide-y divide-white/[0.03] overflow-y-auto flex-1">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center gap-3">
              <Loader2 className="w-7 h-7 text-gray-500 animate-spin" />
              <p className="text-[13px] text-gray-500">Fetching knowledge base…</p>
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="py-16 flex flex-col items-center justify-center gap-3 opacity-50 select-none">
              <BookOpen className="w-10 h-10 text-gray-500" />
              <p className="text-[14px] text-gray-400 font-medium">No documents found</p>
              <p className="text-[12px] text-gray-500">
                {searchQuery ? "Try a different search term" : "Drag & drop files or click 'Upload Document'"}
              </p>
            </div>
          ) : (
            <AnimatePresence initial={false}>
              {filteredDocs.map((doc, idx) => (
                <motion.div
                  key={doc.path}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ delay: idx * 0.03, duration: 0.2 }}
                  className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-4 items-center px-5 py-4 hover:bg-white/[0.02] transition-colors group"
                >
                  {/* Name + size */}
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-center shrink-0 group-hover:border-white/[0.08] group-hover:bg-white/[0.04] transition-all">
                      <ExtIcon ext={doc.ext} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-[14px] font-medium text-white truncate">{doc.name}</p>
                      <p className="text-[11px] text-gray-600 uppercase tracking-wider mt-0.5">
                        {formatBytes(doc.size)}
                      </p>
                    </div>
                  </div>

                  {/* Department */}
                  <p className="text-[12px] text-gray-500 w-24 text-right truncate hidden md:block">
                    {doc.department ?? "—"}
                  </p>

                  {/* Classification */}
                  <div className="w-20 flex justify-center hidden lg:flex">
                    {doc.classification ? (
                      <span className={cn(
                        "text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-md border",
                        doc.classification === "RESTRICTED"  && "text-red-400 bg-red-400/10 border-red-400/20",
                        doc.classification === "CONFIDENTIAL" && "text-orange-400 bg-orange-400/10 border-orange-400/20",
                        doc.classification === "OPEN"        && "text-green-400 bg-green-400/10 border-green-400/20",
                        !["RESTRICTED","CONFIDENTIAL","OPEN"].includes(doc.classification) && "text-gray-500 bg-white/[0.02] border-white/[0.04]",
                      )}>
                        {doc.classification}
                      </span>
                    ) : (
                      <span className="text-[11px] text-gray-600">—</span>
                    )}
                  </div>

                  {/* Extension badge */}
                  <div className="w-20 flex justify-center">
                    <ExtBadge ext={doc.ext} />
                  </div>

                  {/* Permission */}
                  <div className="w-28 flex justify-end">
                    <PermissionBadge doc={doc} />
                  </div>

                  {/* Delete button */}
                  <div className="w-8 flex justify-end">
                    <AnimatePresence mode="wait">
                      {confirmDelete === doc.name ? (
                        <motion.div
                          key="confirm"
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.9 }}
                          className="flex items-center gap-1"
                        >
                          <button
                            onClick={() => handleDeleteDoc(doc.name)}
                            className="text-[10px] font-bold text-red-400 bg-red-400/10 border border-red-400/20 px-2 py-1 rounded-lg hover:bg-red-400/20 transition-all"
                          >
                            {deletingDoc === doc.name ? <Loader2 className="w-3 h-3 animate-spin" /> : "Yes"}
                          </button>
                          <button
                            onClick={() => setConfirmDelete(null)}
                            className="text-[10px] text-gray-500 hover:text-white px-1 py-1"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </motion.div>
                      ) : (
                        <motion.button
                          key="delete"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          exit={{ opacity: 0 }}
                          onClick={() => setConfirmDelete(doc.name)}
                          className="w-7 h-7 rounded-lg flex items-center justify-center text-gray-600 opacity-0 group-hover:opacity-100 hover:text-red-400 hover:bg-red-400/10 transition-all"
                          title="Delete document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </motion.button>
                      )}
                    </AnimatePresence>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
        </div>

        {/* Footer */}
        {!loading && filteredDocs.length > 0 && (
          <div className="px-5 py-3 border-t border-white/[0.03] bg-white/[0.01] flex items-center justify-between shrink-0">
            <p className="text-[11px] text-gray-600">
              {filteredDocs.length} document{filteredDocs.length !== 1 ? "s" : ""}
              {searchQuery && ` matching "${searchQuery}"`}
            </p>
            <p className="text-[11px] text-gray-600 hidden sm:block">
              Drag & drop to upload · Supports PDF, DOCX, images
            </p>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
