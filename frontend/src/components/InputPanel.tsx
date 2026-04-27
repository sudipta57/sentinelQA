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
    <section className="border-b border-gray-200 bg-white px-8 py-5">
      <div className="flex flex-col gap-4 md:flex-row">
        <input
          type="url"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://your-app.com"
          disabled={isRunning}
          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500 disabled:opacity-60"
        />
        <button
          type="button"
          onClick={handleRun}
          disabled={isRunning}
          className="inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
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

      <p className="mt-3 text-xs text-gray-400">
        Running via Docker Compose? Use the service name: http://demo-app:3001 — or any public URL for a live demo.
      </p>

      <div className="mt-5 overflow-x-auto">
        <div className="flex min-w-[700px] items-center py-4">
          {DISPLAY_STEPS.map(({ step, label }, index) => {
            const stepIndex = PIPELINE_ORDER.indexOf(step);
            const isActive = currentStep === step;
            const isDone = currentIndex > -1 && stepIndex < currentIndex;

            return (
              <div key={step} className="relative flex flex-1 items-center">
                <div className="relative flex w-full flex-col items-center">
                  <div
                    className={[
                      "z-10 flex h-4 w-4 items-center justify-center rounded-full",
                      isActive
                        ? "bg-indigo-600"
                        : isDone
                          ? "bg-emerald-500"
                          : "bg-gray-300",
                    ].join(" ")}
                  >
                    {isDone && (
                      <svg className="h-2.5 w-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                      </svg>
                    )}
                  </div>
                  <span
                    className={[
                      "absolute top-6 text-xs text-center",
                      isActive ? "font-medium text-indigo-600" : "text-gray-500",
                    ].join(" ")}
                  >
                    {label}
                  </span>
                </div>

                {index < DISPLAY_STEPS.length - 1 && (
                  <div className="absolute left-1/2 top-2 -z-0 h-px w-full bg-gray-200" />
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
