"use client";

import { Check, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { Notification } from "@/types/api";

import { NOTIFICATION_ICON, NOTIFICATION_LABEL } from "./notification-utils";

export function NotificationListItem({
  notification,
  onMarkRead,
  isMarkingRead,
}: {
  notification: Notification;
  onMarkRead?: (id: string) => void;
  isMarkingRead?: boolean;
}) {
  const Icon = NOTIFICATION_ICON[notification.type];

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-md border px-3 py-3 text-sm",
        notification.persisted && !notification.is_read
          ? "border-primary/30 bg-accent/50"
          : "border-border"
      )}
    >
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full bg-accent text-accent-foreground">
        <Icon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{notification.title}</p>
          <Badge variant="outline" className="text-[10px]">
            {NOTIFICATION_LABEL[notification.type]}
          </Badge>
          {!notification.persisted && (
            <Badge variant="secondary" className="text-[10px]">
              Live status, not stored
            </Badge>
          )}
        </div>
        <p className="mt-0.5 text-muted-foreground">{notification.body}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {formatRelativeTime(notification.created_at)}
        </p>
      </div>
      {notification.persisted && !notification.is_read && onMarkRead && (
        <Button
          variant="ghost"
          size="sm"
          className="shrink-0"
          disabled={isMarkingRead}
          onClick={() => onMarkRead(notification.id)}
        >
          {isMarkingRead ? <Loader2 className="animate-spin" /> : <Check />}
          Mark read
        </Button>
      )}
    </div>
  );
}
