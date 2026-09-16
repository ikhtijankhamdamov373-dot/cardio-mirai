import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DigitalLifelineFlow } from "@/components/lifeline/DigitalLifelineFlow";

describe("DigitalLifelineFlow", () => {
  it("renders the hero upload workflow with the required branding", () => {
    render(<DigitalLifelineFlow />);
    expect(screen.getByText("Digital Lifeline")).toBeInTheDocument();
    expect(screen.getByText("AI-Assisted Emergency ECG Triage")).toBeInTheDocument();
    expect(screen.getAllByText(/TAKE \/ UPLOAD ECG PHOTO/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Upload ECG File")).toBeInTheDocument();
  });

  it("does not show digitization/calibration/layout controls on the main flow", () => {
    render(<DigitalLifelineFlow />);
    expect(screen.queryByText(/Digitize ECG/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/calibration/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Standard 3×4/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/px\/mm/i)).not.toBeInTheDocument();
  });

  it("Presentation Demo menu offers RED, YELLOW, GREEN and each is clearly labeled synthetic", async () => {
    render(<DigitalLifelineFlow />);
    fireEvent.click(screen.getByText("Presentation Demo"));
    expect(screen.getByText("Demo: RED case")).toBeInTheDocument();
    expect(screen.getByText("Demo: YELLOW case")).toBeInTheDocument();
    expect(screen.getByText("Demo: GREEN case")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Demo: RED case"));
    await waitFor(() => {
      expect(screen.getAllByText("SYNTHETIC DEMONSTRATION CASE").length).toBeGreaterThan(0);
    });
    expect(screen.getByText("RED")).toBeInTheDocument();
    expect(screen.getByText("Possible STEMI / Acute Coronary Occlusion Pattern")).toBeInTheDocument();
    // Never say "MI diagnosed"
    expect(screen.queryByText(/MI diagnosed/i)).not.toBeInTheDocument();
  });

  it("YELLOW demo shows the required NSTEMI disclaimer", async () => {
    render(<DigitalLifelineFlow />);
    fireEvent.click(screen.getByText("Presentation Demo"));
    fireEvent.click(screen.getByText("Demo: YELLOW case"));
    await waitFor(() => {
      expect(screen.getByText("YELLOW")).toBeInTheDocument();
    });
    expect(screen.getByText("Possible Ischemic / High-Risk ECG Abnormality")).toBeInTheDocument();
  });

  it("GREEN demo never says the patient is safe and shows ACS-not-excluded language", async () => {
    render(<DigitalLifelineFlow />);
    fireEvent.click(screen.getByText("Presentation Demo"));
    fireEvent.click(screen.getByText("Demo: GREEN case"));
    await waitFor(() => {
      expect(screen.getByText("GREEN")).toBeInTheDocument();
    });
    expect(screen.getByText("No emergency ECG pattern identified by prototype")).toBeInTheDocument();
    expect(screen.getAllByText(/ACS is NOT excluded/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Patient is safe/i)).not.toBeInTheDocument();
  });

  it("CONFIRM TRIAGE and OVERRIDE TRIAGE buttons toggle clinician state", async () => {
    render(<DigitalLifelineFlow />);
    fireEvent.click(screen.getByText("Presentation Demo"));
    fireEvent.click(screen.getByText("Demo: RED case"));
    await waitFor(() => expect(screen.getByText("CONFIRM TRIAGE")).toBeInTheDocument());
    fireEvent.click(screen.getByText("CONFIRM TRIAGE"));
    expect(screen.getByText(/Triage confirmed by clinician/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText("OVERRIDE TRIAGE"));
    expect(screen.getByText(/Triage overridden by clinician/i)).toBeInTheDocument();
  });

  it("shows the AF module with honest legacy/future labeling", async () => {
    render(<DigitalLifelineFlow />);
    fireEvent.click(screen.getByText("Presentation Demo"));
    fireEvent.click(screen.getByText("Demo: GREEN case"));
    await waitFor(() => expect(screen.getByText("Rhythm & Atrial Fibrillation")).toBeInTheDocument());
    expect(screen.getByText("Legacy atrial-abnormality research score — exploratory")).toBeInTheDocument();
    expect(screen.getByText("Under Development")).toBeInTheDocument();
    expect(screen.queryByText(/future AF prediction available/i)).not.toBeInTheDocument();
  });

  it("real upload failure falls back to demonstration mode, never fabricating a specific triage color for the upload", async () => {
    global.URL.createObjectURL = jest.fn(() => "blob:mock-url");
    global.URL.revokeObjectURL = jest.fn();
    global.fetch = jest.fn().mockRejectedValue(new Error("Digitization failed: no grid detected"));
    render(<DigitalLifelineFlow />);
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["fake"], "ecg.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("DEMONSTRATION / RESEARCH PROTOTYPE MODE")).toBeInTheDocument();
    });
    expect(screen.getByText(/Example screening workflow — not derived from your uploaded image/i)).toBeInTheDocument();
    // No SYNTHETIC DEMONSTRATION CASE banner (that's only for explicit Presentation Demo, not a failed real upload)
    expect(screen.queryByText("SYNTHETIC DEMONSTRATION CASE")).not.toBeInTheDocument();
  });

  it("hides PREVENT, Risk Age, Heart Age, and other unrelated modules", () => {
    render(<DigitalLifelineFlow />);
    expect(screen.queryByText(/PREVENT/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Risk Age/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Heart Age/i)).not.toBeInTheDocument();
  });

  it("footer shows the required safety disclaimers", async () => {
    render(<DigitalLifelineFlow />);
    fireEvent.click(screen.getByText("Presentation Demo"));
    fireEvent.click(screen.getByText("Demo: GREEN case"));
    await waitFor(() => expect(screen.getAllByText("Research Prototype").length).toBeGreaterThan(0));
    expect(screen.getByText(/Do not delay emergency care waiting for AI/i)).toBeInTheDocument();
    expect(screen.getByText(/Not a substitute for clinician diagnosis/i)).toBeInTheDocument();
  });
});
