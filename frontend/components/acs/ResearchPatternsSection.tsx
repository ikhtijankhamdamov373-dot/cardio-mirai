"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

const RESEARCH_PATTERNS = [
  "Wellens-type pattern",
  "Hyperacute T-wave pattern",
  "aVR / inferolateral ischemic pattern",
  "De Winter pattern",
  "Sgarbossa / modified Sgarbossa",
];

export function ResearchPatternsSection() {
  const [open, setOpen] = useState(false);

  return (
    <Card>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between text-left"
        aria-expanded={open}
      >
        <span className="font-bold text-navy">Advanced ECG Research Signals</span>
        <span className="text-muted text-sm">{open ? "Hide" : "Show"}</span>
      </button>

      {open && (
        <div className="mt-4 space-y-3">
          <p className="text-xs text-muted">
            These patterns are described in the peer-reviewed ECG literature
            but are not named as formal diagnostic criteria in the 2023 ESC
            or 2025 ACC/AHA ACS guidelines (see Matrix v1.2 FINAL). They are
            shown here for research/educational context only and never
            contribute to the deterministic STEMI Core result above.
          </p>
          <ul className="space-y-2">
            {RESEARCH_PATTERNS.map((pattern) => (
              <li
                key={pattern}
                className="flex items-center justify-between rounded-card border border-line px-3 py-2 text-sm"
              >
                <span className="text-ink">{pattern}</span>
                <Badge tone="neutral">Research module — under development</Badge>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
