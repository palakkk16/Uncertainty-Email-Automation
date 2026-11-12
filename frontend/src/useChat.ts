import { useRef, useState } from "react";
import { ChatRequestError, postChat } from "./api.ts";
import { recordSendCard } from "./auditLog.ts";
import {
  MAX_MESSAGE_LENGTH,
  exceedsMessageCap,
  stitchUserTurns,
} from "./stitch.ts";
import { clearThread, maxTurnId, readThread, writeThread } from "./thread.ts";
import { assistantTurn, isDelivered } from "./turns.ts";
import type { Turn } from "./types.ts";

export const CAP_ERROR =
  "That would make the instruction longer than 4000 characters. Shorten it and try again.";

const NETWORK = "Cannot reach the API.";

export function useChat() {
  const initial = useRef(readThread());
  const [turns, setTurns] = useState<Turn[]>(initial.current.turns);
  const [draft, setDraft] = useState(initial.current.draft);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const ids = useRef(maxTurnId(initial.current.turns));
  const busy = useRef(false);

  const userTexts = turns.flatMap((turn) =>
    turn.role === "user" ? [turn.text] : [],
  );
  const pendingTurns = draft.trim() ? [...userTexts, draft] : userTexts;
  const pendingLength = stitchUserTurns(pendingTurns).length;
  // Every check re-posts all user turns, so a delivered thread would send again.
  const delivered = turns.some(isDelivered);

  function updateDraft(value: string) {
    setDraft(value);
    writeThread(turns, value);
    if (exceedsMessageCap([...userTexts, value])) {
      setError(CAP_ERROR);
      return;
    }
    if (error === CAP_ERROR) {
      setError(null);
    }
  }

  function reset() {
    if (busy.current) {
      return;
    }
    clearThread();
    setTurns([]);
    setDraft("");
    setError(null);
  }

  async function submit() {
    if (busy.current || loading || delivered) {
      return;
    }
    const text = draft.trim();
    if (!text) {
      return;
    }
    if (exceedsMessageCap([...userTexts, text])) {
      setError(CAP_ERROR);
      return;
    }
    busy.current = true;
    setLoading(true);
    setError(null);
    try {
      const response = await postChat(stitchUserTurns([...userTexts, text]));
      const userId = nextId(ids);
      const assistantId = nextId(ids);
      const assistant = assistantTurn(response, assistantId);
      const next: Turn[] = [
        ...turns,
        { id: userId, role: "user", text },
        assistant,
      ];
      if (assistant.role === "assistant" && assistant.decision === "SEND") {
        recordSendCard(turns, assistant);
      }
      writeThread(next, "");
      setTurns(next);
      setDraft("");
    } catch (err) {
      setError(err instanceof ChatRequestError ? err.message : NETWORK);
    } finally {
      busy.current = false;
      setLoading(false);
    }
  }

  return {
    turns,
    draft,
    error,
    loading,
    delivered,
    pendingLength,
    maxLength: MAX_MESSAGE_LENGTH,
    updateDraft,
    submit,
    reset,
  };
}

export type ChatController = ReturnType<typeof useChat>;

function nextId(ids: { current: number }): string {
  ids.current += 1;
  return String(ids.current);
}
