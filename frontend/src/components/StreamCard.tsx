import type { SSEEvent } from "../types";

interface StreamCardProps {
  event: SSEEvent;
}

type VariantStyle = {
  badge: string;
};

const VARIANT_STYLES: Record<string, VariantStyle> = {
  tool_call: { badge: "border-violet-200 bg-violet-50 text-violet-700" },
  tool_result: { badge: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  agent_thought: { badge: "border-amber-200 bg-amber-50 text-amber-700" },
  complete: { badge: "border-indigo-200 bg-indigo-50 text-indigo-700" },
  error: { badge: "border-rose-200 bg-rose-50 text-rose-700" },
  unknown: { badge: "border-gray-200 bg-gray-50 text-gray-700" },
};

const STEP_VARIANT_OVERRIDES: Record<string, VariantStyle> = {
  suggest_fix: { badge: "border-green-200 bg-green-50 text-green-700" },
};

function toTimeLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleTimeString("en-US", { hour12: false });
}

function truncateValue(value: unknown): string {
  const serialized = typeof value === "string" ? value : JSON.stringify(value);
  if (!serialized) {
    return "";
  }
  return serialized.length > 80 ? `${serialized.slice(0, 80)}...` : serialized;
}

function renderPayload(event: SSEEvent): JSX.Element {
  const payload = event.payload;

  if (event.type === "agent_thought") {
    const text = typeof payload === "string" ? payload : JSON.stringify(payload);
    return <p className="text-sm italic text-gray-500">{text ?? ""}</p>;
  }

  if (event.type === "tool_call") {
    const keys = payload && typeof payload === "object" ? Object.keys(payload) : [];
    return (
      <div className="space-y-2">
        <p className="text-sm text-gray-600">{`→ Calling: ${event.step}`}</p>
        {keys.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {keys.map((key) => (
              <span
                key={key}
                className="rounded border border-gray-200 bg-gray-50 px-2 py-0.5 text-[11px] text-gray-500"
              >
                {key}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (event.type === "tool_result") {
    const entries = payload && typeof payload === "object" ? Object.entries(payload) : [];
    if (entries.length === 0) {
      return <p className="text-sm text-gray-500">No result payload.</p>;
    }
    return (
      <div className="space-y-1 text-xs text-gray-600">
        {entries.map(([key, value]) => (
          <div key={key} className="grid grid-cols-[120px_1fr] gap-2">
            <span className="text-gray-400">{key}:</span>
            <span className="break-all">{truncateValue(value)}</span>
          </div>
        ))}
      </div>
    );
  }

  if (event.type === "complete") {
    return <p className="text-sm text-gray-600">✓ Pipeline complete</p>;
  }

  if (event.type === "error") {
    if (typeof payload === "string") {
      return <p className="text-sm text-rose-600">{payload}</p>;
    }
    if (payload && typeof payload === "object" && "message" in payload && typeof payload.message === "string") {
      return <p className="text-sm text-rose-600">{payload.message}</p>;
    }
    return <p className="text-sm text-rose-600">Unexpected agent error.</p>;
  }

  return <p className="text-sm text-gray-600">Unsupported event payload.</p>;
}

export default function StreamCard({ event }: StreamCardProps): JSX.Element {
  const style = STEP_VARIANT_OVERRIDES[event.step] ?? VARIANT_STYLES[event.type] ?? VARIANT_STYLES.unknown;

  return (
    <article
      className="stream-card-enter sentinel-fade-in mb-2 rounded-lg border border-gray-200 bg-white p-3 shadow-none transition-opacity duration-150"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase ${style.badge}`}>
            {event.type}
          </span>
          <span className="ml-1 text-xs font-mono text-gray-400">{event.step}</span>
        </div>
        <span className="text-xs text-gray-300">{toTimeLabel(event.timestamp)}</span>
      </div>

      {renderPayload(event)}
    </article>
  );
}
