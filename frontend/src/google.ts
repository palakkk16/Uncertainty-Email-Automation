import { readSession } from "./session.ts";

const GIS_SRC = "https://accounts.google.com/gsi/client";

type CredentialResponse = {
  credential: string;
};

type GsiButtonOptions = {
  theme: "outline" | "filled_black" | "filled_blue";
  size: "large" | "medium" | "small";
  text: "signin_with" | "signup_with" | "continue_with" | "signin";
  shape: "rectangular" | "pill" | "circle" | "square";
  width?: number;
};

type TokenResponse = {
  access_token?: string;
  expires_in?: number | string;
  error?: string;
};

type TokenClient = {
  requestAccessToken: (override?: { hint?: string }) => void;
};

type GoogleAccounts = {
  accounts: {
    id: {
      initialize: (config: {
        client_id: string;
        callback: (response: CredentialResponse) => void;
        auto_select?: boolean;
        cancel_on_tap_outside?: boolean;
        ux_mode?: "popup" | "redirect";
      }) => void;
      renderButton: (parent: HTMLElement, options: GsiButtonOptions) => void;
      disableAutoSelect: () => void;
      cancel: () => void;
    };
    oauth2?: {
      initTokenClient: (config: {
        client_id: string;
        scope: string;
        hint?: string;
        callback: (response: TokenResponse) => void;
        error_callback?: () => void;
      }) => TokenClient;
    };
  };
};

const GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send";

let loader: Promise<GoogleAccounts> | null = null;
let signInActive = false;

export function googleClientId(): string {
  const value = import.meta.env.VITE_GOOGLE_CLIENT_ID;
  return typeof value === "string" ? value.trim() : "";
}

export function loadGoogleIdentity(): Promise<GoogleAccounts> {
  const existing = windowGoogle();
  if (existing) {
    return Promise.resolve(existing);
  }
  if (loader) {
    return loader;
  }
  loader = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GIS_SRC;
    script.async = true;
    script.onload = () => {
      const api = windowGoogle();
      if (!api) {
        reject(new Error("gis"));
        return;
      }
      resolve(api);
    };
    script.onerror = () => reject(new Error("gis"));
    document.head.appendChild(script);
  });
  return loader;
}

export function setGoogleSignInActive(active: boolean): void {
  signInActive = active;
  if (!active) {
    cancelGooglePrompt();
  }
}

export function isGoogleSignInActive(): boolean {
  return signInActive && readSession() === null;
}

export function cancelGooglePrompt(): void {
  try {
    windowGoogle()?.accounts.id.cancel();
  } catch {
    return;
  }
}

export function disableGoogleAutoSelect(): void {
  try {
    windowGoogle()?.accounts.id.disableAutoSelect();
  } catch {
    return;
  }
}

export function requestGmailAccessToken(email: string): Promise<{
  accessToken: string;
  expiresAt: number;
  email: string;
}> {
  const clientId = googleClientId();
  if (!clientId) {
    return Promise.reject(new Error("gis"));
  }
  return loadGoogleIdentity().then(
    (google) =>
      new Promise((resolve, reject) => {
        const oauth2 = google.accounts.oauth2;
        if (!oauth2) {
          reject(new Error("gis"));
          return;
        }
        const client = oauth2.initTokenClient({
          client_id: clientId,
          scope: GMAIL_SEND_SCOPE,
          hint: email,
          callback: (response) => {
            const token = response.access_token?.trim() ?? "";
            if (response.error || !token) {
              reject(new Error("gmail"));
              return;
            }
            const seconds = Number(response.expires_in);
            const lifetime = Number.isFinite(seconds) && seconds > 0 ? seconds : 3600;
            resolve({
              accessToken: token,
              expiresAt: Date.now() + Math.max(30, lifetime - 60) * 1000,
              email,
            });
          },
          error_callback: () => reject(new Error("gmail")),
        });
        client.requestAccessToken({ hint: email });
      }),
  );
}

function windowGoogle(): GoogleAccounts | null {
  const value = (window as Window & { google?: GoogleAccounts }).google;
  if (!value?.accounts?.id) {
    return null;
  }
  return value;
}
