import { useEffect, useState } from "react";
import { AppShell, type AppView } from "./AppShell.tsx";
import { AuditLogView } from "./AuditLogView.tsx";
import { ComposeView } from "./ComposeView.tsx";
import { LoginPage } from "./LoginPage.tsx";
import { clearGmailToken } from "./gmailToken.ts";
import { cancelGooglePrompt, disableGoogleAutoSelect } from "./google.ts";
import { clearSession, readSession, type Session } from "./session.ts";
import { clearThread } from "./thread.ts";
import { useChat } from "./useChat.ts";

export default function App() {
  const [session, setSession] = useState<Session | null>(readSession);

  function onSignOut() {
    disableGoogleAutoSelect();
    cancelGooglePrompt();
    clearGmailToken();
    clearSession();
    clearThread();
    setSession(null);
    window.location.hash = "";
  }

  function onEnter(next: Session) {
    setSession((current) => current ?? next);
  }

  if (session === null) {
    return <LoginPage onEnter={onEnter} />;
  }

  return <Workspace session={session} onSignOut={onSignOut} />;
}

function Workspace({
  session,
  onSignOut,
}: {
  session: Session;
  onSignOut: () => void;
}) {
  const chat = useChat();
  const [view, setView] = useState<AppView>(readView);

  useEffect(() => {
    cancelGooglePrompt();
  }, []);

  function onView(next: AppView) {
    setView(next);
    window.location.hash = next;
  }

  return (
    <AppShell
      view={view}
      session={session}
      onView={onView}
      onSignOut={onSignOut}
    >
      <div className="shell-pane" hidden={view !== "compose"}>
        <ComposeView chat={chat} active={view === "compose"} />
      </div>
      <div className="shell-pane" hidden={view !== "audit"}>
        <AuditLogView />
      </div>
    </AppShell>
  );
}

function readView(): AppView {
  const hash = window.location.hash.replace("#", "");
  if (hash === "audit" || hash === "compose") {
    return hash;
  }
  return "compose";
}
