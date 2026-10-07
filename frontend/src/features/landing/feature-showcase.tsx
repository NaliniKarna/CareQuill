import Image from "next/image";
import Link from "next/link";
import {
  ArrowRight,
  Check,
  FileSearch,
  FileText,
  LayoutDashboard,
  Send,
  UserRound,
  type LucideIcon,
} from "lucide-react";

import { BrowserFrame, FloatChip, PhoneFrame } from "./device-frames";
import type { LandingCopy } from "./i18n";

type FeatureId = keyof LandingCopy["features"]["items"] | "family";

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

/**
 * Order and visuals of the feature rows.
 *
 * Only the first four features are currently shown on the landing page:
 * 01 Dashboard
 * 02 Medical documents
 * 03 Family
 * 04 Share with your doctor
 *
 * The other existing features are kept below in comments so they can
 * easily be restored later without deleting their original definitions.
 */
const FEATURES: FeatureVisual[] = [
  // 01 · Dashboard
  {
    id: "dashboard",
    icon: LayoutDashboard,
    screen: `${S}/dashboard.webp`,
    url: "dashboard",
    overlay: { kind: "phone", src: `${S}/mobile-dashboard.webp` },
  },

  // 02 · Medical documents
  {
    id: "documents",
    icon: FileSearch,
    screen: `${S}/documents.webp`,
    url: "medical-records",
    overlay: {
      kind: "screen",
      src: `${S}/doc-review.webp`,
      width: 900,
      height: 443,
    },
  },

  // 03 · Family
  //
  // There is currently no dedicated family.webp screenshot in the
  // landing/screens folder, so the existing share.webp image is used
  // temporarily. The Family text is defined locally below.
  {
    id: "family",
    icon: UserRound,
    screen: `${S}/family.png`,
    url: "family",
  },

  // 04 · Share with your doctor
  {
    id: "share",
    icon: Send,
    screen: `${S}/share.webp`,
    url: "appointments?tab=share",
    overlay: { kind: "chip", icon: FileText, tone: "success" },
  },

  /*
  -----------------------------------------------------------------------
  HIDDEN FOR NOW
  -----------------------------------------------------------------------

  {
    id: "medications",
    icon: Pill,
    screen: `${S}/medications.webp`,
    url: "medical-records?tab=medications",
    overlay: { kind: "phone", src: `${S}/mobile-medications.webp` },
  },

  {
    id: "conditions",
    icon: HeartPulse,
    screen: `${S}/conditions.webp`,
    url: "medical-records?tab=conditions",
    overlay: {
      kind: "screen",
      src: `${S}/allergies.webp`,
      width: 900,
      height: 260,
    },
  },

  {
    id: "appointments",
    icon: CalendarClock,
    screen: `${S}/appointments.webp`,
    url: "appointments",
    overlay: {
      kind: "screen",
      src: `${S}/doctors.webp`,
      width: 900,
      height: 279,
    },
  },

  {
    id: "summary",
    icon: Sparkles,
    screen: `${S}/record-summary.webp`,
    url: "record-summary",
    overlay: {
      kind: "chip",
      icon: ClipboardList,
      tone: "warning",
    },
  },

  {
    id: "journal",
    icon: NotebookPen,
    screen: `${S}/journal.webp`,
    url: "journal",
    overlay: {
      kind: "chip",
      icon: Lock,
    },
  },

  {
    id: "notifications",
    icon: Bell,
    screen: `${S}/notifications.webp`,
    url: "settings?tab=notifications",
  },

  {
    id: "profile",
    icon: UserRound,
    screen: `${S}/profile.webp`,
    url: "settings?tab=profile",
  },

  {
    id: "privacy",
    icon: ShieldCheck,
    screen: `${S}/privacy.webp`,
    url: "settings?tab=data",
    overlay: {
      kind: "chip",
      icon: ShieldCheck,
      tone: "success",
    },
  },
  */
];

function FeatureOverlay({
  overlay,
  label,
}: {
  overlay: Overlay;
  label?: string;
}) {
  if (overlay.kind === "phone") {
    return (
      <PhoneFrame
        src={overlay.src}
        alt=""
        className="landing-float absolute -bottom-6 -left-3 w-[24%] min-w-[92px] sm:-left-6"
      />
    );
  }

  if (overlay.kind === "screen") {
    return (
      <div className="landing-float absolute -bottom-8 -left-3 w-[58%] overflow-hidden rounded-lg border border-border bg-card shadow-2xl sm:-left-8">
        <Image
          src={overlay.src}
          alt=""
          width={overlay.width}
          height={overlay.height}
          unoptimized
          className="h-auto w-full"
        />
      </div>
    );
  }

  if (!label) return null;

  return (
    <FloatChip
      icon={overlay.icon}
      label={label}
      tone={overlay.tone}
      className="absolute -bottom-5 -left-2 sm:-left-6"
    />
  );
}

export function FeatureShowcase({ t }: { t: LandingCopy }) {
  return (
    <div className="flex flex-col gap-24 lg:gap-32">
      {FEATURES.map((f, i) => {
        /*
         * Family is intentionally kept local here so we do not have to
         * change the existing English/Nepali landing-page i18n structure.
         */
        const copy =
          f.id === "family"
            ? {
                tag: "Family",
                title: "Keep health documents for your family in one place",
                text: "Keep health documents for your family in one place, and share them with a doctor.",
                points: [
                  "Keep family health documents organised in one place",
                  "Manage a family member's health information until they join",
                  "Share the relevant information with a doctor",
                ],
              }
            : t.features.items[f.id];

        const floatLabel =
          "float" in copy && typeof copy.float === "string"
            ? copy.float
            : undefined;
        const Icon = f.icon;

        return (
          <article
            key={f.id}
            aria-labelledby={`feature-${f.id}`}
            className="grid items-center gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16"
          >
            {/* Left: description */}
            <div className="flex flex-col gap-5">
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
                className="text-2xl font-bold tracking-tight text-balance text-foreground sm:text-3xl"
              >
                {copy.title}
              </h3>

              <p className="text-base leading-relaxed text-muted-foreground">
                {copy.text}
              </p>

              <ul className="grid gap-3">
                {copy.points.map((p) => (
                  <li
                    key={p}
                    className="flex items-start gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-xs"
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
            </div>

            {/* Right: floating screenshot of that page */}
            <div className="relative px-2 pb-8 sm:px-6">
              <div
                aria-hidden
                className="absolute inset-x-6 inset-y-4 -rotate-2 rounded-3xl bg-gradient-to-br from-accent to-[oklch(0.94_0.04_170)]"
              />

              <div className="relative">
                <BrowserFrame
                  src={f.screen}
                  alt={`${copy.tag} – CareQuill`}
                  url={f.url}
                  className={
                    i % 2 === 0
                      ? "landing-float"
                      : "landing-float landing-float-delay"
                  }
                />

                {f.overlay && (
                  <FeatureOverlay
                    overlay={f.overlay}
                    label={floatLabel}
                  />
                )}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}