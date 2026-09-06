/**
 * useAgent — shared hook for running agent tasks via SSE stream.
 * All views use this hook to avoid duplicating the streaming logic.
 */
import { useState, useRef, useCallback } from "react";
import { AgentStep, AgentCallbacks } from "@/types";

const API = "http://localhost:8000";

export function useAgent(callbacks?: Partial<AgentCallbacks>) {
  const [isRunning, setIsRunning] = useState(false);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const addOrUpdateStep = useCallback((step: AgentStep) => {
    setSteps(prev => {
      const idx = prev.findIndex(s => s.description === step.description);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = step;
        return next;
      }
      return [...prev, step];
    });
    callbacks?.onStep?.(step);
  }, [callbacks]);

  const run = useCallback(async (task: string, filePaths: string[] = []) => {
    setIsRunning(true);
    setSteps([]);
    setResult(null);
    setError(null);
    callbacks?.onStart?.();

    try {
      // 1. POST to start the task
      const form = new FormData();
      form.append("task", task);
      form.append("files", JSON.stringify(filePaths));

      const resp = await fetch(`${API}/api/run`, { method: "POST", body: form });
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`Server error: ${txt}`);
      }
      const { task_id } = await resp.json();

      // 2. Open SSE stream
      const es = new EventSource(`${API}/api/stream/${task_id}`);
      esRef.current = es;

      es.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "heartbeat") return;

          if (msg.type === "progress") {
            addOrUpdateStep(msg.data as AgentStep);
          } else if (msg.type === "complete") {
            setResult(msg.data);
            setIsRunning(false);
            callbacks?.onComplete?.(msg.data);
            es.close();
          } else if (msg.type === "error") {
            setError(msg.data.error);
            setIsRunning(false);
            callbacks?.onError?.(msg.data.error);
            es.close();
          }
        } catch (err) {
          console.error("SSE parse error", err);
        }
      };

      es.onerror = () => {
        setError("Connection to agent lost");
        setIsRunning(false);
        callbacks?.onError?.("Connection lost");
        es.close();
      };

    } catch (err: any) {
      setError(err.message || "Unknown error");
      setIsRunning(false);
      callbacks?.onError?.(err.message);
    }
  }, [addOrUpdateStep, callbacks]);

  const cancel = useCallback(() => {
    esRef.current?.close();
    setIsRunning(false);
  }, []);

  return { run, cancel, isRunning, steps, result, error };
}

/**
 * Upload one or more files. Returns array of server paths.
 */
export async function uploadFiles(files: File[]): Promise<string[]> {
  const paths: string[] = [];
  for (const file of files) {
    const form = new FormData();
    form.append("file", file);
    const r = await fetch("http://localhost:8000/api/upload", { method: "POST", body: form });
    if (r.ok) {
      const data = await r.json();
      paths.push(data.path);
    }
  }
  return paths;
}
