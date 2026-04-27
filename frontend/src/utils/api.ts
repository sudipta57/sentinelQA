import type { SSEEvent } from "../types";

const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
export const BACKEND_URL = env?.VITE_BACKEND_URL || "http://localhost:8000";

export async function* streamAgentRun(url: string): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${BACKEND_URL}/api/run-agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!response.ok || !response.body) {
    throw new Error(`Backend error: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("data: ")) {
        const jsonStr = trimmed.slice(6).trim();
        if (!jsonStr) {
          continue;
        }
        try {
          const event = JSON.parse(jsonStr) as SSEEvent;
          yield event;
        } catch {
          // Skip malformed stream lines.
        }
      }
    }
  }
}

