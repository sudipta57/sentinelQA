export default function Header(): JSX.Element {
  return (
    <header className="flex h-14 w-full items-center justify-between border-b border-gray-200 bg-white px-8">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold text-gray-900">SentinelQA</h1>
        <span className="text-xs text-gray-400">•</span>
        <p className="text-sm text-gray-500">Autonomous QA Agent</p>
      </div>
      <span className="rounded-full border border-gray-200 bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500">
        Powered by Gemini
      </span>
    </header>
  );
}
