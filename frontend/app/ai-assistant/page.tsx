import { ComingSoon } from "@/components/ui/ComingSoon";

export const metadata = { title: "AI Assistant | Cardio MIRAI" };

export default function AiAssistantPage() {
  return (
    <ComingSoon
      title="Clinical AI Assistant"
      description="A conversational assistant for guideline lookup, calculator guidance, and literature summaries, grounded in the Knowledge Center once it is published."
      plannedContent={[
        "Guideline and literature Q&A grounded in published sources",
        "Calculator guidance and result interpretation",
        "Case-based learning support for physicians and trainees",
      ]}
    />
  );
}
