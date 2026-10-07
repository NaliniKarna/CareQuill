import type { FamilyLinkStatus, FamilyRelation } from "@/types/api";

export const RELATIONS: { value: FamilyRelation; label: string }[] = [
  { value: "spouse", label: "Spouse / partner" },
  { value: "parent", label: "Parent" },
  { value: "child", label: "Child" },
  { value: "sibling", label: "Sibling" },
  { value: "grandparent", label: "Grandparent" },
  { value: "grandchild", label: "Grandchild" },
  { value: "other", label: "Other" },
];

export const BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];

export function relationLabel(value: string): string {
  return RELATIONS.find((r) => r.value === value)?.label ?? value;
}

type BadgeTone = "secondary" | "warning" | "success" | "outline";

export const STATUS_INFO: Record<
  FamilyLinkStatus,
  { label: string; tone: BadgeTone; hint: string }
> = {
  unlinked: {
    label: "Managed by you",
    tone: "secondary",
    hint: "No account yet. You keep their documents.",
  },
  pending: {
    label: "Waiting for their choice",
    tone: "warning",
    hint: "They claimed this profile. They decide if you keep access.",
  },
  active: {
    label: "You are a helper",
    tone: "success",
    hint: "They keep you as a helper on their record.",
  },
  ended: {
    label: "Access ended",
    tone: "outline",
    hint: "They removed your access.",
  },
};

export function nameInitials(name: string): string {
  const parts = name.split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "?") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}
