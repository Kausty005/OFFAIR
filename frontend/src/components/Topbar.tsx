"use client";

import { SystemStatus } from "@/types";
import { SessionUser } from "./LoginPage";
import { ChevronDown, LogIn, LogOut } from "lucide-react";
import { useState } from "react";

interface Props {
  systemStatus: SystemStatus | null;
  session: SessionUser;
  onLogout: () => void;
}

export default function Topbar({ systemStatus, session, onLogout }: Props) {
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <div style={{
      height: 56,
      background: "var(--bg-primary)",
      borderBottom: "1px solid var(--border)",
      display: "flex",
      alignItems: "center",
      padding: "0 18px 0 12px",
      justifyContent: "space-between",
      flexShrink: 0,
    }}>
      {/* Left: Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{
          width: 30, height: 30,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <img src="/favicon.png" alt="OffAir AI" style={{ width: 30, height: 30, objectFit: "contain" }} />
        </div>
        <div style={{ fontFamily: "'Dancing Script', cursive", fontSize: 25, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.01em" }}>
          OFFAIR <span style={{ color: "var(--accent-orange)" }}>AI.</span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
        <span className="role-pill">{session.role.toUpperCase()}</span>
        <div className="profile-menu-wrap">
          <button
            onClick={() => setProfileOpen((open) => !open)}
            aria-label="Account menu"
            aria-expanded={profileOpen}
            title={session.username}
            className="profile-trigger"
          >
            <span className="profile-avatar">{session.username.slice(0, 1).toUpperCase()}</span>
            <ChevronDown size={13} />
          </button>
          {profileOpen && (
            <div className="profile-menu">
              <div className="profile-name">{session.username}</div>
              <div className="profile-role">{session.role}</div>
              <button className="profile-signout" onClick={onLogout}>
                <LogIn size={14} /> Log in with different account
              </button>
              <button className="profile-signout" onClick={onLogout}>
                <LogOut size={14} /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

