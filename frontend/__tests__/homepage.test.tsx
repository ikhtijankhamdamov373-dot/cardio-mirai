import { render, screen, waitFor } from "@testing-library/react";
import HomePage from "@/app/page";

// Mock fetch used by BackendStatus so this test doesn't depend on a live backend.
beforeEach(() => {
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ ok: true }),
  }) as jest.Mock;
});

describe("HomePage", () => {
  it("renders the hero headline and tagline", async () => {
    render(<HomePage />);
    expect(
      screen.getByRole("heading", {
        name: /AI Platform for Precision Cardiovascular Medicine/i,
      })
    ).toBeInTheDocument();
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  });

  it("renders primary CTA buttons", () => {
    render(<HomePage />);
    expect(screen.getByRole("link", { name: /Start ECG Analysis/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Clinical Calculators/i })).toBeInTheDocument();
  });

  it("renders the research disclaimer", () => {
    render(<HomePage />);
    expect(screen.getByText(/Research prototype\. Not a medical device\./i)).toBeInTheDocument();
  });

  it("renders the developer section with correct attribution", () => {
    render(<HomePage />);
    expect(screen.getByText(/Ikhtiyorjon Khamdamov, MD, MPH/i)).toBeInTheDocument();
    expect(screen.getByText(/Prof\. Tetsuo Sasano/i)).toBeInTheDocument();
  });
});
