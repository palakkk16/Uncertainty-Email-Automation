import type { DispatchStatus, SendTurn, Turn } from "./types.ts";

const AUDIT_KEY = "uncertain-email-audit";
const AUDIT_LIMIT = 50;

type AuditListener = () => void;

const listeners = new Set<AuditListener>();

function notifyAuditListeners(): void {
  for (const listener of listeners) {
    listener();
  }
}

export function subscribeAuditLog(listener: AuditListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export type AuditStatus = "SENT" | "PREVIEW";

export type AuditEntry = {
  id: string;
  timestamp: string;
  recipient: string;
  subject: string;
  bodyPreview: string;
  status: AuditStatus;
  clarificationTurns: number;
};

export function readAuditLog(): AuditEntry[] {
  try {
    const raw = localStorage.getItem(AUDIT_KEY);
    if (!raw) {
      return [];
    }
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) {
      return [];
    }
    return value.filter(isAuditEntry);
  } catch {
    return [];
  }
}

export function recordSendCard(turns: Turn[], send: SendTurn): void {
  const asks = turns.filter(
    (turn) => turn.role === "assistant" && turn.decision === "ASK",
  ).length;
  const entry: AuditEntry = {
    id: `${Date.now()}-${send.id}`,
    timestamp: new Date().toISOString(),
    recipient: previewText(send.extraction.recipient, "Not stated"),
    subject: previewText(send.extraction.subject, "Not stated"),
    bodyPreview: clip(previewText(send.extraction.body, "Not stated"), 96),
    status: auditStatus(send.dispatch),
    clarificationTurns: asks,
  };
  const next = [entry, ...readAuditLog()].slice(0, AUDIT_LIMIT);
  localStorage.setItem(AUDIT_KEY, JSON.stringify(next));
  notifyAuditListeners();
}

export function clearAuditLog(): void {
  localStorage.removeItem(AUDIT_KEY);
  notifyAuditListeners();
}

export function auditStatus(dispatch: DispatchStatus): AuditStatus {
  return dispatch === "sent" || dispatch === "already_sent" ? "SENT" : "PREVIEW";
}

function previewText(value: string | null, fallback: string): string {
  const trimmed = value?.trim() ?? "";
  return trimmed.length > 0 ? trimmed : fallback;
}

function clip(value: string, max: number): string {
  if (value.length <= max) {
    return value;
  }
  return `${value.slice(0, max - 1)}…`;
}

function isAuditEntry(value: unknown): value is AuditEntry {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "string" &&
    typeof record.timestamp === "string" &&
    typeof record.recipient === "string" &&
    typeof record.subject === "string" &&
    typeof record.bodyPreview === "string" &&
    (record.status === "SENT" || record.status === "PREVIEW") &&
    typeof record.clarificationTurns === "number"
  );
}
