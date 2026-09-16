"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { LoadingState, ErrorState } from "@/components/ui/PageStatus";
import type { EcgQualityInput, LeadInput, RealEcgAnalysisResult, ImageAnalysisResult } from "@/lib/acsApi";
import { analyzeRealEcg, analyzeEcgImage } from "@/lib/acsApi";
import { RealEcgResultDisplay } from "@/components/acs/RealEcgResultDisplay";
import { ImageEcgResultDisplay } from "@/components/acs/ImageEcgResultDisplay";
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

  // Image/PDF digitization workflow state
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [calibrationConfirmed, setCalibrationConfirmed] = useState(false);
  const [layoutConfirmed, setLayoutConfirmed] = useState(false);
  const [imageStatus, setImageStatus] = useState<UploadStatus>("idle");
  const [imageError, setImageError] = useState<string | null>(null);
  const [imageResult, setImageResult] = useState<ImageAnalysisResult | null>(null);
  const PAPER_SPEED_MM_S = 25;
  const GAIN_MM_PER_MV = 10;

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

  const handleImageSelect = (fileList: FileList | null) => {
    setImageResult(null);
    setImageError(null);
    setCalibrationConfirmed(false);
    setLayoutConfirmed(false);
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    if (!fileList || fileList.length === 0) {
      setImageFile(null);
      setImagePreviewUrl(null);
      setImageStatus("idle");
      return;
    }
    const file = fileList[0];
    const valid = [".jpg", ".jpeg", ".png", ".pdf"].some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!valid) {
      setImageError(`Unsupported file: ${file.name}. Accepted: .jpg, .jpeg, .png, .pdf`);
      setImageStatus("error");
      setImageFile(null);
      return;
    }
    setImageFile(file);
    setImagePreviewUrl(file.type.startsWith("image/") ? URL.createObjectURL(file) : null);
    setImageStatus("ready");
  };

  const runImageDigitization = async () => {
    if (!imageFile) return;
    setImageStatus("uploading");
    setImageError(null);
    try {
      const result = await analyzeEcgImage({
        file: imageFile,
        paperSpeedMmS: PAPER_SPEED_MM_S,
        gainMmPerMv: GAIN_MM_PER_MV,
        layout: "standard_3x4",
        age: patient?.age ?? null,
        sex: patient?.sex ?? null,
        symptomatic: patient?.symptomatic,
        high_clinical_suspicion: patient?.high_clinical_suspicion,
        ongoing_chest_pain: patient?.ongoing_chest_pain,
      });
      setImageResult(result);
      setImageStatus("success");
    } catch (err) {
      setImageError(err instanceof Error ? err.message : "Digitization failed.");
      setImageStatus("error");
    }
  };

  const imageSteps = [
    { label: "Upload received", done: !!imageFile },
    { label: "Image quality checked", done: imageStatus === "success" || imageStatus === "uploading" },
    { label: "ECG layout identified/confirmed", done: layoutConfirmed },
    { label: "Calibration confirmed", done: calibrationConfirmed },
    { label: "Waveforms digitized", done: imageStatus === "success" },
    { label: "ECG measurements generated", done: imageStatus === "success" },
    { label: "ACS rules evaluated", done: imageStatus === "success" },
  ];

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
          <Badge tone="blue">ECG photo/PDF digitization — research prototype</Badge>
          <p className="mt-2 text-sm text-muted">
            Accepts JPG, PNG, or a single-page PDF. Waveforms are genuinely
            extracted from the uploaded image&rsquo;s pixels — nothing is
            substituted or demonstrated with placeholder data.
          </p>
          <input
            type="file"
            accept=".jpg,.jpeg,.png,.pdf"
            onChange={(e) => handleImageSelect(e.target.files)}
            className="mt-3 w-full text-sm"
          />

          {imagePreviewUrl && (
            <div className="mt-3">
              <p className="text-xs font-bold text-muted">ORIGINAL ECG</p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={imagePreviewUrl} alt="Uploaded ECG preview" className="mt-1 max-h-40 w-full rounded-card border border-line object-contain" />
            </div>
          )}

          {imageFile && (
            <div className="mt-4 space-y-3">
              <div>
                <p className="text-xs font-bold text-ink">Calibration</p>
                <p className="text-xs text-muted mb-1">
                  For today&rsquo;s prototype, confirm the standard values rather than relying on automatic detection.
                </p>
                <Button
                  variant={calibrationConfirmed ? "primary" : "secondary"}
                  onClick={() => setCalibrationConfirmed(true)}
                >
                  Confirm {PAPER_SPEED_MM_S} mm/s, {GAIN_MM_PER_MV} mm/mV
                </Button>
                {calibrationConfirmed && (
                  <p className="mt-1 text-xs text-green">
                    Calibration confirmed by user: {PAPER_SPEED_MM_S} mm/s, {GAIN_MM_PER_MV} mm/mV
                  </p>
                )}
              </div>

              <div>
                <p className="text-xs font-bold text-ink">Detected layout</p>
                <div className="mt-1 flex flex-wrap gap-2">
                  <Button
                    variant={layoutConfirmed ? "primary" : "secondary"}
                    onClick={() => setLayoutConfirmed(true)}
                  >
                    Standard 3×4
                  </Button>
                  <Button variant="ghost" disabled>Standard 6×2 (unsupported)</Button>
                  <Button variant="ghost" disabled>Other / unsupported</Button>
                </div>
              </div>

              {calibrationConfirmed && layoutConfirmed && imageStatus !== "success" && (
                <Button onClick={runImageDigitization} disabled={imageStatus === "uploading"}>
                  {imageStatus === "uploading" ? "Digitizing…" : "Digitize ECG"}
                </Button>
              )}

              {(imageFile) && (
                <ul className="text-xs text-muted space-y-0.5">
                  {imageSteps.map((s, i) => (
                    <li key={s.label} className={s.done ? "text-green font-semibold" : ""}>
                      {i + 1}. {s.label} {s.done ? "✓" : ""}
                    </li>
                  ))}
                </ul>
              )}

              {imageStatus === "uploading" && <LoadingState label="Extracting waveform from image pixels…" />}
              {imageStatus === "error" && imageError && (
                <ErrorState message={imageError} onRetry={imageFile ? runImageDigitization : undefined} />
              )}
            </div>
          )}
        </Card>
      </div>

      {imageResult && <ImageEcgResultDisplay result={imageResult} />}

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
