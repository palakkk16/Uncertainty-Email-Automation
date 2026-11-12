import { useEffect, useRef, useState } from "react";
import { ChatRequestError, verifyGoogleCredential } from "./api.ts";
import { EmailAuthForm, type AuthMode } from "./EmailAuthForm.tsx";
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
  const enterRef = useRef<(session: Session) => void>(onEnter);
  const [mode, setMode] = useState<AuthMode>("signin");
  const [gisError, setGisError] = useState<string | null>(null);

  useEffect(() => {
    if (readSession()) {
      return;
    }
    const clientId = googleClientId();
    if (!clientId) {
      setGisError("Google sign-in is not configured.");
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
            void acceptGoogleCredential(response.credential, enterRef.current, setGisError);
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
          setGisError("Google sign-in could not be loaded.");
        }
      });
    return () => {
      cancelled = true;
      setGoogleSignInActive(false);
    };
  }, []);

  function enterWorkspace(session: Session) {
    writeSession(session);
    setGoogleSignInActive(false);
    cancelGooglePrompt();
    onEnter(session);
  }
  enterRef.current = enterWorkspace;

  return (
    <div className="auth-shell">
      <section className="auth-showcase" aria-label="Product">
        <p className="login-kicker">UNCERTAIN-EMAIL</p>
        <h1>Ask until the instruction is complete.</h1>
        <p>
          Uncertainty-aware email automation for faculty demos. The agent
          clarifies missing slots, then sends only when dispatch is on.
        </p>
        <ul>
          <li>Recipient, subject, and body stay in your words.</li>
          <li>SEND is live Gmail or a preview card — never a guess.</li>
          <li>Signed-in workspace keeps the thread until New email.</li>
        </ul>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <p className="login-kicker">Welcome</p>
          <h2>{mode === "signup" ? "Create your account" : "Sign in to the workspace"}</h2>
          <p className="login-lead">
            Use email and password, or continue with Google. Your name and
            email appear in the sidebar.
          </p>
          <div className="auth-tabs" role="tablist" aria-label="Account">
            <button
              type="button"
              role="tab"
              aria-selected={mode === "signin"}
              className={mode === "signin" ? "active" : undefined}
              onClick={() => setMode("signin")}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "signup"}
              className={mode === "signup" ? "active" : undefined}
              onClick={() => setMode("signup")}
            >
              Create Account
            </button>
          </div>
          <EmailAuthForm key={mode} mode={mode} onEnter={enterWorkspace} />
          <p className="auth-or" role="separator">
            OR
          </p>
          <div ref={slot} className="google-button" />
          {gisError ? (
            <p className="login-error" role="alert">
              {gisError}
            </p>
          ) : null}
          <p className="meta">
            Faculty demo: admin@uncertain.ai · Demo@1234
          </p>
        </div>
      </section>
    </div>
  );
}

async function acceptGoogleCredential(
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
    onEnter(profile);
  } catch (err) {
    if (isGoogleSignInActive()) {
      setError(err instanceof ChatRequestError ? err.message : "Google sign-in was not accepted.");
    }
  }
}
