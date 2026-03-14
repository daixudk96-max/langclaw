"use client";

import { useState } from "react";
import { Activity, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ActivityItem } from "./activity-item";
import { useActivityStore } from "@/stores/activity-store";

interface ActivityFeedProps {
  campaignId: string;
}

export function ActivityFeed({ campaignId }: ActivityFeedProps) {
  const [open, setOpen] = useState(false);
  const { activities, unreadCount, markRead } = useActivityStore();

  const handleOpen = () => {
    setOpen(true);
    markRead();
  };

  return (
    <>
      {/* Floating button */}
      <Button
        variant="outline"
        size="icon"
        className="fixed bottom-6 right-6 h-12 w-12 rounded-full shadow-lg z-50"
        onClick={handleOpen}
      >
        <Activity className="h-5 w-5" />
        {unreadCount > 0 && (
          <Badge className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-[10px]">
            {unreadCount > 9 ? "9+" : unreadCount}
          </Badge>
        )}
      </Button>

      {/* Activity sheet */}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full sm:max-w-sm flex flex-col p-0">
          <SheetHeader className="px-4 py-3 border-b">
            <SheetTitle className="text-base">Activity log</SheetTitle>
          </SheetHeader>

          <ScrollArea className="flex-1 p-4">
            {activities.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">
                No activity yet.
              </p>
            ) : (
              <div className="space-y-3">
                {activities.map((activity) => (
                  <ActivityItem key={activity.id} activity={activity} />
                ))}
              </div>
            )}
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </>
  );
}
