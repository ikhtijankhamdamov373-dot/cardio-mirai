import { Card } from "@/components/ui/Card";
import { DeveloperCard } from "@/components/layout/DeveloperCard";
import { Disclaimer } from "@/components/ui/Disclaimer";

export const metadata = { title: "About | Cardio MIRAI" };

const SECTIONS = [
  {
    title: "Mission",
    body: "To give physicians, researchers, and medical students a single, trustworthy workspace for cardiovascular screening, clinical decision support, education, and research.",
  },
  {
    title: "Vision",
    body: "A comprehensive AI platform for precision cardiovascular medicine — expanding from ECG analysis into echocardiography, imaging, guidelines, and longitudinal risk prediction.",
  },
  {
    title: "Scientific Background",
    body: "Cardio MIRAI's ECG models are trained on public 12-lead ECG datasets (including PTB-XL) using waveform-first preprocessing, with ongoing work on calibration and external validation across additional public datasets.",
  },
  {
    title: "Future Roadmap",
    body: "Planned modules include Echo AI, Coronary CTA AI, MRI AI, a clinical AI assistant, and a longitudinal AF risk prediction engine, released incrementally as each is validated.",
  },
];

export default function AboutPage() {
  return (
    <section className="mx-auto max-w-4xl px-5 py-16">
      <h1 className="text-3xl font-black text-navy">About Cardio MIRAI</h1>

      <div className="mt-8 grid gap-5 sm:grid-cols-2">
        {SECTIONS.map((s) => (
          <Card key={s.title}>
            <p className="font-bold text-navy">{s.title}</p>
            <p className="mt-2 text-sm text-muted">{s.body}</p>
          </Card>
        ))}
      </div>

      <div className="mt-10">
        <p className="text-center text-sm font-bold text-navy uppercase tracking-wide">
          Founder
        </p>
        <div className="mt-4">
          <DeveloperCard />
        </div>
      </div>

      <div className="mt-10">
        <p className="font-bold text-navy mb-3">Medical Disclaimer</p>
        <Disclaimer />
      </div>
    </section>
  );
}
