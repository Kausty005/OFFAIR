import { cn } from "@/lib/utils";

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function GlassCard({ children, className, ...props }: GlassCardProps) {
  return (
    <div className={cn("glass-card rounded-2xl p-6 transition-all duration-300 hover:shadow-[0_12px_48px_-12px_rgba(0,0,0,0.6)]", className)} {...props}>
      {children}
    </div>
  );
}
