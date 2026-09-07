"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  FileStack,
  Scissors,
  BookCopy,
  Trash2,
  RotateCw,
  ImageDown,
  FilePlus,
  FileText,
  Minimize2,
  Info,
  Download,
  Upload,
  X,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  GripVertical,
  ChevronDown,
  ChevronRight,
  Shield,
  Key,
  Eye,
  Type,
  Hash,
  PenTool,
  FileSpreadsheet,
  Layers,
  Search,
  GitCompare,
  Image as ImageIcon,
  Crop,
  FileCode,
  Table as TableIcon,
  Presentation,
  Check,
} from "lucide-react";

const API = "/api/document-tools";

// ─── shared types ────────────────────────────────────────────────────────────

interface FileItem {
  id: string;
  file: File;
  name: string;
  size: number;
}

interface OpState {
  loading: boolean;
  error: string | null;
  success: string | null;
  downloadUrl: string | null;
  downloadName: string | null;
  extraInfo: Record<string, string>;
  rawJson?: any;
}

function initState(): OpState {
  return { loading: false, error: null, success: null, downloadUrl: null, downloadName: null, extraInfo: {} };
}

function fmt(bytes: number): string {
  if (isNaN(bytes) || bytes === null || bytes === undefined || bytes < 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function uid(): string {
  return Math.random().toString(36).slice(2);
}

// ─── reusable UI primitives ──────────────────────────────────────────────────

function SectionHeader({ label }: { label: string }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase",
      color: "var(--text-muted)", paddingBottom: 8, borderBottom: "1px solid var(--border)", marginBottom: 14,
    }}>
      {label}
    </div>
  );
}

function DropZone({
  accept,
  multiple,
  onFiles,
  label,
  hint,
}: {
  accept: string;
  multiple?: boolean;
  onFiles: (files: File[]) => void;
  label?: string;
  hint?: string;
}) {
  const [dragging, setDragging] = useState(false);
  const ref = useRef<HTMLInputElement>(null);

  const handle = (files: FileList | null) => {
    if (!files?.length) return;
    onFiles(Array.from(files));
  };

  return (
    <div
      onClick={() => ref.current?.click()}
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); handle(e.dataTransfer.files); }}
      style={{
        border: `2px dashed ${dragging ? "var(--accent-orange)" : "var(--border)"}`,
        borderRadius: 8, padding: "20px 16px", cursor: "pointer",
        background: dragging ? "rgba(249,115,22,0.04)" : "var(--bg-card)",
        transition: "all 0.15s", textAlign: "center", marginBottom: 12,
      }}
    >
      <Upload size={24} color="var(--text-muted)" style={{ margin: "0 auto 8px" }} />
      <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{label || "Drop files here or click to browse"}</div>
      {hint && <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>{hint}</div>}
      <input ref={ref} type="file" accept={accept} multiple={multiple} style={{ display: "none" }}
        onChange={e => handle(e.target.files)} />
    </div>
  );
}

function FileListItem({
  item,
  onRemove,
  dragHandle,
  extra,
}: {
  item: FileItem;
  onRemove: () => void;
  dragHandle?: boolean;
  extra?: string;
}) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8, padding: "7px 10px",
      background: "var(--bg-card)", border: "1px solid var(--border)",
      borderRadius: 6, marginBottom: 5,
    }}>
      {dragHandle && <GripVertical size={12} color="var(--text-muted)" style={{ cursor: "grab", flexShrink: 0 }} />}
      <FileText size={13} color="var(--accent-orange)" style={{ flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {item.name}
        </div>
        <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{fmt(item.size)}{extra ? ` · ${extra}` : ""}</div>
      </div>
      <button onClick={onRemove} style={{
        background: "transparent", border: "none", cursor: "pointer", padding: 2,
        color: "var(--text-muted)", display: "flex", alignItems: "center",
      }}>
        <X size={12} />
      </button>
    </div>
  );
}

function StatePanel({ state, onReset }: { state: OpState; onReset: () => void }) {
  if (!state.loading && !state.error && !state.success) return null;
  return (
    <div style={{ marginTop: 12 }}>
      {state.loading && (
        <div style={{
          display: "flex", alignItems: "center", gap: 8, padding: "10px 12px",
          background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.2)",
          borderRadius: 7, fontSize: 13, color: "var(--accent-orange)",
        }}>
          <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
          Processing locally…
        </div>
      )}
      {state.error && (
        <div style={{
          display: "flex", gap: 8, padding: "10px 12px",
          background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.25)",
          borderRadius: 7, fontSize: 13, color: "var(--accent-red)",
        }}>
          <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>{state.error}</span>
        </div>
      )}
      {state.success && (
        <div style={{
          padding: "10px 12px",
          background: "rgba(34,197,94,0.07)", border: "1px solid rgba(34,197,94,0.25)",
          borderRadius: 7,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: state.downloadUrl ? 8 : 0 }}>
            <CheckCircle2 size={14} color="var(--accent-green)" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: "var(--accent-green)", fontWeight: 600 }}>{state.success}</span>
          </div>
          {Object.entries(state.extraInfo).map(([k, v]) => (
            <div key={k} style={{ fontSize: 11, color: "var(--text-secondary)", marginLeft: 22, lineHeight: 1.8 }}>
              {k}: <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{v}</span>
            </div>
          ))}
          {state.downloadUrl && (
            <a
              href={state.downloadUrl}
              download={state.downloadName || "output"}
              style={{
                display: "inline-flex", alignItems: "center", gap: 6, marginTop: 8, marginLeft: 22,
                padding: "6px 12px", borderRadius: 5, fontSize: 12, fontWeight: 600,
                background: "rgba(34,197,94,0.12)", border: "1px solid rgba(34,197,94,0.3)",
                color: "var(--accent-green)", textDecoration: "none",
              }}
            >
              <Download size={12} /> Download {state.downloadName}
            </a>
          )}
          <button onClick={onReset} style={{
            display: "inline-flex", alignItems: "center", gap: 4, marginTop: 8, marginLeft: 8,
            padding: "6px 10px", borderRadius: 5, fontSize: 11, cursor: "pointer",
            background: "transparent", border: "1px solid var(--border)", color: "var(--text-muted)",
          }}>Reset</button>
        </div>
      )}
    </div>
  );
}

function RunButton({ onClick, disabled, label }: { onClick: () => void; disabled: boolean; label: string }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="btn"
      style={{
        width: "100%", justifyContent: "center", padding: "10px 16px", marginTop: 8,
        background: disabled ? "rgba(249,115,22,0.05)" : "rgba(249,115,22,0.1)",
        border: "1px solid rgba(249,115,22,0.3)", color: "var(--accent-orange)", fontWeight: 600,
        opacity: disabled ? 0.6 : 1, cursor: disabled ? "not-allowed" : "pointer",
      }}
    >
      {label}
    </button>
  );
}

async function doPost(
  endpoint: string,
  form: FormData,
  setState: (s: OpState) => void,
  successLabel: string,
  filename: string,
  extraExtract?: (res: Response, blob: Blob) => Record<string, string>,
) {
  setState({ loading: true, error: null, success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
  try {
    const res = await fetch(`${API}/${endpoint}`, { method: "POST", body: form });
    if (!res.ok) {
      let msg = `Server error (${res.status})`;
      try { const j = await res.json(); msg = j.detail || msg; } catch {}
      setState({ loading: false, error: msg, success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const extra = extraExtract ? extraExtract(res, blob) : {};
    setState({ loading: false, error: null, success: successLabel, downloadUrl: url, downloadName: filename, extraInfo: extra });
  } catch (err: any) {
    setState({ loading: false, error: err.message || "Network error", success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
  }
}

async function doJsonPost(
  endpoint: string,
  form: FormData,
  setState: (s: OpState) => void,
  renderExtra: (data: any) => { success: string; extraInfo: Record<string, string> },
) {
  setState({ loading: true, error: null, success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
  try {
    const res = await fetch(`${API}/${endpoint}`, { method: "POST", body: form });
    if (!res.ok) {
      let msg = `Server error (${res.status})`;
      try { const j = await res.json(); msg = j.detail || msg; } catch {}
      setState({ loading: false, error: msg, success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
      return;
    }
    const data = await res.json();
    const { success, extraInfo } = renderExtra(data);
    setState({ loading: false, error: null, success, downloadUrl: null, downloadName: null, extraInfo, rawJson: data });
  } catch (err: any) {
    setState({ loading: false, error: err.message || "Network error", success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// 1. ORGANIZE PANELS
// ═══════════════════════════════════════════════════════════════════════════

function MergePanel() {
  const [items, setItems] = useState<FileItem[]>([]);
  const [state, setState] = useState<OpState>(initState());

  const addFiles = (files: File[]) => {
    const pdfs = files.filter(f => f.name.toLowerCase().endsWith(".pdf"));
    if (!pdfs.length) { setState({ ...initState(), error: "Please select PDF files only" }); return; }
    setItems(prev => [...prev, ...pdfs.map(f => ({ id: uid(), file: f, name: f.name, size: f.size }))]);
  };

  const run = async () => {
    if (items.length < 2) { setState({ ...initState(), error: "Select at least 2 PDF files to merge" }); return; }
    const form = new FormData();
    items.forEach(it => form.append("files", it.file, it.name));
    await doPost("merge", form, setState, "PDFs merged successfully", "merged.pdf", (_, blob) => ({
      "Total Files": String(items.length),
      "Merged Size": fmt(blob.size),
    }));
  };

  return (
    <div>
      <SectionHeader label="Merge PDF" />
      <DropZone accept=".pdf,application/pdf" multiple onFiles={addFiles}
        label="Drop 2 or more PDFs here" hint="Files will be merged in the order shown below" />
      {items.map((it, idx) => (
        <FileListItem key={it.id} item={it} dragHandle extra={`#${idx + 1}`}
          onRemove={() => setItems(p => p.filter(x => x.id !== it.id))} />
      ))}
      <RunButton onClick={run} disabled={state.loading || items.length < 2} label={state.loading ? "Merging…" : `Merge ${items.length} PDFs`} />
      <StatePanel state={state} onReset={() => { setItems([]); setState(initState()); }} />
    </div>
  );
}

function SplitPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [mode, setMode] = useState<"all" | "ranges">("all");
  const [ranges, setRanges] = useState("");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("mode", mode);
    if (mode === "ranges") form.append("ranges", ranges);
    await doPost("split", form, setState, "PDF split successfully", mode === "all" ? "split_pages.zip" : "split_parts.zip");
  };

  return (
    <div>
      <SectionHeader label="Split PDF" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF to split" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <div style={{ display: "flex", gap: 8, margin: "10px 0" }}>
        <button onClick={() => setMode("all")} style={{
          flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
          background: mode === "all" ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
          border: `1px solid ${mode === "all" ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
          color: mode === "all" ? "var(--accent-orange)" : "var(--text-secondary)",
        }}>Every Page (ZIP)</button>
        <button onClick={() => setMode("ranges")} style={{
          flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
          background: mode === "ranges" ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
          border: `1px solid ${mode === "ranges" ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
          color: mode === "ranges" ? "var(--accent-orange)" : "var(--text-secondary)",
        }}>Custom Ranges</button>
      </div>
      {mode === "ranges" && (
        <input value={ranges} onChange={e => setRanges(e.target.value)} placeholder="e.g. 1-2, 3-5"
          style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      )}
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Splitting…" : "Split PDF"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function ExtractPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [pages, setPages] = useState("1-2");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("pages", pages);
    await doPost("extract", form, setState, "Pages extracted successfully", "extracted_pages.pdf");
  };

  return (
    <div>
      <SectionHeader label="Extract Pages" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Pages to extract (e.g. 1-3, 5)</label>
      <input value={pages} onChange={e => setPages(e.target.value)}
        style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      <RunButton onClick={run} disabled={state.loading || !item || !pages.trim()} label={state.loading ? "Extracting…" : "Extract Pages"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function DeletePagesPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [pages, setPages] = useState("");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("pages", pages);
    await doPost("delete-pages", form, setState, "Pages removed", "pages_deleted.pdf");
  };

  return (
    <div>
      <SectionHeader label="Delete Pages" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Pages to remove (e.g. 2, 4-5)</label>
      <input value={pages} onChange={e => setPages(e.target.value)} placeholder="e.g. 2, 4"
        style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      <RunButton onClick={run} disabled={state.loading || !item || !pages.trim()} label={state.loading ? "Deleting…" : "Delete Pages"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function ReorderPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [order, setOrder] = useState("");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("order", order);
    await doPost("reorder-pages", form, setState, "Pages reordered", "reordered.pdf");
  };

  return (
    <div>
      <SectionHeader label="Reorder Pages" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF to reorder" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
        New page sequence (comma-separated, 1-indexed, e.g. 3, 1, 2, 4)
      </label>
      <input value={order} onChange={e => setOrder(e.target.value)} placeholder="e.g. 3, 1, 2, 4"
        style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      <RunButton onClick={run} disabled={state.loading || !item || !order.trim()} label={state.loading ? "Reordering…" : "Reorder Pages"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function RotatePanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [angle, setAngle] = useState<90 | 180 | 270>(90);
  const [pages, setPages] = useState("all");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("angle", String(angle));
    form.append("pages", pages);
    await doPost("rotate-pdf", form, setState, `PDF rotated ${angle}°`, "rotated.pdf");
  };

  return (
    <div>
      <SectionHeader label="Rotate PDF" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF to rotate" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Rotation Angle</label>
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        {([90, 180, 270] as const).map(a => (
          <button key={a} onClick={() => setAngle(a)} style={{
            flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
            background: angle === a ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
            border: `1px solid ${angle === a ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
            color: angle === a ? "var(--accent-orange)" : "var(--text-secondary)",
          }}>{a}° Clockwise</button>
        ))}
      </div>
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Pages (e.g. all, 1, 1-3)</label>
      <input value={pages} onChange={e => setPages(e.target.value)}
        style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Rotating…" : "Rotate PDF"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function CropPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [left, setLeft] = useState(20);
  const [top, setTop] = useState(20);
  const [right, setRight] = useState(20);
  const [bottom, setBottom] = useState(20);
  const [pages, setPages] = useState("all");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("left", String(left));
    form.append("top", String(top));
    form.append("right", String(right));
    form.append("bottom", String(bottom));
    form.append("pages", pages);
    await doPost("crop-pdf", form, setState, "PDF cropped", "cropped.pdf");
  };

  return (
    <div>
      <SectionHeader label="Crop PDF" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF to crop" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Left margin (pts)</label>
          <input type="number" value={left} onChange={e => setLeft(Number(e.target.value))} style={{ width: "100%", padding: "6px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)" }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Top margin (pts)</label>
          <input type="number" value={top} onChange={e => setTop(Number(e.target.value))} style={{ width: "100%", padding: "6px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)" }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Right margin (pts)</label>
          <input type="number" value={right} onChange={e => setRight(Number(e.target.value))} style={{ width: "100%", padding: "6px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)" }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Bottom margin (pts)</label>
          <input type="number" value={bottom} onChange={e => setBottom(Number(e.target.value))} style={{ width: "100%", padding: "6px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)" }} />
        </div>
      </div>
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Cropping…" : "Crop PDF"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function ResizePanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [size, setSize] = useState("A4");
  const [pages, setPages] = useState("all");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("target_size", size);
    form.append("pages", pages);
    await doPost("resize-pdf", form, setState, `PDF resized to ${size}`, `resized_${size.toLowerCase()}.pdf`);
  };

  return (
    <div>
      <SectionHeader label="Resize PDF" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF to resize" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Standard Paper Size</label>
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        {["A4", "Letter", "A3", "Legal"].map(s => (
          <button key={s} onClick={() => setSize(s)} style={{
            flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
            background: size === s ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
            border: `1px solid ${size === s ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
            color: size === s ? "var(--accent-orange)" : "var(--text-secondary)",
          }}>{s}</button>
        ))}
      </div>
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Resizing…" : `Resize to ${size}`} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function AddBlankPagePanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [position, setPosition] = useState("end");
  const [targetPage, setTargetPage] = useState(1);
  const [pageSize, setPageSize] = useState("A4");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("position", position);
    form.append("target_page", String(targetPage));
    form.append("page_size", pageSize);
    await doPost("add-blank-page", form, setState, "Blank page inserted", "with_blank_page.pdf");
  };

  return (
    <div>
      <SectionHeader label="Add Blank Page" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        {["start", "end", "after"].map(p => (
          <button key={p} onClick={() => setPosition(p)} style={{
            flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer", textTransform: "capitalize",
            background: position === p ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
            border: `1px solid ${position === p ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
            color: position === p ? "var(--accent-orange)" : "var(--text-secondary)",
          }}>{p === "after" ? "After Page #" : p}</button>
        ))}
      </div>
      {position === "after" && (
        <input type="number" value={targetPage} min={1} onChange={e => setTargetPage(Number(e.target.value))}
          style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      )}
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Adding…" : "Add Blank Page"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function DuplicatePagePanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [count, setCount] = useState(1);
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("page_num", String(pageNum));
    form.append("count", String(count));
    await doPost("duplicate-page", form, setState, "Page duplicated", "page_duplicated.pdf");
  };

  return (
    <div>
      <SectionHeader label="Duplicate Page" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 10 }}>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Page Number</label>
          <input type="number" value={pageNum} min={1} onChange={e => setPageNum(Number(e.target.value))} style={{ width: "100%", padding: "6px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)" }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Copies</label>
          <input type="number" value={count} min={1} max={50} onChange={e => setCount(Number(e.target.value))} style={{ width: "100%", padding: "6px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)" }} />
        </div>
      </div>
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Duplicating…" : "Duplicate Page"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// 2. CONVERT PANELS (Fixes BUG A — PDF → Images)
// ═══════════════════════════════════════════════════════════════════════════

function PDFToImagesPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [fmtChoice, setFmtChoice] = useState<"PNG" | "JPG">("PNG");
  const [pages, setPages] = useState("all");
  const [dpi, setDpi] = useState(150);
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("fmt", fmtChoice);
    form.append("pages", pages);
    form.append("dpi", String(dpi));

    const isSingle = pages !== "all" && !pages.includes(",") && !pages.includes("-");
    const outName = isSingle ? `page_${pages}.${fmtChoice.toLowerCase()}` : "pdf_images.zip";
    await doPost("pdf-to-images", form, setState, "PDF rasterised successfully (Local PyMuPDF)", outName);
  };

  return (
    <div>
      <SectionHeader label="PDF → Images (High-Resolution Local Rasterisation)" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF to convert to images" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>IMAGE FORMAT</label>
          <div style={{ display: "flex", gap: 6 }}>
            {(["PNG", "JPG"] as const).map(f => (
              <button key={f} onClick={() => setFmtChoice(f)} style={{
                flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
                background: fmtChoice === f ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
                border: `1px solid ${fmtChoice === f ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
                color: fmtChoice === f ? "var(--accent-orange)" : "var(--text-secondary)",
              }}>{f}</button>
            ))}
          </div>
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>RESOLUTION (DPI)</label>
          <div style={{ display: "flex", gap: 6 }}>
            {[100, 150, 300].map(d => (
              <button key={d} onClick={() => setDpi(d)} style={{
                flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
                background: dpi === d ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
                border: `1px solid ${dpi === d ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
                color: dpi === d ? "var(--accent-orange)" : "var(--text-secondary)",
              }}>{d}</button>
            ))}
          </div>
        </div>
      </div>
      <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>PAGES (e.g. all, 1, 1-3, 5)</label>
      <input value={pages} onChange={e => setPages(e.target.value)}
        style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Rendering Images…" : "Convert to Images"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function ImagesToPDFPanel() {
  const [items, setItems] = useState<FileItem[]>([]);
  const [state, setState] = useState<OpState>(initState());

  const addFiles = (files: File[]) => {
    const imgs = files.filter(f => f.type.startsWith("image/") || /\.(png|jpe?g|webp|gif|bmp)$/i.test(f.name));
    if (!imgs.length) { setState({ ...initState(), error: "Please select images (PNG/JPG/WebP)" }); return; }
    setItems(prev => [...prev, ...imgs.map(f => ({ id: uid(), file: f, name: f.name, size: f.size }))]);
  };

  const run = async () => {
    if (!items.length) return;
    const form = new FormData();
    items.forEach(it => form.append("files", it.file, it.name));
    await doPost("images-to-pdf", form, setState, "PDF created from images", "images_combined.pdf");
  };

  return (
    <div>
      <SectionHeader label="Images → PDF" />
      <DropZone accept="image/*,.png,.jpg,.jpeg,.webp" multiple onFiles={addFiles}
        label="Drop images here" hint="PNG / JPG / WebP • Order shown below is page order" />
      {items.map((it, idx) => (
        <FileListItem key={it.id} item={it} dragHandle extra={`Page ${idx + 1}`}
          onRemove={() => setItems(p => p.filter(x => x.id !== it.id))} />
      ))}
      <RunButton onClick={run} disabled={state.loading || !items.length} label={state.loading ? "Creating PDF…" : `Create PDF (${items.length} images)`} />
      <StatePanel state={state} onReset={() => { setItems([]); setState(initState()); }} />
    </div>
  );
}

function GenericConvertPanel({
  endpoint,
  title,
  accept,
  dropLabel,
  hint,
  outFilename,
}: {
  endpoint: string;
  title: string;
  accept: string;
  dropLabel: string;
  hint?: string;
  outFilename: string;
}) {
  const [item, setItem] = useState<FileItem | null>(null);
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    await doPost(endpoint, form, setState, "Converted successfully", outFilename);
  };

  return (
    <div>
      <SectionHeader label={title} />
      {!item ? (
        <DropZone accept={accept} onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label={dropLabel} hint={hint} />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Converting…" : "Convert Document"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// 3. OPTIMIZE (Fixes BUG B — Compress PDF Size Reporting)
// ═══════════════════════════════════════════════════════════════════════════

function CompressPDFPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [level, setLevel] = useState<"low" | "medium" | "high">("medium");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) { setState({ ...initState(), error: "No file selected" }); return; }
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("level", level);

    setState({ loading: true, error: null, success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
    try {
      const res = await fetch(`${API}/compress`, { method: "POST", body: form });
      if (!res.ok) {
        let msg = `Server error (${res.status})`;
        try { const j = await res.json(); msg = j.detail || msg; } catch {}
        setState({ loading: false, error: msg, success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      // Extract accurate byte counts from headers or blob fallback
      const headerOrig = Number(res.headers.get("X-Original-Size"));
      const headerOut = Number(res.headers.get("X-Output-Size"));

      const origBytes = (!isNaN(headerOrig) && headerOrig > 0) ? headerOrig : item.size;
      const outBytes = (!isNaN(headerOut) && headerOut > 0) ? headerOut : blob.size;

      let reductionLabel = "Reduction";
      let reductionVal = "0.0%";

      if (origBytes > 0 && outBytes > 0) {
        if (outBytes < origBytes) {
          const diffPct = ((origBytes - outBytes) / origBytes) * 100.0;
          reductionVal = `${diffPct.toFixed(1)}%`;
        } else if (outBytes > origBytes) {
          reductionLabel = "File size";
          const diffPct = ((outBytes - origBytes) / origBytes) * 100.0;
          reductionVal = `Increased by ${diffPct.toFixed(1)}%`;
        } else {
          reductionVal = "0.0% (already optimized)";
        }
      }

      setState({
        loading: false, error: null, success: "PDF optimised successfully",
        downloadUrl: url, downloadName: "compressed.pdf",
        extraInfo: {
          "Original size": fmt(origBytes),
          "Output size": fmt(outBytes),
          [reductionLabel]: reductionVal,
        },
      });
    } catch (err: any) {
      setState({ loading: false, error: err.message || "Network error", success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
    }
  };

  return (
    <div>
      <SectionHeader label="Compress PDF (Lossless & High-Efficiency Optimisation)" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF to optimise" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>OPTIMISATION LEVEL</label>
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        {(["low", "medium", "high"] as const).map(l => (
          <button key={l} onClick={() => setLevel(l)} style={{
            flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer", fontWeight: 600,
            background: level === l ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
            border: `1px solid ${level === l ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
            color: level === l ? "var(--accent-orange)" : "var(--text-secondary)",
            textTransform: "capitalize",
          }}>{l}</button>
        ))}
      </div>
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Optimising…" : "Compress PDF"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function CompressImagePanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [quality, setQuality] = useState(70);
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("quality", String(quality));
    await doPost("compress-image", form, setState, "Image compressed", "compressed_image.jpg", (_, blob) => ({
      "Original size": fmt(item.size),
      "Compressed size": fmt(blob.size),
      "Reduction": `${Math.max(0, (((item.size - blob.size) / item.size) * 100)).toFixed(1)}%`,
    }));
  };

  return (
    <div>
      <SectionHeader label="Compress Image" />
      {!item ? (
        <DropZone accept="image/*" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop image to compress" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Quality: {quality}%</label>
      <input type="range" min={10} max={95} value={quality} onChange={e => setQuality(Number(e.target.value))} style={{ width: "100%", marginBottom: 10 }} />
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Compressing…" : "Compress Image"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// 4. SECURITY PANELS
// ═══════════════════════════════════════════════════════════════════════════

function EncryptPDFPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [password, setPassword] = useState("");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item || !password) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("password", password);
    await doPost("encrypt", form, setState, "PDF encrypted with AES-256", "encrypted.pdf");
  };

  return (
    <div>
      <SectionHeader label="Encrypt PDF / Add Password" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF to encrypt" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Set Document Password</label>
      <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter strong password"
        style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      <RunButton onClick={run} disabled={state.loading || !item || !password.trim()} label={state.loading ? "Encrypting…" : "Encrypt PDF (AES-256)"} />
      <StatePanel state={state} onReset={() => { setItem(null); setPassword(""); setState(initState()); }} />
    </div>
  );
}

function RemovePasswordPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [password, setPassword] = useState("");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item || !password) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("password", password);
    await doPost("remove-password", form, setState, "Password removed — document unlocked", "decrypted.pdf");
  };

  return (
    <div>
      <SectionHeader label="Remove Password (Decrypt PDF)" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop encrypted PDF here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Current Document Password</label>
      <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter existing password"
        style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      <RunButton onClick={run} disabled={state.loading || !item || !password.trim()} label={state.loading ? "Decrypting…" : "Remove Password"} />
      <StatePanel state={state} onReset={() => { setItem(null); setPassword(""); setState(initState()); }} />
    </div>
  );
}

function SecurityInspectorPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    await doJsonPost("security-info", form, setState, data => ({
      success: "Security inspection complete",
      extraInfo: {
        "Encrypted": data.encrypted ? "Yes" : "No",
        "Page count": String(data.page_count),
        "Active JavaScript": data.javascript_detected ? "DETECTED (Warning)" : "None detected",
        "Form fields": String(data.form_fields_count),
        "Embedded files": String(data.embedded_files_count),
        "Metadata present": data.metadata_present ? "Yes" : "Clean",
        "Recommendation": data.security_recommendation,
      },
    }));
  };

  return (
    <div>
      <SectionHeader label="PDF Security Inspector" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF to inspect security" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Inspecting…" : "Inspect Security"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// 5. EDIT & SIGN PANELS
// ═══════════════════════════════════════════════════════════════════════════

function WatermarkPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [text, setText] = useState("CONFIDENTIAL");
  const [angle, setAngle] = useState(45);
  const [opacity, setOpacity] = useState(0.3);
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("text", text);
    form.append("angle", String(angle));
    form.append("opacity", String(opacity));
    await doPost("watermark", form, setState, "Watermark stamped on PDF", "watermarked.pdf");
  };

  return (
    <div>
      <SectionHeader label="Watermark PDF" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Watermark Text</label>
      <input value={text} onChange={e => setText(e.target.value)}
        style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Angle ({angle}°)</label>
          <input type="range" min={0} max={90} step={15} value={angle} onChange={e => setAngle(Number(e.target.value))} style={{ width: "100%" }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Opacity ({Math.round(opacity * 100)}%)</label>
          <input type="range" min={0.1} max={0.9} step={0.1} value={opacity} onChange={e => setOpacity(Number(e.target.value))} style={{ width: "100%" }} />
        </div>
      </div>
      <RunButton onClick={run} disabled={state.loading || !item || !text.trim()} label={state.loading ? "Watermarking…" : "Add Watermark"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function PageNumbersPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [position, setPosition] = useState("bottom-center");
  const [template, setTemplate] = useState("Page {page} of {total}");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("position", position);
    form.append("template", template);
    await doPost("page-numbers", form, setState, "Page numbers added", "numbered.pdf");
  };

  return (
    <div>
      <SectionHeader label="Page Numbers" />
      {!item ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop a PDF here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Position</label>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6, marginBottom: 10 }}>
        {["bottom-left", "bottom-center", "bottom-right", "top-center", "top-right"].map(pos => (
          <button key={pos} onClick={() => setPosition(pos)} style={{
            padding: "6px", borderRadius: 5, fontSize: 11, cursor: "pointer",
            background: position === pos ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
            border: `1px solid ${position === pos ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
            color: position === pos ? "var(--accent-orange)" : "var(--text-secondary)",
          }}>{pos}</button>
        ))}
      </div>
      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Format</label>
      <input value={template} onChange={e => setTemplate(e.target.value)}
        style={{ width: "100%", padding: "7px 10px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)", marginBottom: 10 }} />
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Adding…" : "Add Page Numbers"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function VisualSignaturePanel() {
  const [docFile, setDocFile] = useState<FileItem | null>(null);
  const [sigMode, setSigMode] = useState<"draw" | "upload">("draw");
  const [sigUpload, setSigUpload] = useState<File | null>(null);
  const [pageNum, setPageNum] = useState(1);
  const [posX, setPosX] = useState(350);
  const [posY, setPosY] = useState(700);
  const [sigWidth, setSigWidth] = useState(180);
  const [sigHeight, setSigHeight] = useState(70);
  const [state, setState] = useState<OpState>(initState());

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const isDrawing = useRef(false);

  // Drawing canvas handlers
  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    isDrawing.current = true;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing.current) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#002060"; // signature dark blue ink
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.stroke();
  };

  const stopDrawing = () => {
    isDrawing.current = false;
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);
  };

  const run = async () => {
    if (!docFile) return;

    let sigBlob: Blob | null = null;
    if (sigMode === "draw") {
      const canvas = canvasRef.current;
      if (!canvas) return;
      sigBlob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
    } else {
      sigBlob = sigUpload;
    }

    if (!sigBlob) {
      setState({ ...initState(), error: "Please provide a signature (drawn or uploaded)" });
      return;
    }

    const form = new FormData();
    form.append("file", docFile.file, docFile.name);
    form.append("signature", sigBlob, "signature.png");
    form.append("page_num", String(pageNum));
    form.append("x", String(posX));
    form.append("y", String(posY));
    form.append("width", String(sigWidth));
    form.append("height", String(sigHeight));

    await doPost("visual-signature", form, setState, "Visual signature placed on PDF", "signed.pdf");
  };

  return (
    <div>
      <SectionHeader label="Visual Signature (Stamp Visual Sign-off)" />
      {!docFile ? (
        <DropZone accept=".pdf,application/pdf" onFiles={([f]) => setDocFile({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop PDF document to sign" />
      ) : (
        <FileListItem item={docFile} onRemove={() => setDocFile(null)} />
      )}

      <div style={{
        padding: "8px 12px", background: "rgba(249,115,22,0.06)", border: "1px solid rgba(249,115,22,0.2)",
        borderRadius: 6, fontSize: 11, color: "var(--accent-orange)", marginBottom: 12, lineHeight: 1.4,
      }}>
        Notice: Visual Signature stamps an authentic handwritten image representation onto your document. It is not an X.509 cryptographic certificate.
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        <button onClick={() => setSigMode("draw")} style={{
          flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
          background: sigMode === "draw" ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
          border: `1px solid ${sigMode === "draw" ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
          color: sigMode === "draw" ? "var(--accent-orange)" : "var(--text-secondary)",
        }}>Draw Signature</button>
        <button onClick={() => setSigMode("upload")} style={{
          flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
          background: sigMode === "upload" ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
          border: `1px solid ${sigMode === "upload" ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
          color: sigMode === "upload" ? "var(--accent-orange)" : "var(--text-secondary)",
        }}>Upload Signature Image</button>
      </div>

      {sigMode === "draw" ? (
        <div style={{ marginBottom: 10 }}>
          <canvas
            ref={canvasRef}
            width={400}
            height={120}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            style={{
              background: "#ffffff", border: "1px solid var(--border)",
              borderRadius: 6, width: "100%", height: 120, cursor: "crosshair",
            }}
          />
          <button onClick={clearCanvas} style={{
            fontSize: 11, color: "var(--text-muted)", background: "transparent",
            border: "none", cursor: "pointer", marginTop: 4, textDecoration: "underline",
          }}>Clear signature canvas</button>
        </div>
      ) : (
        <div style={{ marginBottom: 10 }}>
          <DropZone accept="image/png,image/jpeg" onFiles={([f]) => setSigUpload(f)} label="Drop signature PNG/JPG" hint="Transparent PNG recommended" />
          {sigUpload && <div style={{ fontSize: 11, color: "var(--accent-green)", marginBottom: 8 }}>Loaded: {sigUpload.name}</div>}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 10 }}>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Target Page</label>
          <input type="number" min={1} value={pageNum} onChange={e => setPageNum(Number(e.target.value))} style={{ width: "100%", padding: "6px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)" }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>X Position (pts)</label>
          <input type="number" value={posX} onChange={e => setPosX(Number(e.target.value))} style={{ width: "100%", padding: "6px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)" }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)" }}>Y Position (pts)</label>
          <input type="number" value={posY} onChange={e => setPosY(Number(e.target.value))} style={{ width: "100%", padding: "6px", fontSize: 12, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 5, color: "var(--text-primary)" }} />
        </div>
      </div>

      <RunButton onClick={run} disabled={state.loading || !docFile} label={state.loading ? "Placing Signature…" : "Place Visual Signature"} />
      <StatePanel state={state} onReset={() => { setDocFile(null); clearCanvas(); setSigUpload(null); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// 6. OFFICE PANELS: Word, PowerPoint, Spreadsheets
// ═══════════════════════════════════════════════════════════════════════════

function WordToolsPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [action, setAction] = useState<"stats" | "tables" | "markdown">("stats");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);

    if (action === "stats") {
      await doJsonPost("docx-stats", form, setState, data => ({
        success: "Word metrics analyzed",
        extraInfo: {
          "Title": data.title,
          "Author": data.author,
          "Word count": String(data.word_count),
          "Paragraphs": String(data.paragraph_count),
          "Tables": String(data.table_count),
          "Sections": String(data.section_count),
        },
      }));
    } else if (action === "tables") {
      await doJsonPost("docx-extract-tables", form, setState, data => ({
        success: `Extracted ${data.table_count} table(s)`,
        extraInfo: {
          "Total Tables": String(data.table_count),
          "Details": data.tables.map((t: any) => `Table #${t.table_index}: ${t.row_count} rows × ${t.col_count} cols`).join(" | "),
        },
      }));
    } else {
      await doPost("docx-to-markdown", form, setState, "Word converted to Markdown", "document.md");
    }
  };

  return (
    <div>
      <SectionHeader label="Word Document Tools (.docx)" />
      {!item ? (
        <DropZone accept=".docx,.doc" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop Word document (.docx) here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        {[
          { id: "stats", label: "Document Stats" },
          { id: "tables", label: "Extract Tables" },
          { id: "markdown", label: "DOCX → Markdown" },
        ].map(a => (
          <button key={a.id} onClick={() => setAction(a.id as any)} style={{
            flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
            background: action === a.id ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
            border: `1px solid ${action === a.id ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
            color: action === a.id ? "var(--accent-orange)" : "var(--text-secondary)",
          }}>{a.label}</button>
        ))}
      </div>
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Processing…" : "Run Operation"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function PowerPointToolsPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    await doJsonPost("pptx-stats", form, setState, data => ({
      success: "Presentation analyzed",
      extraInfo: {
        "Slide count": String(data.slide_count),
        "Total words": String(data.total_words),
        "Slides with speaker notes": String(data.slides_with_notes),
      },
    }));
  };

  return (
    <div>
      <SectionHeader label="PowerPoint Tools (.pptx)" />
      {!item ? (
        <DropZone accept=".pptx,.ppt" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop PowerPoint presentation here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Analyzing…" : "Extract Presentation Stats"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function SpreadsheetToolsPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [action, setAction] = useState<"preview" | "to-csv">("preview");
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);

    if (action === "preview") {
      await doJsonPost("spreadsheet-preview", form, setState, data => ({
        success: "Spreadsheet structure loaded",
        extraInfo: {
          "Worksheets": data.sheets.map((s: any) => `${s.name} (${s.max_row} rows × ${s.max_column} cols)`).join(" • "),
        },
      }));
    } else {
      await doPost("xlsx-to-csv", form, setState, "Converted to CSV", "sheets.csv");
    }
  };

  return (
    <div>
      <SectionHeader label="Spreadsheet Tools (.xlsx / .csv)" />
      {!item ? (
        <DropZone accept=".xlsx,.xls" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop Excel workbook here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
        <button onClick={() => setAction("preview")} style={{
          flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
          background: action === "preview" ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
          border: `1px solid ${action === "preview" ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
          color: action === "preview" ? "var(--accent-orange)" : "var(--text-secondary)",
        }}>Preview Structure</button>
        <button onClick={() => setAction("to-csv")} style={{
          flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
          background: action === "to-csv" ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
          border: `1px solid ${action === "to-csv" ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
          color: action === "to-csv" ? "var(--accent-orange)" : "var(--text-secondary)",
        }}>Export to CSV</button>
      </div>
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Processing…" : "Execute"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// 7. IMAGE TOOLS PANELS
// ═══════════════════════════════════════════════════════════════════════════

function ImageToolsPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [targetFmt, setTargetFmt] = useState<"PNG" | "JPG" | "WEBP">("PNG");
  const [angle, setAngle] = useState(0);
  const [state, setState] = useState<OpState>(initState());

  const runConvert = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("target_fmt", targetFmt);
    await doPost("convert-image", form, setState, `Image converted to ${targetFmt}`, `image.${targetFmt.toLowerCase()}`);
  };

  const runRotate = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    form.append("angle", String(angle));
    await doPost("rotate-flip-image", form, setState, `Image rotated ${angle}°`, "rotated_image.png");
  };

  return (
    <div>
      <SectionHeader label="Local Image Converter & Transform" />
      {!item ? (
        <DropZone accept="image/*" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop image here" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>CONVERT FORMAT</label>
        <div style={{ display: "flex", gap: 6 }}>
          {(["PNG", "JPG", "WEBP"] as const).map(f => (
            <button key={f} onClick={() => setTargetFmt(f)} style={{
              flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
              background: targetFmt === f ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
              border: `1px solid ${targetFmt === f ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
              color: targetFmt === f ? "var(--accent-orange)" : "var(--text-secondary)",
            }}>{f}</button>
          ))}
        </div>
        <RunButton onClick={runConvert} disabled={state.loading || !item} label={state.loading ? "Converting…" : `Convert to ${targetFmt}`} />
      </div>

      <div>
        <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>ROTATE IMAGE</label>
        <div style={{ display: "flex", gap: 6 }}>
          {[90, 180, 270].map(a => (
            <button key={a} onClick={() => setAngle(a)} style={{
              flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
              background: angle === a ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
              border: `1px solid ${angle === a ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
              color: angle === a ? "var(--accent-orange)" : "var(--text-secondary)",
            }}>{a}°</button>
          ))}
        </div>
        <RunButton onClick={runRotate} disabled={state.loading || !item || angle === 0} label={state.loading ? "Rotating…" : `Rotate ${angle}°`} />
      </div>

      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// 8. OCR PANELS (with Tesseract health status)
// ═══════════════════════════════════════════════════════════════════════════

function OCRPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [ocrEngineAvailable, setOcrEngineAvailable] = useState<boolean | null>(null);
  const [ocrMsg, setOcrMsg] = useState<string>("");
  const [ocrLanguages, setOcrLanguages] = useState<string[]>([]);
  const [pdfMode, setPdfMode] = useState<"text" | "searchable">("text");
  const [pages, setPages] = useState<string>("all");
  const [state, setState] = useState<OpState>(initState());

  useEffect(() => {
    fetch(`${API}/ocr-status`)
      .then(res => res.json())
      .then(data => {
        setOcrEngineAvailable(data.available);
        setOcrMsg(data.message);
        if (Array.isArray(data.languages)) {
          setOcrLanguages(data.languages);
        }
      })
      .catch(() => {
        setOcrEngineAvailable(false);
        setOcrMsg("Tesseract OCR is not available. Install Tesseract or configure TESSERACT_CMD.");
      });
  }, []);

  const isPdf = item ? item.name.toLowerCase().endsWith(".pdf") : false;

  const run = async () => {
    if (!item || ocrEngineAvailable === false) return;

    if (isPdf && pdfMode === "searchable") {
      const form = new FormData();
      form.append("file", item.file, item.name);
      form.append("pages", pages.trim() || "all");
      const outName = `${item.name.replace(/\.[^/.]+$/, "")}_searchable.pdf`;
      await doPost("searchable-pdf", form, setState, "Searchable PDF generated", outName);
      return;
    }

    // Text OCR execution (Image or PDF)
    setState({ loading: true, error: null, success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
    try {
      const endpoint = isPdf ? "ocr-pdf" : "ocr-image";
      const form = new FormData();
      form.append("file", item.file, item.name);
      if (isPdf) {
        form.append("pages", pages.trim() || "all");
      }

      const res = await fetch(`${API}/${endpoint}`, { method: "POST", body: form });
      if (!res.ok) {
        let msg = `Server error (${res.status})`;
        try {
          const j = await res.json();
          msg = j.detail || msg;
        } catch {}
        setState({ loading: false, error: msg, success: null, downloadUrl: null, downloadName: null, extraInfo: {} });
        return;
      }

      const data = await res.json();
      const fullText = (isPdf ? data.full_text : data.text) || "";
      const textBlob = new Blob([fullText], { type: "text/plain;charset=utf-8" });
      const downloadUrl = URL.createObjectURL(textBlob);
      const downloadName = `${item.name.replace(/\.[^/.]+$/, "")}_ocr.txt`;

      const extraInfo: Record<string, string> = {
        "Extracted Text": fullText ? (fullText.slice(0, 300) + (fullText.length > 300 ? "…" : "")) : "[No text detected]",
        "Character Count": String(fullText.length),
      };
      if (isPdf && data.total_pages_ocr !== undefined) {
        extraInfo["Pages OCRed"] = String(data.total_pages_ocr);
      }

      setState({
        loading: false,
        error: null,
        success: "OCR completed successfully",
        downloadUrl,
        downloadName,
        extraInfo,
        rawJson: data,
      });
    } catch (err: any) {
      setState({
        loading: false,
        error: err.message || "Failed to execute OCR",
        success: null,
        downloadUrl: null,
        downloadName: null,
        extraInfo: {},
      });
    }
  };

  return (
    <div>
      <SectionHeader label="OCR Tools (Local Tesseract Engine)" />

      {ocrEngineAvailable === false && (
        <div style={{
          padding: "10px 12px", background: "rgba(249,115,22,0.08)", border: "1px solid rgba(249,115,22,0.3)",
          borderRadius: 6, fontSize: 12, color: "var(--accent-orange)", marginBottom: 12, lineHeight: 1.4,
        }}>
          <strong>Local Tesseract Engine Status:</strong> {ocrMsg || "Tesseract OCR is not available. Install Tesseract or configure TESSERACT_CMD."}
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
            Install Tesseract on this server or configure TESSERACT_CMD to unlock optical character recognition.
          </div>
        </div>
      )}

      {ocrEngineAvailable === true && (
        <div style={{
          padding: "8px 12px", background: "rgba(34,197,94,0.06)", border: "1px solid rgba(34,197,94,0.25)",
          borderRadius: 6, fontSize: 11, color: "var(--accent-green)", marginBottom: 12, display: "flex",
          alignItems: "center", justifyContent: "space-between",
        }}>
          <span><strong>Local Tesseract Engine:</strong> Ready</span>
          <span style={{ color: "var(--text-muted)", fontSize: 11 }}>
            Languages: {ocrLanguages.length > 0 ? ocrLanguages.join(", ") : "eng"}
          </span>
        </div>
      )}

      {!item ? (
        <DropZone accept=".pdf,image/*" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop PDF or image for OCR" />
      ) : (
        <FileListItem item={item} onRemove={() => { setItem(null); setState(initState()); }} />
      )}

      {isPdf && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>OCR Operation</label>
          <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
            <button
              onClick={() => setPdfMode("text")}
              style={{
                flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
                background: pdfMode === "text" ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
                border: `1px solid ${pdfMode === "text" ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
                color: pdfMode === "text" ? "var(--accent-orange)" : "var(--text-secondary)",
              }}
            >
              Extract Text (.txt)
            </button>
            <button
              onClick={() => setPdfMode("searchable")}
              style={{
                flex: 1, padding: "6px", borderRadius: 5, fontSize: 12, cursor: "pointer",
                background: pdfMode === "searchable" ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
                border: `1px solid ${pdfMode === "searchable" ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
                color: pdfMode === "searchable" ? "var(--accent-orange)" : "var(--text-secondary)",
              }}
            >
              Searchable PDF (.pdf)
            </button>
          </div>

          <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Pages to Process</label>
          <input
            type="text"
            value={pages}
            onChange={e => setPages(e.target.value)}
            placeholder="all (or e.g. 1-3, 5)"
            style={{
              width: "100%", padding: "7px 10px", fontSize: 12, borderRadius: 5,
              background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-primary)",
            }}
          />
        </div>
      )}

      <RunButton
        onClick={run}
        disabled={state.loading || !item || ocrEngineAvailable === false}
        label={
          state.loading
            ? "Running Local OCR…"
            : (isPdf && pdfMode === "searchable" ? "Generate Searchable PDF" : "Run Local OCR")
        }
      />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// 9. ANALYZE PANELS: Document Inspector & Compare
// ═══════════════════════════════════════════════════════════════════════════

function DocumentInspectorPanel() {
  const [item, setItem] = useState<FileItem | null>(null);
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!item) return;
    const form = new FormData();
    form.append("file", item.file, item.name);
    await doJsonPost("inspect", form, setState, data => {
      const extra: Record<string, string> = {
        "Category": data.category,
        "File Size": data.formatted_size,
      };
      if (data.details) {
        Object.entries(data.details).forEach(([k, v]) => {
          if (Array.isArray(v)) extra[k] = v.join(", ");
          else extra[k] = String(v);
        });
      }
      return { success: "Document analyzed", extraInfo: extra };
    });
  };

  return (
    <div>
      <SectionHeader label="Document Inspector (Deterministic Offline Analysis)" />
      {!item ? (
        <DropZone accept="*/*" onFiles={([f]) => setItem({ id: uid(), file: f, name: f.name, size: f.size })}
          label="Drop any document (PDF, Word, PPT, Excel, Image, Text)" />
      ) : (
        <FileListItem item={item} onRemove={() => setItem(null)} />
      )}
      <RunButton onClick={run} disabled={state.loading || !item} label={state.loading ? "Inspecting…" : "Inspect Document"} />
      <StatePanel state={state} onReset={() => { setItem(null); setState(initState()); }} />
    </div>
  );
}

function CompareDocumentsPanel() {
  const [f1, setF1] = useState<FileItem | null>(null);
  const [f2, setF2] = useState<FileItem | null>(null);
  const [state, setState] = useState<OpState>(initState());

  const run = async () => {
    if (!f1 || !f2) return;
    const form = new FormData();
    form.append("file1", f1.file, f1.name);
    form.append("file2", f2.file, f2.name);
    await doJsonPost("compare", form, setState, data => ({
      success: `Similarity: ${data.similarity_pct}% ${data.identical ? "(Identical)" : ""}`,
      extraInfo: {
        "File 1": data.file1,
        "File 2": data.file2,
        "Similarity Score": `${data.similarity_pct}%`,
        "Lines Added": String(data.added_lines_count),
        "Lines Removed": String(data.removed_lines_count),
        "Sample Diff": data.diff_text ? (data.diff_text.slice(0, 200) + "…") : "No line differences",
      },
    }));
  };

  return (
    <div>
      <SectionHeader label="Compare Documents (Deterministic Text & Structure Diff)" />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 12 }}>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>ORIGINAL DOCUMENT</label>
          {!f1 ? (
            <DropZone accept=".pdf,.docx,.txt" onFiles={([f]) => setF1({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop Document #1" />
          ) : (
            <FileListItem item={f1} onRemove={() => setF1(null)} />
          )}
        </div>
        <div>
          <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>MODIFIED DOCUMENT</label>
          {!f2 ? (
            <DropZone accept=".pdf,.docx,.txt" onFiles={([f]) => setF2({ id: uid(), file: f, name: f.name, size: f.size })} label="Drop Document #2" />
          ) : (
            <FileListItem item={f2} onRemove={() => setF2(null)} />
          )}
        </div>
      </div>
      <RunButton onClick={run} disabled={state.loading || !f1 || !f2} label={state.loading ? "Comparing…" : "Compare Documents"} />
      <StatePanel state={state} onReset={() => { setF1(null); setF2(null); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// 10. BATCH PROCESSING PANEL
// ═══════════════════════════════════════════════════════════════════════════

function getBatchFileBadgeAndIcon(filename: string) {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  if (ext === "pdf") {
    return {
      badge: "PDF",
      badgeColor: "var(--accent-orange)",
      badgeBg: "rgba(249,115,22,0.12)",
      icon: <FileText size={13} color="var(--accent-orange)" />,
    };
  }
  if (["png", "jpg", "jpeg", "webp", "bmp", "tiff", "gif"].includes(ext)) {
    return {
      badge: "IMG",
      badgeColor: "#38bdf8",
      badgeBg: "rgba(56,189,248,0.12)",
      icon: <ImageIcon size={13} color="#38bdf8" />,
    };
  }
  if (["docx", "doc"].includes(ext)) {
    return {
      badge: "DOCX",
      badgeColor: "#818cf8",
      badgeBg: "rgba(129,140,248,0.12)",
      icon: <FileText size={13} color="#818cf8" />,
    };
  }
  if (["xlsx", "xls", "csv"].includes(ext)) {
    return {
      badge: "SHEET",
      badgeColor: "#34d399",
      badgeBg: "rgba(52,211,153,0.12)",
      icon: <FileSpreadsheet size={13} color="#34d399" />,
    };
  }
  if (["txt", "md"].includes(ext)) {
    return {
      badge: "TXT",
      badgeColor: "#facc15",
      badgeBg: "rgba(250,204,21,0.12)",
      icon: <FileCode size={13} color="#facc15" />,
    };
  }
  return {
    badge: ext.toUpperCase().slice(0, 4) || "FILE",
    badgeColor: "var(--text-muted)",
    badgeBg: "rgba(255,255,255,0.05)",
    icon: <FileText size={13} color="var(--text-muted)" />,
  };
}

function BatchProcessingPanel() {
  const [items, setItems] = useState<FileItem[]>([]);
  const [op, setOp] = useState("pdf-to-txt");
  const [state, setState] = useState<OpState>(initState());

  const addFiles = (files: File[]) => {
    setItems(prev => {
      const existingKeys = new Set(prev.map(f => `${f.name}:${f.size}`));
      const newItems: FileItem[] = [];
      for (const f of files) {
        const key = `${f.name}:${f.size}`;
        if (!existingKeys.has(key)) {
          existingKeys.add(key);
          newItems.push({ id: uid(), file: f, name: f.name, size: f.size });
        }
      }
      return [...prev, ...newItems];
    });
  };

  const removeFile = (id: string) => {
    setItems(prev => prev.filter(x => x.id !== id));
  };

  const clearAllFiles = () => {
    setItems([]);
  };

  const run = async () => {
    if (!items.length) return;
    const form = new FormData();
    items.forEach(it => form.append("files", it.file, it.name));
    form.append("operation", op);
    form.append("options", JSON.stringify({ level: "medium", format: "PNG" }));

    await doPost("batch", form, setState, "Batch operation completed", "batch_results.zip", res => ({
      "Total Files": res.headers.get("X-Total-Files") || String(items.length),
      "Completed": res.headers.get("X-Completed-Files") || String(items.length),
      "Failed": res.headers.get("X-Failed-Files") || "0",
    }));
  };

  return (
    <div>
      <SectionHeader label="Batch Document Processing (Multi-File Workflow)" />
      <DropZone
        accept="*/*"
        multiple
        onFiles={addFiles}
        label="Drop multiple documents here"
        hint="Upload multiple PDFs, Office documents, images or text files to batch process"
      />

      {/* Staged files visual container */}
      {items.length === 0 ? (
        <div style={{
          padding: "14px 16px", borderRadius: 6, border: "1px dashed var(--border)",
          background: "var(--bg-card)", textAlign: "center", fontSize: 12,
          color: "var(--text-muted)", marginBottom: 12,
        }}>
          No documents staged
        </div>
      ) : (
        <div style={{ marginBottom: 12 }}>
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            fontSize: 11, color: "var(--text-muted)", marginBottom: 6,
          }}>
            <span>
              <strong style={{ color: "var(--accent-orange)" }}>{items.length}</strong> document(s) staged for batch
            </span>
            <button
              type="button"
              onClick={clearAllFiles}
              style={{
                background: "transparent", border: "none", color: "var(--text-muted)",
                cursor: "pointer", fontSize: 11, padding: "2px 4px", textDecoration: "underline",
              }}
              onMouseEnter={e => { e.currentTarget.style.color = "var(--accent-red)"; }}
              onMouseLeave={e => { e.currentTarget.style.color = "var(--text-muted)"; }}
            >
              Clear all
            </button>
          </div>

          <div style={{
            maxHeight: 220, overflowY: "auto", border: "1px solid var(--border)",
            borderRadius: 6, background: "rgba(0,0,0,0.18)", padding: 6,
          }}>
            {items.map(it => {
              const { badge, badgeColor, badgeBg, icon } = getBatchFileBadgeAndIcon(it.name);
              return (
                <div
                  key={it.id}
                  style={{
                    display: "flex", alignItems: "center", gap: 8, padding: "6px 10px",
                    background: "var(--bg-card)", border: "1px solid var(--border)",
                    borderRadius: 5, marginBottom: 4,
                  }}
                >
                  <span style={{
                    fontSize: 9, fontWeight: 700, padding: "1px 5px", borderRadius: 3,
                    background: badgeBg, color: badgeColor, border: `1px solid ${badgeColor}40`,
                    flexShrink: 0,
                  }}>
                    {badge}
                  </span>
                  <span style={{ flexShrink: 0, display: "flex", alignItems: "center" }}>{icon}</span>
                  <div
                    title={it.name}
                    style={{
                      flex: 1, minWidth: 0, fontSize: 12, color: "var(--text-primary)",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}
                  >
                    {it.name}
                  </div>
                  <span style={{ fontSize: 10, color: "var(--text-muted)", flexShrink: 0, marginRight: 4 }}>
                    {fmt(it.size)}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeFile(it.id)}
                    title={`Remove ${it.name}`}
                    style={{
                      background: "transparent", border: "none", cursor: "pointer",
                      color: "var(--text-muted)", padding: 2, display: "flex",
                      alignItems: "center", borderRadius: 3, flexShrink: 0,
                    }}
                    onMouseEnter={e => { e.currentTarget.style.color = "var(--accent-red)"; }}
                    onMouseLeave={e => { e.currentTarget.style.color = "var(--text-muted)"; }}
                  >
                    <X size={13} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <label style={{ fontSize: 12, color: "var(--text-muted)", display: "block", marginBottom: 4 }}>BATCH OPERATION</label>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 10 }}>
        {[
          { id: "pdf-to-txt", label: "Extract Text (.txt)" },
          { id: "compress-pdf", label: "Compress PDFs" },
          { id: "pdf-to-images", label: "PDF → Images" },
          { id: "remove-metadata", label: "Strip Metadata" },
          { id: "convert-images", label: "Convert Images" },
          { id: "docx-to-txt", label: "DOCX → Text" },
        ].map(o => (
          <button key={o.id} onClick={() => setOp(o.id)} style={{
            padding: "8px", borderRadius: 5, fontSize: 11, cursor: "pointer", textAlign: "left",
            background: op === o.id ? "rgba(249,115,22,0.12)" : "var(--bg-card)",
            border: `1px solid ${op === o.id ? "rgba(249,115,22,0.4)" : "var(--border)"}`,
            color: op === o.id ? "var(--accent-orange)" : "var(--text-secondary)",
          }}>{o.label}</button>
        ))}
      </div>

      <RunButton
        onClick={run}
        disabled={state.loading || items.length === 0}
        label={
          state.loading
            ? "Processing Batch…"
            : (items.length === 0 ? "Process Batch" : `Process Batch (${items.length} files)`)
        }
      />
      <StatePanel state={state} onReset={() => { setItems([]); setState(initState()); }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// REGISTRY OF ALL SUITE CATEGORIES AND TOOLS
// ═══════════════════════════════════════════════════════════════════════════

interface ToolDef {
  id: string;
  category: string;
  label: string;
  icon: React.ReactNode;
}

const CATEGORIES = [
  { id: "organize", label: "Organize" },
  { id: "convert", label: "Convert" },
  { id: "optimize", label: "Optimize" },
  { id: "security", label: "Security" },
  { id: "edit", label: "Edit & Sign" },
  { id: "office", label: "Office Docs" },
  { id: "images", label: "Image Tools" },
  { id: "ocr", label: "OCR" },
  { id: "analyze", label: "Analyze" },
  { id: "batch", label: "Batch" },
];

const TOOLS: ToolDef[] = [
  // Organize
  { id: "merge", category: "organize", label: "Merge PDF", icon: <FileStack size={14} /> },
  { id: "split", category: "organize", label: "Split PDF", icon: <Scissors size={14} /> },
  { id: "extract", category: "organize", label: "Extract Pages", icon: <BookCopy size={14} /> },
  { id: "delete", category: "organize", label: "Delete Pages", icon: <Trash2 size={14} /> },
  { id: "reorder", category: "organize", label: "Reorder Pages", icon: <Layers size={14} /> },
  { id: "rotate", category: "organize", label: "Rotate PDF", icon: <RotateCw size={14} /> },
  { id: "crop", category: "organize", label: "Crop PDF", icon: <Crop size={14} /> },
  { id: "resize", category: "organize", label: "Resize PDF", icon: <Minimize2 size={14} /> },
  { id: "add-blank", category: "organize", label: "Add Blank Page", icon: <FilePlus size={14} /> },
  { id: "duplicate", category: "organize", label: "Duplicate Page", icon: <BookCopy size={14} /> },

  // Convert
  { id: "pdf-to-images", category: "convert", label: "PDF → Images", icon: <ImageDown size={14} /> },
  { id: "images-to-pdf", category: "convert", label: "Images → PDF", icon: <FilePlus size={14} /> },
  { id: "pdf-to-text", category: "convert", label: "PDF → Text", icon: <FileText size={14} /> },
  { id: "pdf-to-markdown", category: "convert", label: "PDF → Markdown", icon: <FileCode size={14} /> },
  { id: "pdf-to-docx", category: "convert", label: "PDF → Word (DOCX)", icon: <FileText size={14} /> },
  { id: "docx-to-pdf", category: "convert", label: "DOCX → PDF", icon: <FileText size={14} /> },
  { id: "docx-to-text", category: "convert", label: "DOCX → Text", icon: <FileText size={14} /> },
  { id: "txt-to-pdf", category: "convert", label: "TXT → PDF", icon: <FileText size={14} /> },
  { id: "txt-to-docx", category: "convert", label: "TXT → DOCX", icon: <FileText size={14} /> },
  { id: "xlsx-to-csv", category: "convert", label: "XLSX → CSV", icon: <FileSpreadsheet size={14} /> },
  { id: "csv-to-xlsx", category: "convert", label: "CSV → XLSX", icon: <FileSpreadsheet size={14} /> },

  // Optimize
  { id: "compress-pdf", category: "optimize", label: "Compress PDF", icon: <Minimize2 size={14} /> },
  { id: "compress-image", category: "optimize", label: "Compress Image", icon: <Minimize2 size={14} /> },

  // Security
  { id: "encrypt-pdf", category: "security", label: "Encrypt PDF", icon: <Key size={14} /> },
  { id: "remove-password", category: "security", label: "Remove Password", icon: <Key size={14} /> },
  { id: "security-inspector", category: "security", label: "Security Inspector", icon: <Shield size={14} /> },

  // Edit & Sign
  { id: "watermark", category: "edit", label: "Watermark", icon: <Type size={14} /> },
  { id: "page-numbers", category: "edit", label: "Page Numbers", icon: <Hash size={14} /> },
  { id: "visual-signature", category: "edit", label: "Visual Signature", icon: <PenTool size={14} /> },

  // Office
  { id: "word-tools", category: "office", label: "Word Tools", icon: <FileText size={14} /> },
  { id: "pptx-tools", category: "office", label: "PowerPoint Tools", icon: <Presentation size={14} /> },
  { id: "spreadsheet-tools", category: "office", label: "Spreadsheet Tools", icon: <TableIcon size={14} /> },

  // Images
  { id: "image-tools", category: "images", label: "Convert & Rotate", icon: <ImageIcon size={14} /> },

  // OCR
  { id: "ocr-suite", category: "ocr", label: "Local OCR Engine", icon: <Eye size={14} /> },

  // Analyze
  { id: "inspector", category: "analyze", label: "Document Inspector", icon: <Search size={14} /> },
  { id: "compare", category: "analyze", label: "Compare Documents", icon: <GitCompare size={14} /> },

  // Batch
  { id: "batch-proc", category: "batch", label: "Batch Processing", icon: <Layers size={14} /> },
];

function ToolPanel({ toolId }: { toolId: string }) {
  switch (toolId) {
    // Organize
    case "merge": return <MergePanel />;
    case "split": return <SplitPanel />;
    case "extract": return <ExtractPanel />;
    case "delete": return <DeletePagesPanel />;
    case "reorder": return <ReorderPanel />;
    case "rotate": return <RotatePanel />;
    case "crop": return <CropPanel />;
    case "resize": return <ResizePanel />;
    case "add-blank": return <AddBlankPagePanel />;
    case "duplicate": return <DuplicatePagePanel />;

    // Convert
    case "pdf-to-images": return <PDFToImagesPanel />;
    case "images-to-pdf": return <ImagesToPDFPanel />;
    case "pdf-to-text": return <GenericConvertPanel endpoint="pdf-to-text" title="PDF → Text" accept=".pdf" dropLabel="Drop text PDF" outFilename="extracted_text.txt" />;
    case "pdf-to-markdown": return <GenericConvertPanel endpoint="pdf-to-markdown" title="PDF → Markdown" accept=".pdf" dropLabel="Drop PDF to convert" outFilename="document.md" />;
    case "pdf-to-docx": return <GenericConvertPanel endpoint="pdf-to-docx" title="PDF → Word (DOCX)" accept=".pdf" dropLabel="Drop PDF to convert" outFilename="document.docx" />;
    case "docx-to-pdf": return <GenericConvertPanel endpoint="docx-to-pdf" title="Word (DOCX) → PDF" accept=".docx" dropLabel="Drop DOCX to convert" outFilename="converted.pdf" />;
    case "docx-to-text": return <GenericConvertPanel endpoint="docx-to-text" title="Word (DOCX) → Text" accept=".docx" dropLabel="Drop DOCX to extract" outFilename="extracted.txt" />;
    case "txt-to-pdf": return <GenericConvertPanel endpoint="txt-to-pdf" title="Plain Text (TXT) → PDF" accept=".txt" dropLabel="Drop TXT file" outFilename="document.pdf" />;
    case "txt-to-docx": return <GenericConvertPanel endpoint="txt-to-docx" title="Plain Text (TXT) → Word (DOCX)" accept=".txt" dropLabel="Drop TXT file" outFilename="document.docx" />;
    case "xlsx-to-csv": return <GenericConvertPanel endpoint="xlsx-to-csv" title="Excel (XLSX) → CSV" accept=".xlsx" dropLabel="Drop XLSX file" outFilename="sheets.csv" />;
    case "csv-to-xlsx": return <GenericConvertPanel endpoint="csv-to-xlsx" title="CSV → Excel (XLSX)" accept=".csv" dropLabel="Drop CSV file" outFilename="spreadsheet.xlsx" />;

    // Optimize
    case "compress-pdf": return <CompressPDFPanel />;
    case "compress-image": return <CompressImagePanel />;

    // Security
    case "encrypt-pdf": return <EncryptPDFPanel />;
    case "remove-password": return <RemovePasswordPanel />;
    case "security-inspector": return <SecurityInspectorPanel />;

    // Edit & Sign
    case "watermark": return <WatermarkPanel />;
    case "page-numbers": return <PageNumbersPanel />;
    case "visual-signature": return <VisualSignaturePanel />;

    // Office
    case "word-tools": return <WordToolsPanel />;
    case "pptx-tools": return <PowerPointToolsPanel />;
    case "spreadsheet-tools": return <SpreadsheetToolsPanel />;

    // Images
    case "image-tools": return <ImageToolsPanel />;

    // OCR
    case "ocr-suite": return <OCRPanel />;

    // Analyze
    case "inspector": return <DocumentInspectorPanel />;
    case "compare": return <CompareDocumentsPanel />;

    // Batch
    case "batch-proc": return <BatchProcessingPanel />;

    default:
      return <MergePanel />;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// MAIN VIEW COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

export default function DocumentToolsView() {
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({
    organize: true,
  });
  const [activeTool, setActiveTool] = useState<string>("merge");

  const toggleCategory = (catId: string) => {
    setOpenCategories(prev => ({
      ...prev,
      [catId]: !prev[catId],
    }));
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div style={{
        padding: "12px 20px", borderBottom: "1px solid var(--border)",
        display: "flex", alignItems: "center", gap: 10, flexShrink: 0,
      }}>
        <FileStack size={16} color="var(--accent-orange)" />
        <div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Document Tools</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Sovereign local document productivity suite · Air-gap compatible
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          <span style={{
            fontSize: 11, color: "var(--accent-orange)", fontWeight: 600,
            background: "rgba(249,115,22,0.1)", padding: "3px 8px",
            borderRadius: 999, border: "1px solid rgba(249,115,22,0.25)",
          }}>
            Air-Gap Native
          </span>
          <span style={{
            fontSize: 11, color: "var(--text-muted)",
            background: "var(--bg-card)", padding: "3px 8px",
            borderRadius: 999, border: "1px solid var(--border)",
          }}>
            Zero Network Calls
          </span>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Left navigation sidebar */}
        <div style={{
          width: 210, borderRight: "1px solid var(--border)",
          overflowY: "auto", padding: "10px 8px", flexShrink: 0,
        }}>
          {CATEGORIES.map(cat => {
            const isOpen = !!openCategories[cat.id];
            const toolsInCat = TOOLS.filter(t => t.category === cat.id);
            const containsActiveTool = toolsInCat.some(t => t.id === activeTool);

            return (
              <div key={cat.id} style={{ marginBottom: 4 }}>
                <button
                  type="button"
                  onClick={() => toggleCategory(cat.id)}
                  className={`document-tool-category ${containsActiveTool ? "is-active" : ""}`}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "6px 8px", borderRadius: 5, cursor: "pointer",
                    background: containsActiveTool ? "rgba(249,115,22,0.08)" : (isOpen ? "rgba(255,255,255,0.02)" : "transparent"),
                    border: "none", color: containsActiveTool ? "var(--accent-orange)" : (isOpen ? "var(--text-primary)" : "var(--text-muted)"),
                    fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase",
                  }}
                >
                  <span>{cat.label}</span>
                  {isOpen ? (
                    <ChevronDown size={11} color={containsActiveTool ? "var(--accent-orange)" : "var(--text-muted)"} />
                  ) : (
                    <ChevronRight size={11} color={containsActiveTool ? "var(--accent-orange)" : "var(--text-muted)"} />
                  )}
                </button>

                {isOpen && (
                  <div style={{ marginTop: 2, marginBottom: 4 }}>
                    {toolsInCat.map(tool => {
                      const isToolActive = activeTool === tool.id;
                      return (
                        <div
                          key={tool.id}
                          onClick={() => setActiveTool(tool.id)}
                          style={{
                            display: "flex", alignItems: "center", gap: 8, padding: "5px 10px",
                            borderRadius: 5, cursor: "pointer", fontSize: 12, marginLeft: 4, marginBottom: 2,
                            background: isToolActive ? "var(--bg-card)" : "transparent",
                            color: isToolActive ? "var(--text-primary)" : "var(--text-secondary)",
                            border: isToolActive ? "1px solid var(--border)" : "1px solid transparent",
                            fontWeight: isToolActive ? 600 : 400,
                            transition: "all 0.1s",
                          }}
                          onMouseEnter={e => { if (!isToolActive) e.currentTarget.style.background = "var(--bg-card-hover)"; }}
                          onMouseLeave={e => { if (!isToolActive) e.currentTarget.style.background = "transparent"; }}
                        >
                          <span style={{ color: isToolActive ? "var(--accent-orange)" : "var(--text-muted)" }}>{tool.icon}</span>
                          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{tool.label}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Right workspace panel */}
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
          <ToolPanel toolId={activeTool} />
        </div>
      </div>
    </div>
  );
}
