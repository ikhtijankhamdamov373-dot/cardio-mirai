"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingState, ErrorState } from "@/components/ui/PageStatus";
import type { EcgQualityInput, LeadInput, RealEcgAnalysisResult } from "@/lib/acsApi";
import { analyzeRealEcg } from "@/lib/acsApi";
import { RealEcgResultDisplay } from "@/components/acs/RealEcgResultDisplay";
import type { PatientFormState } from "@/components/acs/PatientForm";

const MANUAL_LEADS = ["II", "III", "aVF", "V2", "V3", "V4"];
const ACCEPTED_EXTENSIONS = [".hea", ".dat", ".zip"]; // confirmed by backend audit — see delivery report

export interface EcgInputState {
  quality: EcgQualityInput;
  leads: LeadInput[];
}

export const emptyEcgInput: EcgInputState = {
  quality: {
    leads_detected: 0,
    calibration_available: false,
    signal_suitable: false,
    lead_labels_identified: false,
  },
  leads: MANUAL_LEADS.map((lead) => ({ lead, st_elevation_mm: 0 })),
};

type UploadStatus = "idle" | "ready" | "uploading" | "success" | "error";

export function EcgInputStep({
  value,
  onChange,
  patient,
}: {
  value: EcgInputState;
  onChange: (next: EcgInputState) => void;
  patient?: Pick<
    PatientFormState,
    "age" | "sex" | "symptomatic" | "high_clinical_suspicion" | "ongoing_chest_pain"
  >;
}) {
  const [manualOpen, setManualOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [realResult, setRealResult] = useState<RealEcgAnalysisResult | null>(null);

  const setLead = (lead: string, mm: number) => {
    onChange({
      ...value,
      leads: value.leads.map((l) => (l.lead === lead ? { ...l, st_elevation_mm: mm } : l)),
    });
  };

  const setQualityAcceptable = (acceptable: boolean) => {
    onChange({
      ...value,
      quality: {
        leads_detected: acceptable ? 12 : 6,
        calibration_available: acceptable,
        signal_suitable: acceptable,
        lead_labels_identified: acceptable,
      },
    });
  };

  const handleFileSelect = (fileList: FileList | null) => {
    setRealResult(null);
    setUploadError(null);
    if (!fileList || fileList.length === 0) {
      setSelectedFiles([]);
      setUploadStatus("idle");
      return;
    }
    const files = Array.from(fileList);
    const invalid = files.filter(
      (f) => !ACCEPTED_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    if (invalid.length > 0) {
      setUploadError(
        `Unsupported file(s): ${invalid.map((f) => f.name).join(", ")}. Accepted: ${ACCEPTED_EXTENSIONS.join(", ")}`
      );
      setSelectedFiles([]);
      setUploadStatus("error");
      return;
    }
    setSelectedFiles(files);
    setUploadStatus("ready");
  };

  const runRealAnalysis = async () => {
    setUploadStatus("uploading");
    setUploadError(null);
    try {
      const result = await analyzeRealEcg({
        files: selectedFiles,
        age: patient?.age ?? null,
        sex: patient?.sex ?? null,
        symptomatic: patient?.symptomatic,
        high_clinical_suspicion: patient?.high_clinical_suspicion,
        ongoing_chest_pain: patient?.ongoing_chest_pain,
      });
      setRealResult(result);
      setUploadStatus("success");
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Analysis failed.");
      setUploadStatus("error");
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <p className="font-bold text-navy">Upload Digital 12-Lead ECG</p>
          <Badge tone="blue">Available for prototype analysis</Badge>
          <p className="mt-2 text-sm text-muted">
            Accepts WFDB records (.hea + .dat pair, or a .zip containing
            one) — the only real digital ECG format currently supported.
            The uploaded waveform is genuinely parsed and measured; no
            synthetic values are ever substituted.
          </p>
          <input
            type="file"
            accept=".hea,.dat,.zip"
            multiple
            onChange={(e) => handleFileSelect(e.target.files)}
            className="mt-3 w-full text-sm"
          />
          {selectedFiles.length > 0 && (
            <div className="mt-2 text-xs text-muted">
              {selectedFiles.map((f) => (
                <p key={f.name}>
                  {f.name} — {(f.size / 1024).toFixed(1)} KB
                </p>
              ))}
            </div>
          )}
          {uploadStatus === "ready" && (
            <Button className="mt-3" onClick={runRealAnalysis}>
              Analyze Uploaded ECG
            </Button>
          )}
          {uploadStatus === "uploading" && (
            <div className="mt-3">
              <LoadingState label="Parsing and measuring the uploaded waveform…" />
            </div>
          )}
          {uploadStatus === "error" && uploadError && (
            <div className="mt-3">
              <ErrorState message={uploadError} onRetry={selectedFiles.length > 0 ? runRealAnalysis : undefined} />
            </div>
          )}
          {uploadStatus === "success" && (
            <p className="mt-3 text-sm font-semibold text-green">Upload analyzed successfully.</p>
          )}
        </Card>

        <Card>
          <p className="font-bold text-navy">Take / Upload ECG Photo</p>
          <Badge tone="amber">ECG photo/PDF digitization — experimental / under development</Badge>
          <p className="mt-2 text-sm text-muted">
            Central to the rural Uzbekistan use case. No validated
            photo/PDF-to-waveform digitization pipeline exists in this
            repository yet (confirmed by audit) — file selection is shown
            for workflow demonstration only and does not produce clinical
            ECG measurements.
          </p>
          <input type="file" accept="image/*,.pdf" capture="environment" disabled className="mt-3 w-full text-sm opacity-50" />
        </Card>
      </div>

      {realResult && <RealEcgResultDisplay result={realResult} />}

      <Card>
        <button
          onClick={() => setManualOpen((v) => !v)}
          className="flex w-full items-center justify-between text-left"
          aria-expanded={manualOpen}
        >
          <span className="font-bold text-navy">Manual entry (synthetic demo / interactive exploration)</span>
          <span className="text-muted text-sm">{manualOpen ? "Hide" : "Show"}</span>
        </button>
        {manualOpen && (
          <div className="mt-4 space-y-4">
            <p className="text-xs text-amber font-semibold">
              SYNTHETIC — values entered here are not derived from any uploaded waveform.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => setQualityAcceptable(true)}>
                Mark ECG quality: acceptable
              </Button>
              <Button variant="secondary" onClick={() => setQualityAcceptable(false)}>
                Mark ECG quality: poor
              </Button>
            </div>
            <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
              {value.leads.map((l) => (
                <label key={l.lead} className="text-xs font-semibold text-ink">
                  {l.lead} (mm)
                  <input
                    type="number"
                    step="0.1"
                    className="mt-1 w-full rounded-card border border-line px-2 py-2 text-sm"
                    value={l.st_elevation_mm}
                    onChange={(e) => setLead(l.lead, Number(e.target.value))}
                  />
                </label>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
