"use client";

import { useState, FormEvent } from "react";
import { Draft, Channel } from "@/types";
import { API } from "@/lib/constants";
import { apiFetch, formatTimestamp } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { IntakeForm } from "@/components/IntakeForm";
import { PitchViewer } from "@/components/PitchViewer";
import { VerificationSection } from "@/components/VerificationSection";
import { DecisionSection } from "@/components/DecisionSection";

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

  /* ── Animation trigger ── */
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

    const result = await apiFetch<Draft>(`${API}/drafts/${draft.id}/verify`, {
      method: "POST",
    });

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

    const result = await apiFetch<Draft>(`${API}/drafts/${draft.id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    setIsDeciding(false);
    if (result.ok) {
      setDraft(result.data);
      setDecisionNote("");
    } else {
      setDecisionError(result.detail);
    }
  }

  /* ────────────────────────────────────────────────────────────
     RENDER — Intake Form (pre-draft)
     ──────────────────────────────────────────────────────────── */

  if (!draft) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center px-6 py-16">
        {/* Header */}
        <div className="w-full max-w-2xl mb-10 text-center">
          <p className="font-mono text-[11px] text-text-dim tracking-[0.3em] uppercase mb-2 font-bold">
            Pressella Outbound Compliance Engine
          </p>
          <h1 className="font-serif text-4xl font-bold text-text-primary tracking-tight">
            Pitch Intake & Briefing Dossier
          </h1>
          <p className="font-sans text-sm text-text-secondary mt-3 max-w-xl mx-auto leading-relaxed">
            Enter campaign parameters and target prospect details. The engine will synthesize a pitch draft and execute the 5-layer compliance verification pipeline before human sign-off.
          </p>
        </div>

        {/* Form */}
        <IntakeForm
          channel={channel}
          setChannel={setChannel}
          companyName={companyName}
          setCompanyName={setCompanyName}
          contactRole={contactRole}
          setContactRole={setContactRole}
          industry={industry}
          setIndustry={setIndustry}
          talkingPoints={talkingPoints}
          setTalkingPoints={setTalkingPoints}
          campaignGoal={campaignGoal}
          setCampaignGoal={setCampaignGoal}
          campaignTone={campaignTone}
          setCampaignTone={setCampaignTone}
          keyPoints={keyPoints}
          setKeyPoints={setKeyPoints}
          isGenerating={isGenerating}
          onSubmit={handleGenerate}
        />
      </div>
    );
  }

  /* ────────────────────────────────────────────────────────────
     RENDER — Two-column review layout (post-draft)
     ──────────────────────────────────────────────────────────── */

  return (
    <div className="flex flex-col flex-1 min-h-screen">
      {/* Top bar */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-border bg-bg-surface/60">
        <div className="flex items-center gap-4">
          <p className="font-mono text-[11px] text-text-dim tracking-[0.3em] uppercase font-bold">
            Pressella Outbound Console
          </p>
          <span className="text-border">/</span>
          <p className="font-mono text-xs text-text-muted">
            Draft ID: {draft.id.slice(0, 8)}…
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
            <div className="flex items-center justify-between mb-6 border-b border-border-subtle pb-4">
              <span className="font-mono text-[10px] text-text-primary tracking-[0.25em] uppercase border border-border rounded px-2.5 py-1 bg-bg-raised font-bold">
                Channel: {draft.channel}
              </span>
              <span className="font-mono text-[11px] text-text-dim">
                Created: {formatTimestamp(draft.created_at)}
              </span>
            </div>

            {/* Pitch content document */}
            <div className="bg-bg-surface border border-border rounded-sm p-6 shadow-md">
              <PitchViewer pitch={draft.generated_pitch} channel={draft.channel} />
            </div>

            {/* Input data accordion */}
            <details className="mt-6 group border border-border-subtle rounded p-4 bg-bg-surface/40">
              <summary className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase cursor-pointer hover:text-text-muted transition-colors list-none flex items-center justify-between font-bold">
                <span>View Dossier Input Data</span>
                <span className="font-mono text-xs text-text-dim group-open:rotate-180 transition-transform">▼</span>
              </summary>
              <div className="mt-3 grid grid-cols-2 gap-4 pt-3 border-t border-border-subtle">
                <div className="bg-bg-raised rounded-sm p-4 border border-border-subtle">
                  <span className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase block mb-2 font-bold">
                    Prospect Profile
                  </span>
                  <pre className="font-mono text-xs text-text-muted whitespace-pre-wrap break-words leading-relaxed">
                    {JSON.stringify(draft.prospect_profile, null, 2)}
                  </pre>
                </div>
                <div className="bg-bg-raised rounded-sm p-4 border border-border-subtle">
                  <span className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase block mb-2 font-bold">
                    Campaign Brief
                  </span>
                  <pre className="font-mono text-xs text-text-muted whitespace-pre-wrap break-words leading-relaxed">
                    {JSON.stringify(draft.campaign_brief, null, 2)}
                  </pre>
                </div>
              </div>
            </details>
          </div>
        </section>

        {/* ── RIGHT: Verdict Panel + Decision Bar ── */}
        <section className="w-[45%] flex flex-col overflow-y-auto bg-bg-base">
          <VerificationSection
            draft={draft}
            isVerifying={isVerifying}
            verifyError={verifyError}
            animatingRound={animatingRound}
            onVerify={handleVerify}
            onDismissError={() => setVerifyError(null)}
          />

          <DecisionSection
            draft={draft}
            decisionNote={decisionNote}
            setDecisionNote={setDecisionNote}
            isDeciding={isDeciding}
            decisionError={decisionError}
            onDecision={handleDecision}
            onDismissError={() => setDecisionError(null)}
          />
        </section>
      </div>
    </div>
  );
}
