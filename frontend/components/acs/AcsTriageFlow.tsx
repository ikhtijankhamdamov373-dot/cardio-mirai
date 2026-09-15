"use client";

import { useState, useEffect, useCallback } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Disclaimer } from "@/components/ui/Disclaimer";
import { LoadingState, ErrorState } from "@/components/ui/PageStatus";
import { PlatformArchitecture } from "@/components/acs/PlatformArchitecture";
import { RuralWorkflowVisual } from "@/components/acs/RuralWorkflowVisual";
import { ResearchPatternsSection } from "@/components/acs/ResearchPatternsSection";
import { PatientForm, PatientFormState, emptyPatientForm } from "@/components/acs/PatientForm";
import { EcgInputStep, EcgInputState, emptyEcgInput } from "@/components/acs/EcgInputStep";
import { QualityGate } from "@/components/acs/QualityGate";
import { ResultDisplay } from "@/components/acs/ResultDisplay";
import { assessStemi, DEMO_CASE, StemiAssessResult } from "@/lib/acsApi";

type Step = "patient" | "ecg" | "result";

export function AcsTriageFlow({ autoDemo = false }: { autoDemo?: boolean }) {
  const [step, setStep] = useState<Step>("patient");
  const [patient, setPatient] = useState<PatientFormState>(emptyPatientForm);
  const [ecgInput, setEcgInput] = useState<EcgInputState>(emptyEcgInput);
  const [isDemo, setIsDemo] = useState(autoDemo);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StemiAssessResult | null>(null);

  const loadDemoCase = useCallback(() => {
    setIsDemo(true);
    setPatient({
      ...emptyPatientForm,
      age: DEMO_CASE.patient.age,
      sex: DEMO_CASE.patient.sex,
      symptomatic: DEMO_CASE.patient.symptomatic,
      high_clinical_suspicion: DEMO_CASE.patient.high_clinical_suspicion,
      ongoing_chest_pain: DEMO_CASE.patient.ongoing_chest_pain,
      main_symptom: DEMO_CASE.patient.main_symptom,
      onset_minutes_ago: DEMO_CASE.patient.onset_minutes_ago,
      sbp: DEMO_CASE.patient.sbp,
      dbp: DEMO_CASE.patient.dbp,
      heart_rate: DEMO_CASE.patient.heart_rate,
      spo2: DEMO_CASE.patient.spo2,
      diabetes: DEMO_CASE.patient.diabetes,
    });
    setEcgInput({ leads: DEMO_CASE.leads, quality: DEMO_CASE.quality });
    setStep("ecg");
  }, []);

  // Presentation route (/acs/demo passes autoDemo=true) auto-loads the
  // synthetic case on mount so the presenter never has to type clinical
  // values live — they only click "Analyze" once landed on Step 2.
  useEffect(() => {
    if (autoDemo) {
      loadDemoCase();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoDemo]);

  const restartDemo = () => {
    setStep("patient");
    setPatient(emptyPatientForm);
    setEcgInput(emptyEcgInput);
    setIsDemo(false);
    setResult(null);
    setError(null);
  };

  const analyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await assessStemi({
        leads: ecgInput.leads,
        patient: {
          age: patient.age,
          sex: patient.sex,
          symptomatic: patient.symptomatic,
          high_clinical_suspicion: patient.high_clinical_suspicion,
          ongoing_chest_pain: patient.ongoing_chest_pain,
        },
        quality: ecgInput.quality,
      });
      setResult(res);
      setStep("result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <header className="text-center">
        <h1 className="text-3xl font-black text-navy">Cardio MIRAI ACS</h1>
        <p className="mt-1 text-muted">AI-assisted prehospital ACS triage</p>
        <div className="mt-3">
          <Badge tone="red">RESEARCH PROTOTYPE — NOT FOR CLINICAL USE</Badge>
        </div>
        <p className="mt-3 text-sm text-muted max-w-xl mx-auto">
          Designed to support rapid ECG assessment at first medical contact,
          particularly in settings where immediate cardiology expertise may
          not be available.
        </p>
      </header>

      {isDemo && (
        <div className="mt-6 rounded-card border-2 border-amber bg-amber/10 px-4 py-3 text-center">
          <p className="text-base font-black text-amber tracking-wide">
            SYNTHETIC DEMONSTRATION — NOT A REAL PATIENT
          </p>
        </div>
      )}

      <section className="mt-8">
        <PlatformArchitecture />
      </section>

      <div className="mt-6 flex justify-center">
        <Button variant="secondary" onClick={loadDemoCase}>
          DEMO CASE — Load synthetic demonstration patient
        </Button>
      </div>

      <section className="mt-8 space-y-6">
        {step === "patient" && (
          <Card>
            <p className="font-bold text-navy mb-4">Step 1 — Patient Information</p>
            <PatientForm value={patient} onChange={setPatient} />
            <Button className="mt-6" onClick={() => setStep("ecg")}>
              Continue to ECG Input
            </Button>
          </Card>
        )}

        {step === "ecg" && (
          <>
            <Card>
              <p className="font-bold text-navy mb-4">Step 2 — ECG Input</p>
              <EcgInputStep value={ecgInput} onChange={setEcgInput} />
            </Card>
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" onClick={() => setStep("patient")}>
                Back
              </Button>
              <Button onClick={analyze} disabled={loading}>
                {loading ? "Analyzing…" : "Analyze"}
              </Button>
            </div>
            {loading && <LoadingState label="Running deterministic ECG quality and STEMI-criteria checks…" />}
            {error && <ErrorState message={error} onRetry={analyze} />}
          </>
        )}

        {step === "result" && result && (
          <>
            <QualityGate quality={ecgInput.quality} />
            <ResultDisplay result={result} />
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" onClick={() => setStep("ecg")}>
                Back to ECG Input
              </Button>
              <Button variant="ghost" onClick={restartDemo}>
                Restart Demo
              </Button>
            </div>
          </>
        )}
      </section>

      <section className="mt-10">
        <ResearchPatternsSection />
      </section>

      <section className="mt-10">
        <p className="text-center font-bold text-navy mb-4">Rural Uzbekistan Workflow</p>
        <RuralWorkflowVisual />
      </section>

      <section className="mt-10">
        <Disclaimer />
      </section>
    </div>
  );
}
