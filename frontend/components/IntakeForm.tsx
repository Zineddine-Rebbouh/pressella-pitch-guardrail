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
      className="w-full max-w-2xl bg-gradient-to-b from-[#141622] to-[#0f1019] border border-slate-800/90 rounded-xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-hidden"
    >
      {/* ── Section 01: Prospect Profile ── */}
      <div className="border-b border-slate-800/80 px-8 py-7">
        <div className="flex items-center gap-3 mb-6">
          <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-md">
            01
          </span>
          <h2 className="font-sans text-sm font-semibold text-slate-100 tracking-wider uppercase">
            Prospect Dossier
          </h2>
          <div className="h-px bg-slate-800/80 flex-1 ml-2" />
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-5">
          <FieldGroup label="Company Name" required>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              required
              disabled={isGenerating}
              placeholder="e.g. TechFlow Solutions"
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
              placeholder="e.g. VP of Enterprise Strategy"
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
              placeholder="e.g. B2B Enterprise Software"
              className="field-input"
            />
          </FieldGroup>
          <div /> {/* Grid alignment spacer */}
          <div className="col-span-2">
            <FieldGroup label="Talking Points & Verified Data" required>
              <textarea
                value={talkingPoints}
                onChange={(e) => setTalkingPoints(e.target.value)}
                required
                disabled={isGenerating}
                rows={3}
                placeholder="Verified metrics & achievements (e.g. Closed $15M Series B, expanded to 500+ enterprise clients, 150% YoY growth)"
                className="field-input resize-y"
              />
            </FieldGroup>
          </div>
        </div>
      </div>

      {/* ── Section 02: Campaign Brief ── */}
      <div className="border-b border-slate-800/80 px-8 py-7">
        <div className="flex items-center gap-3 mb-6">
          <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-1 rounded-md">
            02
          </span>
          <h2 className="font-sans text-sm font-semibold text-slate-100 tracking-wider uppercase">
            Campaign Strategy
          </h2>
          <div className="h-px bg-slate-800/80 flex-1 ml-2" />
        </div>

        <div className="grid grid-cols-2 gap-x-6 gap-y-5">
          <FieldGroup label="Campaign Objective" required>
            <input
              type="text"
              value={campaignGoal}
              onChange={(e) => setCampaignGoal(e.target.value)}
              required
              disabled={isGenerating}
              placeholder="e.g. Schedule executive briefing for Q3 roadmap"
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
              placeholder="e.g. Professional, direct, and consultative"
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

      {/* ── Section 03: Channel Selection & Execution ── */}
      <div className="px-8 py-6 flex items-center justify-between bg-[#0a0b12]/60 backdrop-blur-sm">
        <div>
          <span className="font-sans text-xs font-semibold text-slate-300 tracking-wide block mb-2">
            Target Outreach Channel
          </span>
          <div className="bg-[#0b0d16] border border-slate-800 p-1 rounded-lg flex items-center gap-1 shadow-inner">
            {CHANNELS.map((ch) => (
              <button
                key={ch}
                type="button"
                onClick={() => setChannel(ch)}
                disabled={isGenerating}
                className={`font-mono text-xs px-4 py-2 rounded-md transition-all cursor-pointer ${
                  channel === ch
                    ? "bg-gradient-to-r from-indigo-600 to-indigo-700 text-white font-bold shadow-md border border-indigo-400/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
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
          className="bg-gradient-to-r from-indigo-500 via-indigo-600 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white font-mono font-bold text-xs tracking-wider uppercase px-7 py-3.5 rounded-lg shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:-translate-y-0.5 active:translate-y-0 transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
        >
          {isGenerating ? "Synthesizing Pitch Draft..." : "Synthesize Pitch Draft ->"}
        </button>
      </div>
    </form>
  );
}
