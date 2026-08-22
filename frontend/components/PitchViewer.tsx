import { EmailPitch } from "@/types";
import { isEmailPitch } from "@/lib/api";

interface PitchViewerProps {
  pitch: EmailPitch | string;
  channel: string;
}

export function PitchViewer({ pitch, channel }: PitchViewerProps) {
  if (isEmailPitch(pitch)) {
    return (
      <div className="space-y-4">
        <div>
          <span className="font-mono text-[10px] text-text-dim tracking-widest uppercase block mb-1">
            Subject Line
          </span>
          <p className="font-serif text-lg font-bold text-text-primary">
            {pitch.subject}
          </p>
        </div>
        <div className="border-t border-border/50 pt-4">
          <span className="font-mono text-[10px] text-text-dim tracking-widest uppercase block mb-2">
            Email Body
          </span>
          <div className="font-serif text-base text-text-secondary leading-relaxed whitespace-pre-line">
            {pitch.body}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <span className="font-mono text-[10px] text-text-dim tracking-widest uppercase block mb-2">
        Message Body ({channel.toUpperCase()})
      </span>
      <div className="font-mono text-sm text-text-primary leading-relaxed whitespace-pre-line bg-bg-raised p-4 rounded border border-border/50">
        {pitch}
      </div>
    </div>
  );
}
