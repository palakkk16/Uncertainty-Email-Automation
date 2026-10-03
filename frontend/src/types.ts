export type EmailExtraction = {
  recipient: string | null;
  subject: string | null;
  body: string | null;
  recipient_mention: string | null;
};

export type ChatResponse = {
  reply: string;
  phase: "decision_layer";
  decision: "ASK" | "SEND";
  clarification: string | null;
  extraction: EmailExtraction;
  assessment: {
    method: "slot_sufficiency_threshold";
    recipient: "resolved" | "missing" | "bare_name" | "ambiguous";
    subject: "resolved" | "missing";
    body: "resolved" | "missing";
    resolved_fraction: number;
  };
};

export type UserTurn = {
  id: string;
  role: "user";
  text: string;
};

export type AskTurn = {
  id: string;
  role: "assistant";
  decision: "ASK";
  text: string;
};

export type SendTurn = {
  id: string;
  role: "assistant";
  decision: "SEND";
  sentence: string;
  extraction: EmailExtraction;
};

export type Turn = UserTurn | AskTurn | SendTurn;
