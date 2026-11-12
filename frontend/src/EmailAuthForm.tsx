import { useState, type FormEvent } from "react";
import {
  ChatRequestError,
  loginWithPassword,
  registerAccount,
} from "./api.ts";
import type { Session } from "./session.ts";

export type AuthMode = "signin" | "signup";

type EmailAuthFormProps = {
  mode: AuthMode;
  onEnter: (session: Session) => void;
};

export function EmailAuthForm({ mode, onEnter }: EmailAuthFormProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const signup = mode === "signup";

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) {
      return;
    }
    const nextName = name.trim();
    const nextEmail = email.trim();
    if (!nextEmail.includes("@") || password.length === 0) {
      setError("Enter a valid email and password.");
      return;
    }
    if (signup && nextName.length === 0) {
      setError("Enter your name, email, and password.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const profile = signup
        ? await registerAccount(nextName, nextEmail, password)
        : await loginWithPassword(nextEmail, password);
      onEnter(profile);
    } catch (err) {
      setError(
        err instanceof ChatRequestError ? err.message : "Cannot reach the API.",
      );
      setBusy(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={(event) => void onSubmit(event)}>
      {signup ? (
        <label className="auth-field">
          Name
          <input
            name="name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            disabled={busy}
            required
          />
        </label>
      ) : null}
      <label className="auth-field">
        Email
        <input
          name="email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={busy}
          required
        />
      </label>
      <label className="auth-field">
        Password
        <input
          name="password"
          type="password"
          autoComplete={signup ? "new-password" : "current-password"}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={busy}
          required
        />
      </label>
      {error ? (
        <p className="login-error" role="alert">
          {error}
        </p>
      ) : null}
      <button className="auth-submit" type="submit" disabled={busy}>
        {busy ? "Please wait…" : signup ? "Create account" : "Sign in"}
      </button>
    </form>
  );
}
