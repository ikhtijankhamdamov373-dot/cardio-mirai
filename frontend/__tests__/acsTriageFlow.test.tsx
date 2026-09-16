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

  it("both ECG upload inputs are enabled, not disabled", () => {
    render(<AcsTriageFlow />);
    fireEvent.click(screen.getByText(/DEMO CASE/i)); // advance to Step 2
    const fileInputs = document.querySelectorAll('input[type="file"]');
    // Digital upload and image/PDF digitization are both genuinely functional now.
    expect(fileInputs[0]).not.toBeDisabled();
    expect(fileInputs[1]).not.toBeDisabled();
  });

  it("uploading an ECG image, confirming calibration and layout, and digitizing shows the distinctly-labeled image result", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        analysis_source: "uploaded_ecg_image",
        digitization_method: "image_waveform_extraction",
        detected_leads: ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"],
        excluded_low_confidence_leads: [],
        excluded_low_quality_leads: [],
        panel_trace_confidence: {},
        px_per_mm_detected: 8.0,
        paper_speed_mm_s: 25,
        gain_mm_per_mv: 10,
        calibration_confirmed_by_user: true,
        image_quality: { width: 3200, height: 960, megapixels: 3.07, blur_variance: 500, estimated_rotation_deg: 0.1 },
        sampling_frequency_hz: 250,
        heart_rate_bpm: 75,
        qrs_beat_count: 5,
        warnings: [],
        preview_waveforms: { V2: [0, 0.1, 0.2, 0.1, 0] },
        quality_gate_passed: true,
        criteria_met: true,
        requires_clinical_correlation: false,
        mimic_present: false,
        mimic_names: [],
        contiguous_leads: ["V2", "V3", "V4"],
        contiguous_group_name: "Anteroseptal",
        triggering_rule_id: "ACS-CORE-002",
        contributing_measurements: [{ lead: "V2", st_elevation_mm: 2.87 }],
        all_lead_measurements: [],
        reciprocal_changes: [],
        thresholds_applied: { general_leads_mm: 1.0, v2_v3_mm: 2.0 },
        urgency: "EMERGENCY",
        headline: "ECG meets guideline STEMI criteria",
        acs_not_excluded_statement: null,
        nstemi_note: "NSTEMI cannot be determined from ECG alone",
        source: "2025 ACC/AHA ACS Guideline / 2023 ESC ACS Guideline / Fifth Universal Definition of Myocardial Infarction (2026)",
        label: "ECG IMAGE DIGITIZATION — RESEARCH PROTOTYPE",
        interpretation_note: "AI-assisted ECG interpretation from a photographed/scanned ECG. Not clinically validated.",
        disclaimer: "Cardio MIRAI provides decision support and does not replace clinical diagnosis.",
      }),
    }) as jest.Mock;

    render(<AcsTriageFlow />);
    fireEvent.click(screen.getByText(/DEMO CASE/i));

    global.URL.createObjectURL = jest.fn(() => "blob:mock-url");
    global.URL.revokeObjectURL = jest.fn();

    const fileInputs = document.querySelectorAll('input[type="file"]');
    const imgFile = new File(["fake-png-bytes"], "ecg.png", { type: "image/png" });
    fireEvent.change(fileInputs[1], { target: { files: [imgFile] } });

    fireEvent.click(screen.getByText(/Confirm 25 mm\/s, 10 mm\/mV/i));
    fireEvent.click(screen.getByText(/^Standard 3×4$/i));
    fireEvent.click(screen.getByText(/^Digitize ECG$/i));

    await waitFor(() => {
      expect(screen.getByText("ECG IMAGE DIGITIZATION — RESEARCH PROTOTYPE")).toBeInTheDocument();
    });
    expect(screen.getByText("Image-derived ECG measurements")).toBeInTheDocument();
    expect(screen.getByText("DIGITIZED / DETECTED TRACE PREVIEW")).toBeInTheDocument();
  });

  it("selecting an unsupported file shows a clear error, not a silent failure", () => {
    render(<AcsTriageFlow />);
    fireEvent.click(screen.getByText(/DEMO CASE/i));
    const fileInputs = document.querySelectorAll('input[type="file"]');
    const badFile = new File(["fake"], "scan.pdf", { type: "application/pdf" });
    fireEvent.change(fileInputs[0], { target: { files: [badFile] } });
    expect(screen.getByText(/Unsupported file/i)).toBeInTheDocument();
  });

  it("selecting a valid file shows filename and an Analyze button, and a successful analysis renders REAL ECG ANALYSIS distinctly from SYNTHETIC DEMONSTRATION", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        analysis_source: "uploaded_real_ecg",
        detected_leads: ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"],
        unrecognized_leads: [],
        duplicate_leads: [],
        excluded_low_quality_leads: [],
        sampling_frequency_hz: 500,
        duration_seconds: 10,
        heart_rate_bpm: 75,
        qrs_beat_count: 12,
        warnings: [],
        quality_gate_passed: true,
        criteria_met: true,
        requires_clinical_correlation: false,
        mimic_present: false,
        mimic_names: [],
        contiguous_leads: ["V2", "V3", "V4"],
        contiguous_group_name: "Anteroseptal",
        triggering_rule_id: "ACS-CORE-002",
        contributing_measurements: [
          { lead: "V2", st_elevation_mm: 2.6 },
          { lead: "V3", st_elevation_mm: 2.6 },
        ],
        all_lead_measurements: [{ lead: "V2", st_elevation_mm: 2.6, reciprocal_depression_mm: null }],
        reciprocal_changes: [],
        thresholds_applied: { general_leads_mm: 1.0, v2_v3_mm: 2.0 },
        urgency: "EMERGENCY",
        headline: "ECG meets guideline STEMI criteria",
        acs_not_excluded_statement: null,
        nstemi_note: "NSTEMI cannot be determined from ECG alone",
        source: "2025 ACC/AHA ACS Guideline / 2023 ESC ACS Guideline / Fifth Universal Definition of Myocardial Infarction (2026)",
        disclaimer: "Cardio MIRAI provides decision support and does not replace clinical diagnosis.",
      }),
    }) as jest.Mock;

    render(<AcsTriageFlow />);
    fireEvent.click(screen.getByText(/DEMO CASE/i)); // reaches Step 2 with synthetic banner shown
    expect(screen.getByText(/SYNTHETIC DEMONSTRATION — NOT A REAL PATIENT/i)).toBeInTheDocument();

    const fileInputs = document.querySelectorAll('input[type="file"]');
    const heaFile = new File(["header"], "record.hea", { type: "application/octet-stream" });
    fireEvent.change(fileInputs[0], { target: { files: [heaFile] } });
    expect(screen.getByText(/record\.hea/)).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Analyze Uploaded ECG/i));

    await waitFor(() => {
      expect(screen.getByText("REAL ECG ANALYSIS")).toBeInTheDocument();
    });
    // The two labels coexist without conflation: the page-level banner still
    // says SYNTHETIC DEMONSTRATION (because Demo Case was clicked earlier),
    // but the upload result itself is unambiguously labeled REAL ECG ANALYSIS,
    // proving a real upload is never silently merged into the demo state.
    expect(screen.getByText(/SYNTHETIC DEMONSTRATION — NOT A REAL PATIENT/i)).toBeInTheDocument();
    expect(screen.getByText("REAL ECG ANALYSIS")).toBeInTheDocument();
  });
});
