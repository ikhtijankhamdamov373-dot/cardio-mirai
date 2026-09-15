/**
 * Single source of truth for talking to the Cardio MIRAI FastAPI backend.
 *
 * Strategy: the browser calls same-origin `/api/backend/*`, which
 * `next.config.js` rewrites server-side to `NEXT_PUBLIC_API_BASE_URL`.
 * No component should ever hardcode a backend hostname (this replaces the
 * legacy `http://127.0.0.1:8000/...` constant that broke in production).
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

// Client-side calls go through the same-origin proxy path.
const PROXY_PREFIX = "/api/backend";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export type HealthResult =
  | { ok: true; status: "healthy" }
  | { ok: false; status: "unreachable" | "error"; message: string };

/** Fetch with a timeout so a slow/dead backend never hangs the UI forever. */
async function fetchWithTimeout(
  input: RequestInfo,
  init: RequestInit = {},
  timeoutMs = 8000
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

/** Checks backend health via our own server route (server-to-server, no CORS involved). */
export async function checkBackendHealth(): Promise<HealthResult> {
  try {
    const res = await fetchWithTimeout("/api/health", {}, 6000);
    if (!res.ok) {
      return { ok: false, status: "error", message: `Backend returned ${res.status}` };
    }
    const data = await res.json();
    return data?.ok
      ? { ok: true, status: "healthy" }
      : { ok: false, status: "error", message: "Unexpected health payload" };
  } catch (err) {
    const message =
      err instanceof Error && err.name === "AbortError"
        ? "Backend health check timed out"
        : "Backend unreachable";
    return { ok: false, status: "unreachable", message };
  }
}

/** Analyze a WFDB .hea/.dat pair or .zip upload against the existing model endpoint. */
export async function analyzeWfdb(
  files: File[],
  opts: { age?: number; sex?: string } = {}
): Promise<unknown> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  if (opts.age !== undefined) form.append("age", String(opts.age));
  if (opts.sex) form.append("sex", opts.sex);

  let res: Response;
  try {
    res = await fetchWithTimeout(
      `${PROXY_PREFIX}/analyze-wfdb`,
      { method: "POST", body: form },
      30000
    );
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError("The analysis request timed out. Please try again.", 408);
    }
    throw new ApiError("Could not reach the analysis service. Check your connection.", 0);
  }

  if (!res.ok) {
    let detail = "The analysis could not be completed.";
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body, keep default message */
    }
    throw new ApiError(detail, res.status);
  }

  return res.json();
}
