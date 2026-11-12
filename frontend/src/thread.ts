import type { DispatchStatus, EmailExtraction, Turn } from "./types.ts";

const THREAD_KEY = "uncertain-email-thread";

export type StoredThread = {
  turns: Turn[];
  draft: string;
};

export function readThread(): StoredThread {
  try {
    const raw = sessionStorage.getItem(THREAD_KEY);
    if (!raw) {
      return emptyThread();
    }
    const value: unknown = JSON.parse(raw);
    if (!isRecord(value) || !Array.isArray(value.turns) || typeof value.draft !== "string") {
      return emptyThread();
    }
    return { turns: value.turns.filter(isTurn), draft: value.draft };
  } catch {
    return emptyThread();
  }
}

export function writeThread(turns: Turn[], draft: string): void {
  sessionStorage.setItem(THREAD_KEY, JSON.stringify({ turns, draft }));
}

export function clearThread(): void {
  sessionStorage.removeItem(THREAD_KEY);
}

export function maxTurnId(turns: Turn[]): number {
  let max = 0;
  for (const turn of turns) {
    const n = Number(turn.id);
    if (Number.isFinite(n) && n > max) {
      max = n;
    }
  }
  return max;
}

function emptyThread(): StoredThread {
  return { turns: [], draft: "" };
}

function isTurn(value: unknown): value is Turn {
  if (!isRecord(value) || typeof value.id !== "string") {
    return false;
  }
  if (value.role === "user") {
    return typeof value.text === "string";
  }
  if (value.role !== "assistant") {
    return false;
  }
  if (value.decision === "ASK") {
    return typeof value.text === "string";
  }
  if (value.decision !== "SEND") {
    return false;
  }
  return (
    isDispatchStatus(value.dispatch) &&
    typeof value.sentence === "string" &&
    isExtraction(value.extraction)
  );
}

function isDispatchStatus(value: unknown): value is DispatchStatus {
  return (
    value === "sent" ||
    value === "disabled" ||
    value === "already_sent" ||
    value === "rejected"
  );
}

function isExtraction(value: unknown): value is EmailExtraction {
  if (!isRecord(value)) {
    return false;
  }
  return (
    isNullableString(value.recipient) &&
    isNullableString(value.subject) &&
    isNullableString(value.body) &&
    isNullableString(value.recipient_mention)
  );
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
