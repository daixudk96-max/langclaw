"use client";

import { MapPin, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useResearchStore } from "@/stores/research-store";

export function ResearchActionBar() {
  const { selectedIds, clearSelection, setConfigSheetOpen } =
    useResearchStore();

  if (selectedIds.size === 0) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 rounded-lg border bg-background px-4 py-2.5 shadow-lg">
      <span className="text-sm font-medium tabular-nums">
        {selectedIds.size} đã chọn
      </span>

      <div className="h-4 w-px bg-border" />

      <Button
        size="sm"
        onClick={() => setConfigSheetOpen(true)}
        className="gap-1.5"
      >
        <MapPin className="h-3.5 w-3.5" />
        Khảo sát khu vực
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={clearSelection}
        className="gap-1"
      >
        <X className="h-3.5 w-3.5" />
        Hủy chọn
      </Button>
    </div>
  );
}
