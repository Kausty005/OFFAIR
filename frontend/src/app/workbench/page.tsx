"use client";

import { GlassCard } from "@/components/common/glass-card";
import { PageHeader } from "@/components/common/page-header";
import { 
  Terminal, 
  Cpu, 
  UserCircle, 
  BookOpen, 
  Server, 
  Upload, 
  Send, 
  Paperclip,
  CheckCircle2,
  Loader2,
  Bot
} from "lucide-react";
import { motion } from "framer-motion";

const infoCards = [
  { icon: Cpu, label: "Active Model", value: "Reasoning LLM" },
  { icon: UserCircle, label: "User Role", value: "Engineer" },
  { icon: BookOpen, label: "Knowledge Status", value: "Authorized" },
  { icon: Server, label: "Server", value: "GPU Local" },
];

const agentSteps = [
  { label: "Understand Request", status: "done" },
  { label: "Verify Permission", status: "done" },
  { label: "Search Knowledge Base", status: "done" },
  { label: "Rerank Documents", status: "done" },
  { label: "Select Reasoning Model", status: "done" },
  { label: "Generate Approval Note", status: "loading" },
];

const mockChat = [
  { role: "user", content: "Review the attached specification and generate an approval note for the new heat exchanger module. Ensure it complies with our internal safety guidelines." },
  { role: "ai", content: "I will analyze the heat exchanger specification against the internal safety guidelines from our knowledge base and draft the approval note." }
];

export default function WorkbenchPage() {
  return (
    <div className="h-full flex flex-col gap-8 max-w-[1600px] mx-auto px-2">
      <PageHeader 
        title="AI Workbench" 
        description="Confidential Agentic Environment"
      />

      {/* Top Info Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 shrink-0">
        {infoCards.map((card, idx) => (
          <GlassCard key={idx} className="p-5 flex items-center gap-4 bg-surface/30 hover:bg-surface/50 transition-all duration-300 border-white/[0.03] shadow-sm">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-b from-white/5 to-transparent border border-white/10 flex items-center justify-center shrink-0 shadow-inner">
              <card.icon className="w-5 h-5 text-gray-300" />
            </div>
            <div>
              <p className="text-[10px] text-gray-500 font-semibold tracking-widest uppercase mb-1">{card.label}</p>
              <p className="text-[15px] font-medium text-white tracking-wide">{card.value}</p>
            </div>
          </GlassCard>
        ))}
      </div>

      {/* Main Workspace */}
      <div className="flex-1 flex gap-8 min-h-[500px]">
        
        {/* CENTER: Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <GlassCard className="flex-1 flex flex-col p-0 overflow-hidden border-white/[0.04] shadow-[0_16px_64px_-16px_rgba(0,0,0,0.5)] bg-surface/40 backdrop-blur-3xl rounded-3xl">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-8 space-y-8">
              {mockChat.map((msg, idx) => (
                <div key={idx} className={`flex items-start gap-5 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-sm
                    ${msg.role === 'user' ? 'bg-gradient-to-b from-accent/20 to-accent/5 border border-accent/20 text-accent' : 'bg-gradient-to-b from-white/10 to-white/5 border border-white/10 text-white'}`}
                  >
                    {msg.role === 'user' ? <UserCircle className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                  </div>
                  <div className={`max-w-[80%] p-5 shadow-sm text-[15px] leading-relaxed tracking-wide
                    ${msg.role === 'user' 
                      ? 'bg-accent/10 border border-accent/20 text-white rounded-2xl rounded-tr-md' 
                      : 'bg-white/[0.03] border border-white/[0.05] text-gray-200 rounded-2xl rounded-tl-md'
                    }`}
                  >
                    <p>{msg.content}</p>
                  </div>
                </div>
              ))}
              
              {/* Agent typing indicator */}
              <div className="flex items-start gap-5">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-b from-white/10 to-white/5 border border-white/10 flex items-center justify-center shrink-0 shadow-sm">
                  <Bot className="w-5 h-5 text-gray-300" />
                </div>
                <div className="bg-white/[0.02] border border-white/[0.04] rounded-2xl rounded-tl-md px-5 py-4 flex gap-1.5 items-center">
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }} />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }} />
                </div>
              </div>
            </div>

            {/* Input Area */}
            <div className="p-5 bg-background/60 border-t border-white/[0.04] shrink-0">
              <div className="flex gap-3 max-w-4xl mx-auto">
                <button className="h-[56px] px-5 rounded-2xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.05] flex items-center justify-center gap-2.5 text-gray-400 hover:text-white transition-all duration-300">
                  <Paperclip className="w-[18px] h-[18px]" />
                </button>
                <div className="flex-1 relative group">
                  <input 
                    type="text"
                    placeholder="Message OFFAIR AI..."
                    className="w-full h-[56px] bg-white/[0.02] border border-white/[0.05] group-hover:border-white/10 rounded-2xl pl-6 pr-16 text-[15px] text-white focus:outline-none focus:border-accent/50 focus:bg-white/[0.04] transition-all duration-300 placeholder:text-gray-500 shadow-inner"
                    defaultValue="Generate approval note..."
                  />
                  <button className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl bg-white text-background flex items-center justify-center hover:bg-gray-200 transition-all duration-300 shadow-md">
                    <Send className="w-4 h-4 ml-0.5" />
                  </button>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>

        {/* RIGHT PANEL: Agent Activity */}
        <div className="w-[340px] shrink-0 flex flex-col hidden lg:flex">
          <GlassCard className="flex-1 flex flex-col p-0 overflow-hidden border-white/[0.04] bg-surface/30 rounded-3xl">
            <div className="px-6 py-5 border-b border-white/[0.04] bg-white/[0.01]">
              <h3 className="text-[13px] font-semibold text-white flex items-center gap-2.5 tracking-wide">
                <Terminal className="w-4 h-4 text-accent" />
                Agent Activity
              </h3>
            </div>
            
            <div className="flex-1 overflow-y-auto p-8 space-y-2 relative">
              <div className="absolute top-10 left-[41px] bottom-12 w-px bg-white/5 pointer-events-none" />
              
              {agentSteps.map((step, idx) => (
                <motion.div 
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1, ease: "easeOut" }}
                  key={idx} 
                  className="flex gap-5 relative z-10"
                >
                  {/* Connector Line Fill for 'done' */}
                  {idx < agentSteps.length - 1 && step.status === 'done' && (
                    <div className="absolute top-7 left-[9px] w-0.5 h-[calc(100%+8px)] bg-accent/40" />
                  )}
                  
                  {/* Status Icon */}
                  <div className="shrink-0 mt-1">
                    {step.status === 'done' ? (
                      <div className="w-5 h-5 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center shadow-[0_0_12px_rgba(56,114,224,0.3)]">
                        <CheckCircle2 className="w-3 h-3 text-accent" />
                      </div>
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-surface border border-white/20 flex items-center justify-center shadow-[0_0_12px_rgba(255,255,255,0.05)]">
                        <Loader2 className="w-3 h-3 text-gray-400 animate-spin" />
                      </div>
                    )}
                  </div>
                  
                  {/* Step Label */}
                  <div className="pb-8">
                    <p className={`text-[14px] font-medium tracking-wide ${step.status === 'done' ? 'text-gray-300' : 'text-white'}`}>
                      {step.label}
                    </p>
                    {step.status === 'loading' && (
                      <div className="mt-2.5 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.05] w-max">
                        <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-pulse" />
                        <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Processing</span>
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </GlassCard>
        </div>

      </div>
    </div>
  );
}
