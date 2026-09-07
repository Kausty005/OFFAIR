"use client";

import { motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { LogOut } from "lucide-react";

export function UserCard() {
  const { user, logout, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 p-3 rounded-xl border border-white/5 bg-surface/50 opacity-50">
        <div className="w-10 h-10 rounded-full bg-white/10 animate-pulse" />
        <div className="flex-1 space-y-2">
          <div className="h-3 w-20 bg-white/10 rounded animate-pulse" />
          <div className="h-2 w-16 bg-white/10 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  if (!user) return null;

  // Generate initials
  const initials = user.name
    .split(' ')
    .map(n => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase() || "RS";

  return (
    <div className="group relative">
      <motion.div 
        whileHover={{ scale: 1.02 }}
        className="flex items-center gap-3 p-3 rounded-xl border border-white/5 bg-surface/50 hover:bg-surface/80 transition-colors cursor-pointer"
      >
        <div className="relative">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-accent to-accent/50 flex items-center justify-center text-white font-semibold shadow-inner">
            {initials}
          </div>
          <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-green-500 rounded-full border-2 border-background" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-white truncate">{user.name}</h4>
          <p className="text-xs text-gray-400 truncate">{user.role} • {user.division}</p>
        </div>
        
        <button 
          onClick={(e) => { e.stopPropagation(); logout(); }}
          className="w-8 h-8 rounded-lg flex items-center justify-center bg-white/5 hover:bg-red-500/20 text-gray-400 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all border border-transparent hover:border-red-500/30"
          title="Logout"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </motion.div>
    </div>
  );
}
