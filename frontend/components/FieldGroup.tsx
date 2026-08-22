import { ReactNode } from "react";

interface FieldGroupProps {
  label: string;
  required?: boolean;
  children: ReactNode;
}

export function FieldGroup({ label, required, children }: FieldGroupProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="font-mono text-xs text-text-secondary tracking-wide flex items-center gap-1">
        {label}
        {required && <span className="text-verdict-fail text-[10px]">*</span>}
      </label>
      {children}
    </div>
  );
}
