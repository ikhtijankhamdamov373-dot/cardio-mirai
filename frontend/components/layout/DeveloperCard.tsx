import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export function DeveloperCard() {
  return (
    <Card className="mx-auto max-w-2xl text-center transition-transform hover:-translate-y-1">
      <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-gradient-to-br from-navy to-blue text-lg font-black text-white">
        IK
      </div>
      <p className="mt-4 text-lg font-bold text-navy">
        Ikhtiyorjon Khamdamov, MD, MPH
      </p>
      <p className="text-sm text-muted">
        PhD Candidate · Department of Cardiovascular Medicine
      </p>
      <p className="text-sm text-muted">Institute of Science Tokyo</p>
      <p className="mt-2 text-sm font-semibold text-blue">
        Founder and Developer, Cardio MIRAI
      </p>
      <p className="mt-1 text-xs text-muted">
        Supervisor: Prof. Tetsuo Sasano
      </p>

      <div className="mt-4 flex flex-wrap justify-center gap-2">
        <Badge tone="blue">
          <a href="https://cardiomirai.com">cardiomirai.com</a>
        </Badge>
        <Badge tone="neutral">
          <a href="mailto:info@cardiomirai.com">info@cardiomirai.com</a>
        </Badge>
      </div>

      <p className="mt-4 text-xs text-muted">
        Research Prototype · Not a Medical Device
      </p>
    </Card>
  );
}
