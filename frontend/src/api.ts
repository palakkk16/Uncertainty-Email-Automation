import type { ChatResponse, EmailExtraction } from "./types.ts";

export type ChatFailureKind =
  | "rate_limit"
  | "extraction"
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

export async function postChat(message: string): Promise<ChatResponse> {
  const response = await readResponse(message);
  if (response.status === 429) {
    throw new ChatRequestError("rate_limit", RATE_LIMIT);
  }
  if (response.status === 502 || response.status === 503) {
    throw new ChatRequestError("extraction", EXTRACTION);
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
  try {
    return await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ message }),
    });
  } catch {
    throw new ChatRequestError("network", NETWORK);
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
  return true;
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
