/**
 * Cardio MIRAI — Digital Lifeline presentation layer.
 *
 * RESEARCH PROTOTYPE. NOT A MEDICAL DEVICE. NOT FOR CLINICAL USE.
 *
 * This module adds NO new clinical logic. It reuses the existing,
 * already-audited analyzeEcgImage() call and maps its already-computed
 * urgency/criteria_met fields to a RED/YELLOW/GREEN presentation label.
 * The underlying ACS engine, thresholds, and guideline citations are
 * completely untouched.
 */

import { analyzeEcgImage, ImageAnalysisResult } from "@/lib/acsApi";

export type TriageLevel = "RED" | "YELLOW" | "GREEN" | "UNKNOWN";

export interface TriageOutcome {
  level: TriageLevel;
  isRealResult: boolean; // true only if genuinely derived from the uploaded image
  result?: ImageAnalysisResult;
  failureReason?: string;
}

/**
 * Maps an already-computed ACS result to a triage colour. Does not
 * introduce any new clinical judgment — RED requires the same
 * criteria_met+EMERGENCY the existing engine already computes, YELLOW the
 * same HIGH urgency, GREEN the same ROUTINE/non-diagnostic outcome.
 */
function mapResultToTriage(result: ImageAnalysisResult): TriageLevel {
  if (!result.quality_gate_passed) return "UNKNOWN";
  if (result.criteria_met && result.urgency === "EMERGENCY") return "RED";
  if (result.urgency === "HIGH") return "YELLOW";
  return "GREEN";
}

/**
 * Runs the real image pipeline and returns a triage outcome. Never
 * fabricates a triage level when the pipeline fails or the quality gate
 * doesn't pass — callers must handle isRealResult=false by falling back
 * to the clearly-labeled demonstration workflow, never by inventing a
 * color for this specific upload.
 */
export async function runRealTriage(params: {
  file: File;
  age?: number | null;
  sex?: "male" | "female" | null;
  symptomatic?: boolean;
  high_clinical_suspicion?: boolean;
  ongoing_chest_pain?: boolean;
}): Promise<TriageOutcome> {
  try {
    const result = await analyzeEcgImage(params);
    const level = mapResultToTriage(result);
    if (level === "UNKNOWN") {
      return {
        level: "UNKNOWN",
        isRealResult: false,
        result,
        failureReason: result.headline || "Image quality insufficient for reliable screening.",
      };
    }
    return { level, isRealResult: true, result };
  } catch (err) {
    return {
      level: "UNKNOWN",
      isRealResult: false,
      failureReason: err instanceof Error ? err.message : "Analysis failed.",
    };
  }
}

/** Pre-built, clearly-synthetic outcomes for the Presentation Demo menu.
 * These never touch the backend and are never labeled as derived from a
 * real upload. */
export const SYNTHETIC_DEMO_OUTCOMES: Record<"RED" | "YELLOW" | "GREEN", TriageOutcome> = {
  RED: {
    level: "RED",
    isRealResult: false,
    result: {
      analysis_source: "uploaded_ecg_image",
      digitization_method: "image_waveform_extraction",
      detected_leads: ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"],
      excluded_low_confidence_leads: [],
      excluded_low_quality_leads: [],
      panel_trace_confidence: {},
      px_per_mm_detected: 8,
      paper_speed_mm_s: 25,
      gain_mm_per_mv: 10,
      calibration_source: "default",
      image_quality: { width: 0, height: 0, megapixels: 0, blur_variance: 0, estimated_rotation_deg: 0 },
      sampling_frequency_hz: 250,
      heart_rate_bpm: 88,
      qrs_beat_count: 6,
      warnings: [],
      preview_waveforms: {},
      quality_gate_passed: true,
      criteria_met: true,
      requires_clinical_correlation: false,
      mimic_present: false,
      mimic_names: [],
      contiguous_leads: ["V2", "V3", "V4"],
      contiguous_group_name: "Anteroseptal",
      triggering_rule_id: "ACS-CORE-002",
      contributing_measurements: [
        { lead: "V2", st_elevation_mm: 2.6 },
        { lead: "V3", st_elevation_mm: 2.7 },
        { lead: "V4", st_elevation_mm: 2.4 },
      ],
      all_lead_measurements: [],
      reciprocal_changes: [],
      thresholds_applied: { general_leads_mm: 1.0, v2_v3_mm: 2.0 },
      urgency: "EMERGENCY",
      headline: "ECG meets guideline STEMI criteria",
      acs_not_excluded_statement: null,
      nstemi_note: "NSTEMI cannot be determined from ECG alone",
      source: "2025 ACC/AHA ACS Guideline / 2023 ESC ACS Guideline / Fifth Universal Definition of Myocardial Infarction (2026)",
      label: "ECG IMAGE DIGITIZATION — RESEARCH PROTOTYPE",
      interpretation_note: "AI-assisted ECG interpretation from a photographed/scanned ECG. Not clinically validated.",
      disclaimer: "Cardio MIRAI provides decision support and does not replace clinical diagnosis.",
    },
  },
  YELLOW: {
    level: "YELLOW",
    isRealResult: false,
    result: {
      analysis_source: "uploaded_ecg_image",
      digitization_method: "image_waveform_extraction",
      detected_leads: ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"],
      excluded_low_confidence_leads: [],
      excluded_low_quality_leads: [],
      panel_trace_confidence: {},
      px_per_mm_detected: 8,
      paper_speed_mm_s: 25,
      gain_mm_per_mv: 10,
      calibration_source: "default",
      image_quality: { width: 0, height: 0, megapixels: 0, blur_variance: 0, estimated_rotation_deg: 0 },
      sampling_frequency_hz: 250,
      heart_rate_bpm: 92,
      qrs_beat_count: 6,
      warnings: [],
      preview_waveforms: {},
      quality_gate_passed: true,
      criteria_met: false,
      requires_clinical_correlation: false,
      mimic_present: false,
      mimic_names: [],
      contiguous_leads: [],
      contiguous_group_name: null,
      triggering_rule_id: null,
      contributing_measurements: [],
      all_lead_measurements: [],
      reciprocal_changes: [],
      thresholds_applied: { general_leads_mm: 1.0, v2_v3_mm: 2.0 },
      urgency: "HIGH",
      headline: "STEMI criteria not detected on this ECG",
      acs_not_excluded_statement: "A nondiagnostic ECG does not exclude ACS. Clinical assessment, serial ECG and cardiac troponin testing may be required.",
      nstemi_note: "NSTEMI cannot be determined from ECG alone",
      source: "2025 ACC/AHA ACS Guideline / 2023 ESC ACS Guideline / Fifth Universal Definition of Myocardial Infarction (2026)",
      label: "ECG IMAGE DIGITIZATION — RESEARCH PROTOTYPE",
      interpretation_note: "AI-assisted ECG interpretation from a photographed/scanned ECG. Not clinically validated.",
      disclaimer: "Cardio MIRAI provides decision support and does not replace clinical diagnosis.",
    },
  },
  GREEN: {
    level: "GREEN",
    isRealResult: false,
    result: {
      analysis_source: "uploaded_ecg_image",
      digitization_method: "image_waveform_extraction",
      detected_leads: ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"],
      excluded_low_confidence_leads: [],
      excluded_low_quality_leads: [],
      panel_trace_confidence: {},
      px_per_mm_detected: 8,
      paper_speed_mm_s: 25,
      gain_mm_per_mv: 10,
      calibration_source: "default",
      image_quality: { width: 0, height: 0, megapixels: 0, blur_variance: 0, estimated_rotation_deg: 0 },
      sampling_frequency_hz: 250,
      heart_rate_bpm: 72,
      qrs_beat_count: 6,
      warnings: [],
      preview_waveforms: {},
      quality_gate_passed: true,
      criteria_met: false,
      requires_clinical_correlation: false,
      mimic_present: false,
      mimic_names: [],
      contiguous_leads: [],
      contiguous_group_name: null,
      triggering_rule_id: null,
      contributing_measurements: [],
      all_lead_measurements: [],
      reciprocal_changes: [],
      thresholds_applied: { general_leads_mm: 1.0, v2_v3_mm: 2.0 },
      urgency: "ROUTINE",
      headline: "STEMI criteria not detected on this ECG",
      acs_not_excluded_statement: "A nondiagnostic ECG does not exclude ACS. Clinical assessment, serial ECG and cardiac troponin testing may be required.",
      nstemi_note: "NSTEMI cannot be determined from ECG alone",
      source: "2025 ACC/AHA ACS Guideline / 2023 ESC ACS Guideline / Fifth Universal Definition of Myocardial Infarction (2026)",
      label: "ECG IMAGE DIGITIZATION — RESEARCH PROTOTYPE",
      interpretation_note: "AI-assisted ECG interpretation from a photographed/scanned ECG. Not clinically validated.",
      disclaimer: "Cardio MIRAI provides decision support and does not replace clinical diagnosis.",
    },
  },
};
