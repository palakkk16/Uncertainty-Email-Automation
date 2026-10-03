import { useId, type FormEvent, type KeyboardEvent } from "react";
import { MessageList } from "./MessageList.tsx";
import { useChat } from "./useChat.ts";

export default function App() {
  const chat = useChat();
  const inputId = useId();
  const errorId = useId();
  const hintId = useId();
  const overCap = chat.pendingLength > chat.maxLength;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void chat.submit();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <div className="app">
      <main className="sheet">
        <header className="header">
          <h1>UNCERTAIN-EMAIL</h1>
          <p>
            Ask until recipient, subject, and body are in your words. This
            page does not send email.
          </p>
        </header>
        <MessageList turns={chat.turns} loading={chat.loading} />
        {chat.error ? (
          <p className="error" id={errorId} role="alert">
            {chat.error}
          </p>
        ) : null}
        <form className="composer" onSubmit={onSubmit}>
          <label htmlFor={inputId}>Email instruction</label>
          <textarea
            id={inputId}
            name="instruction"
            value={chat.draft}
            placeholder="Who is it for, and what should it say?"
            rows={3}
            disabled={chat.loading}
            aria-invalid={chat.error ? true : undefined}
            aria-describedby={chat.error ? `${hintId} ${errorId}` : hintId}
            onChange={(event) => chat.updateDraft(event.target.value)}
            onKeyDown={onKeyDown}
          />
          <button type="submit" disabled={chat.loading || chat.draft.trim().length === 0}>
            {chat.loading ? "Checking…" : "Check"}
          </button>
          <p id={hintId} className={overCap ? "meta over" : "meta"}>
            Characters in the next check: {chat.pendingLength} / {chat.maxLength}.
            Enter checks the instruction. Shift+Enter adds a line.
          </p>
        </form>
      </main>
    </div>
  );
}
