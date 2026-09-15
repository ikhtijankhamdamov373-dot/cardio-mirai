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
  contributing_measurements?: { lead: string; st_elevation_mm: number }[];
  thresholds_applied?: Record<string, number | null>;
  urgency: "EMERGENCY" | "HIGH" | "ROUTINE" | "INDETERMINATE";
  headline: string;
  acs_not_excluded_statement?: string | null;
  nstemi_note?: string;
  source?: string;
  disclaimer: string;
  error?: string;
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
