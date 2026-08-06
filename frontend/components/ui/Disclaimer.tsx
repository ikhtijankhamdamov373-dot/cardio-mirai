/**
 * Mandatory disclaimer for any page touching ECG AI output, risk scoring,
 * or clinical content. Do not remove or soften this wording without an
 * explicit decision — see Phase 1 safeguard #8.
 */
export function Disclaimer({ compact = false }: { compact?: boolean }) {
  return (
    <div
      role="note"
      aria-label="Research disclaimer"
      className={`rounded-card border border-amber/30 bg-amber/5 text-ink ${
        compact ? "px-4 py-3 text-xs" : "px-5 py-4 text-sm"
      }`}
    >
      <p className="font-bold text-amber">Research prototype. Not a medical device.</p>
      <p className="mt-1 text-muted">
        All outputs are for research and educational purposes only. Results
        require physician confirmation and must not be used for diagnosis or
        treatment decisions. Cardio MIRAI makes no claim of clinical
        accuracy, diagnostic performance, or regulatory validation beyond
        what is reported in its published methodology.
      </p>
    </div>
  );
}
