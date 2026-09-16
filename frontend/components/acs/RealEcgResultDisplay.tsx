import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { RealEcgAnalysisResult } from "@/lib/acsApi";

const URGENCY_TONE: Record<string, "red" | "amber" | "blue" | "neutral"> = {
  EMERGENCY: "red",
  HIGH: "amber",
  ROUTINE: "blue",
  INDETERMINATE: "neutral",
};

export function RealEcgResultDisplay({ result }: { result: RealEcgAnalysisResult }) {
  const isEmergency = result.urgency === "EMERGENCY";

  return (
    <div className="space-y-4">
      <div className="rounded-card border-2 border-blue bg-blue-soft px-4 py-2 text-center">
        <p className="text-sm font-black text-navy tracking-wide">REAL ECG ANALYSIS</p>
      </div>

      <Card>
        <p className="font-bold text-navy">Recording summary</p>
        <div className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          <div>
            <p className="text-muted text-xs">Leads detected</p>
            <p className="font-semibold text-ink">{result.detected_leads.length} of 12</p>
          </div>
          <div>
            <p className="text-muted text-xs">Sampling rate</p>
            <p className="font-semibold text-ink">{result.sampling_frequency_hz} Hz</p>
          </div>
          <div>
            <p className="text-muted text-xs">Duration</p>
            <p className="font-semibold text-ink">{result.duration_seconds} s</p>
          </div>
          <div>
            <p className="text-muted text-xs">Heart rate</p>
            <p className="font-semibold text-ink">
              {result.heart_rate_bpm != null ? `${Math.round(result.heart_rate_bpm)} bpm` : "unavailable"}
            </p>
          </div>
          <div>
            <p className="text-muted text-xs">QRS beats detected</p>
            <p className="font-semibold text-ink">{result.qrs_beat_count}</p>
          </div>
          <div>
            <p className="text-muted text-xs">Quality status</p>
            <p className="font-semibold text-ink">
              {result.quality_gate_passed ? "Acceptable" : "Insufficient"}
            </p>
          </div>
        </div>
        <p className="mt-3 text-xs text-muted">Detected: {result.detected_leads.join(", ")}</p>
        {result.unrecognized_leads.length > 0 && (
          <p className="mt-1 text-xs text-amber">Unrecognized labels ignored: {result.unrecognized_leads.join(", ")}</p>
        )}
        {result.duplicate_leads.length > 0 && (
          <p className="mt-1 text-xs text-amber">Duplicate labels (first occurrence used): {result.duplicate_leads.join(", ")}</p>
        )}
        {result.excluded_low_quality_leads.length > 0 && (
          <p className="mt-1 text-xs text-amber">Excluded for low signal quality: {result.excluded_low_quality_leads.join(", ")}</p>
        )}
      </Card>

      {!result.quality_gate_passed ? (
        <Card className="border-red/40 bg-red-soft/30">
          <p className="font-bold text-red">Analysis unavailable</p>
          <p className="mt-1 text-sm text-ink">{result.headline}</p>
          {result.quality_failure_reasons && (
            <ul className="mt-2 text-sm text-muted list-disc list-inside">
              {result.quality_failure_reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
        </Card>
      ) : (
        <>
          <Card className={isEmergency ? "border-red/40 bg-red-soft/30 ring-2 ring-red/20" : ""}>
            <Badge tone={URGENCY_TONE[result.urgency] ?? "neutral"}>Urgency: {result.urgency}</Badge>
            {isEmergency && (
              <p className="mt-4 text-2xl sm:text-3xl font-black tracking-tight text-red">
                EMERGENCY ECG FINDING
              </p>
            )}
            <p className={isEmergency ? "mt-1 text-xl font-bold text-navy" : "mt-3 text-xl font-black text-navy"}>
              {result.headline}
            </p>

            {result.criteria_met && result.contributing_measurements && result.contributing_measurements.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-bold text-ink">ST elevation detected (measured from uploaded waveform):</p>
                <ul className="mt-1 text-sm text-muted">
                  {result.contributing_measurements.map((m) => (
                    <li key={m.lead}>{m.lead}: +{m.st_elevation_mm} mm</li>
                  ))}
                </ul>
                {result.contiguous_leads && result.contiguous_leads.length > 0 && (
                  <p className="mt-1 text-sm text-muted">
                    Contiguous leads: {result.contiguous_leads.join("–")}
                    {result.contiguous_group_name && (
                      <span className="font-semibold text-ink"> ({result.contiguous_group_name})</span>
                    )}
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
                  Possible mimic detected on the real waveform ({result.mimic_names?.join(", ")}).
                </p>
              </div>
            )}

            <p className="mt-4 text-xs text-muted italic">{result.disclaimer}</p>
          </Card>

          {result.criteria_met && result.thresholds_applied && (
            <Card className="border-blue/30">
              <Badge tone="blue">Explainability</Badge>
              <p className="mt-2 font-bold text-navy text-lg">Why was this flagged?</p>
              <ul className="mt-2 space-y-1 text-sm text-ink">
                {result.contributing_measurements?.map((m) => {
                  const isV2V3 = m.lead === "V2" || m.lead === "V3";
                  const threshold = isV2V3
                    ? result.thresholds_applied?.v2_v3_mm
                    : result.thresholds_applied?.general_leads_mm;
                  return (
                    <li key={m.lead}>
                      {m.lead}: measured ST elevation {m.st_elevation_mm} mm — required threshold {threshold} mm
                    </li>
                  );
                })}
                <li className="pt-1 font-semibold">
                  ≥2 anatomically contiguous leads satisfied{result.contiguous_group_name && ` (${result.contiguous_group_name})`}.
                </li>
                {result.triggering_rule_id && (
                  <li className="text-xs text-muted">Rule: {result.triggering_rule_id}</li>
                )}
              </ul>
              <p className="mt-3 text-xs text-muted">Source: {result.source}</p>
            </Card>
          )}

          <Card>
            <p className="font-bold text-navy">All measured leads</p>
            <ul className="mt-2 grid grid-cols-2 gap-1 text-sm text-ink sm:grid-cols-3">
              {result.all_lead_measurements?.map((m) => (
                <li key={m.lead}>
                  {m.lead}: {m.reciprocal_depression_mm != null ? `−${m.reciprocal_depression_mm}` : `+${m.st_elevation_mm}`} mm
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}

      {result.warnings.length > 0 && (
        <Card className="border-amber/30">
          <p className="font-bold text-amber text-sm">Limitations / warnings</p>
          <ul className="mt-2 text-sm text-ink list-disc list-inside">
            {result.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
