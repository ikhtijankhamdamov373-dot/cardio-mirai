"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { LoadingState } from "@/components/ui/PageStatus";
import {
  TriageCard,
  DemonstrationFallbackCard,
  AfModuleCard,
  ClinicalContextPanel,
  ClinicalContext,
  emptyClinicalContext,
  RolePathwayTabs,
  RepeatEcgCard,
  RoutingCard,
  TimelinePanel,
  RoadmapSection,
  OfflineRuralSection,
  PresentationDemoMenu,
} from "@/components/lifeline/LifelineComponents";
import { runRealTriage, SYNTHETIC_DEMO_OUTCOMES, TriageOutcome } from "@/lib/lifelineApi";

type Stage = "upload" | "analyzing" | "result";

export function DigitalLifelineFlow() {
  const [stage, setStage] = useState<Stage>("upload");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<TriageOutcome | null>(null);
  const [clinical, setClinical] = useState<ClinicalContext>(emptyClinicalContext);
  const [confirmedState, setConfirmedState] = useState<"none" | "confirmed" | "overridden">("none");
  const [ecgAcquiredAt, setEcgAcquiredAt] = useState<number | null>(null);
  const [aiScreeningAt, setAiScreeningAt] = useState<number | null>(null);
  const [isSyntheticDemo, setIsSyntheticDemo] = useState(false);

  const handleUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    const file = fileList[0];
    setIsSyntheticDemo(false);
    setPreviewUrl(file.type.startsWith("image/") ? URL.createObjectURL(file) : null);
    setStage("analyzing");
    setConfirmedState("none");
    const acquiredAt = Date.now();
    setEcgAcquiredAt(acquiredAt);

    const result = await runRealTriage({
      file,
      symptomatic: clinical.chestPain === true,
      high_clinical_suspicion: clinical.chestPain === true,
      ongoing_chest_pain: clinical.chestPain === true,
    });
    setAiScreeningAt(Date.now());
    setOutcome(result);
    setStage("result");
  };

  const handleDemo = (level: "RED" | "YELLOW" | "GREEN") => {
    setIsSyntheticDemo(true);
    setOutcome(SYNTHETIC_DEMO_OUTCOMES[level]);
    setAiScreeningAt(Date.now());
    setConfirmedState("none");
    setStage("result");
  };

  const reset = () => {
    setStage("upload");
    setOutcome(null);
    setPreviewUrl(null);
    setIsSyntheticDemo(false);
    setConfirmedState("none");
  };

  return (
    <div className="mx-auto max-w-3xl px-5 py-8">
      <header className="text-center">
        <h1 className="text-3xl font-black text-navy">Cardio MIRAI</h1>
        <p className="text-lg font-bold text-blue">Digital Lifeline</p>
        <p className="mt-1 text-muted">AI-Assisted Emergency ECG Triage</p>
        <p className="mt-2 text-sm text-muted italic">
          &ldquo;From first medical contact to specialist decision support.&rdquo;
        </p>
        <div className="mt-3">
          <Badge tone="red">Research Prototype</Badge>
        </div>
      </header>

      {stage === "upload" && (
        <section className="mt-8">
          <Card>
            <p className="text-center font-bold text-navy mb-3">Take / Upload ECG Photo</p>
            <label className="block">
              <div className="rounded-card border-2 border-dashed border-blue bg-blue-soft px-6 py-10 text-center cursor-pointer">
                <p className="text-xl font-black text-blue">TAKE / UPLOAD ECG PHOTO</p>
                <p className="mt-1 text-xs text-muted">JPG, PNG, or PDF</p>
              </div>
              <input type="file" accept=".jpg,.jpeg,.png,.pdf" capture="environment" onChange={(e) => handleUpload(e.target.files)} className="hidden" />
            </label>
          </Card>
          <div className="mt-3 text-center">
            <label className="text-sm font-semibold text-muted underline cursor-pointer">
              Upload ECG File
              <input type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => handleUpload(e.target.files)} className="hidden" />
            </label>
          </div>

          <div className="mt-8">
            <ClinicalContextPanel value={clinical} onChange={setClinical} />
          </div>
        </section>
      )}

      {stage === "analyzing" && (
        <section className="mt-10">
          {previewUrl && (
            <img src={previewUrl} alt="Uploaded ECG" className="mx-auto max-h-56 rounded-card border border-line object-contain" />
          )}
          <div className="mt-6">
            <LoadingState label="Cardio MIRAI AI Screening..." />
          </div>
        </section>
      )}

      {stage === "result" && outcome && (
        <section className="mt-6 space-y-5">
          {previewUrl && (
            <Card>
              <p className="text-xs font-bold text-muted uppercase">ECG Image</p>
              <img src={previewUrl} alt="Uploaded ECG" className="mt-1 max-h-48 w-full rounded-card border border-line object-contain" />
            </Card>
          )}

          {isSyntheticDemo && (
            <div className="rounded-card border-2 border-amber bg-amber/10 px-4 py-3 text-center">
              <p className="font-black text-amber">SYNTHETIC DEMONSTRATION PATHWAY — NOT DERIVED FROM UPLOADED ECG</p>
            </div>
          )}

          {outcome.isRealResult || isSyntheticDemo ? (
            <>
              <TriageCard
                outcome={outcome}
                onConfirm={() => setConfirmedState("confirmed")}
                onOverride={() => setConfirmedState("overridden")}
                confirmedState={confirmedState}
              />
              {outcome.level !== "UNKNOWN" && <RoutingCard level={outcome.level} />}
            </>
          ) : (
            <DemonstrationFallbackCard reason={outcome.failureReason} onSelectDemo={handleDemo} />
          )}

          <ClinicalContextPanel value={clinical} onChange={setClinical} />
          <RolePathwayTabs />
          <RepeatEcgCard onUploadRepeat={handleUpload} />
          <TimelinePanel timeline={{ ecgAcquiredAt, aiScreeningAt }} />
          <AfModuleCard isImageUpload={true} />
          <RoadmapSection />
          <OfflineRuralSection />

          <div className="text-center">
            <Button variant="ghost" onClick={reset}>Start over</Button>
          </div>

          <div className="rounded-card border border-line bg-bg px-4 py-4 text-center text-xs text-muted">
            <p className="font-bold">Research Prototype</p>
            <p>AI-assisted clinical decision support. Not a substitute for clinician diagnosis.</p>
            <p>Do not delay emergency care waiting for AI.</p>
          </div>
        </section>
      )}

      <PresentationDemoMenu onSelect={handleDemo} />
    </div>
  );
}
