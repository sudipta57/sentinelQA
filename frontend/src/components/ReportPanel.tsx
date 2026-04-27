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
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-12 w-12 text-gray-400">
      <path
        fill="currentColor"
        d="M12 2l8 3v6c0 5.5-3.8 10.7-8 12-4.2-1.3-8-6.5-8-12V5l8-3zm0 2.1L6 6.3V11c0 4.3 2.8 8.7 6 10 3.2-1.3 6-5.7 6-10V6.3l-6-2.2z"
      />
    </svg>
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
      <section className="flex h-full min-h-0 flex-col items-center justify-center overflow-hidden rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col items-center gap-4 text-center text-gray-400">
          <ShieldIcon />
          <p className="text-sm">Run SentinelQA to scan a URL</p>
        </div>
      </section>
    );
  }

  if (isRunning && !report) {
    return (
      <section className="flex h-full min-h-0 flex-col items-center justify-center overflow-hidden rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col items-center gap-3 text-center text-gray-900">
          <span className="h-6 w-6 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
          <p className="text-sm">Scanning...</p>
        </div>
      </section>
    );
  }

  if (error && !report) {
    return (
      <section className="flex h-full min-h-0 flex-col overflow-y-auto rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-rose-700">
          <p className="font-semibold">Agent run failed</p>
          <p className="mt-1 text-sm text-rose-600">{error}</p>
          <p className="mt-3 text-xs text-rose-500">Try again</p>
        </div>
      </section>
    );
  }

  if (!report) {
    return <section className="h-full min-h-0 rounded-xl border border-gray-200 bg-white shadow-sm" />;
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
    <section className="flex h-full min-h-0 flex-col overflow-y-auto rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard label="Total Tests" value={report.total_tests} color="default" />
          <StatCard label="Passed" value={report.passed} color="green" />
          <StatCard label="Failed" value={report.failed} color="red" />
          <StatCard label="Bugs Found" value={totalBugs} color="red" />
        </div>

        <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
          <p className="text-sm italic text-gray-600">{report.summary}</p>
        </div>

        <div className="flex items-center justify-between gap-3 text-xs text-gray-500">
          <span>{`${report.app_url} • ${report.total_tests} tests • ${(report.run_duration_ms / 1000).toFixed(1)}s`}</span>
          <button
            type="button"
            onClick={handleDownloadReport}
            className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-500 transition-colors hover:border-gray-400 hover:text-gray-900"
          >
            ↓ Download JSON
          </button>
        </div>

        {totalBugs === 0 && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
            {`✓ No bugs found — all ${report.total_tests} tests passed!`}
          </div>
        )}

        {critical.length > 0 && (
          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-rose-700">
              <span className="h-2 w-2 rounded-full bg-red-500" />
              Critical <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">{critical.length}</span>
            </h3>
            <div className="space-y-4">
              {critical.map((bug) => (
                <BugCard key={`${bug.test_id}-${bug.title}`} bug={bug} backendUrl={backendUrl} />
              ))}
            </div>
          </div>
        )}

        {major.length > 0 && (
          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-amber-700">
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              Major <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">{major.length}</span>
            </h3>
            <div className="space-y-4">
              {major.map((bug) => (
                <BugCard key={`${bug.test_id}-${bug.title}`} bug={bug} backendUrl={backendUrl} />
              ))}
            </div>
          </div>
        )}

        {minor.length > 0 && (
          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-sky-700">
              <span className="h-2 w-2 rounded-full bg-sky-500" />
              Minor <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">{minor.length}</span>
            </h3>
            <div className="space-y-4">
              {minor.map((bug) => (
                <BugCard key={`${bug.test_id}-${bug.title}`} bug={bug} backendUrl={backendUrl} />
              ))}
            </div>
          </div>
        )}

        <div className="space-y-3 pt-2">
          <h3 className="text-sm font-semibold text-gray-700">Recommendations</h3>
          <ul className="space-y-3">
            {report.recommendations.map((recommendation, index) => (
              <li key={`rec-${index}`} className="flex items-start rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
                <span className="mr-2 text-xs font-bold text-indigo-600">{index + 1}.</span>
                <span>{recommendation}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
