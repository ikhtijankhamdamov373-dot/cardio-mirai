import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

const GROUPS = [
  {
    title: "Preventive Cardiology",
    items: ["Cardiovascular Profile", "PREVENT / Risk Age"],
    tone: "blue" as const,
  },
  {
    title: "Atrial Intelligence",
    items: ["Current AF", "Atrial Health", "Future AF — Research"],
    tone: "blue" as const,
  },
  {
    title: "Emergency Cardiology",
    items: ["ACS / STEMI Triage — Research Prototype"],
    tone: "red" as const,
    highlight: true,
  },
];

export function PlatformArchitecture() {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      {GROUPS.map((group) => (
        <Card
          key={group.title}
          className={group.highlight ? "border-red/30 bg-red-soft/40" : ""}
        >
          <p className="font-bold text-navy">{group.title}</p>
          <ul className="mt-2 space-y-1">
            {group.items.map((item) => (
              <li key={item} className="text-sm text-muted">
                {item}
              </li>
            ))}
          </ul>
          {group.highlight && (
            <div className="mt-3">
              <Badge tone="red">Research Prototype</Badge>
            </div>
          )}
        </Card>
      ))}
    </div>
  );
}
