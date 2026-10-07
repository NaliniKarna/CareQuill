"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, FileText, Lock, Pencil, Send, ShieldCheck, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ErrorState, ListSkeleton } from "@/components/shared/page-states";
import { familyService } from "@/services/family-service";
import { cn } from "@/lib/utils";
import type { FamilyMember } from "@/types/api";

import { MemberAccessTab } from "./member-access-tab";
import { MemberDocumentsTab } from "./member-documents-tab";
import { MemberShareTab } from "./member-share-tab";
import { STATUS_INFO, relationLabel } from "./family-constants";
import { MemberAvatar } from "./member-avatar";
import { MemberFormDialog } from "./member-form-dialog";

type TabId = "documents" | "share" | "access";

const TABS: { id: TabId; label: string; hint: string; icon: LucideIcon }[] = [
  { id: "documents", label: "Documents", hint: "Reports and scans", icon: FileText },
  { id: "share", label: "Share", hint: "Send to a doctor", icon: Send },
  { id: "access", label: "Access", hint: "Invite and control", icon: ShieldCheck },
];

function parseTab(value: string | null): TabId {
  return TABS.some((t) => t.id === value) ? (value as TabId) : "documents";
}

function LockedNotice({ member }: { member: FamilyMember }) {
  return (
    <Card>
      <CardContent className="flex items-start gap-3 py-6">
        <Lock className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
        <div>
          <p className="font-medium">
            {member.link_status === "pending"
              ? `Waiting for ${member.full_name} to choose`
              : "Your access has ended"}
          </p>
          <p className="text-sm text-muted-foreground">
            {member.link_status === "pending"
              ? "They claimed this profile and their documents moved to their own account. You can see them once they choose to keep you as a helper."
              : `${member.full_name} removed your access, so their documents are no longer visible here. They can allow you again at any time.`}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export function FamilyMemberView() {
  const { id } = useParams<{ id: string }>();
  const params = useSearchParams();
  const active = parseTab(params.get("tab"));
  const [editOpen, setEditOpen] = useState(false);

  const { data: member, isLoading, isError, refetch } = useQuery({
    queryKey: ["family", "member", id],
    queryFn: () => familyService.getMember(id),
    retry: false,
  });

  if (isLoading) return <ListSkeleton rows={3} />;
  if (isError || !member) {
    return (
      <div className="flex flex-col gap-4">
        <Button asChild variant="ghost" size="sm" className="self-start">
          <Link href="/family">
            <ArrowLeft /> Family
          </Link>
        </Button>
        <ErrorState
          title="Family member not found"
          description="This profile may have been removed."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const status = STATUS_INFO[member.link_status];
  const hasAccess = member.link_status === "unlinked" || member.link_status === "active";

  return (
    <div className="flex flex-col gap-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2 self-start">
        <Link href="/family">
          <ArrowLeft /> Family
        </Link>
      </Button>

      <Card>
        <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <MemberAvatar name={member.full_name} className="size-16 text-xl" />
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-2xl font-semibold tracking-tight">{member.full_name}</h1>
            <p className="text-sm text-muted-foreground">
              {relationLabel(member.relation)}
              {member.blood_group ? ` · Blood group ${member.blood_group}` : ""}
              {member.date_of_birth ? ` · Born ${member.date_of_birth}` : ""}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge variant={status.tone}>{status.label}</Badge>
              <span className="text-xs text-muted-foreground">{status.hint}</span>
            </div>
          </div>
          {member.link_status === "unlinked" && (
            <Button variant="outline" onClick={() => setEditOpen(true)}>
              <Pencil /> Edit profile
            </Button>
          )}
        </CardContent>
      </Card>

      <nav aria-label="Family member sections" className="grid grid-cols-3 gap-2 sm:gap-3 lg:max-w-3xl">
        {TABS.map(({ id: tabId, label, hint, icon: Icon }) => {
          const selected = tabId === active;
          return (
            <Link
              key={tabId}
              href={`/family/${member.id}?tab=${tabId}`}
              scroll={false}
              aria-current={selected ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-xl border bg-card p-3 transition-colors",
                "hover:border-primary/40 hover:bg-accent/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                selected && "border-primary bg-accent shadow-sm",
              )}
            >
              <span
                className={cn(
                  "hidden size-9 shrink-0 items-center justify-center rounded-lg sm:flex",
                  selected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground",
                )}
              >
                <Icon className="size-4" />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium">{label}</span>
                <span className="hidden truncate text-xs text-muted-foreground sm:block">{hint}</span>
              </span>
            </Link>
          );
        })}
      </nav>

      <section aria-label={TABS.find((t) => t.id === active)?.label}>
        {active === "access" && <MemberAccessTab member={member} />}
        {active !== "access" && !hasAccess && <LockedNotice member={member} />}
        {active === "documents" && hasAccess && <MemberDocumentsTab member={member} />}
        {active === "share" && hasAccess && <MemberShareTab member={member} />}
      </section>

      <MemberFormDialog open={editOpen} onOpenChange={setEditOpen} member={member} />
    </div>
  );
}
