import { activeGmailAccessToken, clearGmailToken } from "./gmailToken.ts";
import { readSession, type Session } from "./session.ts";
import type { ChatResponse, DispatchResult, EmailExtraction } from "./types.ts";

export type ChatFailureKind =
  | "rate_limit"
  | "extraction"
  | "dispatch"
  | "network"
  | "rejected"
  | "unexpected";

export class ChatRequestError extends Error {
  readonly kind: ChatFailureKind;

  constructor(kind: ChatFailureKind, message: string) {
    super(message);
    this.name = "ChatRequestError";
    this.kind = kind;
  }
}

const RATE_LIMIT = "Gemini rate limit. Wait and try again.";
const EXTRACTION = "Extraction failed. Try again.";
const NETWORK = "Cannot reach the API.";
const REJECTED =
  "That instruction was not accepted. Keep it between 1 and 4000 characters.";
const UNEXPECTED = "The API returned an unexpected error. Try again.";

// Keyed by the API's fixed `detail` text. Every one of these means no email left.
const DISPATCH_ERRORS: Record<string, string> = {
  "Email dispatch failed.": "The email was not sent. Gmail failed. Try again.",
  "Email dispatch is unavailable.":
    "The email was not sent. The server's Gmail sign-in needs attention.",
  "Recipient is not on the dispatch allowlist.":
    "The email was not sent. That recipient is not on the dispatch allowlist.",
  "Reconnect Gmail.": "Reconnect Gmail to send from your account.",
};

export async function postChat(message: string): Promise<ChatResponse> {
  const response = await readResponse(message);
  if (response.status === 429) {
    throw new ChatRequestError("rate_limit", RATE_LIMIT);
  }
  if (response.status === 401) {
    clearGmailToken();
    throw new ChatRequestError("dispatch", "Reconnect Gmail to send from your account.");
  }
  if ([403, 502, 503].includes(response.status)) {
    throw await serverError(response);
  }
  if (response.status === 422) {
    throw new ChatRequestError("rejected", REJECTED);
  }
  if (!response.ok) {
    throw new ChatRequestError("unexpected", UNEXPECTED);
  }
  return parseChatResponse(response);
}

async function readResponse(message: string): Promise<Response> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  const gmailToken = activeGmailAccessToken();
  if (gmailToken) {
    headers["X-Gmail-Token"] = gmailToken;
  }
  try {
    return await fetch("/chat", {
      method: "POST",
      headers,
      body: JSON.stringify({ message }),
    });
  } catch {
    throw new ChatRequestError("network", NETWORK);
  }
}

async function serverError(response: Response): Promise<ChatRequestError> {
  const dispatch = DISPATCH_ERRORS[await readDetail(response)];
  if (dispatch) {
    return new ChatRequestError("dispatch", dispatch);
  }
  if (response.status === 403) {
    return new ChatRequestError("unexpected", UNEXPECTED);
  }
  return new ChatRequestError("extraction", EXTRACTION);
}

async function readDetail(response: Response): Promise<string> {
  try {
    const payload: unknown = await response.json();
    return isRecord(payload) && typeof payload.detail === "string"
      ? payload.detail
      : "";
  } catch {
    return "";
  }
}

async function parseChatResponse(response: Response): Promise<ChatResponse> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ChatRequestError("unexpected", UNEXPECTED);
  }
  if (!isChatResponse(payload)) {
    throw new ChatRequestError("unexpected", UNEXPECTED);
  }
  return payload;
}

function isChatResponse(value: unknown): value is ChatResponse {
  if (!isRecord(value)) {
    return false;
  }
  if (value.phase !== "decision_layer") {
    return false;
  }
  if (value.decision !== "ASK" && value.decision !== "SEND") {
    return false;
  }
  if (typeof value.reply !== "string") {
    return false;
  }
  if (value.clarification !== null && typeof value.clarification !== "string") {
    return false;
  }
  if (!isExtraction(value.extraction) || !isAssessment(value.assessment)) {
    return false;
  }
  // SEND must say whether mail left. ASK never dispatches.
  if (value.decision === "SEND") {
    return isDispatch(value.dispatch);
  }
  return value.dispatch === null;
}

function isDispatch(value: unknown): value is DispatchResult {
  if (!isRecord(value)) {
    return false;
  }
  return (
    (value.status === "sent" ||
      value.status === "disabled" ||
      value.status === "already_sent" ||
      value.status === "rejected") &&
    isNullableString(value.message_id)
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

function isAssessment(value: unknown): boolean {
  if (!isRecord(value)) {
    return false;
  }
  return (
    value.method === "slot_sufficiency_threshold" &&
    typeof value.resolved_fraction === "number"
  );
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

const AUTH_REJECTED = "Google sign-in was not accepted.";
const AUTH_UNCONFIGURED = "Google sign-in is not configured.";
const INVALID_PASSWORD = "Invalid email or password.";
const DUPLICATE_EMAIL = "An account with that email already exists.";
const WEAK_PASSWORD =
  "Use a name, a valid email, and a password of at least 8 characters with a letter and a number.";

export async function loginWithPassword(
  email: string,
  password: string,
): Promise<Session> {
  return postPasswordAuth("/auth/login", { email, password });
}

export async function registerAccount(
  name: string,
  email: string,
  password: string,
): Promise<Session> {
  return postPasswordAuth("/auth/register", { name, email, password });
}

async function postPasswordAuth(
  path: "/auth/login" | "/auth/register",
  body: Record<string, string>,
): Promise<Session> {
  const existing = readSession();
  if (existing) {
    return existing;
  }
  let response: Response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ChatRequestError("network", NETWORK);
  }
  if (response.status === 401) {
    throw new ChatRequestError("rejected", INVALID_PASSWORD);
  }
  if (response.status === 409) {
    throw new ChatRequestError("rejected", DUPLICATE_EMAIL);
  }
  if (response.status === 422) {
    throw new ChatRequestError("rejected", path === "/auth/register" ? WEAK_PASSWORD : INVALID_PASSWORD);
  }
  if (!response.ok) {
    throw new ChatRequestError("unexpected", UNEXPECTED);
  }
  return readAuthProfile(response);
}

export async function verifyGoogleCredential(credential: string): Promise<Session> {
  const existing = readSession();
  if (existing) {
    return existing;
  }
  let response: Response;
  try {
    response = await fetch("/auth/google", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ credential }),
    });
  } catch {
    throw new ChatRequestError("network", NETWORK);
  }
  if (response.status === 401) {
    throw new ChatRequestError("rejected", AUTH_REJECTED);
  }
  if (response.status === 503) {
    throw new ChatRequestError("unexpected", AUTH_UNCONFIGURED);
  }
  if (!response.ok) {
    throw new ChatRequestError("unexpected", UNEXPECTED);
  }
  return readAuthProfile(response);
}

async function readAuthProfile(response: Response): Promise<Session> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ChatRequestError("unexpected", UNEXPECTED);
  }
  if (!isGoogleProfile(payload)) {
    throw new ChatRequestError("unexpected", UNEXPECTED);
  }
  return payload;
}

function isGoogleProfile(value: unknown): value is Session {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.name === "string" &&
    value.name.length > 0 &&
    typeof value.email === "string" &&
    value.email.includes("@") &&
    typeof value.picture === "string"
  );
}
