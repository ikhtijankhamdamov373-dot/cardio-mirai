"use client";

import { useEffect, useState } from "react";
import { checkBackendHealth, HealthResult } from "@/lib/api";
import { LoadingState } from "@/components/ui/PageStatus";
import { Badge } from "@/components/ui/Badge";

export function BackendStatus() {
  const [result, setResult] = useState<HealthResult | null>(null);

  useEffect(() => {
    let active = true;
    checkBackendHealth().then((r) => {
      if (active) setResult(r);
    });
    return () => {
      active = false;
    };
  }, []);

  if (!result) return <LoadingState label="Checking analysis service…" />;

  return result.ok ? (
    <Badge tone="green">Analysis service online</Badge>
  ) : (
    <Badge tone="amber">Analysis service unavailable</Badge>
  );
}
