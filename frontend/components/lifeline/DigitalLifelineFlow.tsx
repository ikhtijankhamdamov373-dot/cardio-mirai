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
  RoleRoadmapCard,
  TimelinePanel,
  RoadmapSection,
  OfflineRuralSection,
  PresentationDemoMenu,
} from "@/components/lifeline/LifelineComponents";

import {
  runRealTriage,
  SYNTHETIC_DEMO_OUTCOMES,
  TriageOutcome,
} from "@/lib/lifelineApi";

type Stage = "upload" | "analyzing" | "result";

export function DigitalLifelineFlow() {
  const [stage, setStage] = useState<Stage>("upload");

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const [outcome, setOutcome] = useState<TriageOutcome | null>(null);

  const [clinical, setClinical] =
    useState<ClinicalContext>(emptyClinicalContext);

  const [confirmedState, setConfirmedState] = useState<
    "none" | "confirmed" | "overridden"
  >("none");

  const [ecgAcquiredAt, setEcgAcquiredAt] =
    useState<number | null>(null);

  const [aiScreeningAt, setAiScreeningAt] =
    useState<number | null>(null);

  const [isSyntheticDemo, setIsSyntheticDemo] =
    useState(false);

  const handleUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;

    const file = fileList[0];

    setIsSyntheticDemo(false);

    setPreviewUrl(
      file.type.startsWith("image/")
        ? URL.createObjectURL(file)
        : null
    );

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

  const handleDemo = (
    level: "RED" | "YELLOW" | "GREEN"
  ) => {
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
    setEcgAcquiredAt(null);
    setAiScreeningAt(null);
  };

  return (
    <div className="mx-auto max-w-4xl px-5 py-8">

      {/* HEADER */}

      <header className="text-center">
        <h1 className="text-3xl font-black text-navy">
          Cardio MIRAI
        </h1>

        <p className="text-lg font-bold text-blue">
          Digital Lifeline
        </p>

        <p className="mt-1 text-muted">
          AI-Assisted Emergency ECG Triage
        </p>

        <p className="mt-2 text-sm text-muted italic">
          &ldquo;From rural first medical contact to
          reperfusion decision support.&rdquo;
        </p>

        <div className="mt-3">
          <Badge tone="red">
            Research Prototype
          </Badge>
        </div>
      </header>

      {/* ===================================================== */}
      {/* STEP 1 — ECG UPLOAD */}
      {/* ===================================================== */}

      {stage === "upload" && (
        <section className="mt-8">

          <Card>
            <p className="text-center text-xs font-bold uppercase text-muted">
              Step 1
            </p>

            <h2 className="mt-1 text-center text-xl font-black text-navy">
              Take / Upload 12-Lead ECG Photo
            </h2>

            <p className="mx-auto mt-2 max-w-2xl text-center text-sm text-muted">
              A nurse, feldsher, or doctor at a rural clinic
              photographs the patient&apos;s ECG and uploads it
              to Cardio MIRAI for AI-assisted emergency screening.
            </p>

            <label className="mt-5 block">
              <div className="cursor-pointer rounded-card border-2 border-dashed border-blue bg-blue-soft px-6 py-10 text-center">

                <p className="text-xl font-black text-blue">
                  TAKE / UPLOAD ECG PHOTO
                </p>

                <p className="mt-2 text-sm font-semibold text-navy">
                  Camera or existing ECG image
                </p>

                <p className="mt-1 text-xs text-muted">
                  JPG, PNG, or PDF
                </p>

              </div>

              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf"
                capture="environment"
                onChange={(e) =>
                  handleUpload(e.target.files)
                }
                className="hidden"
              />
            </label>
          </Card>

          <div className="mt-3 text-center">
            <label className="cursor-pointer text-sm font-semibold text-muted underline">
              Upload ECG File

              <input
                type="file"
                accept=".jpg,.jpeg,.png,.pdf"
                onChange={(e) =>
                  handleUpload(e.target.files)
                }
                className="hidden"
              />
            </label>
          </div>

          {/* CLINICAL CONTEXT */}

          <div className="mt-8">
            <ClinicalContextPanel
              value={clinical}
              onChange={setClinical}
            />
          </div>

        </section>
      )}

      {/* ===================================================== */}
      {/* ANALYZING */}
      {/* ===================================================== */}

      {stage === "analyzing" && (
        <section className="mt-10">

          <p className="mb-4 text-center text-xs font-bold uppercase text-muted">
            Cardio MIRAI ECG Analysis
          </p>

          {previewUrl && (
            <img
              src={previewUrl}
              alt="Uploaded ECG"
              className="mx-auto max-h-56 rounded-card border border-line object-contain"
            />
          )}

          <div className="mt-6">
            <LoadingState label="Cardio MIRAI AI Screening..." />
          </div>

          <p className="mt-4 text-center text-sm text-muted">
            Checking ECG quality and emergency cardiovascular
            patterns...
          </p>

        </section>
      )}

      {/* ===================================================== */}
      {/* RESULT */}
      {/* ===================================================== */}

      {stage === "result" && outcome && (
        <section className="mt-6 space-y-5">

          {/* ECG PREVIEW */}

          {previewUrl && (
            <Card>
              <p className="text-xs font-bold uppercase text-muted">
                Uploaded ECG
              </p>

              <img
                src={previewUrl}
                alt="Uploaded ECG"
                className="mt-2 max-h-48 w-full rounded-card border border-line object-contain"
              />
            </Card>
          )}

          {/* SYNTHETIC SAFETY LABEL */}

          {isSyntheticDemo && (
            <div className="rounded-card border-2 border-amber bg-amber/10 px-4 py-3 text-center">

              <p className="font-black text-amber">
                SYNTHETIC DEMONSTRATION PATHWAY
              </p>

              <p className="mt-1 text-xs font-bold text-amber">
                NOT DERIVED FROM THE UPLOADED ECG
              </p>

            </div>
          )}

          {/* ================================================= */}
          {/* REAL RESULT OR SYNTHETIC DEMO */}
          {/* ================================================= */}

          {outcome.isRealResult || isSyntheticDemo ? (
            <>

              {/* AI TRIAGE */}

              <TriageCard
                outcome={outcome}
                onConfirm={() =>
                  setConfirmedState("confirmed")
                }
                onOverride={() =>
                  setConfirmedState("overridden")
                }
                confirmedState={confirmedState}
              />

              {/* ================================================= */}
              {/* CLINICAL ROUTING */}
              {/* ================================================= */}

              {outcome.level !== "UNKNOWN" && (
                <>

                  <div className="rounded-card border border-line bg-white px-5 py-4">

                    <p className="text-xs font-bold uppercase text-muted">
                      Current Location
                    </p>

                    <p className="mt-1 text-lg font-black text-navy">
                      Rural clinic / non-PCI facility
                    </p>

                    <p className="mt-1 text-sm text-muted">
                      Cardio MIRAI converts the ECG triage
                      result into an emergency clinical and
                      destination pathway.
                    </p>

                  </div>

                  {/* PCI / FIBRINOLYSIS / LOCAL PATHWAY */}

                  <RoutingCard
                    level={outcome.level}
                  />

                  {/* ROLE-SPECIFIC ROADMAPS */}

                  <div className="grid gap-4 lg:grid-cols-2">

                    <RoleRoadmapCard
                      role="nurse"
                      level={outcome.level}
                    />

                    <RoleRoadmapCard
                      role="doctor"
                      level={outcome.level}
                    />

                  </div>

                </>
              )}

            </>
          ) : (

            /* =============================================== */
            /* REAL IMAGE ANALYSIS FAILED */
            /* =============================================== */

            <DemonstrationFallbackCard
              reason={outcome.failureReason}
              onSelectDemo={handleDemo}
            />

          )}

          {/* ================================================= */}
          {/* CLINICAL INFORMATION */}
          {/* ================================================= */}

          <ClinicalContextPanel
            value={clinical}
            onChange={setClinical}
          />

          {/* EXISTING ROLE INFORMATION */}

          <RolePathwayTabs />

          {/* REPEAT ECG */}

          <RepeatEcgCard
            onUploadRepeat={handleUpload}
          />

          {/* SYSTEM TIMELINE */}

          <TimelinePanel
            timeline={{
              ecgAcquiredAt,
              aiScreeningAt,
            }}
          />

          {/* AF MODULE */}

          <AfModuleCard
            isImageUpload={true}
          />

          {/* FUTURE ROADMAP */}

          <RoadmapSection />

          {/* RURAL / OFFLINE */}

          <OfflineRuralSection />

          {/* START AGAIN */}

          <div className="text-center">

            <Button
              variant="ghost"
              onClick={reset}
            >
              Start over
            </Button>

          </div>

          {/* SAFETY */}

          <div className="rounded-card border border-line bg-bg px-4 py-4 text-center text-xs text-muted">

            <p className="font-bold">
              Research Prototype
            </p>

            <p className="mt-1">
              AI-assisted clinical decision support.
              Not a substitute for clinician diagnosis.
            </p>

            <p>
              Review the original ECG and clinical presentation.
            </p>

            <p className="font-bold">
              Do not delay emergency care waiting for AI.
            </p>

          </div>

        </section>
      )}

      {/* PRESENTATION DEMO SHORTCUT */}

      <PresentationDemoMenu
        onSelect={handleDemo}
      />

    </div>
  );
}