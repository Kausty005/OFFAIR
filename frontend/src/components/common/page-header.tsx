import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function PageHeader({ title, description, action, className }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-white/5 mb-8", className)}>
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold text-white tracking-tight">{title}</h1>
        {description && <p className="text-sm text-gray-400">{description}</p>}
      </div>
      {action && <div className="mt-4 sm:mt-0">{action}</div>}
    </div>
  );
}
