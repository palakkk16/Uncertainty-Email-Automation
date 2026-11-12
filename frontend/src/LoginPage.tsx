import { useEffect, useRef, useState } from "react";
import { ChatRequestError, verifyGoogleCredential } from "./api.ts";
import {
  cancelGooglePrompt,
  googleClientId,
  isGoogleSignInActive,
  loadGoogleIdentity,
  setGoogleSignInActive,
} from "./google.ts";
import { readSession, writeSession, type Session } from "./session.ts";

type LoginPageProps = {
  onEnter: (session: Session) => void;
};

export function LoginPage({ onEnter }: LoginPageProps) {
  const slot = useRef<HTMLDivElement>(null);
  const onEnterRef = useRef(onEnter);
  const [error, setError] = useState<string | null>(null);
  onEnterRef.current = onEnter;

  useEffect(() => {
    if (readSession()) {
      return;
    }
    const clientId = googleClientId();
    if (!clientId) {
      setError("Google sign-in is not configured.");
      return;
    }
    let cancelled = false;
    setGoogleSignInActive(true);
    void loadGoogleIdentity()
      .then((google) => {
        if (cancelled || slot.current === null || readSession()) {
          return;
        }
        google.accounts.id.initialize({
          client_id: clientId,
          auto_select: false,
          cancel_on_tap_outside: true,
          ux_mode: "popup",
          callback: (response) => {
            if (cancelled || !isGoogleSignInActive()) {
              return;
            }
            void acceptCredential(response.credential, onEnterRef.current, setError);
          },
        });
        google.accounts.id.renderButton(slot.current, {
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          width: 336,
        });
      })
      .catch(() => {
        if (!cancelled) {
          setError("Google sign-in could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
      setGoogleSignInActive(false);
    };
  }, []);

  return (
    <div className="login-page">
      <main className="login-card">
        <p className="login-kicker">UNCERTAIN-EMAIL</p>
        <h1>Uncertainty-Aware Email Automation</h1>
        <p className="login-lead">
          Sign in with Google to open the workspace. Ask until the
          instruction is complete. Send only when the slots are resolved.
        </p>
        <div ref={slot} className="google-button" />
        {error ? (
          <p className="login-error" role="alert">
            {error}
          </p>
        ) : null}
        <p className="meta">
          Continue with Google verifies your account, then keeps your name
          and photo on this machine.
        </p>
      </main>
    </div>
  );
}

async function acceptCredential(
  credential: string,
  onEnter: (session: Session) => void,
  setError: (message: string | null) => void,
): Promise<void> {
  if (!isGoogleSignInActive()) {
    return;
  }
  setError(null);
  try {
    const profile = await verifyGoogleCredential(credential);
    if (readSession()) {
      return;
    }
    writeSession(profile);
    setGoogleSignInActive(false);
    cancelGooglePrompt();
    onEnter(profile);
  } catch (err) {
    if (isGoogleSignInActive()) {
      setError(err instanceof ChatRequestError ? err.message : "Google sign-in was not accepted.");
    }
  }
}
