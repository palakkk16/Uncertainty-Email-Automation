const SESSION_KEY = "uncertain-email-session";

export type Session = {
  name: string;
  email: string;
  picture: string;
};

export function readSession(): Session | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) {
      return null;
    }
    const value: unknown = JSON.parse(raw);
    if (!isSession(value)) {
      return null;
    }
    return value;
  } catch {
    return null;
  }
}

export function writeSession(session: Session): void {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearSession(): void {
  localStorage.removeItem(SESSION_KEY);
}

function isSession(value: unknown): value is Session {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.name === "string" &&
    record.name.length > 0 &&
    typeof record.email === "string" &&
    record.email.includes("@") &&
    typeof record.picture === "string"
  );
}
