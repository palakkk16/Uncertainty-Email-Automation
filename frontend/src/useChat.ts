import { useRef, useState } from "react";
import { ChatRequestError, postChat } from "./api.ts";
import {
  MAX_MESSAGE_LENGTH,
  exceedsMessageCap,
  stitchUserTurns,
} from "./stitch.ts";
import { assistantTurn, isDelivered } from "./turns.ts";
import type { Turn } from "./types.ts";

export const CAP_ERROR =
  "That would make the instruction longer than 4000 characters. Shorten it and try again.";

const NETWORK = "Cannot reach the API.";

export function useChat() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const ids = useRef(0);
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
      setTurns((current) => [
        ...current,
        { id: userId, role: "user", text },
        assistantTurn(response, assistantId),
      ]);
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

function nextId(ids: { current: number }): string {
  ids.current += 1;
  return String(ids.current);
}
