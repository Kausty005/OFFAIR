"use client";

import { SystemStatus } from "@/types";
import { Lock, Server } from "lucide-react";

interface Props {
  systemStatus: SystemStatus | null;
}

export default function BottomBar({ systemStatus }: Props) {
  const ollamaUp = systemStatus?.ollama ?? null;
  const dockerUp = systemStatus?.docker ?? null;
  const ocrUp = systemStatus?.ocr ?? null;
  const kbDocs = systemStatus?.knowledge_base ?? 0;

  return (
    <div className="bottombar">
      <BottomItem label="LOCAL AI" ok={ollamaUp} />
      <Sep />
      <BottomItem label="RAG" ok={kbDocs > 0 ? true : null} text={kbDocs > 0 ? `${kbDocs} docs` : "EMPTY"} />
      <Sep />
      <BottomItem label="SANDBOX" ok={dockerUp} />
      <Sep />
      <BottomItem label="OCR" ok={ocrUp} />
      <Sep />
      <div style={{ display: "flex", alignItems: "center", gap: 5, marginLeft: "auto" }}>
        <Lock size={10} color="var(--accent-green)" />
        <span style={{ color: "var(--accent-green)", fontSize: 11, fontWeight: 600 }}>
          EXTERNAL CALLS: 0
        </span>
        <Sep />
        <Server size={10} />
        <span>localhost:11434</span>
      </div>
    </div>
  );
}

function BottomItem({ label, ok, text }: { label: string; ok: boolean | null; text?: string }) {
  const color = ok === null
    ? "var(--text-muted)"
    : ok ? "var(--accent-green)" : "var(--accent-red)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <div style={{ width: 5, height: 5, borderRadius: "50%", background: color }} />
      <span style={{ color }}>{label}</span>
      {text && <span style={{ color: "var(--text-muted)" }}>{text}</span>}
    </div>
  );
}

function Sep() {
  return <span style={{ color: "var(--border-accent)" }}>│</span>;
}
