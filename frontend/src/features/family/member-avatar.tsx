import { cn } from "@/lib/utils";

import { nameInitials } from "./family-constants";

export function MemberAvatar({ name, className }: { name: string; className?: string }) {
  return (
    <div
      aria-hidden
      className={cn(
        "flex size-12 shrink-0 items-center justify-center rounded-full bg-accent text-base font-semibold text-accent-foreground",
        className,
      )}
    >
      {nameInitials(name)}
    </div>
  );
}
