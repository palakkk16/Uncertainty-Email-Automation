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

function normalizeEmail(email?: string): string {
  return email?.trim().toLowerCase() ?? "";
}

function scopedKey(email?: string): string {
  const who = normalizeEmail(email);
  return who ? `${GMAIL_KEY}:${who}` : GMAIL_KEY;
}

export function readGmailToken(email?: string): GmailAccess | null {
  const who = normalizeEmail(email);
  const keys = who ? [scopedKey(who), GMAIL_KEY] : [GMAIL_KEY];
  for (const key of keys) {
    const value = readStored(key);
    if (value === null) {
      continue;
    }
    if (who && normalizeEmail(value.email) !== who) {
      continue;
    }
    return value;
  }
  return null;
}

export function activeGmailAccessToken(email?: string): string | null {
  return readGmailToken(email)?.accessToken ?? null;
}

export function writeGmailToken(value: GmailAccess): void {
  const payload = JSON.stringify(value);
  sessionStorage.setItem(scopedKey(value.email), payload);
  sessionStorage.setItem(GMAIL_KEY, payload);
  notify();
}

export function clearGmailToken(email?: string): void {
  if (email) {
    sessionStorage.removeItem(scopedKey(email));
  }
  sessionStorage.removeItem(GMAIL_KEY);
  const prefix = `${GMAIL_KEY}:`;
  const stale: string[] = [];
  for (let index = 0; index < sessionStorage.length; index += 1) {
    const key = sessionStorage.key(index);
    if (key?.startsWith(prefix)) {
      stale.push(key);
    }
  }
  for (const key of stale) {
    sessionStorage.removeItem(key);
  }
  notify();
}

function readStored(key: string): GmailAccess | null {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) {
      return null;
    }
    const value: unknown = JSON.parse(raw);
    if (!isGmailAccess(value)) {
      sessionStorage.removeItem(key);
      return null;
    }
    if (value.expiresAt <= Date.now()) {
      sessionStorage.removeItem(key);
      return null;
    }
    return value;
  } catch {
    return null;
  }
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
