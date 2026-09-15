"use client";

import type { PatientInput } from "@/lib/acsApi";

export interface PatientFormState extends PatientInput {
  main_symptom: string;
  onset_minutes_ago: number | null;
  sbp: number | null;
  dbp: number | null;
  heart_rate: number | null;
  spo2: number | null;
  diabetes: boolean;
  known_cad: boolean;
  previous_mi: boolean;
  previous_pci_cabg: boolean;
  hs_ctn: string;
  hs_ctn_time: string;
  previous_hs_ctn: string;
  previous_ecg_available: boolean;
}

export const emptyPatientForm: PatientFormState = {
  age: null,
  sex: null,
  symptomatic: false,
  high_clinical_suspicion: false,
  ongoing_chest_pain: false,
  main_symptom: "",
  onset_minutes_ago: null,
  sbp: null,
  dbp: null,
  heart_rate: null,
  spo2: null,
  diabetes: false,
  known_cad: false,
  previous_mi: false,
  previous_pci_cabg: false,
  hs_ctn: "",
  hs_ctn_time: "",
  previous_hs_ctn: "",
  previous_ecg_available: false,
};

const inputClass =
  "mt-1 w-full rounded-card border border-line px-3 py-3 text-base"; // text-base + py-3: large touch targets for ambulance use

const labelClass = "text-sm font-semibold text-ink";

export function PatientForm({
  value,
  onChange,
}: {
  value: PatientFormState;
  onChange: (next: PatientFormState) => void;
}) {
  const set = <K extends keyof PatientFormState>(key: K, v: PatientFormState[K]) =>
    onChange({ ...value, [key]: v });

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className={labelClass}>
        Age *
        <input
          type="number"
          inputMode="numeric"
          className={inputClass}
          value={value.age ?? ""}
          onChange={(e) => set("age", e.target.value ? Number(e.target.value) : null)}
        />
      </label>
      <label className={labelClass}>
        Sex *
        <select
          className={inputClass}
          value={value.sex ?? ""}
          onChange={(e) => set("sex", (e.target.value || null) as PatientFormState["sex"])}
        >
          <option value="">Select…</option>
          <option value="male">Male</option>
          <option value="female">Female</option>
        </select>
      </label>

      <label className={`${labelClass} sm:col-span-2`}>
        Main symptom
        <input
          type="text"
          className={inputClass}
          value={value.main_symptom}
          onChange={(e) => set("main_symptom", e.target.value)}
          placeholder="e.g. Acute central chest pain"
        />
      </label>

      <ToggleField
        label="Chest pain"
        checked={value.symptomatic}
        onChange={(v) => set("symptomatic", v)}
      />
      <ToggleField
        label="Ongoing chest pain"
        checked={value.ongoing_chest_pain}
        onChange={(v) => set("ongoing_chest_pain", v)}
      />

      <label className={labelClass}>
        Symptom onset (minutes ago)
        <input
          type="number"
          inputMode="numeric"
          className={inputClass}
          value={value.onset_minutes_ago ?? ""}
          onChange={(e) =>
            set("onset_minutes_ago", e.target.value ? Number(e.target.value) : null)
          }
        />
      </label>
      <ToggleField
        label="High clinical suspicion of ACS"
        checked={value.high_clinical_suspicion}
        onChange={(v) => set("high_clinical_suspicion", v)}
      />

      <label className={labelClass}>
        SBP (mmHg)
        <input
          type="number"
          inputMode="numeric"
          className={inputClass}
          value={value.sbp ?? ""}
          onChange={(e) => set("sbp", e.target.value ? Number(e.target.value) : null)}
        />
      </label>
      <label className={labelClass}>
        DBP (mmHg)
        <input
          type="number"
          inputMode="numeric"
          className={inputClass}
          value={value.dbp ?? ""}
          onChange={(e) => set("dbp", e.target.value ? Number(e.target.value) : null)}
        />
      </label>
      <label className={labelClass}>
        Heart rate (bpm)
        <input
          type="number"
          inputMode="numeric"
          className={inputClass}
          value={value.heart_rate ?? ""}
          onChange={(e) => set("heart_rate", e.target.value ? Number(e.target.value) : null)}
        />
      </label>
      <label className={labelClass}>
        SpO₂ (%)
        <input
          type="number"
          inputMode="numeric"
          className={inputClass}
          value={value.spo2 ?? ""}
          onChange={(e) => set("spo2", e.target.value ? Number(e.target.value) : null)}
        />
      </label>

      <ToggleField label="Diabetes" checked={value.diabetes} onChange={(v) => set("diabetes", v)} />
      <ToggleField label="Known CAD" checked={value.known_cad} onChange={(v) => set("known_cad", v)} />
      <ToggleField
        label="Previous MI"
        checked={value.previous_mi}
        onChange={(v) => set("previous_mi", v)}
      />
      <ToggleField
        label="Previous PCI/CABG"
        checked={value.previous_pci_cabg}
        onChange={(v) => set("previous_pci_cabg", v)}
      />

      <p className="sm:col-span-2 mt-2 text-xs font-bold uppercase tracking-wide text-muted">
        Optional
      </p>
      <label className={labelClass}>
        hs-cTn
        <input
          type="text"
          className={inputClass}
          value={value.hs_ctn}
          onChange={(e) => set("hs_ctn", e.target.value)}
        />
      </label>
      <label className={labelClass}>
        hs-cTn sampling time
        <input
          type="text"
          className={inputClass}
          value={value.hs_ctn_time}
          onChange={(e) => set("hs_ctn_time", e.target.value)}
        />
      </label>
      <label className={labelClass}>
        Previous hs-cTn
        <input
          type="text"
          className={inputClass}
          value={value.previous_hs_ctn}
          onChange={(e) => set("previous_hs_ctn", e.target.value)}
        />
      </label>
      <ToggleField
        label="Previous ECG available"
        checked={value.previous_ecg_available}
        onChange={(v) => set("previous_ecg_available", v)}
      />
    </div>
  );
}

function ToggleField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-3 rounded-card border border-line px-3 py-3 text-sm font-semibold text-ink">
      <input
        type="checkbox"
        className="h-5 w-5"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      {label}
    </label>
  );
}
