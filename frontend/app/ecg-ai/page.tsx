import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Disclaimer } from "@/components/ui/Disclaimer";

export const metadata = { title: "ECG AI | Cardio MIRAI" };

// Per Phase 1 safeguard #6: the ECG interface is NOT ported here yet.
// It stays on the legacy site (which keeps running unchanged) until the
// scaffold and API proxy are verified, then gets ported as its own subphase.
const LEGACY_ECG_URL = process.env.NEXT_PUBLIC_LEGACY_SITE_URL || "https://cardiomirai.com";

export default function EcgAiPage() {
  return (
    <section className="mx-auto max-w-3xl px-5 py-16">
      <Badge tone="blue">Migration in progress</Badge>
      <h1 className="mt-4 text-3xl font-black text-navy">ECG AI</h1>
      <p className="mt-3 text-muted">
        The ECG upload and analysis interface is being migrated to this new
        platform. To avoid any risk to the working analysis workflow, it has
        not been ported yet — the fully functional version remains available
        on the current production site.
      </p>

      <Card className="mt-8">
        <p className="font-bold text-navy">Use the working ECG AI prototype</p>
        <p className="mt-2 text-sm text-muted">
          Supports ECG images, PDF, WFDB (.hea/.dat), and ZIP uploads with
          AI-assisted atrial remodeling and AF-related screening.
        </p>
        <Button href={LEGACY_ECG_URL} variant="primary" className="mt-4">
          Open the current ECG AI prototype
        </Button>
      </Card>

      <div className="mt-8">
        <Disclaimer />
      </div>
    </section>
  );
}
