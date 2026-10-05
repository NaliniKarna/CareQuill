import type { Metadata } from "next";

import { QueryProvider } from "@/components/providers/query-provider";
import { Toaster } from "@/components/ui/sonner";

import "./globals.css";

// Intentionally using the system font stack (defined in globals.css)
// instead of next/font/google: it avoids a build-time dependency on
// fonts.googleapis.com, which is unreachable in some CI/corporate-proxy
// environments, while still looking clean on every OS.

export const metadata: Metadata = {
  title: "MedQueue AI",
  description:
    "A patient-focused AI-powered health record and doctor communication platform.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <QueryProvider>
          {children}
          <Toaster position="top-right" richColors />
        </QueryProvider>
      </body>
    </html>
  );
}
