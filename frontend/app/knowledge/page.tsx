import { ComingSoon } from "@/components/ui/ComingSoon";

export const metadata = { title: "Knowledge Center | Cardio MIRAI" };

export default function KnowledgePage() {
  return (
    <ComingSoon
      title="Knowledge Center"
      description="Original educational content based on publicly available guidelines and literature — not a copy of proprietary resources. Ships in Phase 4."
      plannedContent={[
        "ECG Academy: systematic interpretation, intervals, blocks, cases, quizzes",
        "Echocardiography Academy: measurements, LVEF, diastolic function, valve disease",
        "Cardiovascular Guidelines organized by disease (AF, HF, ACS, CAD, HTN, and more)",
        "Landmark Trials database (PARADIGM-HF, DAPA-HF, ISCHEMIA, and more)",
        "Drug Library with mechanism, dosing, renal adjustment, and ESC/AHA recommendations",
        "Cardiovascular Imaging atlas and a Research Hub for methodology and statistics",
      ]}
    />
  );
}
