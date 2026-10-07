"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuthStore } from "@/store/auth-store";

import { HeroSection } from "./hero-section";
import { useLandingCopy } from "./i18n";
import { LandingHeader } from "./landing-header";
import {
  ContactSection,
  CtaBand,
  FaqSection,
  HowItWorksSection,
  LandingFooter,
  WhySection,
} from "./landing-sections";

export function LandingPage() {
  const router = useRouter();
  const { accessToken, user, hasHydrated } = useAuthStore();
  const { t } = useLandingCopy();

  // Signed-in patients go straight to their dashboard.
  useEffect(() => {
    if (hasHydrated && accessToken && user) {
      router.replace("/dashboard");
    }
  }, [hasHydrated, accessToken, user, router]);

  return (
    <div className="flex flex-1 flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground"
      >
        {t.nav.skip}
      </a>
      <LandingHeader t={t} />
      <main id="main" className="flex-1">
        <HeroSection t={t} />
        <WhySection t={t} />
        <HowItWorksSection t={t} />
        <FaqSection t={t} />
        <ContactSection t={t} />
        <CtaBand t={t} />
      </main>
      <LandingFooter t={t} />
    </div>
  );
}
