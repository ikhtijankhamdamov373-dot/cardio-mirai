"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { TriageLevel, TriageOutcome } from "@/lib/lifelineApi";

// ---------------------------------------------------------------------------
// Triage card
// ---------------------------------------------------------------------------

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
      "Contact PCI-capable center",
      "Arrange emergency transfer where indicated",
      "Do not delay emergency care waiting for AI confirmation",
    ],
    note: "URGENT CLINICIAN REVIEW",
  },
  YELLOW: {
    label: "Possible Ischemic / High-Risk ECG Abnormality",
    tone: "amber",
    bg: "border-amber/40 bg-amber/10",
    actions: [
      "Physician review",
      "Clinical ACS assessment",
      "hs-cTn where available/appropriate",
      "Repeat/serial ECG when clinically indicated",
      "Consider specialist consultation/transfer according to clinical status",
    ],
    note: "NSTEMI cannot be diagnosed or excluded from ECG alone.",
  },
  GREEN: {
    label: "No emergency ECG pattern identified by prototype",
    tone: "blue",
    bg: "border-green/40 bg-green/5",
    actions: [
      "Continue clinical assessment",
      "ACS is NOT excluded",
      "Review symptoms/vital signs",
      "Biomarker testing/serial ECG as clinically indicated",
    ],
    note: "ACS is not excluded by this screening result.",
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
        <span className="text-3xl font-black" style={{ color: meta.tone === "red" ? "#d62839" : meta.tone === "amber" ? "#c47a00" : "#16834a" }}>
          {outcome.level}
        </span>
      </div>
      <p className="mt-3 text-xl font-black text-navy">{meta.label}</p>
      <p className="mt-1 text-sm font-bold text-ink">{meta.note}</p>

      <ul className="mt-4 space-y-1.5 text-sm text-ink">
        {meta.actions.map((a) => (
          <li key={a}>• {a}</li>
        ))}
      </ul>

      <div className="mt-5 flex flex-wrap gap-3">
        <Button
          variant={confirmedState === "confirmed" ? "primary" : "secondary"}
          onClick={onConfirm}
        >
          CONFIRM TRIAGE
        </Button>
        <Button
          variant={confirmedState === "overridden" ? "primary" : "secondary"}
          onClick={onOverride}
        >
          OVERRIDE TRIAGE
        </Button>
      </div>
      {confirmedState !== "none" && (
        <p className="mt-2 text-xs text-muted">
          {confirmedState === "confirmed" ? "Triage confirmed by clinician." : "Triage overridden by clinician."}
        </p>
      )}
    </Card>
  );
}

export function DemonstrationFallbackCard({ reason }: { reason?: string }) {
  return (
    <Card className="border-amber/40 bg-amber/10">
      <Badge tone="amber">DEMONSTRATION / RESEARCH PROTOTYPE MODE</Badge>
      <p className="mt-3 text-sm text-ink">
        The experimental image-analysis pipeline could not produce a
        reliable result for this upload{reason ? `: ${reason}` : "."} Rather
        than fabricate a measurement, here is an example of how the
        screening workflow operates once digitization succeeds.
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {(["RED", "YELLOW", "GREEN"] as const).map((level) => (
          <div key={level} className="rounded-card border border-line bg-white p-3 text-center">
            <p className="text-lg font-black" style={{ color: level === "RED" ? "#d62839" : level === "YELLOW" ? "#c47a00" : "#16834a" }}>
              {level}
            </p>
            <p className="mt-1 text-xs text-muted">{TRIAGE_META[level].label}</p>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted italic">
        Example screening workflow — not derived from your uploaded image.
      </p>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// AF module
// ---------------------------------------------------------------------------

export function AfModuleCard({ isImageUpload }: { isImageUpload: boolean }) {
  return (
    <Card>
      <p className="font-bold text-navy">Rhythm &amp; Atrial Fibrillation</p>
      {isImageUpload ? (
        <>
          <Badge tone="amber">AF analysis from ECG image — Research integration in progress</Badge>
          <p className="mt-2 text-sm text-muted">
            Existing capability: Digital ECG AF analysis available in Cardio
            MIRAI ECG Core.
          </p>
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

// ---------------------------------------------------------------------------
// Clinical context (short form)
// ---------------------------------------------------------------------------

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
        <label className="text-xs font-semibold text-ink">
          Symptom onset
          <input type="text" placeholder="e.g. 45 min ago" className="mt-1 w-full rounded-card border border-line px-2 py-2 text-sm" value={value.onsetTime} onChange={(e) => set("onsetTime", e.target.value)} />
        </label>
        <label className="text-xs font-semibold text-ink">
          SBP
          <input type="number" className="mt-1 w-full rounded-card border border-line px-2 py-2 text-sm" value={value.sbp} onChange={(e) => set("sbp", e.target.value)} />
        </label>
        <label className="text-xs font-semibold text-ink">
          Heart rate
          <input type="number" className="mt-1 w-full rounded-card border border-line px-2 py-2 text-sm" value={value.heartRate} onChange={(e) => set("heartRate", e.target.value)} />
        </label>
        <label className="text-xs font-semibold text-ink">
          SpO₂
          <input type="number" className="mt-1 w-full rounded-card border border-line px-2 py-2 text-sm" value={value.spo2} onChange={(e) => set("spo2", e.target.value)} />
        </label>
        <div>
          <p className="text-xs font-semibold text-ink">Known CAD</p>
          <div className="mt-1 flex gap-1">
            {(["yes", "no", "unknown"] as const).map((v) => (
              <Button key={v} variant={value.knownCad === v ? "primary" : "secondary"} onClick={() => set("knownCad", v)}>
                {v.toUpperCase()}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Role-based pathway tabs
// ---------------------------------------------------------------------------

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
        <Button variant={tab === "nurse" ? "primary" : "secondary"} onClick={() => setTab("nurse")}>
          NURSE / FELDSHER
        </Button>
        <Button variant={tab === "doctor" ? "primary" : "secondary"} onClick={() => setTab("doctor")}>
          DOCTOR
        </Button>
      </div>
      <ol className="mt-4 space-y-1.5 text-sm text-ink list-decimal list-inside">
        {steps.map((s) => <li key={s}>{s}</li>)}
      </ol>
      {tab === "nurse" && <p className="mt-3 text-xs font-bold text-red">No autonomous prescribing.</p>}
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Repeat ECG
// ---------------------------------------------------------------------------

export function RepeatEcgCard({ onUploadRepeat }: { onUploadRepeat: (files: FileList | null) => void }) {
  return (
    <Card>
      <p className="font-bold text-navy">Repeat ECG</p>
      <p className="mt-1 text-sm text-muted">
        If initial ECG is non-diagnostic but symptoms persist: repeat ECG
        recommended according to clinical assessment.
      </p>
      <input type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => onUploadRepeat(e.target.files)} className="mt-3 w-full text-sm" />
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Emergency routing
// ---------------------------------------------------------------------------

export function RoutingCard() {
  return (
    <Card>
      <p className="font-bold text-navy">Emergency Routing</p>
      <div className="mt-2 flex flex-col items-center gap-1 text-sm">
        {["Current facility", "Cardio MIRAI triage", "Doctor confirmation", "PCI-capable center / appropriate emergency facility"].map((s, i, arr) => (
          <div key={s} className="flex flex-col items-center">
            <div className="rounded-card border border-line bg-bg px-3 py-1.5 font-semibold text-ink">{s}</div>
            {i < arr.length - 1 && <span className="text-muted">↓</span>}
          </div>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
        <div><p className="text-muted">Nearest PCI center</p><p className="font-semibold text-ink">—</p></div>
        <div><p className="text-muted">Estimated transfer time</p><p className="font-semibold text-ink">—</p></div>
        <div><p className="text-muted">Contact center</p><p className="font-semibold text-ink">—</p></div>
      </div>
      <Badge tone="neutral">GPS routing integration — prototype / planned integration</Badge>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// System timeline
// ---------------------------------------------------------------------------

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
        <li>Transfer activated — Pending</li>
        <li>PCI/reperfusion — External system</li>
      </ul>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Roadmap
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Presentation demo menu
// ---------------------------------------------------------------------------

export function PresentationDemoMenu({ onSelect }: { onSelect: (level: "RED" | "YELLOW" | "GREEN") => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="fixed bottom-4 right-4 z-30">
      <button
        onClick={() => setOpen((v) => !v)}
        className="rounded-full bg-navy px-3 py-2 text-xs font-bold text-white shadow-panel"
      >
        Presentation Demo
      </button>
      {open && (
        <div className="mt-2 rounded-card border border-line bg-white p-2 shadow-panel">
          {(["RED", "YELLOW", "GREEN"] as const).map((level) => (
            <button
              key={level}
              onClick={() => { onSelect(level); setOpen(false); }}
              className="block w-full rounded-card px-3 py-2 text-left text-sm font-semibold hover:bg-bg"
            >
              Demo: {level} case
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
