"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { getApiErrorMessage } from "@/lib/api-client";
import { notificationService } from "@/services/notification-service";

import { NotificationListItem } from "./notification-list-item";

const POLL_INTERVAL_MS = 60_000;

export function NotificationBell() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data: notifications } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationService.list(),
    refetchInterval: POLL_INTERVAL_MS,
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationService.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (error) =>
      toast.error(getApiErrorMessage(error, "Unable to mark this notification as read.")),
  });

  const unreadCount = notifications?.filter((n) => n.persisted && !n.is_read).length ?? 0;
  const recent = notifications?.slice(0, 6) ?? [];

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="size-4" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-4 min-w-4 justify-center rounded-full px-1 text-[10px]"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-3">
        <div className="flex items-center justify-between px-1">
          <p className="text-sm font-semibold">Notifications</p>
          {unreadCount > 0 && <Badge variant="secondary">{unreadCount} unread</Badge>}
        </div>
        <Separator className="my-2" />
        <div className="flex max-h-80 flex-col gap-2 overflow-y-auto">
          {recent.length === 0 && (
            <p className="px-1 py-4 text-center text-sm text-muted-foreground">
              You&apos;re all caught up.
            </p>
          )}
          {recent.map((notification) => (
            <NotificationListItem
              key={notification.id}
              notification={notification}
              onMarkRead={(id) => markReadMutation.mutate(id)}
              isMarkingRead={markReadMutation.isPending && markReadMutation.variables === notification.id}
            />
          ))}
        </div>
        <Separator className="my-2" />
        <Button asChild variant="ghost" size="sm" className="w-full" onClick={() => setOpen(false)}>
          <Link href="/notifications">View all notifications</Link>
        </Button>
      </PopoverContent>
    </Popover>
  );
}
