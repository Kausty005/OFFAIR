"use client";


import { motion } from "framer-motion";

export function UserCard() {
  return (
    <motion.div 
      whileHover={{ scale: 1.02 }}
      className="flex items-center gap-3 p-3 rounded-xl border border-white/5 bg-surface/50 hover:bg-surface/80 transition-colors cursor-pointer"
    >
      <div className="relative">
        <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-accent to-accent/50 flex items-center justify-center text-white font-semibold shadow-inner">
          RS
        </div>
        <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-green-500 rounded-full border-2 border-background" />
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium text-white truncate">Rahul Sharma</h4>
        <p className="text-xs text-gray-400 truncate">Engineer • Maintenance</p>
      </div>
    </motion.div>
  );
}
