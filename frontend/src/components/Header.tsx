export default function Header(): JSX.Element {
  return (
    <header className="w-full border-b border-gray-800 bg-gray-950 px-6 py-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-white">SentinelQA</h1>
          <span className="rounded-full bg-purple-600/20 px-2 py-1 text-xs font-semibold text-purple-300">
            v1.0
          </span>
        </div>
        <p className="text-sm text-gray-400">Autonomous Bug Hunter Agent</p>
      </div>
    </header>
  );
}
