import { STATUS_LABELS } from "@/lib/constants";

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
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
