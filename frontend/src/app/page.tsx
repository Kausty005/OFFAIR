"use client";

import { useState, useEffect } from "react";
import Topbar from "@/components/Topbar";
import Sidebar from "@/components/Sidebar";
import RightPanel from "@/components/RightPanel";
import BottomBar from "@/components/BottomBar";
import WorkbenchView from "@/components/views/WorkbenchView";
import InspectionView from "@/components/views/InspectionView";
import CodingView from "@/components/views/CodingView";
import VisionView from "@/components/views/VisionView";
import KnowledgeView from "@/components/views/KnowledgeView";
import SecurityView from "@/components/views/SecurityView";
import DocumentToolsView from "@/components/views/DocumentToolsView";
import { AgentStep, ModelRouterInfo, SystemStatus } from "@/types";
import LoginPage, { SessionUser } from "@/components/LoginPage";

export default function Home() {
  const [activeView, setActiveView] = useState<string>("workbench");
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [routerInfo, setRouterInfo] = useState<ModelRouterInfo | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [finalOutput, setFinalOutput] = useState<string>("");
  const [outputFiles, setOutputFiles] = useState<string[]>([]);
  const [ragSources, setRagSources] = useState<any[]>([]);
  const [session, setSession] = useState<SessionUser | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("offair_session");
    if (stored) {
      try { setSession(JSON.parse(stored)); } catch { localStorage.removeItem("offair_session"); }
    }
  }, []);

  // Fetch system status on mount and every 10s
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const r = await fetch("/api/status");
        if (r.ok) setSystemStatus(await r.json());
      } catch {}
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAgentStart = (steps?: AgentStep[]) => {
    setIsAgentRunning(true);
    setAgentSteps(steps || []);
    setFinalOutput("");
    setOutputFiles([]);
    setRagSources([]);
    setRouterInfo(null);
  };

  const handleAgentStep = (step: AgentStep) => {
    setAgentSteps(prev => {
      const idx = prev.findIndex(s => s.description === step.description);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = step;
        return updated;
      }
      return [...prev, step];
    });
  };

  const handleAgentComplete = (result: any) => {
    setIsAgentRunning(false);
    setFinalOutput(result.final_output || "");
    setOutputFiles(result.output_files || []);
    setRagSources(result.rag_sources || []);
    if (result.selected_model || result.task_type) {
      setRouterInfo({
        taskType: result.task_type || "general",
        selectedModel: result.selected_model || "NONE",
        reason: result.routing_reason || "",
        inference: "LOCAL",
        endpoint: result.task_type === "document_operation" ? "localhost:8000 / Document Tools" : "localhost:11434",
      });
    }
  };

  const handleAgentError = () => {
    setIsAgentRunning(false);
  };

  const agentCallbacks = {
    onStart: handleAgentStart,
    onStep: handleAgentStep,
    onComplete: handleAgentComplete,
    onError: handleAgentError,
    setRouterInfo,
  };

  const renderView = () => {
    switch (activeView) {
      case "workbench":
        return <WorkbenchView callbacks={agentCallbacks} />;
      case "inspection":
        return <InspectionView callbacks={agentCallbacks} />;
      case "coding":
        return <CodingView callbacks={agentCallbacks} />;
      case "vision":
        return <VisionView callbacks={agentCallbacks} />;
      case "knowledge":
        return <KnowledgeView session={session!} />;
      case "security":
        return <SecurityView systemStatus={systemStatus} />;
      case "document-tools":
        return <DocumentToolsView />;
      default:
        return <WorkbenchView callbacks={agentCallbacks} />;
    }
  };

  if (!session) return <LoginPage onAuthenticated={setSession} />;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <Topbar systemStatus={systemStatus} session={session} onLogout={() => { localStorage.removeItem("offair_session"); setSession(null); }} />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <Sidebar activeView={activeView} onViewChange={setActiveView} />

        <main style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          {renderView()}
        </main>

        <RightPanel
          agentSteps={agentSteps}
          routerInfo={routerInfo}
          isRunning={isAgentRunning}
          outputFiles={outputFiles}
          ragSources={ragSources}
        />
      </div>

      <BottomBar systemStatus={systemStatus} />
    </div>
  );
}
