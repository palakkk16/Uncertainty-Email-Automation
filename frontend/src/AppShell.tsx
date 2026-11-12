import type { ReactNode } from "react";
import type { Session } from "./session.ts";

export type AppView = "compose" | "audit";

type AppShellProps = {
  view: AppView;
  session: Session;
  onView: (view: AppView) => void;
  onSignOut: () => void;
  children: ReactNode;
};

const NAV: { id: AppView; label: string }[] = [
  { id: "compose", label: "Compose Agent" },
  { id: "audit", label: "Sent & Audit Log" },
];

export function AppShell({
  view,
  session,
  onView,
  onSignOut,
  children,
}: AppShellProps) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <p className="login-kicker">UNCERTAIN-EMAIL</p>
          <h1>Workspace</h1>
        </div>
        <nav aria-label="Workspace">
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              className={view === item.id ? "nav-item active" : "nav-item"}
              aria-current={view === item.id ? "page" : undefined}
              onClick={() => onView(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="sidebar-user">
            {session.picture ? (
              <img
                className="sidebar-avatar"
                src={session.picture}
                alt=""
                referrerPolicy="no-referrer"
              />
            ) : (
              <span className="sidebar-avatar fallback" aria-hidden="true">
                {initials(session.name)}
              </span>
            )}
            <div>
              <p className="sidebar-name">{session.name}</p>
              <p className="sidebar-who">{session.email}</p>
            </div>
          </div>
          <button type="button" className="sign-out" onClick={onSignOut}>
            Sign Out
          </button>
        </div>
      </aside>
      <div className="shell-main">{children}</div>
    </div>
  );
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part.slice(0, 1).toUpperCase()).join("");
}
