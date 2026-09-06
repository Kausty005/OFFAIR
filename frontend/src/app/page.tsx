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
import { AgentStep, ModelRouterInfo, SystemStatus } from "@/types";

export default function Home() {
  const [activeView, setActiveView] = useState<string>("workbench");
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [routerInfo, setRouterInfo] = useState<ModelRouterInfo | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [finalOutput, setFinalOutput] = useState<string>("");
  const [outputFiles, setOutputFiles] = useState<string[]>([]);
  const [ragSources, setRagSources] = useState<any[]>([]);

  // Fetch system status on mount and every 10s
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const r = await fetch("http://localhost:8000/api/status");
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
        selectedModel: result.selected_model || "",
        reason: result.routing_reason || "",
        inference: "LOCAL",
        endpoint: "localhost:11434",
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
        return <KnowledgeView />;
      case "security":
        return <SecurityView systemStatus={systemStatus} />;
      default:
        return <WorkbenchView callbacks={agentCallbacks} />;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      <Topbar systemStatus={systemStatus} />

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
