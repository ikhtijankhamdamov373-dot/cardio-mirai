"use client";

export type TriageLevel = "RED" | "YELLOW" | "GREEN";
type Role = "nurse" | "doctor";

const TRIAGE_META = {
  RED: {
    title: "Possible STEMI / acute coronary occlusion pattern",
    subtitle:
      "EMERGENCY — immediate physician review and reperfusion-pathway assessment",
    box: "border-red-300 bg-red-50",
    text: "text-red-700",
  },
  YELLOW: {
    title: "Possible ischemic / high-risk ECG abnormality",
    subtitle:
      "URGENT — ACS assessment, serial evaluation and clinician-directed routing",
    box: "border-amber-300 bg-amber-50",
    text: "text-amber-700",
  },
  GREEN: {
    title: "No emergency ECG pattern identified",
    subtitle:
      "Continue clinical assessment — a GREEN ECG screen does NOT exclude ACS",
    box: "border-emerald-300 bg-emerald-50",
    text: "text-emerald-700",
  },
} as const;

export function DemonstrationFallbackCard({
  onSelect,
}: {
  onSelect: (level: TriageLevel) => void;
}) {
  return (
    <div className="rounded-2xl border bg-white p-6 shadow-sm">
      <div className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800">
        PRESENTATION / RESEARCH PROTOTYPE
      </div>

      <h2 className="mt-3 text-xl font-extrabold text-slate-950">
        Step 1 · Upload 12-lead ECG photo
      </h2>

      <p className="mt-2 max-w-3xl text-sm text-slate-600">
        Intended workflow: a nurse, feldsher, or doctor at first medical
        contact photographs the 12-lead ECG and uploads it to Cardio MIRAI.
        The production image-analysis pipeline is still under validation.
        For this presentation, select a synthetic AI result to demonstrate
        the downstream clinical pathway.
      </p>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {(["RED", "YELLOW", "GREEN"] as TriageLevel[]).map((level) => {
          const item = TRIAGE_META[level];

          return (
            <button
              key={level}
              type="button"
              onClick={() => onSelect(level)}
              className={`rounded-xl border-2 p-5 text-left transition hover:-translate-y-0.5 hover:shadow-md ${item.box}`}
            >
              <div className={`text-2xl font-black ${item.text}`}>
                {level}
              </div>

              <div className="mt-2 font-bold text-slate-950">
                {item.title}
              </div>

              <div className="mt-3 text-xs font-extrabold uppercase tracking-wide text-slate-600">
                Show {level} pathway →
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function TriageCard({ level }: { level: TriageLevel }) {
  const item = TRIAGE_META[level];

  return (
    <div className={`rounded-2xl border-2 p-6 shadow-sm ${item.box}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-wide text-slate-500">
            Cardio MIRAI AI ECG screening
          </p>

          <h2 className="mt-2 text-2xl font-black text-slate-950">
            {item.title}
          </h2>

          <p className="mt-2 font-bold text-slate-800">
            {item.subtitle}
          </p>
        </div>

        <div className={`text-4xl font-black ${item.text}`}>
          {level}
        </div>
      </div>

      {level === "RED" && (
        <div className="mt-5 rounded-xl border border-red-200 bg-white p-4">
          <div className="font-extrabold text-slate-950">
            Immediate actions
          </div>

          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            <li>Assess ABC and vital signs.</li>
            <li>Immediate physician review of the original 12-lead ECG.</li>
            <li>
              If STEMI / acute coronary occlusion is confirmed or strongly
              suspected, activate the locally approved ACS/STEMI pathway.
            </li>
            <li>Do not delay emergency care while waiting for AI.</li>
          </ul>
        </div>
      )}
    </div>
  );
}

export function RoutingCard({ level }: { level: TriageLevel }) {
  if (level === "RED") {
    return (
      <div className="rounded-2xl border-2 border-red-300 bg-white p-6 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
          Step 3 · Destination & reperfusion pathway
        </p>

        <h2 className="mt-2 text-2xl font-black text-red-700">
          RED → Emergency STEMI pathway
        </h2>

        <div className="mt-5 rounded-xl bg-slate-50 p-5 text-center">
          <div className="font-extrabold text-slate-950">
            Rural clinic / non-PCI facility
          </div>

          <div className="my-2 text-2xl">↓</div>

          <div className="font-extrabold text-red-700">
            Possible STEMI / acute coronary occlusion
          </div>

          <div className="my-2 text-2xl">↓</div>

          <div className="font-extrabold text-slate-950">
            Physician confirms or strongly suspects STEMI
          </div>

          <div className="my-2 text-2xl">↓</div>

          <div className="font-extrabold text-slate-950">
            Can primary PCI be achieved within the applicable
            guideline/network time target?
          </div>
        </div>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl border-2 border-emerald-300 bg-emerald-50 p-5">
            <div className="text-lg font-black text-emerald-800">
              YES → PRIMARY PCI PATHWAY
            </div>

            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-800">
              <li>Activate/contact the PCI-capable center.</li>
              <li>Arrange emergency transport without avoidable delay.</li>
              <li>
                Send the ECG and essential clinical information to the
                receiving team when system integration permits.
              </li>
              <li>
                Transfer through the locally approved primary PCI network.
              </li>
            </ol>

            <div className="mt-4 rounded-lg bg-white p-3 text-center font-extrabold text-emerald-800">
              DESTINATION → PCI-CAPABLE CENTER
            </div>
          </div>

          <div className="rounded-xl border-2 border-red-300 bg-red-50 p-5">
            <div className="text-lg font-black text-red-800">
              NO → ASSESS FIBRINOLYSIS
            </div>

            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-800">
              <li>Confirm STEMI diagnosis and symptom timing.</li>
              <li>
                Physician assesses fibrinolysis eligibility and
                contraindications using the approved local protocol.
              </li>
              <li>
                If clinically indicated, administer fibrinolysis according
                to the approved protocol.
              </li>
              <li>
                Arrange immediate transfer to a PCI-capable center after
                fibrinolysis.
              </li>
            </ol>

            <div className="mt-4 rounded-lg bg-white p-3 text-center font-extrabold text-red-800">
              FIBRINOLYSIS IF INDICATED → TRANSFER TO PCI CENTER
            </div>

            <p className="mt-3 text-xs font-bold text-red-800">
              Cardio MIRAI does not autonomously prescribe or administer
              fibrinolytic therapy.
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-xl border bg-slate-50 p-4 text-sm text-slate-700">
          <strong>Planned network integration:</strong> nearest validated
          PCI-capable center, estimated transport time, center contact,
          activation button, and ECG transmission. Until verified local
          network data are integrated, Cardio MIRAI must not invent a
          hospital destination or travel time.
        </div>
      </div>
    );
  }

  if (level === "YELLOW") {
    return (
      <div className="rounded-2xl border-2 border-amber-300 bg-white p-6 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
          Step 3 · Urgent ACS pathway
        </p>

        <h2 className="mt-2 text-2xl font-black text-amber-700">
          YELLOW → Urgent clinician assessment
        </h2>

        <div className="mt-4 rounded-xl bg-amber-50 p-5">
          <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-800">
            <li>Review symptoms, vital signs and the original ECG.</li>
            <li>
              Obtain hs-cTn where appropriate and perform repeat/serial ECG
              when clinically indicated.
            </li>
            <li>
              Assess for NSTE-ACS and important alternative diagnoses.
            </li>
            <li>
              Arrange cardiology/PCI-center consultation or transfer when
              clinically indicated.
            </li>
          </ol>
        </div>

        <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm font-bold text-amber-900">
          YELLOW is not a generic indication for fibrinolysis. NSTEMI cannot
          be diagnosed or excluded from ECG alone.
        </div>

        <div className="mt-4 rounded-lg bg-slate-50 p-3 text-center font-extrabold text-slate-800">
          DESTINATION → Based on clinical risk, stability and clinician
          assessment
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border-2 border-emerald-300 bg-white p-6 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
        Step 3 · Local clinical pathway
      </p>

      <h2 className="mt-2 text-2xl font-black text-emerald-700">
        GREEN → Continue clinical assessment
      </h2>

      <div className="mt-4 rounded-xl bg-emerald-50 p-5">
        <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-800">
          <li>
            Review symptoms, vital signs, risk factors and the original ECG.
          </li>
          <li>
            If ACS suspicion persists, obtain biomarkers and repeat/serial
            ECG as clinically indicated.
          </li>
          <li>
            Escalate or transfer if symptoms, instability or other findings
            remain concerning.
          </li>
          <li>
            Local management may continue only when the treating clinician
            determines emergency transfer is not required.
          </li>
        </ol>
      </div>

      <div className="mt-4 rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-center text-lg font-black text-emerald-900">
        GREEN DOES NOT EXCLUDE ACS
      </div>
    </div>
  );
}

export function RoleRoadmapCard({
  role,
  level,
}: {
  role: Role;
  level: TriageLevel;
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
            "Prepare repeat ECG and blood sampling/hs-cTn when ordered and available.",
            "Observe for deterioration and escalate immediately if the patient becomes unstable.",
            "Prepare consultation or transfer when directed by the clinician.",
          ]
        : [
            "Record symptoms and vital signs and provide the original ECG for clinician review.",
            "Continue observation and repeat ECG/testing when directed.",
            "Escalate immediately for worsening symptoms, instability or new concerning findings.",
            "Do not interpret GREEN as clearance or exclusion of ACS.",
          ];

  const doctorSteps =
    level === "RED"
      ? [
          "Immediately assess the patient and review the original 12-lead ECG; confirm or override the AI triage.",
          "Assess symptoms, onset time, hemodynamic status and important differential diagnoses.",
          "If STEMI / acute coronary occlusion is confirmed or strongly suspected, activate the local reperfusion pathway.",
          "Determine whether timely primary PCI is achievable within the applicable guideline/network target.",
          "If YES: activate the PCI center and arrange emergency transfer.",
          "If NO: assess fibrinolysis indication, symptom timing and contraindications under the approved protocol; if fibrinolysis is given, arrange immediate transfer to a PCI-capable center.",
        ]
      : level === "YELLOW"
        ? [
            "Review the original ECG and clinical presentation.",
            "Assess for NSTE-ACS and important alternative diagnoses.",
            "Use hs-cTn, serial ECG and clinical reassessment when indicated.",
            "Determine the need and urgency of specialist/PCI-center consultation or transfer.",
            "Do not use a generic YELLOW result as an indication for fibrinolysis.",
          ]
        : [
            "Review the original ECG and complete clinical presentation.",
            "Do not exclude ACS solely because the AI screen is GREEN.",
            "Use biomarkers, serial ECG or additional evaluation when clinical suspicion persists.",
            "Decide whether local management, observation, specialist consultation or transfer is appropriate.",
          ];

  const steps = role === "nurse" ? nurseSteps : doctorSteps;

  return (
    <div className="rounded-2xl border bg-white p-6 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
        Step 4 · Role-specific roadmap
      </p>

      <h3 className="mt-2 text-xl font-black text-slate-950">
        {role === "nurse" ? "Nurse / Feldsher Roadmap" : "Doctor Roadmap"}
      </h3>

      <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-slate-700">
        {steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    </div>
  );
}