"use client";

import { GlassCard } from "@/components/common/glass-card";
import { Activity, Shield, Database, Terminal, Cpu, Lock, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { authService } from "@/lib/services/auth";

const features = [
  { icon: Cpu, title: "Local LLMs", desc: "No data leaves your network" },
  { icon: Database, title: "Permission-Aware RAG", desc: "Role-based document access" },
  { icon: Terminal, title: "Agentic Workflow", desc: "Automated task execution" },
  { icon: Shield, title: "Zero External Calls", desc: "100% air-gap compliance" },
];

const roles = ["Technician", "Engineer", "Manager"];

export default function LoginPage() {
  const router = useRouter();
  const [selectedRole, setSelectedRole] = useState("Engineer");
  const [employeeId, setEmployeeId] = useState("");
  const [passkey, setPasskey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId || !passkey) {
      setError("Please enter all fields");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await authService.login(employeeId, passkey, selectedRole);
      router.push("/workbench");
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background bg-blueprint flex relative overflow-hidden w-full">
      {/* Background gradients */}
      <div className="absolute top-0 left-0 w-1/2 h-full bg-accent/[0.03] blur-[150px] rounded-full pointer-events-none" />
      
      {/* LEFT SIDE - BRANDING */}
      <div className="hidden lg:flex flex-1 flex-col justify-center px-16 xl:px-24 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        >
          <div className="flex items-center gap-4 mb-8">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-b from-accent/20 to-accent/5 border border-accent/20 flex items-center justify-center shadow-[0_0_40px_rgba(56,114,224,0.15)]">
              <Activity className="w-7 h-7 text-accent" />
            </div>
            <h1 className="text-[40px] font-bold text-white tracking-tight leading-none">OFFAIR AI</h1>
          </div>
          
          <h2 className="text-[32px] font-light text-gray-300 mb-3 tracking-tight">
            Confidential Industrial Intelligence.
          </h2>
          <p className="text-[28px] font-medium text-white mb-20 tracking-tight">
            Completely On-Premise.
          </p>

          <div className="grid grid-cols-2 gap-8 max-w-2xl">
            {features.map((feature, idx) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.2 + idx * 0.1, ease: "easeOut" }}
                className="group p-6 rounded-3xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-all duration-300 backdrop-blur-xl hover:border-white/10 hover:shadow-[0_8px_32px_rgba(0,0,0,0.2)]"
              >
                <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/[0.05] flex items-center justify-center mb-5 group-hover:scale-105 group-hover:bg-accent/10 group-hover:border-accent/20 transition-all duration-500 ease-out">
                  <feature.icon className="w-5 h-5 text-gray-400 group-hover:text-accent transition-colors duration-300" />
                </div>
                <h3 className="text-[15px] font-semibold text-white mb-1.5 tracking-wide">{feature.title}</h3>
                <p className="text-[13px] text-gray-400 leading-relaxed">{feature.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* RIGHT SIDE - LOGIN */}
      <div className="flex-1 flex items-center justify-center lg:justify-end lg:pr-32 relative z-10 w-full lg:w-auto">
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
          className="w-full max-w-[440px] px-6 lg:px-0"
        >
          <GlassCard className="p-10 sm:p-12 border-white/[0.05] relative overflow-hidden bg-surface/50 rounded-[32px] shadow-[0_24px_64px_-12px_rgba(0,0,0,0.6)]">
            {/* Inner subtle glow */}
            <div className="absolute -top-32 -right-32 w-64 h-64 bg-accent/10 blur-[80px] rounded-full pointer-events-none" />

            <div className="mb-12">
              <h2 className="text-[28px] font-semibold text-white mb-3 tracking-tight">Enterprise Access</h2>
              <p className="text-[14px] text-gray-400">Sign in to your sovereign workspace</p>
            </div>
            
            <form onSubmit={handleLogin} className="space-y-8 relative z-10">
              <div className="space-y-2.5">
                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.15em] ml-1">Employee ID</label>
                <input 
                  type="text" 
                  value={employeeId}
                  onChange={(e) => setEmployeeId(e.target.value)}
                  className="w-full bg-background/60 border border-white/[0.06] rounded-2xl px-5 py-4 text-[14px] text-white focus:outline-none focus:border-accent/60 focus:bg-white/[0.02] transition-all duration-300 placeholder:text-gray-600 shadow-inner"
                  placeholder="EMP-XXXX"
                />
              </div>

              <div className="space-y-2.5">
                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.15em] ml-1">Password</label>
                <input 
                  type="password" 
                  value={passkey}
                  onChange={(e) => setPasskey(e.target.value)}
                  className="w-full bg-background/60 border border-white/[0.06] rounded-2xl px-5 py-4 text-[14px] text-white focus:outline-none focus:border-accent/60 focus:bg-white/[0.02] transition-all duration-300 placeholder:text-gray-600 shadow-inner"
                  placeholder="••••••••••••"
                />
              </div>

              <div className="space-y-3">
                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-[0.15em] ml-1">Role Clearance</label>
                <div className="grid grid-cols-3 gap-3">
                  {roles.map((role) => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => setSelectedRole(role)}
                      className={cn(
                        "py-3 px-2 text-[12px] font-medium rounded-xl border transition-all duration-300",
                        selectedRole === role 
                          ? "bg-accent/20 border-accent/40 text-white shadow-[0_0_16px_rgba(56,114,224,0.15)]" 
                          : "bg-white/[0.02] border-white/[0.04] text-gray-400 hover:text-white hover:bg-white/[0.04] hover:border-white/[0.08]"
                      )}
                    >
                      {role}
                    </button>
                  ))}
                </div>
              </div>
              
              {error && <p className="text-red-400 text-xs text-center">{error}</p>}

              <div className="pt-6">
                <button 
                  type="submit"
                  disabled={loading}
                  className="w-full bg-white text-background hover:bg-gray-200 disabled:bg-gray-400 font-semibold py-4 rounded-2xl transition-all duration-300 flex items-center justify-center gap-2 shadow-[0_4px_14px_rgba(255,255,255,0.1)] hover:shadow-[0_6px_20px_rgba(255,255,255,0.15)] hover:scale-[1.01] relative overflow-hidden group"
                >
                  <span className="relative z-10 text-[14px] flex items-center gap-2">
                    {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                    Access Enterprise Workspace
                  </span>
                </button>
              </div>
            </form>
            
            <div className="mt-10 pt-8 border-t border-white/[0.04] flex items-center justify-center gap-2.5 text-[11px] font-medium text-gray-400">
              <Lock className="w-[14px] h-[14px] text-green-400/80" />
              Protected by Air-Gapped Enterprise Infrastructure
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </div>
  );
}
