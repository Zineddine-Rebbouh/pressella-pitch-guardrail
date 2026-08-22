import { Draft } from "@/types";
import { formatTimestamp } from "@/lib/api";
import { ErrorBanner } from "@/components/ErrorBanner";

interface DecisionSectionProps {
  draft: Draft;
  decisionNote: string;
  setDecisionNote: (s: string) => void;
  isDeciding: boolean;
  decisionError: string | null;
  onDecision: (decision: "approve" | "reject") => void;
  onDismissError: () => void;
}

export function DecisionSection({
  draft,
  decisionNote,
  setDecisionNote,
  isDeciding,
  decisionError,
  onDecision,
  onDismissError,
}: DecisionSectionProps) {
  const hasVerdict = draft.guardrail_verdicts.length > 0;
  const isDecided = draft.status === "approved" || draft.status === "rejected";
  const canDecide = hasVerdict && !isDecided;

  return (
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
              onDismiss={onDismissError}
            />
          )}

          <div className="flex gap-3">
            <button
              onClick={() => onDecision("approve")}
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
              onClick={() => onDecision("reject")}
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
  );
}
