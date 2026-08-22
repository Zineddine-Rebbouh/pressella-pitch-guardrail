export interface FlaggedClaim {
  claim: string;
  reason: string;
}

export interface GuardrailVerdict {
  rule: string;
  passed: boolean;
  reason: string;
  flagged_claims?: FlaggedClaim[];
}

export interface VerificationRound {
  verified_at: string;
  verdicts: GuardrailVerdict[];
}

export interface HumanDecision {
  decision: "approve" | "reject";
  note: string | null;
  decided_at: string;
}

export interface EmailPitch {
  subject: string;
  body: string;
}

export interface Draft {
  id: string;
  created_at: string;
  channel: "email" | "sms" | "whatsapp";
  prospect_profile: Record<string, unknown>;
  campaign_brief: Record<string, unknown>;
  generated_pitch: EmailPitch | string;
  status: string;
  guardrail_verdicts: VerificationRound[];
  human_decision: HumanDecision | null;
}

export const CHANNELS = ["email", "sms", "whatsapp"] as const;
export type Channel = (typeof CHANNELS)[number];
