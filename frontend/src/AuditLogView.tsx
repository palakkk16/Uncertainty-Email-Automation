import { useEffect, useState } from "react";
import {
  clearAuditLog,
  readAuditLog,
  subscribeAuditLog,
  type AuditEntry,
} from "./auditLog.ts";

export function AuditLogView() {
  const [entries, setEntries] = useState(readAuditLog);

  useEffect(() => subscribeAuditLog(() => setEntries(readAuditLog())), []);

  function onClear() {
    clearAuditLog();
  }

  return (
    <div className="app">
      <main className="sheet wide">
        <header className="header">
          <h1>Sent &amp; Audit Log</h1>
          <p>
            Completed SEND and PREVIEW cards from this browser. Clarification
            turns are the ASK questions before the agent acted.
          </p>
        </header>
        {entries.length === 0 ? (
          <p className="empty pane">
            No completed emails in this session yet. Use Compose Agent, then
            return here after a SEND or preview card.
          </p>
        ) : (
          <div className="table-wrap">
            <table className="audit">
              <thead>
                <tr>
                  <th scope="col">Timestamp</th>
                  <th scope="col">Recipient</th>
                  <th scope="col">Subject</th>
                  <th scope="col">Body</th>
                  <th scope="col">Status</th>
                  <th scope="col">Clarification turns</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <AuditRow key={entry.id} entry={entry} />
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="pane-actions">
          <button type="button" onClick={onClear} disabled={entries.length === 0}>
            Clear History
          </button>
        </div>
      </main>
    </div>
  );
}

function AuditRow({ entry }: { entry: AuditEntry }) {
  const when = formatWhen(entry.timestamp);
  return (
    <tr>
      <td>{when}</td>
      <td>{entry.recipient}</td>
      <td>{entry.subject}</td>
      <td className="preview">{entry.bodyPreview}</td>
      <td>
        <span className={entry.status === "SENT" ? "badge sent" : "badge preview"}>
          {entry.status}
        </span>
      </td>
      <td className={entry.clarificationTurns > 0 ? "asks" : undefined}>
        {entry.clarificationTurns}
      </td>
    </tr>
  );
}

function formatWhen(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}
