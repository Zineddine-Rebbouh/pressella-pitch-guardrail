export const API = "http://localhost:8000";

export const RULE_LABELS: Record<string, string> = {
  pii: "PII / Compliance",
  banned_phrases: "Banned Phrases",
  channel_format: "Channel Format",
  unsubstantiated_claims: "Numeric Claims",
  llm_judge: "LLM Judge",
};

export const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending_verification: {
    label: "PENDING VERIFICATION",
    color: "text-verdict-pending",
  },
  verified_pass: { label: "VERIFIED — PASS", color: "text-verdict-pass" },
  verified_fail: { label: "VERIFIED — FAIL", color: "text-verdict-fail" },
  approved: { label: "APPROVED", color: "text-verdict-pass" },
  rejected: { label: "REJECTED", color: "text-verdict-fail" },
};
