import { ComingSoon } from "@/components/ui/ComingSoon";

export const metadata = { title: "Research Hub | Cardio MIRAI" };

export default function ResearchPage() {
  return (
    <ComingSoon
      title="Research Hub"
      description="Publications, ongoing projects, AI model documentation, public datasets, and registry statistics from the Cardio MIRAI research program. Ships in Phase 5."
      plannedContent={[
        "Publications and manuscripts in preparation",
        "Ongoing research projects and collaborations",
        "AI model documentation and validation reports",
        "Public dataset references (PTB-XL, MIMIC, PhysioNet)",
        "Registry statistics and downloadable summaries",
      ]}
    />
  );
}
