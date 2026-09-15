"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { EcgQualityInput, LeadInput } from "@/lib/acsApi";

const MANUAL_LEADS = ["II", "III", "aVF", "V2", "V3", "V4"];

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

export function EcgInputStep({
  value,
  onChange,
}: {
  value: EcgInputState;
  onChange: (next: EcgInputState) => void;
}) {
  const [manualOpen, setManualOpen] = useState(false);

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

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <p className="font-bold text-navy">Upload Digital 12-Lead ECG</p>
          <Badge tone="blue">Available for prototype analysis</Badge>
          <p className="mt-2 text-sm text-muted">
            Uses the existing supported ECG input pipeline where technically
            possible. For tonight&rsquo;s demonstration, use{" "}
            <strong>Load Demo Case</strong> below or manual entry to exercise
            the deterministic engine directly.
          </p>
          <input type="file" accept=".hea,.dat,.zip" disabled className="mt-3 w-full text-sm opacity-50" />
        </Card>

        <Card>
          <p className="font-bold text-navy">Take / Upload ECG Photo</p>
          <Badge tone="amber">Smartphone ECG Photo — Prototype / Under Development</Badge>
          <p className="mt-2 text-sm text-muted">
            Central to the rural Uzbekistan use case. A validated
            photo-to-waveform digitization pipeline does not exist yet — this
            demonstrates the intended workflow without fabricating clinical
            analysis from an arbitrary photograph.
          </p>
          <input type="file" accept="image/*" capture="environment" disabled className="mt-3 w-full text-sm opacity-50" />
        </Card>
      </div>

      <Card>
        <button
          onClick={() => setManualOpen((v) => !v)}
          className="flex w-full items-center justify-between text-left"
          aria-expanded={manualOpen}
        >
          <span className="font-bold text-navy">Manual entry (interactive demo)</span>
          <span className="text-muted text-sm">{manualOpen ? "Hide" : "Show"}</span>
        </button>
        {manualOpen && (
          <div className="mt-4 space-y-4">
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
