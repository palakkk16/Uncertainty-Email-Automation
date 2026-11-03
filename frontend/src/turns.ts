import type { ChatResponse, DispatchStatus, SendTurn, Turn } from "./types.ts";

const NO_SEND_SENTENCE = "No email was sent.";

/**
 * A SEND decision is delivery only when the API says `sent` or
 * `already_sent`. With dispatch disabled the confirmation must say that no
 * email was sent, so recipient, subject, and body cannot be read as a
 * message that left this machine.
 */
export function assistantTurn(response: ChatResponse, id: string): Turn {
  if (response.decision === "SEND") {
    const dispatch = response.dispatch?.status ?? "disabled";
    return {
      id,
      role: "assistant",
      decision: "SEND",
      dispatch,
      sentence: sendSentence(response, dispatch),
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

/** True once an email left the server, so the thread must not be re-posted. */
export function isDelivered(turn: Turn): turn is SendTurn {
  return (
    turn.role === "assistant" &&
    turn.decision === "SEND" &&
    (turn.dispatch === "sent" || turn.dispatch === "already_sent")
  );
}

function sendSentence(response: ChatResponse, dispatch: DispatchStatus): string {
  const reply = response.reply.trim();
  if (dispatch === "disabled" || dispatch === "rejected") {
    return withNoSendSentence(reply);
  }
  if (reply.length > 0) {
    return reply;
  }
  return dispatch === "sent" ? "Email sent." : "This email was already sent.";
}

function withNoSendSentence(reply: string): string {
  if (reply.includes(NO_SEND_SENTENCE)) {
    return reply;
  }
  if (reply.length === 0) {
    return `The decision is SEND. ${NO_SEND_SENTENCE}`;
  }
  return `${reply} ${NO_SEND_SENTENCE}`;
}
