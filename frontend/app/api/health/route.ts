import { NextResponse } from "next/server";

// Server-to-server call: runs on the Next.js server, never in the browser,
// so it works regardless of backend CORS configuration and never exposes
// the backend URL to client-side code.
const BACKEND_ORIGIN =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export async function GET() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 6000);

  try {
    const res = await fetch(`${BACKEND_ORIGIN}/api/health`, {
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timer);

    if (!res.ok) {
      return NextResponse.json(
        { ok: false, status: "error" },
        { status: 502 }
      );
    }
    const data = await res.json();
    return NextResponse.json({ ok: Boolean(data?.ok) });
  } catch {
    clearTimeout(timer);
    // Never leak internal error detail (stack traces, host info) to the client.
    return NextResponse.json(
      { ok: false, status: "unreachable" },
      { status: 503 }
    );
  }
}
