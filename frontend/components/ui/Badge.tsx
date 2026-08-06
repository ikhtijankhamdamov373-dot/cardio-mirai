import { ReactNode } from "react";

type Tone = "blue" | "green" | "amber" | "red" | "neutral";

const toneClasses: Record<Tone, string> = {
  blue: "bg-blue-soft text-blue",
  green: "bg-green/10 text-green",
  amber: "bg-amber/10 text-amber",
  red: "bg-red-soft text-red",
  neutral: "bg-line/60 text-muted",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}
