/** @type {import('next').NextConfig} */

// Preferred API strategy (see frontend/README.md "API routing strategy"):
// The browser only ever calls same-origin `/api/*`. Next.js rewrites proxy
// those requests server-side to the existing FastAPI backend on Render.
// This avoids depending on backend CORS as the primary mechanism and avoids
// ever hardcoding a backend origin into client-side JS.
const BACKEND_ORIGIN =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${BACKEND_ORIGIN}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
