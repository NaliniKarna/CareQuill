import type { Medication, MedicationReminder } from "@/types/api";

export interface UpcomingReminder {
  id: string;
  medicationName: string;
  dosage: string | null;
  /** Local date-time of the next time this reminder fires. */
  at: Date;
  notes: string | null;
}

const DAY_CODES = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"] as const;

/** Next date-time (from `now`, inclusive) this reminder fires, or null if it
 * never does (disabled / unparseable). `days_of_week` is "daily" or a
 * comma-separated list such as "mon,wed,fri". */
export function nextOccurrence(reminder: MedicationReminder, now: Date): Date | null {
  if (!reminder.is_enabled) return null;
  const [h, m] = reminder.reminder_time.split(":").map(Number);
  if (Number.isNaN(h) || Number.isNaN(m)) return null;
  const days = reminder.days_of_week.toLowerCase();
  const allowed = days === "daily" ? null : new Set(days.split(",").map((d) => d.trim()));

  for (let offset = 0; offset < 8; offset++) {
    const candidate = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset, h, m, 0);
    if (candidate < now) continue;
    if (allowed && !allowed.has(DAY_CODES[candidate.getDay()])) continue;
    return candidate;
  }
  return null;
}

/** Soonest-first list of upcoming reminders across the given medications. */
export function buildUpcomingReminders(
  medications: Medication[],
  remindersByMedication: Array<MedicationReminder[] | undefined>,
  now: Date,
  limit = 4
): UpcomingReminder[] {
  const items: UpcomingReminder[] = [];
  medications.forEach((medication, index) => {
    for (const reminder of remindersByMedication[index] ?? []) {
      const at = nextOccurrence(reminder, now);
      if (at) {
        items.push({
          id: reminder.id,
          medicationName: medication.name,
          dosage: medication.dosage,
          at,
          notes: reminder.notes,
        });
      }
    }
  });
  return items.sort((a, b) => a.at.getTime() - b.at.getTime()).slice(0, limit);
}

export function formatReminderWhen(at: Date, now: Date): string {
  const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const dayDiff = Math.round((startOf(at) - startOf(now)) / 86_400_000);
  const time = at.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (dayDiff === 0) return `Today, ${time}`;
  if (dayDiff === 1) return `Tomorrow, ${time}`;
  return `${at.toLocaleDateString(undefined, { weekday: "short" })}, ${time}`;
}
