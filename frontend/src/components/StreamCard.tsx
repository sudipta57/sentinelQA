import type { SSEEvent } from "../types";

interface StreamCardProps {
  event: SSEEvent;
}

type VariantStyle = {
  border: string;
  badge: string;
};

const VARIANT_STYLES: Record<string, VariantStyle> = {
  tool_call: { border: "border-purple-500", badge: "bg-purple-500/20 text-purple-300" },
  tool_result: { border: "border-teal-500", badge: "bg-teal-500/20 text-teal-300" },
  agent_thought: { border: "border-amber-500", badge: "bg-amber-500/20 text-amber-300" },
  complete: { border: "border-green-500", badge: "bg-green-500/20 text-green-300" },
  error: { border: "border-red-500", badge: "bg-red-500/20 text-red-300" },
  unknown: { border: "border-gray-600", badge: "bg-gray-700 text-gray-200" },
};

const STEP_VARIANT_OVERRIDES: Record<string, VariantStyle> = {
  suggest_fix: { border: "border-green-500", badge: "bg-green-500/20 text-green-300" },
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
    return <p className="text-sm italic text-gray-300">{text ?? ""}</p>;
  }

  if (event.type === "tool_call") {
    const keys = payload && typeof payload === "object" ? Object.keys(payload) : [];
    return (
      <div className="space-y-2">
        <p className="text-sm text-purple-200">{`→ Calling: ${event.step}`}</p>
        {keys.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {keys.map((key) => (
              <span
                key={key}
                className="rounded-full border border-gray-700 bg-gray-800 px-2 py-0.5 text-[11px] text-gray-300"
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
      return <p className="text-sm text-gray-300">No result payload.</p>;
    }
    return (
      <div className="space-y-1 text-xs text-gray-300">
        {entries.map(([key, value]) => (
          <div key={key} className="grid grid-cols-[120px_1fr] gap-2">
            <span className="text-gray-500">{key}:</span>
            <span className="break-all">{truncateValue(value)}</span>
          </div>
        ))}
      </div>
    );
  }

  if (event.type === "complete") {
    return <p className="text-sm font-semibold text-green-300">✓ Pipeline complete</p>;
  }

  if (event.type === "error") {
    if (typeof payload === "string") {
      return <p className="text-sm text-red-300">{payload}</p>;
    }
    if (payload && typeof payload === "object" && "message" in payload && typeof payload.message === "string") {
      return <p className="text-sm text-red-300">{payload.message}</p>;
    }
    return <p className="text-sm text-red-300">Unexpected agent error.</p>;
  }

  return <p className="text-sm text-gray-300">Unsupported event payload.</p>;
}

export default function StreamCard({ event }: StreamCardProps): JSX.Element {
  // Check for step-specific overrides first, then fall back to event type styling
  const style = STEP_VARIANT_OVERRIDES[event.step] ?? VARIANT_STYLES[event.type] ?? VARIANT_STYLES.unknown;

  return (
    <article
      className={`stream-card-enter sentinel-fade-in rounded-lg border-l-4 ${style.border} bg-gray-900 p-3 transition-opacity duration-150`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${style.badge}`}>
            {event.type}
          </span>
          <span className="text-xs text-gray-500">{event.step}</span>
        </div>
        <span className="text-xs text-gray-500">{toTimeLabel(event.timestamp)}</span>
      </div>

      {renderPayload(event)}
    </article>
  );
}
