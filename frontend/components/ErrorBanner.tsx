interface ErrorBannerProps {
  message: string;
  onDismiss: () => void;
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div className="flex items-start gap-3 rounded border-l-[3px] border-l-verdict-fail bg-verdict-fail/8 px-4 py-3 my-3">
      <span className="font-mono text-sm text-verdict-fail shrink-0">ERR</span>
      <p className="font-mono text-sm text-text-secondary flex-1 break-words">
        {message}
      </p>
      <button
        onClick={onDismiss}
        className="text-text-muted hover:text-text-primary text-lg leading-none cursor-pointer"
        aria-label="Dismiss error"
      >
        ×
      </button>
    </div>
  );
}
