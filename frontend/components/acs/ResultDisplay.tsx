import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { StemiAssessResult } from "@/lib/acsApi";

const URGENCY_TONE: Record<string, "red" | "amber" | "blue" | "neutral"> = {
  EMERGENCY: "red",
  HIGH: "amber",
  ROUTINE: "blue",
  INDETERMINATE: "neutral",
};

export function ResultDisplay({ result }: { result: StemiAssessResult }) {
  if (!result.quality_gate_passed) {
    // QualityGate component already renders the failure state; this result
    // display intentionally shows nothing further per "quality failure must
    // prevent downstream diagnostic output."
    return null;
  }

  const isEmergency = result.urgency === "EMERGENCY";

  return (
    <div className="space-y-4">
      <Card className={isEmergency ? "border-red/40 bg-red-soft/30" : ""}>
        <div className="flex items-center gap-2">
          <Badge tone={URGENCY_TONE[result.urgency] ?? "neutral"}>
            Urgency: {result.urgency}
          </Badge>
        </div>
        <p className={`mt-3 text-xl font-black ${isEmergency ? "text-red" : "text-navy"}`}>
          {isEmergency ? "EMERGENCY ECG FINDING" : result.headline}
        </p>
        {isEmergency && <p className="mt-1 text-lg font-bold text-navy">{result.headline}</p>}

        {result.criteria_met && result.contributing_measurements && result.contributing_measurements.length > 0 && (
          <div className="mt-4">
            <p className="text-sm font-bold text-ink">ST elevation detected:</p>
            <ul className="mt-1 text-sm text-muted">
              {result.contributing_measurements.map((m) => (
                <li key={m.lead}>
                  {m.lead}: +{m.st_elevation_mm} mm
                </li>
              ))}
            </ul>
            {result.contiguous_leads && result.contiguous_leads.length > 0 && (
              <p className="mt-1 text-sm text-muted">
                Contiguous leads: {result.contiguous_leads.join("–")}
              </p>
            )}
          </div>
        )}

        {!result.criteria_met && result.acs_not_excluded_statement && (
          <div className="mt-4 rounded-card border border-amber/30 bg-amber/5 px-4 py-3">
            <p className="font-bold text-amber">ACS CANNOT BE EXCLUDED</p>
            <p className="mt-1 text-sm text-ink">{result.acs_not_excluded_statement}</p>
          </div>
        )}

        {result.requires_clinical_correlation && (
          <div className="mt-4 rounded-card border border-amber/30 bg-amber/5 px-4 py-3">
            <p className="font-bold text-amber">Requires clinical correlation</p>
            <p className="mt-1 text-sm text-ink">
              Possible mimic present ({result.mimic_names?.join(", ")}). This
              finding should not be treated as an unqualified emergency
              result without physician correlation.
            </p>
          </div>
        )}

        <div className="mt-4">
          <p className="font-bold text-navy text-sm">Action</p>
          <p className="mt-1 text-sm text-ink">
            {isEmergency
              ? "Urgent emergency physician/cardiology review and activation of the locally approved STEMI pathway should be considered without delay."
              : "Clinical assessment, serial ECG and cardiac troponin testing may be required per the locally adopted ACS pathway."}
          </p>
        </div>

        <p className="mt-4 text-xs text-muted italic">{result.disclaimer}</p>
      </Card>

      {result.criteria_met && result.thresholds_applied && (
        <Card>
          <p className="font-bold text-navy">Why was this flagged?</p>
          <ul className="mt-2 space-y-1 text-sm text-ink">
            {result.contributing_measurements?.map((m) => {
              const isV2V3 = m.lead === "V2" || m.lead === "V3";
              const threshold = isV2V3
                ? result.thresholds_applied?.v2_v3_mm
                : result.thresholds_applied?.general_leads_mm;
              return (
                <li key={m.lead}>
                  {m.lead}: measured ST elevation {m.st_elevation_mm} mm — required
                  threshold {threshold} mm
                </li>
              );
            })}
            <li className="pt-1 font-semibold">≥2 anatomically contiguous leads satisfied.</li>
          </ul>
          <p className="mt-3 text-xs text-muted">Source: {result.source}</p>
        </Card>
      )}

      <NstemiSection result={result} />
    </div>
  );
}

function NstemiSection({ result }: { result: StemiAssessResult }) {
  return (
    <Card>
      <p className="font-bold text-navy">NSTE-ACS Assessment</p>
      <p className="mt-2 text-sm font-semibold text-ink">
        {result.nstemi_note ?? "NSTEMI cannot be determined from ECG alone"}
      </p>
      <p className="mt-1 text-sm text-muted">
        Obtain/review hs-cTn and repeat testing according to the locally
        adopted ACS pathway.
      </p>
      <p className="mt-3 text-xs text-muted">
        If implementing timing support, only the verified source-specific
        rule is used: <strong>ACC/AHA 2025 — repeat hs-cTn at 1–2 hours when
        indicated.</strong> ESC 0/1-h algorithm assay-specific cutoffs are not
        implemented (Matrix v1.2, ACS-CORE-010, unresolved).
      </p>
    </Card>
  );
}
