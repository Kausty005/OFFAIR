import { useCallback, useRef } from "react";
import { chatService } from "@/lib/services/chat";

// Exact status values from the backend's AgentStep
export type StepStatus = "pending" | "running" | "done" | "error" | "skipped";

export interface AgentStep {
  label: string;
  tool: string;
  status: StepStatus;
}

export interface CompletionData {
  final_output: string;
  verified: boolean;
  verification_notes: string[];
  output_files: string[];
  rag_sources: { source?: string; page?: number; score?: number }[];
  selected_model: string;
  task_type: string;
  routing_reason: string;
  tool_results: Record<string, unknown>;
}

export type AgentEventCallback = {
  onStep: (step: AgentStep) => void;
  onComplete: (data: CompletionData) => void;
  onError: (error: string) => void;
};

export function useAgentRun() {
  const eventSourceRef = useRef<EventSource | null>(null);

  const abort = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const run = useCallback(
    async (task: string, uploadedFiles: string[] = [], callbacks: AgentEventCallback) => {
      // Abort any previous run
      abort();

      let task_id: string;
      try {
        const result = await chatService.runAgent(task, uploadedFiles);
        task_id = result.task_id;
      } catch (err) {
        callbacks.onError("Failed to start agent. Is the backend running?");
        return;
      }

      const es = chatService.createEventSource(task_id);
      eventSourceRef.current = es;

      es.onmessage = (event: MessageEvent) => {
        let parsed: { type: string; data: Record<string, unknown> };
        try {
          parsed = JSON.parse(event.data);
        } catch {
          return;
        }

        const { type, data } = parsed;

        if (type === "heartbeat") return;

        if (type === "progress") {
          callbacks.onStep({
            label: (data.description as string) || "Processing…",
            tool: (data.tool as string) || "",
            // backend sends: pending | running | done | error | skipped
            status: (data.status as StepStatus) || "running",
          });
          return;
        }

        if (type === "complete") {
          es.close();
          eventSourceRef.current = null;
          callbacks.onComplete(data as unknown as CompletionData);
          return;
        }

        if (type === "error") {
          es.close();
          eventSourceRef.current = null;
          callbacks.onError((data.error as string) || "Unknown error");
          return;
        }
      };

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;
        callbacks.onError("Lost connection to agent. Check backend status.");
      };
    },
    [abort]
  );

  return { run, abort };
}
