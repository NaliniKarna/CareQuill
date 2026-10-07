import Image from "next/image";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

/** Desktop app screenshot inside a light browser window. */
export function BrowserFrame({
  src,
  alt,
  url,
  className,
  priority = false,
}: {
  src: string;
  alt: string;
  url: string;
  className?: string;
  priority?: boolean;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-card shadow-[0_24px_60px_-20px_oklch(0.35_0.08_224/0.35)]",
        className
      )}
    >
      <div className="flex items-center gap-2 border-b border-border bg-muted/70 px-3 py-2">
        <span className="size-2.5 rounded-full bg-[oklch(0.75_0.12_25)]" />
        <span className="size-2.5 rounded-full bg-[oklch(0.82_0.12_85)]" />
        <span className="size-2.5 rounded-full bg-[oklch(0.75_0.12_155)]" />
        <span className="ml-2 truncate rounded-md bg-background px-2.5 py-0.5 text-[11px] text-muted-foreground">
          carequill.app/{url}
        </span>
      </div>
      <Image
        src={src}
        alt={alt}
        width={1440}
        height={988}
        unoptimized
        priority={priority}
        className="h-auto w-full"
      />
    </div>
  );
}

/** Mobile app screenshot inside a phone outline. */
export function PhoneFrame({
  src,
  alt,
  className,
  priority = false,
}: {
  src: string;
  alt: string;
  className?: string;
  priority?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-[1.6rem] border-[5px] border-[oklch(0.25_0.03_250)] bg-[oklch(0.25_0.03_250)] shadow-[0_24px_50px_-16px_oklch(0.3_0.06_224/0.5)]",
        className
      )}
    >
      <div className="relative overflow-hidden rounded-[1.2rem] bg-background">
        <span className="absolute top-1.5 left-1/2 z-10 h-1.5 w-12 -translate-x-1/2 rounded-full bg-[oklch(0.25_0.03_250)]" />
        <Image
          src={src}
          alt={alt}
          width={780}
          height={1600}
          unoptimized
          priority={priority}
          className="h-auto w-full"
        />
      </div>
    </div>
  );
}

/** Small floating label used around screenshots. */
export function FloatChip({
  icon: Icon,
  label,
  className,
  tone = "primary",
}: {
  icon: LucideIcon;
  label: string;
  className?: string;
  tone?: "primary" | "success" | "warning";
}) {
  const toneClass = {
    primary: "bg-accent text-primary",
    success: "bg-success/15 text-success",
    warning: "bg-warning/20 text-warning-foreground",
  }[tone];
  return (
    <div
      className={cn(
        "landing-float flex items-center gap-2 rounded-xl border border-border bg-card/95 px-3 py-2 text-xs font-medium text-foreground shadow-lg backdrop-blur sm:text-sm",
        className
      )}
    >
      <span className={cn("flex size-7 shrink-0 items-center justify-center rounded-lg", toneClass)}>
        <Icon className="size-4" aria-hidden />
      </span>
      <span className="whitespace-nowrap">{label}</span>
    </div>
  );
}
