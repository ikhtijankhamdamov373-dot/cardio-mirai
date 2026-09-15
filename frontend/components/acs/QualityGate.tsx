import type { EcgQualityInput } from "@/lib/acsApi";
import { Card } from "@/components/ui/Card";

const CHECKS: { key: keyof EcgQualityInput; label: string; isCount?: boolean }[] = [
  { key: "leads_detected", label: "12 leads detected", isCount: true },
  { key: "calibration_available", label: "Calibration available" },
  { key: "signal_suitable", label: "Signal suitable for analysis" },
  { key: "lead_labels_identified", label: "Lead labels identified" },
];

export function QualityGate({ quality }: { quality: EcgQualityInput }) {
  const acceptable =
    quality.leads_detected >= 12 &&
    quality.calibration_available &&
    quality.signal_suitable &&
    quality.lead_labels_identified;

  return (
    <Card className={acceptable ? "border-green/30" : "border-red/30"}>
      <p className="font-bold text-navy">ECG Quality</p>
      <ul className="mt-3 space-y-1.5 text-sm">
        {CHECKS.map((check) => {
          const value = quality[check.key];
          const pass = check.isCount ? Number(value) >= 12 : Boolean(value);
          return (
            <li key={check.key} className={pass ? "text-green" : "text-red"}>
              {pass ? "✓" : "✗"} {check.label}
            </li>
          );
        })}
      </ul>
      {!acceptable && (
        <p className="mt-3 text-sm font-bold text-red">
          Analysis unavailable — ECG quality is insufficient for reliable
          assessment. Please repeat ECG acquisition.
        </p>
      )}
    </Card>
  );
}
