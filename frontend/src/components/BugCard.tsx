import { useMemo, useState } from "react";
import type { ClassifiedBug } from "../types";

interface BugCardProps {
  bug: ClassifiedBug;
  backendUrl: string;
}

const SEVERITY_STYLES: Record<ClassifiedBug["severity"], string> = {
  Critical: "border-rose-200 bg-rose-50 text-rose-700",
  Major: "border-amber-200 bg-amber-50 text-amber-700",
  Minor: "border-sky-200 bg-sky-50 text-sky-700",
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
    <article className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-colors hover:border-gray-300">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="text-base font-semibold text-gray-900">{bug.title}</h4>
          <p className="mt-1 text-sm text-gray-500">{bug.root_cause_hypothesis}</p>
        </div>
        <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${SEVERITY_STYLES[bug.severity]}`}>
          {bug.severity}
        </span>
      </div>

      {bug.fix_suggestion && (
        <div className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-emerald-700">
            🔧 Suggested Fix
          </div>
          <p className="text-sm leading-relaxed text-emerald-800">{bug.fix_suggestion}</p>
        </div>
      )}

      <div className="mt-3">
        <button
          type="button"
          onClick={() => setShowSteps((value) => !value)}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          Steps to Reproduce {showSteps ? "▲" : "▼"}
        </button>

        {showSteps && (
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-gray-600">
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
          className="mt-3 block"
        >
          <img
            src={screenshotUrl}
            alt={bug.title}
            className="max-h-40 w-full cursor-pointer rounded-lg border border-gray-200 object-cover transition-colors hover:border-indigo-300"
            loading="lazy"
          />
        </a>
      )}

      <div className="mt-3 border-t border-gray-100 pt-3">
        <span className="font-mono text-xs text-gray-300">{bug.test_id}</span>
      </div>
    </article>
  );
}
