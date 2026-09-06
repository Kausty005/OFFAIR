import { cn } from "@/lib/utils";

interface StatusBadgeProps {
  status: 'online' | 'offline' | 'local' | 'airgap' | 'neutral';
  label: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const statusConfig = {
    online: "bg-green-500/10 text-green-400 border-green-500/10 shadow-[0_0_12px_rgba(34,197,94,0.1)]",
    offline: "bg-red-500/10 text-red-400 border-red-500/10 shadow-[0_0_12px_rgba(239,68,68,0.1)]",
    local: "bg-green-500/10 text-green-400 border-green-500/10 shadow-[0_0_12px_rgba(34,197,94,0.1)]",
    airgap: "bg-amber-500/10 text-amber-400 border-amber-500/10 shadow-[0_0_12px_rgba(245,158,11,0.1)]",
    neutral: "bg-blue-500/10 text-blue-400 border-blue-500/10 shadow-[0_0_12px_rgba(59,130,246,0.1)]"
  };

  const dotConfig = {
    online: "bg-green-400 shadow-[0_0_8px_rgba(34,197,94,0.8)]",
    offline: "bg-red-400",
    local: "bg-green-400 shadow-[0_0_8px_rgba(34,197,94,0.8)]",
    airgap: "bg-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.8)]",
    neutral: "bg-blue-400"
  };

  return (
    <div className={cn("inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-[10px] font-semibold tracking-widest uppercase backdrop-blur-md transition-all", statusConfig[status], className)}>
      <span className={cn("w-1.5 h-1.5 rounded-full", dotConfig[status])} />
      {label}
    </div>
  );
}
