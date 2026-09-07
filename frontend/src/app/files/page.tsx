"use client";

import { useState, useEffect, useCallback } from "react";
import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import { Download, FileCode, FileText, Search, RefreshCw, File, Clock, HardDrive } from "lucide-react";

const API = "http://localhost:8000";

interface OutputFile {
  name: string;
  size: number;
  modified: number;
  ext: string;
  download_url: string;
}

function fileIcon(ext: string) {
  if (["py", "js", "ts", "sh"].includes(ext)) return <FileCode className="w-5 h-5 text-accent" />;
  if (["docx", "doc", "pdf", "txt", "md"].includes(ext)) return <FileText className="w-5 h-5 text-green-400" />;
  return <File className="w-5 h-5 text-gray-400" />;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

export default function FilesPage() {
  const [files, setFiles] = useState<OutputFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/files`);
      if (r.ok) {
        const data = await r.json();
        setFiles(data.files || []);
      }
    } catch {/* silent */}
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRefresh = () => {
    setRefreshing(true);
    load();
  };

  const filtered = files.filter(f =>
    f.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto">
      <PageHeader
        title="Generated Files"
        description="Files produced by the AI agent — download directly to your machine"
        action={
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] px-4 py-2 rounded-xl text-sm font-medium text-gray-300 transition-all duration-300"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
        }
      />

      <GlassCard className="p-0 overflow-hidden border-white/[0.04]">
        {/* Toolbar */}
        <div className="p-4 border-b border-white/[0.04] flex items-center justify-between gap-4">
          <h3 className="text-sm font-medium text-white shrink-0">
            Workspace Files
            <span className="ml-2 text-[11px] text-gray-500 font-normal">
              ({filtered.length} {filtered.length === 1 ? "file" : "files"})
            </span>
          </h3>
          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter files..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-surface/50 border border-white/[0.06] rounded-xl pl-9 pr-3 py-1.5 text-sm text-white focus:outline-none focus:border-accent/50 w-56 placeholder:text-gray-600 transition-colors"
            />
          </div>
        </div>

        {/* File grid */}
        {loading ? (
          <div className="py-20 text-center text-gray-500 text-sm">
            <RefreshCw className="w-6 h-6 mx-auto mb-3 animate-spin opacity-50" />
            Loading files…
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-20 text-center">
            <File className="w-10 h-10 text-gray-700 mx-auto mb-4" />
            <p className="text-[14px] text-gray-400 mb-2">
              {search ? "No files match your search" : "No generated files yet"}
            </p>
            <p className="text-[12px] text-gray-600">
              {search ? "Try a different search term" : "Run the AI agent on a task to generate output files"}
            </p>
          </div>
        ) : (
          <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((file) => (
              <div
                key={file.name}
                className="p-4 rounded-xl border border-white/[0.05] bg-surface/30 hover:bg-surface/50 hover:border-white/[0.1] transition-all duration-300 flex flex-col gap-3 group"
              >
                <div className="flex items-start justify-between">
                  <div className="w-10 h-10 rounded-xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
                    {fileIcon(file.ext)}
                  </div>
                  <a
                    href={`${API}${file.download_url}`}
                    download={file.name}
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/[0.08] opacity-0 group-hover:opacity-100 transition-all duration-200"
                    title="Download"
                  >
                    <Download className="w-4 h-4" />
                  </a>
                </div>

                <div>
                  <p
                    className="text-[13px] font-medium text-white truncate"
                    title={file.name}
                  >
                    {file.name}
                  </p>
                  <div className="flex items-center gap-3 mt-1.5 text-[11px] text-gray-500">
                    <span className="flex items-center gap-1">
                      <HardDrive className="w-3 h-3" />
                      {formatSize(file.size)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTime(file.modified)}
                    </span>
                  </div>
                </div>

                <a
                  href={`${API}${file.download_url}`}
                  download={file.name}
                  className="mt-auto flex items-center justify-center gap-2 py-2 rounded-lg bg-accent/10 border border-accent/20 text-[12px] font-medium text-accent hover:bg-accent/20 transition-all duration-200"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </a>
              </div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
}
