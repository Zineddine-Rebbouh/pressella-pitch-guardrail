import { Draft } from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import { formatTimestamp } from "@/lib/api";

interface HistoryPanelProps {
  drafts: Draft[];
  onLoad: (draft: Draft) => void;
  onDelete: (id: string) => void;
  onClearAll: () => void;
  onClose: () => void;
}

function companyName(draft: Draft): string {
  const pp = draft.prospect_profile as Record<string, unknown>;
  return typeof pp?.company_name === "string" && pp.company_name
    ? pp.company_name
    : "—";
}

function channelColor(channel: string) {
  switch (channel) {
    case "email":
      return "text-indigo-300 border-indigo-500/30 bg-indigo-500/10";
    case "sms":
      return "text-emerald-300 border-emerald-500/30 bg-emerald-500/10";
    case "whatsapp":
      return "text-teal-300 border-teal-500/30 bg-teal-500/10";
    default:
      return "text-slate-300 border-slate-500/30 bg-slate-500/10";
  }
}

export function HistoryPanel({
  drafts,
  onLoad,
  onDelete,
  onClearAll,
  onClose,
}: HistoryPanelProps) {
  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-stretch justify-end"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {/* Dim overlay */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Drawer */}
      <aside className="relative z-10 w-full max-w-xl flex flex-col bg-[#0d0e17] border-l border-slate-800/90 shadow-[−20px_0_60px_rgba(0,0,0,0.6)] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80 bg-[#0a0b12]/80">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] text-indigo-400 tracking-[0.25em] uppercase font-bold bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded">
              History
            </span>
            {drafts.length > 0 && (
              <span className="font-mono text-[11px] text-slate-500">
                {drafts.length} run{drafts.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            {drafts.length > 0 && (
              <button
                type="button"
                onClick={() => {
                  if (window.confirm("Clear all saved runs?")) onClearAll();
                }}
                className="font-mono text-[11px] text-slate-600 hover:text-red-400 transition-colors cursor-pointer"
              >
                Clear all
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="font-mono text-xs text-slate-500 hover:text-slate-200 transition-colors cursor-pointer px-2 py-1 rounded hover:bg-slate-800/60"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2.5">
          {drafts.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 gap-3">
              <span className="font-mono text-3xl text-slate-700">◫</span>
              <p className="font-mono text-xs text-slate-600 text-center leading-relaxed">
                No saved runs yet.
                <br />
                Submit a pitch to start building history.
              </p>
            </div>
          ) : (
            drafts.map((draft) => (
              <div
                key={draft.id}
                className="group bg-[#12141d] border border-slate-800/80 hover:border-slate-700/80 rounded-xl px-5 py-4 transition-colors"
              >
                {/* Row 1: company + channel + status */}
                <div className="flex items-center justify-between gap-3 mb-2">
                  <span className="font-sans text-sm font-semibold text-slate-100 truncate">
                    {companyName(draft)}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span
                      className={`font-mono text-[10px] font-bold tracking-[0.15em] uppercase border rounded px-2 py-0.5 ${channelColor(draft.channel)}`}
                    >
                      {draft.channel}
                    </span>
                    <StatusBadge status={draft.status} />
                  </div>
                </div>

                {/* Row 2: meta */}
                <div className="flex items-center gap-3 mb-3">
                  <span className="font-mono text-[11px] text-slate-600">
                    {draft.id.slice(0, 8)}…
                  </span>
                  <span className="text-slate-700">·</span>
                  <span className="font-mono text-[11px] text-slate-600">
                    {formatTimestamp(draft.created_at)}
                  </span>
                  {draft.guardrail_verdicts.length > 0 && (
                    <>
                      <span className="text-slate-700">·</span>
                      <span className="font-mono text-[11px] text-slate-600">
                        {draft.guardrail_verdicts.length} verification
                        {draft.guardrail_verdicts.length !== 1 ? "s" : ""}
                      </span>
                    </>
                  )}
                </div>

                {/* Row 3: actions */}
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() => onDelete(draft.id)}
                    className="font-mono text-[11px] text-slate-700 hover:text-red-400 transition-colors cursor-pointer opacity-0 group-hover:opacity-100"
                  >
                    Delete
                  </button>
                  <button
                    type="button"
                    onClick={() => onLoad(draft)}
                    className="font-mono text-xs font-bold tracking-wider uppercase px-4 py-1.5 rounded-md bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/25 hover:text-indigo-200 hover:border-indigo-400/50 transition-all cursor-pointer"
                  >
                    Load →
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
