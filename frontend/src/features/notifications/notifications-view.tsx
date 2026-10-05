"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { toast } from "sonner";

import { EmptyState, ErrorState, ListSkeleton, PageHeader } from "@/components/shared/page-states";
import { getApiErrorMessage } from "@/lib/api-client";
import { notificationService } from "@/services/notification-service";

import { NotificationListItem } from "./notification-list-item";

export function NotificationsView() {
  const queryClient = useQueryClient();

  const { data: notifications, isLoading, isError, refetch } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationService.list(),
    refetchInterval: 60_000,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationService.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (error) =>
      toast.error(getApiErrorMessage(error, "Unable to mark this notification as read.")),
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Notifications"
        description="Updates about your AI summaries, documents, and shared reports, plus upcoming appointments and medication reminders."
      />

      {isLoading && <ListSkeleton />}
      {isError && (
        <ErrorState description="Couldn't load your notifications." onRetry={() => refetch()} />
      )}

      {notifications && notifications.length === 0 && (
        <EmptyState icon={Bell} title="No notifications" description="You're all caught up." />
      )}

      {notifications && notifications.length > 0 && (
        <div className="flex flex-col gap-2">
          {notifications.map((notification) => (
            <NotificationListItem
              key={notification.id}
              notification={notification}
              onMarkRead={(id) => markReadMutation.mutate(id)}
              isMarkingRead={
                markReadMutation.isPending && markReadMutation.variables === notification.id
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
