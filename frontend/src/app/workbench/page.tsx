"use client";

import { GlassCard } from "@/components/common/glass-card";
import { PageHeader } from "@/components/common/page-header";
import {
  Terminal, Cpu, UserCircle, BookOpen, Server, Send,
  Paperclip, CheckCircle2, Loader2, Bot, XCircle, SkipForward
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect, useRef, useCallback } from "react";
import { chatService, ChatMessage } from "@/lib/services/chat";
import { securityService } from "@/lib/services/security";
import { filesService } from "@/lib/services/files";
import { useAgentRun, AgentStep, CompletionData } from "@/hooks/useAgentRun";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

// ─── Types ───────────────────────────────────────────────────────────────────

interface ExtendedMessage extends ChatMessage {
  id: string;
  meta?: {
    model?: string;
    task_type?: string;
    rag_sources?: CompletionData["rag_sources"];
    output_files?: string[];
    verified?: boolean;
    routing_reason?: string;
  };
}

// ─── Step Icon ────────────────────────────────────────────────────────────────

function StepIcon({ status }: { status: AgentStep["status"] }) {
  if (status === "done") {
    return (
      <motion.div
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 20 }}
        className="w-5 h-5 rounded-full bg-accent/20 border border-accent/50 flex items-center justify-center shadow-[0_0_10px_rgba(56,114,224,0.35)]"
      >
        <CheckCircle2 className="w-3 h-3 text-accent" />
      </motion.div>
    );
  }
  if (status === "error") {
    return (
      <div className="w-5 h-5 rounded-full bg-red-500/20 border border-red-500/40 flex items-center justify-center">
        <XCircle className="w-3 h-3 text-red-400" />
      </div>
    );
  }
  if (status === "skipped") {
    return (
      <div className="w-5 h-5 rounded-full bg-white/5 border border-white/15 flex items-center justify-center">
        <SkipForward className="w-3 h-3 text-gray-500" />
      </div>
    );
  }
  // running / pending
  return (
    <div className="w-5 h-5 rounded-full bg-surface border border-white/20 flex items-center justify-center shadow-[0_0_10px_rgba(255,255,255,0.04)]">
      <Loader2 className="w-3 h-3 text-gray-400 animate-spin" />
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function WorkbenchPage() {
  const { user } = useAuth();
  const { run, abort } = useAgentRun();

  const [messages, setMessages] = useState<ExtendedMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [activeModel, setActiveModel] = useState("Loading…");
  const [serverStatus, setServerStatus] = useState("Checking…");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const stepsEndRef = useRef<HTMLDivElement>(null);

  // ── Init: fetch model/status on mount ────────────────────────────────────
  useEffect(() => {
    const init = async () => {
      try {
        const [modelsData, statusData] = await Promise.all([
          chatService.getModels(),
          securityService.getStatus(),
        ]);
        setActiveModel(modelsData.general?.name || "Reasoning LLM");
        setServerStatus(statusData.ollama ? "GPU Local" : "Disconnected");
      } catch {
        setActiveModel("Offline");
        setServerStatus("Offline");
      }
    };
    init();
  }, []);

  // ── Auto-scroll ───────────────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  useEffect(() => {
    stepsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [agentSteps]);

  // ── File attach ───────────────────────────────────────────────────────────
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setPendingFile(e.target.files[0]);
  };

  // ── Send ──────────────────────────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text && !pendingFile) return;

    const userMsgContent = [
      text,
      pendingFile ? `📎 ${pendingFile.name}` : ""
    ].filter(Boolean).join("\n");

    const userMsgId = Date.now().toString();
    setMessages(prev => [...prev, { id: userMsgId, role: "user", content: userMsgContent }]);
    setInput("");
    setIsTyping(true);
    setAgentSteps([]);

    let uploadedPaths: string[] = [];
    if (pendingFile) {
      try {
        const res = await filesService.uploadFile(pendingFile);
        uploadedPaths = [res.path];
      } catch {
        // Non-fatal — continue without file
      }
      setPendingFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }

    await run(text, uploadedPaths, {
      onStep: (step) => {
        setAgentSteps(prev => {
          // If we already have this step (by label) just update its status
          const existingIdx = prev.findIndex(s => s.label === step.label);
          if (existingIdx >= 0) {
            const updated = [...prev];
            updated[existingIdx] = step;
            return updated;
          }
          return [...prev, step];
        });
      },

      onComplete: (data) => {
        setIsTyping(false);
        // Mark any still-running step as done
        setAgentSteps(prev =>
          prev.map(s => s.status === "running" ? { ...s, status: "done" as const } : s)
        );

        const aiMsgId = Date.now().toString();
        setMessages(prev => [
          ...prev,
          {
            id: aiMsgId,
            role: "ai",
            content: data.final_output || "Task completed.",
            meta: {
              model: data.selected_model,
              task_type: data.task_type,
              rag_sources: data.rag_sources,
              output_files: data.output_files,
              verified: data.verified,
              routing_reason: data.routing_reason,
            },
          },
        ]);

        // Update active model from the actual model used
        if (data.selected_model) setActiveModel(data.selected_model);
      },

      onError: (err) => {
        setIsTyping(false);
        setAgentSteps(prev =>
          prev.map(s => s.status === "running" ? { ...s, status: "error" as const } : s)
        );
        const errId = Date.now().toString();
        setMessages(prev => [
          ...prev,
          { id: errId, role: "ai", content: `⚠ ${err}` },
        ]);
      },
    });
  }, [input, pendingFile, run]);

  // ─── Info Cards ────────────────────────────────────────────────────────────
  const infoCards = [
    { icon: Cpu, label: "Active Model", value: activeModel },
    { icon: UserCircle, label: "User Role", value: user?.role || "Engineer" },
    { icon: BookOpen, label: "Knowledge Status", value: "Authorized" },
    { icon: Server, label: "Server", value: serverStatus },
  ];

  return (
    <div className="h-full flex flex-col gap-8 max-w-[1600px] mx-auto px-2">
      <PageHeader title="AI Workbench" description="Confidential Agentic Environment" />

      {/* ── Info Cards ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 shrink-0">
        {infoCards.map((card, idx) => (
          <GlassCard
            key={idx}
            className="p-5 flex items-center gap-4 bg-surface/30 hover:bg-surface/50 transition-all duration-300 border-white/[0.03] shadow-sm"
          >
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-b from-white/5 to-transparent border border-white/10 flex items-center justify-center shrink-0 shadow-inner">
              <card.icon className="w-5 h-5 text-gray-300" />
            </div>
            <div>
              <p className="text-[10px] text-gray-500 font-semibold tracking-widest uppercase mb-1">{card.label}</p>
              <p className="text-[15px] font-medium text-white tracking-wide truncate max-w-[140px]">{card.value}</p>
            </div>
          </GlassCard>
        ))}
      </div>

      {/* ── Main Workspace ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex gap-8 min-h-[500px]">

        {/* CENTER: Chat */}
        <div className="flex-1 flex flex-col min-w-0">
          <GlassCard className="flex-1 flex flex-col p-0 overflow-hidden border-white/[0.04] shadow-[0_16px_64px_-16px_rgba(0,0,0,0.5)] bg-surface/40 backdrop-blur-3xl rounded-3xl">

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-8 space-y-8">
              {messages.length === 0 && !isTyping && (
                <div className="h-full flex flex-col items-center justify-center text-center opacity-40 select-none">
                  <Bot className="w-12 h-12 text-gray-400 mb-4" />
                  <p className="text-[15px] text-gray-300 font-medium">System ready.</p>
                  <p className="text-[13px] text-gray-500 mt-1">Type a prompt or attach a document to begin.</p>
                </div>
              )}

              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25, ease: "easeOut" }}
                    className={cn("flex items-start gap-5", msg.role === "user" && "flex-row-reverse")}
                  >
                    {/* Avatar */}
                    <div className={cn(
                      "w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-sm",
                      msg.role === "user"
                        ? "bg-gradient-to-b from-accent/20 to-accent/5 border border-accent/20 text-accent"
                        : "bg-gradient-to-b from-white/10 to-white/5 border border-white/10 text-white"
                    )}>
                      {msg.role === "user"
                        ? <UserCircle className="w-5 h-5" />
                        : <Bot className="w-5 h-5" />}
                    </div>

                    {/* Bubble */}
                    <div className="flex flex-col gap-2 max-w-[80%]">
                      <div className={cn(
                        "p-5 text-[15px] leading-relaxed tracking-wide whitespace-pre-wrap shadow-sm",
                        msg.role === "user"
                          ? "bg-accent/10 border border-accent/20 text-white rounded-2xl rounded-tr-md"
                          : "bg-white/[0.03] border border-white/[0.05] text-gray-200 rounded-2xl rounded-tl-md"
                      )}>
                        {msg.content}
                      </div>

                      {/* AI metadata strip */}
                      {msg.role === "ai" && msg.meta && (
                        <div className="flex flex-wrap gap-2 pl-1">
                          {msg.meta.model && (
                            <span className="text-[10px] font-bold text-gray-500 bg-white/[0.03] border border-white/[0.04] px-2 py-1 rounded-md uppercase tracking-widest">
                              {msg.meta.model}
                            </span>
                          )}
                          {msg.meta.task_type && (
                            <span className="text-[10px] font-bold text-gray-500 bg-white/[0.03] border border-white/[0.04] px-2 py-1 rounded-md uppercase tracking-widest">
                              {msg.meta.task_type}
                            </span>
                          )}
                          {msg.meta.verified && (
                            <span className="text-[10px] font-bold text-green-400 bg-green-400/[0.08] border border-green-400/20 px-2 py-1 rounded-md uppercase tracking-widest">
                              ✓ Verified
                            </span>
                          )}
                          {msg.meta.rag_sources && msg.meta.rag_sources.length > 0 && (
                            <span className="text-[10px] font-bold text-blue-400 bg-blue-400/[0.08] border border-blue-400/20 px-2 py-1 rounded-md uppercase tracking-widest">
                              {msg.meta.rag_sources.length} Source{msg.meta.rag_sources.length > 1 ? "s" : ""}
                            </span>
                          )}
                          {msg.meta.output_files && msg.meta.output_files.length > 0 && (
                            <button
                              onClick={() => filesService.downloadFileByPath(msg.meta!.output_files![0])}
                              className="text-[10px] font-bold text-amber-400 bg-amber-400/[0.08] border border-amber-400/20 px-2 py-1 rounded-md uppercase tracking-widest hover:bg-amber-400/[0.15] transition-colors"
                            >
                              ↓ Download Output
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {/* Typing indicator */}
              {isTyping && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-start gap-5"
                >
                  <div className="w-10 h-10 rounded-2xl bg-gradient-to-b from-white/10 to-white/5 border border-white/10 flex items-center justify-center shrink-0 shadow-sm">
                    <Bot className="w-5 h-5 text-gray-300" />
                  </div>
                  <div className="bg-white/[0.02] border border-white/[0.04] rounded-2xl rounded-tl-md px-5 py-4 flex gap-2 items-center">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.15s" }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0.3s" }} />
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Pending file chip */}
            {pendingFile && (
              <div className="px-5 pb-0 pt-3 flex items-center gap-2">
                <div className="flex items-center gap-2 bg-accent/10 border border-accent/20 rounded-lg px-3 py-1.5 text-[12px] text-accent font-medium">
                  <Paperclip className="w-3.5 h-3.5" />
                  {pendingFile.name}
                  <button
                    onClick={() => { setPendingFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }}
                    className="ml-1 hover:text-white transition-colors"
                  >
                    ×
                  </button>
                </div>
              </div>
            )}

            {/* Input bar */}
            <div className="p-5 bg-background/60 border-t border-white/[0.04] shrink-0">
              <div className="flex gap-3 max-w-4xl mx-auto">
                <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileSelect} />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="h-[56px] px-5 rounded-2xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.05] flex items-center justify-center text-gray-400 hover:text-white transition-all duration-300"
                >
                  <Paperclip className="w-[18px] h-[18px]" />
                </button>

                <div className="flex-1 relative group">
                  <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                    placeholder="Message OFFAIR AI…"
                    disabled={isTyping}
                    className="w-full h-[56px] bg-white/[0.02] border border-white/[0.05] group-hover:border-white/10 rounded-2xl pl-6 pr-16 text-[15px] text-white focus:outline-none focus:border-accent/50 focus:bg-white/[0.04] transition-all duration-300 placeholder:text-gray-500 shadow-inner disabled:opacity-50"
                  />
                  <button
                    onClick={handleSend}
                    disabled={isTyping || (!input.trim() && !pendingFile)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl bg-white text-background flex items-center justify-center hover:bg-gray-200 transition-all duration-300 shadow-md disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    <Send className="w-4 h-4 ml-0.5" />
                  </button>
                </div>

                {/* Abort button — shown while streaming */}
                {isTyping && (
                  <button
                    onClick={abort}
                    title="Stop agent"
                    className="h-[56px] px-5 rounded-2xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 hover:text-red-300 transition-all duration-300 text-[12px] font-semibold tracking-wide"
                  >
                    Stop
                  </button>
                )}
              </div>
            </div>
          </GlassCard>
        </div>

        {/* RIGHT PANEL: Agent Activity */}
        <div className="w-[340px] shrink-0 hidden lg:flex flex-col">
          <GlassCard className="flex-1 flex flex-col p-0 overflow-hidden border-white/[0.04] bg-surface/30 rounded-3xl">
            {/* Header */}
            <div className="px-6 py-5 border-b border-white/[0.04] bg-white/[0.01] flex items-center justify-between">
              <h3 className="text-[13px] font-semibold text-white flex items-center gap-2.5 tracking-wide">
                <Terminal className="w-4 h-4 text-accent" />
                Agent Activity
              </h3>
              {agentSteps.length > 0 && (
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">
                  {agentSteps.filter(s => s.status === "done").length}/{agentSteps.length}
                </span>
              )}
            </div>

            {/* Steps */}
            <div className="flex-1 overflow-y-auto p-8 relative">
              {agentSteps.length > 0 && (
                <div className="absolute top-10 left-[41px] bottom-12 w-px bg-white/5 pointer-events-none" />
              )}

              {agentSteps.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center opacity-40 select-none">
                  <Terminal className="w-8 h-8 text-gray-500 mb-3" />
                  <p className="text-[13px] text-gray-400">Agent is idle.</p>
                  <p className="text-[11px] text-gray-500 mt-1">Execution stages will appear here.</p>
                </div>
              )}

              <AnimatePresence initial={false}>
                {agentSteps.map((step, idx) => (
                  <motion.div
                    key={`${step.label}-${idx}`}
                    initial={{ opacity: 0, x: 24 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                    className="flex gap-5 relative z-10"
                  >
                    {/* Animated connector line for done steps */}
                    {idx < agentSteps.length - 1 && step.status === "done" && (
                      <motion.div
                        initial={{ scaleY: 0 }}
                        animate={{ scaleY: 1 }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                        style={{ transformOrigin: "top" }}
                        className="absolute top-6 left-[9px] w-0.5 h-[calc(100%-4px)] bg-gradient-to-b from-accent/50 to-accent/10"
                      />
                    )}

                    {/* Icon */}
                    <div className="shrink-0 mt-0.5">
                      <StepIcon status={step.status} />
                    </div>

                    {/* Label */}
                    <div className="pb-8 min-w-0">
                      <p className={cn(
                        "text-[14px] font-medium tracking-wide leading-snug",
                        step.status === "done" && "text-gray-300",
                        step.status === "running" && "text-white",
                        step.status === "error" && "text-red-400",
                        step.status === "skipped" && "text-gray-600",
                        step.status === "pending" && "text-gray-400",
                      )}>
                        {step.label}
                      </p>

                      {step.tool && (
                        <p className="text-[10px] text-gray-600 mt-0.5 uppercase tracking-widest">
                          via {step.tool}
                        </p>
                      )}

                      {step.status === "running" && (
                        <div className="mt-2 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.05] w-max">
                          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                          <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Processing</span>
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              <div ref={stepsEndRef} />
            </div>
          </GlassCard>
        </div>

      </div>
    </div>
  );
}
