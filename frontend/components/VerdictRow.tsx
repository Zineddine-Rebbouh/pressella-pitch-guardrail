import { GuardrailVerdict } from "@/types";
import { RULE_LABELS } from "@/lib/constants";

interface VerdictRowProps {
  verdict: GuardrailVerdict;
  index: number;
  animate: boolean;
}

export function VerdictRow({ verdict, index, animate }: VerdictRowProps) {
  const icon = verdict.passed ? "✓" : "✗";
  const iconColor = verdict.passed ? "text-verdict-pass" : "text-verdict-fail";
  const borderColor = verdict.passed ? "border-l-verdict-pass" : "border-l-verdict-fail";

  return (
    <div
      className={`border-l-[3px] ${borderColor} bg-bg-raised/60 rounded-r px-4 py-3 ${
        animate ? "verdict-row" : ""
      }`}
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
            <div key={i} className="border-l border-verdict-fail/30 pl-3 py-1">
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
