import { AcsTriageFlow } from "@/components/acs/AcsTriageFlow";

export const metadata = { title: "Cardio MIRAI ACS — Live Demo" };

export default function AcsDemoPage() {
  // Auto-loads the synthetic demo case on mount (see AcsTriageFlow's
  // useEffect), so the presenter never types clinical values live —
  // landing here already shows Step 2 (ECG Input) pre-populated; only
  // "Analyze" needs to be clicked. Matches the documented 60-90s sequence:
  // Open -> Emergency Cardiology -> ACS/STEMI Triage -> (auto) Demo loaded
  // -> Analyze -> ECG Quality -> ECG meets STEMI criteria -> Explainability
  // -> Rural pathway.
  return <AcsTriageFlow autoDemo={true} />;
}
