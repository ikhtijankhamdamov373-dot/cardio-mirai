"use client";

import { useState } from "react";
import {
  DemonstrationFallbackCard,
  TriageCard,
  RoutingCard,
  RoleRoadmapCard,
  type TriageLevel,
} from "./LifelineComponents";

export function DigitalLifelineFlow() {
  const [level, setLevel] = useState<TriageLevel | null>(null);

  return (
    <section className="space-y-6">
      {/* HERO */}
      <div className="rounded-2xl border bg-white p-6 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
          Cardio MIRAI Digital Lifeline
        </p>

        <h1 className="mt-2 text-3xl font-extrabold text-slate-950">
          ECG photo → AI triage → clinical pathway → destination
        </h1>

        <p className="mt-3 max-w-3xl text-slate-600">
          Designed for first medical contact in rural clinics and non-PCI
          facilities. A nurse, feldsher, or doctor uploads a 12-lead ECG photo
          together with essential clinical information.
        </p>
      </div>

      {/* ECG / DEMO INPUT */}
      <DemonstrationFallbackCard onSelect={setLevel} />

      {level && (
        <>
          {/* SAFETY LABEL */}
          <div className="rounded-xl border-2 border-amber-500 bg-amber-50 p-4 text-center font-extrabold text-amber-800">
            SYNTHETIC DEMONSTRATION PATHWAY — NOT DERIVED FROM THE UPLOADED ECG
          </div>

          {/* AI RESULT */}
          <TriageCard level={level} />

          {/* LOCATION */}
          <div className="rounded-2xl border bg-white p-6 shadow-sm">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
              Step 2 · Current location
            </p>

            <h2 className="mt-1 text-xl font-extrabold text-slate-950">
              Rural clinic / non-PCI facility
            </h2>

            <p className="mt-2 text-sm text-slate-600">
              Cardio MIRAI converts the ECG screening result into a
              role-specific clinical workflow and destination pathway.
            </p>
          </div>

          {/* PCI / THROMBOLYSIS / LOCAL ROUTING */}
          <RoutingCard level={level} />

          {/* NURSE + DOCTOR */}
          <div className="grid gap-4 lg:grid-cols-2">
            <RoleRoadmapCard role="nurse" level={level} />
            <RoleRoadmapCard role="doctor" level={level} />
          </div>

          {/* SAFETY */}
          <div className="rounded-xl border bg-slate-50 p-4 text-sm text-slate-600">
            <strong>Research prototype.</strong> Cardio MIRAI supports — and
            does not replace — clinician assessment, review of the original
            ECG, local ACS protocols, emergency medical services, and
            specialist consultation. Do not delay emergency care while
            waiting for AI.
          </div>
        </>
      )}
    </section>
  );
}