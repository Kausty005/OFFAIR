"use client";

import { usePathname } from "next/navigation";
import { StatusBadge } from "../common/status-badge";
import { Activity, Shield } from "lucide-react";

export function Topbar() {
  const pathname = usePathname();

  if (pathname === "/login") return null;

  return (
    <header className="h-[72px] border-b border-white/[0.04] bg-surface/40 backdrop-blur-3xl flex items-center justify-between px-8 sticky top-0 z-20 shrink-0 shadow-[0_4px_24px_rgba(0,0,0,0.2)]">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-b from-accent/20 to-accent/5 border border-accent/20 flex items-center justify-center shadow-inner">
            <Activity className="w-4 h-4 text-accent" />
          </div>
          <div className="flex flex-col justify-center">
            <h2 className="text-[14px] font-semibold text-white tracking-wide leading-tight">OFFAIR AI</h2>
            <p className="text-[10px] text-gray-500 uppercase tracking-widest font-medium mt-0.5">Sovereign Agentic Workbench</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-5">
        <StatusBadge status="local" label="Local Server" />
        <StatusBadge status="airgap" label="Air Gap Active" />
        <div className="w-px h-6 bg-white/10 mx-1" />
        <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-white/5 bg-white/[0.02] text-[11px] font-medium text-gray-400 uppercase tracking-widest transition-colors hover:bg-white/[0.04]">
          <Shield className="w-3.5 h-3.5 text-gray-500" />
          External Calls: <span className="text-white">0</span>
        </div>
      </div>
    </header>
  );
}
