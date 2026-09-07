"use client";

import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import {
  Download, Search, RefreshCw, Loader2, FileText,
  FileCode, FileJson, FileImage, File, CheckCircle2,
  AlertCircle, X, FolderOpen
} from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { filesService, GeneratedFile } from "@/lib/services/files";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    const diffHr  = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1)  return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHr  < 24) return `${diffHr}h ago`;
    if (diffDay < 7)  return `${diffDay}d ago`;
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch { return iso; }
}

// ── File type icon + accent ───────────────────────────────────────────────────

interface FileStyle {
  icon: React.ElementType;
  iconColor: string;
  bgFrom: string;
  border: string;
  badgeColor: string;
}

const FILE_STYLES: Record<string, FileStyle> = {
  docx: { icon: FileText,  iconColor: "text-blue-400",   bgFrom: "from-blue-500/20",   border: "border-blue-500/20",   badgeColor: "text-blue-400 bg-blue-400/10 border-blue-400/20"   },
  pdf:  { icon: FileText,  iconColor: "text-red-400",    bgFrom: "from-red-500/20",    border: "border-red-500/20",    badgeColor: "text-red-400 bg-red-400/10 border-red-400/20"      },
  xlsx: { icon: FileJson,  iconColor: "text-green-400",  bgFrom: "from-green-500/20",  border: "border-green-500/20",  badgeColor: "text-green-400 bg-green-400/10 border-green-400/20" },
  csv:  { icon: FileJson,  iconColor: "text-teal-400",   bgFrom: "from-teal-500/20",   border: "border-teal-500/20",   badgeColor: "text-teal-400 bg-teal-400/10 border-teal-400/20"   },
  txt:  { icon: FileText,  iconColor: "text-gray-400",   bgFrom: "from-white/10",      border: "border-white/10",      badgeColor: "text-gray-400 bg-white/[0.04] border-white/[0.06]"  },
  py:   { icon: FileCode,  iconColor: "text-yellow-400", bgFrom: "from-yellow-500/20", border: "border-yellow-500/20", badgeColor: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20" },
  js:   { icon: FileCode,  iconColor: "text-yellow-300", bgFrom: "from-yellow-400/20", border: "border-yellow-400/20", badgeColor: "text-yellow-300 bg-yellow-300/10 border-yellow-300/20" },
  ts:   { icon: FileCode,  iconColor: "text-blue-300",   bgFrom: "from-blue-400/20",   border: "border-blue-400/20",   badgeColor: "text-blue-300 bg-blue-300/10 border-blue-300/20"   },
  json: { icon: FileJson,  iconColor: "text-orange-400", bgFrom: "from-orange-500/20", border: "border-orange-500/20", badgeColor: "text-orange-400 bg-orange-400/10 border-orange-400/20" },
  yaml: { icon: FileCode,  iconColor: "text-purple-400", bgFrom: "from-purple-500/20", border: "border-purple-500/20", badgeColor: "text-purple-400 bg-purple-400/10 border-purple-400/20" },
  png:  { icon: FileImage, iconColor: "text-pink-400",   bgFrom: "from-pink-500/20",   border: "border-pink-500/20",   badgeColor: "text-pink-400 bg-pink-400/10 border-pink-400/20"   },
  jpg:  { icon: FileImage, iconColor: "text-pink-400",   bgFrom: "from-pink-500/20",   border: "border-pink-500/20",   badgeColor: "text-pink-400 bg-pink-400/10 border-pink-400/20"   },
};

const DEFAULT_STYLE: FileStyle = {
  icon: File,
  iconColor: "text-gray-400",
  bgFrom: "from-white/5",
  border: "border-white/10",
  badgeColor: "text-gray-500 bg-white/[0.03] border-white/[0.05]",
};

function getFileStyle(ext: string): FileStyle {
  return FILE_STYLES[ext.toLowerCase()] ?? DEFAULT_STYLE;
}

// ── File Card ─────────────────────────────────────────────────────────────────

function FileCard({ file, idx }: { file: GeneratedFile; idx: number }) {
  const style = getFileStyle(file.ext);
  const Icon = style.icon;

  const handleDownload = () => {
    if (file.path && file.path.length > file.name.length) {
      filesService.downloadFileByPath(file.path);
    } else {
      filesService.downloadFileByName(file.name);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: idx * 0.05, duration: 0.25, ease: "easeOut" }}
      className="p-5 rounded-2xl border border-white/[0.04] bg-surface/30 hover:bg-surface/50 hover:border-white/[0.07] transition-all duration-300 flex flex-col gap-5 group shadow-sm hover:shadow-[0_8px_32px_rgba(0,0,0,0.3)]"
    >
      {/* Top row: icon + download */}
      <div className="flex items-start justify-between">
        <div className={cn(
          "w-12 h-12 rounded-xl bg-gradient-to-b to-transparent border flex items-center justify-center shadow-inner",
          style.bgFrom, style.border
        )}>
          <Icon className={cn("w-5 h-5", style.iconColor)} />
        </div>

        <button
          onClick={handleDownload}
          title="Download"
          className="w-10 h-10 rounded-xl flex items-center justify-center text-gray-500 hover:text-white bg-white/[0.02] hover:bg-white/[0.08] opacity-0 group-hover:opacity-100 transition-all duration-200 border border-transparent hover:border-white/10"
        >
          <Download className="w-4 h-4" />
        </button>
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-[14px] font-semibold text-white truncate tracking-wide" title={file.name}>
          {file.name}
        </p>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          <span className={cn(
            "text-[9px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-md border",
            style.badgeColor
          )}>
            {file.ext || "file"}
          </span>
          {file.size > 0 && (
            <span className="text-[10px] text-gray-600">{formatBytes(file.size)}</span>
          )}
        </div>
      </div>

      {/* Footer: timestamp + verification */}
      <div className="flex items-center justify-between pt-3 border-t border-white/[0.04]">
        <p className="text-[11px] text-gray-600 uppercase tracking-wider">
          {formatTimestamp(file.generated_at)}
        </p>

        {file.verified ? (
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-green-400 bg-green-400/10 border border-green-400/20 px-2 py-1 rounded-md uppercase tracking-wider">
            <CheckCircle2 className="w-3 h-3" />
            Verified
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500 bg-white/[0.02] border border-white/[0.04] px-2 py-1 rounded-md uppercase tracking-wider">
            <AlertCircle className="w-3 h-3" />
            Unverified
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

const EXT_FILTERS = ["all", "docx", "xlsx", "pdf", "txt", "py", "json", "yaml", "png"];

export default function FilesPage() {
  const [files,      setFiles]      = useState<GeneratedFile[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search,     setSearch]     = useState("");
  const [extFilter,  setExtFilter]  = useState("all");

  const fetchFiles = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await filesService.getGeneratedFiles();
      setFiles(data);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchFiles(); }, [fetchFiles]);

  // Filter
  const filtered = files.filter(f => {
    const matchSearch = f.name.toLowerCase().includes(search.toLowerCase());
    const matchExt    = extFilter === "all" || f.ext === extFilter;
    return matchSearch && matchExt;
  });

  // Unique extensions present
  const presentExts = ["all", ...Array.from(new Set(files.map(f => f.ext).filter(Boolean)))];
  const visibleFilters = EXT_FILTERS.filter(e => presentExts.includes(e));

  return (
    <div className="max-w-6xl mx-auto px-4 lg:px-8 py-8 h-full flex flex-col gap-8">

      <PageHeader
        title="Generated Files"
        description="Download files generated by the AI agent"
        action={
          <button
            onClick={() => fetchFiles(true)}
            disabled={refreshing}
            className="flex items-center gap-2 bg-white/[0.04] hover:bg-white/[0.08] disabled:opacity-50 border border-white/[0.06] px-4 py-2.5 rounded-xl text-[12px] font-semibold tracking-wide text-gray-300 transition-all"
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
            Refresh
          </button>
        }
      />

      {/* ── Stats strip ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 shrink-0">
        {[
          { label: "Total Files",  value: files.length },
          { label: "DOCX",         value: files.filter(f => f.ext === "docx").length },
          { label: "Code Files",   value: files.filter(f => ["py","js","ts","yaml","json"].includes(f.ext)).length },
          { label: "Verified",     value: files.filter(f => f.verified).length },
        ].map((stat, i) => (
          <GlassCard key={i} className="p-4 text-center bg-surface/30 border-white/[0.03]">
            <p className="text-[24px] font-bold text-white leading-none">{loading ? "…" : stat.value}</p>
            <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest mt-1">{stat.label}</p>
          </GlassCard>
        ))}
      </div>

      {/* ── Search + Filter bar ───────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-4 shrink-0">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-gray-500 absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Filter files…"
            className="w-full h-11 bg-surface/40 border border-white/[0.05] hover:border-white/10 rounded-xl pl-10 pr-10 text-[13px] text-white focus:outline-none focus:border-accent/50 focus:bg-white/[0.04] transition-all shadow-inner"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Extension pills */}
        <div className="flex items-center gap-2 flex-wrap">
          {visibleFilters.map(ext => (
            <button
              key={ext}
              onClick={() => setExtFilter(ext)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-widest border transition-all",
                extFilter === ext
                  ? "bg-accent/20 border-accent/40 text-white shadow-[0_0_10px_rgba(56,114,224,0.15)]"
                  : "bg-white/[0.02] border-white/[0.04] text-gray-500 hover:text-gray-300 hover:border-white/[0.08]"
              )}
            >
              {ext}
            </button>
          ))}
        </div>
      </div>

      {/* ── File Grid ─────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4 opacity-50">
            <Loader2 className="w-7 h-7 text-gray-400 animate-spin" />
            <p className="text-[13px] text-gray-500">Loading generated files…</p>
          </div>
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 opacity-40 select-none">
          <FolderOpen className="w-14 h-14 text-gray-600" />
          <p className="text-[15px] text-gray-400 font-medium">
            {files.length === 0 ? "No files generated yet." : "No files match your filter."}
          </p>
          <p className="text-[12px] text-gray-600 text-center max-w-xs">
            {files.length === 0
              ? "Run an agent task from the Workbench and generated files will appear here."
              : "Try adjusting your search or file type filter."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          <AnimatePresence initial={false}>
            {filtered.map((file, idx) => (
              <FileCard key={file.path + file.name} file={file} idx={idx} />
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
