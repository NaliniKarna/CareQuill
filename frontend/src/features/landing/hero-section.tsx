import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  FileText,
  Pill,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";

import { FloatChip, PhoneFrame } from "./device-frames";
import type { LandingCopy } from "./i18n";

/** Faint medical-cross pattern used behind the hero and the CTA band. */
export const CROSS_PATTERN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='48' height='48'%3E%3Cpath d='M22 16h4v6h6v4h-6v6h-4v-6h-6v-4h6z' fill='%230f6e86' fill-opacity='0.045'/%3E%3C/svg%3E\")";

export function HeroSection({ t }: { t: LandingCopy }) {
  return (
    <section
      id="home"
      className="relative scroll-mt-20 overflow-hidden bg-gradient-to-b from-accent/60 via-background to-background"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{ backgroundImage: CROSS_PATTERN }}
      />
      <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 pt-10 pb-16 sm:px-6 lg:grid-cols-2 lg:gap-8 lg:pt-16 lg:pb-24">
        {/* Left: copy */}
        <div className="flex flex-col gap-6">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-primary/20 bg-card px-3 py-1 text-xs font-medium text-primary shadow-xs sm:text-sm">
            <ShieldCheck className="size-4" aria-hidden />
            {t.hero.badge}
          </span>

          <h1 className="text-4xl leading-tight font-bold tracking-tight text-balance text-foreground sm:text-5xl lg:text-[3.4rem]">
            {t.hero.titleTop}
            <span className="mt-1 block text-primary">{t.hero.titleBy}</span>
          </h1>

          <p className="max-w-xl text-lg leading-relaxed text-muted-foreground">
            {t.hero.description}
          </p>

          <ul className="grid gap-3">
            {t.hero.bullets.map((b) => (
              <li key={b} className="flex items-start gap-3 text-[0.95rem] text-foreground">
                <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" aria-hidden />
                <span>{b}</span>
              </li>
            ))}
          </ul>

          <div className="mt-2 flex max-w-xl flex-col gap-4 rounded-2xl border border-border bg-card p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="font-semibold text-foreground">{t.hero.ctaTitle}</p>
              <p className="text-sm text-muted-foreground">{t.hero.ctaText}</p>
            </div>
            <div className="flex flex-col items-stretch gap-1.5 sm:items-end">
              <Button asChild size="lg" className="px-6">
                <Link href="/register">
                  {t.hero.signup}
                  <ArrowRight />
                </Link>
              </Button>
              <p className="text-center text-xs text-muted-foreground sm:text-right">
                {t.hero.haveAccount}{" "}
                <Link href="/login" className="font-medium text-primary hover:underline">
                  {t.hero.login}
                </Link>
              </p>
            </div>
          </div>
        </div>

        {/* Right: illustration, phone and feature labels */}
        <div className="relative mx-auto w-full max-w-[600px]">
          <div className="relative aspect-[560/540]">
            <div
              aria-hidden
              className="absolute inset-[6%] rounded-full bg-gradient-to-br from-[oklch(0.9_0.06_200)] via-[oklch(0.95_0.03_210)] to-[oklch(0.92_0.04_170)]"
            />
            <div
              aria-hidden
              className="absolute top-[10%] right-[10%] size-16 rounded-full bg-[oklch(0.88_0.08_165)] opacity-70 blur-xl"
            />
            <Image
              src="/landing/hero-people.svg"
              alt={t.hero.imageAlt}
              width={560}
              height={520}
              priority
              unoptimized
              className="absolute inset-x-0 bottom-0 h-auto w-full [mask-image:linear-gradient(to_bottom,black_78%,transparent)]"
            />
            <PhoneFrame
              src="/landing/screens/mobile-dashboard.webp"
              alt=""
              priority
              className="landing-float absolute top-[24%] left-[41%] w-[26%]"
            />

            <FloatChip icon={FileText} label={t.hero.labels.records} className="absolute top-[4%] left-0" />
            <FloatChip
              icon={CalendarClock}
              label={t.hero.labels.appointments}
              className="landing-float-delay absolute top-[2%] right-0"
            />
            <FloatChip
              icon={Pill}
              label={t.hero.labels.meds}
              tone="success"
              className="landing-float-delay absolute top-[58%] -left-2 hidden sm:flex"
            />
            <FloatChip
              icon={Sparkles}
              label={t.hero.labels.summary}
              className="absolute top-[56%] -right-2 hidden sm:flex"
            />
            <FloatChip
              icon={Send}
              label={t.hero.labels.share}
              className="absolute bottom-[4%] left-[4%]"
            />
            <FloatChip
              icon={ShieldCheck}
              label={t.hero.labels.secure}
              tone="success"
              className="landing-float-delay absolute right-0 bottom-[14%]"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
