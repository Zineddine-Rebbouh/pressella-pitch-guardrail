import { FormEvent } from "react";
import { Channel, CHANNELS } from "@/types";
import { FieldGroup } from "@/components/FieldGroup";

interface IntakeFormProps {
  channel: Channel;
  setChannel: (c: Channel) => void;
  companyName: string;
  setCompanyName: (s: string) => void;
  contactRole: string;
  setContactRole: (s: string) => void;
  industry: string;
  setIndustry: (s: string) => void;
  talkingPoints: string;
  setTalkingPoints: (s: string) => void;
  campaignGoal: string;
  setCampaignGoal: (s: string) => void;
  campaignTone: string;
  setCampaignTone: (s: string) => void;
  keyPoints: string;
  setKeyPoints: (s: string) => void;
  isGenerating: boolean;
  onSubmit: (e: FormEvent) => void;
}

export function IntakeForm({
  channel,
  setChannel,
  companyName,
  setCompanyName,
  contactRole,
  setContactRole,
  industry,
  setIndustry,
  talkingPoints,
  setTalkingPoints,
  campaignGoal,
  setCampaignGoal,
  campaignTone,
  setCampaignTone,
  keyPoints,
  setKeyPoints,
  isGenerating,
  onSubmit,
}: IntakeFormProps) {
  return (
    <form
      onSubmit={onSubmit}
      className="w-full max-w-2xl bg-bg-surface border border-border rounded-sm shadow-xl"
    >
      {/* ── Section: Prospect Profile ── */}
      <div className="border-b border-border px-6 py-5">
        <h2 className="font-mono text-[11px] font-bold text-text-dim tracking-[0.25em] uppercase mb-5">
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
              placeholder="TechFlow Solutions"
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
              placeholder="VP of Enterprise Strategy"
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
              placeholder="B2B Enterprise Software"
              className="field-input"
            />
          </FieldGroup>
          <div /> {/* Spacer */}
          <div className="col-span-2">
            <FieldGroup label="Talking Points & Verified Data" required>
              <textarea
                value={talkingPoints}
                onChange={(e) => setTalkingPoints(e.target.value)}
                required
                disabled={isGenerating}
                rows={3}
                placeholder="Verified metrics & accomplishments — e.g., 'Closed $15M Series B, expanded to 500+ enterprise clients, achieved 150% YoY growth'"
                className="field-input resize-y"
              />
            </FieldGroup>
          </div>
        </div>
      </div>

      {/* ── Section: Campaign Brief ── */}
      <div className="border-b border-border px-6 py-5">
        <h2 className="font-mono text-[11px] font-bold text-text-dim tracking-[0.25em] uppercase mb-5">
          § Campaign Brief
        </h2>
        <div className="grid grid-cols-2 gap-x-6 gap-y-4">
          <FieldGroup label="Campaign Objective" required>
            <input
              type="text"
              value={campaignGoal}
              onChange={(e) => setCampaignGoal(e.target.value)}
              required
              disabled={isGenerating}
              placeholder="Schedule executive briefing for Q3 partnership roadmap"
              className="field-input"
            />
          </FieldGroup>
          <FieldGroup label="Tone & Positioning" required>
            <input
              type="text"
              value={campaignTone}
              onChange={(e) => setCampaignTone(e.target.value)}
              required
              disabled={isGenerating}
              placeholder="Professional, direct, and consultative"
              className="field-input"
            />
          </FieldGroup>
          <div className="col-span-2">
            <FieldGroup label="Key Differentiators & Value Proposition" required>
              <textarea
                value={keyPoints}
                onChange={(e) => setKeyPoints(e.target.value)}
                required
                disabled={isGenerating}
                rows={2}
                placeholder="Core strategic messaging points to emphasize"
                className="field-input resize-y"
              />
            </FieldGroup>
          </div>
        </div>
      </div>

      {/* ── Section: Channel & Action ── */}
      <div className="px-6 py-5 flex items-center justify-between bg-bg-raised/40">
        <div>
          <span className="font-mono text-[10px] text-text-dim tracking-widest uppercase block mb-1.5 font-bold">
            Outreach Channel
          </span>
          <div className="flex items-center gap-1 bg-bg-raised p-1 rounded border border-border">
            {CHANNELS.map((ch) => (
              <button
                key={ch}
                type="button"
                onClick={() => setChannel(ch)}
                disabled={isGenerating}
                className={`font-mono text-xs px-3 py-1.5 rounded transition-all cursor-pointer ${
                  channel === ch
                    ? "bg-bg-surface text-text-primary shadow-xs font-bold border border-border"
                    : "text-text-muted hover:text-text-secondary"
                }`}
              >
                {ch.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={isGenerating}
          className="font-mono text-xs tracking-wider uppercase px-6 py-3 rounded bg-text-primary text-bg-base font-bold hover:bg-text-secondary transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isGenerating ? "Synthesizing Pitch Draft..." : "Synthesize Pitch Draft ->"}
        </button>
      </div>
    </form>
  );
}
