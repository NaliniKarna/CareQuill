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
