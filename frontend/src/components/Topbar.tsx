"use client";

import { SystemStatus } from "@/types";
import { SessionUser } from "./LoginPage";
import { Shield, Cpu, WifiOff } from "lucide-react";

interface Props {
  systemStatus: SystemStatus | null;
  session: SessionUser;
  onLogout: () => void;
}

export default function Topbar({ systemStatus, session, onLogout }: Props) {
  const ollamaUp = systemStatus?.ollama ?? false;
  const dockerUp = systemStatus?.docker ?? false;

  return (
    <div style={{
      height: 48,
      background: "var(--bg-secondary)",
      borderBottom: "1px solid var(--border)",
      display: "flex",
      alignItems: "center",
      padding: "0 20px",
      justifyContent: "space-between",
      flexShrink: 0,
    }}>
      {/* Left: Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 26, height: 26, borderRadius: 6,
          background: "var(--accent-orange)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <WifiOff size={14} color="white" strokeWidth={2.5} />
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 800, color: "var(--text-primary)", letterSpacing: "0.08em" }}>
            OFFAIR AI
          </div>
          <div style={{ fontSize: 9, color: "var(--text-muted)", letterSpacing: "0.08em" }}>
            ON-PREMISE · AIR-GAP READY
          </div>
        </div>
      </div>

      {/* Right: Status pills */}
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, borderLeft: "1px solid var(--border)", paddingLeft: 16 }}>
          <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{session.username}</span>
          <span className="badge badge-blue">{session.role}</span>
          <button className="btn btn-ghost" onClick={onLogout} style={{ padding: "3px 8px", fontSize: 10 }}>Sign out</button>
        </div>
        <StatusPill label="LOCAL AI" ok={ollamaUp} okText="ONLINE" failText="OFFLINE" />
        <StatusPill label="SANDBOX" ok={dockerUp} okText="READY" failText="N/A" />

        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <WifiOff size={11} color="var(--accent-green)" />
          <span style={{ fontSize: 11, color: "var(--accent-green)", fontWeight: 600, letterSpacing: "0.05em" }}>
            AIR-GAP
          </span>
        </div>

        <div style={{
          fontSize: 11, fontWeight: 700, color: "var(--accent-green)",
          background: "rgba(34,197,94,0.08)",
          border: "1px solid rgba(34,197,94,0.2)",
          padding: "2px 10px", borderRadius: 999,
        }}>
          EXT CALLS: 0
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <Cpu size={11} color="var(--accent-blue)" />
          <span style={{ fontSize: 11, color: "var(--accent-blue)", fontWeight: 600 }}>GPU</span>
          <div style={{
            width: 6, height: 6, borderRadius: "50%",
            background: ollamaUp ? "var(--accent-green)" : "var(--text-muted)"
          }} className={ollamaUp ? "pulse" : ""} />
        </div>
      </div>
    </div>
  );
}

function StatusPill({ label, ok, okText, failText }: {
  label: string; ok: boolean; okText: string; failText: string;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
      <span style={{ fontSize: 9, color: "var(--text-muted)", fontWeight: 600, letterSpacing: "0.08em" }}>{label}</span>
      <span style={{
        fontSize: 10, fontWeight: 700, letterSpacing: "0.04em",
        color: ok ? "var(--accent-green)" : "var(--text-muted)"
      }}>{ok ? okText : failText}</span>
      <div style={{
        width: 5, height: 5, borderRadius: "50%",
        background: ok ? "var(--accent-green)" : "var(--text-muted)"
      }} className={ok ? "pulse" : ""} />
    </div>
  );
}
