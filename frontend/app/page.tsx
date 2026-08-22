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
      <div className="flex flex-col flex-1 items-center justify-center px-6 py-16 bg-gradient-to-b from-[#0a0b10] via-[#0d0e17] to-[#0a0b10] min-h-screen">
        {/* Header */}
        <div className="w-full max-w-2xl mb-10 text-center">
          <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1 rounded-full mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            <span className="font-mono text-[11px] font-semibold text-indigo-300 tracking-wider uppercase">
              Pressella Outbound Compliance Engine
            </span>
          </div>
          <h1 className="font-sans text-3xl font-bold text-slate-100 tracking-tight leading-tight">
            Pitch Intake & Briefing Dossier
          </h1>
          <p className="font-sans text-sm text-slate-400 mt-3 max-w-xl mx-auto leading-relaxed">
            Specify prospect dossier data and campaign strategy. The engine will synthesize a targeted outreach pitch and execute the 5-layer compliance verification pipeline.
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
      <header className="flex items-center justify-between px-8 py-4 border-b border-border bg-bg-surface/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <p className="font-mono text-[11px] text-indigo-400 tracking-[0.25em] uppercase font-bold">
            Pressella Review Console
          </p>
          <span className="text-slate-700">/</span>
          <p className="font-mono text-xs text-slate-400">
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
            <div className="flex items-center justify-between mb-6 border-b border-slate-800/80 pb-4">
              <span className="font-mono text-[10px] text-indigo-300 tracking-[0.2em] uppercase border border-indigo-500/30 rounded px-3 py-1 bg-indigo-500/10 font-bold">
                Channel: {draft.channel}
              </span>
              <span className="font-mono text-[11px] text-slate-500">
                Created: {formatTimestamp(draft.created_at)}
              </span>
            </div>

            {/* Pitch content document */}
            <div className="bg-[#12141d] border border-slate-800/90 rounded-xl p-7 shadow-xl">
              <PitchViewer pitch={draft.generated_pitch} channel={draft.channel} />
            </div>

            {/* Input data accordion */}
            <details className="mt-6 group border border-slate-800/80 rounded-xl p-4 bg-[#12141d]/50">
              <summary className="font-mono text-[10px] text-slate-400 tracking-[0.2em] uppercase cursor-pointer hover:text-slate-200 transition-colors list-none flex items-center justify-between font-bold">
                <span>View Dossier Input Data</span>
                <span className="font-mono text-xs text-slate-500 group-open:rotate-180 transition-transform">▼</span>
              </summary>
              <div className="mt-3 grid grid-cols-2 gap-4 pt-3 border-t border-slate-800/80">
                <div className="bg-[#0e0f17] rounded-lg p-4 border border-slate-800/80">
                  <span className="font-mono text-[10px] text-slate-400 tracking-[0.2em] uppercase block mb-2 font-bold">
                    Prospect Profile
                  </span>
                  <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap break-words leading-relaxed">
                    {JSON.stringify(draft.prospect_profile, null, 2)}
                  </pre>
                </div>
                <div className="bg-[#0e0f17] rounded-lg p-4 border border-slate-800/80">
                  <span className="font-mono text-[10px] text-slate-400 tracking-[0.2em] uppercase block mb-2 font-bold">
                    Campaign Brief
                  </span>
                  <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap break-words leading-relaxed">
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
