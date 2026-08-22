import { Draft, VerificationRound } from "@/types";
import { formatTimestamp } from "@/lib/api";
import { ErrorBanner } from "@/components/ErrorBanner";
import { VerdictRow } from "@/components/VerdictRow";

interface VerificationSectionProps {
  draft: Draft;
  isVerifying: boolean;
  verifyError: string | null;
  animatingRound: number | null;
  onVerify: () => void;
  onDismissError: () => void;
}

export function VerificationSection({
  draft,
  isVerifying,
  verifyError,
  animatingRound,
  onVerify,
  onDismissError,
}: VerificationSectionProps) {
  const hasVerdict = draft.guardrail_verdicts.length > 0;
  const latestRound: VerificationRound | null = hasVerdict
    ? draft.guardrail_verdicts[draft.guardrail_verdicts.length - 1]
    : null;
  const previousRounds: VerificationRound[] = hasVerdict
    ? draft.guardrail_verdicts.slice(0, -1)
    : [];

  return (
    <div className="px-8 py-8 flex-1">
      {/* Verify header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-serif text-2xl font-bold text-text-primary tracking-tight">
          Compliance Audit Pipeline
        </h2>
        <button
          onClick={onVerify}
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
            ? "Executing Rules..."
            : hasVerdict
            ? "Re-Run Verification"
            : "Run Guardrails"}
        </button>
      </div>

      {verifyError && (
        <ErrorBanner message={verifyError} onDismiss={onDismissError} />
      )}

      {/* Latest round */}
      {latestRound && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <span className="font-mono text-[10px] text-text-dim tracking-[0.25em] uppercase font-bold">
              Verification Round {draft.guardrail_verdicts.length}
            </span>
            <span className="font-mono text-[10px] text-text-dim">
              {formatTimestamp(latestRound.verified_at)}
            </span>
            {latestRound.verdicts.every((v) => v.passed) ? (
              <span className="font-mono text-[10px] text-verdict-pass tracking-widest ml-auto font-bold border border-verdict-pass/30 rounded px-2 py-0.5 bg-verdict-pass/10">
                ALL RULES PASSED
              </span>
            ) : (
              <span className="font-mono text-[10px] text-verdict-fail tracking-widest ml-auto font-bold border border-verdict-fail/30 rounded px-2 py-0.5 bg-verdict-fail/10">
                {latestRound.verdicts.filter((v) => !v.passed).length} DISCREPANCIES DETECTED
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
                  animatingRound === draft.guardrail_verdicts.length - 1
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
        <div className="flex flex-col items-center justify-center py-16 text-center border border-dashed border-border rounded p-6 bg-bg-surface/30">
          <p className="font-mono text-sm text-text-muted mb-1 font-medium">
            Pending Guardrail Verification
          </p>
          <p className="font-mono text-xs text-text-dim">
            Click &ldquo;Run Guardrails&rdquo; above to execute the 5 compliance checks.
          </p>
        </div>
      )}

      {/* Previous rounds history */}
      {previousRounds.length > 0 && (
        <details className="mt-6 group border-t border-border-subtle pt-4">
          <summary className="font-mono text-[10px] text-text-dim tracking-[0.2em] uppercase cursor-pointer hover:text-text-muted transition-colors list-none flex items-center justify-between">
            <span>Historical Audit Log ({previousRounds.length} prior round{previousRounds.length > 1 ? "s" : ""})</span>
            <span className="font-mono text-xs text-text-dim group-open:rotate-180 transition-transform">▼</span>
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
                    <span className="font-mono text-[10px] text-text-dim tracking-[0.2em] font-bold">
                      Round {ri + 1}
                    </span>
                    <span className="font-mono text-[10px] text-text-dim">
                      {formatTimestamp(round.verified_at)}
                    </span>
                    <span
                      className={`font-mono text-[10px] tracking-widest ml-auto font-bold ${
                        allPassed ? "text-verdict-pass" : "text-verdict-fail"
                      }`}
                    >
                      {allPassed
                        ? "PASS"
                        : `${round.verdicts.filter((v) => !v.passed).length} FAIL`}
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
                            v.passed ? "text-verdict-pass font-bold" : "text-verdict-fail font-bold"
                          }
                        >
                          [{v.passed ? "PASS" : "FAIL"}]
                        </span>
                        <span className="text-text-muted">{v.rule}</span>
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
  );
}
