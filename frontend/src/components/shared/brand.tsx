import Image from "next/image";

import { cn } from "@/lib/utils";

/** The CareQuill shield-and-heart mark (transparent PNG, teal). */
export function BrandMark({ className }: { className?: string }) {
  return (
    <Image
      src="/brand/carequill-mark.png"
      alt=""
      width={656}
      height={720}
      unoptimized
      priority
      className={cn("h-8 w-auto", className)}
    />
  );
}

/** Mark + wordmark. The wordmark is real text so it stays crisp and selectable. */
export function BrandLogo({
  className,
  markClassName,
  textClassName,
}: {
  className?: string;
  markClassName?: string;
  textClassName?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <BrandMark className={markClassName} />
      <span className={cn("text-lg font-semibold tracking-tight text-primary", textClassName)}>
        CareQuill
      </span>
    </span>
  );
}
