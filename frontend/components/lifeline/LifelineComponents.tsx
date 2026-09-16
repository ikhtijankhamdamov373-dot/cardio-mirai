"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { TriageLevel, TriageOutcome } from "@/lib/lifelineApi";

const TRIAGE_META: Record<
  Exclude<TriageLevel, "UNKNOWN">,
  { label: string; tone: "red" | "amber" | "blue"; bg: string; actions: string[]; note: string }
> = {
  RED: {
    label: "Possible STEMI / Acute Coronary Occlusion Pattern",
    tone: "red",
    bg: "border-red/40 bg-red-soft/40 ring-2 ring-red/20",
    actions: [
      "Assess ABC and vital signs",
      "Immediate physician review",
      "Review original 12-lead ECG",
      "Activate locally approved STEMI/ACS pathway if confirmed",
      "Contact PCI-capable center and arrange emergency transfer",
      "If timely primary PCI is not achievable, clinician assesses fibrinolysis eligibility when STEMI is confirmed and there are no contraindications",
      "Do not delay emergency care waiting for AI confirmation",
    ],
    note: "EMERGENCY — immediate clinician review and reperfusion pathway assessment",
  },
  YELLOW: {
    label: "Possible Ischemic / High-Risk ECG Abnormality",
    tone: "amber",
    bg: "border-amber/40 bg-amber/10",
    actions: [
      "Urgent physician review",
      "Clinical ACS assessment",
      "hs-cTn where available and appropriate",
      "Repeat/serial ECG when clinically indicated",
      "Risk-stratify and obtain specialist/PCI-center consultation or transfer when indicated",
    ],
    note: "NSTEMI cannot be diagnosed or excluded from ECG alone. Generic YELLOW triage is not an indication for fibrinolysis.",
  },
  GREEN: {
    label: "No Emergency ECG Pattern Identified",
    tone: "blue",
    bg: "border-green/40 bg-green/5",
    actions: [
      "Continue clinical assessment",
      "Review symptoms, vital signs, and cardiovascular risk",
      "If ACS remains suspected: repeat ECG, biomarkers, and physician review as appropriate",
      "Local management may continue when the clinician determines emergency transfer is not required",
    ],
    note: "GREEN DOES NOT MEAN ACS IS EXCLUDED.",
  },
};

export function TriageCard({
  outcome,
  onConfirm,
  onOverride,
  confirmedState,
}: {
  outcome: TriageOutcome;
  onConfirm: () => void;
  onOverride: () => void;
  confirmedState: "none" | "confirmed" | "overridden";
}) {
  if (outcome.level === "UNKNOWN") return null;
  const meta = TRIAGE_META[outcome.level];

  return (
    <Card className={meta.bg}>
      <div className="flex items-center justify-between gap-2">
        <Badge tone={outcome.isRealResult ? "blue" : "neutral"}>
          {outcome.isRealResult ? "REAL IMAGE-DERIVED RESULT" : "SYNTHETIC DEMONSTRATION CASE"}
        </Badge>
        <span className="text-4xl font-black" style={{ color: meta.tone === "red" ? "#d62839" : meta.tone === "amber" ? "#c47a00" : "#16834a" }}>
          {outcome.level}
        </span>
      </div>
      <p className="mt-3 text-xl font-black text-navy">{meta.label}</p>
      <p className="mt-1 text-sm font-bold text-ink">{meta.note}</p>

      <div className="mt-4 rounded-card border border-line bg-white/70 p-3">
        <p className="text-xs font-black uppercase text-muted">What happens next?</p>
        <ul className="mt-2 space-y-1.5 text-sm text-ink">
          {meta.actions.map((a) => <li key={a}>• {a}</li>)}
        </ul>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <Button variant={confirmedState === "confirmed" ? "primary" : "secondary"} onClick={onConfirm}>CONFIRM TRIAGE</Button>
        <Button variant={confirmedState === "overridden" ? "primary" : "secondary"} onClick={onOverride}>OVERRIDE TRIAGE</Button>
      </div>
      {confirmedState !== "none" && (
        <p className="mt-2 text-xs text-muted">
          {confirmedState === "confirmed" ? "Triage confirmed by clinician." : "Triage overridden by clinician. Final clinical decision remains with the physician."}
        </p>
      )}
    </Card>
  );
}

export function DemonstrationFallbackCard({
  reason,
  onSelectDemo,
}: {
  reason?: string;
  onSelectDemo: (level: "RED" | "YELLOW" | "GREEN") => void;
}) {
  return (
    <Card className="border-amber/40 bg-amber/10">
      <Badge tone="amber">IMAGE ANALYSIS NOT AVAILABLE</Badge>
      <p className="mt-3 font-bold text-navy">This uploaded ECG could not be reliably classified by the current image-analysis prototype.</p>
      <p className="mt-2 text-sm text-ink">
        {reason ? `${reason} ` : ""}No patient-specific RED, YELLOW, or GREEN result has been generated.
      </p>

      <div className="mt-4 rounded-card border border-amber/40 bg-white p-3 text-center">
        <p className="font-black text-amber">PRESENTATION DEMONSTRATION</p>
        <p className="mt-1 text-xs text-muted">Choose a synthetic case to demonstrate the corresponding pathway. It is not derived from the uploaded ECG.</p>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {(["RED", "YELLOW", "GREEN"] as const).map((level) => (
          <button key={level} type="button" onClick={() => onSelectDemo(level)} className="rounded-card border-2 border-line bg-white p-4 text-center transition hover:shadow-panel">
            <p className="text-2xl font-black" style={{ color: level === "RED" ? "#d62839" : level === "YELLOW" ? "#c47a00" : "#16834a" }}>{level}</p>
            <p className="mt-2 text-xs font-semibold text-ink">{TRIAGE_META[level].label}</p>
            <p className="mt-3 text-xs font-black text-blue">SHOW {level} PATHWAY →</p>
          </button>
        ))}
      </div>

      <p className="mt-4 text-center text-xs font-bold text-red">SYNTHETIC DEMONSTRATION ONLY — NOT DERIVED FROM UPLOADED ECG</p>
    </Card>
  );
}

export function AfModuleCard({ isImageUpload }: { isImageUpload: boolean }) {
  return (
    <Card>
      <p className="font-bold text-navy">Rhythm &amp; Atrial Fibrillation</p>
      {isImageUpload ? (
        <>
          <Badge tone="amber">AF analysis from ECG image — Research integration in progress</Badge>
          <p className="mt-2 text-sm text-muted">Existing capability: Digital ECG AF analysis available in Cardio MIRAI ECG Core.</p>
        </>
      ) : (
        <p className="mt-2 text-sm text-muted">Rhythm screening available for digital ECG uploads.</p>
      )}
      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        <div className="rounded-card border border-line p-2">
          <p className="text-xs font-bold text-muted uppercase">Current AF Evidence</p>
          <Badge tone="neutral">Legacy atrial-abnormality research score — exploratory</Badge>
        </div>
        <div className="rounded-card border border-line p-2">
          <p className="text-xs font-bold text-muted uppercase">Future AF Risk</p>
          <Badge tone="neutral">Under Development</Badge>
        </div>
      </div>
    </Card>
  );
}

export interface ClinicalContext {
  chestPain: boolean | null;
  onsetTime: string;
  sbp: string;
  heartRate: string;
  spo2: string;
  knownCad: "yes" | "no" | "unknown";
}

export const emptyClinicalContext: ClinicalContext = {
  chestPain: null, onsetTime: "", sbp: "", heartRate: "", spo2: "", knownCad: "unknown",
};

export function ClinicalContextPanel({ value, onChange }: { value: ClinicalContext; onChange: (v: ClinicalContext) => void }) {
  const set = <K extends keyof ClinicalContext>(k: K, v: ClinicalContext[K]) => onChange({ ...value, [k]: v });
  return (
    <Card>
      <p className="font-bold text-navy">Clinical Context</p>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div>
          <p className="text-xs font-semibold text-ink">Chest pain</p>
          <div className="mt-1 flex gap-2">
            <Button variant={value.chestPain === true ? "primary" : "secondary"} onClick={() => set("chestPain", true)}>YES</Button>
            <Button variant={value.chestPain === false ? "primary" : "secondary"} onClick={() => set("chestPain", false)}>NO</Button>
          </div>
        </div>
        <label className="text-xs font-semibold text-ink">Symptom onset
          <input type="text" placeholder="e.g. 45 min ago" className="mt-1 w-full rounded-card border border-line px-2 py-2 text-sm" value={value.onsetTime} onChange={(e) => set("onsetTime", e.target.value)} />
        </label>
        <label className="text-xs font-semibold text-ink">SBP
          <input type="number" className="mt-1 w-full rounded-card border border-line px-2 py-2 text-sm" value={value.sbp} onChange={(e) => set("sbp", e.target.value)} />
        </label>
        <label className="text-xs font-semibold text-ink">Heart rate
          <input type="number" className="mt-1 w-full rounded-card border border-line px-2 py-2 text-sm" value={value.heartRate} onChange={(e) => set("heartRate", e.target.value)} />
        </label>
        <label className="text-xs font-semibold text-ink">SpO2
          <input type="number" className="mt-1 w-full rounded-card border border-line px-2 py-2 text-sm" value={value.spo2} onChange={(e) => set("spo2", e.target.value)} />
        </label>
        <div>
          <p className="text-xs font-semibold text-ink">Known CAD</p>
          <div className="mt-1 flex gap-1">
            {(["yes", "no", "unknown"] as const).map((v) => (
              <Button key={v} variant={value.knownCad === v ? "primary" : "secondary"} onClick={() => set("knownCad", v)}>{v.toUpperCase()}</Button>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

const NURSE_STEPS = [
  "Acquire/upload 12-lead ECG",
  "Record symptoms and vital signs",
  "Review Cardio MIRAI triage",
  "RED → notify doctor immediately",
  "Follow locally approved emergency/transfer pathway",
  "Do not delay emergency treatment while waiting for AI",
];

const DOCTOR_STEPS = [
  "Review original ECG",
  "Review symptoms and vital signs",
  "Confirm/override AI triage",
  "Assess ACS clinically",
  "Obtain/review hs-cTn where appropriate",
  "Repeat ECG when clinically indicated",
  "If STEMI/acute coronary occlusion suspected: activate locally approved reperfusion/PCI pathway",
  "Arrange consultation/transfer as appropriate",
];

export function RolePathwayTabs() {
  const [tab, setTab] = useState<"nurse" | "doctor">("nurse");
  const steps = tab === "nurse" ? NURSE_STEPS : DOCTOR_STEPS;
  return (
    <Card>
      <div className="flex gap-2">
        <Button variant={tab === "nurse" ? "primary" : "secondary"} onClick={() => setTab("nurse")}>NURSE / FELDSHER</Button>
        <Button variant={tab === "doctor" ? "primary" : "secondary"} onClick={() => setTab("doctor")}>DOCTOR</Button>
      </div>
      <ol className="mt-4 space-y-1.5 text-sm text-ink list-decimal list-inside">
        {steps.map((s) => <li key={s}>{s}</li>)}
      </ol>
      {tab === "nurse" && <p className="mt-3 text-xs font-bold text-red">No autonomous prescribing.</p>}
    </Card>
  );
}

export function RepeatEcgCard({ onUploadRepeat }: { onUploadRepeat: (files: FileList | null) => void }) {
  return (
    <Card>
      <p className="font-bold text-navy">Repeat ECG</p>
      <p className="mt-1 text-sm text-muted">If the initial ECG is non-diagnostic but symptoms persist, repeat ECG according to clinical assessment.</p>
      <input type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => onUploadRepeat(e.target.files)} className="mt-3 w-full text-sm" />
    </Card>
  );
}

export function RoutingCard({ level }: { level: Exclude<TriageLevel, "UNKNOWN"> }) {
  const pathways = {
    RED: {
      title: "RED — Emergency Reperfusion / Transfer Pathway",
      boxes: ["First medical contact", "Immediate physician review", "STEMI / acute occlusion suspected", "Activate emergency ACS / reperfusion pathway", "PCI-capable center"],
      routing: "PCI-CAPABLE CENTER — EMERGENCY PRIORITY",
      detail: "Primary PCI is preferred when timely achievable. If timely PCI is not achievable, an eligible confirmed STEMI patient requires clinician assessment for fibrinolysis and contraindications, followed by transfer to a PCI-capable center.",
    },
    YELLOW: {
      title: "YELLOW — Urgent ACS Assessment Pathway",
      boxes: ["First medical contact", "Urgent doctor review", "Clinical ACS assessment", "hs-cTn + serial ECG as appropriate", "Risk stratification / specialist consultation"],
      routing: "SPECIALIST / PCI-CENTER CONSULTATION AS INDICATED",
      detail: "If high-risk ACS is suspected or confirmed, escalate to specialist/PCI-center consultation or transfer according to clinical status. NSTEMI cannot be diagnosed from ECG alone.",
    },
    GREEN: {
      title: "GREEN — Local Clinical Assessment Pathway",
      boxes: ["First medical contact", "Clinical assessment", "Symptoms + vitals + risk factors", "Further testing if ACS remains suspected", "Local management if emergency transfer is not required"],
      routing: "LOCAL MANAGEMENT MAY CONTINUE — SUBJECT TO CLINICIAN ASSESSMENT",
      detail: "GREEN does not exclude ACS. If clinical suspicion persists, repeat ECG, biomarkers and physician review are appropriate before deciding on local management or escalation.",
    },
  };
  const data = pathways[level];

  return (
    <Card>
      <p className="text-lg font-black text-navy">{data.title}</p>
      <div className="mt-4 flex flex-col items-center gap-1 text-sm">
        {data.boxes.map((s, i) => (
          <div key={s} className="flex w-full flex-col items-center">
            <div className="w-full rounded-card border border-line bg-bg px-3 py-2 text-center font-semibold text-ink">{s}</div>
            {i < data.boxes.length - 1 && <span className="py-1 text-xl text-muted">↓</span>}
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-card border border-line bg-white p-3">
        <p className="text-xs font-black uppercase text-muted">Routing decision</p>
        <p className="mt-1 text-sm font-black text-navy">{data.routing}</p>
        <p className="mt-2 text-xs text-muted">{data.detail}</p>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
        <div><p className="text-muted">Nearest PCI center</p><p className="font-semibold text-ink">Integration planned</p></div>
        <div><p className="text-muted">Estimated transport time</p><p className="font-semibold text-ink">GPS integration planned</p></div>
        <div><p className="text-muted">Contact center</p><p className="font-semibold text-ink">Integration planned</p></div>
      </div>
      <div className="mt-3"><Badge tone="neutral">GPS / emergency referral integration — planned</Badge></div>
    </Card>
  );
}

export interface Timeline {
  ecgAcquiredAt: number | null;
  aiScreeningAt: number | null;
}

export function TimelinePanel({ timeline }: { timeline: Timeline }) {
  const fmt = (ts: number | null, base: number | null) => {
    if (ts == null) return "Pending";
    if (base == null) return "00:00";
    const deltaSec = Math.max(0, Math.round((ts - base) / 1000));
    return `+${String(Math.floor(deltaSec / 60)).padStart(2, "0")}:${String(deltaSec % 60).padStart(2, "0")}`;
  };
  return (
    <Card>
      <p className="font-bold text-navy">System Timeline</p>
      <ul className="mt-2 text-sm text-ink space-y-1">
        <li>ECG acquired — {timeline.ecgAcquiredAt ? "00:00" : "Pending"}</li>
        <li>AI screening — {fmt(timeline.aiScreeningAt, timeline.ecgAcquiredAt)}</li>
        <li>Doctor review — Pending</li>
        <li>Transfer decision — Pending</li>
        <li>PCI/reperfusion — External clinical system</li>
      </ul>
    </Card>
  );
}

export function RoadmapSection() {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <Card>
        <p className="font-bold text-navy text-sm">AVAILABLE / PROTOTYPE</p>
        <ul className="mt-2 text-sm text-muted space-y-1 list-disc list-inside">
          <li>Emergency ECG workflow</li>
          <li>ECG photo upload</li>
          <li>Current AF / rhythm engine for supported digital ECG</li>
          <li>ACS triage framework</li>
          <li>Clinician decision-support pathway</li>
        </ul>
      </Card>
      <Card>
        <p className="font-bold text-navy text-sm">IN DEVELOPMENT</p>
        <ul className="mt-2 text-sm text-muted space-y-1 list-disc list-inside">
          <li>Validated ECG photo digitization</li>
          <li>Automated ST measurement</li>
          <li>Future AF prediction</li>
          <li>Multimodal ECG + Echo + clinical AI</li>
          <li>GPS/PCI-center routing</li>
          <li>Offline rural deployment</li>
          <li>Prospective Uzbekistan validation</li>
        </ul>
      </Card>
    </div>
  );
}

export function OfflineRuralSection() {
  return (
    <Card>
      <p className="font-bold text-navy text-sm">Designed for Resource-Limited Settings</p>
      <ul className="mt-2 text-sm text-muted space-y-1 list-disc list-inside">
        <li>Smartphone ECG photo acquisition</li>
        <li>Low-bandwidth workflow</li>
        <li>Uzbek / Russian / English</li>
        <li>Offline-capable workflow — planned/prototype</li>
        <li>Integration with emergency referral networks — roadmap</li>
      </ul>
    </Card>
  );
}

export function PresentationDemoMenu({ onSelect }: { onSelect: (level: "RED" | "YELLOW" | "GREEN") => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="fixed bottom-4 right-4 z-30">
      <button onClick={() => setOpen((v) => !v)} className="rounded-full bg-navy px-3 py-2 text-xs font-bold text-white shadow-panel">
        Presentation Demo
      </button>
      {open && (
        <div className="mt-2 rounded-card border border-line bg-white p-2 shadow-panel">
          {(["RED", "YELLOW", "GREEN"] as const).map((level) => (
            <button key={level} onClick={() => { onSelect(level); setOpen(false); }} className="block w-full rounded-card px-3 py-2 text-left text-sm font-semibold hover:bg-bg">
              Demo: {level} case
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
export function RoleRoadmapCard({
  role,
  level,
}: {
  role: "nurse" | "doctor";
  level: Exclude<TriageLevel, "UNKNOWN">;
}) {
  const nurseSteps =
    level === "RED"
      ? [
          "Acquire/upload the 12-lead ECG and record symptoms and vital signs.",
          "Recognize the RED alert and immediately notify the responsible physician.",
          "Prepare emergency monitoring, equipment and transport according to local protocol and scope of practice.",
          "Prepare the original ECG and essential clinical information for the receiving team.",
          "Do not independently decide on fibrinolysis unless specifically authorized under an approved protocol and scope of practice.",
          "Do not delay emergency transport or treatment while waiting for AI.",
        ]
      : level === "YELLOW"
        ? [
            "Record symptoms and vital signs and notify the responsible clinician.",
            "Prepare repeat ECG and blood sampling / hs-cTn when ordered and available.",
            "Observe for deterioration and escalate immediately if the patient becomes unstable.",
            "Prepare specialist consultation or transfer when directed by the clinician.",
          ]
        : [
            "Record symptoms and vital signs and provide the original ECG for clinician review.",
            "Continue observation and repeat ECG/testing when directed.",
            "Escalate immediately for worsening symptoms, instability, or new concerning findings.",
            "Do not interpret GREEN as clearance or exclusion of ACS.",
          ];

  const doctorSteps =
    level === "RED"
      ? [
          "Immediately assess the patient and review the original 12-lead ECG; confirm or override the AI triage.",
          "Assess symptoms, onset time, hemodynamic status, and important differential diagnoses.",
          "If STEMI / acute coronary occlusion is confirmed or strongly suspected, activate the locally approved reperfusion pathway.",
          "Determine whether timely primary PCI is achievable within the applicable guideline/network target.",
          "If YES: activate/contact the PCI-capable center and arrange emergency transfer.",
          "If NO: assess fibrinolysis indication, symptom timing, and contraindications under the approved protocol.",
          "If fibrinolysis is given, arrange immediate transfer to a PCI-capable center.",
        ]
      : level === "YELLOW"
        ? [
            "Review the original ECG and clinical presentation.",
            "Assess for NSTE-ACS and important alternative diagnoses.",
            "Use hs-cTn, serial ECG, and clinical reassessment when indicated.",
            "Determine the need and urgency of specialist / PCI-center consultation or transfer.",
            "Do not use a generic YELLOW result as an indication for fibrinolysis.",
          ]
        : [
            "Review the original ECG and complete clinical presentation.",
            "Do not exclude ACS solely because the AI screen is GREEN.",
            "Use biomarkers, serial ECG, or additional evaluation when clinical suspicion persists.",
            "Decide whether local management, observation, specialist consultation, or transfer is appropriate.",
          ];

  const steps = role === "nurse" ? nurseSteps : doctorSteps;

  return (
    <Card>
      <p className="text-xs font-black uppercase text-muted">
        Step 4 · Role-Specific Roadmap
      </p>

      <p className="mt-2 text-lg font-black text-navy">
        {role === "nurse"
          ? "Nurse / Feldsher Roadmap"
          : "Doctor Roadmap"}
      </p>

      <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-ink">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>

      {role === "nurse" && (
        <div className="mt-4 rounded-card border border-red/30 bg-red-soft/30 p-3">
          <p className="text-xs font-bold text-red">
            No autonomous prescribing. Medication and reperfusion decisions
            remain subject to clinician authority, scope of practice, and
            locally approved protocols.
          </p>
        </div>
      )}

      {role === "doctor" && level === "RED" && (
        <div className="mt-4 rounded-card border border-line bg-bg p-3">
          <p className="text-xs font-bold text-navy">
            Final reperfusion and destination decisions remain with the
            treating physician and the applicable regional STEMI network.
          </p>
        </div>
      )}
    </Card>
  );
}