import { Annoyed, Frown, Laugh, Meh, Smile, type LucideIcon } from "lucide-react";

export const MOODS: { value: number; label: string; icon: LucideIcon; tone: string }[] = [
  { value: 1, label: "Very low", icon: Frown, tone: "text-destructive" },
  { value: 2, label: "Low", icon: Annoyed, tone: "text-warning-foreground" },
  { value: 3, label: "Okay", icon: Meh, tone: "text-muted-foreground" },
  { value: 4, label: "Good", icon: Smile, tone: "text-primary" },
  { value: 5, label: "Great", icon: Laugh, tone: "text-success" },
];

export function moodFor(value: number | null) {
  return MOODS.find((m) => m.value === value) ?? null;
}

/** Today's date in the user's own time zone (not UTC) as YYYY-MM-DD. */
export function localTodayIso(): string {
  const d = new Date();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${day}`;
}
