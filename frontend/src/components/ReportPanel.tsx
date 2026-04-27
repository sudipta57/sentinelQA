import BugCard from "./BugCard";
import StatCard from "./StatCard";
import type { Report } from "../types";

interface ReportPanelProps {
  report: Report | null;
  isRunning: boolean;
  error: string | null;
  backendUrl: string;
}

function ShieldIcon(): JSX.Element {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-12 w-12 text-gray-700">
      <path
        fill="currentColor"
        d="M12 2l8 3v6c0 5.5-3.8 10.7-8 12-4.2-1.3-8-6.5-8-12V5l8-3zm0 2.1L6 6.3V11c0 4.3 2.8 8.7 6 10 3.2-1.3 6-5.7 6-10V6.3l-6-2.2z"
      />
    </svg>
  );
}

function Spinner(): JSX.Element {
  return <span className="h-7 w-7 animate-spin rounded-full border-2 border-gray-300 border-t-transparent" />;
}

function RunningDots(): JSX.Element {
  return (
    <span className="inline-flex gap-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.2s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:-0.1s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" />
    </span>
  );
}

export default function ReportPanel({
  report,
  isRunning,
  error,
  backendUrl,
}: ReportPanelProps): JSX.Element {
  if (!report && !isRunning && !error) {
    return (
      <section className="flex h-full min-h-0 items-center justify-center bg-gray-950 p-6">
        <div className="flex flex-col items-center gap-4 text-center text-gray-500">
          <ShieldIcon />
          <p className="text-sm">Run SentinelQA to see results</p>
        </div>
      </section>
    );
  }

  if (isRunning && !report) {
    return (
      <section className="flex h-full min-h-0 items-center justify-center bg-gray-950 p-6">
        <div className="flex flex-col items-center gap-3 text-center text-gray-300">
          <Spinner />
          <p className="text-sm">Agent is analysing your app...</p>
          <RunningDots />
        </div>
      </section>
    );
  }

  if (error && !report) {
    return (
      <section className="h-full min-h-0 overflow-y-auto bg-gray-950 p-6">
        <div className="rounded-lg border border-red-800 bg-red-950/40 p-4 text-red-200">
          <p className="font-semibold">Agent run failed</p>
          <p className="mt-1 text-sm">{error}</p>
          <p className="mt-3 text-xs text-red-300/80">Try again</p>
        </div>
      </section>
    );
  }

  if (!report) {
    return <section className="h-full min-h-0 bg-gray-950" />;
  }

  const critical = report.bugs_by_severity.critical;
  const major = report.bugs_by_severity.major;
  const minor = report.bugs_by_severity.minor;
  const totalBugs = critical.length + major.length + minor.length;

  const handleDownloadReport = () => {
    if (!report) return;
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const filename = `sentinelqa-report-${timestamp}.json`;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  return (
    <section className="h-full min-h-0 overflow-y-auto bg-gray-950 p-4 md:p-6">
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Total Tests" value={report.total_tests} color="purple" />
          <StatCard label="Passed" value={report.passed} color="green" />
          <StatCard label="Failed" value={report.failed} color="red" />
          <StatCard label="Bugs Found" value={totalBugs} color="red" />
        </div>

        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <p className="text-sm italic text-gray-300">{report.summary}</p>
        </div>

        <div className="flex items-center justify-between gap-3 text-xs text-gray-500">
          <span>{`${report.app_url} • ${report.total_tests} tests • ${(report.run_duration_ms / 1000).toFixed(1)}s`}</span>
          <button
            type="button"
            onClick={handleDownloadReport}
            className="rounded border border-gray-700 bg-gray-900 px-2 py-1 text-xs font-medium text-gray-200 transition hover:border-gray-500 hover:text-white"
          >
            ⬇ Download JSON
          </button>
        </div>

        {totalBugs === 0 && (
          <div className="rounded-lg border border-green-900 bg-green-950/30 p-3 text-sm font-medium text-green-300">
            {`✓ No bugs found — all ${report.total_tests} tests passed!`}
          </div>
        )}

        {critical.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-red-300">🔴 Critical ({critical.length})</h3>
            <div className="space-y-3">
              {critical.map((bug) => (
                <BugCard key={`${bug.test_id}-${bug.title}`} bug={bug} backendUrl={backendUrl} />
              ))}
            </div>
          </div>
        )}

        {major.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-amber-300">🟡 Major ({major.length})</h3>
            <div className="space-y-3">
              {major.map((bug) => (
                <BugCard key={`${bug.test_id}-${bug.title}`} bug={bug} backendUrl={backendUrl} />
              ))}
            </div>
          </div>
        )}

        {minor.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-teal-300">🟢 Minor ({minor.length})</h3>
            <div className="space-y-3">
              {minor.map((bug) => (
                <BugCard key={`${bug.test_id}-${bug.title}`} bug={bug} backendUrl={backendUrl} />
              ))}
            </div>
          </div>
        )}

        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-200">Recommendations</h3>
          <ol className="space-y-2">
            {report.recommendations.map((recommendation, index) => (
              <li key={`rec-${index}`} className="rounded-lg border border-gray-800 bg-gray-900 p-3 text-sm text-gray-300">
                {`${index + 1}. ${recommendation}`}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
