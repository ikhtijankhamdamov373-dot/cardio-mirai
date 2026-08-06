export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 text-muted text-sm py-4">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-blue border-t-transparent"
        aria-hidden="true"
      />
      {label}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-card border border-red/30 bg-red-soft px-4 py-3 text-sm text-red"
    >
      <p className="font-bold">Something went wrong</p>
      <p className="mt-1">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded-card border border-red/40 px-3 py-1.5 text-xs font-bold hover:bg-red hover:text-white transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  );
}
