"use client";

import { Brain, Factory, Code2, Eye, BookOpen, Shield, Plus, FileStack, MessageSquare, Trash2 } from "lucide-react";
import { useState, useEffect } from "react";

interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  group: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "workbench",  label: "AI Workbench",      icon: <Brain size={14} />,   group: "WORKSPACE" },
  { id: "inspection", label: "Inspection Agent",   icon: <Factory size={14} />, group: "WORKSPACE" },
  { id: "coding",     label: "Coding Agent",       icon: <Code2 size={14} />,   group: "WORKSPACE" },
  { id: "vision",         label: "Vision Analysis",  icon: <Eye size={14} />,       group: "WORKSPACE" },
  { id: "document-tools", label: "Document Tools",    icon: <FileStack size={14} />, group: "WORKSPACE" },
  { id: "knowledge",  label: "Knowledge Base",     icon: <BookOpen size={14} />,group: "DATA" },
  { id: "security",   label: "Security & Audit",   icon: <Shield size={14} />,  group: "DATA" },
];

interface SessionInfo {
  id: string;
  title: string;
  updatedAt: string;
}

interface Props {
  activeView: string;
  onViewChange: (view: string) => void;
  activeSessionId?: string | null;
  onSessionChange?: (id: string | null) => void;
}

export default function Sidebar({ activeView, onViewChange, activeSessionId, onSessionChange }: Props) {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  
  const fetchSessions = async () => {
    try {
      const res = await fetch("/api/history");
      if (res.ok) setSessions(await res.json());
    } catch (e) {}
  };

  useEffect(() => {
    fetchSessions();
    const intv = setInterval(fetchSessions, 5000);
    return () => clearInterval(intv);
  }, []);

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await fetch(`/api/history/${id}`, { method: "DELETE" });
      if (activeSessionId === id && onSessionChange) onSessionChange(null);
      fetchSessions();
    } catch (e) {}
  };

  const groups = [...new Set(NAV_ITEMS.map(i => i.group))];

  return (
    <div style={{
      width: 220,
      backgroundColor: "var(--bg-secondary)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      flexShrink: 0,
      overflow: "hidden",
    }}>

      {/* Nav groups */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 0" }}>
        {groups.map(group => (
          <div key={group}>
            <div style={{
              fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
              color: "var(--text-muted)", padding: "12px 16px 4px",
            }}>
              {group}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 1, padding: "0 8px" }}>
              {NAV_ITEMS.filter(i => i.group === group).map(item => {
                const isActive = activeView === item.id;
                return (
                  <div
                    key={item.id}
                    onClick={() => onViewChange(item.id)}
                    style={{
                      display: "flex", alignItems: "center", gap: 9,
                      padding: "7px 10px", borderRadius: 6,
                      fontSize: 13, cursor: "pointer",
                      color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                      background: isActive ? "var(--bg-card)" : "transparent",
                      transition: "all 0.15s",
                    }}
                    onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = "var(--bg-card-hover)"; }}
                    onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
                  >
                    <span style={{ color: isActive ? "var(--accent-orange)" : "var(--text-muted)", flexShrink: 0 }}>
                      {item.icon}
                    </span>
                    {item.label}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Chat History section */}
      <div style={{ flex: 1, overflowY: "auto", borderTop: "1px solid var(--border)", paddingTop: 12 }}>
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "0 16px 8px"
        }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.08em", color: "var(--text-muted)" }}>
            CHAT HISTORY
          </div>
          <button
            onClick={() => {
              if (onSessionChange) onSessionChange(null);
              onViewChange("workbench");
            }}
            style={{
              background: "transparent", border: "none", color: "var(--text-primary)",
              cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontSize: 10, fontWeight: 600
            }}
          >
            <Plus size={12} /> NEW
          </button>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 1, padding: "0 8px" }}>
          {sessions.map(s => {
            const isActive = activeSessionId === s.id;
            return (
              <div
                key={s.id}
                onClick={() => {
                  if (onSessionChange) onSessionChange(s.id);
                  onViewChange("workbench");
                }}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "7px 10px", borderRadius: 6,
                  fontSize: 13, cursor: "pointer",
                  color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                  background: isActive ? "var(--bg-card)" : "transparent",
                  transition: "all 0.15s",
                }}
                onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = "var(--bg-card-hover)"; }}
                onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = "transparent"; }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 9, overflow: "hidden" }}>
                  <MessageSquare size={14} style={{ color: isActive ? "var(--accent-blue)" : "var(--text-muted)", flexShrink: 0 }} />
                  <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {s.title}
                  </span>
                </div>
                <button
                  onClick={(e) => handleDeleteSession(e, s.id)}
                  style={{
                    background: "transparent", border: "none", color: "var(--text-muted)",
                    cursor: "pointer", display: "flex", opacity: isActive ? 1 : 0.5
                  }}
                  onMouseEnter={e => e.currentTarget.style.color = "var(--error)"}
                  onMouseLeave={e => e.currentTarget.style.color = "var(--text-muted)"}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick Demo section */}
      <div style={{ padding: "12px 8px 12px", borderTop: "1px solid var(--border)" }}>
        <div style={{
          fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
          color: "var(--text-muted)", padding: "0 8px 8px",
        }}>
          QUICK DEMO
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <DemoButton label="Inspection Demo"  onClick={() => onViewChange("inspection")} accent="var(--accent-orange)" />
          <DemoButton label="Coding Demo"      onClick={() => onViewChange("coding")}     accent="var(--accent-blue)" />
          <DemoButton label="Vision Demo"      onClick={() => onViewChange("vision")}     accent="var(--accent-green)" />
        </div>
      </div>
    </div>
  );
}

function DemoButton({ label, onClick, accent }: { label: string; onClick: () => void; accent: string }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "6px 10px", borderRadius: 5, cursor: "pointer",
        background: `${accent}10`,
        border: `1px solid ${accent}30`,
        color: accent, fontSize: 11, fontWeight: 600,
        letterSpacing: "0.02em", width: "100%",
        transition: "all 0.15s",
      }}
      onMouseEnter={e => { e.currentTarget.style.background = `${accent}20`; }}
      onMouseLeave={e => { e.currentTarget.style.background = `${accent}10`; }}
    >
      <Plus size={10} />
      {label}
    </button>
  );
}
