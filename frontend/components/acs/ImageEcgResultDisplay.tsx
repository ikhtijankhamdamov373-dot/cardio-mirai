import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { ImageAnalysisResult } from "@/lib/acsApi";

const URGENCY_TONE: Record<string, "red" | "amber" | "blue" | "neutral"> = {
  EMERGENCY: "red",
  HIGH: "amber",
  ROUTINE: "blue",
  INDETERMINATE: "neutral",
};

export function ImageEcgResultDisplay({ result }: { result: ImageAnalysisResult }) {
  const isEmergency = result.urgency === "EMERGENCY";

  return (
    <div className="space-y-4">
      <div className="rounded-card border-2 border-blue bg-blue-soft px-4 py-2 text-center">
        <p className="text-sm font-black text-navy tracking-wide">
          ECG IMAGE DIGITIZATION — RESEARCH PROTOTYPE
        </p>
        <p className="mt-1 text-xs text-muted">Image-derived ECG measurements</p>
      </div>

      <Card>
        <p className="font-bold text-navy">Digitization summary</p>
        <div className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
          <div><p className="text-muted text-xs">Leads extracted</p><p className="font-semibold text-ink">{result.detected_leads.length} of 12</p></div>
          <div><p className="text-muted text-xs">Calibration used</p><p className="font-semibold text-ink">{result.paper_speed_mm_s} mm/s, {result.gain_mm_per_mv} mm/mV</p></div>
          <div><p className="text-muted text-xs">Grid pitch detected</p><p className="font-semibold text-ink">{result.px_per_mm_detected} px/mm</p></div>
          <div><p className="text-muted text-xs">Heart rate</p><p className="font-semibold text-ink">{result.heart_rate_bpm != null ? `${Math.round(result.heart_rate_bpm)} bpm` : "unavailable"}</p></div>
          <div><p className="text-muted text-xs">QRS beats detected</p><p className="font-semibold text-ink">{result.qrs_beat_count}</p></div>
          <div><p className="text-muted text-xs">Image resolution</p><p className="font-semibold text-ink">{result.image_quality.width}×{result.image_quality.height}</p></div>
        </div>
        <p className="mt-3 text-xs font-semibold text-blue">
          {result.calibration_source === "user_confirmed"
            ? `Calibration confirmed by user: ${result.paper_speed_mm_s} mm/s, ${result.gain_mm_per_mv} mm/mV`
            : `Standard calibration assumed: ${result.paper_speed_mm_s} mm/s, ${result.gain_mm_per_mv} mm/mV (not detected by OCR)`}
        </p>
        <p className="mt-2 text-xs text-muted">Extracted: {result.detected_leads.join(", ")}</p>
        {result.excluded_low_confidence_leads.length > 0 && (
          <p className="mt-1 text-xs text-amber">Excluded (unreliable trace extraction): {result.excluded_low_confidence_leads.join(", ")}</p>
        )}
        {result.excluded_low_quality_leads.length > 0 && (
          <p className="mt-1 text-xs text-amber">Excluded (low signal quality): {result.excluded_low_quality_leads.join(", ")}</p>
        )}
      </Card>

      {Object.keys(result.preview_waveforms).length > 0 && (
        <Card>
          <p className="font-bold text-navy">DIGITIZED / DETECTED TRACE PREVIEW</p>
          <p className="mt-1 text-xs text-muted">
            Genuine waveform extracted from the uploaded image&rsquo;s pixels — not a placeholder or demo trace.
          </p>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Object.entries(result.preview_waveforms).map(([lead, values]) => (
              <Sparkline key={lead} lead={lead} values={values} />
            ))}
          </div>
        </Card>
      )}

      {!result.quality_gate_passed ? (
        <Card className="border-red/40 bg-red-soft/30">
          <p className="font-bold text-red">Analysis unavailable</p>
          <p className="mt-1 text-sm text-ink">{result.headline}</p>
          {result.quality_failure_reasons && (
            <ul className="mt-2 text-sm text-muted list-disc list-inside">
              {result.quality_failure_reasons.map((r) => <li key={r}>{r}</li>)}
            </ul>
          )}
        </Card>
      ) : (
        <>
          <Card className={isEmergency ? "border-red/40 bg-red-soft/30 ring-2 ring-red/20" : ""}>
            <Badge tone={URGENCY_TONE[result.urgency] ?? "neutral"}>Urgency: {result.urgency}</Badge>
            {isEmergency && <p className="mt-4 text-2xl sm:text-3xl font-black tracking-tight text-red">EMERGENCY ECG FINDING</p>}
            <p className={isEmergency ? "mt-1 text-xl font-bold text-navy" : "mt-3 text-xl font-black text-navy"}>{result.headline}</p>

            {result.criteria_met && result.contributing_measurements && result.contributing_measurements.length > 0 && (
              <div className="mt-4">
                <p className="text-sm font-bold text-ink">ST elevation detected (from image-derived waveform):</p>
                <ul className="mt-1 text-sm text-muted">
                  {result.contributing_measurements.map((m) => <li key={m.lead}>{m.lead}: +{m.st_elevation_mm} mm</li>)}
                </ul>
                {result.contiguous_leads && result.contiguous_leads.length > 0 && (
                  <p className="mt-1 text-sm text-muted">
                    Contiguous leads: {result.contiguous_leads.join("–")}
                    {result.contiguous_group_name && <span className="font-semibold text-ink"> ({result.contiguous_group_name})</span>}
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

            <p className="mt-4 text-xs text-muted italic">{result.interpretation_note}</p>
            <p className="mt-1 text-xs text-muted italic">{result.disclaimer}</p>
          </Card>

          {result.criteria_met && result.thresholds_applied && (
            <Card className="border-blue/30">
              <Badge tone="blue">Explainability</Badge>
              <p className="mt-2 font-bold text-navy text-lg">Why was this flagged?</p>
              <ul className="mt-2 space-y-1 text-sm text-ink">
                {result.contributing_measurements?.map((m) => {
                  const isV2V3 = m.lead === "V2" || m.lead === "V3";
                  const threshold = isV2V3 ? result.thresholds_applied?.v2_v3_mm : result.thresholds_applied?.general_leads_mm;
                  return <li key={m.lead}>{m.lead}: measured ST elevation {m.st_elevation_mm} mm — required threshold {threshold} mm</li>;
                })}
                <li className="pt-1 font-semibold">≥2 anatomically contiguous leads satisfied{result.contiguous_group_name && ` (${result.contiguous_group_name})`}.</li>
                {result.triggering_rule_id && <li className="text-xs text-muted">Rule: {result.triggering_rule_id}</li>}
              </ul>
              <p className="mt-3 text-xs text-muted">Source: {result.source}</p>
            </Card>
          )}
        </>
      )}

      {result.warnings.length > 0 && (
        <Card className="border-amber/30">
          <p className="font-bold text-amber text-sm">Limitations / warnings</p>
          <ul className="mt-2 text-sm text-ink list-disc list-inside">
            {result.warnings.map((w) => <li key={w}>{w}</li>)}
          </ul>
        </Card>
      )}
    </div>
  );
}

function Sparkline({ lead, values }: { lead: string; values: number[] }) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const width = 100;
  const height = 32;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <div className="rounded-card border border-line bg-white p-2">
      <p className="text-xs font-bold text-navy">{lead}</p>
      <svg viewBox={`0 0 ${width} ${height}`} className="mt-1 h-8 w-full" preserveAspectRatio="none">
        <polyline points={points} fill="none" stroke="#175ca8" strokeWidth="1.2" />
      </svg>
    </div>
  );
}
