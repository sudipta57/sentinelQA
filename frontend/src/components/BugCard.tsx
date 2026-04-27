import { useMemo, useState } from "react";
import type { ClassifiedBug } from "../types";

interface BugCardProps {
  bug: ClassifiedBug;
  backendUrl: string;
}

const SEVERITY_STYLES: Record<ClassifiedBug["severity"], string> = {
  Critical: "bg-red-500/25 text-red-200",
  Major: "bg-amber-500/25 text-amber-200",
  Minor: "bg-teal-500/25 text-teal-200",
};

function toAssetUrl(backendUrl: string, path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalizedBase = backendUrl.endsWith("/") ? backendUrl.slice(0, -1) : backendUrl;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

export default function BugCard({ bug, backendUrl }: BugCardProps): JSX.Element {
  const [showSteps, setShowSteps] = useState<boolean>(false);

  const screenshotUrl = useMemo(() => {
    if (!bug.screenshot_path) {
      return null;
    }
    return toAssetUrl(backendUrl, bug.screenshot_path);
  }, [backendUrl, bug.screenshot_path]);

  return (
    <article className="space-y-3 rounded-lg border border-gray-800 bg-gray-900 p-4">
      <div className="flex items-start justify-between gap-3">
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${SEVERITY_STYLES[bug.severity]}`}>
          {bug.severity}
        </span>
      </div>

      <div>
        <h4 className="text-base font-semibold text-white">{bug.title}</h4>
        <p className="mt-1 text-sm italic text-gray-400">{bug.root_cause_hypothesis}</p>
      </div>

      {bug.fix_suggestion && (
        <div className="rounded-lg border border-green-900 bg-green-950/30 p-3">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-lg">🔧</span>
            <span className="font-semibold uppercase tracking-widest text-green-400">How to Fix</span>
          </div>
          <p className="text-sm leading-relaxed text-green-300">{bug.fix_suggestion}</p>
        </div>
      )}

      <div>
        <button
          type="button"
          onClick={() => setShowSteps((value) => !value)}
          className="text-sm font-medium text-gray-300 underline-offset-2 hover:text-white hover:underline"
        >
          Steps to Reproduce {showSteps ? "▲" : "▼"}
        </button>

        {showSteps && (
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-gray-300">
            {bug.steps_to_reproduce.map((step, index) => (
              <li key={`${bug.test_id}-step-${index}`}>{step}</li>
            ))}
          </ol>
        )}
      </div>

      {screenshotUrl && (
        <a
          href={screenshotUrl}
          target="_blank"
          rel="noreferrer"
          className="block overflow-hidden rounded border border-gray-700"
        >
          <img src={screenshotUrl} alt={bug.title} className="h-36 w-full object-cover" loading="lazy" />
        </a>
      )}

      <div className="text-xs text-gray-600">
        <span className="font-mono">{bug.test_id}</span>
      </div>
    </article>
  );
}
