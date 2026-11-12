import { useEffect, useRef } from "react";
import type { AskTurn, SendTurn, Turn, UserTurn } from "./types.ts";

type MessageListProps = {
  turns: Turn[];
  loading: boolean;
};

export function MessageList({ turns, loading }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [turns, loading]);

  return (
    <div
      className="thread"
      role="log"
      aria-live="polite"
      aria-relevant="additions"
      aria-busy={loading}
    >
      {turns.length === 0 ? <EmptyState /> : null}
      {turns.map((turn) => (
        <TurnView key={turn.id} turn={turn} />
      ))}
      {loading ? (
        <p className="status" role="status">
          Checking the instruction…
        </p>
      ) : null}
      <div ref={endRef} />
    </div>
  );
}

function EmptyState() {
  return (
    <p className="empty">
      Describe what you want to write. The agent asks for missing details
      and drafts a complete email. It is sent only if dispatch is on.
    </p>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  if (turn.role === "user") {
    return <UserBubble turn={turn} />;
  }
  if (turn.decision === "ASK") {
    return <AskBubble turn={turn} />;
  }
  return <SendCard turn={turn} />;
}

function UserBubble({ turn }: { turn: UserTurn }) {
  return (
    <article className="bubble user">
      <p className="who">You</p>
      <p className="text">{turn.text}</p>
    </article>
  );
}

function AskBubble({ turn }: { turn: AskTurn }) {
  return (
    <article className="bubble ask">
      <p className="who">Question</p>
      <p className="text">{turn.text}</p>
    </article>
  );
}

const SEND_HEADINGS: Record<SendTurn["dispatch"], { who: string; label: string }> = {
  sent: { who: "Sent", label: "Email sent." },
  already_sent: { who: "Already sent", label: "Email already sent. Not sent again." },
  disabled: { who: "Decision", label: "Send decision. No email was sent." },
  rejected: { who: "Preview", label: "Send decision. Recipient is not on the allowlist. No email was sent." },
};

function SendCard({ turn }: { turn: SendTurn }) {
  const heading = SEND_HEADINGS[turn.dispatch];
  return (
    <article className="bubble send" aria-label={heading.label}>
      <p className="who">{heading.who}</p>
      <p className="sentence">{turn.sentence}</p>
      <dl>
        <div>
          <dt>Recipient</dt>
          <dd>{stated(turn.extraction.recipient)}</dd>
        </div>
        <div>
          <dt>Subject</dt>
          <dd>{stated(turn.extraction.subject)}</dd>
        </div>
        <div>
          <dt>Body</dt>
          <dd>{stated(turn.extraction.body)}</dd>
        </div>
      </dl>
    </article>
  );
}

function stated(value: string | null): string {
  const trimmed = value?.trim() ?? "";
  return trimmed.length > 0 ? trimmed : "Not stated";
}
