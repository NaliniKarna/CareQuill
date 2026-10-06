import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle (.next/standalone): the production image
  // ships only what is needed to run, instead of the full node_modules.
  output: "standalone",
  compress: true,
  poweredByHeader: false,
  reactStrictMode: true,
  experimental: {
    // Import only the icons/components actually used instead of whole barrels.
    optimizePackageImports: ["lucide-react", "@radix-ui/react-select", "@radix-ui/react-dialog"],
  },
  async redirects() {
    // Standalone pages that moved: Health profile -> Settings; medications,
    // conditions and allergies -> sections of Medical records.
    return [
      { source: "/profile", destination: "/settings?tab=profile", permanent: false },
      { source: "/medications", destination: "/medical-records?tab=medications", permanent: false },
      { source: "/conditions", destination: "/medical-records?tab=conditions", permanent: false },
      { source: "/doctors", destination: "/appointments?tab=doctors", permanent: false },
      { source: "/reports", destination: "/appointments?tab=doctors", permanent: false },
      { source: "/notifications", destination: "/settings?tab=notifications", permanent: false },
      { source: "/timeline", destination: "/journal", permanent: false },
      { source: "/ai-summary", destination: "/record-summary", permanent: false },
      { source: "/allergies", destination: "/medical-records?tab=allergies", permanent: false },
    ];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
