import { useEffect, useState } from "react";
import {
  readGmailToken,
  subscribeGmailToken,
  writeGmailToken,
  type GmailAccess,
} from "./gmailToken.ts";
import { requestGmailAccessToken } from "./google.ts";

type GmailConnectProps = {
  email: string;
};

export function GmailConnect({ email }: GmailConnectProps) {
  const [status, setStatus] = useState<GmailAccess | null>(() =>
    readGmailToken(email),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setStatus(readGmailToken(email));
    return subscribeGmailToken(() => setStatus(readGmailToken(email)));
  }, [email]);

  const connected = status !== null;

  async function onConnect() {
    if (busy) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const next = await requestGmailAccessToken(email);
      writeGmailToken(next);
      setStatus(next);
    } catch {
      setError("Gmail could not be connected.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="gmail-connect">
      <button
        type="button"
        className={connected ? "gmail-pill connected" : "gmail-pill"}
        onClick={() => void onConnect()}
        disabled={busy}
      >
        {label(busy, connected, status?.email ?? email)}
      </button>
      {error ? (
        <p className="gmail-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function label(busy: boolean, connected: boolean, email: string): string {
  if (busy) {
    return "Connecting…";
  }
  if (connected) {
    return `Gmail Connected (${email})`;
  }
  return "Connect Gmail to Send";
}
