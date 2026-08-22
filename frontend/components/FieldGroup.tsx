import { ReactNode } from "react";

interface FieldGroupProps {
  label: string;
  required?: boolean;
  children: ReactNode;
}

export function FieldGroup({ label, required, children }: FieldGroupProps) {
  return (
    <div className="flex flex-col gap-2">
      <label className="font-sans text-xs font-semibold text-slate-200 tracking-wide flex items-center justify-between">
        <span>
          {label}
          {required && (
            <span className="text-amber-400 font-bold ml-1 inline-block" title="Required field">
              *
            </span>
          )}
        </span>
        {required && (
          <span className="font-mono text-[9px] font-normal text-slate-500 tracking-widest uppercase">
            Required
          </span>
        )}
      </label>
      {children}
    </div>
  );
}
