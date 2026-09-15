import { ComingSoon } from "@/components/ui/ComingSoon";

export const metadata = { title: "Clinical Calculators | Cardio MIRAI" };

export default function CalculatorsPage() {
  return (
    <ComingSoon
      title="Clinical Calculators"
      description="An MDCalc-style dashboard of guideline-referenced cardiovascular calculators, grouped by clinical use. Ships in Phase 3."
      plannedContent={[
        "CHA₂DS₂-VASc, HAS-BLED, GRACE, TIMI, HEART, Wells, Geneva",
        "PRECISE-DAPT, DAPT score, ASCVD risk, Framingham risk",
        "H2FPEF, HFA-PEFF, CKD-EPI eGFR, Cockcroft-Gault",
        "BMI, BSA, QTc, Mean Arterial Pressure",
        "Each calculator: inputs, formula, interpretation, and ESC/AHA references",
      ]}
    />
  );
}
