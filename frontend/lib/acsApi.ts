/**
 * Cardio MIRAI ACS — client for the additive /api/acs/* backend endpoints.
 *
 * RESEARCH PROTOTYPE. NOT A MEDICAL DEVICE. NOT FOR CLINICAL USE.
 *
 * Uses the same same-origin proxy strategy as lib/api.ts: calls go to
 * /api/backend/acs/* and next.config.js rewrites them server-side to the
 * FastAPI backend. No backend host is ever hardcoded here.
 */

const PROXY_PREFIX = "/api/backend/acs";

export interface LeadInput {
  lead: string;
  st_elevation_mm: number;
  reciprocal_depression_mm?: number | null;
}

export interface MimicInput {
  lvh?: boolean;
  lbbb?: boolean;
  rbbb?: boolean;
  paced_rhythm?: boolean;
  pericarditis?: boolean;
  brugada?: boolean;
  takotsubo?: boolean;
  early_repolarization?: boolean;
}

export interface PatientInput {
  age: number | null;
  sex: "male" | "female" | null;
  symptomatic: boolean;
  high_clinical_suspicion: boolean;
  ongoing_chest_pain: boolean;
}

export interface EcgQualityInput {
  leads_detected: number;
  calibration_available: boolean;
  signal_suitable: boolean;
  lead_labels_identified: boolean;
}

export interface StemiAssessResult {
  quality_gate_passed: boolean;
  quality_failure_reasons?: string[];
  criteria_met?: boolean;
  requires_clinical_correlation?: boolean;
  mimic_present?: boolean;
  mimic_names?: string[];
  contiguous_leads?: string[];
  contiguous_group_name?: string | null;
  triggering_rule_id?: string | null;
  contributing_measurements?: { lead: string; st_elevation_mm: number }[];
  reciprocal_changes?: { lead: string; reciprocal_depression_mm: number }[];
  thresholds_applied?: Record<string, number | null>;
  urgency: "EMERGENCY" | "HIGH" | "ROUTINE" | "INDETERMINATE";
  headline: string;
  acs_not_excluded_statement?: string | null;
  nstemi_note?: string;
  source?: string;
  disclaimer: string;
  error?: string;
}

export interface RealEcgAnalysisResult {
  analysis_source: "uploaded_real_ecg";
  detected_leads: string[];
  unrecognized_leads: string[];
  duplicate_leads: string[];
  excluded_low_quality_leads: string[];
  sampling_frequency_hz: number;
  duration_seconds: number;
  heart_rate_bpm: number | null;
  qrs_beat_count: number;
  warnings: string[];
  quality_gate_passed: boolean;
  quality_failure_reasons?: string[];
  criteria_met?: boolean;
  requires_clinical_correlation?: boolean;
  mimic_present?: boolean;
  mimic_names?: string[];
  contiguous_leads?: string[];
  contiguous_group_name?: string | null;
  triggering_rule_id?: string | null;
  contributing_measurements?: { lead: string; st_elevation_mm: number }[];
  all_lead_measurements?: { lead: string; st_elevation_mm: number; reciprocal_depression_mm: number | null }[];
  reciprocal_changes?: { lead: string; reciprocal_depression_mm: number }[];
  thresholds_applied?: Record<string, number | null>;
  urgency: "EMERGENCY" | "HIGH" | "ROUTINE" | "INDETERMINATE";
  headline: string;
  acs_not_excluded_statement?: string | null;
  nstemi_note?: string;
  source?: string;
  disclaimer: string;
}

/** Uploads a real digital 12-lead ECG (.hea+.dat pair, or .zip containing
 * one) for genuine measurement and ACS assessment. Never falls back to
 * synthetic/demo data — a parsing or measurement failure throws, with the
 * backend's specific error message, rather than returning a fabricated
 * result. */
export async function analyzeRealEcg(params: {
  files: File[];
  age?: number | null;
  sex?: "male" | "female" | null;
  symptomatic?: boolean;
  high_clinical_suspicion?: boolean;
  ongoing_chest_pain?: boolean;
  paced_rhythm?: boolean;
  pericarditis?: boolean;
  brugada?: boolean;
  takotsubo?: boolean;
  early_repolarization?: boolean;
}): Promise<RealEcgAnalysisResult> {
  const form = new FormData();
  for (const file of params.files) form.append("files", file);
  if (params.age != null) form.append("age", String(params.age));
  if (params.sex) form.append("sex", params.sex);
  form.append("symptomatic", String(Boolean(params.symptomatic)));
  form.append("high_clinical_suspicion", String(Boolean(params.high_clinical_suspicion)));
  form.append("ongoing_chest_pain", String(Boolean(params.ongoing_chest_pain)));
  form.append("paced_rhythm", String(Boolean(params.paced_rhythm)));
  form.append("pericarditis", String(Boolean(params.pericarditis)));
  form.append("brugada", String(Boolean(params.brugada)));
  form.append("takotsubo", String(Boolean(params.takotsubo)));
  form.append("early_repolarization", String(Boolean(params.early_repolarization)));

  const res = await fetch(`${PROXY_PREFIX}/analyze-ecg`, { method: "POST", body: form });
  if (!res.ok) {
    let detail = "The uploaded ECG could not be analyzed.";
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body, keep default message */
    }
    throw new Error(detail);
  }
  return res.json();
}

export interface ImageAnalysisResult {
  analysis_source: "uploaded_ecg_image";
  digitization_method: "image_waveform_extraction";
  detected_leads: string[];
  excluded_low_confidence_leads: string[];
  excluded_low_quality_leads: string[];
  panel_trace_confidence: Record<string, number>;
  px_per_mm_detected: number;
  paper_speed_mm_s: number;
  gain_mm_per_mv: number;
  calibration_confirmed_by_user: boolean;
  image_quality: {
    width: number; height: number; megapixels: number;
    blur_variance: number; estimated_rotation_deg: number;
  };
  sampling_frequency_hz: number;
  heart_rate_bpm: number | null;
  qrs_beat_count: number;
  warnings: string[];
  preview_waveforms: Record<string, number[]>;
  quality_gate_passed: boolean;
  quality_failure_reasons?: string[];
  criteria_met?: boolean;
  requires_clinical_correlation?: boolean;
  mimic_present?: boolean;
  mimic_names?: string[];
  contiguous_leads?: string[];
  contiguous_group_name?: string | null;
  triggering_rule_id?: string | null;
  contributing_measurements?: { lead: string; st_elevation_mm: number }[];
  all_lead_measurements?: { lead: string; st_elevation_mm: number; reciprocal_depression_mm: number | null }[];
  reciprocal_changes?: { lead: string; reciprocal_depression_mm: number }[];
  thresholds_applied?: Record<string, number | null>;
  urgency: "EMERGENCY" | "HIGH" | "ROUTINE" | "INDETERMINATE";
  headline: string;
  acs_not_excluded_statement?: string | null;
  nstemi_note?: string;
  source?: string;
  label?: string;
  interpretation_note?: string;
  disclaimer: string;
}

/** Uploads an ECG photo/PDF for genuine pixel-based waveform digitization.
 * Calibration (paper speed, gain) and layout must be explicitly confirmed
 * by the caller — never silently assumed. Never falls back to synthetic
 * or demo data on failure; throws with the backend's specific error. */
export async function analyzeEcgImage(params: {
  file: File;
  paperSpeedMmS: number;
  gainMmPerMv: number;
  layout: "standard_3x4";
  age?: number | null;
  sex?: "male" | "female" | null;
  symptomatic?: boolean;
  high_clinical_suspicion?: boolean;
  ongoing_chest_pain?: boolean;
}): Promise<ImageAnalysisResult> {
  const form = new FormData();
  form.append("file", params.file);
  form.append("paper_speed_mm_s", String(params.paperSpeedMmS));
  form.append("gain_mm_per_mv", String(params.gainMmPerMv));
  form.append("layout", params.layout);
  if (params.age != null) form.append("age", String(params.age));
  if (params.sex) form.append("sex", params.sex);
  form.append("symptomatic", String(Boolean(params.symptomatic)));
  form.append("high_clinical_suspicion", String(Boolean(params.high_clinical_suspicion)));
  form.append("ongoing_chest_pain", String(Boolean(params.ongoing_chest_pain)));

  const res = await fetch(`${PROXY_PREFIX}/analyze-ecg-image`, { method: "POST", body: form });
  if (!res.ok) {
    let detail = "The ECG image could not be digitized.";
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body, keep default message */
    }
    throw new Error(detail);
  }
  return res.json();
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${PROXY_PREFIX}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`ACS request failed: ${res.status}`);
  }
  return res.json();
}

export async function assessStemi(params: {
  leads: LeadInput[];
  patient: PatientInput;
  mimics?: MimicInput;
  quality: EcgQualityInput;
}): Promise<StemiAssessResult> {
  return postJson<StemiAssessResult>("/assess", params);
}

export async function serialEcgIndication(params: {
  initial_ecg_diagnostic: boolean;
  high_clinical_suspicion?: boolean;
  symptoms_persistent?: boolean;
  condition_deteriorating?: boolean;
  care_setting?: "prehospital" | "in_hospital";
}) {
  return postJson("/serial-ecg-indication", params);
}

export async function hsCtnRepeatWindow(assayType: "hs_ctn" | "conventional") {
  return postJson("/hs-ctn-repeat-window", { assay_type: assayType });
}

/** Synthetic demo fixture — clearly not a real patient. Meets the anterior
 * STEMI general-lead + V2-V3 contiguous criteria (ACS-CORE-001/002) with a
 * clean, artifact-free quality profile so the demo always succeeds. */
export const DEMO_CASE = {
  label: "SYNTHETIC DEMONSTRATION — NOT A REAL PATIENT",
  patient: {
    age: 58,
    sex: "male" as const,
    symptomatic: true,
    high_clinical_suspicion: true,
    ongoing_chest_pain: true,
    main_symptom: "Acute central chest pain",
    onset_minutes_ago: 45,
    sbp: 148,
    dbp: 88,
    heart_rate: 84,
    spo2: 97,
    diabetes: true,
  },
  leads: [
    { lead: "V2", st_elevation_mm: 2.3 },
    { lead: "V3", st_elevation_mm: 2.5 },
    { lead: "V4", st_elevation_mm: 1.8 },
  ] as LeadInput[],
  quality: {
    leads_detected: 12,
    calibration_available: true,
    signal_suitable: true,
    lead_labels_identified: true,
  } as EcgQualityInput,
};
