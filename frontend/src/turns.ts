import type { ChatResponse, Turn } from "./types.ts";

const NO_SEND_SENTENCE = "No email was sent.";

/**
 * A SEND decision is not delivery. The confirmation must say that no
 * email was sent, so recipient, subject, and body cannot be read as a
 * message that left this machine. This UI has no mail-send call.
 */
export function assistantTurn(response: ChatResponse, id: string): Turn {
  if (response.decision === "SEND") {
    return {
      id,
      role: "assistant",
      decision: "SEND",
      sentence: withNoSendSentence(response.reply),
      extraction: response.extraction,
    };
  }
  const question = response.clarification?.trim() || response.reply.trim();
  return {
    id,
    role: "assistant",
    decision: "ASK",
    text: question || "The instruction is still incomplete.",
  };
}

function withNoSendSentence(reply: string): string {
  if (reply.includes(NO_SEND_SENTENCE)) {
    return reply;
  }
  const trimmed = reply.trim();
  if (trimmed.length === 0) {
    return `The decision is SEND. ${NO_SEND_SENTENCE}`;
  }
  return `${trimmed} ${NO_SEND_SENTENCE}`;
}
