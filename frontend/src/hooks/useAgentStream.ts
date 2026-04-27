import { useCallback, useState } from "react";
import { streamAgentRun } from "../utils/api";
import type { PipelineStep, Report, SSEEvent } from "../types";

interface UseAgentStreamReturn {
  events: SSEEvent[];
  isRunning: boolean;
  currentStep: PipelineStep;
  report: Report | null;
  error: string | null;
  startRun: (url: string) => void;
  reset: () => void;
}

const STEP_MAP: Record<string, PipelineStep> = {
  crawl_app: "crawl_app",
  generate_test_cases: "generate_test_cases",
  execute_test: "execute_test",
  classify_bug: "classify_bug",
  reflect_and_expand: "reflect_and_expand",
  generate_report: "generate_report",
  done: "done",
};

function toStep(step: string): PipelineStep | null {
  return STEP_MAP[step] ?? null;
}

function extractErrorMessage(payload: SSEEvent["payload"]): string {
  if (typeof payload === "string") {
    return payload;
  }
  if (payload && typeof payload === "object" && "message" in payload) {
    const message = payload.message;
    if (typeof message === "string") {
      return message;
    }
  }
  return "Agent run failed.";
}

export function useAgentStream(): UseAgentStreamReturn {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<PipelineStep>("idle");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reset = useCallback((): void => {
    setEvents([]);
    setIsRunning(false);
    setCurrentStep("idle");
    setReport(null);
    setError(null);
  }, []);

  const startRun = useCallback((url: string): void => {
    const trimmedUrl = url.trim();

    reset();
    if (!trimmedUrl) {
      setError("Please provide a URL before running SentinelQA.");
      return;
    }

    setIsRunning(true);
    let lastEventTime = Date.now();
    const timeoutCheckId = window.setInterval(() => {
      if (Date.now() - lastEventTime > 60_000) {
        window.clearInterval(timeoutCheckId);
        setError(
          "Stream timed out after 60s with no response. The agent may still be running — " +
            "check http://localhost:8000/api/last-run for the cached result, or try again."
        );
        setIsRunning(false);
      }
    }, 5_000);

    void (async () => {
      try {
        for await (const event of streamAgentRun(trimmedUrl)) {
          lastEventTime = Date.now();
          setEvents((previous) => [...previous, event]);

          const mapped = toStep(event.step);
          if (mapped) {
            setCurrentStep(mapped);
          }

          if (event.type === "complete") {
            const payload = event.payload;
            if (payload && typeof payload === "object" && "report" in payload) {
              const maybeReport = payload.report;
              if (maybeReport && typeof maybeReport === "object") {
                setReport(maybeReport as Report);
              }
            }
          }

          if (event.type === "error") {
            setCurrentStep("error");
            setError(extractErrorMessage(event.payload));
          }
        }
      } catch (caught) {
        const message = caught instanceof Error ? caught.message : "Unknown stream error.";
        setCurrentStep("error");
        setError(message);
      } finally {
        window.clearInterval(timeoutCheckId);
        setIsRunning(false);
      }
    })();
  }, [reset]);

  return { events, isRunning, currentStep, report, error, startRun, reset };
}
