import { GuardrailVerdict } from "@/types";
import { RULE_LABELS } from "@/lib/constants";

interface VerdictRowProps {
  verdict: GuardrailVerdict;
  index: number;
  animate: boolean;
}

export function VerdictRow({ verdict, index, animate }: VerdictRowProps) {
  const isPass = verdict.passed;
  const statusColor = isPass ? "text-verdict-pass" : "text-verdict-fail";
  const borderColor = isPass ? "border-l-verdict-pass" : "border-l-verdict-fail";
  const statusLabel = isPass ? "PASS" : "FAIL";

  return (
    <div
      className={`border-l-[3px] ${borderColor} bg-bg-raised/60 rounded-r px-4 py-3 ${
        animate ? "verdict-row" : ""
      }`}
      style={animate ? { animationDelay: `${index * 100}ms` } : undefined}
    >
      {/* Header row */}
      <div className="flex items-center gap-3">
        <span className={`font-mono text-xs font-bold ${statusColor} tracking-wider`}>
          [{statusLabel}]
        </span>
        <span className="font-mono text-xs font-semibold text-text-primary tracking-wide">
          {verdict.rule}
        </span>
        <span className="font-mono text-[10px] text-text-dim tracking-widest uppercase ml-auto">
          {RULE_LABELS[verdict.rule] ?? verdict.rule}
        </span>
      </div>

      {/* Reason */}
      <p className="font-mono text-xs text-text-muted mt-2 leading-relaxed">
        {verdict.reason}
      </p>

      {/* Flagged claims (llm_judge) */}
      {verdict.flagged_claims && verdict.flagged_claims.length > 0 && (
        <div className="mt-3 space-y-2 border-t border-border-subtle pt-2">
          <span className="font-mono text-[10px] font-bold text-verdict-fail tracking-widest uppercase block">
            Flagged Claims & Compliance Discrepancies
          </span>
          {verdict.flagged_claims.map((fc, i) => (
            <div key={i} className="border-l-2 border-verdict-fail/40 pl-3 py-1 bg-verdict-fail/5 rounded-r">
              <p className="font-mono text-xs text-text-primary font-medium">
                &ldquo;{fc.claim}&rdquo;
              </p>
              <p className="font-mono text-[11px] text-text-secondary mt-0.5">
                {fc.reason}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
