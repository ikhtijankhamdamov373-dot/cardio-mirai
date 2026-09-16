import { render, screen, fireEvent } from "@testing-library/react";
import { Navbar } from "@/components/layout/Navbar";

describe("Navbar", () => {
  it("renders all 8 primary nav links", () => {
    render(<Navbar />);
    const expected = [
      "Home",
      "Digital Lifeline",
      "ECG AI",
      "Emergency Cardiology",
      "Clinical Calculators",
      "Knowledge Center",
      "Research Hub",
      "AI Assistant",
      "About",
      "Contact",
    ];
    for (const label of expected) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it("mobile menu is closed by default and opens on toggle", () => {
    render(<Navbar />);
    const toggle = screen.getByLabelText("Open menu");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(screen.getByLabelText("Close menu")).toHaveAttribute("aria-expanded", "true");
  });
});
