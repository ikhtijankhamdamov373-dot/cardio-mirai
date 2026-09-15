import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AcsTriageFlow } from "@/components/acs/AcsTriageFlow";

describe("AcsTriageFlow", () => {
  it("renders the research prototype banner", () => {
    render(<AcsTriageFlow />);
    expect(screen.getByText(/RESEARCH PROTOTYPE — NOT FOR CLINICAL USE/i)).toBeInTheDocument();
  });

  it("renders the three-module platform architecture", () => {
    render(<AcsTriageFlow />);
    expect(screen.getByText("Preventive Cardiology")).toBeInTheDocument();
    expect(screen.getByText("Atrial Intelligence")).toBeInTheDocument();
    expect(screen.getByText("Emergency Cardiology")).toBeInTheDocument();
  });

  it("loading the demo case shows the synthetic-patient banner and advances to ECG step", () => {
    render(<AcsTriageFlow />);
    fireEvent.click(screen.getByText(/DEMO CASE/i));
    expect(screen.getByText(/SYNTHETIC DEMONSTRATION — NOT A REAL PATIENT/i)).toBeInTheDocument();
    expect(screen.getByText(/Step 2 — ECG Input/i)).toBeInTheDocument();
  });

  it("autoDemo=true (the /acs/demo presentation route) loads the case on mount with zero clicks", () => {
    render(<AcsTriageFlow autoDemo={true} />);
    expect(screen.getByText(/SYNTHETIC DEMONSTRATION — NOT A REAL PATIENT/i)).toBeInTheDocument();
    expect(screen.getByText(/Step 2 — ECG Input/i)).toBeInTheDocument();
    // Confirms the presenter only needs to click Analyze, never type values.
    expect(screen.getByText(/^Analyze$/i)).toBeInTheDocument();
  });

  it("running the demo case analysis calls the backend and shows the EMERGENCY headline", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        quality_gate_passed: true,
        criteria_met: true,
        requires_clinical_correlation: false,
        mimic_present: false,
        mimic_names: [],
        contiguous_leads: ["V2", "V3", "V4"],
        contributing_measurements: [
          { lead: "V2", st_elevation_mm: 2.3 },
          { lead: "V3", st_elevation_mm: 2.5 },
          { lead: "V4", st_elevation_mm: 1.8 },
        ],
        thresholds_applied: { general_leads_mm: 1.0, v2_v3_mm: 2.0 },
        urgency: "EMERGENCY",
        headline: "ECG meets guideline STEMI criteria",
        acs_not_excluded_statement: null,
        nstemi_note: "NSTEMI cannot be determined from ECG alone",
        source: "2025 ACC/AHA ACS Guideline / 2023 ESC ACS Guideline / Fourth Universal Definition of MI",
        disclaimer: "Cardio MIRAI provides decision support and does not replace clinical diagnosis.",
      }),
    }) as jest.Mock;

    render(<AcsTriageFlow />);
    fireEvent.click(screen.getByText(/DEMO CASE/i));
    fireEvent.click(screen.getByText(/^Analyze$/i));

    await waitFor(() => {
      expect(screen.getByText("EMERGENCY ECG FINDING")).toBeInTheDocument();
    });
    expect(screen.getByText("ECG meets guideline STEMI criteria")).toBeInTheDocument();
    expect(screen.getByText(/does not replace clinical diagnosis/i)).toBeInTheDocument();
  });

  it("never renders a prohibited phrase after a nondiagnostic result", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        quality_gate_passed: true,
        criteria_met: false,
        requires_clinical_correlation: false,
        mimic_present: false,
        mimic_names: [],
        contiguous_leads: [],
        contributing_measurements: [],
        thresholds_applied: { general_leads_mm: 1.0, v2_v3_mm: null },
        urgency: "ROUTINE",
        headline: "STEMI criteria not detected on this ECG",
        acs_not_excluded_statement:
          "A nondiagnostic ECG does not exclude ACS. Clinical assessment, serial ECG and cardiac troponin testing may be required.",
        nstemi_note: "NSTEMI cannot be determined from ECG alone",
        source: "2025 ACC/AHA ACS Guideline / 2023 ESC ACS Guideline / Fourth Universal Definition of MI",
        disclaimer: "Cardio MIRAI provides decision support and does not replace clinical diagnosis.",
      }),
    }) as jest.Mock;

    render(<AcsTriageFlow />);
    fireEvent.click(screen.getByText(/DEMO CASE/i));
    fireEvent.click(screen.getByText(/^Analyze$/i));

    await waitFor(() => {
      expect(screen.getByText("ACS CANNOT BE EXCLUDED")).toBeInTheDocument();
    });

    const bodyText = document.body.textContent ?? "";
    for (const phrase of ["STEMI diagnosed", "NSTEMI diagnosed", "No ACS", "ACS excluded", "Safe to discharge"]) {
      expect(bodyText).not.toContain(phrase);
    }
  });

  it("research patterns section is collapsed by default and labeled under development", () => {
    render(<AcsTriageFlow />);
    fireEvent.click(screen.getByText("Advanced ECG Research Signals"));
    expect(screen.getAllByText("Research module — under development").length).toBeGreaterThan(0);
    expect(screen.getByText("Wellens-type pattern")).toBeInTheDocument();
    expect(screen.getByText("de Winter pattern".replace("de", "De"))).toBeInTheDocument();
  });
});
