"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserCard } from "./user-card";
import { 
  Terminal, 
  BookOpen, 
  Files, 
  ShieldCheck, 
  Activity, 
  Settings 
} from "lucide-react";

const navItems = [
  { name: "AI Workbench", href: "/workbench", icon: Terminal },
  { name: "Knowledge Base", href: "/knowledge", icon: BookOpen },
  { name: "Generated Files", href: "/files", icon: Files },
  { name: "Security Center", href: "/security", icon: ShieldCheck },
  { name: "Audit Logs", href: "/audit", icon: Activity },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  if (pathname === "/login") return null;

  return (
    <aside className="w-[280px] h-screen border-r border-white/[0.04] bg-surface/40 backdrop-blur-3xl flex flex-col shrink-0 relative z-20 shadow-[4px_0_24px_rgba(0,0,0,0.2)]">
      <div className="flex-1 overflow-y-auto p-5 space-y-8">
        
        <div className="px-1 pt-4">
          <p className="text-[10px] font-semibold tracking-widest text-gray-500/80 uppercase mb-4 ml-3">Main Navigation</p>
          <nav className="space-y-1 relative">
            {navItems.map((item) => {
              const isActive = pathname?.startsWith(item.href);
              const Icon = item.icon;
              
              return (
                <Link key={item.name} href={item.href}>
                  <div className={cn(
                    "flex items-center gap-3.5 px-3 py-2.5 rounded-xl transition-all group relative",
                    isActive ? "text-white bg-white/5" : "text-gray-400 hover:text-gray-200 hover:bg-white/[0.02]"
                  )}>
                    <Icon className={cn("w-[18px] h-[18px] transition-colors", isActive ? "text-accent" : "text-gray-500 group-hover:text-gray-400")} />
                    <span className={cn("text-[13px] tracking-wide", isActive ? "font-medium" : "font-normal")}>{item.name}</span>
                    {isActive && (
                      <motion.div 
                        layoutId="sidebarActiveIndicator"
                        className="absolute left-0 w-[3px] h-[60%] bg-accent rounded-r-full shadow-[0_0_8px_rgba(56,114,224,0.6)]"
                        initial={false}
                        transition={{ type: "spring", stiffness: 400, damping: 30 }}
                      />
                    )}
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>

      </div>

      <div className="p-5 border-t border-white/[0.04] bg-background/30 backdrop-blur-xl">
        <UserCard />
      </div>
    </aside>
  );
}
