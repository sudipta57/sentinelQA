import { useEffect, useRef } from "react";
import StreamCard from "./StreamCard";
import type { SSEEvent } from "../types";

interface StreamPanelProps {
  events: SSEEvent[];
  isRunning: boolean;
}

function TerminalIcon(): JSX.Element {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-10 w-10 text-gray-400">
      <path
        fill="currentColor"
        d="M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5zm2 0v14h14V5H5zm2.2 3.6L10.6 12l-3.4 3.4-1.2-1.2 2.2-2.2-2.2-2.2 1.2-1.2zM12 15h6v2h-6v-2z"
      />
    </svg>
  );
}

export default function StreamPanel({ events, isRunning }: StreamPanelProps): JSX.Element {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events]);

  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <header className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
        <h2 className="text-sm font-semibold text-gray-700">Agent Log</h2>
        {isRunning && <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-400" />}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto bg-gray-50 p-6">
        {events.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-gray-400">
            <TerminalIcon />
            <p className="text-sm">Waiting for agent...</p>
          </div>
        ) : (
          <div className="space-y-3">
            {events.map((event, index) => (
              <StreamCard key={`${event.timestamp}-${event.type}-${index}`} event={event} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
    </section>
  );
}
