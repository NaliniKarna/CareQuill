"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, FileText, HeartHandshake, Plus, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState, ErrorState, PageHeader } from "@/components/shared/page-states";
import { Skeleton } from "@/components/ui/skeleton";
import { familyService } from "@/services/family-service";
import type { FamilyMember } from "@/types/api";

import { AccessPanel } from "./access-panel";
import { ClaimCard } from "./claim-card";
import { STATUS_INFO, relationLabel } from "./family-constants";
import { MemberAvatar } from "./member-avatar";
import { MemberFormDialog } from "./member-form-dialog";

function MemberCard({ member }: { member: FamilyMember }) {
  const status = STATUS_INFO[member.link_status];
  return (
    <Card className="transition-colors hover:border-primary/40">
      <CardContent className="flex h-full flex-col gap-4">
        <div className="flex items-start gap-3">
          <MemberAvatar name={member.full_name} />
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium">{member.full_name}</p>
            <p className="truncate text-sm text-muted-foreground">
              {relationLabel(member.relation)}
              {member.blood_group ? ` · ${member.blood_group}` : ""}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={status.tone}>{status.label}</Badge>
          {member.invite_active && <Badge variant="outline">Invite code active</Badge>}
        </div>
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <FileText className="size-3.5" />
          {member.document_count === null
            ? member.link_status === "pending"
              ? "Documents hidden until they choose"
              : "No access to their documents"
            : `${member.document_count} document${member.document_count === 1 ? "" : "s"}`}
        </p>
        <Button asChild variant="outline" size="sm" className="mt-auto justify-between">
          <Link href={`/family/${member.id}`}>
            Open <ChevronRight className="size-4" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

export function FamilyHub() {
  const [formOpen, setFormOpen] = useState(false);
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["family", "members"],
    queryFn: () => familyService.listMembers(),
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Family"
        description="Keep health documents for your family in one place, share them with a doctor, and hand a profile over when they join."
        action={
          <Button onClick={() => setFormOpen(true)}>
            <Plus /> Add family member
          </Button>
        }
      />

      <AccessPanel />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <section aria-label="Your family" className="flex flex-col gap-4">
          {isLoading && (
            <div className="grid gap-3 sm:grid-cols-2">
              {Array.from({ length: 2 }).map((_, i) => (
                <Skeleton key={i} className="h-44" />
              ))}
            </div>
          )}
          {isError && <ErrorState description="Couldn't load your family." onRetry={() => refetch()} />}
          {data && data.length === 0 && (
            <EmptyState
              icon={Users}
              title="No family members yet"
              description="Add a parent, child or partner to store their reports and share them with their doctor."
              action={
                <Button onClick={() => setFormOpen(true)}>
                  <Plus /> Add family member
                </Button>
              }
            />
          )}
          {data && data.length > 0 && (
            <div className="grid gap-3 sm:grid-cols-2">
              {data.map((member) => (
                <MemberCard key={member.id} member={member} />
              ))}
            </div>
          )}
        </section>

        <aside className="flex flex-col gap-4">
          <ClaimCard />
          <Card className="bg-accent/30">
            <CardContent className="flex gap-3 text-sm text-muted-foreground">
              <HeartHandshake className="mt-0.5 size-4 shrink-0 text-primary" />
              <p>
                You stay in control. A relative who joins decides whether you keep helper access, and
                can end it at any time. CareQuill never diagnoses or changes a record without review.
              </p>
            </CardContent>
          </Card>
        </aside>
      </div>

      <MemberFormDialog open={formOpen} onOpenChange={setFormOpen} />
    </div>
  );
}
