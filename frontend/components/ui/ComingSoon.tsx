import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export function ComingSoon({
  title,
  description,
  plannedContent,
}: {
  title: string;
  description: string;
  plannedContent: string[];
}) {
  return (
    <section className="mx-auto max-w-3xl px-5 py-16">
      <Badge tone="blue">In development</Badge>
      <h1 className="mt-4 text-3xl font-black text-navy">{title}</h1>
      <p className="mt-3 text-muted">{description}</p>

      <Card className="mt-8">
        <p className="font-bold text-navy">Planned for this module</p>
        <ul className="mt-3 space-y-2 text-sm text-muted list-disc list-inside">
          {plannedContent.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Card>
    </section>
  );
}
