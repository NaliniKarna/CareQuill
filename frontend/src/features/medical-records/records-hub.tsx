"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { FileStack, HeartPulse, Pill, ShieldAlert, type LucideIcon } from "lucide-react";

import { PageHeader } from "@/components/shared/page-states";
import { cn } from "@/lib/utils";
import { allergyService } from "@/services/allergy-service";
import { conditionService } from "@/services/condition-service";
import { documentService } from "@/services/document-service";
import { medicationService } from "@/services/medication-service";
import { AllergiesView } from "@/features/allergies/allergies-view";
import { ConditionsView } from "@/features/conditions/conditions-view";
import { MedicationsView } from "@/features/medications/medications-view";

import { MedicalRecordsView } from "./medical-records-view";

const SECTIONS = [
  { id: "documents", label: "Documents", hint: "Reports & scans", icon: FileStack },
  { id: "medications", label: "Medications", hint: "What you take", icon: Pill },
  { id: "conditions", label: "Conditions", hint: "Diagnosed history", icon: HeartPulse },
  { id: "allergies", label: "Allergies", hint: "Reactions to avoid", icon: ShieldAlert },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

function isSection(value: string | null): value is SectionId {
  return SECTIONS.some((s) => s.id === value);
}

function useSectionCounts(): Record<SectionId, number | undefined> {
  const docs = useQuery({
    queryKey: ["documents", "count"],
    queryFn: () => documentService.list({ limit: 1 }),
  });
  const meds = useQuery({
    queryKey: ["medications", "count"],
    queryFn: () => medicationService.list({ active: true }),
  });
  const conds = useQuery({ queryKey: ["conditions"], queryFn: () => conditionService.list() });
  const allergies = useQuery({ queryKey: ["allergies"], queryFn: () => allergyService.list() });
  return {
    documents: docs.data?.total,
    medications: meds.data?.length,
    conditions: conds.data?.length,
    allergies: allergies.data?.length,
  };
}

export function RecordsHub() {
  const param = useSearchParams().get("tab");
  const active: SectionId = isSection(param) ? param : "documents";
  const counts = useSectionCounts();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Medical records"
        description="Your documents, medications, conditions and allergies in one place."
      />

      <nav aria-label="Record sections" className="grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
        {SECTIONS.map(({ id, label, hint, icon: Icon }) => {
          const selected = id === active;
          const count = counts[id];
          return (
            <Link
              key={id}
              href={`/medical-records?tab=${id}`}
              scroll={false}
              aria-current={selected ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-xl border bg-card p-3 transition-colors",
                "hover:border-primary/40 hover:bg-accent/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                selected && "border-primary bg-accent shadow-sm",
              )}
            >
              <SectionIcon icon={Icon} selected={selected} />
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium">{label}</span>
                  {count !== undefined && (
                    <span className="rounded-full bg-muted px-2 text-xs font-medium text-muted-foreground tabular-nums">
                      {count}
                    </span>
                  )}
                </span>
                <span className="hidden truncate text-xs text-muted-foreground sm:block">{hint}</span>
              </span>
            </Link>
          );
        })}
      </nav>

      <section aria-label={SECTIONS.find((s) => s.id === active)?.label}>
        {active === "documents" && <MedicalRecordsView embedded />}
        {active === "medications" && <MedicationsView embedded />}
        {active === "conditions" && <ConditionsView embedded />}
        {active === "allergies" && <AllergiesView embedded />}
      </section>
    </div>
  );
}

function SectionIcon({ icon: Icon, selected }: { icon: LucideIcon; selected: boolean }) {
  return (
    <span
      className={cn(
        "hidden size-9 shrink-0 items-center justify-center sm:flex rounded-lg",
        selected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
      )}
    >
      <Icon className="size-4" />
    </span>
  );
}
