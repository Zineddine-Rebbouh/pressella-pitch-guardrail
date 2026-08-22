"use client";

import { useState, FormEvent } from "react";

/* ────────────────────────────────────────────────────────────
   Types — mirror backend models (§5 of PRD)
   ──────────────────────────────────────────────────────────── */

interface FlaggedClaim {
  claim: string;
  reason: string;
}

interface GuardrailVerdict {
  rule: string;
  passed: boolean;
  reason: string;
  flagged_claims?: FlaggedClaim[];
}

interface VerificationRound {
  verified_at: string;
  verdicts: GuardrailVerdict[];
}

interface HumanDecision {
  decision: "approve" | "reject";
  note: string | null;
  decided_at: string;
}

interface EmailPitch {
  subject: string;
  body: string;
}

interface Draft {
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

/* ────────────────────────────────────────────────────────────
   Constants
   ──────────────────────────────────────────────────────────── */

const API = "http://localhost:8000";

const CHANNELS = ["email", "sms", "whatsapp"] as const;
type Channel = (typeof CHANNELS)[number];

const RULE_LABELS: Record<string, string> = {
  pii: "PII / Compliance",
  banned_phrases: "Banned Phrases",
  channel_format: "Channel Format",
  unsubstantiated_claims: "Numeric Claims",
  llm_judge: "LLM Judge",
};

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  pending_verification: {
    label: "PENDING VERIFICATION",
    color: "text-verdict-pending",
  },
  verified_pass: { label: "VERIFIED — PASS", color: "text-verdict-pass" },
  verified_fail: { label: "VERIFIED — FAIL", color: "text-verdict-fail" },
  approved: { label: "APPROVED", color: "text-verdict-pass" },
  rejected: { label: "REJECTED", color: "text-verdict-fail" },
};

/* ────────────────────────────────────────────────────────────
   Helpers
   ──────────────────────────────────────────────────────────── */

function isEmailPitch(
  pitch: EmailPitch | string
): pitch is EmailPitch {
  return typeof pitch === "object" && pitch !== null && "subject" in pitch;
}

function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

async function apiFetch<T>(
  url: string,
  opts?: RequestInit
): Promise<{ ok: true; data: T } | { ok: false; status: number; detail: string }> {
  try {
    const res = await fetch(url, opts);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch {
        /* no json body */
      }
      return { ok: false, status: res.status, detail };
    }
    const data = (await res.json()) as T;
    return { ok: true, data };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      detail: err instanceof Error ? err.message : "Network error",
    };
  }
}

/* ────────────────────────────────────────────────────────────
   Sub-components (inline, single file)
   ──────────────────────────────────────────────────────────── */

/** Inline error banner with fail-red left border */
function ErrorBanner({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
  return (
    <div className="flex items-start gap-3 rounded border-l-[3px] border-l-verdict-fail bg-verdict-fail/8 px-4 py-3 my-3">
      <span className="font-mono text-sm text-verdict-fail shrink-0">ERR</span>
      <p className="font-mono text-sm text-text-secondary flex-1 break-words">
        {message}
      </p>
      <button
        onClick={onDismiss}
        className="text-text-muted hover:text-text-primary text-lg leading-none cursor-pointer"
        aria-label="Dismiss error"
      >
        ×
      </button>
    </div>
  );
}

/** Status badge */
function StatusBadge({ status }: { status: string }) {
  const info = STATUS_LABELS[status] ?? {
    label: status.toUpperCase(),
    color: "text-text-muted",
  };
  return (
    <span
      className={`font-mono text-xs tracking-widest ${info.color} border border-current/25 rounded px-2 py-1`}
    >
      {info.label}
    </span>
  );
}

/** Single guardrail verdict row */
function VerdictRow({
  verdict,
  index,
  animate,
}: {
  verdict: GuardrailVerdict;
  index: number;
  animate: boolean;
}) {
  const icon = verdict.passed ? "✓" : "✗";
  const iconColor = verdict.passed
    ? "text-verdict-pass"
    : "text-verdict-fail";
  const borderColor = verdict.passed
    ? "border-l-verdict-pass"
    : "border-l-verdict-fail";

  return (
    <div
      className={`border-l-[3px] ${borderColor} bg-bg-raised/60 rounded-r px-4 py-3 ${animate ? "verdict-row" : ""}`}
      style={animate ? { animationDelay: `${index * 120}ms` } : undefined}
    >
      {/* Header row */}
      <div className="flex items-center gap-3">
        <span className={`text-lg font-bold ${iconColor} leading-none`}>
          {icon}
        </span>
        <span className="font-mono text-sm text-text-primary tracking-wide">
          {verdict.rule}
        </span>
        <span className="font-mono text-[10px] text-text-dim tracking-widest uppercase ml-auto">
          {RULE_LABELS[verdict.rule] ?? verdict.rule}
        </span>
      </div>

      {/* Reason */}
      <p className="font-mono text-xs text-text-muted mt-2 pl-8 leading-relaxed">
        {verdict.reason}
      </p>

      {/* Flagged claims (llm_judge) */}
      {verdict.flagged_claims && verdict.flagged_claims.length > 0 && (
        <div className="mt-3 pl-8 space-y-2">
          <span className="font-mono text-[10px] text-verdict-fail tracking-widest uppercase">
            Flagged Claims
          </span>
          {verdict.flagged_claims.map((fc, i) => (
            <div
              key={i}
              className="border-l border-verdict-fail/30 pl-3 py-1"
            >
              <p className="font-mono text-xs text-text-secondary">
                &ldquo;{fc.claim}&rdquo;
              </p>
              <p className="font-mono text-[11px] text-text-dim mt-0.5">
                {fc.reason}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Main Page Component
   ──────────────────────────────────────────────────────────── */

export default function Home() {
  /* ── Draft state ── */
  const [draft, setDraft] = useState<Draft | null>(null);

  /* ── Loading flags ── */
  const [isGenerating, setIsGenerating] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isDeciding, setIsDeciding] = useState(false);

  /* ── Error messages ── */
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [decisionError, setDecisionError] = useState<string | null>(null);

  /* ── Form state ── */
  const [channel, setChannel] = useState<Channel>("email");
  const [companyName, setCompanyName] = useState("");
  const [contactRole, setContactRole] = useState("");
  const [industry, setIndustry] = useState("");
  const [talkingPoints, setTalkingPoints] = useState("");
  const [campaignGoal, setCampaignGoal] = useState("");
  const [campaignTone, setCampaignTone] = useState("");
  const [keyPoints, setKeyPoints] = useState("");

  /* ── Decision state ── */
  const [decisionNote, setDecisionNote] = useState("");

  /* ── Animation trigger: the index of the verification round that should animate ── */
  const [animatingRound, setAnimatingRound] = useState<number | null>(null);

  /* ── Handlers ── */

  async function handleGenerate(e: FormEvent) {
    e.preventDefault();
    setGenerateError(null);
    setIsGenerating(true);

    const body = {
      prospect_profile: {
        company_name: companyName,
        contact_role: contactRole,
        industry: industry,
        talking_points: talkingPoints,
      },
      campaign_brief: {
        goal: campaignGoal,
        tone: campaignTone,
        key_talking_points: keyPoints,
      },
      channel,
    };

    const result = await apiFetch<Draft>(`${API}/drafts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    setIsGenerating(false);
    if (result.ok) {
      setDraft(result.data);
    } else {
      setGenerateError(result.detail);
    }
  }

  async function handleVerify() {
    if (!draft) return;
    setVerifyError(null);
    setIsVerifying(true);

    const result = await apiFetch<Draft>(
      `${API}/drafts/${draft.id}/verify`,
      { method: "POST" }
    );

    setIsVerifying(false);
    if (result.ok) {
      setAnimatingRound(result.data.guardrail_verdicts.length - 1);
      setDraft(result.data);
    } else {
      setVerifyError(result.detail);
    }
  }

  async function handleDecision(decision: "approve" | "reject") {
    if (!draft) return;
    setDecisionError(null);
    setIsDeciding(true);

    const body: { decision: string; note?: string } = { decision };
    if (decisionNote.trim()) body.note = decisionNote.trim();

    const result = await apiFetch<Draft>(
      `${API}/drafts/${draft.id}/decision`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    );

    setIsDeciding(false);
    if (result.ok) {
      setDraft(result.data);
      setDecisionNote("");
    } else {
      setDecisionError(result.detail);
    }
  }

  /* ── Derived state ── */
  const hasVerdict = draft !== null && draft.guardrail_verdicts.length > 0;
  const latestRound = hasVerdict
    ? draft.guardrail_verdicts[draft.guardrail_verdicts.length - 1]
    : null;
  const previousRounds = hasVerdict
    ? draft.guardrail_verdicts.slice(0, -1)
    : [];
  const canDecide =
    hasVerdict &&
    draft.status !== "approved" &&
    draft.status !== "rejected";
  const isDecided =
    draft?.status === "approved" || draft?.status === "rejected";

  /* ────────────────────────────────────────────────────────────
     RENDER — Intake Form (pre-draft)
     ──────────────────────────────────────────────────────────── */

  if (!draft) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center px-6 py-16">
        {/* Header */}
        <div className="w-full max-w-2xl mb-10">
          <p className="font-mono text-[10px] text-text-dim tracking-[0.3em] uppercase mb-2">
            Pressella Pitch Guardrail
          </p>
          <h1 className="font-serif text-4xl font-bold text-text-primary tracking-tight">
            Intake Briefing
          </h1>
          <p className="font-serif text-lg text-text-muted mt-2 italic">
            Prepare the prospect dossier and campaign parameters. The system
            will generate a pitch draft and run it through five guardrail
            checks before human review.
          </p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleGenerate}
          className="w-full max-w-2xl bg-bg-surface border border-border rounded-sm"
        >
          {/* ── Section: Prospect Profile ── */}
          <div className="border-b border-border px-6 py-5">
            <h2 className="font-mono text-[11px] text-text-dim tracking-[0.25em] uppercase mb-5">
              § Prospect Profile
            </h2>
            <div className="grid grid-cols-2 gap-x-6 gap-y-4">
              <FieldGroup label="Company Name" required>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  required
                  disabled={isGenerating}
                  placeholder="Acme Corp"
                  className="field-input"
                />
              </FieldGroup>
              <FieldGroup label="Contact Role" required>
                <input
                  type="text"
                  value={contactRole}
                  onChange={(e) => setContactRole(e.target.value)}
                  required
                  disabled={isGenerating}
                  placeholder="VP of Marketing"
                  className="field-input"
                />
              </FieldGroup>
              <FieldGroup label="Industry" required>
                <input
                  type="text"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  required
                  disabled={isGenerating}
                  placeholder="SaaS / FinTech / Healthcare…"
                  className="field-input"
                />
              </FieldGroup>
              <div /> {/* spacer for grid alignment */}
              <div className="col-span-2">
                <FieldGroup label="Talking Points & Data" required>
                  <textarea
                    value={talkingPoints}
                    onChange={(e) => setTalkingPoints(e.target.value)}
                    required
                    disabled={isGenerating}
                    rows={3}
                    placeholder="Key facts, metrics, achievements — e.g. 'Raised $12M Series A, 40% YoY growth, 200+ enterprise clients'"
                    className="field-input resize-y"
                  />
                </FieldGroup>
              </div>
            </div>
          </div>

          {/* ── Section: Campaign Brief ── */}
          <div className="border-b border-border px-6 py-5">
            <h2 className="font-mono text-[11px] text-text-dim tracking-[0.25em] uppercase mb-5">
              § Campaign Brief
            </h2>
            <div className="grid grid-cols-2 gap-x-6 gap-y-4">
              <FieldGroup label="Campaign Goal" required>
                <input
                  type="text"
                  value={campaignGoal}
                  onChange={(e) => setCampaignGoal(e.target.value)}
                  required
                  disabled={isGenerating}
                  placeholder="Secure coverage in tier-1 tech outlets"
                  className="field-input"
                />
              </FieldGroup>
              <FieldGroup label="Tone" required>
                <input
                  type="text"
                  value={campaignTone}
                  onChange={(e) => setCampaignTone(e.target.value)}
                  required
                  disabled={isGenerating}
                  placeholder="Professional, confident, data-driven"
                  className="field-input"
                />
              </FieldGroup>
              <div className="col-span-2">
                <FieldGroup label="Key Talking Points" required>
                  <textarea
                    value={keyPoints}
                    onChange={(e) => setKeyPoints(e.target.value)}
                    required
                    disabled={isGenerating}
                    rows={3}
                    placeholder="Main messages to convey — product differentiators, proof points, desired call to action"
                    className="field-input resize-y"
                  />
                </FieldGroup>
              </div>
            </div>
          </div>

          {/* ── Section: Channel + Submit ── */}
          <div className="px-6 py-5">
            <h2 className="font-mono text-[11px] text-text-dim tracking-[0.25em] uppercase mb-4">
              § Outreach Channel
            </h2>
            <div className="flex gap-0 mb-6">
              {CHANNELS.map((ch) => (
                <button
                  key={ch}
                  type="button"
                  onClick={() => setChannel(ch)}
                  disabled={isGenerating}
                  className={`
                    font-mono text-sm tracking-wide px-5 py-2.5 border cursor-pointer
                    transition-colors duration-150
                    ${
                      channel === ch
                        ? "bg-text-primary text-bg-base border-text-primary"
                        : "bg-transparent text-text-muted border-border hover:border-text-dim hover:text-text-secondary"
                    }
                    ${ch === "email" ? "rounded-l-sm" : ""}
                    ${ch === "whatsapp" ? "rounded-r-sm" : ""}
                    ${ch !== "email" ? "-ml-px" : ""}
                    disabled:opacity-40 disabled:cursor-not-allowed
                  `}
                >
                  {ch.toUpperCase()}
                </button>
              ))}
            </div>

            {generateError && (
              <ErrorBanner
                message={generateError}
                onDismiss={() => setGenerateError(null)}
              />
            )}

            <button
              type="submit"
              disabled={isGenerating}
              className={`
                w-full font-mono text-sm tracking-[0.15em] uppercase py-3.5 rounded-sm
                cursor-pointer transition-all duration-200
                ${
                  isGenerating
                    ? "bg-bg-raised text-text-dim audit-pulse cursor-not-allowed"
                    : "bg-text-primary text-bg-base hover:bg-text-secondary"
                }
                disabled:cursor-not-allowed
              `}
            >
              {isGenerating ? "Generating Draft…" : "Generate Pitch Draft"}
            </button>
          </div>
        </form>
      </div>
    );
  }

  /* ────────────────────────────────────────────────────────────
     RENDER — Two-column review layout (post-draft)
     ──────────────────────────────────────────────────────────── */

  const pitch = draft.generated_pitch;

  return (
    <div className="flex flex-col flex-1 min-h-screen">
      {/* Top bar */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-border bg-bg-surface/60">
        <div className="flex items-center gap-4">
          <p className="font-mono text-[10px] text-text-dim tracking-[0.3em] uppercase">
            Pressella Pitch Guardrail
          </p>
          <span className="text-border">/</span>
          <p className="font-mono text-xs text-text-muted">
            Draft {draft.id.slice(0, 8)}…
          </p>
        </div>
        <StatusBadge status={draft.status} />
      </header>

      {/* Two-column body */}
      <div className="flex flex-1 min-h-0">
        {/* ── LEFT: Generated Pitch ── */}
        <section className="w-[55%] border-r border-border overflow-y-auto">
          <div className="px-10 py-8">
            {/* Channel tag */}
            <div className="flex items-center gap-3 mb-6">
              <span className="font-mono text-[10px] text-text-dim tracking-[0.25em] uppercase border border-border rounded px-2 py-1">
                {draft.channel}
              </span>
              <span className="font-mono text-[10px] text-text-dim">
                {formatTimestamp(draft.created_at)}
              </span>
            </div>

            {/* Pitch content — styled as a document */}
            <div className="bg-bg-surface border border-border rounded-sm">
              {isEmailPitch(pitch) ? (
                <>
                  {/* Subject */}
                  <div className="px-6 py-4 border-b border-border-subtle">
                    <span className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase block mb-1.5">
                      Subject
                    </span>
                    <p className="font-serif text-xl text-text-primary leading-snug">
                      {pitch.subject}
                    </p>
                  </div>
                  {/* Body */}
                  <div className="px-6 py-5">
                    <span className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase block mb-2">
                      Body
                    </span>
                    <div className="font-serif text-[15px] text-text-secondary leading-relaxed whitespace-pre-wrap">
                      {pitch.body}
                    </div>
                  </div>
                </>
              ) : (
                <div className="px-6 py-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase">
                      Message
                    </span>
                    <span className="font-mono text-[10px] text-text-dim">
                      {(pitch as string).length} chars
                    </span>
                  </div>
                  <div className="font-serif text-[15px] text-text-secondary leading-relaxed whitespace-pre-wrap">
                    {pitch as string}
                  </div>
                </div>
              )}
            </div>

            {/* Input data accordion (collapsed by default) */}
            <details className="mt-6 group">
              <summary className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase cursor-pointer hover:text-text-muted transition-colors list-none flex items-center gap-2">
                <span className="text-text-dim group-open:rotate-90 transition-transform duration-200 inline-block">
                  ▸
                </span>
                Input Data
              </summary>
              <div className="mt-3 grid grid-cols-2 gap-4">
                <div className="bg-bg-raised rounded-sm p-4 border border-border-subtle">
                  <span className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase block mb-2">
                    Prospect Profile
                  </span>
                  <pre className="font-mono text-xs text-text-muted whitespace-pre-wrap break-words">
                    {JSON.stringify(draft.prospect_profile, null, 2)}
                  </pre>
                </div>
                <div className="bg-bg-raised rounded-sm p-4 border border-border-subtle">
                  <span className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase block mb-2">
                    Campaign Brief
                  </span>
                  <pre className="font-mono text-xs text-text-muted whitespace-pre-wrap break-words">
                    {JSON.stringify(draft.campaign_brief, null, 2)}
                  </pre>
                </div>
              </div>
            </details>
          </div>
        </section>

        {/* ── RIGHT: Verdict Panel + Decision Bar ── */}
        <section className="w-[45%] flex flex-col overflow-y-auto bg-bg-base">
          <div className="px-8 py-8 flex-1">
            {/* Verify button */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-serif text-2xl font-bold text-text-primary tracking-tight">
                Guardrail Audit
              </h2>
              <button
                onClick={handleVerify}
                disabled={isVerifying}
                className={`
                  font-mono text-xs tracking-[0.15em] uppercase px-5 py-2.5 rounded-sm
                  cursor-pointer transition-all duration-200 border
                  ${
                    isVerifying
                      ? "bg-bg-raised text-text-dim border-border audit-pulse cursor-not-allowed"
                      : "bg-transparent text-verdict-pending border-verdict-pending/40 hover:bg-verdict-pending/10 hover:border-verdict-pending"
                  }
                  disabled:cursor-not-allowed
                `}
              >
                {isVerifying
                  ? "Running Checks…"
                  : hasVerdict
                    ? "Re-run Guardrails"
                    : "Run Guardrails"}
              </button>
            </div>

            {verifyError && (
              <ErrorBanner
                message={verifyError}
                onDismiss={() => setVerifyError(null)}
              />
            )}

            {/* Latest round */}
            {latestRound && (
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <span className="font-mono text-[10px] text-text-dim tracking-[0.25em] uppercase">
                    Round {draft.guardrail_verdicts.length}
                  </span>
                  <span className="font-mono text-[10px] text-text-dim">
                    {formatTimestamp(latestRound.verified_at)}
                  </span>
                  {latestRound.verdicts.every((v) => v.passed) ? (
                    <span className="font-mono text-[10px] text-verdict-pass tracking-widest ml-auto">
                      ALL PASS
                    </span>
                  ) : (
                    <span className="font-mono text-[10px] text-verdict-fail tracking-widest ml-auto">
                      {latestRound.verdicts.filter((v) => !v.passed).length}{" "}
                      FAILED
                    </span>
                  )}
                </div>
                <div className="space-y-2">
                  {latestRound.verdicts.map((v, i) => (
                    <VerdictRow
                      key={`${v.rule}-${i}`}
                      verdict={v}
                      index={i}
                      animate={
                        animatingRound ===
                        draft.guardrail_verdicts.length - 1
                      }
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Verify skeleton placeholder */}
            {isVerifying && !latestRound && (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="h-16 bg-bg-raised/40 rounded-r border-l-[3px] border-l-border audit-pulse"
                    style={{ animationDelay: `${i * 100}ms` }}
                  />
                ))}
              </div>
            )}

            {/* No verdict yet prompt */}
            {!hasVerdict && !isVerifying && (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <p className="font-mono text-sm text-text-dim mb-1">
                  No guardrail checks have been run.
                </p>
                <p className="font-mono text-xs text-text-dim">
                  Click &ldquo;Run Guardrails&rdquo; to begin verification.
                </p>
              </div>
            )}

            {/* Previous rounds */}
            {previousRounds.length > 0 && (
              <details className="mt-6 group">
                <summary className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase cursor-pointer hover:text-text-muted transition-colors list-none flex items-center gap-2">
                  <span className="text-text-dim group-open:rotate-90 transition-transform duration-200 inline-block">
                    ▸
                  </span>
                  {previousRounds.length} Previous Round
                  {previousRounds.length > 1 ? "s" : ""}
                </summary>
                <div className="mt-3 space-y-4">
                  {previousRounds.map((round, ri) => {
                    const allPassed = round.verdicts.every((v) => v.passed);
                    return (
                      <div
                        key={ri}
                        className="bg-bg-surface/40 border border-border-subtle rounded-sm p-4"
                      >
                        <div className="flex items-center gap-3 mb-3">
                          <span className="font-mono text-[10px] text-text-dim tracking-[0.2em]">
                            Round {ri + 1}
                          </span>
                          <span className="font-mono text-[10px] text-text-dim">
                            {formatTimestamp(round.verified_at)}
                          </span>
                          <span
                            className={`font-mono text-[10px] tracking-widest ml-auto ${allPassed ? "text-verdict-pass" : "text-verdict-fail"}`}
                          >
                            {allPassed
                              ? "ALL PASS"
                              : `${round.verdicts.filter((v) => !v.passed).length} FAILED`}
                          </span>
                        </div>
                        <div className="space-y-1">
                          {round.verdicts.map((v, vi) => (
                            <div
                              key={vi}
                              className="flex items-center gap-2 font-mono text-xs"
                            >
                              <span
                                className={
                                  v.passed
                                    ? "text-verdict-pass"
                                    : "text-verdict-fail"
                                }
                              >
                                {v.passed ? "✓" : "✗"}
                              </span>
                              <span className="text-text-muted">
                                {v.rule}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </details>
            )}
          </div>

          {/* ── Decision Bar ── */}
          <div className="border-t border-border bg-bg-surface/60 px-8 py-5">
            {/* Already decided — show recorded decision */}
            {isDecided && draft.human_decision && (
              <div className="flex items-center gap-3">
                <span
                  className={`font-mono text-sm tracking-[0.15em] uppercase font-bold ${
                    draft.human_decision.decision === "approve"
                      ? "text-verdict-pass"
                      : "text-verdict-fail"
                  }`}
                >
                  {draft.human_decision.decision === "approve"
                    ? "✓ Approved"
                    : "✗ Rejected"}
                </span>
                <span className="font-mono text-[10px] text-text-dim">
                  {formatTimestamp(draft.human_decision.decided_at)}
                </span>
                {draft.human_decision.note && (
                  <p className="font-mono text-xs text-text-muted ml-auto max-w-[50%] truncate">
                    &ldquo;{draft.human_decision.note}&rdquo;
                  </p>
                )}
              </div>
            )}

            {/* Active decision controls */}
            {!isDecided && (
              <>
                <div className="flex items-center gap-3 mb-3">
                  <h3 className="font-mono text-[10px] text-text-dim tracking-[0.25em] uppercase">
                    Human Decision
                  </h3>
                  {!canDecide && (
                    <span className="font-mono text-[10px] text-verdict-pending">
                      Run guardrails before deciding
                    </span>
                  )}
                </div>

                {/* Note textarea */}
                <textarea
                  value={decisionNote}
                  onChange={(e) => setDecisionNote(e.target.value)}
                  disabled={!canDecide || isDeciding}
                  placeholder="Optional reviewer note…"
                  rows={2}
                  className="field-input mb-3 resize-none text-sm"
                />

                {decisionError && (
                  <ErrorBanner
                    message={decisionError}
                    onDismiss={() => setDecisionError(null)}
                  />
                )}

                <div className="flex gap-3">
                  <button
                    onClick={() => handleDecision("approve")}
                    disabled={!canDecide || isDeciding}
                    className={`
                      flex-1 font-mono text-sm tracking-[0.15em] uppercase py-3 rounded-sm
                      cursor-pointer transition-all duration-200 border
                      ${
                        canDecide && !isDeciding
                          ? "bg-verdict-pass/10 text-verdict-pass border-verdict-pass/30 hover:bg-verdict-pass/20 hover:border-verdict-pass"
                          : "bg-bg-raised text-text-dim border-border cursor-not-allowed opacity-50"
                      }
                    `}
                  >
                    {isDeciding ? "…" : "Approve"}
                  </button>
                  <button
                    onClick={() => handleDecision("reject")}
                    disabled={!canDecide || isDeciding}
                    className={`
                      flex-1 font-mono text-sm tracking-[0.15em] uppercase py-3 rounded-sm
                      cursor-pointer transition-all duration-200 border
                      ${
                        canDecide && !isDeciding
                          ? "bg-verdict-fail/10 text-verdict-fail border-verdict-fail/30 hover:bg-verdict-fail/20 hover:border-verdict-fail"
                          : "bg-bg-raised text-text-dim border-border cursor-not-allowed opacity-50"
                      }
                    `}
                  >
                    {isDeciding ? "…" : "Reject"}
                  </button>
                </div>
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

/* ────────────────────────────────────────────────────────────
   Field wrapper (used in intake form)
   ──────────────────────────────────────────────────────────── */

function FieldGroup({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="font-mono text-[11px] text-text-muted tracking-wide">
        {label}
        {required && <span className="text-verdict-fail ml-1">*</span>}
      </span>
      {children}
    </label>
  );
}
