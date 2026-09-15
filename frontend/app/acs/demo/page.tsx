import { AcsTriageFlow } from "@/components/acs/AcsTriageFlow";

export const metadata = { title: "Cardio MIRAI ACS — Live Demo" };

export default function AcsDemoPage() {
  // autoDemo pre-flags the synthetic-demo banner; the presenter still clicks
  // "DEMO CASE" once to populate and advance to the ECG step, matching the
  // documented 60-90s live-demo sequence exactly (Open -> Emergency
  // Cardiology -> ACS/STEMI Triage -> Load Synthetic Demo -> Analyze ->
  // ECG Quality -> ECG meets STEMI criteria -> Explainability -> Rural pathway).
  return <AcsTriageFlow autoDemo={false} />;
}
