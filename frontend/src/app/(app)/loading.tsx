import { Skeleton } from "@/components/ui/skeleton";

/** Shown instantly while a route segment loads, so navigation never feels
 * frozen on a slow connection or a cold dev server. */
export default function Loading() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-4 w-80" />
      <Skeleton className="h-32" />
      <Skeleton className="h-32" />
    </div>
  );
}
