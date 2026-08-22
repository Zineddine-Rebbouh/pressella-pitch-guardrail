interface ErrorBannerProps {
  message: string;
  onDismiss: () => void;
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div className="flex items-start gap-3 rounded border-l-[3px] border-l-verdict-fail bg-verdict-fail/10 px-4 py-3 my-3">
      <span className="font-mono text-xs font-bold text-verdict-fail shrink-0 tracking-wider">
        ERROR
      </span>
      <p className="font-mono text-xs text-text-secondary flex-1 break-words leading-relaxed">
        {message}
      </p>
      <button
        onClick={onDismiss}
        className="text-text-muted hover:text-text-primary text-sm font-mono leading-none cursor-pointer px-1"
        aria-label="Dismiss error"
      >
        Dismiss
      </button>
    </div>
  );
}
