const STEPS = [
  "Patient",
  "Rural ambulance / clinic",
  "12-lead ECG",
  "Cardio MIRAI ACS",
  "Guideline-based triage",
  "Emergency physician / cardiologist",
  "Appropriate regional pathway",
];

export function RuralWorkflowVisual() {
  return (
    <div className="flex flex-col items-center gap-1">
      {STEPS.map((step, i) => (
        <div key={step} className="flex flex-col items-center">
          <div className="rounded-card border border-line bg-white px-4 py-2 text-sm font-semibold text-navy text-center">
            {step}
          </div>
          {i < STEPS.length - 1 && (
            <span aria-hidden="true" className="text-muted text-lg leading-none py-0.5">
              ↓
            </span>
          )}
        </div>
      ))}
      <p className="mt-3 text-xs text-muted text-center max-w-sm">
        Specific facility names and PCI transfer destinations are not
        hardcoded until regional infrastructure is verified with local
        clinical partners.
      </p>
    </div>
  );
}
