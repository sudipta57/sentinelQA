import { useMemo, useState } from "react";
import type { PipelineStep } from "../types";

interface InputPanelProps {
  onRun: (url: string) => void;
  isRunning: boolean;
  currentStep: PipelineStep;
}

const PIPELINE_ORDER: PipelineStep[] = [
  "crawl_app",
  "generate_test_cases",
  "execute_test",
  "classify_bug",
  "reflect_and_expand",
  "generate_report",
  "done",
];

const DISPLAY_STEPS: Array<{ step: PipelineStep; label: string }> = [
  { step: "crawl_app", label: "Crawling" },
  { step: "generate_test_cases", label: "Generating" },
  { step: "execute_test", label: "Executing" },
  { step: "classify_bug", label: "Classifying" },
  { step: "reflect_and_expand", label: "Reflecting" },
  { step: "generate_report", label: "Reporting" },
];

export default function InputPanel({ onRun, isRunning, currentStep }: InputPanelProps): JSX.Element {
  const [url, setUrl] = useState<string>("http://demo-app:3001");

  const currentIndex = useMemo(() => {
    const idx = PIPELINE_ORDER.indexOf(currentStep);
    return idx;
  }, [currentStep]);

  const handleRun = (): void => {
    onRun(url);
  };

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row">
        <input
          type="url"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://your-app.com"
          disabled={isRunning}
          className="h-11 w-full rounded-lg border border-gray-700 bg-gray-900 px-3 text-white outline-none transition focus:border-purple-500 focus:ring-1 focus:ring-purple-500 disabled:cursor-not-allowed disabled:opacity-60"
        />
        <button
          type="button"
          onClick={handleRun}
          disabled={isRunning}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-purple-600 px-5 text-sm font-semibold text-white transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isRunning ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Running...
            </>
          ) : (
            "Run SentinelQA"
          )}
        </button>
      </div>

      <p className="text-xs text-gray-400">
        Running via Docker Compose? Use the service name: <span className="text-gray-200">http://demo-app:3001</span>{" "}
        — or any public URL for a live demo.
      </p>

      <div className="overflow-x-auto">
        <div className="flex min-w-[700px] items-center">
          {DISPLAY_STEPS.map(({ step, label }, index) => {
            const stepIndex = PIPELINE_ORDER.indexOf(step);
            const isActive = currentStep === step;
            const isDone = currentIndex > -1 && stepIndex < currentIndex;

            return (
              <div key={step} className="flex flex-1 items-center">
                <div className="flex min-w-0 flex-col items-start">
                  <div className="flex items-center gap-2">
                    <span
                      className={[
                        "h-2.5 w-2.5 rounded-full",
                        isActive
                          ? "animate-pulse bg-purple-400"
                          : isDone
                            ? "bg-green-400"
                            : "bg-gray-600",
                      ].join(" ")}
                    />
                    <span
                      className={[
                        "text-xs font-medium",
                        isActive ? "text-white" : isDone ? "text-green-400" : "text-gray-500",
                      ].join(" ")}
                    >
                      {label}
                    </span>
                  </div>
                  <div
                    className={[
                      "mt-1 h-0.5 w-16",
                      isActive ? "bg-purple-500" : isDone ? "bg-green-500" : "bg-transparent",
                    ].join(" ")}
                  />
                </div>

                {index < DISPLAY_STEPS.length - 1 && (
                  <div className={[
                    "mx-3 h-px flex-1",
                    isDone ? "bg-green-600/70" : "bg-gray-700",
                  ].join(" ")} />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
