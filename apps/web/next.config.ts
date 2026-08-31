import fs from "node:fs";
import path from "node:path";

import type { NextConfig } from "next";

function loadParentEnv() {
  const envPath = path.resolve(__dirname, "../../.env");
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
    const i = trimmed.indexOf("=");
    const key = trimmed.slice(0, i).trim();
    let val = trimmed.slice(i + 1).split("#")[0].trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (process.env[key] === undefined || process.env[key] === "") {
      process.env[key] = val;
    }
  }
}

loadParentEnv();

const apiInternal = (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const isProd = process.env.NODE_ENV === "production";
const scriptSrc = isProd
  ? "script-src 'self' 'unsafe-inline' https://telegram.org https://*.telegram.org"
  : "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://telegram.org https://*.telegram.org";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "X-DNS-Prefetch-Control", value: "off" },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      scriptSrc,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https://telegram.org https://*.telegram.org https://t.me",
      "font-src 'self' data:",
      "connect-src 'self' https://telegram.org https://*.telegram.org",
      "frame-src 'self' https://oauth.telegram.org https://telegram.org https://*.telegram.org",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  allowedDevOrigins: ["whiteshop.tech", "www.whiteshop.tech"],
  agentRules: false,
  devIndicators: false,
  images: {
    formats: ["image/webp"],
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return {
      beforeFiles: [
        { source: "/__nextjs_launch-editor", destination: "/blocked-devtools" },
        { source: "/__nextjs_launch-editor/:path*", destination: "/blocked-devtools" },
        { source: "/__nextjs_original-stack-frames", destination: "/blocked-devtools" },
      ],
      afterFiles: [
        { source: "/api/:path*", destination: `${apiInternal}/api/:path*` },
        { source: "/health", destination: `${apiInternal}/health` },
      ],
    };
  },
};

export default nextConfig;
