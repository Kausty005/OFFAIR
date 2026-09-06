// Shared TypeScript types for the frontend

export interface AgentStep {
  description: string;
  status: "pending" | "running" | "done" | "failed" | "skipped";
  result?: string;
  tool?: string;
}

export interface ModelRouterInfo {
  taskType: string;
  selectedModel: string;
  reason: string;
  inference: string;
  endpoint: string;
  visionModel?: string;
}

export interface SystemStatus {
  ollama: boolean;
  docker: boolean;
  ocr: boolean;
  knowledge_base: number;
  external_api_calls: number;
  internet_dependency: boolean;
  timestamp?: number;
}

export interface RAGSource {
  document: string;
  page?: string | number;
  text: string;
  score?: number;
}

export interface AgentCallbacks {
  onStart: (initialSteps?: AgentStep[]) => void;
  onStep: (step: AgentStep) => void;
  onComplete: (result: any) => void;
  onError: (error: string) => void;
  setRouterInfo: (info: ModelRouterInfo) => void;
}

export interface UploadedFile {
  filename: string;
  path: string;
  size: number;
}
