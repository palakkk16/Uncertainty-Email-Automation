const GMAIL_KEY = "uncertain-email-gmail";

export type GmailAccess = {
  accessToken: string;
  expiresAt: number;
  email: string;
};

type Listener = () => void;

const listeners = new Set<Listener>();

function notify(): void {
  for (const listener of listeners) {
    listener();
  }
}

export function subscribeGmailToken(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function readGmailToken(): GmailAccess | null {
  try {
    const raw = sessionStorage.getItem(GMAIL_KEY);
    if (!raw) {
      return null;
    }
    const value: unknown = JSON.parse(raw);
    if (!isGmailAccess(value)) {
      sessionStorage.removeItem(GMAIL_KEY);
      return null;
    }
    if (value.expiresAt <= Date.now()) {
      sessionStorage.removeItem(GMAIL_KEY);
      return null;
    }
    return value;
  } catch {
    return null;
  }
}

export function activeGmailAccessToken(): string | null {
  return readGmailToken()?.accessToken ?? null;
}

export function writeGmailToken(value: GmailAccess): void {
  sessionStorage.setItem(GMAIL_KEY, JSON.stringify(value));
  notify();
}

export function clearGmailToken(): void {
  sessionStorage.removeItem(GMAIL_KEY);
  notify();
}

function isGmailAccess(value: unknown): value is GmailAccess {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.accessToken === "string" &&
    record.accessToken.length > 0 &&
    typeof record.expiresAt === "number" &&
    typeof record.email === "string" &&
    record.email.includes("@")
  );
}
