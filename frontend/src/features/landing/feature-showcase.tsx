import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  FileSearch,
  FileText,
  LayoutDashboard,
  Send,
  Users,
  type LucideIcon,
} from "lucide-react";

import { Reveal, TiltStage } from "./motion";
import { BrowserFrame, FloatChip, PhoneFrame } from "./device-frames";
import type { LandingCopy } from "./i18n";

type FeatureId = keyof LandingCopy["features"]["items"];

type Overlay =
  | { kind: "phone"; src: string }
  | { kind: "screen"; src: string; width: number; height: number }
  | { kind: "chip"; icon: LucideIcon; tone?: "primary" | "success" | "warning" };

interface FeatureVisual {
  id: FeatureId;
  icon: LucideIcon;
  screen: string;
  url: string;
  overlay?: Overlay;
}

const S = "/landing/screens";

/** Order and visuals of the feature rows; text comes from the i18n copy. */
const FEATURES: FeatureVisual[] = [
  {
    id: "dashboard",
    icon: LayoutDashboard,
    screen: `${S}/dashboard.webp`,
    url: "dashboard",
    overlay: { kind: "phone", src: `${S}/mobile-dashboard.webp` },
  },
  {
    id: "documents",
    icon: FileSearch,
    screen: `${S}/documents.webp`,
    url: "medical-records",
    overlay: { kind: "screen", src: `${S}/doc-review.webp`, width: 900, height: 443 },
  },
  {
    id: "family",
    icon: Users,
    screen: `${S}/family.webp`,
    url: "family",
    overlay: { kind: "chip", icon: Users, tone: "success" },
  },
  {
    id: "share",
    icon: Send,
    screen: `${S}/share.webp`,
    url: "appointments?tab=share",
    overlay: { kind: "chip", icon: FileText, tone: "success" },
  },
];

function FeatureOverlay({ overlay, label }: { overlay: Overlay; label?: string }) {
  if (overlay.kind === "phone") {
    return (
      <div className="landing-depth-2 absolute -bottom-6 -left-3 w-[24%] min-w-[92px] sm:-left-6">
        <PhoneFrame src={overlay.src} alt="" className="landing-float" />
      </div>
    );
  }
  if (overlay.kind === "screen") {
    return (
      <div className="landing-depth-2 absolute -bottom-8 -left-3 w-[58%] sm:-left-8">
        <div className="landing-float overflow-hidden rounded-lg border border-border bg-card shadow-2xl">
          <Image
            src={overlay.src}
            alt=""
            width={overlay.width}
            height={overlay.height}
            unoptimized
            className="h-auto w-full"
          />
        </div>
      </div>
    );
  }
  if (!label) return null;
  return (
    <div className="landing-depth-2 absolute -bottom-5 -left-2 sm:-left-6">
      <FloatChip icon={overlay.icon} label={label} tone={overlay.tone} />
    </div>
  );
}

export function FeatureShowcase({ t }: { t: LandingCopy }) {
  return (
    <div>
      <div className="flex flex-col gap-24 lg:gap-36">
        {FEATURES.map((f, i) => {
          const copy = t.features.items[f.id];
          const floatLabel = "float" in copy ? copy.float : undefined;
          const Icon = f.icon;
          const flip = i % 2 === 1;
          return (
            <article
              key={f.id}
              aria-labelledby={`feature-${f.id}`}
              className="grid items-center gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16"
            >
              {/* Description */}
              <Reveal className={flip ? "flex flex-col gap-5 lg:order-2" : "flex flex-col gap-5"}>
                <div className="flex items-center gap-3">
                  <span className="flex size-11 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-md">
                    <Icon className="size-5" aria-hidden />
                  </span>
                  <span className="text-sm font-semibold tracking-wide text-primary uppercase">
                    {String(i + 1).padStart(2, "0")} · {copy.tag}
                  </span>
                </div>
                <h3
                  id={`feature-${f.id}`}
                  className="scroll-mt-24 text-2xl font-bold tracking-tight text-balance text-foreground sm:text-3xl"
                >
                  {copy.title}
                </h3>
                <p className="text-base leading-relaxed text-muted-foreground">{copy.text}</p>
                <ul className="grid gap-3">
                  {copy.points.map((p) => (
                    <li
                      key={p}
                      className="flex items-start gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-xs transition hover:-translate-y-0.5 hover:shadow-md"
                    >
                      <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-success/15 text-success">
                        <Check className="size-3.5" aria-hidden />
                      </span>
                      <span className="text-sm text-foreground">{p}</span>
                    </li>
                  ))}
                </ul>
                <Link
                  href="/register"
                  className="inline-flex w-fit items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
                >
                  {t.features.tryIt}
                  <ArrowRight className="size-4" aria-hidden />
                </Link>
              </Reveal>

              {/* Screenshot on a tilted 3D stage */}
              <Reveal delay={120} className={flip ? "lg:order-1" : undefined}>
                <TiltStage direction={flip ? "right" : "left"} className="relative px-2 pb-8 sm:px-6">
                  <div
                    aria-hidden
                    className={`landing-orb pointer-events-none absolute ${flip ? "-right-4" : "-left-4"} -top-6 size-40 rounded-full bg-[oklch(0.88_0.08_195)] opacity-60 blur-3xl`}
                  />
                  <div
                    aria-hidden
                    className="absolute inset-x-6 inset-y-4 -rotate-2 rounded-3xl bg-gradient-to-br from-accent to-[oklch(0.94_0.04_170)]"
                  />
                  <div className="relative [transform-style:preserve-3d]">
                    <BrowserFrame
                      src={f.screen}
                      alt={`${copy.tag} – CareQuill`}
                      url={f.url}
                      className={i % 2 === 0 ? "" : "landing-float-delay"}
                    />
                    {f.overlay && <FeatureOverlay overlay={f.overlay} label={floatLabel} />}
                  </div>
                </TiltStage>
              </Reveal>
            </article>
          );
        })}
      </div>
    </div>
  );
}
