import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DeveloperCard } from "@/components/layout/DeveloperCard";
import { BackendStatus } from "@/components/layout/BackendStatus";
import { Disclaimer } from "@/components/ui/Disclaimer";

const FEATURES = [
  {
    title: "ECG AI",
    body: "Upload digital ECG (WFDB), images, or PDFs for AI-assisted rhythm and morphology screening.",
    href: "/ecg-ai",
  },
  {
    title: "Clinical Calculators",
    body: "CHA₂DS₂-VASc, HAS-BLED, GRACE, TIMI, HEART, Wells, ASCVD and more — guideline-referenced.",
    href: "/calculators",
  },
  {
    title: "Knowledge Center",
    body: "ECG Academy, echocardiography, guidelines, landmark trials, and a drug library in one place.",
    href: "/knowledge",
  },
  {
    title: "Research Hub",
    body: "Publications, ongoing projects, AI models, datasets, and registry statistics.",
    href: "/research",
  },
];

export default function HomePage() {
  return (
    <div>
      <section className="bg-gradient-to-br from-navy to-blue text-white">
        <div className="mx-auto max-w-6xl px-5 py-20 grid gap-10 md:grid-cols-2 items-center">
          <div>
            <span className="inline-block rounded-full bg-white/10 px-3 py-1 text-xs font-bold tracking-wide">
              CARDIO MIRAI
            </span>
            <h1 className="mt-4 text-4xl md:text-5xl font-black leading-tight">
              AI Platform for Precision Cardiovascular Medicine
            </h1>
            <p className="mt-4 text-white/80 text-lg">
              Helping physicians through intelligent cardiovascular
              screening, diagnosis, clinical decision support, education and
              research.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button href="/ecg-ai" variant="primary">Start ECG Analysis</Button>
              <Button href="/calculators" variant="secondary">Clinical Calculators</Button>
              <Button href="/knowledge" variant="secondary">Knowledge Center</Button>
              <Button href="/research" variant="ghost">Research</Button>
            </div>
            <div className="mt-6">
              <BackendStatus />
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16">
        <h2 className="text-2xl font-black text-navy">Platform modules</h2>
        <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <Card key={f.href} className="hover:-translate-y-1 transition-transform">
              <p className="font-bold text-navy">{f.title}</p>
              <p className="mt-2 text-sm text-muted">{f.body}</p>
              <Button href={f.href} variant="ghost" className="mt-4 px-0 justify-start">
                Explore →
              </Button>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-4">
        <Disclaimer />
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16">
        <h2 className="text-center text-2xl font-black text-navy">Developed by</h2>
        <div className="mt-6">
          <DeveloperCard />
        </div>
      </section>
    </div>
  );
}
